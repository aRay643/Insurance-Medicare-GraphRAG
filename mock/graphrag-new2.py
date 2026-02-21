# ======================== 1. 导入所有核心依赖 ========================
from difflib import get_close_matches
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Set
import uvicorn
import hashlib
import hmac
import base64
import requests
from datetime import datetime, timezone  # 修复时区警告
from urllib.parse import urlparse
import re
from neo4j import GraphDatabase
import threading
from contextlib import asynccontextmanager

# neo4j配置
NEO4J_URI = "bolt://127.0.0.1:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "88888888"
NEO4J_DATABASE = "neo4j"

driver = None

def init_neo4j_driver():
    """初始化 Neo4j 驱动"""
    global driver
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

def close_neo4j_driver():
    """关闭驱动连接"""
    if driver:
        driver.close()


# ======================== 节点名缓存（减少全表扫描） ========================
class NodeCache:
    """带 TTL 的简单节点名缓存，线程安全。"""
    def __init__(self, ttl: int = 3600, limit: int = 10000):
        self.ttl = ttl
        self.limit = limit
        self.lock = threading.Lock()
        self.nodes: List[str] = []
        self.timestamp = None

    def is_valid(self) -> bool:
        if not self.timestamp:
            return False
        return (datetime.now() - self.timestamp).total_seconds() < self.ttl

    def refresh(self):
        """从 Neo4j 加载节点名（只加载 name 字段），失败则保持旧缓存。"""
        if not driver:
            return
        try:
            with driver.session(database=NEO4J_DATABASE) as session:
                q = f"""
                MATCH (n)
                WHERE n.name IS NOT NULL
                RETURN DISTINCT n.name as name
                LIMIT {self.limit}
                """
                result = session.run(q)
                names = [rec["name"] for rec in result if rec and rec.get("name")]
            with self.lock:
                self.nodes = names
                self.timestamp = datetime.now()
        except Exception as e:
            # 不抛异常，日志输出供排查
            print(f"⚠️ NodeCache.refresh 失败：{e}")

    def get(self, refresh: bool = False) -> List[str]:
        with self.lock:
            if not refresh and self.is_valid() and self.nodes:
                return self.nodes
        # 切换到外部刷新以减少锁持有
        self.refresh()
        with self.lock:
            return list(self.nodes)


# 全局缓存实例（默认 1 小时）
node_cache = NodeCache(ttl=3600, limit=10000)

# ======================== 2. 全局配置（替换Key/Secret + 兜底开关） ========================
# 讯飞星火 LLM 配置
SPARK_API_KEY = "APIKey"  # 替换为控制台的 APIKey
SPARK_API_SECRET = "APISecret"  # 替换为控制台的 APISecret
SPARK_MODEL = "lite"
# 兜底开关：API恢复后改为 False 即可切回星火真实调用
SPARK_API_FALLBACK = False

# FastAPI 服务配置
API_HOST = "0.0.0.0"
API_PORT = 8000

# 本地兜底实体提取规则（适配保险医疗场景，可扩展）
FALLBACK_ENTITY_RULES = {
    "高血压": "原发性高血压",
    "高血压病": "原发性高血压",
    "糖尿病": "2型糖尿病",
    "平安e生保": "平安e生保护理险",
    "e生保": "平安e生保护理险",
    "平安e生保护理险": "平安e生保护理险",
    "住院医疗费用": "住院医疗费用",
    "等待期": "等待期"
}
# 年龄提取正则（匹配问题中的数字+岁）
AGE_PATTERN = re.compile(r"(\d+)岁")

# 优化的模糊匹配工具（优先使用 rapidfuzz，回退到 difflib）
try:
    from rapidfuzz import process as _rf_process, fuzz as _rf_fuzz
    _HAS_RAPIDFUZZ = True
except Exception:
    _HAS_RAPIDFUZZ = False


def normalize_name(s: str) -> str:
    """基础字符串规范化：小写、去空白和常见标点，便于匹配"""
    if not s:
        return ""
    s2 = s.strip().lower()
    # 去掉常见中文/英文标点与空白
    s2 = re.sub(r"[\s\u3000]+", "", s2)
    s2 = re.sub(r"[，。,\.;:：;、!！?？\"'()（）\[\]【】]+", "", s2)
    return s2


def get_close_matches_custom(query: str, candidates: List[str], n: int = 1, cutoff: float = 0.5) -> List[str]:
    """
    返回与 query 最相近的候选名列表（按相似度降序）。
    - 尝试使用 rapidfuzz（得分 0..100），回退到 difflib（得分 0..1）。
    - cutoff 在 0..1 之间表示接受阈值。
    """
    if not candidates:
        return []

    # 规范化 query 与候选（但保留原候选映射）
    qn = normalize_name(query)
    mapped = {}
    normed = []
    for c in candidates:
        if not c:
            continue
        nc = normalize_name(str(c))
        if not nc:
            continue
        # 如果有重复规范名，保留第一个出现的原始形式
        if nc not in mapped:
            mapped[nc] = c
            normed.append(nc)

    if not normed:
        return []

    # 使用 rapidfuzz 时，score 范围为 0..100
    if _HAS_RAPIDFUZZ:
        results = _rf_process.extract(qn, normed, scorer=_rf_fuzz.WRatio, limit=n)
        matches = []
        for name, score, _ in results:
            if (score / 100.0) >= cutoff:
                matches.append(mapped.get(name, name))
        return matches

    # 回退 difflib（cutoff 直接使用）
    from difflib import get_close_matches as _dl_get

    approx = _dl_get(qn, normed, n=n, cutoff=cutoff)
    return [mapped.get(x, x) for x in approx]


# ======================== 3. 星火 API 签名+调用函数（修复时区警告） ========================
def get_spark_signature(api_key: str, api_secret: str, url: str, method: str = "POST") -> dict:
    """生成星火 API HMAC 签名头（修复时区警告）"""
    parsed_url = urlparse(url)
    host = parsed_url.netloc
    path = parsed_url.path
    # 修复：使用 timezone-aware 的 UTC 时间
    now = datetime.now(timezone.utc)
    date = now.strftime("%a, %d %b %Y %H:%M:%S GMT")
    signature_origin = f"host: {host}\ndate: {date}\n{method} {path} HTTP/1.1"
    signature_sha = hmac.new(api_secret.encode('utf-8'), signature_origin.encode('utf-8'),
                             digestmod=hashlib.sha256).digest()
    signature_b64 = base64.b64encode(signature_sha).decode('utf-8')
    authorization = (
        f'api_key="{api_key}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature_b64}"'
    )
    return {
        "Host": host,
        "Date": date,
        "Authorization": authorization,
        "Content-Type": "application/json"
    }


def spark_chat_completions(messages: list, temperature: float = 0.0) -> str:
    """星火 LLM 核心调用函数"""
    url = "https://spark-api-open.xf-yun.com/v1/chat/completions"
    headers = get_spark_signature(SPARK_API_KEY, SPARK_API_SECRET, url)
    payload = {"model": SPARK_MODEL, "messages": messages, "temperature": temperature}
    try:
        response = requests.post(url=url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"].strip()
    except Exception as e:
        raise Exception(f"星火 API 调用失败：{str(e)}")


# ======================== 4. 实体提取兜底函数（优化实体解析） ========================
def fallback_extract_entities(user_query: str) -> Set[str]:
    """本地规则提取实体（星火API失败时兜底）"""
    entities = set()
    # 1. 匹配疾病/保险/业务实体
    for mention, standard in FALLBACK_ENTITY_RULES.items():
        if mention in user_query:
            entities.add(standard)
    # 2. 匹配年龄实体
    age_match = AGE_PATTERN.search(user_query)
    if age_match:
        entities.add(f"{age_match.group(1)}岁")
    # 3. 清洗无效实体（解决星火返回格式混乱问题）
    cleaned_entities = set()
    for ent in entities:
        # 过滤包含冒号/换行的无效实体（修复提取结果混乱）
        if ":" not in ent and "\n" not in ent:
            cleaned_entities.add(ent)
    return cleaned_entities


# ======================== 5. 初始化 FastAPI 应用（带生命周期） ========================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI 生命周期：启动时初始化 Neo4j 驱动并预热节点缓存，关闭时释放。"""
    try:
        init_neo4j_driver()
        print("✅ Neo4j 驱动已初始化")
        # 预热缓存（首次加载节点名）
        try:
            node_cache.get(refresh=True)
            print(f"✅ 节点缓存已预热，{len(node_cache.nodes)} 个节点")
        except Exception as e:
            print(f"⚠️ 预热节点缓存失败：{e}")
    except Exception as e:
        print(f"⚠️ 启动时初始化 Neo4j 驱动失败：{e}")

    yield

    try:
        close_neo4j_driver()
        print("✅ Neo4j 驱动已关闭")
    except Exception:
        pass


app = FastAPI(title="保险医疗 GraphRAG API", version="1.0", lifespan=lifespan)

# ======================== 6. 模拟知识图谱（原逻辑保留） ========================
STANDARD_NODES = [
    "原发性高血压", "2型糖尿病", "平安e生保护理险", "65岁", "慢性病",
    "住院医疗费用", "等待期", "百万医疗险"
]

GRAPH_TRIPLES = [
    ("原发性高血压", "被排除在承保范围之外", "平安e生保护理险"),
    ("平安e生保护理险", "最高投保年龄", "65岁"),
    ("原发性高血压", "分类为", "慢性病"),
    ("平安e生保护理险", "承保范围", "住院医疗费用"),
    ("平安e生保护理险", "等待期", "30天"),
    ("2型糖尿病", "被排除在承保范围之外", "平安e生保护理险")
]

CORE_RELATIONS = {"被排除在承保范围之外", "最高投保年龄", "分类为", "承保范围", "等待期"}


# ======================== 7. 核心业务函数（优化回答话术，贴合保险业务） ========================
def extract_entities(user_query: str) -> Set[str]:
    """实体提取：优先星火API，失败则自动兜底"""
    # 第一步：尝试调用星火API
    if not SPARK_API_FALLBACK:
        try:
            messages = [
                {"role": "system", "content": """你是保险医疗实体提取专家，仅提取以下类型实体：
                1. 保险名称（如：平安e生保护理险）；
                2. 疾病名称（如：原发性高血压、2型糖尿病）；
                3. 年龄（如：70岁）；
                4. 药品名称；
                5. 养老机构或医院名称；
                如果未发现以上实体则不用提取。输出格式为纯逗号分隔的字符串，无任何多余字符、冒号、换行或解释。"""},
                {"role": "user", "content": user_query}
            ]
            raw_result = spark_chat_completions(messages, temperature=0.0)
            raw_entities = raw_result.split(",")
            # 清洗星火返回的无效实体
            cleaned = {ent.strip() for ent in raw_entities if ent.strip() and ":" not in ent and "\n" not in ent}
            return cleaned
        except Exception as e:
            print(f"【实体提取 API 调用失败】：{str(e)}")
            print("【触发本地兜底】：使用规则提取实体")

    # 第二步：星火API失败/开启兜底时，调用本地规则
    return fallback_extract_entities(user_query)


def get_subgraph(entity_name: str, return_json: bool = True) -> List[Dict] | List[str]:
    """
    图谱查询接口（备份逻辑）：
    - 使用 `get_close_matches_custom` 在模块内 `STANDARD_NODES` 列表中做模糊匹配；
    - 若匹配到标准实体名，则在硬编码的 `GRAPH_TRIPLES` 中查找并返回相关三元组（当前为兜底数据）。
    说明：生产环境应将此函数替换为对 Neo4j 的精确/多跳查询。
    """
    # 优先使用 Neo4j（通过缓存匹配标准实体名并做精确查询），如不可用则回退到内存三元组
    json_triples = []
    text_facts = []

    # 尝试从 Neo4j 获取
    try:
        if driver:
            candidates = node_cache.get()
            matches = []
            if candidates:
                matches = get_close_matches_custom(entity_name, candidates, n=3, cutoff=0.55)

            # 如果命中候选，则用最优候选在 Neo4j 中做精确查询
            if matches:
                standard = matches[0]
                try:
                    with driver.session(database=NEO4J_DATABASE) as session:
                        query = """
                        MATCH (h)-[r]->(t)
                        WHERE h.name = $name OR t.name = $name
                        RETURN h.name as head, type(r) as relation, t.name as tail
                        LIMIT $limit
                        """
                        result = session.run(query, name=standard, limit=50)
                        for rec in result:
                            head = rec.get("head")
                            relation = rec.get("relation")
                            tail = rec.get("tail")
                            if head and relation and tail:
                                json_triples.append({"head": head, "relation": relation, "tail": tail})
                                text_facts.append(f"{head} 的 {relation} 是 {tail}")
                except Exception as ee:
                    print(f"⚠️ Neo4j 查询失败：{ee}")

            if json_triples:
                json_triples = [dict(t) for t in {tuple(d.items()) for d in json_triples}]
                text_facts = list(set(text_facts))
                return json_triples if return_json else text_facts
    except Exception as e:
        print(f"⚠️ 使用 Neo4j 检索时出错：{e}")

    # 回退：在内存三元组中查找（兜底）
    standard_entity_matches = get_close_matches_custom(entity_name, STANDARD_NODES, n=1, cutoff=0.5)
    if not standard_entity_matches:
        return []
    standard_entity = standard_entity_matches[0]

    for s, p, o in GRAPH_TRIPLES:
        if standard_entity in (s, o) and p in CORE_RELATIONS:
            json_triples.append({"head": s, "relation": p, "tail": o})
            text_facts.append(f"{s} 的 {p} 是 {o}")

    json_triples = [dict(t) for t in {tuple(d.items()) for d in json_triples}]
    text_facts = list(set(text_facts))
    return json_triples if return_json else text_facts


def generate_answer(user_query: str, facts: List[str]) -> str:
    """回答生成：优化话术，贴合保险业务，专业且友好"""
    context = "\n".join([f"- {f}" for f in facts]) if facts else "无"
    # 第一步：尝试星火API生成回答（优化Prompt，让回答更专业）
    if not SPARK_API_FALLBACK:
        prompt = f"""你是资深保险医养顾问，需基于以下事实背景，用专业、友好的话术回答用户问题，要求：
1. 结论清晰（如“可以购买”/“无法购买”）；
2. 原因详细且贴合保险业务逻辑；
3. 语言温和，符合保险顾问的沟通风格；
4. 仅使用提供的事实，不编造信息；
5. 无相关事实时，明确说明“暂未查询到相关投保信息”。

【事实背景】：
{context}

【用户问题】：{user_query}"""
        try:
            messages = [
                {"role": "system", "content": "资深保险医养顾问，严格遵守回答规则"},
                {"role": "user", "content": prompt}
            ]
            return spark_chat_completions(messages, temperature=0.1)
        except Exception as e:
            err_msg = f"【接口调用提示】：暂无法调用AI生成回答（{str(e)}）"
            print(err_msg)

    # 第二步：本地兜底生成专业回答（贴合保险业务）
    if not facts:
        return "您好，暂未查询到与您问题相关的投保信息，建议您咨询平安保险官方客服获取更精准的解答。"

    # 解析核心事实
    is_deny_disease = False  # 是否有排除疾病
    max_age = 65  # 最高投保年龄
    coverage = ""  # 承保范围
    waiting_period = ""  # 等待期

    for fact in facts:
        if "被排除在承保范围之外" in fact and "平安e生保护理险" in fact:
            is_deny_disease = True
        if "最高投保年龄" in fact:
            max_age = int(fact.split("是")[-1].strip("岁"))
        if "承保范围" in fact:
            coverage = fact.split("是")[-1].strip()
        if "等待期" in fact:
            waiting_period = fact.split("是")[-1].strip()

    # 提取用户年龄
    user_age = None
    age_match = AGE_PATTERN.search(user_query)
    if age_match:
        user_age = int(age_match.group(1))

    # 生成业务化回答
    answer_parts = ["您好！针对您的问题，为您解答如下："]

    # 场景1：询问能否投保（核心场景）
    if "能买" in user_query or "可以买" in user_query or "投保" in user_query:
        deny_reasons = []
        if is_deny_disease:
            deny_reasons.append(
                "您提及的疾病（原发性高血压/2型糖尿病）属于平安e生保护理险的承保排除范围，该保险不承保此类慢性病患者")
        if user_age and user_age > max_age:
            deny_reasons.append(f"您的年龄（{user_age}岁）已超过该保险的最高投保年龄（{max_age}岁），不符合投保年龄要求")

        if deny_reasons:
            answer_parts.append("❌ 很抱歉，您暂时无法购买平安e生保护理险，原因如下：")
            answer_parts.extend([f"- {reason}" for reason in deny_reasons])
            answer_parts.append("建议您咨询保险公司的其他医疗险产品，或联系平安保险客服了解适配的保障方案。")
        elif user_age and user_age <= max_age and not is_deny_disease:
            answer_parts.append("✅ 您符合平安e生保护理险的投保条件，可以购买该保险。")
            if coverage:
                answer_parts.append(f"- 该保险的核心承保范围：{coverage}")
            if waiting_period:
                answer_parts.append(f"- 该保险的等待期：{waiting_period}（等待期内出险不承担理赔责任）")
        else:
            answer_parts.append("ℹ️ 暂无法完全判断您的投保资格，需补充以下信息：")
            answer_parts.append("- 确认您是否患有原发性高血压/2型糖尿病等排除疾病；")
            answer_parts.append(f"- 确认您的年龄是否在{max_age}岁及以下。")

    # 场景2：询问承保范围
    elif "承保范围" in user_query or "保什么" in user_query:
        answer_parts.append(f"✅ 平安e生保护理险的核心承保范围为：{coverage}")
        answer_parts.append("⚠️ 注意：原发性高血压、2型糖尿病等慢性病患者不在承保范围内。")

    # 场景3：询问等待期
    elif "等待期" in user_query or "多久生效" in user_query:
        answer_parts.append(f"✅ 平安e生保护理险的等待期为：{waiting_period}")
        answer_parts.append(
            "📌 保险等待期说明：投保后需等待30天，等待期结束后出险才可申请理赔，等待期内出险保险公司不承担理赔责任。")

    # 场景4：询问年龄限制
    elif "年龄限制" in user_query or "多大能买" in user_query:
        answer_parts.append(f"✅ 平安e生保护理险的最高投保年龄为：{max_age}岁")
        answer_parts.append("📌 说明：仅65岁及以下的非排除疾病人群可投保该保险。")

    # 通用补充
    answer_parts.append("\n💡 温馨提示：以上解答基于现有图谱信息，最终投保资格以平安保险官方核保结果为准。")

    return "\n".join(answer_parts)


# ======================== 8. FastAPI 接口：/subgraph（原逻辑保留） ========================
class EntityRequest(BaseModel):
    """/subgraph 接口请求体"""
    entity_name: str


@app.post("/subgraph", response_model=List[Dict])
async def api_subgraph(request: EntityRequest):
    """POST /subgraph - 图谱三元组查询接口"""
    try:
        return get_subgraph(request.entity_name, return_json=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"接口调用失败：{str(e)}")


# ======================== 8.1 新增接口：/api/v1/chat ========================
class ChatRequest(BaseModel):
    """Chat 接口请求体"""
    question: str
    hop: int = 2
    limit: int = 20


@app.post("/api/v1/chat")
async def api_chat(request: ChatRequest):
    """POST /api/v1/chat - 完整 GraphRAG 问答接口"""
    try:
        # 1. 提取实体
        raw_entities = extract_entities(request.question)

        # 2. 查询图谱
        all_facts = []
        all_triples = []
        for entity in raw_entities:
            triples = get_subgraph(entity, return_json=True)
            facts = get_subgraph(entity, return_json=False)
            all_triples.extend(triples)
            all_facts.extend(facts)

        # 去重
        all_triples = [dict(t) for t in {tuple(d.items()) for d in all_triples}]
        all_facts = list(set(all_facts))

        # 3. 生成回答
        answer = generate_answer(request.question, all_facts)

        return {
            "answer": answer,
            "citations": all_triples,
            "confidence": "高" if all_triples else "低"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ======================== 9. 批量测试函数（20个全场景测试问题） ========================
def batch_test():
    """批量执行20个不同场景的测试问题"""
    # 20个测试问题（覆盖不同场景、不同提问方式）
    test_queries = [
        # 基础场景（核心投保问题）
        "买商业险，我有高血压，今年70岁，能、吗？",
        "我今年65岁，没有高血压，能投保平安e生保吗？",
        "50岁，有2型糖尿病，是否可以购买平安e生保护理险？",
        "80岁老人，身体健康，能买平安e生保护理险吗？",
        # 业务细节场景
        "平安e生保护理险的承保范围是什么？",
        "平安e生保保哪些内容？",
        "平安e生保护理险的等待期是多久？",
        "买了平安e生保后多久生效？",
        "平安e生保护理险的投保年龄限制是多少？",
        "多大年龄可以买平安e生保护理险？",
        # 口语化/模糊场景
        "我有高血压，想买e生保，行不行？",
        "糖尿病患者能买平安e生保吗？",
        "70岁买e生保会不会被拒保？",
        "平安e生保对慢性病有什么限制？",
        # 边缘场景
        "我今年60岁，身体健康，能买平安e生保护理险吗？",
        "平安e生保护理险的等待期内出险能理赔吗？",
        "没有慢性病，66岁能投保平安e生保吗？",
        "平安e生保除了高血压还排除哪些疾病？",
        "住院医疗费用包含在平安e生保的承保范围里吗？",
        "我既没有高血压也没有糖尿病，70岁能买平安e生保吗？"
    ]

    print("=" * 80)
    print("开始批量测试（20个场景）")
    print("=" * 80)

    for idx, query in enumerate(test_queries, 1):
        print(f"\n【测试问题 {idx}】：{query}")
        print("-" * 50)
        graph_rag_pipeline(query)

    print("=" * 80)
    print("20个场景测试完成")
    print("=" * 80)


# ======================== 10. GraphRAG 主工作流（原逻辑保留） ========================
def graph_rag_pipeline(user_query: str) -> str:
    """完整流程：提取实体 → 查图谱 → 生成回答"""
    # 步骤1：提取实体（含兜底）
    raw_entities = extract_entities(user_query)
    print(f"1. 提取有效实体：{raw_entities}")

    # 步骤2：查询图谱
    all_facts = []
    for entity in raw_entities:
        facts = get_subgraph(entity, return_json=False)
        all_facts.extend(facts)
    all_facts = list(set(all_facts))
    print(f"2. 检索图谱事实：\n{chr(10).join([f'- {f}' for f in all_facts]) if all_facts else '无'}")

    # 步骤3：生成回答（优化话术）
    final_answer = generate_answer(user_query, all_facts)
    print(f"3. 专业回答：\n{final_answer}")

    return final_answer


# ======================== 11. 测试/启动入口 ========================
if __name__ == "__main__":
    # 方式1：批量执行20个测试问题（推荐）
    # batch_test()

    # 方式2：单问题测试（注释方式1，打开方式2）
    # test_query = "我有高血压，今年70岁，能买平安e生保护理险吗？"
    # print("=== 单问题测试 ===")
    # graph_rag_pipeline(test_query)

    # 方式3：启动 FastAPI 服务（注释方式1/2，打开方式3）
    uvicorn.run(app, host=API_HOST, port=API_PORT)

# ======================== 1. 导入所有核心依赖 ========================
# -*- coding: utf-8 -*-
import os
from dotenv import load_dotenv  # 新增：用于加载 .env 文件
from difflib import get_close_matches
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Set
import uvicorn
import requests
from datetime import datetime
import re
from neo4j import GraphDatabase
import threading
from contextlib import asynccontextmanager

# neo4j配置
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "88888888")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

driver = None

def init_neo4j_driver():
    """初始化 Neo4j 驱动"""
    global driver
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        # 验证连接
        driver.verify_connectivity()
    except Exception as e:
        print(f"?? Neo4j 驱动初始化失败: {e}")
        driver = None


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
            print("?? NodeCache.refresh 失败：Neo4j 驱动未初始化。")
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
            print(f"?? NodeCache.refresh 失败：{e}")

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

# ======================== 2. 全局配置（从 mock/.env 文件读取） ========================
# 明确从 mock 文件夹下的 .env 加载配置
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

# SiliconFlow Qwen2.5 配置
QWEN_API_KEY = os.getenv("QWEN_API_KEY")

# 检查 Qwen API 配置
if not QWEN_API_KEY:
    print("*"*60)
    print("【警告】: SiliconFlow QWEN_API_KEY 未在 mock/.env 文件中配置。")
    print("【提示】: 请在 mock/.env 文件中添加：")
    print("QWEN_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxx")
    print("*"*60)

# 保持兼容性的占位变量
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


# ======================== 3. 星火 API 签名+调用函数 ========================
def spark_chat_completions(messages: list, temperature: float = 0.0) -> str:
    """已切换至 Qwen2.5 (SiliconFlow 免费版)"""
    api_key = os.getenv("QWEN_API_KEY")
    if not api_key:
        raise ValueError("请在 .env 中配置 QWEN_API_KEY")

    # SiliconFlow 的 API 地址
    url = "https://api.siliconflow.cn/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        # 使用 SiliconFlow 上的免费模型名
        "model": "Qwen/Qwen2.5-7B-Instruct",
        "messages": messages,
        "temperature": temperature,
        "max_tokens": 512
    }

    try:
        response = requests.post(url=url, headers=headers, json=payload, timeout=60)

        if response.status_code != 200:
            print(f"Qwen API 报错: {response.text}")
            response.raise_for_status()

        result = response.json()
        return result["choices"][0]["message"]["content"].strip()
    except Exception as e:
        raise Exception(f"Qwen 调用失败：{str(e)}")


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
    init_neo4j_driver()
    print("? Neo4j 驱动已初始化")
    # 预热缓存（首次加载节点名）
    if driver:
        try:
            node_cache.get(refresh=True)
            print(f"节点缓存已预热，{len(node_cache.nodes)} 个节点")
        except Exception as e:
            print(f"预热节点缓存失败：{e}")
    else:
        print("?? 未能预热节点缓存，因为 Neo4j 驱动初始化失败。")
        
    yield

    close_neo4j_driver()
    print("Neo4j 驱动已关闭")


app = FastAPI(title="保险医疗 GraphRAG API", version="1.0", lifespan=lifespan)

# CORS 配置：允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

# 简单关键词到节点标签的映射，用于精确查询
LABEL_KEYWORDS = {
    "机构": "Org",
    "养老": "Org",
    "医院": "Org",
    "险": "Product",
    "保险": "Product",
    "产品": "Product",
    "疾病": "Disease",
    "药": "Product",
}

# 意图关键词 -> 关系类型映射，用于精确检索
RELATION_KEYWORDS = {
    "岁": ["最高投保年龄", "投保规则"],
    "年龄": ["最高投保年龄", "投保规则"],  # 覆盖含“年龄”提问
    "等待期": ["等待期"],
    "承保范围": ["承保范围"],
    "保障范围": ["承保范围"],  # 同义映射
    "报销": ["医保政策", "医保报销"],
    "报销比例": ["医保报销"],
    "理赔": ["理赔条款", "赔付"],
    "赔付": ["理赔条款", "赔付"],
    "投保": ["投保规则", "理赔条款"],
    "除外": ["被排除在承保范围之外"],
    "免责": ["被排除在承保范围之外"],
    "上浮": ["费率表"],
    "领取": ["投保规则"],
    "结算": ["医保政策"],
    "支持": ["投保规则"],
    "区别": ["投保规则"],
}


# ======================== 7. 核心业务函数（优化回答话术，贴合保险业务） ========================
def extract_entities(user_query: str) -> Set[str]:
    """实体提取：优先星火API，失败则自动兜底，加入 Few-Shot 示例强制模型依葫芦画瓢"""
    if not SPARK_API_FALLBACK:
        try:
            # 引入 Few-Shot (小样本) 提示，这是对付小模型不听话最有效的手段
            messages = [
                {"role": "system", "content": """你是一个冷酷的保险词汇提取器。你的唯一任务是从用户输入中提取核心词汇，不要回答问题！不要解释！
提取类别包括：保险产品、疾病症状、年龄、医疗方式、保险术语、养老机构、地域。

【示例 1】
输入：60岁有高血压病史能买百万医疗险吗？
输出：60岁,高血压病,百万医疗险

【示例 2】
输入：如果因车祸导致骨折入院，意外险和医疗险的理赔款是互斥的还是叠加的？
输出：车祸,骨折,意外险,医疗险,理赔款,互斥,叠加

【示例 3】
输入：对比泰康康惠保防癌险和国寿防癌疾病保险，70岁老人选哪个？
输出：泰康康惠保防癌险,国寿防癌疾病保险,70岁,老人

请严格按照上面的【输出】格式返回，用英文逗号分隔，不要带有任何多余的汉字。"""},
                {"role": "user", "content": f"输入：{user_query}\n输出："}
            ]
            raw_result = spark_chat_completions(messages, temperature=0.0).strip()
            
            # 【优化防御机制】：去除模型习惯性加在末尾的句号/感叹号
            raw_result = raw_result.strip("。！. ")
            
            # 拦截判断：如果长度过长，或者包含明显的回答型词汇，判定为提取失败
            if raw_result == "无" or len(raw_result) > 100 or "因为" in raw_result or "也就是说" in raw_result:
                print(f"   [警告]: 模型未遵循指令(长文本)。截断显示: {raw_result[:30]}...")
                return fallback_extract_entities(user_query)
            
            # 兼容中文逗号，进行切分
            raw_result = raw_result.replace("，", ",") 
            raw_entities = raw_result.split(",")
            
            # 清洗无效实体：去掉带有“输入”、“输出”等格式残留的错误词汇
            cleaned = set()
            for ent in raw_entities:
                ent = ent.strip()
                if ent and ":" not in ent and "输入" not in ent and "输出" not in ent:
                    cleaned.add(ent)
            
            if not cleaned:
                return fallback_extract_entities(user_query)
                
            return cleaned
        except Exception as e:
            print(f"【实体提取 API 调用失败】：{str(e)}")
            print("【触发本地兜底】：使用规则提取实体")

    # 星火API失败/开启兜底/触发防御 时，调用本地规则
    return fallback_extract_entities(user_query)



# ---------------------------- helper utilities ----------------------------

def guess_label(entity: str) -> str | None:
    """根据实体名简单猜测其最可能的节点标签（Org/Product/Disease）。"""
    if not entity:
        return None
    for kw, lab in LABEL_KEYWORDS.items():
        if kw in entity:
            return lab
    return None


def extract_relations_from_query(query: str | None) -> List[str]:
    """根据用户问句关键词筛选出相关关系类型。
    如果没有匹配到，就返回 CORE_RELATIONS 的列表。
    """
    if not query:
        return list(CORE_RELATIONS)
    rels = set()
    for kw, types in RELATION_KEYWORDS.items():
        if kw in query:
            rels.update(types)
    return list(rels) if rels else list(CORE_RELATIONS)


# ======================== 7. 核心业务函数（优化回答话术，贴合保险业务） ========================

def get_subgraph(entity_name: str, query: str | None = None, return_json: bool = True) -> List[Dict] | List[str]:
    """图谱查询接口，优先Neo4j，失败则回退到内存数据。

    添加了：
    * 可以传入用户问题 (query) 以便意图检测
    * 借助 guess_label() 精确过滤节点标签
    * 调用 extract_relations_from_query() 限制返回关系类型
    """
    json_triples = []
    text_facts = []

    # 1. 准备过滤条件
    label_hint = guess_label(entity_name)
    allowed_rels = extract_relations_from_query(query)

    # 优先使用 Neo4j
    if driver:
        try:
            candidates = node_cache.get()
            matches = []
            if candidates:
                matches = get_close_matches_custom(entity_name, candidates, n=3, cutoff=0.55)

            if matches:
                standard = matches[0]
                with driver.session(database=NEO4J_DATABASE) as session:
                    if label_hint:
                        cypher = f"""
                        MATCH (h:{label_hint})-[r]->(t)
                        WHERE (h.name = $name OR t.name = $name)
                          AND type(r) IN $rels
                        RETURN h.name as head, type(r) as relation, t.name as tail
                        LIMIT $limit
                        """
                    else:
                        cypher = """
                        MATCH (h)-[r]->(t)
                        WHERE (h.name = $name OR t.name = $name)
                          AND type(r) IN $rels
                        RETURN h.name as head, type(r) as relation, t.name as tail
                        LIMIT $limit
                        """

                    result = session.run(cypher, name=standard, rels=allowed_rels, limit=50)
                    for rec in result:
                        head, relation, tail = rec.get("head"), rec.get("relation"), rec.get("tail")
                        if all([head, relation, tail]):
                            json_triples.append({"head": head, "relation": relation, "tail": tail})
                            text_facts.append(f"{head} 的 {relation} 是 {tail}")

            if json_triples:
                # 去重后返回
                unique_triples = [dict(t) for t in {tuple(d.items()) for d in json_triples}]
                unique_facts = list(set(text_facts))
                return unique_triples if return_json else unique_facts
        except Exception as e:
            print(f"?? 使用 Neo4j 检索时出错：{e}")

    # 回退到内存三元组（同样运用 allowed_rels 过滤）
    standard_entity_matches = get_close_matches_custom(entity_name, STANDARD_NODES, n=1, cutoff=0.5)
    if not standard_entity_matches:
        return []
    standard_entity = standard_entity_matches[0]

    # 对 allowed_rels 做规范化以便比较
    norm_allowed = {normalize_name(r) for r in allowed_rels}
    for s, p, o in GRAPH_TRIPLES:
        # 1. 实体匹配
        if standard_entity in (s, o):
            # 2. 关系类型过滤（比较规范化后的值）
            if normalize_name(p) in norm_allowed:
                json_triples.append({"head": s, "relation": p, "tail": o})
                text_facts.append(f"{s} 对 {o} 有关系 {p}")

    json_triples = [dict(t) for t in {tuple(d.items()) for d in json_triples}]
    text_facts = list(set(text_facts))
    return json_triples if return_json else text_facts


def generate_answer(user_query: str, facts: List[str]) -> str:
    """回答生成：优化话术，贴合保险业务，专业且友好"""
    context = "\n".join([f"- {f}" for f in facts]) if facts else "无"
    # 第一步：尝试星火API生成回答
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

    # 第二步：本地兜底生成专业回答
    if not facts:
        return "您好，暂未查询到与您问题相关的投保信息，建议您咨询保险官方客服获取更精准的解答。"

    # 解析核心事实
    is_deny_disease = False
    max_age = 65
    coverage, waiting_period = "", ""

    for fact in facts:
        if "被排除在承保范围之外" in fact:
            is_deny_disease = True
        if "最高投保年龄" in fact:
            age_str = fact.split("是")[-1].strip("岁").strip()
            if age_str.isdigit(): max_age = int(age_str)
        if "承保范围" in fact:
            coverage = fact.split("是")[-1].strip()
        if "等待期" in fact:
            waiting_period = fact.split("是")[-1].strip()

    user_age = None
    age_match = AGE_PATTERN.search(user_query)
    if age_match: user_age = int(age_match.group(1))

    # 生成业务化回答
    answer_parts = ["您好！针对您的问题，为您解答如下："]
    
    deny_reasons = []
    if "能买" in user_query or "可以买" in user_query or "投保" in user_query:
        if is_deny_disease:
            deny_reasons.append("您提及的疾病（如高血压/糖尿病）可能属于该产品的承保排除范围。")
        if user_age and user_age > max_age:
            deny_reasons.append(f"您的年龄（{user_age}岁）已超过最高投保年龄（{max_age}岁）。")

        if deny_reasons:
            answer_parts.append("? 很抱歉，根据现有信息，您可能无法购买该保险，原因如下：")
            answer_parts.extend([f"- {reason}" for reason in deny_reasons])
        else:
            answer_parts.append("? 根据现有信息，您可能符合该产品的投保条件。")
            if coverage: answer_parts.append(f"- 保险的核心承保范围为“{coverage}”。")
            if waiting_period: answer_parts.append(f"- 等待期为“{waiting_period}”，期内出险不予理赔。")
    else:
        # 其他类型问题的回答
        if facts:
            answer_parts.append("根据查询到的信息：")
            answer_parts.extend([f"- {fact}" for fact in facts])
        else:
            return "您好，暂未查询到与您问题相关的信息。"

    answer_parts.append("\n? 温馨提示：以上解答基于现有图谱信息，最终投保资格以保险公司官方核保结果为准。")
    return "\n".join(answer_parts)

# ======================== 8. FastAPI 接口 ========================
class EntityRequest(BaseModel):
    entity_name: str

@app.post("/subgraph", response_model=List[Dict])
async def api_subgraph(request: EntityRequest):
    try:
        # 这个简单查询不考虑用户问句，因此 query=None
        return get_subgraph(request.entity_name, query=None, return_json=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"接口调用失败：{str(e)}")

class ChatRequest(BaseModel):
    question: str
    hop: int = 2
    limit: int = 20

# ======================== 替换原有的 api_chat 函数 ========================
@app.post("/api/v1/chat")
async def api_chat(request: ChatRequest):
    print(f"\n{'='*20} 收到前端请求 {'='*20}")
    print(f"用户问题: {request.question}")

    try:
        # 1. 提取实体
        print(">>> 正在提取实体...")
        raw_entities = extract_entities(request.question)
        print(f"   [提取结果]: {raw_entities}")

        if not raw_entities:
            print("   [警告]: 未提取到任何实体，后续检索将为空！")

        # 2. 检索图谱
        print(">>> 正在检索图谱...")
        all_facts, all_triples = [], []
        for entity in raw_entities:
            print(f"   -> 正在检索实体: {entity}")
            triples = get_subgraph(entity, query=request.question, return_json=True)
            facts = get_subgraph(entity, query=request.question, return_json=False)

            if not triples:
                print(f"      (实体 '{entity}' 未在图谱/本地数据中匹配到任何三元组)")
            else:
                print(f"      (命中 {len(triples)} 条相关信息)")

            all_triples.extend(triples)
            all_facts.extend(facts)

        # 去重
        all_triples = [dict(t) for t in {tuple(d.items()) for d in all_triples}]
        all_facts = list(set(all_facts))
        print(f"   [最终检索到的事实数量]: {len(all_facts)}")

        # 3. 生成回答
        print(">>> 正在生成回答...")
        answer = generate_answer(request.question, all_facts)
        print("   [回答生成完毕]")
        print(f"{'='*20} 请求处理结束 {'='*20}\n")

        return {"answer": answer, "citations": all_triples, "confidence": "高" if all_triples else "低"}
    except Exception as e:
        import traceback
        traceback.print_exc() # 打印详细报错堆栈
        raise HTTPException(status_code=500, detail=str(e))

# ======================== 9. 批量测试函数 ========================
def batch_test():
    """批量执行多个不同场景的测试问题"""
    test_queries = [
        "我有高血压，今年70岁，能买平安e生保护理险吗？",
        "50岁，有2型糖尿病，是否可以购买平安e生保护理险？",
        "平安e生保护理险的承保范围是什么？",
        "平安e生保护理险的等待期是多久？",
        "80岁老人，身体健康，能买平安e生保护理险吗？",
    ]
    print("="*80 + "\n开始批量测试\n" + "="*80)
    for idx, query in enumerate(test_queries, 1):
        print(f"\n【测试问题 {idx}】：{query}\n" + "-"*50)
        graph_rag_pipeline(query)
    print("="*80 + "\n批量测试完成\n" + "="*80)

# ======================== 10. GraphRAG 主工作流 ========================
def graph_rag_pipeline(user_query: str) -> str:
    """完整流程：提取实体 → 查图谱 → 生成回答"""
    print(f"1. 提取有效实体...")
    raw_entities = extract_entities(user_query)
    print(f"   ? 提取结果: {raw_entities}")

    print(f"2. 检索图谱事实...")
    all_facts = []
    for entity in raw_entities:
        facts = get_subgraph(entity, query=user_query, return_json=False)
        all_facts.extend(facts)
    all_facts = list(set(all_facts))
    print(f"   ? 检索结果:\n{chr(10).join([f'- {f}' for f in all_facts]) if all_facts else '无'}")

    print(f"3. 生成专业回答...")
    final_answer = generate_answer(user_query, all_facts)
    print(f"   ? 最终回答:\n{final_answer}")
    return final_answer

# ======================== 11. 测试/启动入口 ========================
if __name__ == "__main__":
    # 启动 FastAPI 服务
    uvicorn.run(app, host=API_HOST, port=API_PORT)

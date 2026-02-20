# ======================== 1. 导入所有核心依赖（含星火签名所需） ========================
from difflib import get_close_matches
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Set
import uvicorn
import time
import hashlib
import hmac
import base64
import requests
from datetime import datetime
from urllib.parse import urlparse

# ======================== 2. 全局配置（仅需替换此处的 APIKey/APISecret） ========================
# 讯飞星火 LLM 配置（解决 401 签名错误的核心）
SPARK_API_KEY = "APIkey"  # 替换为控制台的 APIKey
SPARK_API_SECRET = "APISecret"  # 替换为控制台的 APISecret
SPARK_MODEL = "lite"  # 星火轻量版（免费够用）

# FastAPI 服务配置
API_HOST = "0.0.0.0"
API_PORT = 8000


# ======================== 3. 星火 API 签名核心函数（解决 401 错误） ========================
def get_spark_signature(api_key: str, api_secret: str, url: str, method: str = "POST") -> dict:
    """生成星火 API 要求的 HMAC 签名头，解决签名验证失败问题"""
    parsed_url = urlparse(url)
    host = parsed_url.netloc
    path = parsed_url.path

    # 生成 UTC 时间戳（星火要求）
    now = datetime.utcnow()
    date = now.strftime("%a, %d %b %Y %H:%M:%S GMT")

    # 构造待签名字符串
    signature_origin = f"host: {host}\ndate: {date}\n{method} {path} HTTP/1.1"

    # HMAC-SHA256 签名
    signature_sha = hmac.new(
        api_secret.encode('utf-8'),
        signature_origin.encode('utf-8'),
        digestmod=hashlib.sha256
    ).digest()
    signature_b64 = base64.b64encode(signature_sha).decode('utf-8')

    # 构造 Authorization 头
    authorization = (
        f'api_key="{api_key}", '
        f'algorithm="hmac-sha256", '
        f'headers="host date request-line", '
        f'signature="{signature_b64}"'
    )

    return {
        "Host": host,
        "Date": date,
        "Authorization": authorization,
        "Content-Type": "application/json"
    }


def spark_chat_completions(messages: list, temperature: float = 0.0) -> str:
    """
    星火 LLM 调用核心函数（替代原 openai 库）
    :param messages: 对话消息列表（格式和 OpenAI 一致）
    :param temperature: 随机性（0=最严谨，1=最灵活）
    :return: LLM 回答内容
    """
    # 星火 OpenAI 兼容接口地址
    url = "https://spark-api-open.xf-yun.com/v1/chat/completions"

    # 获取签名请求头
    headers = get_spark_signature(SPARK_API_KEY, SPARK_API_SECRET, url)

    # 构造请求体（和 OpenAI 格式完全兼容）
    payload = {
        "model": SPARK_MODEL,
        "messages": messages,
        "temperature": temperature
    }

    # 发送请求并处理响应
    try:
        response = requests.post(
            url=url,
            headers=headers,
            json=payload,
            timeout=30  # 超时保护
        )
        response.raise_for_status()  # 抛出 HTTP 错误（如 401/500）
        result = response.json()
        return result["choices"][0]["message"]["content"].strip()
    except Exception as e:
        raise Exception(f"星火 API 调用失败：{str(e)}")


# ======================== 4. 初始化 FastAPI 应用 ========================
app = FastAPI(title="保险医疗 GraphRAG API", version="1.0")

# ======================== 5. 模拟知识图谱（预留真实图谱替换接口） ========================
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

CORE_RELATIONS = {"被排除在承保范围之外", "最高投保年龄", "分类为", "承保范围"}


# ======================== 6. 核心业务函数（适配星火签名版调用） ========================
def extract_entities(user_query: str) -> Set[str]:
    """星火 LLM 提取用户问题中的实体（解决 401 错误）"""
    try:
        # 构造实体提取的提示词
        messages = [
            {
                "role": "system",
                "content": """你是实体提取专家，仅提取「保险名称、疾病名称、年龄」相关实体，
                输出格式为逗号分隔的字符串，禁止添加任何解释和多余内容。"""
            },
            {"role": "user", "content": user_query}
        ]
        # 调用星火 API（带签名）
        raw_result = spark_chat_completions(messages, temperature=0.0)
        # 解析并去重
        raw_entities = raw_result.split(",")
        return {entity.strip() for entity in raw_entities if entity.strip()}
    except Exception as e:
        print(f"【实体提取 API 调用失败】：{str(e)}")
        return set()


def get_subgraph(entity_name: str, return_json: bool = True) -> List[Dict] | List[str]:
    """图谱查询接口（本地模拟，后期可替换为 Neo4j）"""
    # 实体对齐
    standard_entity = get_close_matches(entity_name, STANDARD_NODES, n=1, cutoff=0.5)
    if not standard_entity:
        return []
    standard_entity = standard_entity[0]

    # 检索核心三元组
    json_triples = []
    text_facts = []
    for s, p, o in GRAPH_TRIPLES:
        if standard_entity in (s, o) and p in CORE_RELATIONS:
            json_triples.append({"head": s, "relation": p, "tail": o})
            text_facts.append(f"{s} 的 {p} 是 {o}")

    # 去重返回
    json_triples = [dict(t) for t in {tuple(d.items()) for d in json_triples}]
    text_facts = list(set(text_facts))
    return json_triples if return_json else text_facts


def generate_answer(user_query: str, facts: List[str]) -> str:
    """星火 LLM 根据图谱事实生成回答（解决 401 错误）"""
    # 构造回答提示词
    context = "\n".join([f"- {f}" for f in facts]) if facts else "无"
    prompt = f"""已知事实背景：
{context}

请严格按照以下规则回答用户问题「{user_query}」：
1. 仅使用上述事实回答，禁止编造任何信息；
2. 有明确结论时直接给出（如“不能购买”），禁止模糊表述；
3. 无相关事实时，明确说明“未查询到相关信息”。"""

    try:
        messages = [
            {"role": "system", "content": "你是严谨的保险医养专家，严格遵守回答规则。"},
            {"role": "user", "content": prompt}
        ]
        # 调用星火 API 生成回答
        return spark_chat_completions(messages, temperature=0.1)
    except Exception as e:
        return f"【回答生成 API 调用失败】：{str(e)}"


# ======================== 7. FastAPI 接口：/subgraph ========================
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


# ======================== 8. GraphRAG 主工作流 ========================
def graph_rag_pipeline(user_query: str) -> str:
    """完整流程：提取实体 → 查图谱 → 生成回答"""
    print(f"\n=== 开始处理用户问题 ===")
    print(f"用户问题：{user_query}")

    # 步骤1：提取实体
    raw_entities = extract_entities(user_query)
    print(f"1. 提取原始实体：{raw_entities}")

    # 步骤2：查询图谱
    all_facts = []
    for entity in raw_entities:
        facts = get_subgraph(entity, return_json=False)
        all_facts.extend(facts)
    all_facts = list(set(all_facts))
    print(f"2. 图谱检索事实：\n{chr(10).join([f'- {f}' for f in all_facts]) if all_facts else '无'}")

    # 步骤3：生成回答
    final_answer = generate_answer(user_query, all_facts)
    print(f"3. 最终回答：\n{final_answer}")
    print(f"=== 处理结束 ===\n")

    return final_answer


# ======================== 9. 测试/启动入口 ========================
if __name__ == "__main__":
    # test_query = "我有高血压，今年70岁，能买平安e生保护理险吗？"
    # graph_rag_pipeline(test_query)

     #方式2：启动 FastAPI 服务（注释方式1，打开方式2）
     uvicorn.run(app, host=API_HOST, port=API_PORT)
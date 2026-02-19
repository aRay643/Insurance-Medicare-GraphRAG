from difflib import get_close_matches
from openai import OpenAI

# 1. 初始化客户端
client = OpenAI(
    api_key="API_KEY", 
    base_url="https://spark-api-open.xf-yun.com/v1"
)

# 2. 节点定义 (用于实体链接)
MOCK_NODES = [
    "高血压", "糖尿病", "心脏病", "癌症", "阿尔兹海默症", "骨折",
    "护理险", "意外险", "医疗险", "补充医疗险",
    "等待期", "除外责任", "免责条款", "费率表", "失能等级", "医保报销", "异地结算",
    "降压药", "手术", "化疗", "康复",
    "城市医养结合机构", "城市养老机构", "社区卫生中心",
    "居家养老", "机构养老", "上门护理服务",
    "68岁", "70岁"
]

# 3. 对应扩展的模拟图谱数据 (增加关系以支撑复杂查询)
# 结构: (Subject, Relation, Object, Relation_Type)
MOCK_GRAPH = [
    # 保险与疾病关系
    ("高血压", "在健康告知中被要求如实告知", "护理险", "投保规则"),
    ("高血压", "通常作为除外责任", "医疗险", "理赔条款"),
    ("癌症", "等待期通常为", "90天", "投保规则"),
    
    # 产品限制
    ("护理险", "最高投保年龄", "65岁", "投保规则"),
    ("意外险", "支持投保年龄可达", "80岁", "投保规则"),
    
    # 医养结合逻辑
    ("社区卫生中心", "提供", "上门护理服务", "养老服务"),
    ("阿尔兹海默症", "适合入住", "城市医养结合机构", "养老匹配"),
    ("城市养老机构", "支持", "异地结算", "医保政策"),
    
    # 医疗逻辑
    ("高血压", "需要长期服用", "降压药", "医学常识"),
    ("骨折", "术后需要", "康复", "医学常识")
]

# 4. 逻辑函数
def link_entity(user_mention):
    """使用 get_close_matches 在你定义的 MOCK_NODES 中寻找最接近的实体"""
    match = get_close_matches(user_mention, MOCK_NODES, n=1, cutoff=0.5)
    return match[0] if match else None

def get_subgraph_optimized(entity_names, query):
    """
    关系过滤逻辑：
    根据问题中的关键词（如 '年龄', '机构', '报销'）动态筛选关系类型
    """
    intent_map = {
        "岁": ["投保规则"],
        "年": ["投保规则"],
        "能买": ["投保规则", "理赔条款"],
        "住": ["养老匹配", "养老服务"],
        "钱": ["费率表", "医保报销"],
        "报销": ["医保政策", "医保报销"]
    }
    
    active_types = []
    for key, r_types in intent_map.items():
        if key in query:
            active_types.extend(r_types)
    
    # 如果没匹配到意图，默认展示基础投保逻辑
    if not active_types:
        active_types = ["投保规则", "理赔条款", "养老匹配"]

    facts = []
    for name in entity_names:
        sub = [
            f"{s} 的 {p} 是 {o}" 
            for s, p, o, r_type in MOCK_GRAPH 
            if (name == s or name == o) and r_type in active_types
        ]
        facts.extend(sub)
    return list(set(facts))

def ask_spark(prompt):
    """调用星火 Lite"""
    try:
        completion = client.chat.completions.create(
            model="lite",
            messages=[
                {"role": "system", "content": "你是一位资深的保险医养专家。请根据事实进行严谨的逻辑推导.未出现的事实回答不知道，禁止编造。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"接口调用失败: {str(e)}"

# 5. 增强版主工作流
def graph_rag_run(query):
    print(f"--- 跨域检索测试 ---")
    print(f"问: {query}")
    
    # 模拟简单的实体提取逻辑（实际可用 NLP 工具提取更多）
    # 这里我们遍历 MOCK_NODES，看看问题里提到了哪些
    found_mentions = [node for node in MOCK_NODES if node in query]
    
    # 实体对齐
    standard_entities = [link_entity(m) for m in found_mentions]
    print(f"匹配实体: {standard_entities}")
    
    # 检索
    facts = get_subgraph_optimized(standard_entities, query)
    context = "\n".join([f"- {f}" for f in facts])
    print(f"检索事实:\n{context if context else '无相关事实'}")
    
    # 生成
    final_prompt = f"【事实背景】\n{context}\n\n【问题】\n{query}\n\n请结合事实背景给出专业建议："
    answer = ask_spark(final_prompt)
    
    print(f"\nAI 回答:\n{answer}\n")

if __name__ == "__main__":
    # 测试 1：保险与年龄限制
    graph_rag_run("我有高血压，70岁了，还能买护理险吗？")
    
    # 测试 2：养老机构与政策
    graph_rag_run("阿尔兹海默症老人适合住哪类机构？能异地结算吗？")
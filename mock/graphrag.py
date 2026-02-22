import os
from difflib import get_close_matches
from openai import OpenAI

api_key = os.getenv("OPENAI_API_KEY", "API_KEY")
base_url = os.getenv("OPENAI_BASE_URL", "https://spark-api-open.xf-yun.com/v1")

client = OpenAI(
    api_key=api_key,
    base_url=base_url
)

# 2. 模拟图谱数据
MOCK_NODES = ["原发性高血压", "2型糖尿病", "平安e生保护理险", "投保年龄限制"]
MOCK_GRAPH = [
    ("原发性高血压", "被排除在承保范围之外", "平安e生保护理险"),
    ("平安e生保护理险", "最高投保年龄", "65岁"),
    ("原发性高血压", "分类为", "慢性病")
]

# 3. 逻辑函数封装
def link_entity(user_mention):
    """实体对齐：将用户口语词映射到标准节点名"""
    match = get_close_matches(user_mention, MOCK_NODES, n=1, cutoff=0.5)
    return match[0] if match else None

#需要增加关系过滤防止prompt爆炸
def get_subgraph(entity_names):
    """知识检索：获取相关实体的 1-hop 三元组"""
    facts = []
    for name in entity_names:
        sub = [f"{s} 的 {p} 是 {o}" for s, p, o in MOCK_GRAPH if name in (s, o)]
        facts.extend(sub)
    return list(set(facts)) # 去重

def ask_spark(prompt):
    """调用星火 Lite 生成答案"""
    try:
        completion = client.chat.completions.create(
            model="lite",
            messages=[
                {"role": "system", "content": "你是一个严谨的保险医养专家。只能根据提供的事实回答，禁止胡编乱造。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1 # 降低随机性，保证严谨
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"接口调用失败: {str(e)}"
    
# 4. GraphRAG 主工作流
def graph_rag_test(query):
    print(f"--- 测试开始 ---")
    print(f"用户问题: {query}")
    
    # A. 提取实体并对齐 (实际工程中这步也可用 LLM 做)
    mentions = ["高血压", "平安e生保"] 
    standard_entities = [link_entity(m) for m in mentions if link_entity(m)]
    print(f"识别实体: {standard_entities}")
    
    # B. 从图谱获取背景知识
    facts = get_subgraph(standard_entities)
    context = "\n".join([f"- {f}" for f in facts])
    print(f"检索事实:\n{context if context else '未找到相关事实'}")
    
    # C. 构造 Prompt 并生成回答
    final_prompt = f"已知事实背景：\n{context}\n\n请回答：{query}"
    answer = ask_spark(final_prompt)
    
    print(f"\nAI 回答:\n{answer}")
    print(f"--- 测试结束 ---\n")

# 5. 执行一次完整的逻辑测试
if __name__ == "__main__":
    # 场景：测试保险年龄限制和疾病禁忌
    test_query = "我有高血压，今年70岁，能买平安e生保护理险吗？"
    graph_rag_test(test_query)

'''#--- 测试开始 ---
用户问题: 我有高血压，今年70岁，能买平安e生保护理险吗？
识别实体: ['原发性高血压', '平安e生保护理险']
检索事实:
- 原发性高血压 的 被排除在承保范围之外 是 平安e生保护理险
- 平安e生保护理险 的 最高投保年龄 是 65岁
- 原发性高血压 的 分类为 是 慢性病

AI 回答:
根据提供的事实背景，原发性高血压被排除在承保范围之外。这意味着如果你有高血压，那么你可能无法购买平安e生保护理险。然而，你提到今年70岁，这可能意味着你已经超过了最高投保年龄。因此，我无法确定你是否能够购买平安e生保护理险，除非提供更多关于你的年龄和健康状况的信息。
--- 测试结束 ---'''
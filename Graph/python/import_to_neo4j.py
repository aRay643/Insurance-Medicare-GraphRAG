"""
JSON 三元组数据导入 Neo4j 数据库脚本
===================================
将 medicine、Insurance、NursingHome 三个目录下的 JSON 三元组数据
导入到 Neo4j 图数据库中，实现跨域自然关联和数据去重。
"""

import json
import os
import re
from collections import defaultdict
from neo4j import GraphDatabase
from tqdm import tqdm

# ============================================================
# Neo4j 连接配置
# ============================================================
NEO4J_URI = "bolt://127.0.0.1:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "88888888"
NEO4J_DATABASE = "neo4j"  # Community Edition 仅支持默认数据库

# ============================================================
# 数据目录配置
# ============================================================
# ============================================================
# 数据目录配置
# ============================================================
BASE_DIR = r"d:\Edge_Download\Data"
DATA_SOURCES = {
    "medicine": os.path.join(BASE_DIR, "medicine"),
    "insurance": os.path.join(BASE_DIR, "Insurance"),
    "nursing_home": os.path.join(BASE_DIR, "NursingHome"),
}
SEED_DIR = os.path.join(BASE_DIR, "Seeds")

# 批量提交大小
BATCH_SIZE = 500


def normalize_text(text):
    """
    标准化文本：去除多余空白、换行符等，用于去重比较。
    """
    if not isinstance(text, str):
        return text
    # 去除 \n \r 并压缩空格
    text = re.sub(r'[\r\n]+', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def normalize_name(name):
    """
    标准化实体名称用于去重：去除换行、多余空格。
    """
    if not isinstance(name, str):
        return str(name)
    name = re.sub(r'[\r\n]+', '', name)
    name = re.sub(r'\s+', '', name)
    return name.strip()


def clean_properties(props):
    """
    清理属性值，确保所有值都是 Neo4j 兼容的基本类型。
    - 嵌套字典会被扁平化（键名用下划线连接）
    - 列表中的非基本类型转为 JSON 字符串
    - 无法处理的类型转为 JSON 字符串
    """
    cleaned = {}

    def flatten(d, prefix=''):
        for k, v in d.items():
            key = f"{prefix}{k}" if not prefix else f"{prefix}_{k}"
            if isinstance(v, dict):
                flatten(v, key)
            elif isinstance(v, list):
                # Neo4j 支持基本类型的数组
                if all(isinstance(item, (str, int, float, bool)) for item in v):
                    cleaned[key] = v
                elif all(isinstance(item, str) for item in v):
                    cleaned[key] = v
                else:
                    # 包含复杂类型的列表，转为 JSON 字符串
                    cleaned[key] = json.dumps(v, ensure_ascii=False)
            elif isinstance(v, str):
                cleaned[key] = normalize_text(v)
            elif isinstance(v, (int, float, bool)):
                cleaned[key] = v
            elif v is None:
                pass  # 跳过 None
            else:
                cleaned[key] = str(v)

    flatten(props)
    return cleaned


def load_json_files(directory):
    """
    加载目录下所有 JSON 文件，返回三元组列表。
    """
    triplets = []
    if not os.path.exists(directory):
        return triplets
        
    json_files = sorted([f for f in os.listdir(directory) if f.endswith('.json')])

    for filename in json_files:
        filepath = os.path.join(directory, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, list):
                for item in data:
                    item['_source_file'] = filename
                    triplets.append(item)
            elif isinstance(data, dict):
                data['_source_file'] = filename
                triplets.append(data)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            print(f"  ⚠ 跳过文件 {filename}: {e}")

    return triplets


def load_seeds():
    """
    加载种子数据
    """
    seeds = []
    if not os.path.exists(SEED_DIR):
        return seeds
        
    json_files = sorted([f for f in os.listdir(SEED_DIR) if f.endswith('.json')])
    for filename in json_files:
        filepath = os.path.join(SEED_DIR, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, list):
                seeds.extend(data)
        except Exception as e:
            print(f"  ⚠ 跳过种子文件 {filename}: {e}")
    return seeds


def deduplicate_triplets(triplets):
    """
    对三元组进行去重：
    基于 (normalized_subject, subject_type, predicate, normalized_object, object_type) 去重。
    如果有重复，保留属性最丰富的那条。
    """
    seen = {}
    for t in triplets:
        subj = normalize_name(t.get('subject', ''))
        obj = normalize_name(t.get('object', ''))
        key = (
            subj,
            t.get('subject_type', ''),
            t.get('predicate', ''),
            obj,
            t.get('object_type', ''),
        )
        if key in seen:
            # 保留属性更多的那条
            existing_props = seen[key].get('properties', {})
            new_props = t.get('properties', {})
            if len(new_props) > len(existing_props):
                seen[key] = t
        else:
            seen[key] = t

    return list(seen.values())


def create_constraints_and_indexes(session):
    """
    为所有节点标签创建唯一性约束或索引。
    使用 name + label 组合进行去重。
    """
    labels = [
        "Product", "Medical", "Brand", "Company", "Insurance",
        "Benefit", "Condition", "Exclusion", "Eligibility",
        "Org", "District", "Province",
        "ProductCategory", "Service"  # V6 新增标签
    ]

    for label in labels:
        try:
            # 尝试创建索引（兼容不同 Neo4j 版本）
            session.run(
                f"CREATE INDEX idx_{label.lower()}_name IF NOT EXISTS "
                f"FOR (n:{label}) ON (n.name)"
            )
            print(f"  ✓ 索引 idx_{label.lower()}_name 已创建/已存在")
        except Exception as e:
            print(f"  ⚠ 创建索引 {label} 时: {e}")


def import_seeds(tx, seeds):
    """
    导入种子数据
    """
    print(f"  正在导入 {len(seeds)} 条种子数据...")
    for seed in seeds:
        label = seed.get('type', 'Concept')
        name = normalize_name(seed.get('name', ''))
        if not name:
            continue
            
        props = clean_properties({k:v for k,v in seed.items() if k not in ['type', 'name']})
        props['is_seed'] = True
        
        # 动态构建 Cypher
        # 注意：使用 seed 中的属性更新节点
        cypher = (
            f"MERGE (n:`{label}` {{name: $name}}) "
            f"SET n += $props"
        )
        tx.run(cypher, name=name, props=props)


def import_batch(tx, batch, domain):
    """
    批量导入三元组到 Neo4j。
    使用 UNWIND + MERGE 实现高效去重导入。
    """
    # 准备批量数据
    records = []
    for t in batch:
        subj_name = normalize_name(t.get('subject', ''))
        obj_name = normalize_name(t.get('object', ''))
        subj_type = t.get('subject_type', 'Entity')
        obj_type = t.get('object_type', 'Entity')
        predicate = t.get('predicate', 'RELATED_TO')
        props = clean_properties(t.get('properties', {}))
        
        # V6 改进：写入 source_domain
        props['source_domain'] = domain
        source_file = t.get('_source_file', '')
        props['source_file'] = source_file

        records.append({
            'subj_name': subj_name,
            'subj_type': subj_type,
            'obj_name': obj_name,
            'obj_type': obj_type,
            'predicate': predicate,
            'props': props,
        })

    # 按 (subject_type, object_type, predicate) 分组导入
    # 因为 Cypher 中节点标签和关系类型不能参数化，需要动态构建
    groups = defaultdict(list)
    for r in records:
        key = (r['subj_type'], r['obj_type'], r['predicate'])
        groups[key].append(r)

    for (subj_type, obj_type, predicate), group_records in groups.items():
        # 安全检查标签名（防止注入）
        subj_type = re.sub(r'[^a-zA-Z0-9_\u4e00-\u9fff]', '_', subj_type)
        obj_type = re.sub(r'[^a-zA-Z0-9_\u4e00-\u9fff]', '_', obj_type)
        predicate = re.sub(r'[^a-zA-Z0-9_]', '_', predicate)

        params = [{'sn': r['subj_name'], 'on': r['obj_name'], 'props': r['props']}
                  for r in group_records]

        cypher = (
            f"UNWIND $params AS p "
            f"MERGE (s:`{subj_type}` {{name: p.sn}}) "
            # V6 改进：MERGE 时设置 source_domain
            f"ON CREATE SET s.source_domain = p.props.source_domain " 
            f"MERGE (o:`{obj_type}` {{name: p.on}}) "
            f"ON CREATE SET o.source_domain = p.props.source_domain "
            f"MERGE (s)-[r:`{predicate}`]->(o) "
            f"SET r += p.props"
        )

        tx.run(cypher, params=params)


def clear_database(session):
    """
    清空数据库中的所有节点和关系。
    分批删除以避免内存问题。
    """
    print("\n🗑️  正在清空数据库...")
    while True:
        result = session.run(
            "MATCH (n) WITH n LIMIT 10000 DETACH DELETE n RETURN count(*) AS deleted"
        )
        deleted = result.single()["deleted"]
        if deleted == 0:
            break
        print(f"  已删除 {deleted} 个节点...")
    print("  ✓ 数据库已清空")


def verify_import(session):
    """
    验证导入结果。
    """
    print("\n" + "=" * 60)
    print("📊 导入验证报告")
    print("=" * 60)

    # 1. 节点统计
    print("\n📌 节点统计：")
    result = session.run(
        "MATCH (n) RETURN labels(n)[0] AS label, count(n) AS cnt "
        "ORDER BY cnt DESC"
    )
    total_nodes = 0
    for record in result:
        cnt = record["cnt"]
        total_nodes += cnt
        print(f"  {record['label']:20s} : {cnt:,}")
    print(f"  {'总计':20s} : {total_nodes:,}")

    # 2. 关系统计
    print("\n🔗 关系统计：")
    result = session.run(
        "MATCH ()-[r]->() RETURN type(r) AS rel_type, count(r) AS cnt "
        "ORDER BY cnt DESC"
    )
    total_rels = 0
    for record in result:
        cnt = record["cnt"]
        total_rels += cnt
        print(f"  {record['rel_type']:25s} : {cnt:,}")
    print(f"  {'总计':25s} : {total_rels:,}")

    # 3. 数据来源统计
    print("\n🌐 各数据来源关系数：")
    result = session.run(
        "MATCH ()-[r]->() RETURN r.source_domain AS domain, count(r) AS cnt "
        "ORDER BY cnt DESC"
    )
    for record in result:
        print(f"  {str(record['domain']):20s} : {record['cnt']:,}")

    # 4. 跨域关联统计
    print("\n🔄 跨域自然关联：")

    # 检查保险产品与药品目录之间的关联（通过 Insurance 节点）
    result = session.run(
        "MATCH (p:Product)-[:BELONGS_TO]->(i:Insurance) "
        "WITH i, count(p) AS product_count "
        "RETURN i.name AS catalog, product_count "
        "ORDER BY product_count DESC LIMIT 5"
    )
    records_list = list(result)
    if records_list:
        print("  药品-保险目录关联:")
        for record in records_list:
            print(f"    {record['catalog']}: {record['product_count']} 个药品")

    # 5. 数据抽样
    print("\n📝 数据抽样检查：")

    # Medicine 抽样
    result = session.run(
        "MATCH (p:Product)-[r:TREATS]->(m:Medical) "
        "RETURN p.name AS drug, m.name AS disease LIMIT 3"
    )
    records_list = list(result)
    if records_list:
        print("  药品-疾病关系:")
        for record in records_list:
            print(f"    {record['drug']} → 治疗 → {record['disease']}")

    # Insurance 抽样
    result = session.run(
        "MATCH (p:Product)-[r:COVERS]->(b:Benefit) "
        "RETURN p.name AS product, b.name AS benefit LIMIT 3"
    )
    records_list = list(result)
    if records_list:
        print("  保险-保障关系:")
        for record in records_list:
            print(f"    {record['product']} → 覆盖 → {record['benefit']}")

    # NursingHome 抽样
    result = session.run(
        "MATCH (o:Org)-[r:LOCATED_IN]->(d:District) "
        "RETURN o.name AS org, d.name AS district, r.bed_count AS beds LIMIT 3"
    )
    records_list = list(result)
    if records_list:
        print("  养老机构-区域关系:")
        for record in records_list:
            beds = record['beds'] if record['beds'] else '未知'
            print(f"    {record['org']} → 位于 → {record['district']} (床位: {beds})")

    print("\n" + "=" * 60)
    print(f"✅ 导入完成！共 {total_nodes:,} 个节点，{total_rels:,} 条关系")
    print("=" * 60)


def main():
    print("=" * 60)
    print("🚀 JSON 三元组 → Neo4j 导入工具")
    print("=" * 60)
    print(f"  Neo4j URI:  {NEO4J_URI}")
    print(f"  数据库:     {NEO4J_DATABASE}")
    print(f"  数据目录:   {BASE_DIR}")
    print()

    # 1. 加载所有数据
    all_triplets = {}
    total_raw = 0
    
    # 1b. 加载种子数据
    print("🌱 加载种子数据...")
    seeds = load_seeds()
    print(f"  种子数据:   {len(seeds):,} 条")
    
    for domain, directory in DATA_SOURCES.items():
        print(f"📂 加载 {domain} 数据...")
        triplets = load_json_files(directory)
        print(f"  原始三元组: {len(triplets):,} 条")
        deduped = deduplicate_triplets(triplets)
        print(f"  去重后:     {len(deduped):,} 条 (去除 {len(triplets) - len(deduped)} 条重复)")
        all_triplets[domain] = deduped
        total_raw += len(triplets)

    total_deduped = sum(len(v) for v in all_triplets.values())
    print(f"\n📊 总计: {len(seeds):,} 条种子 + {total_raw:,} 条原始 → {total_deduped:,} 条去重后")

    # 2. 连接 Neo4j
    print(f"\n🔌 连接 Neo4j ({NEO4J_URI})...")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    try:
        # 验证连接
        driver.verify_connectivity()
        print("  ✓ 连接成功")

        with driver.session(database=NEO4J_DATABASE) as session:
            # 3. 清空数据库
            clear_database(session)

            # 4. 创建索引
            print("\n📇 创建索引...")
            create_constraints_and_indexes(session)
            
            # 5a. 导入种子数据
            if seeds:
                print("\n🌱 导入种子数据...")
                session.execute_write(import_seeds, seeds)

            # 5b. 导入数据
            print("\n📥 开始导入数据...")
            for domain, triplets in all_triplets.items():
                print(f"\n  🔄 导入 {domain} ({len(triplets):,} 条)...")
                # 分批导入
                for i in tqdm(range(0, len(triplets), BATCH_SIZE),
                              desc=f"  {domain}",
                              unit="batch"):
                    batch = triplets[i:i + BATCH_SIZE]
                    session.execute_write(import_batch, batch, domain)

            # 6. 验证
            verify_import(session)

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.close()
        print("\n🔌 连接已关闭")


if __name__ == "__main__":
    main()

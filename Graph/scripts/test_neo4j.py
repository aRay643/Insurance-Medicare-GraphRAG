"""
Neo4j 数据库功能测试
==================
模拟真实业务查询场景，验证三个域的数据是否可正常使用。
"""
import os
import sys

# 将脚本所在目录加入 sys.path 以便导入可能的模块（如需要）
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from neo4j import GraphDatabase

driver = GraphDatabase.driver("bolt://127.0.0.1:7687", auth=("neo4j", "88888888"))
s = driver.session(database="neo4j")

passed = 0
failed = 0

def test(name, query, expect_rows=True, print_fn=None):
    global passed, failed
    print(f"\n[TEST] {name}")
    try:
        result = s.run(query)
        recs = list(result)
        if expect_rows and len(recs) == 0:
            print("  ⚠ WARN - No results returned")
            failed += 1
            return recs
        if print_fn:
            for rec in recs:
                print_fn(rec)
        print(f"  ✅ PASS ({len(recs)} rows)")
        passed += 1
        return recs
    except Exception as e:
        print(f"  ❌ FAIL - {e}")
        failed += 1
        return []


# ============================================================
# 1. 基础连通性
# ============================================================
print("=" * 60)
print("Neo4j 数据库功能测试")
print("=" * 60)

test("基础连通性",
     "RETURN 1 AS ok",
     print_fn=lambda r: print(f"  Database OK: {r['ok']}"))

# ============================================================
# 2. 全局统计
# ============================================================
test("节点总数",
     "MATCH (n) RETURN count(n) AS total",
     print_fn=lambda r: print(f"  节点总数: {r['total']:,}"))

test("关系总数",
     "MATCH ()-[r]->() RETURN count(r) AS total",
     print_fn=lambda r: print(f"  关系总数: {r['total']:,}"))

test("标签分布",
     "MATCH (n) RETURN labels(n)[0] AS label, count(n) AS cnt ORDER BY cnt DESC",
     print_fn=lambda r: print(f"  {str(r['label']):20s}: {r['cnt']:,}"))

# ============================================================
# 3. 保险域查询
# ============================================================
test("保险产品列表",
     "MATCH (p:Product)-[:BELONGS_TO_CATEGORY]->(pc:ProductCategory) "
     "RETURN pc.name AS category, collect(p.name)[..3] AS products, count(p) AS cnt "
     "ORDER BY cnt DESC",
     print_fn=lambda r: print(f"  {r['category']}: {r['cnt']} products, e.g. {r['products']}"))

test("保险保障内容",
     "MATCH (p:Product)-[:COVERS]->(b:Benefit) "
     "RETURN p.name AS product, collect(b.name)[..3] AS benefits "
     "LIMIT 3",
     print_fn=lambda r: print(f"  {r['product']} -> {r['benefits']}"))

test("保险免责条款粒度",
     "MATCH (p:Product)-[:HAS_EXCLUSION]->(e:Exclusion) "
     "RETURN p.name AS product, count(e) AS cnt "
     "ORDER BY cnt DESC LIMIT 5",
     print_fn=lambda r: print(f"  {r['product']}: {r['cnt']} exclusions"))

test("投保条件 (age_min/age_max)",
     "MATCH (p:Product)-[r:ELIGIBILITY]->(e:Eligibility) "
     "RETURN p.name AS product, r.age_min AS age_min, r.age_max AS age_max "
     "LIMIT 5",
     print_fn=lambda r: print(f"  {r['product']}: age {r['age_min']}~{r['age_max']}"))

# ============================================================
# 4. 药品域查询
# ============================================================
test("药品-疾病关联",
     "MATCH (p:Product)-[r:TREATS]->(m:Medical) "
     "RETURN p.name AS drug, m.name AS disease, "
     "r.treatment_line AS line, r.indication_limit AS indication "
     "LIMIT 5",
     print_fn=lambda r: print(f"  {r['drug']} -> {r['disease']} (line {r['line']}, {r['indication']})"))

test("药品品牌查询",
     "MATCH (p:Product)-[:HAS_TRADE_NAME]->(b:Brand) "
     "RETURN p.name AS drug, b.name AS brand "
     "LIMIT 5",
     print_fn=lambda r: print(f"  {r['drug']} -> {r['brand']}"))

test("制药公司统计",
     "MATCH (p:Product)-[:PRODUCED_BY]->(c:Company) "
     "RETURN c.name AS company, count(p) AS cnt "
     "ORDER BY cnt DESC LIMIT 5",
     print_fn=lambda r: print(f"  {r['company']}: {r['cnt']} products"))

# ============================================================
# 5. 养老域查询
# ============================================================
test("各省养老机构数",
     "MATCH (o:Org)-[:LOCATED_IN]->(d:District)-[:BELONGS_TO]->(p:Province) "
     "RETURN p.name AS province, count(o) AS cnt "
     "ORDER BY cnt DESC LIMIT 10",
     print_fn=lambda r: print(f"  {r['province']}: {r['cnt']:,} orgs"))

test("按服务类型统计",
     "MATCH (o:Org)-[:PROVIDES_SERVICE]->(s:Service) "
     "RETURN s.name AS service, count(o) AS cnt "
     "ORDER BY cnt DESC",
     print_fn=lambda r: print(f"  {r['service']}: {r['cnt']:,} orgs"))

test("含医疗设施的机构",
     "MATCH (o:Org)-[r:LOCATED_IN]->(d:District) "
     "WHERE r.has_medical_facility = true "
     "RETURN count(o) AS cnt",
     print_fn=lambda r: print(f"  含医疗设施的机构: {r['cnt']:,}"))

test("床位统计",
     "MATCH (o:Org)-[r:LOCATED_IN]->(d:District) "
     "WHERE r.bed_count > 0 "
     "RETURN min(r.bed_count) AS min_bed, "
     "avg(r.bed_count) AS avg_bed, "
     "max(r.bed_count) AS max_bed, "
     "count(o) AS total",
     print_fn=lambda r: print(
         f"  bed range: {r['min_bed']}~{r['max_bed']}, "
         f"avg: {r['avg_bed']:.0f}, "
         f"count: {r['total']:,}"))

# ============================================================
# 6. 跨域查询
# ============================================================
test("跨域桥接 (Service -> ProductCategory)",
     "MATCH (s:Service)-[:SUITABLE_FOR]->(pc:ProductCategory) "
     "RETURN s.name AS service, pc.name AS category",
     print_fn=lambda r: print(f"  {r['service']} -> {r['category']}"))

test("跨域路径 (Org -> Service -> ProductCategory)",
     "MATCH (o:Org)-[:PROVIDES_SERVICE]->(s:Service)"
     "-[:SUITABLE_FOR]->(pc:ProductCategory) "
     "RETURN s.name AS service, pc.name AS category, count(o) AS orgs "
     "ORDER BY orgs DESC",
     print_fn=lambda r: print(f"  {r['service']} -> {r['category']}: {r['orgs']:,} orgs"))

test("完整跨域路径 (Org -> ... -> Product)",
     "MATCH (o:Org)-[:PROVIDES_SERVICE]->(s:Service)"
     "-[:SUITABLE_FOR]->(pc:ProductCategory)"
     "<-[:BELONGS_TO_CATEGORY]-(p:Product) "
     "RETURN s.name AS service, pc.name AS category, "
     "collect(DISTINCT p.name)[..3] AS products, count(DISTINCT o) AS orgs "
     "ORDER BY orgs DESC",
     print_fn=lambda r: print(
         f"  {r['service']} -> {r['category']}: "
         f"{r['orgs']:,} orgs, products: {r['products']}"))

# ============================================================
# 7. 种子数据
# ============================================================
test("种子数据完整性",
     "MATCH (n) WHERE n.is_seed = true "
     "RETURN labels(n)[0] AS label, n.name AS name, n.definition AS def "
     "LIMIT 5",
     print_fn=lambda r: print(f"  [{r['label']}] {r['name']}: {str(r['def'])[:40]}..."))

# ============================================================
# 8. 业务场景模拟
# ============================================================
print("\n" + "=" * 60)
print("业务场景模拟查询")
print("=" * 60)

test("场景A: 北京有医疗设施的养老机构",
     "MATCH (o:Org)-[r:LOCATED_IN]->(d:District)-[:BELONGS_TO]->(p:Province {name: '北京市'}) "
     "WHERE r.has_medical_facility = true "
     "RETURN o.name AS org, d.name AS district, r.bed_count AS beds "
     "ORDER BY r.bed_count DESC LIMIT 5",
     print_fn=lambda r: print(f"  {r['org']} ({r['district']}, {r['beds']} beds)"))

test("场景B: 治疗肺癌的药品及其品牌",
     "MATCH (p:Product)-[r:TREATS]->(m:Medical) "
     "WHERE m.name CONTAINS '肺癌' OR m.name CONTAINS '非小细胞' "
     "OPTIONAL MATCH (p)-[:HAS_TRADE_NAME]->(b:Brand) "
     "RETURN p.name AS drug, b.name AS brand, m.name AS disease, r.indication_limit AS indication "
     "LIMIT 5",
     print_fn=lambda r: print(f"  {r['drug']}({r['brand']}) -> {r['disease']} [{r['indication']}]"))

test("场景C: 某保险产品的完整保障图谱",
     "MATCH (p:Product)-[r]->(n) "
     "WHERE p.source_domain = 'insurance' "
     "WITH p, type(r) AS rel, labels(n)[0] AS target_type, count(n) AS cnt "
     "RETURN p.name AS product, rel, target_type, cnt "
     "ORDER BY p.name, cnt DESC "
     "LIMIT 15",
     print_fn=lambda r: print(f"  {r['product']} -[{r['rel']}]-> ({r['target_type']}) x{r['cnt']}"))

# ============================================================
# 结果汇总
# ============================================================
print("\n" + "=" * 60)
total = passed + failed
print(f"测试结果: {passed}/{total} PASSED, {failed}/{total} WARN/FAIL")
print("=" * 60)

s.close()
driver.close()

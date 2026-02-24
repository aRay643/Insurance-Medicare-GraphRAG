"""
Neo4j 数据库功能测试 (V2)
==========================
模拟真实业务查询场景，验证三个域的数据是否可正常使用。
新增: 彩色输出、查询计时、金额倍数测试、表格格式化
"""
import os
import sys
import time

# 将脚本所在目录加入 sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from neo4j import GraphDatabase

# ANSI 颜色代码
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# 配置
NEO4J_URI = "bolt://127.0.0.1:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "88888888"

# 测试统计
stats = {
    "passed": 0,
    "failed": 0,
    "warned": 0,
    "queries": [],
    "start_time": None
}

def format_number(n):
    """格式化数字显示"""
    if n is None:
        return "N/A"
    return f"{n:,}"

def format_time(seconds):
    """格式化时间显示"""
    if seconds < 0.001:
        return f"{seconds*1000:.2f}ms"
    elif seconds < 1:
        return f"{seconds*1000:.1f}ms"
    else:
        return f"{seconds:.2f}s"

def format_table(headers, rows, max_width=50):
    """打印表格"""
    # 计算每列宽度
    col_widths = []
    for i, header in enumerate(headers):
        max_len = len(header)
        for row in rows:
            val = str(row[i]) if i < len(row) else ""
            max_len = max(max_len, min(len(val), max_width))
        col_widths.append(max_len + 2)

    # 打印表头
    header_line = Colors.BOLD + Colors.OKCYAN
    for i, header in enumerate(headers):
        header_line += f"{header.ljust(col_widths[i])}"
    header_line += Colors.ENDC
    print(header_line)

    # 打印分隔线
    print("-" * sum(col_widths))

    # 打印数据行
    for row in rows:
        line = ""
        for i, val in enumerate(row):
            val_str = str(row[i]) if i < len(row) else ""
            if len(val_str) > max_width:
                val_str = val_str[:max_width-3] + "..."
            line += val_str.ljust(col_widths[i])
        print(line)

def test(name, query, expect_rows=True, print_fn=None, use_table=False,
         table_headers=None, table_max_width=50):
    """
    执行测试

    参数:
        name: 测试名称
        query: Cypher查询语句
        expect_rows: 是否期望有结果行
        print_fn: 自定义打印函数
        print_table: 是否以表格形式打印
        table_headers: 表格列名
        table_max_width: 表格单元格最大宽度
    """
    print(f"\n{Colors.OKBLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.ENDC}")
    print(f"{Colors.BOLD}[TEST]{Colors.ENDC} {Colors.BOLD}{name}{Colors.ENDC}")

    start_time = time.time()
    try:
        result = s.run(query)
        recs = list(result)
        elapsed = time.time() - start_time

        # 记录查询统计
        stats["queries"].append({
            "name": name,
            "rows": len(recs),
            "time": elapsed
        })

        # 处理结果
        if expect_rows and len(recs) == 0:
            print(f"  {Colors.WARNING}⚠ WARN - No results returned{Colors.ENDC}")
            stats["warned"] += 1
        elif use_table and table_headers and recs:
            # 表格形式输出
            rows = [[str(v) for v in rec.values()] for rec in recs[:10]]
            format_table(table_headers, rows, table_max_width)
            if len(recs) > 10:
                print(f"  ... ({len(recs)-10} more rows)")
            print(f"  {Colors.OKGREEN}✅ PASS{Colors.ENDC} ({len(recs)} rows, {format_time(elapsed)})")
            stats["passed"] += 1
        elif print_fn:
            for rec in recs[:8]:
                print_fn(rec)
            if len(recs) > 8:
                print(f"  ... ({len(recs)-8} more rows)")
            print(f"  {Colors.OKGREEN}✅ PASS{Colors.ENDC} ({len(recs)} rows, {format_time(elapsed)})")
            stats["passed"] += 1
        else:
            print(f"  {Colors.OKGREEN}✅ PASS{Colors.ENDC} ({len(recs)} rows, {format_time(elapsed)})")
            stats["passed"] += 1

        return recs

    except Exception as e:
        elapsed = time.time() - start_time
        stats["queries"].append({
            "name": name,
            "rows": 0,
            "time": elapsed,
            "error": str(e)
        })
        print(f"  {Colors.FAIL}❌ FAIL{Colors.ENDC} - {e}")
        stats["failed"] += 1
        return []

def print_summary():
    """打印测试摘要"""
    total = stats["passed"] + stats["failed"] + stats["warned"]

    print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}测试摘要{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}")

    # 总体结果
    print(f"\n{Colors.BOLD}结果统计:{Colors.ENDC}")
    if stats["failed"] == 0 and stats["warned"] == 0:
        print(f"  {Colors.OKGREEN}✓ 全部通过! {stats['passed']}/{total} 个测试{Colors.ENDC}")
    else:
        print(f"  通过: {Colors.OKGREEN}{stats['passed']}{Colors.ENDC}/{total}")
        print(f"  警告: {Colors.WARNING}{stats['warned']}{Colors.ENDC}")
        print(f"  失败: {Colors.FAIL}{stats['failed']}{Colors.ENDC}")

    # 查询时间统计
    if stats["queries"]:
        times = [q["time"] for q in stats["queries"]]
        print(f"\n{Colors.BOLD}查询性能:{Colors.ENDC}")
        print(f"  总查询数: {len(stats['queries'])}")
        print(f"  总耗时: {format_time(sum(times))}")
        print(f"  平均: {format_time(sum(times)/len(times))}")
        print(f"  最快: {format_time(min(times))}")
        print(f"  最慢: {format_time(max(times))}")

        # 找出最慢的查询
        slowest = max(stats["queries"], key=lambda x: x["time"])
        print(f"  最慢查询: {slowest['name']} ({format_time(slowest['time'])})")

    # 总执行时间
    if stats["start_time"]:
        total_time = time.time() - stats["start_time"]
        print(f"\n{Colors.BOLD}总执行时间:{Colors.ENDC} {format_time(total_time)}")

    print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")

# ============================================================
# 主程序
# ============================================================
if __name__ == "__main__":
    stats["start_time"] = time.time()

    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        s = driver.session(database="neo4j")
    except Exception as e:
        print(f"{Colors.FAIL}无法连接到数据库: {e}{Colors.ENDC}")
        print(f"请确保Neo4j正在运行，URI: {NEO4J_URI}")
        sys.exit(1)

    print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}Neo4j 数据库功能测试 V2{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}")
    print(f"  URI: {NEO4J_URI}")
    print(f"  Database: neo4j")

    # ============================================================
    # 1. 基础连通性
    # ============================================================
    test("基础连通性",
         "RETURN 1 AS ok, 'Database connected!' AS msg",
         print_fn=lambda r: print(f"  {r['msg']}"))

    # ============================================================
    # 2. 全局统计
    # ============================================================
    test("节点总数",
         "MATCH (n) RETURN count(n) AS total",
         print_fn=lambda r: print(f"  节点总数: {format_number(r['total'])}"))

    test("关系总数",
         "MATCH ()-[r]->() RETURN count(r) AS total",
         print_fn=lambda r: print(f"  关系总数: {format_number(r['total'])}"))

    test("标签分布",
         "MATCH (n) RETURN labels(n)[0] AS label, count(n) AS cnt ORDER BY cnt DESC",
         use_table=True,
         table_headers=["标签类型", "数量"])

    # ============================================================
    # 3. 保险域查询
    # ============================================================
    print(f"\n{Colors.OKCYAN}━━━ 保险域查询 ━━━{Colors.ENDC}")

    test("保险产品分类统计",
         "MATCH (p:Product)-[:BELONGS_TO_CATEGORY]->(pc:ProductCategory) "
         "RETURN pc.name AS category, count(p) AS cnt "
         "ORDER BY cnt DESC",
         use_table=True,
         table_headers=["保险类别", "产品数量"])

    test("保险产品示例",
         "MATCH (p:Product)-[:BELONGS_TO_CATEGORY]->(pc:ProductCategory) "
         "RETURN pc.name AS category, collect(p.name)[..3] AS examples "
         "ORDER BY pc.name",
         print_fn=lambda r: print(f"  {r['category']}: {r['examples']}"))

    # ============================================================
    # 4. 赔付倍数/金额信息测试 (新增)
    # ============================================================
    print(f"\n{Colors.OKCYAN}━━━ 赔付倍数/金额信息测试 ━━━{Colors.ENDC}")

    test("有明确赔付倍数的产品",
         "MATCH (p:Product)-[r:COVERS]->(b:Benefit) "
         "WHERE r.payout_basis CONTAINS '倍' OR r.payout_ratio IS NOT NULL "
         "RETURN p.name AS product, b.name AS benefit, r.payout_basis AS payout, r.payout_ratio AS ratio "
         "ORDER BY product, benefit "
         "LIMIT 15",
         use_table=True,
         table_headers=["产品", "保障", "赔付依据", "比例"])

    test("年金保险给付频率",
         "MATCH (p:Product)-[r:COVERS]->(b:Benefit) "
         "WHERE b.name CONTAINS '年金' OR b.name CONTAINS '生存金' "
         "RETURN p.name AS product, b.name AS benefit, r.payout_frequency AS freq, r.payout_basis AS payout "
         "ORDER BY product "
         "LIMIT 10",
         use_table=True,
         table_headers=["产品", "保障", "给付频率", "赔付依据"])

    test("身故保险金赔付方式",
         "MATCH (p:Product)-[r:COVERS]->(b:Benefit) "
         "WHERE b.name CONTAINS '身故' "
         "RETURN p.name AS product, b.name AS benefit, r.payout_basis AS payout "
         "ORDER BY product "
         "LIMIT 10",
         use_table=True,
         table_headers=["产品", "保障", "赔付依据"])

    test("年龄相关的赔付条件",
         "MATCH (p:Product)-[r:COVERS]->(b:Benefit) "
         "WHERE r.age_limit_min IS NOT NULL OR r.age_limit_max IS NOT NULL "
         "RETURN p.name AS product, b.name AS benefit, "
         "coalesce(r.age_limit_min, 0) AS age_min, coalesce(r.age_limit_max, 999) AS age_max, r.payout_basis AS payout "
         "ORDER BY product "
         "LIMIT 10",
         use_table=True,
         table_headers=["产品", "保障", "年龄下限", "年龄上限", "赔付依据"])

    test("少儿年金保险教育金倍数",
         "MATCH (p:Product)-[r:COVERS]->(b:Benefit) "
         "WHERE p.name CONTAINS '少儿' AND (b.name CONTAINS '教育' OR b.name CONTAINS '关爱' OR b.name CONTAINS '成家') "
         "RETURN p.name AS product, b.name AS benefit, r.payout_basis AS payout "
         "ORDER BY product, benefit",
         use_table=True,
         table_headers=["产品", "保障", "赔付依据"])

    # ============================================================
    # 5. 保险投保条件测试
    # ============================================================
    print(f"\n{Colors.OKCYAN}━━━ 投保条件测试 ━━━{Colors.ENDC}")

    test("投保年龄范围统计",
         "MATCH (e:Eligibility)-[r:ELIGIBILITY]->(p:Product) "
         "RETURN min(r.age_min) AS min_age, max(r.age_max) AS max_age, "
         "count(DISTINCT p) AS total_products, "
         "count(CASE WHEN r.age_min <= 1 THEN 1 END) AS from_birth "
         "LIMIT 1",
         print_fn=lambda r: print(f"  年龄范围: {r['min_age']}岁 ~ {r['max_age']}岁 (999=无限制)"))

    test("可出生投保的产品",
         "MATCH (e:Eligibility)-[r:ELIGIBILITY]->(p:Product) "
         "WHERE r.age_min <= 1 "
         "RETURN p.name AS product, r.age_min AS min_age, r.health_requirement AS health "
         "ORDER BY product "
         "LIMIT 10",
         use_table=True,
         table_headers=["产品", "最低年龄", "健康要求"])

    test("老年可投保产品",
         "MATCH (e:Eligibility)-[r:ELIGIBILITY]->(p:Product) "
         "WHERE r.age_max >= 60 OR r.age_max = 999 "
         "RETURN p.name AS product, r.age_max AS max_age, r.health_requirement AS health "
         "ORDER BY r.age_max DESC "
         "LIMIT 10",
         use_table=True,
         table_headers=["产品", "最高年龄", "健康要求"])

    # ============================================================
    # 6. 免责条款测试
    # ============================================================
    print(f"\n{Colors.OKCYAN}━━━ 免责条款测试 ━━━{Colors.ENDC}")

    test("免责条款最多的产品",
         "MATCH (p:Product)-[:HAS_EXCLUSION]->(e:Exclusion) "
         "WITH p, count(e) AS cnt "
         "RETURN p.name AS product, cnt "
         "ORDER BY cnt DESC "
         "LIMIT 5",
         use_table=True,
         table_headers=["产品", "免责条款数"])

    test("常见免责项",
         "MATCH (p:Product)-[:HAS_EXCLUSION]->(e:Exclusion) "
         "WITH e.name AS exclusion, count(DISTINCT p) AS products "
         "RETURN exclusion, products "
         "ORDER BY products DESC "
         "LIMIT 10",
         use_table=True,
         table_headers=["免责项", "产品数"])

    # ============================================================
    # 7. 药品域查询
    # ============================================================
    print(f"\n{Colors.OKCYAN}━━━ 药品域查询 ━━━{Colors.ENDC}")

    test("药品-疾病关联",
         "MATCH (p:Product)-[r:TREATS]->(m:Medical) "
         "RETURN p.name AS drug, m.name AS disease, r.treatment_line AS line "
         "LIMIT 5",
         use_table=True,
         table_headers=["药品", "疾病", "治疗线"])

    test("制药公司统计",
         "MATCH (p:Product)-[:PRODUCED_BY]->(c:Company) "
         "RETURN c.name AS company, count(p) AS cnt "
         "ORDER BY cnt DESC LIMIT 5",
         use_table=True,
         table_headers=["公司", "产品数"])

    # ============================================================
    # 8. 养老域查询
    # ============================================================
    print(f"\n{Colors.OKCYAN}━━━ 养老域查询 ━━━{Colors.ENDC}")

    test("各省养老机构数",
         "MATCH (o:Org)-[:LOCATED_IN]->(d:District)-[:BELONGS_TO]->(p:Province) "
         "RETURN p.name AS province, count(o) AS cnt "
         "ORDER BY cnt DESC LIMIT 10",
         use_table=True,
         table_headers=["省份", "机构数"])

    test("床位统计",
         "MATCH (o:Org)-[r:LOCATED_IN]->(d:District) "
         "WHERE r.bed_count > 0 "
         "RETURN min(r.bed_count) AS min_bed, toInteger(avg(r.bed_count)) AS avg_bed, max(r.bed_count) AS max_bed, count(o) AS total "
         "LIMIT 1",
         print_fn=lambda r: print(f"  床位范围: {r['min_bed']} ~ {r['max_bed']}, 平均: {r['avg_bed']}, 机构: {r['total']:,}"))

    # ============================================================
    # 9. 跨域查询
    # ============================================================
    print(f"\n{Colors.OKCYAN}━━━ 跨域查询 ━━━{Colors.ENDC}")

    test("完整跨域路径 (机构 -> 服务 -> 保险类别 -> 保险产品)",
         "MATCH (o:Org)-[:PROVIDES_SERVICE]->(s:Service)"
         "-[:SUITABLE_FOR]->(pc:ProductCategory)"
         "<-[:BELONGS_TO_CATEGORY]-(p:Product) "
         "WITH s.name AS service, pc.name AS category, count(DISTINCT o) AS orgs, count(DISTINCT p) AS prods "
         "RETURN service, category, orgs, prods "
         "ORDER BY orgs DESC "
         "LIMIT 10",
         use_table=True,
         table_headers=["服务", "保险类别", "机构数", "产品数"])

    # ============================================================
    # 10. 业务场景模拟
    # ============================================================
    print(f"\n{Colors.OKCYAN}━━━ 业务场景模拟 ━━━{Colors.ENDC}")

    test("场景A: 北京有医疗设施的养老机构",
         "MATCH (o:Org)-[r:LOCATED_IN]->(d:District)-[:BELONGS_TO]->(p:Province {name: '北京市'}) "
         "WHERE r.has_medical_facility = true "
         "RETURN o.name AS org, d.name AS district, r.bed_count AS beds "
         "ORDER BY r.bed_count DESC LIMIT 5",
         use_table=True,
         table_headers=["机构", "区县", "床位数"])

    test("场景B: 60岁老人可投保的保险产品",
         "MATCH (e:Eligibility)-[r:ELIGIBILITY]->(p:Product)-[:BELONGS_TO_CATEGORY]->(pc:ProductCategory) "
         "WHERE r.age_min <= 60 AND (r.age_max >= 60 OR r.age_max = 999) "
         "RETURN p.name AS product, pc.name AS category, r.age_max AS max_age "
         "ORDER BY product "
         "LIMIT 10",
         use_table=True,
         table_headers=["产品", "类别", "投保上限年龄"])

    test("场景C: 重大疾病保险产品",
         "MATCH (p:Product)-[:BELONGS_TO_CATEGORY]->(pc:ProductCategory) "
         "WHERE pc.name IN ['重大疾病保险', '防癌疾病保险', '疾病保险'] OR p.name CONTAINS '重疾' "
         "RETURN DISTINCT p.name AS product, pc.name AS category "
         "ORDER BY product "
         "LIMIT 10",
         use_table=True,
         table_headers=["产品", "类别"])

    # ============================================================
    # 11. 基础概念（种子数据）测试
    # ============================================================
    print(f"\n{Colors.OKCYAN}━━━ 基础概念（种子数据）测试 ━━━{Colors.ENDC}")

    test("种子数据统计",
         "MATCH (n) WHERE n.is_seed = true "
         "WITH labels(n)[0] AS type, count(n) AS cnt "
         "RETURN type, cnt "
         "ORDER BY type",
         use_table=True,
         table_headers=["类型", "数量"])

    test("Condition条件概念（保险术语）",
         "MATCH (c:Condition) WHERE c.is_seed = true "
         "RETURN c.name AS name, c.definition AS definition "
         "ORDER BY name",
         use_table=True,
         table_headers=["条件名称", "定义"],
         table_max_width=50)

    test("Exclusion免责概念",
         "MATCH (e:Exclusion) WHERE e.is_seed = true "
         "RETURN e.name AS name, e.definition AS definition "
         "ORDER BY name",
         use_table=True,
         table_headers=["免责项", "定义"],
         table_max_width=50)

    test("种子数据与实际保险产品关联",
         "MATCH (seed:Condition) WHERE seed.is_seed = true "
         "MATCH (p:Product)-[:HAS_TERM]->(seed) "
         "RETURN seed.name AS concept, count(p) AS products "
         "ORDER BY products DESC "
         "LIMIT 10",
         use_table=True,
         table_headers=["种子概念", "关联产品数"])

    test("带有等待期的产品",
         "MATCH (seed:Condition {name: '等待期'}) "
         "MATCH (p:Product)-[:HAS_TERM]->(seed) "
         "RETURN p.name AS product "
         "ORDER BY product "
         "LIMIT 10",
         print_fn=lambda r: print(f"  {r['product']}"))

    test("带有犹豫期的产品",
         "MATCH (seed:Condition {name: '犹豫期'}) "
         "MATCH (p:Product)-[:HAS_TERM]->(seed) "
         "WITH p, seed "
         "MATCH (p)-[r:HAS_TERM]->(seed) "
         "RETURN p.name AS product, r.days AS days "
         "ORDER BY product "
         "LIMIT 10",
         use_table=True,
         table_headers=["产品", "天数"])

    # ============================================================
    # 12. 疾病与医疗域查询 (新增)
    # ============================================================
    print(f"\n{Colors.OKCYAN}━━━ 疾病与医疗域查询 ━━━{Colors.ENDC}")

    test("常见疾病的主次症状",
         "MATCH (d:Disease)-[:HAS_SYMPTOM]->(s:Symptom) "
         "WITH d, collect(s.name) AS symptoms "
         "RETURN d.name AS disease, symptoms[0..5] AS top_symptoms, size(symptoms) AS cnt "
         "ORDER BY cnt DESC LIMIT 5",
         use_table=True,
         table_headers=["疾病", "主要症状", "症状总数"])

    test("疾病及其关联并发症",
         "MATCH (d:Disease)-[:HAS_COMPLICATION]->(c:Disease) "
         "WITH d, collect(c.name) AS complications "
         "RETURN d.name AS disease, complications[0..5] AS comps, size(complications) AS cnt "
         "ORDER BY cnt DESC LIMIT 5",
         use_table=True,
         table_headers=["疾病", "常见并发症", "并发症数量"])

    test("重点科室涵盖的疾病统计",
         "MATCH (d:Disease)-[:TREATED_AT]->(dept:Department) "
         "WITH dept, count(d) AS disease_cnt "
         "RETURN dept.name AS department, disease_cnt "
         "ORDER BY disease_cnt DESC LIMIT 5",
         use_table=True,
         table_headers=["科室", "诊疗疾病数"])

    test("疾病与药品的跨域关联（新版）",
         "MATCH (d:Disease)-[:CAN_BE_TREATED_BY]->(p:Product) "
         "WITH d, collect(p.name) AS drugs "
         "RETURN d.name AS disease, drugs[0..3] AS recomm_drugs, size(drugs) AS cnt "
         "ORDER BY cnt DESC LIMIT 5",
         use_table=True,
         table_headers=["疾病", "推荐药品", "药品数量"])

    test("各类治疗方式与受治疾病",
         "MATCH (d:Disease)-[:CURED_BY]->(t:Treatment) "
         "WITH t, count(d) AS disease_cnt "
         "RETURN t.name AS treatment, disease_cnt "
         "ORDER BY disease_cnt DESC LIMIT 5",
         use_table=True,
         table_headers=["治疗方式", "适用疾病数"])

    test("常规检查项目统计",
         "MATCH (d:Disease)-[:REQUIRES_CHECK]->(c:CheckItem) "
         "WITH c, count(d) AS disease_cnt "
         "RETURN c.name as check_item, disease_cnt "
         "ORDER BY disease_cnt DESC LIMIT 5",
         use_table=True,
         table_headers=["检查项目", "相关疾病数"])

    # ============================================================
    # 13. 新增关系类型专项测试 (v2.3新增)
    # ============================================================
    print(f"\n{Colors.OKCYAN}━━━ 新增关系类型专项测试 ━━━{Colors.ENDC}")

    test("TREATS_DISEASE: 药品治疗疾病百科",
         "MATCH (p:Product)-[r:TREATS_DISEASE]->(d:Disease) "
         "RETURN p.name AS 药品, d.name AS 疾病 "
         "LIMIT 10",
         use_table=True,
         table_headers=["药品", "疾病百科"])

    test("HAS_ATTRIBUTE: 疾病属性存储",
         "MATCH (d:Disease)-[r:HAS_ATTRIBUTE]->(d:Disease) "
         "WHERE d.name = '肺泡蛋白质沉积症' "
         "RETURN d.name AS 疾病, keys(r)[1..5] AS 属性 "
         "LIMIT 1",
         print_fn=lambda r: print(f"  疾病: {r['疾病']}"))

    test("疾病百科与保险疾病关联 (名称匹配)",
         "MATCH (d1:Disease) "
         "MATCH (m:Medical) "
         "WHERE m.name CONTAINS d1.name OR d1.name CONTAINS m.name "
         "MATCH (m)-[r:COVERED_BY]->(p:Product) "
         "RETURN DISTINCT d1.name AS 疾病百科, m.name AS 保险疾病, p.name AS 保险产品 "
         "LIMIT 10",
         use_table=True,
         table_headers=["疾病百科", "保险疾病", "保险产品"])

    test("完整跨域路径: 疾病百科 → 药品 → 保险",
         "MATCH (d:Disease {name: '冠心病'})-[:CAN_BE_TREATED_BY]->(p1:Product) "
         "WITH d, collect(p1.name) as drugs "
         "OPTIONAL MATCH (m:Medical)-[:COVERED_BY]->(p2:Product) "
         "WHERE m.name CONTAINS d.name "
         "RETURN d.name AS 疾病百科, drugs AS 治疗药品, "
         "collect(DISTINCT p2.name) AS 承保产品 "
         "LIMIT 1",
         print_fn=lambda r: (
             print(f"  疾病: 冠心病"),
             print(f"    治疗药品: {r['治疗药品']}"),
             print(f"    承保产品: {r['承保产品']}")
         ))

    # ============================================================
    # 清理和摘要
    # ============================================================
    s.close()
    driver.close()

    print_summary()

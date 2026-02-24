# 保险-药品-养老 知识图谱 (Insurance-Medicine-NursingHome Knowledge Graph)

基于 Neo4j 图数据库构建的跨域知识图谱，覆盖 **保险产品**、**创新药品**、**养老机构** 和 **疾病百科** 四大领域，通过自然实体关联和桥接关系实现跨域查询。

## 📊 数据规模

| 指标 | 数量 |
|------|------|
| 节点总数 | **91,899** |
| 关系总数 | **597,563** |
| 保险产品 | 105 |
| 养老机构 | 56,368 |
| 药品实体 | 23 |
| 疾病百科 (Disease) | 8,807 |
| 症状 (Symptom) | 5,998 |
| 治疗方式 (Treatment) | 544 |
| 检查项目 (CheckItem) | 3,353 |
| 就诊科室 (Department) | 54 |
| 疾病/医疗项目 (Medical) | 8,924 |
| 保障项目 (Benefit) | 166 |
| 免责条款 (Exclusion) | 177 |

## 🎯 数据质量 (v2.3)

| 指标 | 覆盖率 |
|------|--------|
| ELIGIBILITY (投保条件) | **100.0%** (105/105) |
| COVERS (保障责任) | **100.0%** (105/105) |

**最近更新** (2026-02-24):
- ✅ 新增疾病百科数据：8,807个Disease节点
- ✅ 新增症状数据：5,998个Symptom节点
- ✅ 新增治疗方式和检查项目数据
- ✅ 建立疾病-药品关联：59,738条CAN_BE_TREATED_BY关系
- ✅ 建立疾病-症状关联：54,695条HAS_SYMPTOM关系

## 🏗️ 项目结构

```
├── prompts/                         # LLM 提取 Prompt (V6 最终版)
│   ├── insurance_prompt_v6.md       # 保险数据提取 Prompt
│   ├── nursing_home_prompt_v6.md    # 养老机构数据提取 Prompt
│   └── medicine_prompt_v6.md        # 商业创新药品 Prompt
│
├── Seeds/                           # 通用术语种子数据
│   └── common_terms.json            # 犹豫期、等待期等标准定义
│
├── db_data/                         # 图谱数据 (JSON 三元组)
│   ├── Insurance_v2/                # 保险三元组数据 (105 文件)
│   ├── Medicine_v2/                 # 药品三元组数据
│   │   ├── medical_triplets.json    # 转换后的三元组 (266,950条)
│   │   ├── medical_triplets_linkage.json  # 关联三元组
│   │   └── medicine_structure_v6.json     # 药品结构数据
│   └── NursingHome_v2/              # 养老机构三元组数据 (1168 文件)
│
├── source/                          # 原始数据源
│   ├── insurance/                   # 保险条款文本
│   ├── medicine/                    # 药品目录/疾病数据
│   │   ├── medical.json             # 原始疾病百科数据 (8,808条)
│   │   ├── 国家基本医疗保险...pdf    # 医保药品目录
│   │   └── 商业健康保险创新药品目录.pdf  # 创新药品目录
│   └── nursing_home/                # 养老机构原始数据
│
├── scripts/                         # Python 工具脚本
│   ├── import_to_neo4j.py           # Neo4j 导入脚本
│   ├── transform_medical_improved.py # 疾病数据转换脚本
│   ├── test_neo4j.py                # 数据库功能测试
│   └── extract_pdf_text_00_105.py   # PDF 文本提取工具
│
├── requirements.txt                 # Python 依赖
└── README.md
```

## 🚀 快速开始

### 1. 环境准备

#### Python 环境

```bash
# 安装 Python 依赖
pip install -r requirements.txt
```

#### Neo4j 数据库配置

本脚本默认连接本地数据库 `bolt://127.0.0.1:7687`。

**0. 文件配置**
1. **三元组配置**：将下载的db_data压缩包解压缩并放到根目录下。
2. **原始数据配置**：将下载的source压缩包解压缩，放到根目录下。（可选）

**1. 下载与安装**
- 访问 [Neo4j Download Center](https://neo4j.com/download/) 下载并安装 **Neo4j Desktop**。
- 启动 Neo4j Desktop 并确保安装了 Database。

**2. 创建数据库（使用 Neo4j Desktop）**
1. **新建项目**: 在 Neo4j Desktop 中创建一个新 instance。
2. **添加数据库**: 任意起一个数据库名称，版本保持默认版本。
3. **设置密码**: 建议设置密码为 **`88888888`**，点击Create。
   - *如果使用其他密码，请修改 `scripts/import_to_neo4j.py` 和 `scripts/test_neo4j.py` 中的 `NEO4J_PASSWORD` 变量。*
4. **安装插件**: (可选) 推荐安装 **APOC** 插件以支持更高级的图算法。
5. **启动服务**: 点击 `Start`，等待数据库状态变为 `Active`。
6. **确认端口**: 确保 Bolt 端口为默认的 `7687`（可在 DBMS 的 Settings 中查看 `dbms.connector.bolt.listen_address`）。

### 2. 导入数据

```bash
# 全量导入（清空后重导）
python Graph/scripts/import_to_neo4j.py --clear

# 增量导入（保留已有数据）
python Graph/scripts/import_to_neo4j.py
```

### 3. 验证导入

```bash
python Graph/scripts/test_neo4j.py
```

## 🔗 知识图谱 Schema

### 节点类型

| 标签 | 说明 | 数量 |
|------|------|------|
| `Product` | 保险产品 / 药品 | 3,956 |
| `Disease` | 疾病百科 | 8,807 |
| `Medical` | 疾病(保险相关)/手术/治疗 | 8,924 |
| `Symptom` | 症状 | 5,998 |
| `CheckItem` | 检查项目 | 3,353 |
| `Org` | 养老机构 | 56,368 |
| `District` | 区/县 | 3,369 |
| `Treatment` | 治疗方式 | 544 |
| `Department` | 就诊科室 | 54 |
| `Benefit` | 保障项目 | 166 |
| `Exclusion` | 免责条款 | 177 |
| `Condition` | 合同条件 | 42 |
| `Service` | 服务类型 | 30 |
| `ProductCategory` | 保险类别 | 15 |
| `Eligibility` | 投保资格 | 11 |

### 关系类型

| 关系 | 说明 | 数量 |
|------|------|------|
| `CAN_BE_TREATED_BY` | 疾病可被药品治疗 (Disease → Product) | 59,738 |
| `TREATS_DISEASE` | 药品治疗疾病 (Product → Disease) | 59,738 |
| `HAS_SYMPTOM` | 疾病具有症状 (Disease/Medical → Symptom) | 54,695 |
| `REQUIRES_CHECK` | 疾病需要检查项目 (Disease → CheckItem) | 39,531 |
| `CURED_BY` | 疾病可采用治疗方式 (Disease → Treatment) | 21,049 |
| `COVERED_BY` | 疾病被保险产品承保 (Medical → Product) | 107 |
| `HAS_COMPLICATION` | 疾病引起并发症 (Disease → Disease) | 12,052 |
| `TREATED_AT` | 疾病就医科室 (Disease → Department) | 11,338 |
| `COVERS` | 保险产品保障项目 (Product → Benefit) | 275 |
| `HAS_EXCLUSION` | 保险产品免责条款 (Product → Exclusion) | 705 |
| `BELONGS_TO_CATEGORY` | 产品归属类别 (Product → ProductCategory) | 112 |
| `LOCATED_IN` | 机构所在区域 (Org → District) | 56,880 |
| `PROVIDES_SERVICE` | 机构提供服务 (Org → Service) | 56,775 |

### 跨域连接

| 跨域关系 | 说明 | 状态 | 数量 |
|---------|------|------|------|
| Medical → Product | 疾病被保险产品覆盖 | ✅ | 107条 |
| Product → Medical | 药品治疗疾病 | ✅ | 已实现 |
| Disease → Product | 疾病百科推荐药品 | ✅ | 59,738条 |
| Disease → Symptom | 疾病症状 | ✅ | 54,695条 |
| Benefit → Medical | 保障项目覆盖疾病 | ✅ | 55条 |
| Org → Product | 养老机构关联保险 | ⚠️ | 待完善 |

## 🏥 养老机构分类

养老机构按提供的服务类型分为10类：

| 服务类型 | 机构数量 | 占比 |
|---------|---------|------|
| 政府敬老服务 | 18,351 | 32.3% |
| 通用养老 | 17,889 | 31.5% |
| 机构养老 | 13,738 | 24.2% |
| 综合福利服务 | 2,712 | 4.8% |
| 专业护理 | 1,107 | 1.9% |
| 农村互助养老 | 979 | 1.7% |
| 社区养老 | 790 | 1.4% |
| 医养结合 | 663 | 1.2% |
| 康复服务 | 282 | 0.5% |
| 居家养老 | 264 | 0.5% |

## 📖 业务场景示例

```cypher
-- 场景1: 查询某疾病是否在保险范围内
MATCH (m:Medical)-[r:COVERED_BY]->(p:Product)
WHERE m.name CONTAINS '恶性肿瘤'
RETURN m.name as 疾病, p.name as 承保产品

-- 场景2: 查询疾病的症状（从疾病百科Disease）
MATCH (d:Disease {name: '肺泡蛋白质沉积症'})-[r:HAS_SYMPTOM]->(s:Symptom)
RETURN s.name as 症状

-- 场景3: 查询疾病可用的治疗药品
MATCH (d:Disease)-[r:CAN_BE_TREATED_BY]->(p:Product)
WHERE d.name = '冠心病'
RETURN d.name as 疾病, p.name as 药品

-- 场景4: 查询某年龄段可投保的产品
MATCH (p:Product)<-[e:ELIGIBILITY]-(elig:Eligibility)
WHERE e.age_min <= 30 AND e.age_max >= 30
RETURN p.name, e.age_min, e.age_max

-- 场景5: 查找医养结合的养老机构
MATCH (o:Org)-[:PROVIDES_SERVICE]->(s:Service {name: '医养结合'})
MATCH (o)-[:LOCATED_IN]->(d:District)
RETURN o.name, d.name

-- 场景6: 查询疾病的治疗方式
MATCH (d:Disease)-[r:CURED_BY]->(t:Treatment)
WHERE d.name CONTAINS '肺炎'
RETURN d.name, t.name

-- 场景7: 查询疾病需要的检查项目
MATCH (d:Disease)-[r:REQUIRES_CHECK]->(c:CheckItem)
WHERE d.name = '肺泡蛋白质沉积症'
RETURN d.name, c.name

-- 场景8: 查询某保险产品的保障项目和免责条款
MATCH (p:Product {name: '国寿康惠团体终身重大疾病保险（尊享版）'})
OPTIONAL MATCH (p)-[c:COVERS]->(b:Benefit)
OPTIONAL MATCH (p)-[e:HAS_EXCLUSION]->(ex:Exclusion)
RETURN p.name,
       collect(DISTINCT b.name) as benefits,
       collect(DISTINCT ex.name) as exclusions
```

## ⚙️ 配置

Neo4j 连接参数在 `scripts/import_to_neo4j.py` 头部配置：

```python
NEO4J_URI = "bolt://127.0.0.1:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "88888888"
NEO4J_DATABASE = "neo4j"
```

## 🔧 数据提取流程（数据库建立过程复现，导入数据库无需进行）

1. **原始数据** → 放入 `source/` 目录
2. **文本提取** → 运行 `scripts/extract_pdf_text_00_105.py`（仅限保险条款）
3. **LLM 提取** → 使用 `prompts/` 中的 V6 Prompt 指导 LLM 从文本中抽取三元组
4. **JSON 输出** → 提取结果保存为 JSON 三元组格式至 `db_data/*_v2/` 目录
5. **疾病数据转换** → 运行 `scripts/transform_medical_improved.py` 将 `source/medicine/medical.json` 转换为三元组
6. **Neo4j 导入** → 运行 `scripts/import_to_neo4j.py`
7. **验证测试** → 运行 `scripts/test_neo4j.py`

## 📝 更新日志

### v2.3 (2026-02-24)
- 新增疾病百科数据：8,807个Disease节点
- 新增症状、治疗方式、检查项目节点
- 建立疾病-药品关联：59,738条关系
- 新增跨域查询能力：疾病→保险、疾病→药品
- 节点总数：91,899
- 关系总数：597,563

### v2.2 (2026-02-23)
- 补充25个产品的ELIGIBILITY数据
- 补充24个产品的COVERS数据
- 修复产品名称错误和重复数据
- 清理无效节点
- ELIGIBILITY和COVERS覆盖率达到100%

### v2.1 (2026-02-21)
- 增强保障项目属性
- 添加报销比例、给付比例等属性

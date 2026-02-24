# 保险-药品-养老 知识图谱 (Insurance-Medicine-NursingHome Knowledge Graph)

基于 Neo4j 图数据库构建的跨域知识图谱，覆盖 **保险产品**、**创新药品** 和 **养老机构** 三大领域，通过自然实体关联和桥接关系实现跨域查询。

## 📊 数据规模

| 指标 | 数量 |
|------|------|
| 节点总数 | 60,527 |
| 关系总数 | 118,968 |
| 保险产品 | 105 |
| 养老机构 | 56,368 |
| 药品实体 | 28 |
| 疾病/医疗项目 | 300+ |
| 保障项目 | 400+ |
| 免责条款 | 600+ |

## 🎯 数据质量 (v2.2)

| 指标 | 覆盖率 |
|------|--------|
| ELIGIBILITY (投保条件) | **100.0%** (105/105) |
| COVERS (保障责任) | **100.0%** (105/105) |

**最近更新** (2026-02-23):
- ✅ 为25个产品补充了ELIGIBILITY数据
- ✅ 为24个产品补充了COVERS数据
- ✅ 修复产品名称错误和重复数据
- ✅ 清理无效节点

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
│   ├── Medicine_v2/                 # 药品三元组数据 (1 文件)
│   └── NursingHome_v2/              # 养老机构三元组数据 (1168 文件)
│
├── source/                          # 原始数据源
│   ├── insurance/                   # 保险条款文本
│   └── medicine_pdf/                # 药品目录 PDF
│
├── scripts/                         # Python 工具脚本
│   ├── import_to_neo4j.py           # Neo4j 导入脚本
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
| `Product` | 保险产品 / 药品 | 133 |
| `ProductCategory` | 保险类别 | - |
| `Benefit` | 保障项目 | 400+ |
| `Exclusion` | 免责条款 | 600+ |
| `Condition` | 合同条件（犹豫期等） | - |
| `Eligibility` | 投保资格 | - |
| `Medical` | 疾病/医疗项目 | 300+ |
| `Brand` | 药品商品名 | - |
| `Company` | 制药公司 | - |
| `Insurance` | 药品目录 | - |
| `Org` | 养老机构 | 56,368 |
| `District` | 区/县 | - |
| `Province` | 省/直辖市 | - |
| `Service` | 服务类型 | - |

### 关系类型

| 关系 | 说明 | 数量 |
|------|------|------|
| `COVERS` | 保险产品 → 保障项目 | 269 |
| `HAS_EXCLUSION` | 保险产品 → 免责条款 | 704 |
| `BELONGS_TO_CATEGORY` | 保险产品 → 产品类别 | 112 |
| `ELIGIBILITY` | 投保资格 → 保险产品 | 107 |
| `TREATS` | 药品 → 疾病 | - |
| `HAS_TRADE_NAME` | 药品 → 商品名 | - |
| `PRODUCED_BY` | 药品 → 制药公司 | - |
| `LOCATED_IN` | 养老机构 → 区域 | 56,880 |
| `PROVIDES_SERVICE` | 养老机构 → 服务类型 | 56,775 |
| `COVERED_BY` | 疾病 → 保险产品 | 107 |
| `COVERS_DISEASE` | 保障项目 → 疾病 | 55 |
| `COVERS_TREATMENT` | 保障项目 → 治疗 | 8 |

### 跨域连接

| 跨域关系 | 说明 | 状态 |
|---------|------|------|
| Medical → Product | 疾病被保险产品覆盖 | ✅ 107条 |
| Product → Medical | 药品治疗疾病 | ✅ 已实现 |
| Benefit → Medical | 保障项目覆盖疾病 | ✅ 55条 |
| Product → Service | 保险产品包含服务 | ✅ 34条 |
| Org → Product | 养老机构关联保险 | ⚠️ 待完善 |

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
-- 场景1: 查找覆盖某种疾病的保险产品
MATCH (m:Medical)-[r:COVERED_BY]->(p:Product)
WHERE m.name CONTAINS '恶性肿瘤'
RETURN p.name, m.name

-- 场景2: 查找治疗某种疾病的药品
MATCH (p:Product)-[r:TREATS]->(m:Medical)
WHERE m.name CONTAINS '白血病'
RETURN p.name, m.name

-- 场景3: 查找某年龄段可投保的产品
MATCH (p:Product)<-[e:ELIGIBILITY]-(elig:Eligibility)
WHERE e.age_min <= 30 AND e.age_max >= 30
RETURN p.name, e.age_min, e.age_max

-- 场景4: 查找医养结合的养老机构
MATCH (o:Org)-[:PROVIDES_SERVICE]->(s:Service {name: '医养结合'})
MATCH (o)-[:LOCATED_IN]->(d:District)
RETURN o.name, d.name

-- 场景5: 查找保险产品的保障项目和免责条款
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
5. **Neo4j 导入** → 运行 `scripts/import_to_neo4j.py`
6. **验证测试** → 运行 `scripts/test_neo4j.py`

## 📝 更新日志

### v2.2 (2026-02-23)
- 补充25个产品的ELIGIBILITY数据
- 补充24个产品的COVERS数据
- 修复产品名称错误和重复数据
- 清理无效节点
- ELIGIBILITY和COVERS覆盖率达到100%

### v2.1 (2026-02-21)
- 增强保障项目属性
- 添加报销比例、给付比例等属性
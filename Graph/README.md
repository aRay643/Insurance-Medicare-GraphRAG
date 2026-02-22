# 保险-药品-养老 知识图谱 (Insurance-Medicine-NursingHome Knowledge Graph)

基于 Neo4j 图数据库构建的跨域知识图谱，覆盖 **保险产品**、**创新药品** 和 **养老机构** 三大领域，通过自然实体关联和桥接关系实现跨域查询。

## 📊 数据规模

| 指标 | 数量 |
|------|------|
| 节点总数 | 60,515 |
| 关系总数 | 118,896 |
| 保险产品 | 128 |
| 养老机构 | 56,368 |
| 药品实体 | 128 (含品牌/公司) |
| 疾病实体 | 136 |
| 跨域路径 | 15,899 |

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

| 标签 | 说明 | 来源 |
|------|------|------|
| `Product` | 保险产品 / 药品 | 保险 + 药品 |
| `ProductCategory` | 保险类别（医疗/养老/护理等） | 保险 |
| `Benefit` | 保障项目 | 保险 |
| `Exclusion` | 免责条款 | 保险 |
| `Condition` | 合同条件（犹豫期等） | 保险 + 种子 |
| `Eligibility` | 投保资格 | 保险 |
| `Medical` | 疾病/适应症 | 保险 + 药品 |
| `Brand` | 药品商品名 | 药品 |
| `Company` | 制药公司 | 药品 |
| `Insurance` | 药品目录 | 药品 |
| `Org` | 养老机构 | 养老 |
| `District` | 区/县 | 养老 |
| `Province` | 省/直辖市 | 养老 |
| `Service` | 服务类型 | 养老 + 保险 |

### 关系类型

| 关系 | 说明 |
|------|------|
| `COVERS` | 保险产品 → 保障项目 |
| `HAS_EXCLUSION` | 保险产品 → 免责条款 |
| `BELONGS_TO_CATEGORY` | 保险产品 → 产品类别 |
| `ELIGIBILITY` | 保险产品 → 投保资格 |
| `TREATS` | 药品 → 疾病 |
| `HAS_TRADE_NAME` | 药品 → 商品名 |
| `PRODUCED_BY` | 药品 → 制药公司 |
| `LOCATED_IN` | 养老机构 → 区域 |
| `PROVIDES_SERVICE` | 养老机构 → 服务类型 |
| `SUITABLE_FOR` | 服务类型 → 保险类别（跨域桥接） |

### 跨域查询路径

```
养老机构(Org) →[PROVIDES_SERVICE]→ 服务(Service)
    →[SUITABLE_FOR]→ 保险类别(ProductCategory)
        ←[BELONGS_TO_CATEGORY]← 保险产品(Product)
```

## 📖 业务场景示例

```cypher
-- 场景1: 查找北京有医疗设施的养老机构
MATCH (o:Org)-[r:LOCATED_IN]->(d:District)-[:BELONGS_TO]->(p:Province {name: '北京市'})
WHERE r.has_medical_facility = true
RETURN o.name, d.name, r.bed_count
ORDER BY r.bed_count DESC LIMIT 10

-- 场景2: 查找治疗肺癌的药品及品牌
MATCH (p:Product)-[r:TREATS]->(m:Medical)
WHERE m.name CONTAINS '肺癌'
OPTIONAL MATCH (p)-[:HAS_TRADE_NAME]->(b:Brand)
RETURN p.name, b.name, r.indication_limit

-- 场景3: 跨域 - 为养老机构推荐保险产品
MATCH (o:Org)-[:PROVIDES_SERVICE]->(s:Service)
      -[:SUITABLE_FOR]->(pc:ProductCategory)
      <-[:BELONGS_TO_CATEGORY]-(p:Product)
WHERE o.name CONTAINS '护理'
RETURN DISTINCT o.name, s.name, pc.name, p.name
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

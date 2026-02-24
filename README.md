# Insurance+Medicare GraphRAG

基于知识图谱的保险问答系统 (GraphRAG)。支持从保险条款中提取实体与关系，并通过图谱检索增强问答质量。

## 系统架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Insurance+Medicare GraphRAG                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐              │
│  │  User   │────▶│   Web   │────▶│ FastAPI │────▶│  Neo4j  │              │
│  │ (Input) │     │   UI    │     │ Backend │     │ GraphDB │              │
│  └─────────┘     └─────────┘     └─────────┘     └─────────┘              │
│                                              │           │                   │
│                                              ▼           ▼                   │
│                                        ┌─────────┐   ┌─────────┐             │
│                                        │   LLM   │   │  Graph  │             │
│                                        │ Client  │   │ Engine  │             │
│                                        └─────────┘   └─────────┘             │
│                                              │                               │
│                                              ▼                               │
│                                        ┌─────────┐                         │
│                                        │ Prompt  │                         │
│                                        │ Builder │                         │
│                                        └─────────┘                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 本地开发部署（推荐）

### 前置要求

- Node.js >= 18
- Python >= 3.9
- pnpm (前端包管理器)
- Neo4j Desktop (图数据库)

### 步骤 1：安装前端环境

#### 第一步：确认 Node.js 是否安装

在终端中输入以下命令检查 Node.js 是否已安装：

```bash
npm -v
```

- 如果返回版本号（如 10.x.x）：说明 Node.js 已安装，继续第二步
- 如果报错"无法识别..."：需要先从 [Node.js 官网](https://nodejs.org/) 下载并安装长期支持版（LTS），安装完成后重启终端

#### 第二步：全局安装 pnpm

**Windows (PowerShell):**
```powershell
npm install -g pnpm
```

**macOS / Linux:**
```bash
npm install -g pnpm
```

#### 第三步：验证 pnpm 安装

```bash
pnpm -v
```

输出版本号即表示安装成功

#### 第四步：安装前端依赖

```bash
cd frontend
pnpm install
```

### 步骤 2：创建 Python 虚拟环境

```bash
# 在项目根目录创建虚拟环境
py -m venv Insurance-Medicare-Graphrag-venv

# 激活虚拟环境
# Windows:
Insurance-Medicare-Graphrag-venv\Scripts\activate
# macOS/Linux:
source Insurance-Medicare-Graphrag-venv/bin/activate

# 安装后端依赖
pip install -r mock/requirements.txt

# 安装图数据处理依赖
pip install -r Graph/requirements.txt
```

### 步骤 3：启动 Neo4j 数据库

推荐使用 Neo4j Desktop：

1. 下载并安装 [Neo4j Desktop](https://neo4j.com/download/)
2. 创建新数据库，设置密码为 `88888888`（或修改 `.env` 中的配置）
3. 启动数据库，确保 Bolt 端口为 `7687`

### 步骤 4：导入图谱数据（可选）

```bash
# 1. 解压数据文件到 Graph 文件夹
# 将项目根目录下的 db_data.zip 解压到 Graph/ 目录下（得到 Graph/db_data/）
# 注意：source.zip 不需要解压

# 2. 导入图谱数据
# 全量导入（清空后重导）
python Graph/scripts/import_to_neo4j.py --clear

# 增量导入（保留已有数据）
python Graph/scripts/import_to_neo4j.py

# 验证导入
python Graph/scripts/test_neo4j.py
```

### 步骤 5：配置环境变量

```bash
# 复制环境配置
cp .env.example .env
```

编辑 `.env` 文件，配置 Neo4j 连接：

```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=88888888
LLM_PROVIDER=mock
```

### 步骤 6：启动服务

```bash
# 终端1：启动后端（激活虚拟环境后）
python mock/graphrag-new2.py

# 终端2：启动前端
cd frontend
pnpm dev
```

### 步骤 7：访问

- 前端: http://localhost:5173
- 后端 API: http://localhost:8000
- Neo4j Browser: http://localhost:7474

## 数据库说明

### 数据规模 (v2.3)

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

### 数据质量

| 指标 | 覆盖率 |
|------|--------|
| ELIGIBILITY (投保条件) | **100.0%** (105/105) |
| COVERS (保障责任) | **100.0%** (105/105) |

### Schema 定义

#### 节点类型

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

#### 关系类型

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

#### 跨域连接

| 跨域关系 | 说明 | 状态 | 数量 |
|---------|------|------|------|
| Medical → Product | 疾病被保险产品覆盖 | ✅ | 107条 |
| Product → Medical | 药品治疗疾病 | ✅ | 已实现 |
| Disease → Product | 疾病百科推荐药品 | ✅ | 59,738条 |
| Disease → Symptom | 疾病症状 | ✅ | 54,695条 |
| Benefit → Medical | 保障项目覆盖疾病 | ✅ | 55条 |

详见 [Graph/README.md](Graph/README.md)

## 问答流程

```
┌──────────┐    ┌────────────┐    ┌──────────┐    ┌─────────┐    ┌─────────┐
│ Question │───▶│  Entity    │───▶│ Subgraph │───▶│ Prompt  │───▶│   LLM   │
│          │    │  Linker    │    │ Retrieval│    │ Builder │    │ Generate│
└──────────┘    └────────────┘    └──────────┘    └─────────┘    └─────────┘
                                             │                              │
                                             ▼                              ▼
                                      ┌────────────┐              ┌──────────────┐
                                      │   Graph    │              │   Answer    │
                                      │   (Neo4j) │              │ + Citations │
                                      └────────────┘              └──────────────┘
```

## Demo 示例问题

1. **70岁高血压能买XX护理险吗？**
2. **60岁老人可以购买哪些护理险？**
3. **糖尿病患者是否被XX医疗险承保？**

## 目录说明

```
Insurance-Medicare-GraphRAG/
├── frontend/               # React + TypeScript 前端 (Vite)
│   ├── src/
│   │   ├── pages/         # 页面组件 (Login, Chat)
│   │   ├── services/      # API 调用封装
│   │   ├── App.tsx        # 路由配置
│   │   └── main.tsx       # 入口文件
│   ├── package.json
│   ├── vite.config.ts     # Vite 配置（含 API 代理）
│   └── README.md
│
├── mock/                   # GraphRAG 后端服务
│   ├── graphrag-new2.py   # 后端服务脚本（含本地模板兜底）
│   ├── requirements.txt   # Python 依赖
│   └── .env              # 环境配置
│
├── Graph/                  # 知识图谱数据与处理
│   ├── db_data/           # 图谱数据 (JSON 三元组)
│   ├── prompts/           # LLM 提取 Prompt
│   ├── scripts/           # 导入脚本
│   ├── requirements.txt   # Python 依赖
│   └── README.md
│
├── Insurance-Medicare-Graphrag-venv/  # Python 虚拟环境
│
├── .env.example
└── README.md
```

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| POST | `/api/v1/chat` | 问答接口（返回答案 + 图谱证据） |
| POST | `/subgraph` | 图谱三元组查询 |

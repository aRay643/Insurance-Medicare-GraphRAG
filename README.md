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
- Python >= 3.10
- pnpm (前端包管理器)

### 步骤 1：安装前端依赖

```bash
cd frontend
pnpm install
```

### 步骤 2：创建后端 Python 虚拟环境

```bash
# 在项目根目录创建虚拟环境
python3 -m venv Insurance-Medicare-GraphRAG-venv

# 激活虚拟环境
source Insurance-Medicare-GraphRAG-venv/bin/activate  # macOS/Linux
# 或
Insurance-Medicare-GraphRAG-venv\Scripts\activate      # Windows

# 安装后端依赖
pip install -r backend/requirements.txt
```

> 注意：讯飞星火 LLM API 配置位于 `mock/graphrag-new2.py` 第 17-18 行，需要替换为你的 API Key 和 Secret。

### 步骤 3：启动服务

```bash
# 终端1：启动后端
source Insurance-Medicare-GraphRAG-venv/bin/activate
python mock/graphrag-new2.py

# 终端2：启动前端
cd frontend
pnpm dev
```

### 步骤 4：访问

- 前端: http://localhost:5173
- 后端 API: http://localhost:8000

## Docker 部署（可选）

如果需要完整版（包含 Neo4j 图数据库）：

```bash
# 1. 复制环境配置
cp .env.example .env

# 2. 启动后端服务 (Neo4j + Backend)
cd deploy
docker compose up --build

# 3. 启动前端 (新终端)
cd frontend
pnpm install
pnpm dev
```

访问：
- 前端: http://localhost:5173
- API文档: http://localhost:8000/docs
- Neo4j Browser: http://localhost:7474

## 快速导入样例图谱

```bash
cd kg/scripts
python make_sample_data.py  # 生成样例数据
python load_neo4j.py --uri bolt://localhost:7687 --user neo4j --password your_password
```

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
├── backend/                # FastAPI 后端服务
│   ├── app/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── docker-compose.yml
│   └── README.md
│
├── mock/                   # GraphRAG Mock 服务（本地开发用）
│   └── graphrag-new2.py   # Mock 服务脚本（含本地模板兜底）
│
├── kg/                     # 图谱构建与导入
│   ├── scripts/
│   │   ├── make_sample_data.py  # 生成样例数据
│   │   ├── validate_data.py     # 数据验证
│   │   └── load_neo4j.py        # 导入 Neo4j
│   └── README.md
│
├── docs/                   # 文档
│   ├── api_contract.md    # API 契约
│   ├── ontology.md         # 本体定义
│   ├── data_contract.md   # 数据格式
│   ├── acceptance.md      # 验收标准
│   └── eval_questions.json# 评估问题集
│
├── deploy/                 # 部署配置
│   ├── docker-compose.yml
│   └── README.md
│
├── scripts/                # 脚本工具
│   └── run_demo.py        # 批量测试
│
├── Insurance-Medicare-GraphRAG-venv/  # Python 虚拟环境（本地开发用）
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

详见 [docs/api_contract.md](docs/api_contract.md)

# 医保健康管理问答系统 - 前端

## 环境要求

- Node.js >= 18
- pnpm (推荐) 或 npm

## 快速启动

```bash
# 1. 进入前端目录
cd frontend

# 2. 安装依赖
pnpm install

# 3. 启动开发服务器
pnpm dev
```

访问 http://localhost:5173

## 项目结构

```
frontend/
├── src/
│   ├── pages/
│   │   ├── Login.tsx    # 登录页
│   │   └── Chat.tsx    # 对话页
│   ├── services/
│   │   └── api.ts      # API 调用
│   ├── App.tsx         # 路由配置
│   └── main.tsx        # 入口文件
├── package.json
└── vite.config.ts
```

## 常用命令

| 命令 | 说明 |
|------|------|
| pnpm dev | 启动开发服务器 |
| pnpm build | 构建生产版本 |
| pnpm preview | 预览生产版本 |

## 注意事项

- 后端 API 地址: http://localhost:8000
- 确保后端已启动后再使用对话功能

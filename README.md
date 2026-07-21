# Growth Atlas

Growth Atlas V2 是一个面向重要人生选择的个人决策系统。它帮助用户澄清目标、区分事实与假设、比较方案、形成行动，并在后续反馈中逐步沉淀个人决策模型。

它不是心理治疗工具，也不替用户做最终决定。AI 生成的分析和报告在用户确认前都只是可审阅草稿。

## 当前状态

项目正从 V1 的“反思与成长记录”迁移到 V2 的“决策闭环”。当前代码已经包含：

- React 前端与 Supabase 登录、个人档案；
- FastAPI 后端、档案与反思接口；
- V2 决策事件的创建、读取、更新与状态流转；
- 可审阅的 AI 决策报告草稿与 V2 数据库基础；
- 兼容期内保留的 V1 数据表和页面。

## 先从这里读

- 产品方向与 V2 定位：[`PRODUCT_PIVOT.md`](PRODUCT_PIVOT.md)
- MVP 范围与验收边界：[`MVP_SPEC.md`](MVP_SPEC.md)
- 软件架构：[`ARCHITECTURE.md`](ARCHITECTURE.md)
- AI 行为契约：[`AI_CONVERSATION.md`](AI_CONVERSATION.md)
- V2 数据库与迁移：[`supabase/V2_DATABASE.md`](supabase/V2_DATABASE.md)
- Beta 部署、RLS 与完整旅程验收：[`docs/BETA_DEPLOYMENT.md`](docs/BETA_DEPLOYMENT.md)
- 面向贡献者和 AI 的短规则：[`AGENTS.md`](AGENTS.md)

`docs/knowledge_base/` 保存产品、理论和创始人背景资料；上面的 Markdown 契约与数据库迁移是日常开发入口。

## 本地启动

### 1. 后端

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

服务地址为 `http://localhost:8000`：

- `/api/health`：进程是否可访问；
- `/api/ready`：AI 与 Supabase 依赖是否已配置，不返回任何密钥；
- `/docs`：交互式 API 文档。

### 2. 前端

```powershell
cd frontend
pnpm install
Copy-Item .env.example .env
pnpm dev
```

默认访问地址为 `http://localhost:5173`。

### 3. 数据库

按文件名顺序应用 `supabase/migrations/`。不要修改已经应用过的迁移；新的数据库变更应新增迁移。详情见 [`supabase/README.md`](supabase/README.md)。

## 验证

在项目根目录运行统一检查：

```powershell
.\scripts\check.ps1
```

它依次执行后端 lint、后端测试和前端类型检查/生产构建。任一步失败都会停止并给出明确错误；只有全部通过才输出成功。

## 安全边界

- `KIMI_API_KEY`、Supabase service-role key 等服务端密钥不得进入前端或版本控制。
- 前端只使用 `VITE_SUPABASE_ANON_KEY` 等可公开配置。
- 用户数据访问必须保留用户身份校验和 Supabase RLS 边界。
- 医疗、法律、投资及紧急危险情境必须保留专业求助提示和人工决策点。

# Growth Atlas Backend

## 本地启动

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
# 编辑 .env，设置 Supabase 与 KIMI_API_KEY
uvicorn app.main:app --reload
```

健康检查地址：`http://localhost:8000/api/health`

基础业务接口：

- `POST /api/profile`：提交用户成长档案
- `POST /api/reflection`：提交问题反思记录
- `POST /api/reflection/analyze`：调用 OpenAI 返回结构化决策报告（不保存数据）
- `GET /api/report`：获取模拟成长报告，可选传入 `user_id` 查询参数

AI 模型可通过 `.env` 中的 `KIMI_MODEL` 调整；超时与结构化输出尝试次数由
`AI_TIMEOUT_SECONDS` 和 `AI_OUTPUT_ATTEMPTS` 控制。API Key 只放在后端
`backend/.env`，不要使用 `VITE_` 前缀，也不要提交到版本控制。

# Document Desensitizer MVP

一个可容器化的文档脱敏服务 MVP，支持上传 txt / md / docx / xlsx 文件，按规则执行脱敏，输出脱敏文件与 JSON 审计报告。

## 当前支持
- txt
- md
- docx
- xlsx

## 当前脱敏能力
- 手机号
- 邮箱
- 身份证号
- 银行卡号
- 自定义词典关键词

## 当前输出
- 脱敏后的原格式文件
- JSON 审计报告
- ZIP 打包结果（文件 + 报告）

## 明确限制
- 不支持 pdf / 图片 / 扫描件 / OCR
- docx 已补跨 run 合并处理，但会牺牲部分细粒度 run 样式保留
- xlsx 不处理公式单元格、宏、图表
- 未做异步任务队列，当前为同步处理

## 启动方式

### 本地 Python
```bash
cd /root/.openclaw/workspace/projects/desensitize_service
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Docker Compose
```bash
cd /root/.openclaw/workspace/projects/desensitize_service
docker compose up --build
```

## 测试
```bash
cd /root/.openclaw/workspace/projects/desensitize_service
pytest
```

## 接口
- `GET /healthz` 健康检查
- `GET /` 极简上传页
- `POST /api/v1/desensitize` 上传并处理文件（配置 `API_KEY` 后需携带 `x-api-key` 请求头）
- `GET /api/v1/files/{filename}` 下载脱敏文件
- `GET /api/v1/reports/{filename}` 查看 JSON 报告
- `GET /api/v1/bundles/{filename}` 下载 ZIP 打包结果
- `GET /api/v1/desensitize/download/{task_id}` 按任务 ID 直接下载 ZIP

## 规则配置
- `config/rules.yaml`
- `config/dictionaries/*.txt`

修改规则后，重启服务生效。

## 交付文档
- `DEPLOYMENT.md`：部署与验证步骤
- `CHANGELOG.md`：当前版本变更记录
- `PRODUCTION_NOTES.md`：生产注意事项与风险说明

## GitHub 自动构建镜像
仓库已补充 GitHub Actions 工作流：
- `.github/workflows/docker-image.yml`

默认行为：
- push 到 `main` 自动构建并推送镜像
- 打 tag（如 `v0.1.0`）自动构建并推送镜像
- 镜像仓库默认推送到：`ghcr.io/<github-owner>/desensitize-service`

常见镜像 tag：
- `latest`
- `main`
- `sha-xxxxxxx`
- `v0.1.0`

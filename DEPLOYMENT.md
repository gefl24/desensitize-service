# DEPLOYMENT.md

## 1. 项目路径
`/root/.openclaw/workspace/projects/desensitize_service`

## 2. 本地运行
```bash
cd /root/.openclaw/workspace/projects/desensitize_service
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 3. Docker Compose 运行
```bash
cd /root/.openclaw/workspace/projects/desensitize_service
docker compose up --build -d
```

查看日志：
```bash
docker compose logs -f
```

停止服务：
```bash
docker compose down
```

## 4. 健康检查
- URL: `GET /healthz`
- 成功返回：
```json
{"status":"ok"}
```

## 5. 环境变量
在 `docker-compose.yml` 中可配置：

- `TZ=Asia/Shanghai`
- `API_KEY=`

说明：
- 当 `API_KEY` 为空时，上传接口默认不鉴权
- 当 `API_KEY` 有值时，请求 `POST /api/v1/desensitize` 必须带请求头：
  - `x-api-key: <你的值>`

## 6. 挂载目录
Compose 默认挂载：
- `./logs -> /app/logs`

说明：若宿主机日志目录权限不足，服务会自动降级到 stdout 输出日志，不再因日志文件权限导致启动失败。

说明：若 `uploads` / `outputs` / `logs` 挂载目录不可写，服务会自动降级到容器内 `/tmp/desensitize_service/<dir>`，优先保证服务可用与验证可继续。
- `./config -> /app/config`
- `./uploads -> /app/uploads`
- `./outputs -> /app/outputs`

说明：ZIP 打包结果也输出到 `/app/outputs`，不再额外创建子目录。

## 7. 配置规则
规则文件位置：
- `config/rules.yaml`
- `config/dictionaries/*.txt`

修改规则后，建议重启服务：
```bash
docker compose restart
```

## 8. 验证步骤
### 8.1 接口健康验证
```bash
curl http://localhost:8000/healthz
```

### 8.2 Swagger 页面
打开：
- `http://localhost:8000/docs`

### 8.3 上传验证
可通过网页：
- `http://localhost:8000/`

或通过 curl：
```bash
curl -X POST 'http://localhost:8000/api/v1/desensitize' \
  -H 'x-api-key: your-key-if-needed' \
  -F 'file=@tests/sample_input.txt'
```

## 9. 输出结果
接口成功后会返回：
- 脱敏文件下载地址
- JSON 报告地址
- ZIP 打包下载地址
- task_id

## 10. 已知限制
- 不支持 pdf / 图片 / OCR
- docx 跨 run 已做合并处理，但会牺牲部分细粒度样式
- xlsx 跳过公式单元格、宏、图表
- 当前为同步处理，未引入任务队列

## 11. GitHub / GHCR 部署方式
当仓库推到 GitHub 后，可使用 GitHub Actions 自动构建镜像并推送到 GHCR：
- 工作流文件：`.github/workflows/docker-image.yml`
- 默认镜像地址：`ghcr.io/<github-owner>/desensitize-service`

部署侧拉取示例：
```bash
docker pull ghcr.io/<github-owner>/desensitize-service:latest
```

运行示例：
```bash
docker run -d \
  --name desensitizer-api \
  -p 8000:8000 \
  -e TZ=Asia/Shanghai \
  -e API_KEY=your-key \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/uploads:/app/uploads \
  -v $(pwd)/outputs:/app/outputs \
  ghcr.io/<github-owner>/desensitize-service:latest
```

## 12. 回滚方式
如果本次部署异常：
1. 回退代码目录到上一个稳定版本，或切换到上一个镜像 tag
2. 重新执行：
```bash
docker compose up --build -d
```
或：
```bash
docker run ... ghcr.io/<github-owner>/desensitize-service:<previous-tag>
```
3. 用 `/healthz` 和上传样例重新验证

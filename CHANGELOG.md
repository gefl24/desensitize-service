# CHANGELOG.md

## v0.1.0-mvp

### Added
- FastAPI 服务入口与极简上传页
- `/healthz` 健康检查
- txt / md / docx / xlsx 文件脱敏主链路
- 正则脱敏：手机号、邮箱、身份证、银行卡
- 词典脱敏能力（FlashText）
- JSON 审计报告输出
- ZIP 打包输出
- 文件签名校验（docx/xlsx）
- 24 小时过期文件清理
- API Key 鉴权开关
- pytest 基础测试、API 集成测试、docx 跨 run 测试

### Changed
- docx 从单 run 处理调整为按段落合并后处理，解决跨 run 命中问题
- 健康检查从 `/docs` 逻辑改为独立 `/healthz`

### Known Issues
- docx 细粒度 run 样式保留有限
- 尚未加入限流与异步任务队列
- 尚未完成实际构建、测试执行与 git 提交验证

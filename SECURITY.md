# Security Policy

## Reporting

请不要在公开 Issue 中提交 API Key、企业微信 Secret、Token、EncodingAESKey 或可利用的代码执行细节。

## Execution Risk

SWE2 会在 Docker 或本地仓库中执行模型生成的命令。请仅在可信仓库和受控环境中运行。

生产部署建议：

- 使用 Docker 隔离。
- 限制公网回调服务访问。
- 使用固定出口 IP。
- 保留 Git 提交和离线备份。
- 定期轮换 API Key 和企业微信密钥。

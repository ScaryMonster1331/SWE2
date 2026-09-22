# SWE2

SWE2 是一个面向真实代码仓库的软件工程智能体。它将大语言模型、工具调用、Docker 沙箱、执行反馈和补丁生成组合起来，用于完成代码修复、需求实现和自动化软件工程任务。

## 核心能力

- 使用 DeepSeek 或其他 LiteLLM 支持的模型执行软件工程任务。
- 在 Docker 隔离环境中读取、搜索、修改和验证代码。
- 自动保存完整 trajectory、日志和 patch。
- 支持本地 Git 仓库直接生成补丁。
- 支持企业微信审批需求自动读取、群通知和本地补丁执行。
- 提供 Web Inspector 查看模型思考、工具调用和最终补丁。
- 保持命令行、Python 配置和工具 Bundle 的可扩展性。

## 工作流程

```text
需求或问题描述
    ↓
模型分析仓库
    ↓
Docker 中搜索代码并执行命令
    ↓
修改源码并运行验证
    ↓
生成 patch
    ↓
保存 trajectory、日志和结果
```

企业微信需求模式：

```text
审批通过
  ↓
按审批编号读取申请内容
  ↓
推送到“需求通知”群
  ↓
生成本地 problem_statement
  ↓
执行 SWE2 补丁流程
```

## 环境要求

- Windows 10/11、macOS 或 Linux
- Python 3.11 或 3.12
- Docker Desktop 或兼容的 Docker 环境
- DeepSeek API Key
- 可选：企业微信自建应用和群机器人

## 安装

```powershell
git clone https://github.com/ScaryMonster1331/SWE2.git
cd SWE2

py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip setuptools wheel
python -m pip install --editable .
```

构建默认 Docker 运行镜像：

```powershell
docker build -f Dockerfile.runtime -t swe2-runtime:3.11 .
```

## 配置

复制环境变量模板：

```powershell
Copy-Item .env.example .env
```

填写模型密钥：

```dotenv
DEEPSEEK_API_KEY=你的DeepSeekKey
```

企业微信相关配置：

```dotenv
WECOM_CORP_ID=
WECOM_CORP_SECRET=
WECOM_WEBHOOK_KEY=
WECOM_CALLBACK_TOKEN=
WECOM_ENCODING_AES_KEY=
```

默认模型和工作流配置位于：

```text
config/default.yaml
config/deepseek_flash.yaml
config/requirements.example.yaml
```

## 运行单个任务

```powershell
swe2 run `
  --config config/default.yaml `
  --config config/deepseek_flash.yaml `
  --env.repo.path=D:\path\to\repository `
  --problem_statement.path=problem.md
```

也可以继续使用兼容命令：

```powershell
sweagent run ...
```

## 企业微信审批需求

复制配置模板：

```powershell
Copy-Item config\requirements.example.yaml config\requirements.yaml
```

在 `config\requirements.yaml` 中设置本地目标仓库：

```yaml
repository:
  path: D:/path/to/your/repository
```

检查审批内容：

```powershell
swe2 requirements inspect --approval-id "审批编号"
```

推送到需求通知群：

```powershell
swe2 requirements sync --approval-id "审批编号"
```

执行本地补丁流程：

```powershell
swe2 requirements run --approval-id "审批编号"
```

一步完成通知和补丁：

```powershell
swe2 requirements process --approval-id "审批编号"
```

## Web 轨迹查看器

```powershell
swe2 inspector --directory trajectories --port 8000
```

访问：

```text
http://127.0.0.1:8000
```

## 项目结构

```text
SWE2/
├── sweagent/              核心 Python 包
├── config/                模型、Agent 和需求工作流配置
├── tools/                 工具 Bundle
├── .runtime-tools/        Linux LF 格式工具副本
├── docs/                  项目文档
├── tests/                 测试
├── Dockerfile.runtime      运行沙箱镜像
└── pyproject.toml         Python 包元数据
```

## Cloudflare 测试隧道

如果仅使用本地电脑，可运行：

```powershell
.\install_cloudflared.ps1
.\start_wecom_tunnel.ps1
```

脚本会启动本地回调服务并输出企业微信接收消息服务器 URL。
## 安全说明

- 模型生成的代码会在 Docker 或本地仓库中执行。
- 不要将 `.env`、Token、Secret 或企业微信密钥提交到 Git。
- 公网回调服务应使用 HTTPS。
- 生产环境建议使用固定域名和固定出口 IP。
- 自动修改代码前应保留 Git 提交或备份。

## License

MIT。完整许可文本见 `LICENSE`。


jjy
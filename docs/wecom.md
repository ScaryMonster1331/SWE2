# 企业微信需求流程

## 流程

```text
审批通过
  ↓
swe2 requirements inspect
  ↓
swe2 requirements sync
  ↓
swe2 requirements run
  ↓
生成本地补丁
```

## 必需配置

```dotenv
WECOM_CORP_ID=
WECOM_CORP_SECRET=
WECOM_WEBHOOK_KEY=
```

如果使用接收消息服务器验证：

```dotenv
WECOM_CALLBACK_TOKEN=
WECOM_ENCODING_AES_KEY=
```

## 命令

```powershell
swe2 requirements inspect --approval-id "审批编号"
swe2 requirements sync --approval-id "审批编号"
swe2 requirements run --approval-id "审批编号"
swe2 requirements process --approval-id "审批编号"
```

## 本地回调服务

```powershell
python wecom_callback_server.py
```

或使用：

```powershell
.\start_wecom_tunnel.ps1
```

公网隧道适合测试。生产环境建议使用固定域名、HTTPS 和固定出口 IP。

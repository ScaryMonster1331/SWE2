# Contributing

欢迎提交问题和改进。

## 开发环境

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --editable ".[dev]"
```

## 提交前检查

```powershell
python -m pytest tests -q
python -m compileall -q sweagent
```

请勿提交 `.env`、API Key、企业微信 Secret、轨迹文件或本地运行产物。

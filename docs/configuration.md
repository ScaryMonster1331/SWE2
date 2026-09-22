# 配置说明

主要配置位于 `config/`。

## 默认 Agent

`config/default.yaml` 定义：

- Prompt 模板
- Bash 工具
- 编辑工具
- 提交工具
- Function Calling 解析器

## DeepSeek

`config/deepseek_flash.yaml` 使用：

```yaml
agent:
  model:
    name: deepseek/deepseek-flash
```

并指定 Docker 沙箱镜像：

```yaml
env:
  deployment:
    image: swe2-runtime:3.11
```

## 企业微信需求

`config/requirements.example.yaml` 定义：

- 企业微信环境变量名称
- 审批字段匹配规则
- 本地目标仓库
- 状态文件和输出目录

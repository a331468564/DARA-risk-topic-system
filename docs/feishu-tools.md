# 飞书 CLI / MCP 工具

工具安装在 E 盘，不依赖本仓库内的 `node_modules`。

## 安装位置

| 工具 | 版本 | 路径 |
| --- | --- | --- |
| `@larksuite/cli` | `1.0.48` | `E:\DARA-tools\lark-cli` |
| `@larksuiteoapi/lark-mcp` | `0.5.1` | `E:\DARA-tools\lark-mcp` |
| npm cache | - | `E:\DARA-tools\npm-cache` |
| wrapper | - | `E:\DARA-tools\bin` |

## CLI

使用隔离配置的 wrapper：

```powershell
& 'E:\DARA-tools\bin\lark-cli-e.cmd' config show
```

CLI 配置位置：

```text
E:\DARA-tools\lark-cli-home\.lark-cli\hermes\config.json
```

验证风险 Base：

```powershell
& 'E:\DARA-tools\bin\lark-cli-e.cmd' api GET '/open-apis/bitable/v1/apps/Dq83bus70asgLAs1OwNcluWsnke/tables'
```

## MCP

MCP secret 配置文件在 E 盘，不提交到 GitHub：

```text
E:\DARA-tools\lark-mcp\config\dara-risk-mcp.json
```

该配置使用：

```text
tools = preset.base.default
tokenMode = tenant_access_token
mode = stdio
```

只启用飞书 Base / 多维表格相关工具，不启用 IM、Docs、Calendar 等能力。

### Stdio 模式

适合配置到支持 MCP 的 Agent 客户端：

```json
{
  "mcpServers": {
    "lark-risk-base": {
      "command": "E:\\DARA-tools\\bin\\lark-mcp-e.cmd",
      "args": [
        "mcp",
        "--config",
        "E:\\DARA-tools\\lark-mcp\\config\\dara-risk-mcp.json"
      ]
    }
  }
}
```

### 临时 Streamable HTTP 验证

```powershell
& 'E:\DARA-tools\bin\lark-mcp-e.cmd' mcp --config 'E:\DARA-tools\lark-mcp\config\dara-risk-mcp.json' --mode streamable --host localhost --port 3030
```

启动成功后 endpoint：

```text
http://localhost:3030/mcp
```

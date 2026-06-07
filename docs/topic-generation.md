# Topic Generation Writeback

This step turns verified risk-material records into first-pass topic drafts for manual review in Feishu.

## What It Writes

`scripts/generate_topics.py` fills these Feishu fields:

- `老板视角`
- `可写选题`
- `短视频开头`
- `公众号标题`
- `处理状态` = `待人工验证`

By default, the script only updates records that:

- have no existing `可写选题`
- have at least one of `风险类型` or `风险信号`

## Recommended First Pass

Start with verified evidence records only:

```powershell
& 'E:\DARA-tools\risk-source-tester\.venv\Scripts\python.exe' scripts\generate_topics.py --evidence-level A --dry-run
```

Write them to Feishu:

```powershell
& 'E:\DARA-tools\risk-source-tester\.venv\Scripts\python.exe' scripts\generate_topics.py --evidence-level A
```

After writing, the same dry-run should return `records_to_update: 0`.

## Other Modes

Preview a small sample:

```powershell
& 'E:\DARA-tools\risk-source-tester\.venv\Scripts\python.exe' scripts\generate_topics.py --limit 5 --dry-run
```

Overwrite existing generated fields:

```powershell
& 'E:\DARA-tools\risk-source-tester\.venv\Scripts\python.exe' scripts\generate_topics.py --evidence-level A --force
```

## CLI Verification

Use the E-drive Feishu CLI wrapper to inspect a record:

```powershell
& 'E:\DARA-tools\bin\lark-cli-e.cmd' api GET '/open-apis/bitable/v1/apps/Dq83bus70asgLAs1OwNcluWsnke/tables/tbliLiUQsl8rhAOr/records/<record_id>'
```

## MCP Note

The local MCP wrapper is installed at:

```text
E:\DARA-tools\bin\lark-mcp-e.cmd
```

This Codex session does not expose the Feishu MCP server as a direct callable tool. The MCP service can still be started from the E-drive wrapper and attached by an MCP-capable client using the config documented in `docs/feishu-tools.md`.

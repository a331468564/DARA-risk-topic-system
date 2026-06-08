# Risk CLI

`scripts/risk.py` is the thin command entry for the MVP workflow. It reuses the existing data-source, import, and topic-generation scripts instead of replacing them.

## Commands

### Manual Add

Preview one manually collected material:

```powershell
& 'E:\DARA-tools\risk-source-tester\.venv\Scripts\python.exe' scripts\risk.py add `
  --title '关于公司新增债务逾期的公告' `
  --url 'https://example.com/a.pdf' `
  --company '样例公司' `
  --risk-type '债务风险' `
  --risk-signal '债务逾期' `
  --dry-run
```

Remove `--dry-run` to write it to Feishu.

### Import

Import the latest local XLSX/CSV table:

```powershell
& 'E:\DARA-tools\risk-source-tester\.venv\Scripts\python.exe' scripts\risk.py import --dry-run
```

### Generate Topics

Generate first-pass topic fields for verified evidence records:

```powershell
& 'E:\DARA-tools\risk-source-tester\.venv\Scripts\python.exe' scripts\risk.py generate --evidence-level A --dry-run
```

### Manual Verification

Preview a manual status update:

```powershell
& 'E:\DARA-tools\risk-source-tester\.venv\Scripts\python.exe' scripts\risk.py verify recxxxxxxxxxxxx --status 已采用 --note 人工确认可写 --dry-run
```

Remove `--dry-run` to write `处理状态` and optional `备注` back to Feishu.

Recommended status values:

- `待人工验证`
- `需修改`
- `已采用`
- `暂不采用`

### Daily Report

Print a text report:

```powershell
& 'E:\DARA-tools\risk-source-tester\.venv\Scripts\python.exe' scripts\risk.py report --top 5
```

Print JSON:

```powershell
& 'E:\DARA-tools\risk-source-tester\.venv\Scripts\python.exe' scripts\risk.py report --format json
```

The report includes:

- total material count
- source distribution
- risk-type distribution
- records waiting for manual verification
- top writeable topics

## MCP Check

The Feishu MCP connection can directly list fields and search records for this Base. In this Codex session, MCP access was verified against:

```text
app_token = Dq83bus70asgLAs1OwNcluWsnke
table_id = tbliLiUQsl8rhAOr
```

The production scripts still use OpenAPI because that path is stable for scheduled jobs and CLI execution.

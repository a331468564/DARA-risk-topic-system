# DARA Risk Topic System

企业老板风险管理选题库 MVP。

当前目标是先验证低成本数据源是否能稳定产出风险素材，并把素材整理成本地表格，为后续迁移到飞书多维表做准备。

## 当前数据源

- 36氪官方 RSS：创业、融资、科技公司线索
- 华尔街见闻 RSSHub：宏观、行业、资本市场风险
- 格隆汇快讯 RSSHub：市场快讯，临时代替财联社
- 巨潮资讯公告接口：上市公司硬风险公告

## 本地工具位置

Python 虚拟环境和依赖安装在 E 盘：

```powershell
E:\DARA-tools\risk-source-tester\.venv
```

## 运行数据源测试

```powershell
& 'E:\DARA-tools\risk-source-tester\.venv\Scripts\python.exe' scripts\test_sources.py --rss-limit 20 --cninfo-limit 5
```

输出目录：

```text
data/source_tests/
```

字段说明见：

```text
docs/local-table-fields.md
```

## 飞书风险库

已创建专用飞书多维表：

```text
config/feishu_risk.json
```

本仓库只保存风险库的 Base token 和 Table ID，不保存 `FEISHU_APP_SECRET`。本地凭证请放在环境变量或 `.env` 中，参考：

```text
.env.example
```

飞书 CLI / MCP 工具安装和使用说明见：

```text
docs/feishu-tools.md
```

## 导入飞书

先 dry-run：

```powershell
& 'E:\DARA-tools\risk-source-tester\.venv\Scripts\python.exe' scripts\feishu_import.py data\source_tests\risk_materials_local_20260607_174123.xlsx --dry-run
```

确认数量后导入：

```powershell
& 'E:\DARA-tools\risk-source-tester\.venv\Scripts\python.exe' scripts\feishu_import.py data\source_tests\risk_materials_local_20260607_174123.xlsx
```

导入脚本按 `去重键` 跳过已存在记录。

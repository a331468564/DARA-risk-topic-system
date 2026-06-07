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

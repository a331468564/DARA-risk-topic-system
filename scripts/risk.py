from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import feishu_import  # noqa: E402
import generate_topics  # noqa: E402
from feishu_setup import FeishuClient  # noqa: E402


def clean_text(value: Any) -> str:
    return str(value or "").strip()


def load_client_and_config() -> tuple[FeishuClient, dict[str, str]]:
    app_id = os.environ.get("FEISHU_APP_ID")
    app_secret = os.environ.get("FEISHU_APP_SECRET")
    if not app_id or not app_secret:
        raise SystemExit("FEISHU_APP_ID and FEISHU_APP_SECRET are required in environment variables.")
    return FeishuClient(app_id=app_id, app_secret=app_secret), feishu_import.load_feishu_config()


def build_manual_record(
    *,
    title: str,
    url: str,
    source: str = "手动录入",
    risk_type: str = "",
    risk_signal: str = "",
    company: str = "",
    summary: str = "",
    evidence_level: str = "C",
    note: str = "",
) -> dict[str, dict[str, str]]:
    today = datetime.now().strftime("%Y-%m-%d")
    fields = {
        "记录日期": today,
        "来源": source,
        "来源类型": "manual",
        "素材层级": "证据池" if evidence_level == "A" else "线索池",
        "原始标题": clean_text(title),
        "原文链接": clean_text(url),
        "发布时间": today,
        "原始摘要": clean_text(summary or title),
        "涉及企业": clean_text(company),
        "涉及人物": "",
        "风险类型": clean_text(risk_type),
        "风险信号": clean_text(risk_signal),
        "风险关键词": clean_text(risk_signal),
        "核验状态": "已核验" if evidence_level == "A" else "未核验",
        "处理状态": "待加工",
        "证据等级": clean_text(evidence_level),
        "证据链接": clean_text(url),
        "去重键": clean_text(url) or f"{source}:{clean_text(title)}",
        "备注": clean_text(note),
    }
    return {"fields": {key: value for key, value in fields.items() if value != ""}}


def build_verify_update(record_id: str, status: str, note: str = "") -> dict[str, Any]:
    fields = {"处理状态": clean_text(status)}
    if clean_text(note):
        fields["备注"] = clean_text(note)
    return {"record_id": record_id, "fields": fields}


def summarize_records(records: list[dict[str, Any]], top: int = 5) -> dict[str, Any]:
    by_source: Counter[str] = Counter()
    by_risk_type: Counter[str] = Counter()
    writeable_topics: list[dict[str, str]] = []
    needs_verification = 0

    for record in records:
        fields = record.get("fields", {})
        source = clean_text(fields.get("来源", "未标注"))
        risk_type = clean_text(fields.get("风险类型", "未分类"))
        status = clean_text(fields.get("处理状态", ""))
        topic = clean_text(fields.get("可写选题", ""))
        title = clean_text(fields.get("原始标题", ""))

        by_source[source] += 1
        by_risk_type[risk_type] += 1
        if status == "待人工验证":
            needs_verification += 1
        if topic:
            writeable_topics.append(
                {
                    "record_id": clean_text(record.get("record_id") or record.get("id")),
                    "topic": topic,
                    "title": title,
                    "risk_type": risk_type,
                    "status": status,
                }
            )

    return {
        "total": len(records),
        "by_source": dict(by_source),
        "by_risk_type": dict(by_risk_type),
        "needs_verification": needs_verification,
        "writeable_topics": writeable_topics[:top],
    }


def format_report(summary: dict[str, Any]) -> str:
    lines = [
        "# 今日风险素材日报",
        "",
        f"- 素材总数：{summary['total']}",
        f"- 待人工验证：{summary['needs_verification']}",
        "",
        "## 来源分布",
    ]
    lines.extend(f"- {name}: {count}" for name, count in summary["by_source"].items())
    lines.extend(["", "## 风险类型分布"])
    lines.extend(f"- {name}: {count}" for name, count in summary["by_risk_type"].items())
    lines.extend(["", "## 最值得写的素材"])
    for item in summary["writeable_topics"]:
        lines.append(f"- [{item['record_id']}] {item['topic']}（{item['risk_type']} / {item['status']}）")
    return "\n".join(lines) + "\n"


def add_record(args: argparse.Namespace) -> None:
    record = build_manual_record(
        title=args.title,
        url=args.url,
        source=args.source,
        risk_type=args.risk_type,
        risk_signal=args.risk_signal,
        company=args.company,
        summary=args.summary,
        evidence_level=args.evidence_level,
        note=args.note,
    )
    result = {"records_to_create": 1, "dry_run": args.dry_run, "created": 0, "record": record}
    if not args.dry_run:
        client, config = load_client_and_config()
        result["created"] = feishu_import.batch_create_records(client, config["app_token"], config["table_id"], [record])
    print(json.dumps(result, ensure_ascii=False, indent=2))


def update_verification(args: argparse.Namespace) -> None:
    update = build_verify_update(args.record_id, status=args.status, note=args.note)
    result = {"records_to_update": 1, "dry_run": args.dry_run, "updated": 0, "record": update}
    if not args.dry_run:
        client, config = load_client_and_config()
        result["updated"] = generate_topics.batch_update_records(client, config["app_token"], config["table_id"], [update])
    print(json.dumps(result, ensure_ascii=False, indent=2))


def write_report(args: argparse.Namespace) -> None:
    client, config = load_client_and_config()
    records = feishu_import.list_all_records(client, config["app_token"], config["table_id"])
    summary = summarize_records(records, top=args.top)
    if args.format == "json":
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(format_report(summary), end="")


def run_import(args: argparse.Namespace) -> None:
    argv = []
    if args.path:
        argv.append(str(args.path))
    if args.sheet_name:
        argv.extend(["--sheet-name", args.sheet_name])
    if args.limit is not None:
        argv.extend(["--limit", str(args.limit)])
    if args.dry_run:
        argv.append("--dry-run")
    feishu_import.main(argv)


def run_generate(args: argparse.Namespace) -> None:
    argv = []
    if args.limit is not None:
        argv.extend(["--limit", str(args.limit)])
    if args.evidence_level:
        argv.extend(["--evidence-level", args.evidence_level])
    if args.force:
        argv.append("--force")
    if args.dry_run:
        argv.append("--dry-run")
    generate_topics.main(argv)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="DARA risk material command line.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    import_parser = subparsers.add_parser("import", help="Import local XLSX/CSV into Feishu.")
    import_parser.add_argument("path", nargs="?", type=Path)
    import_parser.add_argument("--sheet-name", default=None)
    import_parser.add_argument("--limit", type=int)
    import_parser.add_argument("--dry-run", action="store_true")
    import_parser.set_defaults(func=run_import)

    generate_parser = subparsers.add_parser("generate", help="Generate topic drafts and write back to Feishu.")
    generate_parser.add_argument("--limit", type=int)
    generate_parser.add_argument("--evidence-level")
    generate_parser.add_argument("--force", action="store_true")
    generate_parser.add_argument("--dry-run", action="store_true")
    generate_parser.set_defaults(func=run_generate)

    report_parser = subparsers.add_parser("report", help="Print daily risk material report.")
    report_parser.add_argument("--top", type=int, default=5)
    report_parser.add_argument("--format", choices=["text", "json"], default="text")
    report_parser.set_defaults(func=write_report)

    verify_parser = subparsers.add_parser("verify", help="Update manual verification status.")
    verify_parser.add_argument("record_id")
    verify_parser.add_argument("--status", required=True)
    verify_parser.add_argument("--note", default="")
    verify_parser.add_argument("--dry-run", action="store_true")
    verify_parser.set_defaults(func=update_verification)

    add_parser = subparsers.add_parser("add", help="Add one manual risk material record.")
    add_parser.add_argument("--title", required=True)
    add_parser.add_argument("--url", required=True)
    add_parser.add_argument("--source", default="手动录入")
    add_parser.add_argument("--risk-type", default="")
    add_parser.add_argument("--risk-signal", default="")
    add_parser.add_argument("--company", default="")
    add_parser.add_argument("--summary", default="")
    add_parser.add_argument("--evidence-level", default="C")
    add_parser.add_argument("--note", default="")
    add_parser.add_argument("--dry-run", action="store_true")
    add_parser.set_defaults(func=add_record)

    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()

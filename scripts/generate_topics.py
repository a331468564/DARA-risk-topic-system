from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "feishu_risk.json"
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from feishu_import import list_all_records  # noqa: E402
from feishu_setup import FeishuClient  # noqa: E402


GENERATED_FIELDS = {"老板视角", "可写选题", "短视频开头", "公众号标题", "处理状态"}


def clean_text(value: Any) -> str:
    text = re.sub(r"<[^>]+>", "", str(value or ""))
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def field(record: dict[str, Any], name: str) -> str:
    return clean_text(record.get("fields", {}).get(name, ""))


def generate_draft_fields(record: dict[str, Any]) -> dict[str, str]:
    title = field(record, "原始标题") or "这条风险信号"
    company = field(record, "涉及企业")
    risk_type = field(record, "风险类型") or "经营风险"
    signal = field(record, "风险信号") or risk_type
    subject = company or "这类企业"

    return {
        "老板视角": (
            f"老板要看的不是“{title}”本身，而是{subject}暴露出的{risk_type}："
            f"{signal}是否会传导到现金流、融资、客户信任和管理层责任。"
        ),
        "可写选题": f"{subject}出现{signal}，老板该如何提前识别{risk_type}的连锁反应？",
        "短视频开头": (
            f"如果你的公司也遇到{signal}，先别只看新闻热闹，老板真正要问的是："
            "它会不会把现金流、信用和团队信心一起拖下水？"
        ),
        "公众号标题": f"从{subject}{signal}看老板必须盯住的{risk_type}",
        "处理状态": "待人工验证",
    }


def needs_generation(record: dict[str, Any], force: bool = False) -> bool:
    if force:
        return True
    fields = record.get("fields", {})
    has_risk_marker = bool(clean_text(fields.get("风险类型", "")) or clean_text(fields.get("风险信号", "")))
    return has_risk_marker and not clean_text(fields.get("可写选题", ""))


def filter_records(records: list[dict[str, Any]], evidence_level: str | None = None) -> list[dict[str, Any]]:
    if not evidence_level:
        return records
    expected = clean_text(evidence_level)
    return [record for record in records if field(record, "证据等级") == expected]


def build_batch_update_records(records: list[dict[str, Any]], force: bool = False) -> list[dict[str, Any]]:
    updates = []
    for record in records:
        if not needs_generation(record, force=force):
            continue
        record_id = record.get("record_id") or record.get("id")
        if not record_id:
            continue
        updates.append({"record_id": record_id, "fields": generate_draft_fields(record)})
    return updates


def batch_update_records(
    client: FeishuClient,
    app_token: str,
    table_id: str,
    records: list[dict[str, Any]],
    batch_size: int = 100,
) -> int:
    updated = 0
    for start in range(0, len(records), batch_size):
        chunk = records[start : start + batch_size]
        if not chunk:
            continue
        client.request(
            "POST",
            f"/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_update",
            json={"records": chunk},
        )
        updated += len(chunk)
    return updated


def load_feishu_config(path: Path = CONFIG_PATH) -> dict[str, str]:
    config = json.loads(path.read_text(encoding="utf-8"))
    return {
        "app_token": config["FEISHU_RISK_BITABLE_APP_TOKEN"],
        "table_id": config["FEISHU_RISK_TABLE_ID"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate draft topic fields and write them back to Feishu Bitable.")
    parser.add_argument("--limit", type=int, help="Only process the first N eligible records.")
    parser.add_argument("--evidence-level", help="Only process records with this evidence level, for example A.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing generated topic fields.")
    parser.add_argument("--dry-run", action="store_true", help="Preview updates without writing to Feishu.")
    args = parser.parse_args()

    app_id = os.environ.get("FEISHU_APP_ID")
    app_secret = os.environ.get("FEISHU_APP_SECRET")
    if not app_id or not app_secret:
        raise SystemExit("FEISHU_APP_ID and FEISHU_APP_SECRET are required in environment variables.")

    config = load_feishu_config()
    client = FeishuClient(app_id=app_id, app_secret=app_secret)
    records = list_all_records(client, config["app_token"], config["table_id"])
    records = filter_records(records, evidence_level=args.evidence_level)
    updates = build_batch_update_records(records, force=args.force)
    if args.limit is not None:
        updates = updates[: args.limit]

    result = {
        "records_read": len(records),
        "evidence_level": args.evidence_level,
        "records_to_update": len(updates),
        "dry_run": args.dry_run,
        "force": args.force,
        "updated": 0,
        "sample": updates[:3],
    }
    if not args.dry_run and updates:
        result["updated"] = batch_update_records(client, config["app_token"], config["table_id"], updates)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

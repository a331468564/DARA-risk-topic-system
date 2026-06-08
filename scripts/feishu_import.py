from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "feishu_risk.json"
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from feishu_setup import FeishuClient  # noqa: E402


def row_to_record(row: pd.Series) -> dict[str, dict[str, str]]:
    fields: dict[str, str] = {}
    for key, value in row.items():
        if pd.isna(value):
            continue
        text = str(value).strip()
        if not text:
            continue
        fields[str(key)] = text
    return {"fields": fields}


def existing_dedupe_keys(records: list[dict[str, Any]]) -> set[str]:
    keys = set()
    for record in records:
        key = record.get("fields", {}).get("去重键")
        if key:
            keys.add(str(key))
    return keys


def records_for_import(df: pd.DataFrame, existing_keys: set[str]) -> list[dict[str, dict[str, str]]]:
    records = []
    for _, row in df.iterrows():
        key = row.get("去重键")
        if pd.notna(key) and str(key) in existing_keys:
            continue
        records.append(row_to_record(row))
    return records


def read_local_table(path: Path, sheet_name: str = "风险素材表") -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    if path.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(path, sheet_name=sheet_name)
    raise ValueError(f"Unsupported file type: {path}")


def load_feishu_config(path: Path = CONFIG_PATH) -> dict[str, str]:
    config = json.loads(path.read_text(encoding="utf-8"))
    return {
        "app_token": config["FEISHU_RISK_BITABLE_APP_TOKEN"],
        "table_id": config["FEISHU_RISK_TABLE_ID"],
        "table_name": config["FEISHU_RISK_TABLE_NAME"],
    }


def list_all_records(client: FeishuClient, app_token: str, table_id: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    page_token = ""
    while True:
        query = "page_size=500"
        if page_token:
            query += f"&page_token={page_token}"
        payload = client.request("GET", f"/bitable/v1/apps/{app_token}/tables/{table_id}/records?{query}")
        data = payload.get("data", {})
        records.extend(data.get("items", []))
        if not data.get("has_more"):
            break
        page_token = data.get("page_token", "")
        if not page_token:
            break
    return records


def batch_create_records(
    client: FeishuClient,
    app_token: str,
    table_id: str,
    records: list[dict[str, dict[str, str]]],
    batch_size: int = 100,
) -> int:
    created = 0
    for start in range(0, len(records), batch_size):
        chunk = records[start : start + batch_size]
        if not chunk:
            continue
        client.request(
            "POST",
            f"/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_create",
            json={"records": chunk},
        )
        created += len(chunk)
    return created


def latest_local_table() -> Path:
    candidates = sorted((ROOT / "data" / "source_tests").glob("risk_materials_local_*.xlsx"))
    if not candidates:
        raise FileNotFoundError("No local XLSX table found in data/source_tests.")
    return candidates[-1]


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Import local risk materials into Feishu Bitable.")
    parser.add_argument("path", nargs="?", type=Path, default=None)
    parser.add_argument("--sheet-name", default="风险素材表")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    path = args.path or latest_local_table()
    df = read_local_table(path, sheet_name=args.sheet_name)
    if args.limit is not None:
        df = df.head(args.limit)

    config = load_feishu_config()
    app_id = os.environ.get("FEISHU_APP_ID")
    app_secret = os.environ.get("FEISHU_APP_SECRET")
    if not app_id or not app_secret:
        raise SystemExit("FEISHU_APP_ID and FEISHU_APP_SECRET are required in environment variables.")

    client = FeishuClient(app_id=app_id, app_secret=app_secret)
    existing = list_all_records(client, config["app_token"], config["table_id"])
    existing_keys = existing_dedupe_keys(existing)
    records = records_for_import(df, existing_keys)

    result = {
        "input_path": str(path),
        "rows_read": len(df),
        "existing_records": len(existing),
        "existing_dedupe_keys": len(existing_keys),
        "records_to_create": len(records),
        "dry_run": args.dry_run,
        "created": 0,
    }
    if not args.dry_run and records:
        result["created"] = batch_create_records(client, config["app_token"], config["table_id"], records)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

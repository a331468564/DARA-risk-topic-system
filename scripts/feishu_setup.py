from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "config"
FEISHU_RISK_CONFIG = CONFIG_DIR / "feishu_risk.json"
FEISHU_ENV_EXAMPLE = ROOT / ".env.example"

BASE_URL = "https://open.feishu.cn/open-apis"


def risk_material_fields() -> list[dict[str, Any]]:
    # Use text fields first. They are the most stable OpenAPI field type and can
    # later be upgraded manually to single-select/date/url in Feishu if needed.
    names = [
        "记录日期",
        "来源",
        "来源类型",
        "素材层级",
        "原始标题",
        "原文链接",
        "发布时间",
        "原始摘要",
        "涉及企业",
        "涉及人物",
        "风险类型",
        "风险信号",
        "风险关键词",
        "老板视角",
        "可写选题",
        "短视频开头",
        "公众号标题",
        "核验状态",
        "处理状态",
        "证据等级",
        "证据链接",
        "去重键",
        "备注",
    ]
    return [{"field_name": name, "type": 1} for name in names]


def public_config(app_token: str, table_id: str, table_name: str) -> dict[str, str]:
    return {
        "FEISHU_RISK_BITABLE_APP_TOKEN": app_token,
        "FEISHU_RISK_TABLE_ID": table_id,
        "FEISHU_RISK_TABLE_NAME": table_name,
    }


class FeishuClient:
    def __init__(self, app_id: str, app_secret: str) -> None:
        self.app_id = app_id
        self.app_secret = app_secret
        self._tenant_access_token: str | None = None

    def tenant_access_token(self) -> str:
        if self._tenant_access_token:
            return self._tenant_access_token
        response = requests.post(
            f"{BASE_URL}/auth/v3/tenant_access_token/internal",
            json={"app_id": self.app_id, "app_secret": self.app_secret},
            timeout=30,
        )
        payload = response.json()
        if payload.get("code") != 0:
            raise RuntimeError(f"Feishu token error: code={payload.get('code')} msg={payload.get('msg')}")
        self._tenant_access_token = payload["tenant_access_token"]
        return self._tenant_access_token

    def request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        token = self.tenant_access_token()
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {token}"
        response = requests.request(method, f"{BASE_URL}{path}", headers=headers, timeout=30, **kwargs)
        payload = response.json()
        if payload.get("code") != 0:
            raise RuntimeError(f"Feishu API error: {method} {path} code={payload.get('code')} msg={payload.get('msg')}")
        return payload

    def create_bitable_app(self, name: str) -> str:
        payload = self.request("POST", "/bitable/v1/apps", json={"name": name})
        app = payload.get("data", {}).get("app", {})
        app_token = app.get("app_token") or payload.get("data", {}).get("app_token")
        if not app_token:
            raise RuntimeError(f"Cannot find app_token in response: {payload}")
        return app_token

    def list_tables(self, app_token: str) -> list[dict[str, Any]]:
        payload = self.request("GET", f"/bitable/v1/apps/{app_token}/tables")
        return payload.get("data", {}).get("items", [])

    def create_table(self, app_token: str, table_name: str) -> str:
        payload = self.request(
            "POST",
            f"/bitable/v1/apps/{app_token}/tables",
            json={
                "table": {
                    "name": table_name,
                    "default_view_name": "默认视图",
                    "fields": [{"field_name": "记录日期", "type": 1}],
                }
            },
        )
        data = payload.get("data", {})
        table_id = data.get("table_id") or data.get("table", {}).get("table_id")
        if not table_id:
            raise RuntimeError(f"Cannot find table_id in response: {payload}")
        return table_id

    def create_field(self, app_token: str, table_id: str, field: dict[str, Any]) -> dict[str, Any]:
        payload = self.request(
            "POST",
            f"/bitable/v1/apps/{app_token}/tables/{table_id}/fields",
            json={"field_name": field["field_name"], "type": field["type"]},
        )
        return payload.get("data", {}).get("field", {})

    def list_fields(self, app_token: str, table_id: str) -> list[dict[str, Any]]:
        payload = self.request("GET", f"/bitable/v1/apps/{app_token}/tables/{table_id}/fields")
        return payload.get("data", {}).get("items", [])

    def ensure_fields(self, app_token: str, table_id: str, fields: list[dict[str, Any]]) -> list[dict[str, Any]]:
        existing = {field.get("field_name") for field in self.list_fields(app_token, table_id)}
        created = []
        for field in fields:
            if field["field_name"] in existing:
                continue
            created.append(self.create_field(app_token, table_id, field))
        return created


def write_public_config(config: dict[str, str], app_name: str) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "app_name": app_name,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        **config,
    }
    FEISHU_RISK_CONFIG.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    example_lines = [
        "FEISHU_APP_ID=cli_xxx",
        "FEISHU_APP_SECRET=your_app_secret",
        f"FEISHU_RISK_BITABLE_APP_TOKEN={config['FEISHU_RISK_BITABLE_APP_TOKEN']}",
        f"FEISHU_RISK_TABLE_ID={config['FEISHU_RISK_TABLE_ID']}",
    ]
    FEISHU_ENV_EXAMPLE.write_text("\n".join(example_lines) + "\n", encoding="utf-8")


def setup_risk_bitable(
    app_name: str,
    table_name: str,
    client: FeishuClient,
    existing_app_token: str | None = None,
) -> dict[str, Any]:
    app_token = existing_app_token or client.create_bitable_app(app_name)
    table_id = client.create_table(app_token, table_name)
    created_fields = client.ensure_fields(app_token, table_id, risk_material_fields())
    fields = client.list_fields(app_token, table_id)
    return {
        "app_token": app_token,
        "table_id": table_id,
        "table_name": table_name,
        "field_count": len(fields),
        "created_field_count": len(created_fields),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Create Feishu Bitable files for the risk topic MVP.")
    parser.add_argument("--app-name", default="企业老板风险选题库")
    parser.add_argument("--table-name", default="风险素材表")
    parser.add_argument("--app-token", help="Use an existing Bitable app token instead of creating a new Base.")
    args = parser.parse_args()

    app_id = os.environ.get("FEISHU_APP_ID")
    app_secret = os.environ.get("FEISHU_APP_SECRET")
    if not app_id or not app_secret:
        raise SystemExit("FEISHU_APP_ID and FEISHU_APP_SECRET are required in environment variables.")

    client = FeishuClient(app_id=app_id, app_secret=app_secret)
    result = setup_risk_bitable(args.app_name, args.table_name, client, existing_app_token=args.app_token)
    config = public_config(
        app_token=result["app_token"],
        table_id=result["table_id"],
        table_name=result["table_name"],
    )
    write_public_config(config, args.app_name)

    print(json.dumps({**result, "config_path": str(FEISHU_RISK_CONFIG)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

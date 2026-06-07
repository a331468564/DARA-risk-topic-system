import importlib.util
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "feishu_setup.py"
SPEC = importlib.util.spec_from_file_location("feishu_setup_script", SCRIPT_PATH)
feishu_setup = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(feishu_setup)


class FeishuSetupTests(unittest.TestCase):
    def test_risk_fields_include_required_table_columns(self):
        field_names = [field["field_name"] for field in feishu_setup.risk_material_fields()]

        for name in ["记录日期", "来源", "素材层级", "原始标题", "原文链接", "核验状态", "去重键"]:
            self.assertIn(name, field_names)

    def test_field_names_are_unique(self):
        field_names = [field["field_name"] for field in feishu_setup.risk_material_fields()]

        self.assertEqual(len(field_names), len(set(field_names)))

    def test_public_config_does_not_include_credentials(self):
        config = feishu_setup.public_config(
            app_token="base_token",
            table_id="table_id",
            table_name="风险素材表",
        )

        rendered = "\n".join(f"{key}={value}" for key, value in config.items())
        self.assertIn("FEISHU_RISK_BITABLE_APP_TOKEN=base_token", rendered)
        self.assertIn("FEISHU_RISK_TABLE_ID=table_id", rendered)
        self.assertNotIn("APP_SECRET", rendered)
        self.assertNotIn("tenant_access_token", rendered)

    def test_setup_can_use_existing_app_token(self):
        class FakeClient:
            def __init__(self):
                self.created_apps = []

            def create_bitable_app(self, name):
                self.created_apps.append(name)
                return "new_app_token"

            def create_table(self, app_token, table_name):
                self.app_token = app_token
                self.table_name = table_name
                return "table_id"

            def ensure_fields(self, app_token, table_id, fields):
                self.field_count = len(fields)
                return fields[1:]

            def list_fields(self, app_token, table_id):
                return feishu_setup.risk_material_fields()

        client = FakeClient()
        result = feishu_setup.setup_risk_bitable(
            app_name="企业老板风险选题库",
            table_name="风险素材表",
            client=client,
            existing_app_token="existing_app_token",
        )

        self.assertEqual(client.created_apps, [])
        self.assertEqual(client.app_token, "existing_app_token")
        self.assertEqual(result["app_token"], "existing_app_token")
        self.assertEqual(result["table_id"], "table_id")


if __name__ == "__main__":
    unittest.main()

import importlib.util
import io
import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "risk.py"
SPEC = importlib.util.spec_from_file_location("risk_cli_script", SCRIPT_PATH)
risk_cli = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(risk_cli)


class RiskCliTests(unittest.TestCase):
    def test_build_manual_record_sets_required_defaults(self):
        record = risk_cli.build_manual_record(
            title="关于公司新增债务逾期的公告",
            url="https://example.com/a.pdf",
            source="手动录入",
            risk_type="债务风险",
            risk_signal="债务逾期",
            company="样例公司",
        )

        fields = record["fields"]
        self.assertEqual(fields["来源"], "手动录入")
        self.assertEqual(fields["原始标题"], "关于公司新增债务逾期的公告")
        self.assertEqual(fields["风险类型"], "债务风险")
        self.assertEqual(fields["风险信号"], "债务逾期")
        self.assertEqual(fields["涉及企业"], "样例公司")
        self.assertEqual(fields["核验状态"], "未核验")
        self.assertEqual(fields["处理状态"], "待加工")
        self.assertEqual(fields["证据等级"], "C")
        self.assertEqual(fields["去重键"], "https://example.com/a.pdf")

    def test_build_verify_update_sets_status_and_optional_note(self):
        update = risk_cli.build_verify_update("rec1", status="已采用", note="人工确认可写")

        self.assertEqual(update["record_id"], "rec1")
        self.assertEqual(update["fields"]["处理状态"], "已采用")
        self.assertEqual(update["fields"]["备注"], "人工确认可写")

    def test_summarize_records_counts_daily_report_inputs(self):
        records = [
            {
                "record_id": "rec1",
                "fields": {
                    "来源": "巨潮资讯",
                    "风险类型": "债务风险",
                    "证据等级": "A",
                    "处理状态": "待人工验证",
                    "可写选题": "选题 A",
                    "原始标题": "标题 A",
                },
            },
            {
                "record_id": "rec2",
                "fields": {
                    "来源": "36氪",
                    "风险类型": "舆情风险",
                    "证据等级": "C",
                    "处理状态": "待加工",
                    "可写选题": "",
                    "原始标题": "标题 B",
                },
            },
        ]

        summary = risk_cli.summarize_records(records, top=5)

        self.assertEqual(summary["total"], 2)
        self.assertEqual(summary["by_source"], {"巨潮资讯": 1, "36氪": 1})
        self.assertEqual(summary["by_risk_type"], {"债务风险": 1, "舆情风险": 1})
        self.assertEqual(summary["needs_verification"], 1)
        self.assertEqual(summary["writeable_topics"][0]["record_id"], "rec1")

    def test_parser_accepts_expected_subcommands(self):
        parser = risk_cli.build_parser()

        self.assertEqual(parser.parse_args(["import", "--dry-run"]).command, "import")
        self.assertEqual(parser.parse_args(["generate", "--evidence-level", "A"]).command, "generate")
        self.assertEqual(parser.parse_args(["report", "--top", "3"]).top, 3)
        self.assertEqual(parser.parse_args(["verify", "rec1", "--status", "已采用"]).record_id, "rec1")
        self.assertEqual(parser.parse_args(["add", "--title", "T", "--url", "U"]).command, "add")

    def test_add_dry_run_does_not_require_feishu_credentials(self):
        with patch.dict(os.environ, {}, clear=True), patch("sys.stdout", new_callable=io.StringIO) as stdout:
            risk_cli.main(["add", "--title", "T", "--url", "U", "--dry-run"])

        payload = json.loads(stdout.getvalue())
        self.assertTrue(payload["dry_run"])
        self.assertEqual(payload["created"], 0)
        self.assertEqual(payload["record"]["fields"]["原始标题"], "T")

    def test_verify_dry_run_does_not_require_feishu_credentials(self):
        with patch.dict(os.environ, {}, clear=True), patch("sys.stdout", new_callable=io.StringIO) as stdout:
            risk_cli.main(["verify", "rec1", "--status", "已采用", "--dry-run"])

        payload = json.loads(stdout.getvalue())
        self.assertTrue(payload["dry_run"])
        self.assertEqual(payload["updated"], 0)
        self.assertEqual(payload["record"]["fields"]["处理状态"], "已采用")


if __name__ == "__main__":
    unittest.main()

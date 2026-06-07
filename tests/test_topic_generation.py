import importlib.util
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "generate_topics.py"
SPEC = importlib.util.spec_from_file_location("generate_topics_script", SCRIPT_PATH)
topic_generation = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(topic_generation)


class TopicGenerationTests(unittest.TestCase):
    def test_generate_draft_fields_uses_company_risk_and_signal(self):
        record = {
            "record_id": "rec1",
            "fields": {
                "原始标题": "关于公司新增债务逾期的公告",
                "涉及企业": "ST合纵",
                "风险类型": "债务风险",
                "风险信号": "债务逾期",
                "证据等级": "A",
            },
        }

        fields = topic_generation.generate_draft_fields(record)

        self.assertIn("ST合纵", fields["老板视角"])
        self.assertIn("债务风险", fields["老板视角"])
        self.assertIn("债务逾期", fields["可写选题"])
        self.assertTrue(fields["短视频开头"].startswith("如果你的公司"))
        self.assertIn("债务逾期", fields["公众号标题"])
        self.assertEqual(fields["处理状态"], "待人工验证")

    def test_needs_generation_skips_records_with_existing_topic_by_default(self):
        record = {
            "record_id": "rec1",
            "fields": {
                "可写选题": "已有选题",
                "老板视角": "",
            },
        }

        self.assertFalse(topic_generation.needs_generation(record, force=False))
        self.assertTrue(topic_generation.needs_generation(record, force=True))

    def test_needs_generation_skips_unclassified_records_by_default(self):
        record = {
            "record_id": "rec1",
            "fields": {
                "原始标题": "普通行业新闻",
                "风险类型": "",
                "风险信号": "",
                "可写选题": "",
            },
        }

        self.assertFalse(topic_generation.needs_generation(record, force=False))
        self.assertTrue(topic_generation.needs_generation(record, force=True))

    def test_build_batch_update_records_keeps_record_id_and_generated_fields(self):
        records = [
            {
                "record_id": "rec1",
                "fields": {
                    "原始标题": "股票交易异常波动公告",
                    "涉及企业": "阳光股份",
                    "风险类型": "舆情风险",
                    "风险信号": "异常波动",
                },
            }
        ]

        updates = topic_generation.build_batch_update_records(records, force=False)

        self.assertEqual(len(updates), 1)
        self.assertEqual(updates[0]["record_id"], "rec1")
        self.assertEqual(set(updates[0]["fields"]), topic_generation.GENERATED_FIELDS)
        self.assertIn("异常波动", updates[0]["fields"]["公众号标题"])

    def test_filter_records_by_evidence_level(self):
        records = [
            {"record_id": "rec1", "fields": {"证据等级": "A"}},
            {"record_id": "rec2", "fields": {"证据等级": "C"}},
        ]

        filtered = topic_generation.filter_records(records, evidence_level="A")

        self.assertEqual([record["record_id"] for record in filtered], ["rec1"])


if __name__ == "__main__":
    unittest.main()

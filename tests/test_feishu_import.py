import importlib.util
import unittest
from pathlib import Path

import pandas as pd


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "feishu_import.py"
SPEC = importlib.util.spec_from_file_location("feishu_import_script", SCRIPT_PATH)
feishu_import = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(feishu_import)


class FeishuImportTests(unittest.TestCase):
    def test_row_to_record_removes_nan_and_keeps_text_values(self):
        row = pd.Series(
            {
                "来源": "36氪",
                "原始标题": "测试标题",
                "涉及企业": float("nan"),
                "风险类型": "",
                "去重键": "https://example.com/a",
            }
        )

        record = feishu_import.row_to_record(row)

        self.assertEqual(record["fields"]["来源"], "36氪")
        self.assertEqual(record["fields"]["原始标题"], "测试标题")
        self.assertEqual(record["fields"]["去重键"], "https://example.com/a")
        self.assertNotIn("涉及企业", record["fields"])
        self.assertNotIn("风险类型", record["fields"])

    def test_dedupe_existing_keys_from_records(self):
        records = [
            {"fields": {"去重键": "a"}},
            {"fields": {"去重键": "b"}},
            {"fields": {}},
        ]

        self.assertEqual(feishu_import.existing_dedupe_keys(records), {"a", "b"})

    def test_records_for_import_skips_existing_keys(self):
        df = pd.DataFrame(
            [
                {"来源": "36氪", "原始标题": "A", "去重键": "a"},
                {"来源": "巨潮资讯", "原始标题": "B", "去重键": "b"},
            ]
        )

        records = feishu_import.records_for_import(df, existing_keys={"a"})

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["fields"]["去重键"], "b")


if __name__ == "__main__":
    unittest.main()

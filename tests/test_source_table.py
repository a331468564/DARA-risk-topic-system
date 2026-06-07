import importlib.util
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "test_sources.py"
SPEC = importlib.util.spec_from_file_location("test_sources_script", SCRIPT_PATH)
source_script = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(source_script)


class SourceTableTests(unittest.TestCase):
    def test_loads_keyword_rules_from_config_file(self):
        rules = source_script.load_keyword_rules(
            {
                "债务风险": ["债务逾期"],
                "合规风险": ["监管函"],
            }
        )

        self.assertEqual(rules["债务风险"], ["债务逾期"])
        self.assertEqual(
            source_script.classify_risk("公司新增债务逾期公告", rules),
            ("债务风险", "债务逾期", "债务逾期"),
        )

    def test_media_rows_are_unverified_leads(self):
        row = source_script.build_row(
            source="36氪",
            source_type="official_rss",
            title="某公司回应市场传闻",
            url="https://example.com/news",
            published_at="2026-06-07",
            summary="公司发布澄清说明",
            evidence_level="C",
            material_tier="线索池",
        )

        self.assertEqual(row["素材层级"], "线索池")
        self.assertEqual(row["核验状态"], "未核验")
        self.assertEqual(row["证据等级"], "C")

    def test_cninfo_rows_are_verified_evidence(self):
        row = source_script.build_row(
            source="巨潮资讯",
            source_type="cninfo_api",
            title="关于收到监管函的公告",
            url="https://example.com/notice.pdf",
            published_at="2026-06-07",
            summary="关于收到监管函的公告",
            company="某上市公司",
            evidence_level="A",
            material_tier="证据池",
        )

        self.assertEqual(row["素材层级"], "证据池")
        self.assertEqual(row["核验状态"], "已核验")
        self.assertEqual(row["证据等级"], "A")

    def test_broad_business_words_do_not_create_risk_hits(self):
        rules = source_script.load_keyword_rules_from_file()

        broad_texts = [
            "公司按计划完成产品交付，客户反馈良好",
            "某产业基金完成备案并开始投资科技企业",
            "招股书介绍实际控制人及法定代表人基本情况",
            "企业宣布新一轮融资用于扩大研发团队",
        ]

        for text in broad_texts:
            with self.subTest(text=text):
                self.assertEqual(source_script.classify_risk(text, rules), ("", "", ""))

    def test_specific_risk_phrases_still_match(self):
        rules = source_script.load_keyword_rules_from_file()

        self.assertEqual(
            source_script.classify_risk("公司收到监管函并被责令改正", rules),
            ("合规风险", "监管函", "监管函、责令改正"),
        )
        self.assertEqual(
            source_script.classify_risk("控股股东所持股份被司法冻结", rules),
            ("股权风险", "司法冻结", "司法冻结"),
        )


if __name__ == "__main__":
    unittest.main()

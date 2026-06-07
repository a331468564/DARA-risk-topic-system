from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import feedparser
import pandas as pd
import requests


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "source_tests.json"
KEYWORDS_PATH = ROOT / "config" / "risk_keywords.json"
OUTPUT_DIR = ROOT / "data" / "source_tests"

LOCAL_TABLE_COLUMNS = [
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

DEFAULT_RISK_KEYWORDS = {
    "债务风险": ["债务逾期", "延期兑付", "无法按期兑付", "破产重整", "清算"],
    "股权风险": ["股权冻结", "股权质押", "实控人变更", "关联交易"],
    "合规风险": ["行政处罚", "监管函", "问询函", "立案调查", "纪律处分"],
    "老板个人风险": ["被执行", "失信", "限制高消费", "董事长辞职"],
    "供应链风险": ["客户暴雷", "供应链中断", "原材料价格", "交付"],
    "舆情风险": ["传闻", "澄清", "不实", "投诉", "异常波动"],
    "融资风险": ["融资", "IPO", "上市", "兑付", "基金"],
    "传承风险": ["继任", "接班", "家族", "控制权"],
}


def load_keyword_rules(raw_rules: dict[str, Any] | None = None) -> dict[str, list[str]]:
    source = raw_rules if raw_rules is not None else DEFAULT_RISK_KEYWORDS
    rules: dict[str, list[str]] = {}
    for risk_type, keywords in source.items():
        cleaned = [str(keyword).strip() for keyword in keywords if str(keyword).strip()]
        if cleaned:
            rules[str(risk_type)] = cleaned
    return rules


def load_keyword_rules_from_file(path: Path = KEYWORDS_PATH) -> dict[str, list[str]]:
    if not path.exists():
        return load_keyword_rules()
    return load_keyword_rules(json.loads(path.read_text(encoding="utf-8")))


def clean_html(value: str) -> str:
    value = re.sub(r"<[^>]+>", "", value or "")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def classify_risk(text: str, keyword_rules: dict[str, list[str]] | None = None) -> tuple[str, str, str]:
    rules = keyword_rules or load_keyword_rules()
    for risk_type, keywords in rules.items():
        matched = [keyword for keyword in keywords if keyword in text]
        if matched:
            return risk_type, matched[0], "、".join(sorted(set(matched)))
    return "", "", ""


def make_dedupe_key(source: str, title: str, url: str) -> str:
    base = url.strip() or f"{source}:{title.strip()}"
    return re.sub(r"\s+", "", base)


def build_row(
    *,
    source: str,
    source_type: str,
    title: str,
    url: str,
    published_at: str,
    summary: str,
    company: str = "",
    evidence_level: str = "C",
    material_tier: str = "线索池",
    evidence_url: str = "",
    note: str = "",
    keyword_rules: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    text = f"{title} {summary}"
    risk_type, risk_signal, risk_keywords = classify_risk(text, keyword_rules)
    return {
        "记录日期": datetime.now().strftime("%Y-%m-%d"),
        "来源": source,
        "来源类型": source_type,
        "素材层级": material_tier,
        "原始标题": clean_html(title),
        "原文链接": url,
        "发布时间": published_at,
        "原始摘要": clean_html(summary)[:1000],
        "涉及企业": company,
        "涉及人物": "",
        "风险类型": risk_type,
        "风险信号": risk_signal,
        "风险关键词": risk_keywords,
        "老板视角": "",
        "可写选题": "",
        "短视频开头": "",
        "公众号标题": "",
        "核验状态": "已核验" if evidence_level == "A" else "未核验",
        "处理状态": "待加工",
        "证据等级": evidence_level,
        "证据链接": evidence_url or url,
        "去重键": make_dedupe_key(source, title, url),
        "备注": note,
    }


def fetch_rss_source(
    source: dict[str, Any],
    limit: int,
    keyword_rules: dict[str, list[str]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    parsed = feedparser.parse(source["url"])
    entries = parsed.entries[:limit]
    rows = []

    for entry in entries:
        title = entry.get("title", "")
        url = entry.get("link", "")
        published_at = entry.get("published", "") or entry.get("updated", "")
        summary = entry.get("summary", "") or entry.get("description", "")
        rows.append(
            build_row(
                source=source["name"],
                source_type=source["source_type"],
                title=title,
                url=url,
                published_at=published_at,
                summary=summary,
                evidence_level="C",
                material_tier="线索池",
                note=source.get("purpose", ""),
                keyword_rules=keyword_rules,
            )
        )

    status = {
        "来源": source["name"],
        "测试地址": source["url"],
        "接入方式": source["source_type"],
        "返回条数": len(rows),
        "是否可用": "是" if rows else "否",
        "说明": parsed.bozo_exception.getMessage() if getattr(parsed, "bozo", False) else source.get("purpose", ""),
    }
    return rows, status


def fetch_cninfo(
    config: dict[str, Any],
    per_keyword: int,
    keyword_rules: dict[str, list[str]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "http://www.cninfo.com.cn/new/commonUrl/pageOfSearch?url=disclosure/list/search",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    }
    rows: list[dict[str, Any]] = []
    errors: list[str] = []

    for keyword in config["keywords"]:
        data = {
            "pageNum": "1",
            "pageSize": str(per_keyword),
            "column": "szse",
            "tabName": "fulltext",
            "plate": "",
            "stock": "",
            "searchkey": keyword,
            "secid": "",
            "category": "",
            "trade": "",
            "seDate": "",
            "sortName": "",
            "sortType": "",
            "isHLtitle": "true",
        }
        try:
            response = requests.post(config["url"], headers=headers, data=data, timeout=20)
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            errors.append(f"{keyword}: {exc}")
            continue

        for item in payload.get("announcements") or []:
            title = clean_html(item.get("announcementTitle", ""))
            adjunct_url = item.get("adjunctUrl", "")
            url = f"http://static.cninfo.com.cn/{adjunct_url}" if adjunct_url else ""
            timestamp = item.get("announcementTime")
            published_at = ""
            if timestamp:
                published_at = datetime.fromtimestamp(timestamp / 1000).strftime("%Y-%m-%d")
            company = item.get("secName", "") or item.get("tileSecName", "")
            rows.append(
                build_row(
                    source=config["name"],
                    source_type="cninfo_api",
                    title=title,
                    url=url,
                    published_at=published_at,
                    summary=title,
                    company=company,
                    evidence_level="A",
                    material_tier="证据池",
                    evidence_url=url,
                    note=f"巨潮关键词：{keyword}",
                    keyword_rules=keyword_rules,
                )
            )

    status = {
        "来源": config["name"],
        "测试地址": config["url"],
        "接入方式": "cninfo_api",
        "返回条数": len(rows),
        "是否可用": "是" if rows else "否",
        "说明": "; ".join(errors) if errors else config.get("purpose", ""),
    }
    return rows, status


def write_outputs(rows: list[dict[str, Any]], statuses: list[dict[str, Any]]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    local_df = pd.DataFrame(rows, columns=LOCAL_TABLE_COLUMNS)
    status_df = pd.DataFrame(statuses)

    local_csv = OUTPUT_DIR / f"risk_materials_local_{timestamp}.csv"
    local_xlsx = OUTPUT_DIR / f"risk_materials_local_{timestamp}.xlsx"
    status_csv = OUTPUT_DIR / f"source_status_{timestamp}.csv"

    local_df.to_csv(local_csv, index=False, encoding="utf-8-sig")
    status_df.to_csv(status_csv, index=False, encoding="utf-8-sig")

    with pd.ExcelWriter(local_xlsx, engine="openpyxl") as writer:
        local_df.to_excel(writer, sheet_name="风险素材表", index=False)
        status_df.to_excel(writer, sheet_name="数据源测试结果", index=False)

    print(f"rows={len(local_df)}")
    print(f"local_csv={local_csv}")
    print(f"local_xlsx={local_xlsx}")
    print(f"status_csv={status_csv}")
    print(status_df.to_string(index=False))


def main() -> None:
    parser = argparse.ArgumentParser(description="Test risk-topic data sources and export a local table.")
    parser.add_argument("--rss-limit", type=int, default=20)
    parser.add_argument("--cninfo-limit", type=int, default=5)
    args = parser.parse_args()

    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    keyword_rules = load_keyword_rules_from_file()
    rows: list[dict[str, Any]] = []
    statuses: list[dict[str, Any]] = []

    for source in config["rss_sources"]:
        source_rows, status = fetch_rss_source(source, args.rss_limit, keyword_rules)
        rows.extend(source_rows)
        statuses.append(status)

    cninfo_rows, cninfo_status = fetch_cninfo(config["cninfo"], args.cninfo_limit, keyword_rules)
    rows.extend(cninfo_rows)
    statuses.append(cninfo_status)

    unique_rows = list({row["去重键"]: row for row in rows}.values())
    write_outputs(unique_rows, statuses)


if __name__ == "__main__":
    main()

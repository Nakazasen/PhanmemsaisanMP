"""
Allocation engine.

Responsibilities:
- map direct-cost staging rows to account_code
- generate allocation rows from map_allocation_rules
"""

import re
import sqlite3
import unicodedata

from src.engine.account_resolver import AccountResolutionError, resolve_account_code_for_source
from src.services.headcount_source_policy import HeadcountSourceError, load_canonical_headcount
from src.utils import excel_helpers as helpers

HEALTH_CHECK_KEYWORDS = ("kham suc khoe", "khám sức khỏe", "健康診断")
MALE_KEYWORDS = ("cho cnv nam", " nam)", " male", "男")
FEMALE_KEYWORDS = ("cho cnv nu", "cho cnv nữ", " nu)", " nữ)", " female", "女")
MANUAL_EVENT_ITEM_TOKENS = (
    "visa",
    "passport",
    "gpld",
    "ho chieu",
    "ho ch\u1ebfu",
    "the tam tru",
    "th\u1ebb t\u1ea1m tru",
    "th\u1ebb t\u1ea1m tr\u00fa",
    "nhap canh",
    "nh\u1eadp canh",
    "nh\u1eadp c\u1ea3nh",
    "luu tru",
    "\u52b4\u50cd\u8a31\u53ef",
    "\u5728\u7559",
    "\u65c5\u5238",
    "\u5165\u56fd",
    "\u30d3\u30b6",
    "部門方針発表会後の決起コンパ",
    "phương châm bộ phận",
    "phuong cham bo phan",
    "社員旅行不参加",
    "không thể tham gia du lịch",
    "khong the tham gia du lich",
    "マイエピソード",
    "cảm nghĩ về triết lý kinh doanh",
    "cam nghi ve triet ly kinh doanh",
    "10年勤続記念コンパ",
    "tiệc kỷ niệm 10 năm",
    "tiec ky niem 10 nam",
    "10年勤続記念品",
    "quà kỷ niệm",
    "qua ky niem",
    "会社設立記念",
    "sự kiện tri ân",
    "su kien tri an",
)
EVENT_MONTH_TOKENS = (
    "\u5165\u793e\u6708",
    "\u914d\u5e03\u6708",
    "\u7533\u8acb\u6708",
    "\u53d6\u5f97\u6708",
    "thang vao lam",
    "thang phat",
    "thang cap",
)
NEXT_EVENT_MONTH_TOKENS = ("\u7fcc\u6708", "thang tiep theo")
NEW_HIRE_DRIVER_TOKENS = (
    "\u65b0\u5165\u793e\u54e1",
    "\u914d\u5c5e\u4eba\u6570",
    "nguoi moi",
    "so nguoi vao",
    "nhan vien moi",
    "cong nhan moi",
    "new hire",
)
NEW_HIRE_PHOTO_ONLY_TOKENS = (
    "\u793e\u54e1\u8a3c\u7528\u5199\u771f\u306e\u307f",
    "\u793e\u54e1\u8a3c\u7528\u5199\u771f",
)
MANUAL_DISTRIBUTION_DRIVER_TOKENS = (
    "\u914d\u5e03\u6570",
)
ACTUAL_COUNT_DRIVER_TOKENS = (
    "\u5b9f\u969b\u306e\u53c2\u52a0\u4eba\u6570",
    "\u53c2\u52a0\u4eba\u6570",
    "\u6570\u91cf\u767a\u5b9f\u7e3e",
    "so nguoi tham gia",
    "so luong phat thuc te",
    "số người tham gia",
    "số lượng phát thực tế",
)
RECRUITMENT_HEALTH_TOKENS = (
    "採用の健康診断費",
    "採用時健診",
    "khám sức khỏe tuyển dụng",
    "khám sức khỏe khi tuyển dụng",
    "kham suc khoe tuyen dung",
    "kham suc khoe khi tuyen dung",
)
SUPPRESSED_UNIFORM_ITEM_RAW_TOKENS = (
    "\u5236\u670d",  # 制服
    "\u9577\u8896",  # 長袖
)
SUPPRESSED_UNIFORM_ITEM_NORMALIZED_TOKENS = (
    "dong phuc",
    "ao dai tay",
)
SEPARATE_COUNT_PLACEHOLDER_MARKER = "missing_separate_count=1"
SEPARATE_COUNT_PLACEHOLDER_TOKENS = (
    ("部門方針発表会後",),
    ("phuong cham bo phan", "fy2027"),
    ("社員旅行不参加",),
    ("khong the tham gia du lich",),
    ("マイエピソード",),
    ("cam nghi ve triet ly kinh doanh",),
    ("10年勤続記念コンパ",),
    ("tiec ky niem 10 nam",),
    ("10年勤続記念品",),
    ("qua ky niem", "10"),
)
FISCAL_YEAR_KICKOFF_TOKENS = (
    "決起コンパ",
    "豎ｺ襍ｷ繧ｳ",
    "khuay dong nam tai chinh",
    "khuấy động năm tài chính",
)
DEPARTMENT_POLICY_KICKOFF_TOKENS = (
    "部門方針",
    "phuong cham bo phan",
    "phương châm bộ phận",
)
YEAR_END_PARTY_SUBSIDY_TOKENS = (
    "忘年会補助金",
    "ho tro tiec tat nien",
)
MY_EPISODE_PHILOSOPHY_TOKENS = (
    "マイエピソード",
    "cảm nghĩ về triết lý kinh doanh",
    "cam nghi ve triet ly kinh doanh",
)
MOONCAKE_TOKENS = (
    "月餅",
    "bánh trung thu",
    "banh trung thu",
)
COMPANY_FOUNDING_THANKS_EVENT_TOKENS = (
    "会社設立記念",
    "感謝イベント",
    "sự kiện tri ân",
    "su kien tri an",
    "thành lập công ty",
    "thanh lap cong ty",
)
LUCKY_MONEY_TOKENS = (
    "お年玉",
    "tiền lì xì",
    "tien li xi",
)
COMPANY_TRIP_TOKENS = (
    "du lịch công ty",
    "du lich cong ty",
)
FIXED_HEADCOUNT_RULE_SPECS = (
    (MOONCAKE_TOKENS, 9, 9),
    (COMPANY_FOUNDING_THANKS_EVENT_TOKENS, 10, 10),
    (LUCKY_MONEY_TOKENS, 2, 2),
    (COMPANY_TRIP_TOKENS, 5, 5),
)
BUS_RULE_SPECS = {
    "bus_expat_count": {
        "tokens": ("出向者通勤送迎費", "xe dua don cho nguoi nhat", "xe đưa đón cho người nhật"),
        "form_row": 53,
        "label": "expat bus",
    },
    "bus_vietnamese_count": {
        "tokens": ("ローカル通勤送迎費", "xe dua don cho nguoi viet", "xe đưa đón cho người việt"),
        "form_row": 54,
        "label": "Vietnamese bus",
    },
}
BUS_UNIT_PRICE_SPECS = {
    "bus_expat_count": {
        "tokens": ("出向者送迎費", "xe dua don nguoi nhat", "xe đưa đón người nhật"),
        "source_workbook": "総務課 FY2027 MP 振替予定.xlsx",
        "source_sheet": "FY2027予定",
        "source_cells": "B9:M9",
    },
    "bus_vietnamese_count": {
        "tokens": ("ローカル社員送迎費", "xe dua don nguoi viet", "xe đưa đón người việt"),
        "source_workbook": "総務課 FY2027 MP 振替予定.xlsx",
        "source_sheet": "FY2027予定",
        "source_cells": "B10:M10",
    },
}


class AllocationEngine:
    def __init__(self, conn: sqlite3.Connection, target_cc: object | None = None):
        self.conn = conn
        self.target_cc = str(target_cc).strip() if target_cc is not None else None
        self.sys_params = self._load_sys_params()
        self.cost_centers = self._load_cost_centers()
        if self.target_cc and not self.cost_centers:
            raise ValueError(f"Không tìm thấy mã bộ phận trong danh mục hiện hành: {self.target_cc}")
        fy_str = self.sys_params.get("fiscal_year", "FY2027")
        self.fiscal_year = int(fy_str.replace("FY", ""))
        self.fy_months = helpers.get_fy_months(self.fiscal_year)
        self.period_index = {p: i for i, p in enumerate(self.fy_months)}
        self.hc_cache = self._load_headcount_cache()
        self.bus_driver_cache = self._load_bus_driver_cache()
        self.bus_unit_price_cache = self._load_bus_unit_price_cache()
        self._missing_input_keys: set[tuple[str, str, str, str]] = set()
        self._account_resolution_cache: dict[tuple[str, str, str, int | None], int | None] = {}

    def _normalize_text(self, value: str) -> str:
        text = unicodedata.normalize("NFKD", str(value or ""))
        text = "".join(ch for ch in text if not unicodedata.combining(ch))
        text = text.replace("\n", " ").replace("\u3000", " ").strip().lower()
        return " ".join(text.split())

    def _load_sys_params(self) -> dict[str, str]:
        rows = self.conn.execute("SELECT key, value FROM sys_params").fetchall()
        return {row["key"]: row["value"] for row in rows}

    def _load_cost_centers(self):
        if self.target_cc:
            return self.conn.execute(
                "SELECT * FROM dim_cost_centers WHERE CAST(code AS TEXT) = ? ORDER BY seq_no",
                (self.target_cc,),
            ).fetchall()
        return self.conn.execute("SELECT * FROM dim_cost_centers ORDER BY seq_no").fetchall()

    def _load_headcount_cache(self) -> dict[tuple[str, str], dict[str, float | str]]:
        """Load staffing through the canonical field-level source policy."""
        canonical = load_canonical_headcount(self.conn, self.fiscal_year)
        return {
            key: {
                "headcount_all": row.headcount_all,
                "headcount_expat": row.headcount_expat,
                "headcount_staff": row.headcount_staff,
                "headcount_worker": row.headcount_worker,
                "headcount_male": row.headcount_male,
                "headcount_female": row.headcount_female,
                "staffing_source": row.staffing_source,
                "split_status": row.split_status,
                "gender_source": row.gender_source,
            }
            for key, row in canonical.items()
        }

    def _load_bus_driver_cache(self) -> dict[str, dict[str, float]]:
        rows = self.conn.execute(
            """
            SELECT cc_code, bus_expat_count, bus_vietnamese_count
            FROM fact_bus_headcount_drivers
            WHERE source = 'manual'
            """
        ).fetchall()
        return {
            str(row["cc_code"]).strip(): {
                "bus_expat_count": float(row["bus_expat_count"] or 0.0),
                "bus_vietnamese_count": float(row["bus_vietnamese_count"] or 0.0),
            }
            for row in rows
        }

    def _load_bus_unit_price_cache(self) -> dict[str, dict[str, float]]:
        rows = self.conn.execute(
            """
            SELECT period, description, amount_vnd
            FROM fact_input_data
            WHERE source = 'ga_unit_price'
              AND amount_vnd > 0
            """
        ).fetchall()
        cache: dict[str, dict[str, float]] = {driver_key: {} for driver_key in BUS_UNIT_PRICE_SPECS}
        ambiguous: set[tuple[str, str]] = set()
        for row in rows:
            description = self._normalize_text(row["description"] or "")
            period = str(row["period"] or "").strip()
            if period not in self.period_index:
                continue
            amount = float(row["amount_vnd"] or 0.0)
            if amount <= 0:
                continue
            for driver_key, spec in BUS_UNIT_PRICE_SPECS.items():
                tokens = tuple(self._normalize_text(token) for token in spec["tokens"])
                if not any(token in description for token in tokens):
                    continue
                existing = cache[driver_key].get(period)
                if existing is not None and abs(existing - amount) > 1e-9:
                    ambiguous.add((driver_key, period))
                    cache[driver_key].pop(period, None)
                    continue
                if (driver_key, period) not in ambiguous:
                    cache[driver_key][period] = amount
        return cache

    @staticmethod
    def _is_valid_account_code(value) -> bool:
        """Account code hợp lệ: not None, not empty, not 0, not '0'."""
        if value is None:
            return False
        if isinstance(value, str):
            return value.strip() not in ("", "0")
        return value != 0

    def _get_account_for_cc(self, cost_type: str, mfg_acc: int, ga_acc: int, sales_acc: int) -> int | None:
        text = str(cost_type or "")
        if "製造" in text:
            return mfg_acc if self._is_valid_account_code(mfg_acc) else None
        if "販売" in text:
            return sales_acc if self._is_valid_account_code(sales_acc) else None
        # Unknown / 一般 cost_type → ga_acc (existing behavior)
        return ga_acc if self._is_valid_account_code(ga_acc) else None

    def _get_monthly_hc(self, cc_code: object, period: str, driver_type: str) -> float:
        cc_key = str(cc_code).strip()
        row = self.hc_cache.get((cc_key, period))
        if row:
            value = row.get(driver_type)
            if value is None:
                value = row.get("headcount_all", 0.0)
            return float(value or 0.0)

        cc = next((x for x in self.cost_centers if str(x["code"]).strip() == cc_key), None)
        if not cc:
            return 0.0
        if driver_type == "headcount_staff":
            return float(cc["staff_count"] or 0)
        if driver_type == "headcount_worker":
            return float(cc["worker_count"] or 0)
        if driver_type in ("headcount_male", "headcount_female"):
            return 0.0
        return float((cc["staff_count"] or 0) + (cc["worker_count"] or 0))

    def _get_canonical_monthly_hc(self, cc_code: object, period: str, driver_type: str) -> float | None:
        cc_key = str(cc_code).strip()
        row = self.hc_cache.get((cc_key, period))
        if row is None:
            return None
        value = row.get(driver_type)
        if value is None:
            if driver_type in ("headcount_staff", "headcount_worker"):
                raise HeadcountSourceError(
                    f"CC {cc_key}, kỳ {period}: nguồn chỉ có tổng người local; "
                    f"chưa có tách Nhân viên/Công nhân cho driver {driver_type}."
                )
            value = row.get("headcount_all", 0.0)
        return float(value or 0.0)

    def _get_prev_period(self, period: str) -> str | None:
        idx = self.period_index.get(period)
        if idx is not None and idx > 0:
            return self.fy_months[idx - 1]
        text = str(period or "").strip()
        if len(text) != 6 or not text.isdigit():
            return None
        year = int(text[:4])
        month = int(text[4:])
        if month < 1 or month > 12:
            return None
        if month == 1:
            return f"{year - 1}12"
        return f"{year}{month - 1:02d}"

    def _get_working_days(self, period: str) -> float:
        raw = self.sys_params.get(f"working_days_{period}")
        try:
            val = float(raw) if raw is not None else 20.0
        except (TypeError, ValueError):
            val = 20.0
        return val if val > 0 else 20.0

    def _extract_month_numbers(self, text: str) -> set[int]:
        values: set[int] = set()
        for m in re.findall(r"([1-9]|1[0-2])\s*月", text):
            values.add(int(m))
        for m in re.findall(r"(?<!\d)([1-9]|1[0-2])(?!\d)", text):
            values.add(int(m))
        return values

    def _resolve_target_periods(self, posting_month: str | None) -> list[str]:
        if posting_month is None:
            return self.fy_months
        text = str(posting_month).strip()
        if not text:
            return self.fy_months
        lower_text = text.lower()

        if text == "-":
            return []
        if any(token in lower_text for token in ("moi thang", "hang thang", "every month", "everymonth")) or "毎月" in text:
            return self.fy_months

        months = self._extract_month_numbers(text)
        if months:
            return [p for p in self.fy_months if int(p[-2:]) in months]

        # Event markers still evaluate per month (by event delta).
        if any(token in text for token in EVENT_MONTH_TOKENS + NEXT_EVENT_MONTH_TOKENS):
            return self.fy_months
        if any(token in lower_text for token in EVENT_MONTH_TOKENS + NEXT_EVENT_MONTH_TOKENS):
            return self.fy_months
        return self.fy_months

    def _is_event_month_rule(self, posting_month: str | None) -> bool:
        if not posting_month:
            return False
        raw_text = str(posting_month)
        lower_text = raw_text.lower()
        return any(token in raw_text for token in EVENT_MONTH_TOKENS) or any(
            token in lower_text for token in EVENT_MONTH_TOKENS
        )

    def _is_next_event_month_rule(self, posting_month: str | None) -> bool:
        if not posting_month:
            return False
        raw_text = str(posting_month)
        lower_text = raw_text.lower()
        return any(token in raw_text for token in NEXT_EVENT_MONTH_TOKENS) or any(
            token in lower_text for token in NEXT_EVENT_MONTH_TOKENS
        )

    def _is_mixed_event_and_fixed_month_rule(self, posting_month: str | None) -> bool:
        if not posting_month:
            return False
        return bool(self._extract_month_numbers(str(posting_month))) and (
            self._is_event_month_rule(posting_month) or self._is_next_event_month_rule(posting_month)
        )

    def _is_new_hire_driven_rule(self, rule, posting_month: str | None = None) -> bool:
        raw_text = " ".join(
            str(rule[key] or "")
            for key in ("item_name", "driver_raw", "posting_month")
            if key in rule.keys()
        )
        normalized_text = self._normalize_text(raw_text)
        if any(token in raw_text for token in NEW_HIRE_DRIVER_TOKENS):
            return True
        if any(token in normalized_text for token in NEW_HIRE_DRIVER_TOKENS):
            return True
        return self._is_event_month_rule(posting_month) or self._is_next_event_month_rule(posting_month)

    def _is_new_hire_photo_only_rule(self, rule) -> bool:
        raw_text = str(rule["item_name"] or "")
        normalized_text = self._normalize_text(raw_text)
        has_photo_only = any(token in raw_text for token in NEW_HIRE_PHOTO_ONLY_TOKENS) or any(
            token in normalized_text for token in NEW_HIRE_PHOTO_ONLY_TOKENS
        )
        if not has_photo_only:
            return False
        return True

    def _clear_allocator_missing_inputs(self) -> None:
        if self.target_cc:
            self.conn.execute(
                "DELETE FROM fact_missing_inputs WHERE source = 'allocator' AND CAST(cc_code AS TEXT) = ?",
                (self.target_cc,),
            )
            return
        self.conn.execute("DELETE FROM fact_missing_inputs WHERE source = 'allocator'")

    def _record_event_delta_missing(
        self,
        cc_code: object,
        period: str,
        prev_period: str | None,
        driver_type: str,
        rule,
        missing_parts: tuple[str, ...],
    ) -> None:
        cc_key = str(cc_code).strip()
        rule_id = int(rule["id"]) if rule is not None and rule["id"] is not None else None
        prev_text = prev_period or ""
        key = (cc_key, period, prev_text, driver_type)
        if key in self._missing_input_keys:
            return
        self._missing_input_keys.add(key)

        missing_text = ",".join(missing_parts) if missing_parts else "unknown"
        message = (
            "Missing complete monthly headcount driver for event-delta allocation: "
            f"cc={cc_key}, month={period}, previous_month={prev_text}, "
            f"category={driver_type}, missing={missing_text}"
        )
        action = (
            "Provide monthly headcount for both the event month and previous month "
            "before using event-delta allocation."
        )
        self.conn.execute(
            """
            INSERT INTO fact_missing_inputs
            (severity, cc_code, period, area, message, action, source, rule_id)
            VALUES ('action', ?, ?, 'headcount_event_delta', ?, ?, 'allocator', ?)
            """,
            (cc_key, period, message, action, rule_id),
        )

    def _bus_rule_kind(self, rule) -> str | None:
        item_name = self._normalize_text(rule["item_name"] or "")
        for driver_key, spec in BUS_RULE_SPECS.items():
            normalized_tokens = tuple(self._normalize_text(token) for token in spec["tokens"])
            if any(token in item_name for token in normalized_tokens):
                return driver_key
        return None

    def _bus_rule_for_driver(self, driver_key: str):
        matches = []
        for rule in self.conn.execute("SELECT * FROM map_allocation_rules").fetchall():
            if self._bus_rule_kind(rule) == driver_key:
                matches.append(rule)
        if len(matches) == 1:
            return matches[0]
        return None

    def _record_bus_missing(self, cc_code: object, driver_key: str, missing_input: str, rule=None) -> None:
        cc_key = str(cc_code).strip()
        key = (cc_key, "FY", driver_key, missing_input)
        if key in self._missing_input_keys:
            return
        self._missing_input_keys.add(key)

        spec = BUS_RULE_SPECS.get(driver_key, {})
        rule_id = int(rule["id"]) if rule is not None and rule["id"] is not None else None
        message = f"Missing bus allocation input: cc={cc_key}, driver_type={driver_key}, missing={missing_input}"
        action = (
            f"Provide {missing_input} for {spec.get('label', driver_key)} before bus allocation can be generated."
        )
        self.conn.execute(
            """
            INSERT INTO fact_missing_inputs
            (severity, cc_code, period, area, message, action, source, rule_id)
            VALUES ('action', ?, ?, 'bus_headcount_driver', ?, ?, 'allocator', ?)
            """,
            (cc_key, ",".join(self.fy_months), message, action, rule_id),
        )

    def _record_manual_driver_missing(
        self,
        cc_code: object,
        period: str,
        area: str,
        reason: str,
        rule,
    ) -> None:
        cc_key = str(cc_code).strip()
        rule_id = int(rule["id"]) if rule is not None and rule["id"] is not None else None
        period_text = str(period or "").strip() or ",".join(self.fy_months)
        key = (cc_key, period_text, area, str(rule_id or ""))
        if key in self._missing_input_keys:
            return
        self._missing_input_keys.add(key)

        item_name = str(rule["item_name"] or "").replace("\n", " ").strip() if rule is not None else ""
        message = (
            "Missing manual event/distribution driver for allocation rule: "
            f"cc={cc_key}, period={period_text}, rule_id={rule_id}, item={item_name}, reason={reason}"
        )
        action = (
            "Provide an explicit event/distribution count or amount in event_drivers_manual.csv "
            "for this cost center and target month. The allocator does not infer actual "
            "participant/distribution counts from total headcount."
        )
        self.conn.execute(
            """
            INSERT INTO fact_missing_inputs
            (severity, cc_code, period, area, message, action, source, rule_id)
            VALUES ('action', ?, ?, ?, ?, ?, 'allocator', ?)
            """,
            (cc_key, period_text, area, message, action, rule_id),
        )

    def _record_rule_missing_for_all_cost_centers(
        self,
        rule,
        *,
        area: str,
        reason: str,
        periods: list[str] | None = None,
    ) -> None:
        target_periods = periods or [",".join(self.fy_months)]
        for cc in self.cost_centers:
            for period in target_periods:
                self._record_manual_driver_missing(cc["code"], period, area, reason, rule)

    def _bus_unit_price_for_period(self, driver_key: str, period: str, rule) -> tuple[float, str]:
        monthly_price = float(self.bus_unit_price_cache.get(driver_key, {}).get(period, 0.0) or 0.0)
        if monthly_price > 0:
            return monthly_price, "ga_unit_price"
        if rule is None:
            return 0.0, ""
        rule_price = float(rule["unit_price"] or 0.0)
        if rule_price > 0:
            return rule_price, "allocation_rules_master"
        return 0.0, ""

    def _bus_unit_price_source_metadata(self, driver_key: str, source_kind: str) -> dict[str, str]:
        if source_kind == "ga_unit_price":
            spec = BUS_UNIT_PRICE_SPECS.get(driver_key, {})
            return {
                "workbook": spec.get("source_workbook", "総務課 FY2027 MP 振替予定.xlsx"),
                "sheet": spec.get("source_sheet", "FY2027予定"),
                "cells": spec.get("source_cells", ""),
            }
        if source_kind == "allocation_rules_master":
            return {
                "workbook": "allocation_rules_master",
                "sheet": "map_allocation_rules",
                "cells": "unit_price",
            }
        return {"workbook": "", "sheet": "", "cells": ""}

    def _get_event_delta(self, cc_code: object, period: str, driver_type: str, rule=None) -> float:
        prev_period = self._get_prev_period(period)
        if not prev_period:
            self._record_event_delta_missing(
                cc_code,
                period,
                prev_period,
                driver_type,
                rule,
                ("previous",),
            )
            return 0.0
        current = self._get_canonical_monthly_hc(cc_code, period, driver_type)
        prev = self._get_canonical_monthly_hc(cc_code, prev_period, driver_type)
        missing_parts: list[str] = []
        if current is None:
            missing_parts.append("current")
        if prev is None:
            missing_parts.append("previous")
        if missing_parts:
            self._record_event_delta_missing(
                cc_code,
                period,
                prev_period,
                driver_type,
                rule,
                tuple(missing_parts),
            )
            return 0.0
        delta = current - prev
        return delta if delta > 0 else 0.0

    def _resolve_rule_driver_type(self, rule) -> str:
        driver_type = str(rule["driver_type"] or "").strip() or "headcount_all"
        if driver_type in ("headcount_male", "headcount_female"):
            return driver_type

        item_name = helpers.normalize_text(rule["item_name"] or "")
        if any(keyword in item_name for keyword in HEALTH_CHECK_KEYWORDS):
            if any(keyword in item_name for keyword in MALE_KEYWORDS):
                return "headcount_male"
            if any(keyword in item_name for keyword in FEMALE_KEYWORDS):
                return "headcount_female"
        return driver_type

    def _effective_posting_month(self, rule) -> str | None:
        raw_posting_month = str(rule["posting_month"] or "").strip()
        return raw_posting_month or None

    def _is_recruitment_health_rule(self, rule) -> bool:
        item_name = self._normalize_text(rule["item_name"] or "")
        return any(self._normalize_text(token) in item_name for token in RECRUITMENT_HEALTH_TOKENS)

    def _recruitment_health_new_hires(self, cc_code: object, source_period: str, rule) -> tuple[float, float]:
        staff_new = self._get_event_delta(cc_code, source_period, "headcount_staff", rule=rule)
        worker_new = self._get_event_delta(cc_code, source_period, "headcount_worker", rule=rule)
        return staff_new, worker_new

    def _requires_manual_event_source(self, rule) -> bool:
        if self._is_recruitment_health_rule(rule):
            return False
        if self._is_fixed_headcount_override_rule(rule):
            return False
        raw_item_name = str(rule["item_name"] or "")
        normalized_item_name = self._normalize_text(raw_item_name)
        if any(token in raw_item_name for token in MANUAL_EVENT_ITEM_TOKENS):
            return True
        if any(token in normalized_item_name for token in MANUAL_EVENT_ITEM_TOKENS):
            return True
        return False

    def _is_suppressed_uniform_rule(self, rule) -> bool:
        raw_item_name = str(rule["item_name"] or "")
        normalized_item_name = self._normalize_text(raw_item_name)
        if any(token in raw_item_name for token in SUPPRESSED_UNIFORM_ITEM_RAW_TOKENS):
            return True
        return any(token in normalized_item_name for token in SUPPRESSED_UNIFORM_ITEM_NORMALIZED_TOKENS)

    def _requires_separate_count_placeholder(self, rule) -> bool:
        if self._is_fixed_headcount_override_rule(rule):
            return False
        normalized_item_name = self._normalize_text(rule["item_name"] or "")
        for token_group in SEPARATE_COUNT_PLACEHOLDER_TOKENS:
            if all(self._normalize_text(token) in normalized_item_name for token in token_group):
                return True
        return False

    def _fixed_headcount_rule_spec(self, rule) -> tuple[tuple[str, ...], int, int] | None:
        normalized_item_name = self._normalize_text(rule["item_name"] or "")
        for spec in FIXED_HEADCOUNT_RULE_SPECS:
            tokens, _target_month, _source_month = spec
            if any(self._normalize_text(token) in normalized_item_name for token in tokens):
                return spec
        return None

    def _is_fixed_headcount_override_rule(self, rule) -> bool:
        return self._fixed_headcount_rule_spec(rule) is not None

    def _is_fiscal_year_kickoff_rule(self, rule) -> bool:
        normalized_item_name = self._normalize_text(rule["item_name"] or "")
        has_kickoff = any(self._normalize_text(token) in normalized_item_name for token in FISCAL_YEAR_KICKOFF_TOKENS)
        has_department_policy = any(
            self._normalize_text(token) in normalized_item_name for token in DEPARTMENT_POLICY_KICKOFF_TOKENS
        )
        return has_kickoff and not has_department_policy

    def _fiscal_period_for_month_number(self, month_number: int) -> str | None:
        for period in self.fy_months:
            if int(str(period)[-2:]) == int(month_number):
                return period
        return None

    def _fixed_month_headcount_override(self, rule) -> tuple[int, int] | None:
        fixed_headcount_spec = self._fixed_headcount_rule_spec(rule)
        if fixed_headcount_spec:
            _tokens, target_month, source_month = fixed_headcount_spec
            return target_month, source_month
        normalized_item_name = self._normalize_text(rule["item_name"] or "")
        if self._is_fiscal_year_kickoff_rule(rule):
            return 5, 4
        if any(self._normalize_text(token) in normalized_item_name for token in YEAR_END_PARTY_SUBSIDY_TOKENS):
            return 2, 1
        return None

    def _has_manual_event_driver_for_rule(self, cc_code: object, period: str, rule) -> bool:
        item_name = self._normalize_text(rule["item_name"] or "")
        rows = self.conn.execute(
            """
            SELECT description
            FROM fact_input_data
            WHERE source = 'manual_event_driver'
              AND cc_code = ?
              AND period = ?
            """,
            (str(cc_code).strip(), str(period)),
        ).fetchall()
        for row in rows:
            description = self._normalize_text(row["description"] or "")
            if item_name and (item_name in description or description in item_name):
                return True
            for token_group in SEPARATE_COUNT_PLACEHOLDER_TOKENS:
                if all(self._normalize_text(token) in description for token in token_group):
                    return True
        return False

    def _insert_separate_count_placeholders(self, cursor, rule, target_periods: list[str]) -> None:
        unit_price = float(rule["unit_price"] or 0.0)
        if unit_price <= 0:
            self._record_rule_missing_for_all_cost_centers(
                rule,
                area="manual_event_driver",
                reason="separate-count event has no unit price for placeholder formula",
                periods=target_periods or None,
            )
            return

        rows_to_insert = []
        for period in target_periods:
            for cc in self.cost_centers:
                cc_code = str(cc["code"]).strip()
                if self._has_manual_event_driver_for_rule(cc_code, period, rule):
                    continue
                target_acc = self._get_account_for_cc(
                    str(cc["cost_type"]),
                    rule["mfg_account"],
                    rule["ga_account"],
                    rule["sales_account"],
                )
                if not target_acc:
                    continue
                formula = f"0*{self._format_formula_number(unit_price)}"
                description = (
                    f"Alloc: {rule['item_name']}|formula_expr={formula}|"
                    f"{SEPARATE_COUNT_PLACEHOLDER_MARKER}|status=NEEDS_SEPARATE_COUNT"
                )
                rows_to_insert.append(
                    (
                        f"alloc_{int(rule['id'])}",
                        period,
                        0.0,
                        cc_code,
                        int(target_acc),
                        None,
                        description,
                    )
                )
        if rows_to_insert:
            cursor.executemany(
                """
                INSERT INTO fact_input_data
                (source, period, amount_vnd, cc_code, account_code, form_row, scenario_id, description)
                VALUES (?, ?, ?, ?, ?, ?, 'base', ?)
                """,
                rows_to_insert,
            )

    def _requires_manual_distribution_count(self, rule) -> bool:
        # Hybrid rules with both event-month and fixed-month instructions are
        # computed from monthly headcount deltas plus fixed-month headcount.
        if self._is_mixed_event_and_fixed_month_rule(rule["posting_month"]):
            return False
        if self._is_fixed_headcount_override_rule(rule):
            return False
        driver_raw = str(rule["driver_raw"] or "")
        normalized_driver = self._normalize_text(driver_raw)
        return any(token in driver_raw for token in MANUAL_DISTRIBUTION_DRIVER_TOKENS) or any(
            self._normalize_text(token) in normalized_driver for token in ACTUAL_COUNT_DRIVER_TOKENS
        )

    def run_allocation(self) -> dict:
        print("Bắt đầu tính phân bổ...")
        self._map_direct_costs()
        self._process_allocation_rules()
        self._process_bus_headcount_drivers()
        self.conn.commit()
        return {"status": "success"}

    def _map_direct_costs(self) -> dict[str, int]:
        cursor = self.conn.cursor()
        where = "(account_code IS NULL OR account_code = 0) AND source <> 'ga_unit_price'"
        params: tuple[object, ...] = ()
        if self.target_cc:
            where += " AND CAST(cc_code AS TEXT) = ?"
            params = (self.target_cc,)
        raw_rows = cursor.execute(
            f"""
            SELECT id, source, cc_code, description, form_row
            FROM fact_input_data
            WHERE {where}
            """,
            params,
        ).fetchall()

        updates: list[tuple[int, int]] = []
        unresolved = 0
        for row in raw_rows:
            cache_key = (
                str(row["source"] or ""),
                str(row["cc_code"] or "").strip(),
                str(row["description"] or ""),
                int(row["form_row"]) if row["form_row"] is not None else None,
            )
            if cache_key not in self._account_resolution_cache:
                try:
                    self._account_resolution_cache[cache_key] = resolve_account_code_for_source(
                        self.conn,
                        cache_key[0],
                        cache_key[1],
                        description=cache_key[2],
                        form_row=cache_key[3],
                    )
                except AccountResolutionError:
                    self._account_resolution_cache[cache_key] = None
            target_code = self._account_resolution_cache[cache_key]
            if target_code is None:
                unresolved += 1
                continue
            updates.append((target_code, int(row["id"])))

        if updates:
            cursor.executemany("UPDATE fact_input_data SET account_code = ? WHERE id = ?", updates)
        scope = f" của CC {self.target_cc}" if self.target_cc else ""
        print(f"Đã xác định tài khoản kế toán cho {len(updates)} bản ghi{scope}; chưa xác định: {unresolved}.")
        return {"examined": len(raw_rows), "mapped": len(updates), "unresolved": unresolved}

    def _process_allocation_rules(self):
        self._missing_input_keys.clear()
        self._clear_allocator_missing_inputs()
        rules = self.conn.execute("SELECT * FROM map_allocation_rules").fetchall()
        cursor = self.conn.cursor()

        for rule in rules:
            if self._bus_rule_kind(rule) is not None:
                continue
            if self._is_suppressed_uniform_rule(rule):
                continue
            if self._requires_separate_count_placeholder(rule):
                target_periods = self._resolve_target_periods(self._effective_posting_month(rule))
                if not target_periods:
                    self._record_rule_missing_for_all_cost_centers(
                        rule,
                        area="manual_event_driver",
                        reason="posting month is blank/dash or cannot be resolved from source",
                    )
                    continue
                self._insert_separate_count_placeholders(cursor, rule, target_periods)
                continue
            if self._requires_manual_event_source(rule):
                target_periods = self._resolve_target_periods(self._effective_posting_month(rule))
                self._record_rule_missing_for_all_cost_centers(
                    rule,
                    area="manual_event_driver",
                    reason="event requires explicit actual count/amount input",
                    periods=target_periods or None,
                )
                continue
            if self._requires_manual_distribution_count(rule):
                target_periods = self._resolve_target_periods(self._effective_posting_month(rule))
                self._record_rule_missing_for_all_cost_centers(
                    rule,
                    area="manual_distribution_driver",
                    reason="actual participant/distribution count cannot be inferred from headcount",
                    periods=target_periods or None,
                )
                continue

            if self._is_recruitment_health_rule(rule):
                unit_price = float(rule["unit_price"] or 0.0)
                for target_period in self.fy_months:
                    source_period = self._get_prev_period(target_period)
                    if not source_period:
                        continue
                    for cc in self.cost_centers:
                        staff_new, worker_new = self._recruitment_health_new_hires(cc["code"], source_period, rule)
                        total_new = staff_new + worker_new
                        target_acc = self._get_account_for_cc(
                            str(cc["cost_type"]), rule["mfg_account"], rule["ga_account"], rule["sales_account"]
                        )
                        if not target_acc:
                            continue
                        formula = (
                            f"({self._format_formula_number(staff_new)}+"
                            f"{self._format_formula_number(worker_new)})*"
                            f"{self._format_formula_number(unit_price)}"
                        )
                        description = (
                            f"Alloc: {rule['item_name']}|business_identity=recruitment_health|"
                            f"source_month={source_period}|posting_rule=next_month|"
                            f"new_staff={self._format_formula_number(staff_new)}|"
                            f"new_worker={self._format_formula_number(worker_new)}|"
                            f"driver_value={self._format_formula_number(total_new)}|formula_expr={formula}"
                        )
                        cursor.execute(
                            """
                            INSERT INTO fact_input_data
                            (source, period, amount_vnd, cc_code, account_code, form_row, scenario_id, description)
                            VALUES (?, ?, ?, ?, ?, NULL, 'base', ?)
                            """,
                            (
                                f"alloc_{int(rule['id'])}", target_period, total_new * unit_price,
                                str(cc["code"]).strip(), int(target_acc), description,
                            ),
                        )
                continue

            unit_price = float(rule["unit_price"] or 0.0)
            if unit_price <= 0:
                continue

            posting_month = self._effective_posting_month(rule)
            fixed_month_override = self._fixed_month_headcount_override(rule)
            source_period = None
            if fixed_month_override:
                target_month, source_month = fixed_month_override
                target_period = self._fiscal_period_for_month_number(target_month)
                source_period = self._fiscal_period_for_month_number(source_month)
                target_periods = [target_period] if target_period and source_period else []
            else:
                target_periods = self._resolve_target_periods(posting_month)
            if not target_periods:
                self._record_rule_missing_for_all_cost_centers(
                    rule,
                    area="manual_event_driver",
                    reason="posting month is blank/dash or cannot be resolved from source",
                )
                continue

            driver_type = self._resolve_rule_driver_type(rule)
            if fixed_month_override:
                driver_type = "headcount_all"
            new_hire_driven = self._is_new_hire_driven_rule(rule, posting_month)
            if fixed_month_override:
                new_hire_driven = False
            if new_hire_driven and self._is_new_hire_photo_only_rule(rule):
                continue
            mixed_event_fixed_month = self._is_mixed_event_and_fixed_month_rule(posting_month)
            fixed_month_numbers = self._extract_month_numbers(str(posting_month or "")) if mixed_event_fixed_month else set()
            if mixed_event_fixed_month:
                target_periods = self.fy_months
            for period in target_periods:
                for cc in self.cost_centers:
                    if driver_type == "working_days":
                        driver_val = self._get_working_days(period)
                    elif mixed_event_fixed_month:
                        driver_val = 0.0
                        if self._is_event_month_rule(posting_month):
                            driver_val += self._get_event_delta(cc["code"], period, driver_type, rule=rule)
                        elif self._is_next_event_month_rule(posting_month):
                            prev_period = self._get_prev_period(period)
                            if prev_period:
                                driver_val += self._get_event_delta(cc["code"], prev_period, driver_type, rule=rule)
                        if int(str(period)[-2:]) in fixed_month_numbers:
                            driver_val += self._get_monthly_hc(cc["code"], period, driver_type)
                    else:
                        if self._is_next_event_month_rule(posting_month):
                            prev_period = self._get_prev_period(period)
                            if not prev_period:
                                continue
                            driver_val = self._get_event_delta(cc["code"], prev_period, driver_type, rule=rule)
                        elif self._is_event_month_rule(posting_month) or new_hire_driven:
                            driver_val = self._get_event_delta(cc["code"], period, driver_type, rule=rule)
                        elif fixed_month_override and source_period:
                            driver_val = self._get_monthly_hc(cc["code"], source_period, driver_type)
                        else:
                            driver_val = self._get_monthly_hc(cc["code"], period, driver_type)

                    if driver_val <= 0:
                        continue

                    target_acc = self._get_account_for_cc(
                        str(cc["cost_type"]),
                        rule["mfg_account"],
                        rule["ga_account"],
                        rule["sales_account"],
                    )
                    if not target_acc:
                        continue

                    amount_vnd = unit_price * float(driver_val)
                    if amount_vnd <= 0:
                        continue
                    formula = f"{self._format_formula_number(driver_val)}*{self._format_formula_number(unit_price)}"
                    cursor.execute(
                        """
                        INSERT INTO fact_input_data
                        (source, period, amount_vnd, cc_code, account_code, description)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            f"alloc_{rule['id']}",
                            period,
                            amount_vnd,
                            str(cc["code"]).strip(),
                            int(target_acc),
                            (
                                f"Alloc: {rule['item_name']}|source_month={source_period}"
                                f"|driver_month={source_period[:4]}-{source_period[-2:]}"
                                f"|driver_type={driver_type}|driver_value={self._format_formula_number(driver_val)}"
                                f"|formula_expr={formula}"
                                if fixed_month_override and source_period
                                else f"Alloc: {rule['item_name']}"
                            ),
                        ),
                    )

    def _process_bus_headcount_drivers(self) -> None:
        cursor = self.conn.cursor()
        for driver_key, spec in BUS_RULE_SPECS.items():
            rule = self._bus_rule_for_driver(driver_key)
            for cc in self.cost_centers:
                cc_code = str(cc["code"]).strip()
                driver_row = self.bus_driver_cache.get(cc_code)
                if driver_row is None:
                    self._record_bus_missing(cc_code, driver_key, driver_key, rule=rule)
                    continue

                driver_value = float(driver_row.get(driver_key, 0.0) or 0.0)
                if driver_value <= 0:
                    continue

                if rule is None:
                    self._record_bus_missing(cc_code, driver_key, "account mapping", rule=None)
                    continue

                target_acc = self._get_account_for_cc(
                    str(cc["cost_type"]),
                    rule["mfg_account"],
                    rule["ga_account"],
                    rule["sales_account"],
                )
                if not target_acc:
                    self._record_bus_missing(cc_code, driver_key, "account mapping", rule=rule)
                    continue

                rows_to_insert = []
                for period in self.fy_months:
                    unit_price, source_kind = self._bus_unit_price_for_period(driver_key, period, rule)
                    if unit_price <= 0:
                        missing_name = (
                            "expat bus unit_price"
                            if driver_key == "bus_expat_count"
                            else "Vietnamese bus unit_price"
                        )
                        self._record_bus_missing(cc_code, driver_key, missing_name, rule=rule)
                        continue

                    amount_vnd = driver_value * unit_price
                    if amount_vnd <= 0:
                        continue

                    source_meta = self._bus_unit_price_source_metadata(driver_key, source_kind)
                    formula = f"{self._format_formula_number(driver_value)}*{self._format_formula_number(unit_price)}"
                    description = (
                        f"Alloc: {rule['item_name']}|driver_type={driver_key}"
                        f"|driver_value={self._format_formula_number(driver_value)}"
                        f"|unit_price_key={rule['item_name']}|unit_price_source={source_kind}"
                        f"|source_workbook={source_meta['workbook']}|source_sheet={source_meta['sheet']}"
                        f"|source_cells={source_meta['cells']}|provenance=bus_headcount_manual"
                        f"|status=OK|formula_expr={formula}"
                    )
                    rows_to_insert.append(
                        (
                            f"alloc_{int(rule['id'])}",
                            period,
                            amount_vnd,
                            cc_code,
                            int(target_acc),
                            int(spec["form_row"]),
                            description,
                        )
                    )

                if rows_to_insert:
                    cursor.executemany(
                        """
                        INSERT INTO fact_input_data
                        (source, period, amount_vnd, cc_code, account_code, form_row, scenario_id, description)
                        VALUES (?, ?, ?, ?, ?, ?, 'base', ?)
                        """,
                        rows_to_insert,
                    )

    def _format_formula_number(self, value: float) -> str:
        number = float(value or 0.0)
        if abs(number - round(number)) < 1e-9:
            return str(int(round(number)))
        return f"{number:.6f}".rstrip("0").rstrip(".")

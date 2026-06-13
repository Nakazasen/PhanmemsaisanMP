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
from src.utils import excel_helpers as helpers

HEALTH_CHECK_KEYWORDS = ("kham suc khoe", "khám sức khỏe", "健康診断")
MALE_KEYWORDS = ("cho cnv nam", " nam)", " male", "男")
FEMALE_KEYWORDS = ("cho cnv nu", "cho cnv nữ", " nu)", " nữ)", " female", "女")
POSTING_MONTH_ITEM_OVERRIDES = (
    (("部門方針発表会後の決起コンパ", "phương châm bộ phận"), "4月"),
    (("tiệc khuấy động năm tài chính", "quyet起コンパ", "決起コンパ"), "5月"),
    (("社員旅行不参加", "không thể tham gia du lịch"), "6月"),
    (("社員旅行 du lịch công ty", "社員旅行"), "5月"),
    (("マイエピソード", "cảm nghĩ về triết lý kinh doanh"), "7月"),
    (("京セラフェスティバル", "lễ hội kyocera"), "9月"),
    (("月餅", "bánh trung thu"), "9月"),
    (("10年勤続記念コンパ", "tiệc kỷ niệm 10 năm"), "10月"),
    (("10年勤続記念品", "quà kỷ niệm"), "10月"),
    (("ポケットカレンダー", "pocket calendar", "lịch bỏ túi"), "11月"),
    (("運動会", "đại hội thể thao"), "11月"),
    (("忘年会補助金", "hỗ trợ tiệc tất niên"), "2月"),
    (("お年玉", "tiền lì xì"), "2月"),
    (("会社設立記念", "sự kiện tri ân ngày thành lập công ty"), "10月"),
)


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
    "採用時健診",
    "khám sức khỏe khi tuyển dụng",
    "kham suc khoe khi tuyen dung",
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


class AllocationEngine:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.sys_params = self._load_sys_params()
        self.cost_centers = self._load_cost_centers()
        fy_str = self.sys_params.get("fiscal_year", "FY2027")
        self.fy_months = helpers.get_fy_months(int(fy_str.replace("FY", "")))
        self.period_index = {p: i for i, p in enumerate(self.fy_months)}
        self.hc_cache = self._load_headcount_cache()
        self.bus_driver_cache = self._load_bus_driver_cache()
        self._missing_input_keys: set[tuple[str, str, str, str]] = set()

    def _normalize_text(self, value: str) -> str:
        text = unicodedata.normalize("NFKD", str(value or ""))
        text = "".join(ch for ch in text if not unicodedata.combining(ch))
        text = text.replace("\n", " ").replace("\u3000", " ").strip().lower()
        return " ".join(text.split())

    def _load_sys_params(self) -> dict[str, str]:
        rows = self.conn.execute("SELECT key, value FROM sys_params").fetchall()
        return {row["key"]: row["value"] for row in rows}

    def _load_cost_centers(self):
        return self.conn.execute("SELECT * FROM dim_cost_centers ORDER BY seq_no").fetchall()

    def _load_headcount_cache(self) -> dict[tuple[str, str], dict[str, float]]:
        # Priority: manual > ga > others
        rows = self.conn.execute(
            """
            SELECT
                cc_code, period, headcount_all, headcount_staff, headcount_worker,
                headcount_male, headcount_female, source
            FROM fact_monthly_headcount
            ORDER BY
                CASE source
                    WHEN 'manual' THEN 3
                    WHEN 'ga' THEN 2
                    ELSE 1
                END
            """
        ).fetchall()
        cache: dict[tuple[str, str], dict[str, float]] = {}
        for row in rows:
            cache[(str(row["cc_code"]).strip(), str(row["period"]))] = {
                "headcount_all": float(row["headcount_all"] or 0.0),
                "headcount_staff": float(row["headcount_staff"] or 0.0),
                "headcount_worker": float(row["headcount_worker"] or 0.0),
                "headcount_male": float(row["headcount_male"] or 0.0),
                "headcount_female": float(row["headcount_female"] or 0.0),
            }
        return cache

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

    def _clear_allocator_missing_inputs(self) -> None:
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
        item_name = self._normalize_text(rule["item_name"] or "")
        for tokens, posting_month in POSTING_MONTH_ITEM_OVERRIDES:
            normalized_tokens = tuple(self._normalize_text(token) for token in tokens)
            if any(token in item_name for token in normalized_tokens):
                return posting_month
        raw_posting_month = str(rule["posting_month"] or "").strip()
        return raw_posting_month or None

    def _requires_manual_event_source(self, rule) -> bool:
        raw_item_name = str(rule["item_name"] or "")
        normalized_item_name = self._normalize_text(raw_item_name)
        if any(token in raw_item_name for token in MANUAL_EVENT_ITEM_TOKENS):
            return True
        if any(token in normalized_item_name for token in MANUAL_EVENT_ITEM_TOKENS):
            return True
        return False

    def run_allocation(self) -> dict:
        print("Starting Refactored Allocation Engine...")
        self._map_direct_costs()
        self._process_allocation_rules()
        self._process_bus_headcount_drivers()
        self.conn.commit()
        return {"status": "success"}

    def _map_direct_costs(self):
        cursor = self.conn.cursor()
        raw_rows = cursor.execute(
            """
            SELECT id, source, cc_code, description, form_row
            FROM fact_input_data
            WHERE account_code IS NULL OR account_code = 0
            """
        ).fetchall()

        updates: list[tuple[int, int]] = []

        for row in raw_rows:
            try:
                target_code = resolve_account_code_for_source(
                    self.conn,
                    str(row["source"] or ""),
                    row["cc_code"],
                    description=row["description"],
                    form_row=row["form_row"],
                )
            except AccountResolutionError:
                continue
            updates.append((target_code, int(row["id"])))

        if updates:
            cursor.executemany("UPDATE fact_input_data SET account_code = ? WHERE id = ?", updates)
            print(f"Mapped {len(updates)} direct cost records.")

    def _process_allocation_rules(self):
        self._missing_input_keys.clear()
        self._clear_allocator_missing_inputs()
        rules = self.conn.execute("SELECT * FROM map_allocation_rules").fetchall()
        cursor = self.conn.cursor()

        for rule in rules:
            if self._bus_rule_kind(rule) is not None:
                continue
            if self._requires_manual_event_source(rule):
                continue

            unit_price = float(rule["unit_price"] or 0.0)
            if unit_price <= 0:
                continue

            posting_month = self._effective_posting_month(rule)
            target_periods = self._resolve_target_periods(posting_month)
            if not target_periods:
                continue

            driver_type = self._resolve_rule_driver_type(rule)
            for period in target_periods:
                for cc in self.cost_centers:
                    if driver_type == "working_days":
                        driver_val = self._get_working_days(period)
                    else:
                        if self._is_next_event_month_rule(posting_month):
                            prev_period = self._get_prev_period(period)
                            if not prev_period:
                                continue
                            driver_val = self._get_event_delta(cc["code"], prev_period, driver_type, rule=rule)
                        elif self._is_event_month_rule(posting_month):
                            driver_val = self._get_event_delta(cc["code"], period, driver_type, rule=rule)
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
                            f"Alloc: {rule['item_name']}",
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

                unit_price = float(rule["unit_price"] or 0.0)
                if unit_price <= 0:
                    missing_name = "expat bus unit_price" if driver_key == "bus_expat_count" else "Vietnamese bus unit_price"
                    self._record_bus_missing(cc_code, driver_key, missing_name, rule=rule)
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

                amount_vnd = driver_value * unit_price
                if amount_vnd <= 0:
                    continue

                formula = f"{self._format_formula_number(driver_value)}*{self._format_formula_number(unit_price)}"
                description = (
                    f"Alloc: {rule['item_name']}|driver_type={driver_key}|driver_value={self._format_formula_number(driver_value)}"
                    f"|unit_price_key={rule['item_name']}|unit_price={self._format_formula_number(unit_price)}"
                    f"|formula_expr={formula}|source_workbook=allocation_rules_master|source_sheet=map_allocation_rules"
                    "|provenance=bus_headcount_manual|status=OK"
                )
                cursor.executemany(
                    """
                    INSERT INTO fact_input_data
                    (source, period, amount_vnd, cc_code, account_code, form_row, scenario_id, description)
                    VALUES (?, ?, ?, ?, ?, ?, 'base', ?)
                    """,
                    [
                        (
                            f"alloc_{int(rule['id'])}",
                            period,
                            amount_vnd,
                            cc_code,
                            int(target_acc),
                            int(spec["form_row"]),
                            description,
                        )
                        for period in self.fy_months
                    ],
                )

    def _format_formula_number(self, value: float) -> str:
        number = float(value or 0.0)
        if abs(number - round(number)) < 1e-9:
            return str(int(round(number)))
        return f"{number:.6f}".rstrip("0").rstrip(".")

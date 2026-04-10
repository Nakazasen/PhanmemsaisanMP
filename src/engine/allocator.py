"""
Allocation engine.

Responsibilities:
- map direct-cost staging rows to account_code
- generate allocation rows from map_allocation_rules
"""

import re
import sqlite3
import unicodedata

from src.utils import excel_helpers as helpers

HEALTH_CHECK_KEYWORDS = ("kham suc khoe", "khám sức khỏe", "健康診断")
MALE_KEYWORDS = ("cho cnv nam", " nam)", " male", "男")
FEMALE_KEYWORDS = ("cho cnv nu", "cho cnv nữ", " nu)", " nữ)", " female", "女")
POSTING_MONTH_ITEM_OVERRIDES = (
    (("tiệc khuấy động năm tài chính", "quyet起コンパ", "決起コンパ"), "5月"),
    (("社員旅行 du lịch công ty", "社員旅行"), "5月"),
    (("京セラフェスティバル", "lễ hội kyocera"), "9月"),
    (("月餅", "bánh trung thu"), "9月"),
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


class AllocationEngine:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.sys_params = self._load_sys_params()
        self.cost_centers = self._load_cost_centers()
        fy_str = self.sys_params.get("fiscal_year", "FY2027")
        self.fy_months = helpers.get_fy_months(int(fy_str.replace("FY", "")))
        self.period_index = {p: i for i, p in enumerate(self.fy_months)}
        self.hc_cache = self._load_headcount_cache()

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

    def _get_account_for_cc(self, cost_type: str, mfg_acc: int, ga_acc: int, sales_acc: int) -> int | None:
        text = str(cost_type or "")
        if "製造" in text:
            return mfg_acc
        if "販売" in text:
            return sales_acc
        return ga_acc

    def _get_monthly_hc(self, cc_code: object, period: str, driver_type: str) -> float:
        cc_key = str(cc_code).strip()
        row = self.hc_cache.get((cc_key, period))
        if row:
            return float(row.get(driver_type, row.get("headcount_all", 0.0)))

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

    def _get_prev_period(self, period: str) -> str | None:
        idx = self.period_index.get(period)
        if idx is None or idx == 0:
            return None
        return self.fy_months[idx - 1]

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

    def _get_event_delta(self, cc_code: object, period: str, driver_type: str) -> float:
        prev_period = self._get_prev_period(period)
        if not prev_period:
            return 0.0
        current = self._get_monthly_hc(cc_code, period, driver_type)
        prev = self._get_monthly_hc(cc_code, prev_period, driver_type)
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
        self.conn.commit()
        return {"status": "success"}

    def _find_account_row(self, keywords: tuple[str, ...]):
        rows = self.conn.execute("SELECT * FROM dim_accounts").fetchall()
        for row in rows:
            name = f"{row['name_jp'] or ''} {row['name_vn'] or ''}".lower()
            if any(k.lower() in name for k in keywords):
                return row
        return None

    def _find_account_by_code(self, account_code: int):
        return self.conn.execute("SELECT * FROM dim_accounts WHERE code = ?", (account_code,)).fetchone()

    def _row_to_target_acc(self, row, cost_type: str) -> int | None:
        if not row:
            return None
        acc_code = self._get_account_for_cc(
            cost_type,
            row["mfg_code"],
            row["ga_code"],
            row["sales_code"],
        )
        if acc_code:
            return int(acc_code)
        if row["code"]:
            return int(row["code"])
        return None

    def _map_direct_costs(self):
        cursor = self.conn.cursor()
        raw_rows = cursor.execute(
            """
            SELECT id, source, cc_code, description
            FROM fact_input_data
            WHERE account_code IS NULL OR account_code = 0
            """
        ).fetchall()

        acc_depr_building = self._find_account_by_code(5006016260)
        acc_depr_land = self._find_account_by_code(5006016261)
        acc_depr_equipment = self._find_account_by_code(5006016244)
        acc_interest = self._find_account_by_code(9114120007) or self._find_account_row(("金利", "lãi", "interest"))
        acc_electric = self._find_account_row(("電気", "electric", "điện"))
        acc_water = self._find_account_row(("水道", "water", "nước"))
        acc_it = self._find_account_by_code(5005246282) or self._find_account_row(("software", "system", "it", "通信"))
        acc_ga = self._find_account_row(("福利", "gas", "vệ sinh", "ga"))
        default_acc = self._find_account_row(("消耗", "chi phí")) or acc_ga

        updates: list[tuple[int, int]] = []

        for row in raw_rows:
            source = str(row["source"] or "")
            desc = str(row["description"] or "").lower()
            cc = next((c for c in self.cost_centers if str(c["code"]).strip() == str(row["cc_code"]).strip()), None)
            cost_type = str(cc["cost_type"]) if cc else ""

            target_row = None
            if source == "facility":
                if "depreciation_building" in desc:
                    target_row = acc_depr_building
                elif "depreciation_land" in desc:
                    target_row = acc_depr_land
                elif "interest" in desc:
                    target_row = acc_interest
                elif "electric" in desc:
                    target_row = acc_electric
                elif "water" in desc:
                    target_row = acc_water
            elif source == "fixed_assets":
                target_row = acc_interest if "interest" in desc else acc_depr_equipment
            elif source == "it_sim":
                target_row = acc_it
            elif "ga" in source:
                target_row = acc_ga

            target_code = self._row_to_target_acc(target_row or default_acc, cost_type)
            if target_code:
                updates.append((target_code, int(row["id"])))

        if updates:
            cursor.executemany("UPDATE fact_input_data SET account_code = ? WHERE id = ?", updates)
            print(f"Mapped {len(updates)} direct cost records.")

    def _process_allocation_rules(self):
        rules = self.conn.execute("SELECT * FROM map_allocation_rules").fetchall()
        cursor = self.conn.cursor()

        for rule in rules:
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
                            driver_val = self._get_event_delta(cc["code"], prev_period, driver_type)
                        elif self._is_event_month_rule(posting_month):
                            driver_val = self._get_event_delta(cc["code"], period, driver_type)
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

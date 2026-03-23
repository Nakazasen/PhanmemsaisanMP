"""
Allocation engine.

Responsibilities:
- map direct-cost staging rows to account_code
- generate allocation rows from map_allocation_rules
"""

import re
import sqlite3

from src.utils import excel_helpers as helpers


class AllocationEngine:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.sys_params = self._load_sys_params()
        self.cost_centers = self._load_cost_centers()
        fy_str = self.sys_params.get("fiscal_year", "FY2027")
        self.fy_months = helpers.get_fy_months(int(fy_str.replace("FY", "")))
        self.period_index = {p: i for i, p in enumerate(self.fy_months)}
        self.hc_cache = self._load_headcount_cache()

    def _load_sys_params(self) -> dict[str, str]:
        rows = self.conn.execute("SELECT key, value FROM sys_params").fetchall()
        return {row["key"]: row["value"] for row in rows}

    def _load_cost_centers(self):
        return self.conn.execute("SELECT * FROM dim_cost_centers ORDER BY seq_no").fetchall()

    def _load_headcount_cache(self) -> dict[tuple[int, str], dict[str, float]]:
        # Priority: manual > ga > others
        rows = self.conn.execute(
            """
            SELECT cc_code, period, headcount_all, headcount_staff, headcount_worker, source
            FROM fact_monthly_headcount
            ORDER BY
                CASE source
                    WHEN 'manual' THEN 3
                    WHEN 'ga' THEN 2
                    ELSE 1
                END
            """
        ).fetchall()
        cache: dict[tuple[int, str], dict[str, float]] = {}
        for row in rows:
            cache[(int(row["cc_code"]), str(row["period"]))] = {
                "headcount_all": float(row["headcount_all"] or 0.0),
                "headcount_staff": float(row["headcount_staff"] or 0.0),
                "headcount_worker": float(row["headcount_worker"] or 0.0),
            }
        return cache

    def _get_account_for_cc(self, cost_type: str, mfg_acc: int, ga_acc: int, sales_acc: int) -> int | None:
        text = str(cost_type or "")
        if "製造" in text:
            return mfg_acc
        if "販売" in text:
            return sales_acc
        return ga_acc

    def _get_monthly_hc(self, cc_code: int, period: str, driver_type: str) -> float:
        row = self.hc_cache.get((cc_code, period))
        if row:
            return float(row.get(driver_type, row.get("headcount_all", 0.0)))

        cc = next((x for x in self.cost_centers if int(x["code"]) == int(cc_code)), None)
        if not cc:
            return 0.0
        if driver_type == "headcount_staff":
            return float(cc["staff_count"] or 0)
        if driver_type == "headcount_worker":
            return float(cc["worker_count"] or 0)
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

        # Event markers still evaluate per month (by event delta)
        event_tokens = ("入社月", "配布月", "申請月", "取得月", "翌月", 
                        "thang vao lam", "thang tiep theo", "thang phat", "thang cap")
        if any(token in lower_text for token in event_tokens):
            return self.fy_months
        return self.fy_months

    def _is_event_month_rule(self, posting_month: str | None) -> bool:
        if not posting_month:
            return False
        text = str(posting_month).lower()
        return any(token in text for token in ("入社月", "配布月", "申請月", "取得月", 
                                             "thang vao lam", "thang phat", "thang cap"))

    def _is_next_event_month_rule(self, posting_month: str | None) -> bool:
        if not posting_month:
            return False
        return any(token in str(posting_month).lower() for token in ("翌月", "thang tiep theo"))

    def _get_event_delta(self, cc_code: int, period: str, driver_type: str) -> float:
        prev_period = self._get_prev_period(period)
        if not prev_period:
            return 0.0
        current = self._get_monthly_hc(cc_code, period, driver_type)
        prev = self._get_monthly_hc(cc_code, prev_period, driver_type)
        delta = current - prev
        return delta if delta > 0 else 0.0

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

        acc_depr = self._find_account_row(("減価償却", "khấu hao", "depreciation"))
        acc_interest = self._find_account_row(("金利", "lãi", "interest"))
        acc_electric = self._find_account_row(("電気", "electric", "điện"))
        acc_water = self._find_account_row(("水道", "water", "nước"))
        acc_it = self._find_account_row(("software", "system", "it", "通信"))
        acc_ga = self._find_account_row(("福利", "gas", "vệ sinh", "ga"))
        default_acc = self._find_account_row(("消耗", "chi phí")) or acc_ga

        updates: list[tuple[int, int]] = []

        for row in raw_rows:
            source = str(row["source"] or "")
            desc = str(row["description"] or "").lower()
            cc = next((c for c in self.cost_centers if int(c["code"]) == int(row["cc_code"])), None)
            cost_type = str(cc["cost_type"]) if cc else ""

            target_row = None
            if source == "facility":
                if "depreciation" in desc:
                    target_row = acc_depr
                elif "interest" in desc:
                    target_row = acc_interest
                elif "electric" in desc:
                    target_row = acc_electric
                elif "water" in desc:
                    target_row = acc_water
            elif source == "fixed_assets":
                target_row = acc_interest if "interest" in desc else acc_depr
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
            posting_month = str(rule["posting_month"] or "").strip()
            target_periods = self._resolve_target_periods(posting_month)
            if not target_periods:
                continue

            driver_type = str(rule["driver_type"] or "").strip()
            for period in target_periods:
                for cc in self.cost_centers:
                    if driver_type == "working_days":
                        driver_val = self._get_working_days(period)
                    else:
                        if self._is_next_event_month_rule(posting_month):
                            prev_period = self._get_prev_period(period)
                            if not prev_period:
                                continue
                            driver_val = self._get_event_delta(int(cc["code"]), prev_period, driver_type)
                        elif self._is_event_month_rule(posting_month):
                            driver_val = self._get_event_delta(int(cc["code"]), period, driver_type)
                        else:
                            driver_val = self._get_monthly_hc(int(cc["code"]), period, driver_type)

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

                    amount_vnd = float(rule["unit_price"]) * float(driver_val)
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
                            int(cc["code"]),
                            int(target_acc),
                            f"Alloc: {rule['item_name']}",
                        ),
                    )

"""
MP2027 Manager - Allocation Engine (Refactored V4.5.0)
Processes staging data and allocation rules into final, fully-mapped records.
"""
import sqlite3
import pandas as pd
from src.utils import excel_helpers as helpers

class AllocationEngine:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.sys_params = self._load_sys_params()
        self.cost_centers = self._load_cost_centers()
        self.exchange_rate = float(self.sys_params.get('exchange_rate_usd_vnd', 25450.0))
        fy_str = self.sys_params.get('fiscal_year', 'FY2027')
        self.fy_months = helpers.get_fy_months(int(fy_str.replace('FY', '')))

    def _load_sys_params(self):
        rows = self.conn.execute("SELECT key, value FROM sys_params").fetchall()
        return {r['key']: r['value'] for r in rows}

    def _load_cost_centers(self):
        return self.conn.execute("SELECT * FROM dim_cost_centers ORDER BY seq_no").fetchall()

    def _get_account_for_cc(self, cost_type: str, mfg_acc: int, ga_acc: int, sales_acc: int) -> int:
        if '製造' in cost_type: return mfg_acc
        if '販売' in cost_type: return sales_acc
        return ga_acc

    def _get_monthly_hc(self, cc_code: int, period: str, driver_type: str) -> float:
        """DYNAMIC DRIVER: Get headcount for a specific CC and Month."""
        query = "SELECT headcount_all, headcount_staff, headcount_worker FROM fact_monthly_headcount WHERE cc_code = ? AND period = ?"
        row = self.conn.execute(query, (cc_code, period)).fetchone()
        if not row:
            # Fallback to static if monthly not found (with warning)
            cc = next((c for c in self.cost_centers if c['code'] == cc_code), None)
            if not cc: return 0.0
            if driver_type == 'headcount_staff': return float(cc['staff_count'] or 0)
            if driver_type == 'headcount_worker': return float(cc['worker_count'] or 0)
            return float((cc['staff_count'] or 0) + (cc['worker_count'] or 0))
        
        if driver_type == 'headcount_staff': return row['headcount_staff']
        if driver_type == 'headcount_worker': return row['headcount_worker']
        return row['headcount_all']

    def run_allocation(self) -> dict:
        print("Starting Refactored Allocation Engine...")
        self._map_direct_costs()
        self._process_allocation_rules()
        self.conn.commit()
        return {'status': 'success'}
    def _map_direct_costs(self):
        """Map raw staging data to correct account codes using description keywords."""
        count = 0
        cursor = self.conn.cursor()
        # Ensure row-factory is set if needed, but here we assume dictionary-like access if conn is configured
        # Or we use index-based if not. Let's assume dict for clarity if already set elsewhere,
        # otherwise we'll fetchall and handle.
        try:
            self.conn.row_factory = sqlite3.Row
        except: pass
        accounts = self.conn.execute("SELECT * FROM dim_accounts").fetchall()
        
        def find_acc(keyword: str):
            for acc in accounts:
                if keyword in (acc['name_jp'] or ''):
                    return dict(acc)
            return None
            
        mapping_rules = {
            'depreciation_building': find_acc('建物'),
            'depreciation_land': find_acc('土地'),
            'interest_building': find_acc('支払利息') or find_acc('金利') or find_acc('利息'),
            'interest_land': find_acc('支払利息') or find_acc('金利') or find_acc('利息'),
            'electric': find_acc('電気'),
            'water': find_acc('水道'),
            'fixed_assets': find_acc('減価償却') or find_acc('減価'),
            'it_sim': find_acc('ソフトウエア') or find_acc('支払手数料') or find_acc('通信費'),
            'ga_unit_price': find_acc('事務用') or find_acc('消耗品') or find_acc('雑費')
        }
        
        default_acc = find_acc('雑費') or find_acc('手数料')
        
        unmapped_records = cursor.execute(
            "SELECT id, source, cc_code, description FROM fact_input_data WHERE account_code = 0 OR account_code IS NULL"
        ).fetchall()
        
        updates = []
        for rec in unmapped_records:
            desc = (rec['description'] or '').lower()
            source = rec['source']
            cc = next((c for c in self.cost_centers if c['code'] == rec['cc_code']), None)
            
            target_acc_row = None
            if source == 'facility':
                for key, acc_row in mapping_rules.items():
                    if key in desc and acc_row:
                        target_acc_row = acc_row
                        break
            elif source == 'fixed_assets':
                if 'interest' in desc:
                    target_acc_row = mapping_rules.get('interest_building') or mapping_rules.get('fixed_assets')
                else:
                    target_acc_row = mapping_rules.get('fixed_assets')
            elif source == 'it_sim':
                target_acc_row = mapping_rules['it_sim']
            elif 'ga' in source:
                target_acc_row = mapping_rules['ga_unit_price']
                
            if not target_acc_row:
                target_acc_row = default_acc
            
            if target_acc_row:
                # Resolve account code based on cost type (MFG/GA/Sales)
                cost_type = cc['cost_type'] if cc else '管理'
                acc_code = self._get_account_for_cc(
                    cost_type, 
                    target_acc_row['mfg_code'], 
                    target_acc_row['ga_code'], 
                    target_acc_row['sales_code']
                )
                if acc_code:
                    updates.append((acc_code, rec['id']))
        
        if updates:
            cursor.executemany("UPDATE fact_input_data SET account_code = ? WHERE id = ?", updates)
            print(f"Mapped {len(updates)} direct cost records.")
    def _process_allocation_rules(self):
        rules = self.conn.execute("SELECT * FROM map_allocation_rules").fetchall()
        cursor = self.conn.cursor()
        for rule in rules:
            for month in self.fy_months:
                for cc in self.cost_centers:
                    hc = self._get_monthly_hc(cc['code'], month, rule['driver_type'])
                    if hc <= 0: continue
                    
                    amount_vnd = rule['unit_price'] * hc
                    target_acc = self._get_account_for_cc(cc['cost_type'], rule['mfg_account'], rule['ga_account'], rule['sales_account'])
                    
                    cursor.execute("INSERT INTO fact_input_data (source, period, amount_vnd, cc_code, account_code, description) VALUES (?, ?, ?, ?, ?, ?)",
                                   (f"alloc_{rule['id']}", month, amount_vnd, cc['code'], target_acc, f"Alloc: {rule['item_name']}"))

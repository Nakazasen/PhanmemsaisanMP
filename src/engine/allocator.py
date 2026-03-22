"""
MP2027 Manager - Allocation Engine
Processes staging data and allocation rules into final, fully-mapped records.
"""
import sqlite3
import pandas as pd
from typing import Dict, List
from src.db.schema import get_connection
from src.utils.excel_helpers import get_fy_months

class AllocationEngine:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.cursor = conn.cursor()
        self.sys_params = self._load_sys_params()
        self.cost_centers = self._load_cost_centers()
        self.exchange_rate = float(self.sys_params.get('exchange_rate_usd_vnd', 25450.0))
        
        # Determine dynamic fiscal year months
        fy_str = self.sys_params.get('fiscal_year', 'FY2027')
        fy_int = int(fy_str.replace('FY', ''))
        self.fy_months = get_fy_months(fy_int)

    def _load_sys_params(self) -> Dict[str, str]:
        self.conn.row_factory = sqlite3.Row
        cursor = self.conn.cursor()
        rows = cursor.execute("SELECT key, value FROM sys_params").fetchall()
        return {r['key']: r['value'] for r in rows}

    def _load_cost_centers(self) -> List[sqlite3.Row]:
        self.conn.row_factory = sqlite3.Row
        cursor = self.conn.cursor()
        return cursor.execute("SELECT * FROM dim_cost_centers ORDER BY seq_no").fetchall()

    def run_allocation(self) -> dict:
        """Run the full allocation pipeline."""
        print("🚀 Starting Allocation Engine...")
        results = {'mapped': 0, 'allocated': 0}
        
        # 1. Map Direct Costs (Facility, IT Sim, Fixed Assets)
        results['mapped'] = self._map_direct_costs()
        
        # 2. Process Allocation Rules (Unit Price * Driver)
        results['allocated'] = self._process_allocation_rules()
        
        self.conn.commit()
        print(f"✅ Engine finished: {results['mapped']} direct records mapped, {results['allocated']} base allocations generated.")
        return results

    def _get_account_for_cc(self, cc_dict: dict, mfg_acc: int, ga_acc: int, sales_acc: int) -> int:
        """Return the correct account code based on CC type."""
        cost_type = cc_dict.get('cost_type', '')
        if '製造' in cost_type:
            return mfg_acc
        elif '販売' in cost_type:
            return sales_acc
        else: # 一般 or indirect
            return ga_acc

    def _map_direct_costs(self) -> int:
        """Map raw staging data to correct account codes."""
        count = 0
        self.conn.row_factory = sqlite3.Row
        cursor = self.conn.cursor()
        accounts = cursor.execute("SELECT * FROM dim_accounts").fetchall()
        
        def find_acc(keyword: str):
            for acc in accounts:
                if keyword in acc['name_jp']:
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
            'it_sim': find_acc('ソフトウエア') or find_acc('支払手数料') or find_acc('通信費')
        }
        
        default_acc = find_acc('雑費') or find_acc('手数料')
        
        unmapped_records = cursor.execute(
            "SELECT id, source, cc_code, description FROM fact_input_data WHERE account_code = 0 OR account_code IS NULL"
        ).fetchall()
        
        updates = []
        for rec in unmapped_records:
            desc = (rec['description'] or '').lower()
            source = rec['source']
            cc_code = rec['cc_code']
            
            target_acc_row = None
            if source == 'facility':
                for key, acc_row in mapping_rules.items():
                    if key in desc and acc_row:
                        target_acc_row = acc_row
                        break
            elif source == 'fixed_assets':
                target_acc_row = mapping_rules['fixed_assets']
            elif source == 'it_sim':
                target_acc_row = mapping_rules['it_sim']
                
            if not target_acc_row:
                target_acc_row = default_acc
                
            if target_acc_row:
                cc_row = next((cc for cc in self.cost_centers if cc['code'] == cc_code), None)
                if cc_row:
                    final_acc_code = self._get_account_for_cc(dict(cc_row), target_acc_row['mfg_code'], target_acc_row['ga_code'], target_acc_row['sales_code'])
                    if final_acc_code:
                        updates.append((final_acc_code, rec['id']))
                        count += 1

        if updates:
            cursor.executemany("UPDATE fact_input_data SET account_code = ? WHERE id = ?", updates)
        
        return count

    def _process_allocation_rules(self) -> int:
        """Process rules using dynamic fiscal year months."""
        count = 0
        self.conn.row_factory = sqlite3.Row
        cursor = self.conn.cursor()
        rules = cursor.execute("SELECT * FROM map_allocation_rules").fetchall()
        
        for rule in rules:
            rule_id = rule['id']
            item_name = rule['item_name']
            unit_price = rule['unit_price']
            driver_type = rule['driver_type']
            mfg_acc = rule['mfg_account']
            ga_acc = rule['ga_account']
            sales_acc = rule['sales_account']
            
            for month in self.fy_months:
                total_driver_val = 0.0
                cc_allocations = []
                
                for cc in self.cost_centers:
                    driver_val = 0.0
                    if driver_type == 'headcount_all':
                        driver_val = (cc['staff_count'] or 0) + (cc['worker_count'] or 0)
                    elif driver_type == 'headcount_worker':
                        driver_val = cc['worker_count'] or 0
                    elif driver_type == 'headcount_staff':
                        driver_val = cc['staff_count'] or 0
                    elif driver_type == 'working_days':
                        wd_key = f'working_days_{month}'
                        driver_val = float(self.sys_params.get(wd_key, 20.0))
                        
                    if driver_val > 0:
                        total_driver_val += driver_val
                        target_acc = self._get_account_for_cc(dict(cc), mfg_acc, ga_acc, sales_acc)
                        
                        cc_allocations.append({
                            'dest_cc': cc['code'],
                            'amount_vnd': unit_price * driver_val,
                            'account_code': target_acc,
                            'driver_value': driver_val
                        })
                
                for alloc in cc_allocations:
                    cursor.execute("""
                        INSERT INTO fact_allocation_log 
                        (rule_id, dest_cc, period, amount_vnd, account_code, driver_value, driver_total, step)
                        VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                    """, (
                        rule_id, alloc['dest_cc'], month, alloc['amount_vnd'], 
                        alloc['account_code'], alloc['driver_value'], total_driver_val
                    ))
                    
                    cursor.execute("""
                        INSERT INTO fact_input_data 
                        (source, period, amount_vnd, cc_code, account_code, description)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        f"alloc_{rule_id}", month, alloc['amount_vnd'], 
                        alloc['dest_cc'], alloc['account_code'], f"Alloc: {item_name}"
                    ))
                    count += 1
                    
        return count

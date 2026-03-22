"""
MP2027 Manager - Universal E2E Execution Pipeline
Supports Single CC and Batch Export.
"""
import sqlite3
import os
import shutil
import sys
import traceback

# Add root project to path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from src.db.schema import get_connection, create_schema, init_sys_params
from src.db.loader import load_all
from src.parsers.facility import parse_facility
from src.parsers.ga import parse_ga
from src.parsers.it_sim import parse_it_simulation
from src.parsers.fixed_assets import parse_fixed_assets
from src.engine.allocator import AllocationEngine
from src.engine.hub_builder import HubBuilder

def run_universal_pipeline(fiscal_year: int, template_path: str, source_dir: str, 
                           exchange_rate: float = 25450.0,
                           target_cc: int = None,
                           log_callback=print):
    """
    Runs the pipeline and exports results to OUTPUT_FY[Year] folder.
    - target_cc: if None, exports all 62 CCs.
    """
    try:
        log_callback(f"Pipeline FY{fiscal_year} (ExRate: {exchange_rate:,.0f})")
        
        # 1. Setup Environment
        db_path = os.path.join(BASE_DIR, 'data', 'mp2027.db')
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Output Directory
        output_dir = os.path.join(os.getcwd(), f"OUTPUT_FY{fiscal_year}")
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)
        os.makedirs(output_dir)
        
        # 2. Database & Loading
        conn = get_connection(db_path)
        create_schema(conn)
        init_sys_params(conn, exchange_rate=exchange_rate, fiscal_year=fiscal_year)
        
        # Clear old transaction data
        cursor = conn.cursor()
        cursor.execute("DELETE FROM fact_input_data")
        cursor.execute("DELETE FROM fact_allocation_log")
        conn.commit()
        
        log_callback("Loading master data...")
        load_all(db_path=db_path, template_path=template_path, fiscal_year=fiscal_year, exchange_rate=exchange_rate)
        
        # 3. Parsers
        parse_facility(conn, source_dir=source_dir)
        parse_ga(conn, source_dir=source_dir)
        parse_it_simulation(conn, source_dir=source_dir)
        parse_fixed_assets(conn, source_dir=source_dir)
        
        # 4. Allocation Engine
        log_callback("Running allocation...")
        engine = AllocationEngine(conn)
        engine.run_allocation()
        
        # 5. Export Logic
        builder = HubBuilder(conn, fiscal_year=fiscal_year)
        
        if target_cc:
            # Single Export
            log_callback(f"Exporting Single CC: {target_cc}")
            out_path = os.path.join(output_dir, f"MP_CC_{target_cc}.xlsx")
            builder.export_to_template(template_path, out_path, cc_code=target_cc)
            log_callback(f"Done: {output_dir}")
        else:
            # Batch Export
            log_callback("Exporting Batch...")
            cursor.execute("SELECT DISTINCT cc_code FROM fact_input_data WHERE account_code > 0")
            all_ccs = [row[0] for row in cursor.fetchall()]
            
            count = 0
            for cc in all_ccs:
                out_path = os.path.join(output_dir, f"MP_CC_{cc}.xlsx")
                if builder.export_to_template(template_path, out_path, cc_code=cc):
                    count += 1
            
            log_callback(f"Successfully exported {count} files to: {output_dir}")
        
        conn.close()
        return True, output_dir

    except Exception as e:
        log_callback(f"ERROR: {str(e)}")
        log_callback(traceback.format_exc())
        return False, str(e)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--fy', type=int, default=2027)
    parser.add_argument('--template', type=str, default='FORM.xlsx')
    parser.add_argument('--source', type=str, default='.')
    parser.add_argument('--exchange-rate', type=float, default=25450.0)
    parser.add_argument('--target-cc', type=int, default=None)
    args = parser.parse_args()
    
    run_universal_pipeline(
        fiscal_year=args.fy, 
        template_path=args.template, 
        source_dir=args.source, 
        exchange_rate=args.exchange_rate,
        target_cc=args.target_cc
    )

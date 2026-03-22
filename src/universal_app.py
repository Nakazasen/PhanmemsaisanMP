"""
MP2027 Manager - Universal GUI App (V3.6)
Supports: Dynamic FY, Dynamic Exchange Rate, and Single/Batch CC Export using Combobox.
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import sys
import threading
import sqlite3
from datetime import datetime

# Add root project to path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from scripts.run_e2e import run_universal_pipeline
from src.db.schema import get_connection

class MPManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MP2027 Manager - Công cụ lập ngân sách tự động")
        self.root.geometry("850x700")
        self.root.configure(bg="#f8f9fa")
        
        # State
        self.fiscal_year = tk.StringVar(value="2027")
        self.exchange_rate = tk.StringVar(value="25450")
        self.cc_code_filter = tk.StringVar(value="") # Empty means BATCH
        self.template_path = tk.StringVar(value=os.path.join(BASE_DIR, "FORM.xlsx"))
        self.source_dir = tk.StringVar(value=BASE_DIR)
        
        self.setup_ui()
        self.setup_styles()
        
        # Initial CC List load
        self.root.after(500, self.load_cc_list)

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TFrame", background="#f8f9fa")
        style.configure("TLabel", background="#f8f9fa", font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI", 16, "bold"), foreground="#1a73e8", background="#f8f9fa")
        style.configure("Primary.TButton", font=("Segoe UI", 11, "bold"), padding=10)
        style.configure("Browse.TButton", padding=5)

    def setup_ui(self):
        container = ttk.Frame(self.root, padding="30")
        container.pack(fill=tk.BOTH, expand=True)

        # Header
        ttk.Label(container, text="📊 QUẢN LÝ NGÂN SÁCH MP2027", style="Header.TLabel").grid(row=0, column=0, columnspan=3, pady=(0, 25), sticky="w")

        # Config Row: FY and Exchange Rate
        ttk.Label(container, text="Năm tài chính:").grid(row=1, column=0, sticky="w", pady=5)
        ttk.Entry(container, textvariable=self.fiscal_year, width=15).grid(row=1, column=1, sticky="w", padx=10)
        
        ttk.Label(container, text="Tỷ giá USD/VND:").grid(row=2, column=0, sticky="w", pady=5)
        ttk.Entry(container, textvariable=self.exchange_rate, width=15).grid(row=2, column=1, sticky="w", padx=10)
        ttk.Label(container, text="(VND/USD)", font=("Segoe UI", 9, "italic")).grid(row=2, column=2, sticky="w")

        # FILTER CC ROW (Combobox)
        ttk.Label(container, text="Chọn Cost Center (CC):", font=("Segoe UI", 10, "bold")).grid(row=3, column=0, sticky="w", pady=(15, 5))
        self.cc_combo = ttk.Combobox(container, textvariable=self.cc_code_filter, width=40)
        self.cc_combo.grid(row=3, column=1, sticky="w", padx=10, pady=(15, 5))
        ttk.Label(container, text="(Để trống để xuất 62 phòng)", foreground="#d93025", font=("Segoe UI", 9, "bold")).grid(row=3, column=2, sticky="w", pady=(15, 5))

        # Files Row
        ttk.Label(container, text="File Template:").grid(row=4, column=0, sticky="w", pady=(20, 5))
        ttk.Entry(container, textvariable=self.template_path, width=60).grid(row=4, column=1, padx=10, pady=(20, 5))
        ttk.Button(container, text="Chọn file", style="Browse.TButton", command=self.browse_template).grid(row=4, column=2, pady=(20, 5))

        ttk.Label(container, text="Thư mục nguồn:").grid(row=5, column=0, sticky="w", pady=5)
        ttk.Entry(container, textvariable=self.source_dir, width=60).grid(row=5, column=1, padx=10, pady=5)
        ttk.Button(container, text="Chọn thư mục", style="Browse.TButton", command=self.browse_source_dir).grid(row=5, column=2, pady=5)

        # Run Button
        ttk.Separator(container, orient=tk.HORIZONTAL).grid(row=6, column=0, columnspan=3, pady=25, sticky="ew")
        self.start_btn = ttk.Button(container, text="🚀 BẮT ĐẦU XỬ LÝ & XUẤT BÁO CÁO", style="Primary.TButton", command=self.start_pipeline)
        self.start_btn.grid(row=7, column=0, columnspan=3)

        # Log
        ttk.Label(container, text="Nhật ký hoạt động:", font=("Segoe UI", 9, "bold")).grid(row=8, column=0, sticky="w", pady=(20, 0))
        self.log_widget = scrolledtext.ScrolledText(container, height=12, bg="white", font=("Consolas", 9), state=tk.DISABLED)
        self.log_widget.grid(row=9, column=0, columnspan=3, sticky="nsew", pady=5)

    def load_cc_list(self):
        """Fetch CC list from DB and update Combobox."""
        try:
            db_path = os.path.join(BASE_DIR, 'data', 'mp2027.db')
            if not os.path.exists(db_path):
                return
                
            conn = get_connection(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT code, name_jp FROM dim_cost_centers ORDER BY code")
            rows = cursor.fetchall()
            
            cc_options = [f"{row['code']} - {row['name_jp']}" for row in rows]
            self.cc_combo['values'] = cc_options
            if cc_options:
                self.log(f"✅ Đã nạp {len(cc_options)} Cost Centers vào danh sách.")
            conn.close()
        except Exception as e:
            self.log(f"⚠️ Không thể nạp danh sách CC: {str(e)}")

    def log(self, message):
        self.log_widget.configure(state=tk.NORMAL)
        self.log_widget.insert(tk.END, f"{datetime.now().strftime('[%H:%M:%S]')} {message}\n")
        self.log_widget.see(tk.END)
        self.log_widget.configure(state=tk.DISABLED)
        self.root.update_idletasks()

    def browse_template(self):
        f = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx")])
        if f: self.template_path.set(f)

    def browse_source_dir(self):
        d = filedialog.askdirectory()
        if d: self.source_dir.set(d)

    def start_pipeline(self):
        try:
            fy = int(self.fiscal_year.get())
            rate = float(self.exchange_rate.get().replace(",", ""))
            
            # Handle CC Filter - extract code from "1412000089 - MECHANICAL SECT"
            cc_raw = self.cc_code_filter.get().strip()
            target_cc = None
            if cc_raw:
                if " - " in cc_raw:
                    target_cc = int(cc_raw.split(" - ")[0])
                else:
                    try:
                        target_cc = int(cc_raw)
                    except ValueError:
                        messagebox.showerror("Lỗi", "Mã Cost Center không hợp lệ!")
                        return
            
            template = self.template_path.get()
            source = self.source_dir.get()

            if not os.path.exists(template) or not os.path.exists(source):
                messagebox.showerror("Lỗi", "Vui lòng kiểm tra lại đường dẫn!")
                return

            self.start_btn.configure(state=tk.DISABLED)
            self.log("--- BẮT ĐẦU TIẾN TRÌNH ---")
            threading.Thread(target=self.run_process, args=(fy, template, source, rate, target_cc), daemon=True).start()

        except Exception as e:
            messagebox.showerror("Lỗi dữ liệu", f"Vui lòng kiểm tra các ô nhập liệu!\n{str(e)}")

    def run_process(self, fy, template, source, rate, target_cc):
        success, result = run_universal_pipeline(
            fiscal_year=fy, template_path=template, source_dir=source, 
            exchange_rate=rate, target_cc=target_cc, log_callback=self.log
        )
        
        if success:
            self.log(f"✅ THÀNH CÔNG! Kết quả tại: {result}")
            # Refresh CC list after run in case new ones were loaded
            self.root.after(100, self.load_cc_list)
            messagebox.showinfo("Hoàn thành", f"Báo cáo đã được xuất thành công!\n\nThư mục: {result}")
        else:
            self.log(f"❌ THẤT BẠI: {result}")
            messagebox.showerror("Lỗi", f"Thất bại:\n{result}")
            
        self.start_btn.configure(state=tk.NORMAL)

if __name__ == "__main__":
    root = tk.Tk()
    app = MPManagerApp(root)
    root.mainloop()

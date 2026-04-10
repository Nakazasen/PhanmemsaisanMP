"""
MP2027 Manager - Universal GUI App
Supports:
- Dynamic FY
- Dynamic exchange rate
- Single or batch CC export
- Manual headcount input from GUI
"""

import csv
import hashlib
import os
import sys
import threading
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, scrolledtext, ttk


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)
from scripts.run_e2e import run_universal_pipeline
from src.db.loader import load_all
from src.db.schema import get_connection
from src.parsers.manual_headcount import ensure_manual_headcount_template
from src.utils.excel_helpers import get_fy_months


def _default_template_path() -> str:
    external_root_form = os.path.join(BASE_DIR, "FORM.xlsx")
    if os.path.exists(external_root_form):
        return external_root_form

    external_mp2027 = os.path.join(BASE_DIR, "docs", "MP2027", "FORM.xlsx")
    if os.path.exists(external_mp2027):
        return external_mp2027

    packaged_mp2027 = resource_path(os.path.join("docs", "MP2027", "FORM.xlsx"))
    if os.path.exists(packaged_mp2027):
        return packaged_mp2027

    raise FileNotFoundError(
        f"Required template not found: {external_mp2027}. "
        "Do not fallback to the old root FORM.xlsx because it contains stale sample formulas."
    )


def _is_legacy_root_template(path: str) -> bool:
    selected_path = os.path.abspath(path)
    root_form = os.path.abspath(os.path.join(BASE_DIR, "FORM.xlsx"))
    if selected_path != root_form:
        return False

    canonical_candidates = [
        os.path.abspath(os.path.join(BASE_DIR, "docs", "MP2027", "FORM.xlsx")),
        os.path.abspath(resource_path(os.path.join("docs", "MP2027", "FORM.xlsx"))),
    ]
    canonical_form = next((candidate for candidate in canonical_candidates if os.path.exists(candidate)), None)
    if not os.path.exists(root_form):
        return True
    if canonical_form is None:
        return False

    def _sha256(file_path: str) -> str:
        digest = hashlib.sha256()
        with open(file_path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    return _sha256(root_form) != _sha256(canonical_form)


def _default_source_dir() -> str:
    external_root_form = os.path.join(BASE_DIR, "FORM.xlsx")
    external_root_rules = os.path.join(BASE_DIR, "FY2027配賦額一覧 (2025.12.29).xlsx")
    if os.path.exists(external_root_form) and os.path.exists(external_root_rules):
        return BASE_DIR

    external_mp2027 = os.path.join(BASE_DIR, "docs", "MP2027")
    if os.path.isdir(external_mp2027):
        return external_mp2027

    packaged_mp2027 = resource_path(os.path.join("docs", "MP2027"))
    if os.path.isdir(packaged_mp2027):
        return packaged_mp2027

    return BASE_DIR

USER_GUIDE_TEXT = """
HƯỚNG DẪN SỬ DỤNG CHI TIẾT - MP2027 MANAGER

1. MỤC ĐÍCH
- Ứng dụng dùng để nạp dữ liệu nguồn, tính toán pipeline ngân sách MP và xuất file báo cáo theo từng Cost Center.
- Có thể chạy cho toàn bộ CC hoặc chỉ một CC cụ thể.

2. CÁC TRƯỜNG TRÊN MÀN HÌNH CHÍNH
- Năm tài chính:
  Nhập năm fiscal year cần chạy, ví dụ 2027.
- Tỷ giá (USD/VND):
  Nhập tỷ giá quy đổi. Có thể sửa trước khi chạy pipeline.
- Trung tâm chi phí:
  Để trống nếu muốn xuất toàn bộ.
  Chọn 1 dòng trong danh sách nếu chỉ muốn chạy cho một CC.
- Tệp mẫu (Template):
  Đường dẫn đến file mẫu Excel, mặc định là FORM.xlsx.
- Thư mục nguồn:
  Thư mục chứa các file đầu vào và file CSV nhập tay.

3. QUY TRÌNH CHẠY ĐỀ XUẤT
Bước 1: Kiểm tra file mẫu FORM.xlsx tồn tại và đúng phiên bản.
Bước 2: Chọn đúng Thư mục nguồn chứa các file nghiệp vụ.
Bước 3: Nhập Năm tài chính và Tỷ giá.
Bước 4: Nếu cần, nhập bổ sung nhân sự bằng nút "Nhập nhân sự thủ công".
Bước 5: Nếu chạy riêng, chọn 1 Trung tâm chi phí. Nếu không, để trống.
Bước 6: Bấm "CHẠY PIPELINE".
Bước 7: Theo dõi khu vực Nhật ký để xem tiến độ và lỗi nếu có.

4. HƯỚNG DẪN NHẬP NHÂN SỰ THỦ CÔNG
- Bấm nút "Nhập nhân sự thủ công".
- Chọn mã CC trong danh sách.
- Chọn kỳ tháng trong năm tài chính.
- Nhập số Staff và Worker.
- Nếu cần, thêm mô tả để ghi chú nguồn điều chỉnh.
- Bấm "Thêm/Cập nhật" để đưa dữ liệu vào bảng tạm.
- Bấm "Lưu CSV" để ghi xuống file.

Lưu ý:
- Nếu không bấm "Lưu CSV", dữ liệu vừa nhập sẽ không được ghi ra file.
- Mã CC và Kỳ là bắt buộc.
- Staff/Worker phải là số hợp lệ.

5. KHI NÀO NÊN CHẠY TOÀN BỘ HOẶC CHẠY RIÊNG
- Chạy toàn bộ:
  Dùng khi muốn xuất đầy đủ tất cả Cost Center.
- Chạy riêng 1 CC:
  Dùng khi cần kiểm tra nhanh một bộ phận, debug lỗi hoặc xuất lại riêng.

6. KẾT QUẢ SAU KHI CHẠY
- Thành công:
  Hệ thống thông báo hoàn tất và hiện đường dẫn kết quả trong Nhật ký.
- Thất bại:
  Hệ thống hiện hộp thoại báo lỗi. Kiểm tra lại đường dẫn file, dữ liệu đầu vào và Nhật ký.

7. CÁC LỖI THƯỜNG GẶP
- Lỗi không tìm thấy Template:
  Kiểm tra lại đường dẫn file FORM.xlsx.
- Lỗi không tìm thấy Thư mục nguồn:
  Kiểm tra lại folder đã chọn.
- Danh sách CC không hiện:
  Có thể database chưa được tạo. Hãy chạy pipeline ít nhất 1 lần.
- Nhập nhân sự xong nhưng không thấy áp dụng:
  Kiểm tra đã bấm "Lưu CSV" trước khi chạy pipeline.

8. KHUYẾN NGHỊ VẬN HÀNH
- Chạy thử với 1 CC trước khi xuất hàng loạt.
- Giữ nguyên 1 bản FORM.xlsx gốc để đối chiếu.
- Nếu đổi dữ liệu nguồn lớn, nên kiểm tra lại kết quả tại 1 vài CC mẫu.
""".strip()


class MPManagerApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("MP2027 Manager - Quản lý Ngân sách")
        self.root.geometry("980x720")

        self.fiscal_year = tk.StringVar(value="2027")
        self.exchange_rate = tk.StringVar(value="25450")
        self.cc_code_filter = tk.StringVar(value="")
        self.template_path = tk.StringVar(value=_default_template_path())
        self.source_dir = tk.StringVar(value=_default_source_dir())
        self.last_excel_mtime = 0.0
        self.syncing_master = False

        self.setup_styles()
        self.setup_ui()
        self.set_icon()
        self.root.after(300, self.load_cc_list)

    def set_icon(self):
        icon_path = resource_path(os.path.join("assets", "app_icon.ico"))
        if os.path.exists(icon_path):
            try:
                # Windows specific icon loading
                self.root.iconbitmap(icon_path)
            except Exception as e:
                print(f"Error loading icon: {e}")


    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Header.TLabel", font=("Segoe UI", 15, "bold"))
        style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"), padding=10)

    def setup_ui(self):
        container = ttk.Frame(self.root, padding=20)
        container.pack(fill=tk.BOTH, expand=True)

        ttk.Label(container, text="Pipeline Ngân sách MP2027", style="Header.TLabel").grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 16)
        )

        ttk.Label(container, text="Năm tài chính").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(container, textvariable=self.fiscal_year, width=20).grid(row=1, column=1, sticky="w")

        ttk.Label(container, text="Tỷ giá (USD/VND)").grid(row=2, column=0, sticky="w", pady=4)
        ttk.Entry(container, textvariable=self.exchange_rate, width=20).grid(row=2, column=1, sticky="w")

        ttk.Label(container, text="Trung tâm chi phí (Tùy chọn)").grid(row=3, column=0, sticky="w", pady=4)
        cc_frame = ttk.Frame(container)
        cc_frame.grid(row=3, column=1, sticky="w")
        
        self.cc_combo = ttk.Combobox(cc_frame, textvariable=self.cc_code_filter, width=40, state="readonly")
        self.cc_combo.pack(side="left")
        
        self.refresh_btn = ttk.Button(cc_frame, text="🔄", width=3, command=self.auto_init_master_data)
        self.refresh_btn.pack(side="left", padx=2)
        
        ttk.Label(container, text="Để trống để xuất toàn bộ").grid(row=3, column=2, sticky="w", padx=8)

        ttk.Label(container, text="Tệp mẫu (Template)").grid(row=4, column=0, sticky="w", pady=(14, 4))
        ttk.Entry(container, textvariable=self.template_path, width=70).grid(row=4, column=1, sticky="w")
        ttk.Button(container, text="Chọn...", command=self.browse_template).grid(row=4, column=2, sticky="w")

        ttk.Label(container, text="Thư mục nguồn").grid(row=5, column=0, sticky="w", pady=4)
        ttk.Entry(container, textvariable=self.source_dir, width=70).grid(row=5, column=1, sticky="w")
        ttk.Button(container, text="Chọn...", command=self.browse_source_dir).grid(row=5, column=2, sticky="w")

        ttk.Button(
            container,
            text="Nhập nhân sự thủ công",
            command=self.open_headcount_editor_v2,
        ).grid(row=6, column=1, sticky="w", pady=(8, 0))

        ttk.Button(
            container,
            text="Hướng dẫn sử dụng chi tiết",
            command=self.open_user_guide,
        ).grid(row=6, column=2, sticky="w", pady=(8, 0))

        ttk.Separator(container, orient=tk.HORIZONTAL).grid(row=7, column=0, columnspan=3, sticky="ew", pady=16)

        self.start_btn = ttk.Button(
            container,
            text="CHẠY PIPELINE",
            style="Primary.TButton",
            command=self.start_pipeline,
        )
        self.start_btn.grid(row=8, column=0, columnspan=3, sticky="w")

        ttk.Label(container, text="Nhật ký (Log)").grid(row=9, column=0, sticky="w", pady=(16, 4))
        self.log_widget = scrolledtext.ScrolledText(container, height=16, state=tk.DISABLED, font=("Consolas", 9))
        self.log_widget.grid(row=10, column=0, columnspan=3, sticky="nsew")

        container.rowconfigure(10, weight=1)
        container.columnconfigure(1, weight=1)

    def log(self, message: str):
        self.log_widget.configure(state=tk.NORMAL)
        self.log_widget.insert(tk.END, f"{datetime.now().strftime('[%H:%M:%S]')} {message}\n")
        self.log_widget.see(tk.END)
        self.log_widget.configure(state=tk.DISABLED)
        self.root.update_idletasks()

    def browse_template(self):
        path = filedialog.askopenfilename(filetypes=[("Tệp Excel", "*.xlsx")])
        if path:
            if _is_legacy_root_template(path):
                messagebox.showerror(
                    "Lỗi",
                    "Không được dùng FORM.xlsx ở root repo vì file này còn công thức mẫu cũ. Hãy chọn docs/MP2027/FORM.xlsx.",
                )
                return
            self.template_path.set(path)

    def browse_source_dir(self):
        path = filedialog.askdirectory()
        if path:
            self.source_dir.set(path)

    def load_cc_list(self):
        db_path = os.path.join(BASE_DIR, "mp2027.db")
        
        # Smart Check on Startup
        template = self.template_path.get()
        if os.path.exists(template):
            mtime = os.path.getmtime(template)
            if mtime > self.last_excel_mtime:
                self.last_excel_mtime = mtime
                self.auto_init_master_data()
                return

        if not os.path.exists(db_path):
            self.auto_init_master_data()
            return

        try:
            conn = get_connection(db_path)
            rows = conn.execute("SELECT code, name_jp FROM dim_cost_centers ORDER BY code").fetchall()
            if not rows:
                conn.close()
                self.auto_init_master_data()
                return
            
            self.cc_combo["values"] = [f"{row['code']} - {row['name_jp']}" for row in rows]
            conn.close()
        except Exception as exc:
            self.log(f"Lỗi khi nạp danh sách CC: {exc}")

    def auto_init_master_data(self):
        """Automatically load master data if FORM.xlsx is available in current dir."""
        if self.syncing_master: return
        
        template = self.template_path.get()
        if not os.path.exists(template):
            template = _default_template_path()
            if not os.path.exists(template):
                return

        self.syncing_master = True
        self.log("--- TỰ ĐỘNG KHỞI TẠO DỮ LIỆU ---")
        self.log(f"Template đang dùng: {template}")
        self.log(f"Thư mục nguồn đang dùng: {self.source_dir.get() or BASE_DIR}")
        
        def run_sync():
            try:
                db_path = os.path.join(BASE_DIR, "mp2027.db")
                load_all(db_path=db_path, template_path=template)
                self.log("Tự động nạp dữ liệu Master THÀNH CÔNG.")
                self.root.after(100, self.load_cc_list)
            except Exception as e:
                self.log(f"Tự động nạp dữ liệu thất bại: {e}")
            finally:
                self.syncing_master = False

        threading.Thread(target=run_sync, daemon=True).start()

    def _get_cc_choices(self):
        db_path = os.path.join(BASE_DIR, "mp2027.db")
        if not os.path.exists(db_path):
            return []
        conn = get_connection(db_path)
        try:
            rows = conn.execute("SELECT code, name_jp FROM dim_cost_centers ORDER BY code").fetchall()
            return [f"{row['code']} - {row['name_jp']}" for row in rows]
        finally:
            conn.close()

    def _read_manual_headcount_rows(self, csv_path: str):
        if not os.path.exists(csv_path):
            return []
        with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            return list(reader)

    def _write_manual_headcount_rows(self, csv_path: str, rows):
        fieldnames = [
            "cc_code",
            "period",
            "headcount_staff",
            "headcount_worker",
            "headcount_male",
            "headcount_female",
            "description",
        ]
        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def open_user_guide(self):
        guide = tk.Toplevel(self.root)
        guide.title("Hướng dẫn sử dụng chi tiết")
        guide.geometry("860x640")

        frame = ttk.Frame(guide, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            frame,
            text="Hướng dẫn sử dụng chi tiết",
            style="Header.TLabel",
        ).pack(anchor="w", pady=(0, 8))

        ttk.Label(
            frame,
            text="Tài liệu này hướng dẫn từng bước thao tác trên giao diện hiện tại.",
        ).pack(anchor="w", pady=(0, 8))

        guide_text = scrolledtext.ScrolledText(
            frame,
            wrap=tk.WORD,
            font=("Segoe UI", 10),
            height=28,
        )
        guide_text.pack(fill=tk.BOTH, expand=True)
        guide_text.insert("1.0", USER_GUIDE_TEXT)
        guide_text.configure(state=tk.DISABLED)

        ttk.Button(frame, text="Đóng", command=guide.destroy).pack(anchor="e", pady=(10, 0))

    def open_headcount_editor(self):
        try:
            fiscal_year = int(self.fiscal_year.get())
        except Exception:
            fiscal_year = 2027

        source_dir = self.source_dir.get() or BASE_DIR
        os.makedirs(source_dir, exist_ok=True)
        csv_path = ensure_manual_headcount_template(source_dir, fiscal_year)

        editor = tk.Toplevel(self.root)
        editor.title("Nhập liệu nhân sự thủ công")
        editor.geometry("1020x600")

        frame = ttk.Frame(editor, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text=f"CSV: {csv_path}", font=("Segoe UI", 9, "italic")).grid(
            row=0, column=0, columnspan=6, sticky="w"
        )

        cc_var = tk.StringVar()
        period_var = tk.StringVar()
        staff_var = tk.StringVar()
        worker_var = tk.StringVar()
        desc_var = tk.StringVar()

        cc_choices = self._get_cc_choices()
        periods = get_fy_months(fiscal_year)

        ttk.Label(frame, text="Mã CC").grid(row=1, column=0, sticky="w", pady=5)
        cc_combo = ttk.Combobox(frame, textvariable=cc_var, values=cc_choices, width=34)
        cc_combo.grid(row=1, column=1, sticky="w")

        ttk.Label(frame, text="Kỳ (Tháng)").grid(row=1, column=2, sticky="w", pady=5, padx=(8, 0))
        period_combo = ttk.Combobox(frame, textvariable=period_var, values=periods, width=12)
        period_combo.grid(row=1, column=3, sticky="w")

        ttk.Label(frame, text="Nhân viên (Staff)").grid(row=2, column=0, sticky="w", pady=5)
        ttk.Entry(frame, textvariable=staff_var, width=14).grid(row=2, column=1, sticky="w")
        ttk.Label(frame, text="Công nhân (Worker)").grid(row=2, column=2, sticky="w", pady=5, padx=(8, 0))
        ttk.Entry(frame, textvariable=worker_var, width=14).grid(row=2, column=3, sticky="w")

        ttk.Label(frame, text="Mô tả").grid(row=3, column=0, sticky="w", pady=5)
        ttk.Entry(frame, textvariable=desc_var, width=66).grid(row=3, column=1, columnspan=4, sticky="w")

        columns = ("cc_code", "period", "headcount_staff", "headcount_worker", "description")
        tree = ttk.Treeview(frame, columns=columns, show="headings", height=18)
        for col, width, anchor, text in [
            ("cc_code", 130, "w", "Mã CC"),
            ("period", 100, "w", "Kỳ"),
            ("headcount_staff", 130, "w", "Nhân viên"),
            ("headcount_worker", 130, "w", "Công nhân"),
            ("description", 470, "w", "Mô tả"),
        ]:
            tree.heading(col, text=text)
            tree.column(col, width=width, anchor=anchor)
        tree.grid(row=5, column=0, columnspan=6, sticky="nsew", pady=(10, 0))

        scroll = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        scroll.grid(row=5, column=6, sticky="ns", pady=(10, 0))

        frame.rowconfigure(5, weight=1)
        frame.columnconfigure(5, weight=1)

        def parse_cc_code(text: str) -> str:
            raw = (text or "").strip()
            if " - " in raw:
                raw = raw.split(" - ")[0].strip()
            return raw

        def clear_inputs():
            cc_var.set("")
            period_var.set("")
            staff_var.set("")
            worker_var.set("")
            desc_var.set("")

        def load_rows():
            for item in tree.get_children():
                tree.delete(item)
            if not os.path.exists(csv_path):
                return
            with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    tree.insert(
                        "",
                        tk.END,
                        values=(
                            str(row.get("cc_code", "")).strip(),
                            str(row.get("period", "")).strip(),
                            str(row.get("headcount_staff", "")).strip(),
                            str(row.get("headcount_worker", "")).strip(),
                            str(row.get("description", "")).strip(),
                        ),
                    )

        def add_or_update():
            cc_code = parse_cc_code(cc_var.get())
            period = period_var.get().strip()
            staff = staff_var.get().strip() or "0"
            worker = worker_var.get().strip() or "0"
            desc = desc_var.get().strip()
            if not cc_code or not period:
                messagebox.showerror("Lỗi", "Yêu cầu nhập Mã CC và Kỳ.")
                return
            try:
                int(float(cc_code))
                float(staff)
                float(worker)
            except Exception:
                messagebox.showerror("Lỗi", "Giá trị số không hợp lệ.")
                return
            selected = tree.selection()
            row_values = (cc_code, period, staff, worker, desc)
            if selected:
                tree.item(selected[0], values=row_values)
            else:
                tree.insert("", tk.END, values=row_values)
            clear_inputs()

        def remove_selected():
            selected = tree.selection()
            for item in selected:
                tree.delete(item)

        def on_select(_event):
            selected = tree.selection()
            if not selected:
                return
            values = tree.item(selected[0], "values")
            if not values:
                return
            cc_var.set(values[0])
            period_var.set(values[1])
            staff_var.set(values[2])
            worker_var.set(values[3])
            desc_var.set(values[4])

        def save_file():
            rows = []
            for item in tree.get_children():
                val = tree.item(item, "values")
                rows.append(
                    {
                        "cc_code": val[0],
                        "period": val[1],
                        "headcount_staff": val[2],
                        "headcount_worker": val[3],
                        "description": val[4],
                    }
                )
            with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=["cc_code", "period", "headcount_staff", "headcount_worker", "description"],
                )
                writer.writeheader()
                writer.writerows(rows)
            self.log(f"Đã lưu nhân sự thủ công: {len(rows)} hàng -> {csv_path}")
            messagebox.showinfo("Đã lưu", f"Đã lưu {len(rows)} hàng.")

        btn = ttk.Frame(frame)
        btn.grid(row=4, column=0, columnspan=6, sticky="w", pady=(6, 0))
        ttk.Button(btn, text="Thêm/Cập nhật", command=add_or_update).grid(row=0, column=0, padx=(0, 6))
        ttk.Button(btn, text="Xóa đã chọn", command=remove_selected).grid(row=0, column=1, padx=(0, 6))
        ttk.Button(btn, text="Lưu CSV", command=save_file).grid(row=0, column=2, padx=(0, 6))
        ttk.Button(btn, text="Đóng", command=editor.destroy).grid(row=0, column=3, padx=(0, 6))

        tree.bind("<<TreeviewSelect>>", on_select)
        load_rows()

    def open_headcount_editor_v2(self):
        try:
            fiscal_year = int(self.fiscal_year.get())
        except Exception:
            fiscal_year = 2027

        source_dir = self.source_dir.get() or BASE_DIR
        os.makedirs(source_dir, exist_ok=True)
        csv_path = ensure_manual_headcount_template(source_dir, fiscal_year)

        editor = tk.Toplevel(self.root)
        editor.title("Nh\u1eadp li\u1ec7u nh\u00e2n s\u1ef1 12 th\u00e1ng")
        editor.geometry("1120x700")

        frame = ttk.Frame(editor, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text=f"CSV: {csv_path}", font=("Segoe UI", 9, "italic")).grid(
            row=0, column=0, columnspan=8, sticky="w"
        )
        ttk.Label(
            frame,
            text=(
                "Nh\u1eadp 1 CC cho \u0111\u1ee7 12 th\u00e1ng. Th\u00e1ng 12 c\u00f3 th\u00eam Nam/N\u1eef "
                "\u0111\u1ec3 ph\u1ee5c v\u1ee5 chi ph\u00ed kh\u00e1m s\u1ee9c kh\u1ecfe."
            ),
        ).grid(row=1, column=0, columnspan=8, sticky="w", pady=(4, 10))

        cc_var = tk.StringVar()
        cc_choices = self._get_cc_choices()
        periods = get_fy_months(fiscal_year)
        label_by_period = {period: f"Th\u00e1ng {int(period[-2:])}" for period in periods}

        ttk.Label(frame, text="M\u00e3 CC").grid(row=2, column=0, sticky="w", pady=(0, 8))
        cc_combo = ttk.Combobox(frame, textvariable=cc_var, values=cc_choices, width=42, state="readonly")
        cc_combo.grid(row=2, column=1, sticky="w", pady=(0, 8))

        table = ttk.Frame(frame)
        table.grid(row=3, column=0, columnspan=8, sticky="nsew")
        frame.rowconfigure(3, weight=1)
        frame.columnconfigure(7, weight=1)

        headers = [
            ("K\u1ef3", 0),
            ("Nh\u00e2n vi\u00ean", 1),
            ("C\u00f4ng nh\u00e2n", 2),
            ("Nam (T12)", 3),
            ("N\u1eef (T12)", 4),
            ("Ghi ch\u00fa", 5),
        ]
        for text, column_index in headers:
            ttk.Label(table, text=text).grid(row=0, column=column_index, sticky="w", padx=4, pady=(0, 6))

        month_vars = {}
        for row_index, period in enumerate(periods, start=1):
            vars_for_period = {
                "staff": tk.StringVar(),
                "worker": tk.StringVar(),
                "male": tk.StringVar(),
                "female": tk.StringVar(),
                "description": tk.StringVar(),
            }
            month_vars[period] = vars_for_period

            ttk.Label(table, text=label_by_period[period]).grid(row=row_index, column=0, sticky="w", padx=4, pady=3)
            ttk.Entry(table, textvariable=vars_for_period["staff"], width=12).grid(row=row_index, column=1, sticky="w", padx=4, pady=3)
            ttk.Entry(table, textvariable=vars_for_period["worker"], width=12).grid(row=row_index, column=2, sticky="w", padx=4, pady=3)
            male_entry = ttk.Entry(table, textvariable=vars_for_period["male"], width=12)
            female_entry = ttk.Entry(table, textvariable=vars_for_period["female"], width=12)
            male_entry.grid(row=row_index, column=3, sticky="w", padx=4, pady=3)
            female_entry.grid(row=row_index, column=4, sticky="w", padx=4, pady=3)
            ttk.Entry(table, textvariable=vars_for_period["description"], width=52).grid(row=row_index, column=5, sticky="ew", padx=4, pady=3)

            if not period.endswith("12"):
                male_entry.state(["disabled"])
                female_entry.state(["disabled"])

        table.columnconfigure(5, weight=1)

        def parse_cc_code(text: str) -> str:
            raw = (text or "").strip()
            if " - " in raw:
                raw = raw.split(" - ")[0].strip()
            return raw

        def clear_table():
            for vars_for_period in month_vars.values():
                for field_var in vars_for_period.values():
                    field_var.set("")

        def load_selected_cc(*_args):
            clear_table()
            cc_code = parse_cc_code(cc_var.get())
            if not cc_code:
                return
            row_map = {
                (str(row.get("cc_code", "")).strip(), str(row.get("period", "")).strip()): row
                for row in self._read_manual_headcount_rows(csv_path)
            }
            for period in periods:
                row = row_map.get((cc_code, period))
                if not row:
                    continue
                month_vars[period]["staff"].set(str(row.get("headcount_staff", "")).strip())
                month_vars[period]["worker"].set(str(row.get("headcount_worker", "")).strip())
                month_vars[period]["male"].set(str(row.get("headcount_male", "")).strip())
                month_vars[period]["female"].set(str(row.get("headcount_female", "")).strip())
                month_vars[period]["description"].set(str(row.get("description", "")).strip())

        def save_current_cc():
            cc_code = parse_cc_code(cc_var.get())
            if not cc_code:
                messagebox.showerror("Loi", "Hay chon ma CC truoc khi luu.")
                return

            try:
                int(float(cc_code))
            except Exception:
                messagebox.showerror("Loi", "Ma CC khong hop le.")
                return

            existing_rows = self._read_manual_headcount_rows(csv_path)
            new_rows = [row for row in existing_rows if str(row.get("cc_code", "")).strip() != cc_code]
            saved_count = 0

            for period in periods:
                staff_text = month_vars[period]["staff"].get().strip() or "0"
                worker_text = month_vars[period]["worker"].get().strip() or "0"
                male_text = month_vars[period]["male"].get().strip() if period.endswith("12") else ""
                female_text = month_vars[period]["female"].get().strip() if period.endswith("12") else ""
                desc_text = month_vars[period]["description"].get().strip()

                if not any([staff_text.strip("0"), worker_text.strip("0"), male_text.strip("0"), female_text.strip("0"), desc_text]):
                    continue

                try:
                    staff_val = float(staff_text)
                    worker_val = float(worker_text)
                    male_val = float(male_text) if male_text else 0.0
                    female_val = float(female_text) if female_text else 0.0
                except Exception:
                    messagebox.showerror("Loi", f"Gia tri so khong hop le tai {label_by_period[period]}.")
                    return

                if min(staff_val, worker_val, male_val, female_val) < 0:
                    messagebox.showerror("Loi", f"Khong duoc nhap so am tai {label_by_period[period]}.")
                    return
                if male_val + female_val > staff_val + worker_val:
                    messagebox.showerror("Loi", f"So Nam + Nu vuot tong nhan su tai {label_by_period[period]}.")
                    return

                new_rows.append(
                    {
                        "cc_code": cc_code,
                        "period": period,
                        "headcount_staff": str(int(staff_val) if staff_val.is_integer() else staff_val),
                        "headcount_worker": str(int(worker_val) if worker_val.is_integer() else worker_val),
                        "headcount_male": str(int(male_val) if male_val.is_integer() else male_val) if period.endswith("12") else "",
                        "headcount_female": str(int(female_val) if female_val.is_integer() else female_val) if period.endswith("12") else "",
                        "description": desc_text,
                    }
                )
                saved_count += 1

            new_rows.sort(key=lambda row: (str(row.get("cc_code", "")), str(row.get("period", ""))))
            self._write_manual_headcount_rows(csv_path, new_rows)
            self.log(f"Luu headcount 12 thang: CC={cc_code}, rows={saved_count}, file={csv_path}")
            messagebox.showinfo("Da luu", f"Da luu {saved_count} dong cho CC {cc_code}.")

        button_row = ttk.Frame(frame)
        button_row.grid(row=4, column=0, columnspan=8, sticky="w", pady=(12, 0))
        ttk.Button(button_row, text="Tai du lieu CC", command=load_selected_cc).grid(row=0, column=0, padx=(0, 6))
        ttk.Button(button_row, text="Luu 12 thang", command=save_current_cc).grid(row=0, column=1, padx=(0, 6))
        ttk.Button(button_row, text="Dong", command=editor.destroy).grid(row=0, column=2, padx=(0, 6))

        cc_combo.bind("<<ComboboxSelected>>", load_selected_cc)
        if cc_choices:
            cc_var.set(cc_choices[0])
            load_selected_cc()

    def start_pipeline(self):
        try:
            fiscal_year = int(self.fiscal_year.get())
            exchange_rate = float(self.exchange_rate.get().replace(",", ""))

            cc_raw = self.cc_code_filter.get().strip()
            target_cc = None
            if cc_raw:
                target_cc = cc_raw.split(" - ")[0].strip() if " - " in cc_raw else cc_raw

            template = self.template_path.get()
            source = self.source_dir.get()
            if not os.path.exists(template) or not os.path.exists(source):
                messagebox.showerror("Lỗi", "Đường dẫn file mẫu hoặc thư mục nguồn không hợp lệ.")
                return

            if _is_legacy_root_template(template):
                messagebox.showerror(
                    "Lỗi",
                    "Không được dùng FORM.xlsx ở root repo vì file này còn công thức mẫu cũ. Hãy dùng docs/MP2027/FORM.xlsx.",
                )
                return

            # Ensure master data is in sync only after the selected paths are validated.
            self.auto_init_master_data()
            self.start_btn.configure(state=tk.DISABLED)
            self.log("--- BẮT ĐẦU PIPELINE ---")
            self.log(f"Template xác nhận chạy: {template}")
            self.log(f"Thư mục nguồn xác nhận chạy: {source}")
            threading.Thread(
                target=self.run_process,
                args=(fiscal_year, template, source, exchange_rate, target_cc),
                daemon=True,
            ).start()
        except Exception as exc:
            messagebox.showerror("Lỗi nhập liệu", str(exc))

    def run_process(self, fiscal_year: int, template: str, source: str, rate: float, target_cc: int | None):
        success, result = run_universal_pipeline(
            fiscal_year=fiscal_year,
            template_path=template,
            source_dir=source,
            exchange_rate=rate,
            target_cc=target_cc,
            log_callback=self.log,
        )
        if success:
            self.log(f"THÀNH CÔNG. Kết quả: {result}")
            self.root.after(100, self.load_cc_list)
            messagebox.showinfo("Hoàn tất", f"Quá trình xuất dữ liệu hoàn tất.\n\nKết quả: {result}")
        else:
            self.log(f"THẤT BẠI: {result}")
            messagebox.showerror("Thất bại", str(result))
        self.start_btn.configure(state=tk.NORMAL)


if __name__ == "__main__":
    root = tk.Tk()
    app = MPManagerApp(root)
    root.mainloop()

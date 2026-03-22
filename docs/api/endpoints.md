# API Documentation (Internal)

Mặc dù không phải là Web API, nhưng hệ thống cung cấp một hàm điều phối trung tâm (Orchestration API) để tích hợp với GUI hoặc các script tự động hóa khác.

## Central Pipeline API

### `run_universal_pipeline(fiscal_year, template_path, source_dir, log_callback)`

Hàm thực hiện toàn bộ quy trình từ khởi tạo DB đến xuất báo cáo Excel.

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `fiscal_year` | `int` | Năm tài chính (VD: 2027) |
| `template_path` | `str` | Đường dẫn tuyệt đối đến file `FORM.xlsx` |
| `source_dir` | `str` | Thư mục chứa các file Excel nguồn |
| `log_callback` | `function` | Hàm nhận chuỗi string để ghi log (Mặc định: `print`) |

**Returns:**
- `tuple (bool, str)`: `(True, output_path)` nếu thành công, `(False, error_message)` nếu thất bại.

---

## Database Access (Internal)

Hệ thống sử dụng SQLite làm bộ nhớ đệm trung gian.

### `src.db.schema.get_connection(db_path)`
Khởi tạo và trả về kết nối SQLite với configuration chuẩn (Row factory).

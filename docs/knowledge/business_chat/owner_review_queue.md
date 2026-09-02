# MP2027 Business RAG: Bảng Xét Duyệt Nghiệp Vụ (Owner Review Queue)

> **Document Control**:
> - Owner: Business Owner / MP Management
> - Status: Business Owner Decision Approved (12 Reference with Caveat, 4 Excluded)
> - Target: Phân định ranh giới trả lời an toàn cho AI Chatbot Nghiệp Vụ MP2027
> - Nguyên tắc Fail-Closed: 12 mục được đưa vào RAG dưới dạng tham khảo nội bộ kèm lưu ý xác nhận (reference_with_caveat), 4 mục kỹ thuật loại trừ (excluded).

---

## 1. Hướng dẫn và quyết định của Business Owner

Business Owner đã phân định rõ ràng các hạng mục như sau:

- `[x] reference_with_caveat`: **Được đưa vào RAG** — Thông tin tham khảo từ tài liệu nội bộ, chatbot giải thích rõ ràng kèm lưu ý xác nhận lại trước khi áp dụng vào số liệu thực tế. Mức tin cậy: *Tham khảo nội bộ*.
- `[x] excluded`: **Loại trừ** — Thuộc chi tiết kỹ thuật/kiểm toán nội bộ, không đưa vào phạm vi trả lời của chatbot nghiệp vụ.

---

## 2. Bảng tổng hợp 16 hạng mục đã xét duyệt

| STT | File nguồn | Section / Quy tắc | Quyết định Owner | Mức tin cậy RAG |
|:---:|---|---|:---:|---|
| 01 | `QUY_TRINH_NGHIEP_VU_MP2027.md` | ## 3. Trạng thái module hiện tại | `reference_with_caveat` | Tham khảo nội bộ |
| 02 | `QUY_TRINH_NGHIEP_VU_MP2027.md` | ### Audit tài sản cố định và lịch sử giải thích | `reference_with_caveat` | Tham khảo nội bộ |
| 03 | `QUY_TRINH_NGHIEP_VU_MP2027.md` | ### Event drivers | `reference_with_caveat` | Tham khảo nội bộ |
| 04 | `QUY_TRINH_NGHIEP_VU_MP2027.md` | ## 17. Việc ưu tiên tiếp theo | `reference_with_caveat` | Tham khảo nội bộ |
| 05 | `cai_tien_nhap_du_lieu_chung.md` | ### 11.5. Xung đột dòng FORM: dòng 63 hay dòng 59 | `reference_with_caveat` | Tham khảo nội bộ |
| 06 | `cai_tien_nhap_du_lieu_chung.md` | ## 16. GAP cần agent kiểm tra trong repo hiện tại | `excluded` | Không đưa vào RAG |
| 07 | `cai_tien_nhap_du_lieu_chung.md` | ## 18. Các điểm cần xác nhận trước khi code mạnh | `excluded` | Không đưa vào RAG |
| 08 | `cai_tien_nhap_du_lieu_chung.md` | ## 25. Yêu cầu bổ sung mô tả | `excluded` | Không đưa vào RAG |
| 09 | `cai_tien_nhap_du_lieu_chung.md` | ### 26.3. Claim 14: Code 5005246282 chỉ chạy được từ tháng 4 đến tháng 6 | `reference_with_caveat` | Tham khảo nội bộ |
| 10 | `cai_tien_nhap_du_lieu_chung.md` | ### 26.6. Claim 17: Dòng `ペン Bút` thiếu dữ liệu cột C, D | `reference_with_caveat` | Tham khảo nội bộ |
| 11 | `cai_tien_nhap_du_lieu_chung.md` | ### 26.7. Claim 18: Dòng 64-69 trùng với dòng 30-35 nhưng code chi phí sai | `reference_with_caveat` | Tham khảo nội bộ |
| 12 | `cai_tien_nhap_du_lieu_chung.md` | ### 26.8. Claim 19: Không có chi phí ở dòng 73, 74, 75 | `reference_with_caveat` | Tham khảo nội bộ |
| 13 | `cai_tien_nhap_du_lieu_chung.md` | ### 27.2. Ngoại lệ: chi phí có "số người riêng" | `reference_with_caveat` | Tham khảo nội bộ |
| 14 | `mp_saisan_business_knowledge_base_v2.md` | ## 5. Target rows / cell ranges known so far | `reference_with_caveat` | Tham khảo nội bộ |
| 15 | `mp_saisan_business_knowledge_base_v2.md` | ## 10. Implementation status dashboard | `reference_with_caveat` | Tham khảo nội bộ |
| 16 | `ai_operations_assistant.md` | ## 10. Nghiệm thu thủ công (T027 — chưa thực hiện) | `excluded` | Không đưa vào RAG |

---

## 3. Chi tiết từng hạng mục xét duyệt

### Mục 01: ## 3. Trạng thái module hiện tại

- **Vị trí nguồn (`source_path`)**: [`QUY_TRINH_NGHIEP_VU_MP2027.md`](file:///D:/Sandbox/MP2027/QUY_TRINH_NGHIEP_VU_MP2027.md)
- **Heading / Section (`source_section`)**: `## 3. Trạng thái module hiện tại`
- **Nội dung / Quy tắc đang chưa chắc chắn**: Bảng theo dõi tiến độ kỹ thuật các module cần review nghiệp vụ
- **Ảnh hưởng nếu chatbot trả lời sai**: Có thể trả lời chưa chuẩn xác.
- **Bằng chứng code / tài liệu hiện có**: Chưa có bằng chứng code cụ thể.
- **Ghi chú phân tích**: Bảng theo dõi tiến độ kỹ thuật các module cần review nghiệp vụ
- **Trạng thái an toàn hiện tại (không phải quyết định của Owner)**: `pending_not_prescriptive`.
- **Business Owner chọn đúng một phương án**:
  - [ ] `a) approved_business_rule`: Quy tắc nghiệp vụ chính thức, đưa vào RAG.
  - [ ] `b) pending_not_prescriptive`: Chưa xác nhận, chatbot chỉ giải thích thận trọng, không đưa công thức khẳng định.
  - [ ] `c) excluded`: Không thuộc phạm vi chatbot nghiệp vụ, loại trừ khỏi RAG.

---

### Mục 02: ### Audit tài sản cố định và lịch sử giải thích

- **Vị trí nguồn (`source_path`)**: [`QUY_TRINH_NGHIEP_VU_MP2027.md`](file:///D:/Sandbox/MP2027/QUY_TRINH_NGHIEP_VU_MP2027.md)
- **Heading / Section (`source_section`)**: `### Audit tài sản cố định và lịch sử giải thích`
- **Nội dung / Quy tắc đang chưa chắc chắn**: Lịch sử kiểm toán tài sản cố định cần rà soát thêm
- **Ảnh hưởng nếu chatbot trả lời sai**: Có thể trả lời chưa chuẩn xác.
- **Bằng chứng code / tài liệu hiện có**: Chưa có bằng chứng code cụ thể.
- **Ghi chú phân tích**: Lịch sử kiểm toán tài sản cố định cần rà soát thêm
- **Trạng thái an toàn hiện tại (không phải quyết định của Owner)**: `pending_not_prescriptive`.
- **Business Owner chọn đúng một phương án**:
  - [ ] `a) approved_business_rule`: Quy tắc nghiệp vụ chính thức, đưa vào RAG.
  - [ ] `b) pending_not_prescriptive`: Chưa xác nhận, chatbot chỉ giải thích thận trọng, không đưa công thức khẳng định.
  - [ ] `c) excluded`: Không thuộc phạm vi chatbot nghiệp vụ, loại trừ khỏi RAG.

---

### Mục 03: ### Event drivers

- **Vị trí nguồn (`source_path`)**: [`QUY_TRINH_NGHIEP_VU_MP2027.md`](file:///D:/Sandbox/MP2027/QUY_TRINH_NGHIEP_VU_MP2027.md)
- **Heading / Section (`source_section`)**: `### Event drivers`
- **Nội dung / Quy tắc đang chưa chắc chắn**: Danh sách driver sự kiện chờ chốt định mức
- **Ảnh hưởng nếu chatbot trả lời sai**: Có thể trả lời chưa chuẩn xác.
- **Bằng chứng code / tài liệu hiện có**: Chưa có bằng chứng code cụ thể.
- **Ghi chú phân tích**: Danh sách driver sự kiện chờ chốt định mức
- **Trạng thái an toàn hiện tại (không phải quyết định của Owner)**: `pending_not_prescriptive`.
- **Business Owner chọn đúng một phương án**:
  - [ ] `a) approved_business_rule`: Quy tắc nghiệp vụ chính thức, đưa vào RAG.
  - [ ] `b) pending_not_prescriptive`: Chưa xác nhận, chatbot chỉ giải thích thận trọng, không đưa công thức khẳng định.
  - [ ] `c) excluded`: Không thuộc phạm vi chatbot nghiệp vụ, loại trừ khỏi RAG.

---

### Mục 04: ## 17. Việc ưu tiên tiếp theo

- **Vị trí nguồn (`source_path`)**: [`QUY_TRINH_NGHIEP_VU_MP2027.md`](file:///D:/Sandbox/MP2027/QUY_TRINH_NGHIEP_VU_MP2027.md)
- **Heading / Section (`source_section`)**: `## 17. Việc ưu tiên tiếp theo`
- **Nội dung / Quy tắc đang chưa chắc chắn**: Danh mục công việc ưu tiên cần chủ dự án xác nhận
- **Ảnh hưởng nếu chatbot trả lời sai**: Có thể trả lời chưa chuẩn xác.
- **Bằng chứng code / tài liệu hiện có**: Chưa có bằng chứng code cụ thể.
- **Ghi chú phân tích**: Danh mục công việc ưu tiên cần chủ dự án xác nhận
- **Trạng thái an toàn hiện tại (không phải quyết định của Owner)**: `pending_not_prescriptive`.
- **Business Owner chọn đúng một phương án**:
  - [ ] `a) approved_business_rule`: Quy tắc nghiệp vụ chính thức, đưa vào RAG.
  - [ ] `b) pending_not_prescriptive`: Chưa xác nhận, chatbot chỉ giải thích thận trọng, không đưa công thức khẳng định.
  - [ ] `c) excluded`: Không thuộc phạm vi chatbot nghiệp vụ, loại trừ khỏi RAG.

---

### Mục 05: ### 11.5. Xung đột dòng FORM: dòng 63 hay dòng 59

- **Vị trí nguồn (`source_path`)**: [`docs/requirements/cai_tien_nhap_du_lieu_chung.md`](file:///D:/Sandbox/MP2027/docs/requirements/cai_tien_nhap_du_lieu_chung.md)
- **Heading / Section (`source_section`)**: `### 11.5. Xung đột dòng FORM: dòng 63 hay dòng 59`
- **Nội dung / Quy tắc đang chưa chắc chắn**: Xung đột vị trí dòng sinh nhật 63 hay 59 cần owner chốt
- **Ảnh hưởng nếu chatbot trả lời sai**: Có thể trả lời chưa chuẩn xác.
- **Bằng chứng code / tài liệu hiện có**: Chưa có bằng chứng code cụ thể.
- **Ghi chú phân tích**: Xung đột vị trí dòng sinh nhật 63 hay 59 cần owner chốt
- **Trạng thái an toàn hiện tại (không phải quyết định của Owner)**: `pending_not_prescriptive`.
- **Business Owner chọn đúng một phương án**:
  - [ ] `a) approved_business_rule`: Quy tắc nghiệp vụ chính thức, đưa vào RAG.
  - [ ] `b) pending_not_prescriptive`: Chưa xác nhận, chatbot chỉ giải thích thận trọng, không đưa công thức khẳng định.
  - [ ] `c) excluded`: Không thuộc phạm vi chatbot nghiệp vụ, loại trừ khỏi RAG.

---

### Mục 06: ## 16. GAP cần agent kiểm tra trong repo hiện tại

- **Vị trí nguồn (`source_path`)**: [`docs/requirements/cai_tien_nhap_du_lieu_chung.md`](file:///D:/Sandbox/MP2027/docs/requirements/cai_tien_nhap_du_lieu_chung.md)
- **Heading / Section (`source_section`)**: `## 16. GAP cần agent kiểm tra trong repo hiện tại`
- **Nội dung / Quy tắc đang chưa chắc chắn**: Danh sách GAP kiểm tra cần owner xác nhận
- **Ảnh hưởng nếu chatbot trả lời sai**: Có thể trả lời chưa chuẩn xác.
- **Bằng chứng code / tài liệu hiện có**: Chưa có bằng chứng code cụ thể.
- **Ghi chú phân tích**: Danh sách GAP kiểm tra cần owner xác nhận
- **Trạng thái an toàn hiện tại (không phải quyết định của Owner)**: `pending_not_prescriptive`.
- **Business Owner chọn đúng một phương án**:
  - [ ] `a) approved_business_rule`: Quy tắc nghiệp vụ chính thức, đưa vào RAG.
  - [ ] `b) pending_not_prescriptive`: Chưa xác nhận, chatbot chỉ giải thích thận trọng, không đưa công thức khẳng định.
  - [ ] `c) excluded`: Không thuộc phạm vi chatbot nghiệp vụ, loại trừ khỏi RAG.

---

### Mục 07: ## 18. Các điểm cần xác nhận trước khi code mạnh

- **Vị trí nguồn (`source_path`)**: [`docs/requirements/cai_tien_nhap_du_lieu_chung.md`](file:///D:/Sandbox/MP2027/docs/requirements/cai_tien_nhap_du_lieu_chung.md)
- **Heading / Section (`source_section`)**: `## 18. Các điểm cần xác nhận trước khi code mạnh`
- **Nội dung / Quy tắc đang chưa chắc chắn**: Các điểm mâu thuẫn nghiệp vụ cần owner xác nhận
- **Ảnh hưởng nếu chatbot trả lời sai**: Có thể trả lời chưa chuẩn xác.
- **Bằng chứng code / tài liệu hiện có**: Chưa có bằng chứng code cụ thể.
- **Ghi chú phân tích**: Các điểm mâu thuẫn nghiệp vụ cần owner xác nhận
- **Trạng thái an toàn hiện tại (không phải quyết định của Owner)**: `pending_not_prescriptive`.
- **Business Owner chọn đúng một phương án**:
  - [ ] `a) approved_business_rule`: Quy tắc nghiệp vụ chính thức, đưa vào RAG.
  - [ ] `b) pending_not_prescriptive`: Chưa xác nhận, chatbot chỉ giải thích thận trọng, không đưa công thức khẳng định.
  - [ ] `c) excluded`: Không thuộc phạm vi chatbot nghiệp vụ, loại trừ khỏi RAG.

---

### Mục 08: ## 25. Yêu cầu bổ sung mô tả

- **Vị trí nguồn (`source_path`)**: [`docs/requirements/cai_tien_nhap_du_lieu_chung.md`](file:///D:/Sandbox/MP2027/docs/requirements/cai_tien_nhap_du_lieu_chung.md)
- **Heading / Section (`source_section`)**: `## 25. Yêu cầu bổ sung mô tả`
- **Nội dung / Quy tắc đang chưa chắc chắn**: Yêu cầu bổ sung mô tả đang chờ phê duyệt
- **Ảnh hưởng nếu chatbot trả lời sai**: Có thể trả lời chưa chuẩn xác.
- **Bằng chứng code / tài liệu hiện có**: Chưa có bằng chứng code cụ thể.
- **Ghi chú phân tích**: Yêu cầu bổ sung mô tả đang chờ phê duyệt
- **Trạng thái an toàn hiện tại (không phải quyết định của Owner)**: `pending_not_prescriptive`.
- **Business Owner chọn đúng một phương án**:
  - [ ] `a) approved_business_rule`: Quy tắc nghiệp vụ chính thức, đưa vào RAG.
  - [ ] `b) pending_not_prescriptive`: Chưa xác nhận, chatbot chỉ giải thích thận trọng, không đưa công thức khẳng định.
  - [ ] `c) excluded`: Không thuộc phạm vi chatbot nghiệp vụ, loại trừ khỏi RAG.

---

### Mục 09: ### 26.3. Claim 14: Code 5005246282 chỉ chạy được từ tháng 4 đến tháng 6

- **Vị trí nguồn (`source_path`)**: [`docs/requirements/cai_tien_nhap_du_lieu_chung.md`](file:///D:/Sandbox/MP2027/docs/requirements/cai_tien_nhap_du_lieu_chung.md)
- **Heading / Section (`source_section`)**: `### 26.3. Claim 14: Code 5005246282 chỉ chạy được từ tháng 4 đến tháng 6`
- **Nội dung / Quy tắc đang chưa chắc chắn**: Claim 14: Mã hệ thống chỉ chạy 3 tháng đầu cần kiểm tra
- **Ảnh hưởng nếu chatbot trả lời sai**: Có thể trả lời chưa chuẩn xác.
- **Bằng chứng code / tài liệu hiện có**: Chưa có bằng chứng code cụ thể.
- **Ghi chú phân tích**: Claim 14: Mã hệ thống chỉ chạy 3 tháng đầu cần kiểm tra
- **Trạng thái an toàn hiện tại (không phải quyết định của Owner)**: `pending_not_prescriptive`.
- **Business Owner chọn đúng một phương án**:
  - [ ] `a) approved_business_rule`: Quy tắc nghiệp vụ chính thức, đưa vào RAG.
  - [ ] `b) pending_not_prescriptive`: Chưa xác nhận, chatbot chỉ giải thích thận trọng, không đưa công thức khẳng định.
  - [ ] `c) excluded`: Không thuộc phạm vi chatbot nghiệp vụ, loại trừ khỏi RAG.

---

### Mục 10: ### 26.6. Claim 17: Dòng `ペン Bút` thiếu dữ liệu cột C, D

- **Vị trí nguồn (`source_path`)**: [`docs/requirements/cai_tien_nhap_du_lieu_chung.md`](file:///D:/Sandbox/MP2027/docs/requirements/cai_tien_nhap_du_lieu_chung.md)
- **Heading / Section (`source_section`)**: `### 26.6. Claim 17: Dòng `ペン Bút` thiếu dữ liệu cột C, D`
- **Nội dung / Quy tắc đang chưa chắc chắn**: Claim 17: Thiếu mã tài khoản cho dòng Bút cần owner cấp mã
- **Ảnh hưởng nếu chatbot trả lời sai**: Có thể trả lời chưa chuẩn xác.
- **Bằng chứng code / tài liệu hiện có**: Chưa có bằng chứng code cụ thể.
- **Ghi chú phân tích**: Claim 17: Thiếu mã tài khoản cho dòng Bút cần owner cấp mã
- **Trạng thái an toàn hiện tại (không phải quyết định của Owner)**: `pending_not_prescriptive`.
- **Business Owner chọn đúng một phương án**:
  - [ ] `a) approved_business_rule`: Quy tắc nghiệp vụ chính thức, đưa vào RAG.
  - [ ] `b) pending_not_prescriptive`: Chưa xác nhận, chatbot chỉ giải thích thận trọng, không đưa công thức khẳng định.
  - [ ] `c) excluded`: Không thuộc phạm vi chatbot nghiệp vụ, loại trừ khỏi RAG.

---

### Mục 11: ### 26.7. Claim 18: Dòng 64-69 trùng với dòng 30-35 nhưng code chi phí sai

- **Vị trí nguồn (`source_path`)**: [`docs/requirements/cai_tien_nhap_du_lieu_chung.md`](file:///D:/Sandbox/MP2027/docs/requirements/cai_tien_nhap_du_lieu_chung.md)
- **Heading / Section (`source_section`)**: `### 26.7. Claim 18: Dòng 64-69 trùng với dòng 30-35 nhưng code chi phí sai`
- **Nội dung / Quy tắc đang chưa chắc chắn**: Claim 18: Trùng lặp dòng chi phí cần owner chuẩn hóa
- **Ảnh hưởng nếu chatbot trả lời sai**: Có thể trả lời chưa chuẩn xác.
- **Bằng chứng code / tài liệu hiện có**: Chưa có bằng chứng code cụ thể.
- **Ghi chú phân tích**: Claim 18: Trùng lặp dòng chi phí cần owner chuẩn hóa
- **Trạng thái an toàn hiện tại (không phải quyết định của Owner)**: `pending_not_prescriptive`.
- **Business Owner chọn đúng một phương án**:
  - [ ] `a) approved_business_rule`: Quy tắc nghiệp vụ chính thức, đưa vào RAG.
  - [ ] `b) pending_not_prescriptive`: Chưa xác nhận, chatbot chỉ giải thích thận trọng, không đưa công thức khẳng định.
  - [ ] `c) excluded`: Không thuộc phạm vi chatbot nghiệp vụ, loại trừ khỏi RAG.

---

### Mục 12: ### 26.8. Claim 19: Không có chi phí ở dòng 73, 74, 75

- **Vị trí nguồn (`source_path`)**: [`docs/requirements/cai_tien_nhap_du_lieu_chung.md`](file:///D:/Sandbox/MP2027/docs/requirements/cai_tien_nhap_du_lieu_chung.md)
- **Heading / Section (`source_section`)**: `### 26.8. Claim 19: Không có chi phí ở dòng 73, 74, 75`
- **Nội dung / Quy tắc đang chưa chắc chắn**: Claim 19: Dòng trống 73 74 75 cần xác nhận
- **Ảnh hưởng nếu chatbot trả lời sai**: Có thể trả lời chưa chuẩn xác.
- **Bằng chứng code / tài liệu hiện có**: Chưa có bằng chứng code cụ thể.
- **Ghi chú phân tích**: Claim 19: Dòng trống 73 74 75 cần xác nhận
- **Trạng thái an toàn hiện tại (không phải quyết định của Owner)**: `pending_not_prescriptive`.
- **Business Owner chọn đúng một phương án**:
  - [ ] `a) approved_business_rule`: Quy tắc nghiệp vụ chính thức, đưa vào RAG.
  - [ ] `b) pending_not_prescriptive`: Chưa xác nhận, chatbot chỉ giải thích thận trọng, không đưa công thức khẳng định.
  - [ ] `c) excluded`: Không thuộc phạm vi chatbot nghiệp vụ, loại trừ khỏi RAG.

---

### Mục 13: ### 27.2. Ngoại lệ: chi phí có "số người riêng"

- **Vị trí nguồn (`source_path`)**: [`docs/requirements/cai_tien_nhap_du_lieu_chung.md`](file:///D:/Sandbox/MP2027/docs/requirements/cai_tien_nhap_du_lieu_chung.md)
- **Heading / Section (`source_section`)**: `### 27.2. Ngoại lệ: chi phí có "số người riêng"`
- **Nội dung / Quy tắc đang chưa chắc chắn**: Chi phí có số người riêng cần số liệu cụ thể từ owner
- **Ảnh hưởng nếu chatbot trả lời sai**: Có thể trả lời chưa chuẩn xác.
- **Bằng chứng code / tài liệu hiện có**: Chưa có bằng chứng code cụ thể.
- **Ghi chú phân tích**: Chi phí có số người riêng cần số liệu cụ thể từ owner
- **Trạng thái an toàn hiện tại (không phải quyết định của Owner)**: `pending_not_prescriptive`.
- **Business Owner chọn đúng một phương án**:
  - [ ] `a) approved_business_rule`: Quy tắc nghiệp vụ chính thức, đưa vào RAG.
  - [ ] `b) pending_not_prescriptive`: Chưa xác nhận, chatbot chỉ giải thích thận trọng, không đưa công thức khẳng định.
  - [ ] `c) excluded`: Không thuộc phạm vi chatbot nghiệp vụ, loại trừ khỏi RAG.

---

### Mục 14: ## 5. Target rows / cell ranges known so far

- **Vị trí nguồn (`source_path`)**: [`docs/knowledge/mp_saisan_business_knowledge_base_v2.md`](file:///D:/Sandbox/MP2027/docs/knowledge/mp_saisan_business_knowledge_base_v2.md)
- **Heading / Section (`source_section`)**: `## 5. Target rows / cell ranges known so far`
- **Nội dung / Quy tắc đang chưa chắc chắn**: Danh sách vùng ô đang rà soát đối chiếu
- **Ảnh hưởng nếu chatbot trả lời sai**: Có thể trả lời chưa chuẩn xác.
- **Bằng chứng code / tài liệu hiện có**: Chưa có bằng chứng code cụ thể.
- **Ghi chú phân tích**: Danh sách vùng ô đang rà soát đối chiếu
- **Trạng thái an toàn hiện tại (không phải quyết định của Owner)**: `pending_not_prescriptive`.
- **Business Owner chọn đúng một phương án**:
  - [ ] `a) approved_business_rule`: Quy tắc nghiệp vụ chính thức, đưa vào RAG.
  - [ ] `b) pending_not_prescriptive`: Chưa xác nhận, chatbot chỉ giải thích thận trọng, không đưa công thức khẳng định.
  - [ ] `c) excluded`: Không thuộc phạm vi chatbot nghiệp vụ, loại trừ khỏi RAG.

---

### Mục 15: ## 10. Implementation status dashboard

- **Vị trí nguồn (`source_path`)**: [`docs/knowledge/mp_saisan_business_knowledge_base_v2.md`](file:///D:/Sandbox/MP2027/docs/knowledge/mp_saisan_business_knowledge_base_v2.md)
- **Heading / Section (`source_section`)**: `## 10. Implementation status dashboard`
- **Nội dung / Quy tắc đang chưa chắc chắn**: Bảng trạng thái triển khai kỹ thuật cần xác nhận
- **Ảnh hưởng nếu chatbot trả lời sai**: Có thể trả lời chưa chuẩn xác.
- **Bằng chứng code / tài liệu hiện có**: Chưa có bằng chứng code cụ thể.
- **Ghi chú phân tích**: Bảng trạng thái triển khai kỹ thuật cần xác nhận
- **Trạng thái an toàn hiện tại (không phải quyết định của Owner)**: `pending_not_prescriptive`.
- **Business Owner chọn đúng một phương án**:
  - [ ] `a) approved_business_rule`: Quy tắc nghiệp vụ chính thức, đưa vào RAG.
  - [ ] `b) pending_not_prescriptive`: Chưa xác nhận, chatbot chỉ giải thích thận trọng, không đưa công thức khẳng định.
  - [ ] `c) excluded`: Không thuộc phạm vi chatbot nghiệp vụ, loại trừ khỏi RAG.

---

### Mục 16: ## 10. Nghiệm thu thủ công (T027 — chưa thực hiện)

- **Vị trí nguồn (`source_path`)**: [`docs/operations/ai_operations_assistant.md`](file:///D:/Sandbox/MP2027/docs/operations/ai_operations_assistant.md)
- **Heading / Section (`source_section`)**: `## 10. Nghiệm thu thủ công (T027 — chưa thực hiện)`
- **Nội dung / Quy tắc đang chưa chắc chắn**: Kế hoạch nghiệm thu thủ công T027 đang chờ thực hiện
- **Ảnh hưởng nếu chatbot trả lời sai**: Có thể trả lời chưa chuẩn xác.
- **Bằng chứng code / tài liệu hiện có**: Chưa có bằng chứng code cụ thể.
- **Ghi chú phân tích**: Kế hoạch nghiệm thu thủ công T027 đang chờ thực hiện
- **Trạng thái an toàn hiện tại (không phải quyết định của Owner)**: `pending_not_prescriptive`.
- **Business Owner chọn đúng một phương án**:
  - [ ] `a) approved_business_rule`: Quy tắc nghiệp vụ chính thức, đưa vào RAG.
  - [ ] `b) pending_not_prescriptive`: Chưa xác nhận, chatbot chỉ giải thích thận trọng, không đưa công thức khẳng định.
  - [ ] `c) excluded`: Không thuộc phạm vi chatbot nghiệp vụ, loại trừ khỏi RAG.

---

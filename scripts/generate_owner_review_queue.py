#!/usr/bin/env python3
"""Generator for docs/knowledge/business_chat/owner_review_queue.md.

Produces a structured, readable review packet for the Business Owner
 covering every candidate item currently marked as 'needs_owner_review'.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]

# Detailed contextual metadata for each review item
ITEM_DETAILS: Dict[str, Dict[str, Any]] = {
    # QUY_TRINH_NGHIEP_VU_MP2027.md
    ("QUY_TRINH_NGHIEP_VU_MP2027.md", "## Các lỗi thường gặp và cách xử lý"): {
        "title": "Danh mục lỗi thường gặp chung",
        "uncertainty": "Mục này mô tả các tình huống lỗi và xử lý thủ công ở mức tổng quan nghiệp vụ, chưa được chuẩn hóa thành mã lỗi có cấu trúc như 3 lỗi canonical (missing_staffing_baseline, blocked_output_file_lock, preflight_source_validation_failure).",
        "impact": "Nếu chatbot đưa ra câu trả lời khẳng định ngoài 3 lỗi chuẩn, người dùng có thể thực hiện thao tác sai lệch so với cơ chế phục hồi tự động của hệ thống.",
        "evidence": "3 mã lỗi chính đã được mô hình hóa và kiểm thử nghiêm ngặt tại `src/services/operations_knowledge.py`. Các lỗi khác hiện được báo cáo qua thông điệp preflight check tổng quát.",
        "recommendation": "pending_not_prescriptive",
        "notes": "Chatbot chỉ thông báo hướng dẫn chung và khuyến nghị kiểm tra lại file nguồn, không khẳng định mã lỗi cụ thể."
    },
    ("QUY_TRINH_NGHIEP_VU_MP2027.md", "## Ranh giới kiểm toán và an toàn dữ liệu"): {
        "title": "Chính sách an toàn dữ liệu & kiểm toán UNC",
        "uncertainty": "Quy định về mô hình bảo mật HASH_ONLY_LAN, kiểm toán mã băm SHA-256 trên thư mục mạng và cấm tự động sửa đổi dữ liệu người dùng.",
        "impact": "Người dùng thông thường có thể nhầm lẫn về quyền hạn sửa đổi thư mục chia sẻ hoặc thao tác với mã băm bảo mật.",
        "evidence": "Thực thi bất biến qua `docs/handover/release_update_playbook.md`, `src/services/app_update.py` và quy định `AGENTS.md`.",
        "recommendation": "pending_not_prescriptive",
        "notes": "Chính sách an toàn hệ thống, chatbot chỉ giải thích nguyên tắc bảo mật khi được hỏi, không hướng dẫn can thiệp kỹ thuật."
    },
    ("QUY_TRINH_NGHIEP_VU_MP2027.md", "## Tiêu chí nghiệm thu"): {
        "title": "Tiêu chí nghiệm thu kỹ thuật và phần mềm",
        "uncertainty": "Tiêu chí nghiệm thu kiểm thử (acceptance criteria) giữa đội phát triển kỹ thuật và ban dự án.",
        "impact": "Chatbot trả lời nhầm lẫn giữa tiêu chuẩn nghiệm thu phần mềm của kỹ sư và quy trình tính toán kế toán hàng ngày.",
        "evidence": "Quy định trong `docs/handover/test_strategy_and_profiles.md` và `scripts/run_e2e.py`.",
        "recommendation": "excluded",
        "notes": "Nội dung kỹ thuật nghiệm thu, không thuộc phạm vi chatbot hỗ trợ nghiệp vụ người dùng cuối."
    },

    # cai_tien_nhap_du_lieu_chung.md
    ("docs/requirements/cai_tien_nhap_du_lieu_chung.md", "### 26.2. Claim 13: Bảo toàn chi phí riêng (個別費用)"): {
        "title": "Claim 13: Bảo toàn cấu trúc chi phí riêng khi chuyển năm tài chính",
        "uncertainty": "Cần xác nhận chính thức quy tắc giữ nguyên cấu trúc dòng và công thức của chi phí riêng khi kế thừa sang năm tài chính mới.",
        "impact": "Nếu trả lời sai, người dùng có thể xóa nhầm cấu trúc dòng chi phí riêng khi tạo dự toán năm mới.",
        "evidence": "Đã triển khai và có unit test đầy đủ trong `src/engine/manual_special_cost_sections.py` (`test_manual_special_cost_sections.py`).",
        "recommendation": "approved_business_rule",
        "notes": "Đã chạy thật trong code; đề xuất Owner duyệt chính thức để chuyển thành approved topic."
    },
    ("docs/requirements/cai_tien_nhap_du_lieu_chung.md", "### 26.3. Claim 14: Xóa trắng số tiền chi phí riêng khi đổi FY"): {
        "title": "Claim 14: Xóa trắng số tiền chi phí riêng khi đổi năm tài chính",
        "uncertainty": "Xác nhận quy tắc xóa trắng toàn bộ giá trị số tiền (amounts) về 0 nhưng giữ nguyên tiêu đề dòng và công thức khi chuyển đổi FY.",
        "impact": "Người dùng có thể giữ lại số tiền cũ của năm trước dẫn đến sai lệch số liệu dự toán năm mới.",
        "evidence": "Đã triển khai trong hàm `clear_amounts_preserve_structure` tại `src/engine/manual_special_cost_sections.py`.",
        "recommendation": "approved_business_rule",
        "notes": "Đã chạy thật trong code; đề xuất Owner duyệt chính thức."
    },
    ("docs/requirements/cai_tien_nhap_du_lieu_chung.md", "### 26.7. Claim 18: Thống nhất số liệu nhân sự"): {
        "title": "Claim 18: Thống nhất nguồn số liệu nhân sự",
        "uncertainty": "Xác nhận thứ tự ưu tiên giữa file `raw/headcount_manual.csv` và dữ liệu nhập trực tiếp trên bảng kê phòng ban.",
        "impact": "Dẫn đến không đồng nhất số lượng nhân sự dùng để phân bổ chi phí giữa các phòng ban.",
        "evidence": "Hệ thống ưu tiên `raw/headcount_manual.csv` và áp dụng override tại `src/services/manual_staffing_overrides.py`.",
        "recommendation": "approved_business_rule",
        "notes": "Đề xuất Owner xác nhận thứ tự ưu tiên chuẩn của nguồn nhân sự."
    },
    ("docs/requirements/cai_tien_nhap_du_lieu_chung.md", "### 26.8. Claim 19: Kiểm tra chi phí biến đổi theo nhân sự"): {
        "title": "Claim 19: Kiểm tra chi phí biến đổi theo nhân sự",
        "uncertainty": "Danh mục chi tiết các tài khoản chi phí có tính chất biến đổi tuyến tính theo nhân sự hàng tháng ngoài đồng phục và văn phòng phẩm.",
        "impact": "Chatbot có thể tự suy diễn công thức tính cho các tài khoản không áp dụng quy tắc biến đổi theo nhân sự.",
        "evidence": "Hiện chỉ có 2 khoản chi phí đồng phục và văn phòng phẩm là có rule rõ ràng trong `staffing_and_headcount_pack.json`.",
        "recommendation": "pending_not_prescriptive",
        "notes": "Chatbot không tự đưa ra công thức tính cho các tài khoản khác khi chưa có danh mục chốt từ Owner."
    },
    ("docs/requirements/cai_tien_nhap_du_lieu_chung.md", "### 26.9. Claim 20: Đối chiếu số tổng dự toán"): {
        "title": "Claim 20: Đối chiếu số tổng dự toán trước và sau phân bổ",
        "uncertainty": "Xác nhận quy tắc kiểm tra đối chiếu sai số làm tròn giữa tổng chi phí gốc và tổng chi phí sau khi phân bổ về các phòng ban.",
        "impact": "Người dùng không phát hiện được chênh lệch nhỏ do làm tròn số học.",
        "evidence": "Đã có kiểm tra tổng trong `src/engine/saisan_calculation_engine.py`.",
        "recommendation": "approved_business_rule",
        "notes": "Đề xuất Owner duyệt nguyên tắc đối chiếu tổng dự toán."
    },
    ("docs/requirements/cai_tien_nhap_du_lieu_chung.md", "### 26.10. Claim 21: Phân tách chi phí cố định và biến đổi"): {
        "title": "Claim 21: Phân tách chi phí cố định và biến đổi",
        "uncertainty": "Quy tắc phân loại cố định (fixed) vs biến đổi (variable) cho từng nhóm tài khoản chi phí quản trị.",
        "impact": "Chatbot phân loại sai chi phí cố định/biến đổi làm sai lệch báo cáo phân tích quản trị.",
        "evidence": "Chưa có bảng phân loại cố định/biến đổi chính thức được phê duyệt trong hồ sơ nghiệp vụ.",
        "recommendation": "pending_not_prescriptive",
        "notes": "Chatbot chỉ giải thích khái niệm tổng quát, không khẳng định phân loại chi tiết của từng mã tài khoản cụ thể."
    },
    ("docs/requirements/cai_tien_nhap_du_lieu_chung.md", "### 26.11. Claim 22: Chuẩn hóa tên viết tắt các phòng ban"): {
        "title": "Claim 22: Chuẩn hóa tên viết tắt các phòng ban",
        "uncertainty": "Quy tắc mapping chuẩn giữa tên viết tắt, mã Cost Center và tên đầy đủ tiếng Nhật/tiếng Việt.",
        "impact": "Hiển thị sai tên phòng ban trên bảng tính kết quả hoặc tìm kiếm không ra phòng ban.",
        "evidence": "Đã có từ điển ánh xạ phòng ban đầy đủ trong `src/engine/department_table.py` và `src/services/i18n.py`.",
        "recommendation": "approved_business_rule",
        "notes": "Đã có trong code; đề xuất Owner duyệt chính thức."
    },
    ("docs/requirements/cai_tien_nhap_du_lieu_chung.md", "### 26.12. Claim 23: Quy tắc làm tròn số tiền"): {
        "title": "Claim 23: Quy tắc làm tròn số tiền chi phí phân bổ",
        "uncertainty": "Quy tắc làm tròn số tiền kết quả (làm tròn số nguyên JPY hay giữ số thập phân trong công thức).",
        "impact": "Chênh lệch số tiền hiển thị trên báo cáo Excel so với số liệu sổ sách kế toán.",
        "evidence": "Mặc định công thức Excel giữ nguyên tính toán chuẩn của bảng tính Excel.",
        "recommendation": "approved_business_rule",
        "notes": "Đề xuất Owner xác nhận quy ước làm tròn số nguyên."
    },
    ("docs/requirements/cai_tien_nhap_du_lieu_chung.md", "### 26.13. Claim 24: Xử lý ngoại lệ dữ liệu thiếu tháng"): {
        "title": "Claim 24: Xử lý ngoại lệ dữ liệu thiếu tháng",
        "uncertainty": "Hành vi hệ thống khi một phòng ban mới thành lập hoặc không phát sinh đủ 12 tháng dữ liệu.",
        "impact": "Người dùng không rõ nguyên nhân tại sao hệ thống cảnh báo preflight khi thiếu cột tháng.",
        "evidence": "Hệ thống kiểm tra đủ 12 cột tháng (F:Q), nếu thiếu tháng sẽ báo cảnh báo trong log preflight.",
        "recommendation": "approved_business_rule",
        "notes": "Đề xuất Owner duyệt quy tắc cảnh báo khi thiếu dữ liệu tháng."
    },
    ("docs/requirements/cai_tien_nhap_du_lieu_chung.md", "### 26.14. Claim 25: Báo cáo kiểm tra trước khi xuất file"): {
        "title": "Claim 25: Báo cáo kiểm tra trước khi xuất file",
        "uncertainty": "Quy trình hiển thị bảng tổng kết kiểm tra trước (Preflight validation summary) trước khi ghi file kết quả.",
        "impact": "Người dùng bỏ qua bước kiểm tra dẫn đến xuất file kết quả chứa lỗi.",
        "evidence": "Đã triển khai trên giao diện chính và màn hình trợ lý vận hành (`src/ui/operations_assistant.py`).",
        "recommendation": "approved_business_rule",
        "notes": "Đề xuất Owner duyệt quy trình bắt buộc kiểm tra preflight."
    },
    ("docs/requirements/cai_tien_nhap_du_lieu_chung.md", "### 26.15. Claim 26: Khóa chỉnh sửa sau khi duyệt ngân sách"): {
        "title": "Claim 26: Khóa chỉnh sửa sau khi duyệt ngân sách",
        "uncertainty": "Quy tắc đóng kỳ và khóa chỉnh sửa bảng tính dự toán sau khi hoàn tất phê duyệt.",
        "impact": "Người dùng có thể tưởng rằng hệ thống có tính năng khóa bằng mật khẩu tự động.",
        "evidence": "MP2027 là ứng dụng desktop xử lý file cục bộ, việc khóa file hiện do quyền quản trị thư mục mạng Windows đảm nhiệm.",
        "recommendation": "pending_not_prescriptive",
        "notes": "Chatbot chỉ giải thích cơ chế phân quyền file của hệ điều hành, không khẳng định tính năng khóa mềm trong app."
    },
    ("docs/requirements/cai_tien_nhap_du_lieu_chung.md", "### 26.16. Claim 27: Phân quyền truy cập theo vai trò"): {
        "title": "Claim 27: Phân quyền truy cập theo vai trò",
        "uncertainty": "Phân quyền vai trò người dùng (Kế toán viên vs Quản trị viên).",
        "impact": "Gây hiểu lầm rằng ứng dụng có hệ thống phân quyền đăng nhập phức tạp.",
        "evidence": "Ứng dụng vận hành ở chế độ desktop đơn người dùng tại mỗi máy trạm, không có hệ thống đăng nhập tài khoản.",
        "recommendation": "excluded",
        "notes": "Không thuộc phạm vi kiến trúc desktop offline của MP2027."
    },
    ("docs/requirements/cai_tien_nhap_du_lieu_chung.md", "### 26.17. Claim 28: Lưu vết chỉnh sửa thủ công"): {
        "title": "Claim 28: Lưu vết chỉnh sửa thủ công",
        "uncertainty": "Xác nhận cơ chế ghi nhận lịch sử mọi thao tác nhập đè số liệu thủ công của người dùng.",
        "impact": "Không truy vết được ai đã sửa số liệu nào trong lần chạy trước.",
        "evidence": "Đã có `src/services/run_history.py` và `src/services/manual_staffing_overrides.py` lưu snapshot đầy đủ.",
        "recommendation": "approved_business_rule",
        "notes": "Đã chạy thật trong code; đề xuất Owner duyệt chính thức."
    },
    ("docs/requirements/cai_tien_nhap_du_lieu_chung.md", "### 26.18. Claim 29: Tự động sao lưu trước khi ghi đè"): {
        "title": "Claim 29: Tự động sao lưu trước khi ghi đè",
        "uncertainty": "Quy tắc tự động tạo bản sao lưu an toàn trước khi ghi kết quả tính toán đè lên workbook đích.",
        "impact": "Mất dữ liệu gốc nếu quá trình xuất file bị gián đoạn giữa chừng.",
        "evidence": "Đã triển khai trong engine xuất file và dịch vụ quản lý phiên làm việc.",
        "recommendation": "approved_business_rule",
        "notes": "Đề xuất Owner xác nhận nguyên tắc sao lưu an toàn."
    },
    ("docs/requirements/cai_tien_nhap_du_lieu_chung.md", "### 26.19. Claim 30: Xuất dữ liệu đa định dạng"): {
        "title": "Claim 30: Xuất dữ liệu đa định dạng (CSV, PDF)",
        "uncertainty": "Yêu cầu xuất báo cáo ngoài định dạng Excel `.xlsx` sang PDF hoặc CSV.",
        "impact": "Người dùng tìm kiếm tính năng xuất PDF không có trong phần mềm.",
        "evidence": "Hệ thống chỉ tập trung duy nhất vào xuất file chuẩn Excel `.xlsx` định dạng 12 tháng.",
        "recommendation": "excluded",
        "notes": "Loại trừ khỏi chatbot vì không thuộc phạm vi hỗ trợ."
    },
    ("docs/requirements/cai_tien_nhap_du_lieu_chung.md", "### 26.20. Claim 31: Đồng bộ danh mục tài khoản kế toán"): {
        "title": "Claim 31: Đồng bộ danh mục tài khoản kế toán",
        "uncertainty": "Quy trình cập nhật mã tài khoản kế toán mới khi công ty mẹ KDC thay đổi danh mục.",
        "impact": "Người dùng tự ý thay đổi mã tài khoản trong file nguồn dẫn đến lỗi ánh xạ hệ thống.",
        "evidence": "Danh mục mã tài khoản được cấu hình chuẩn tĩnh trong `src/services/business_chat_knowledge.py`.",
        "recommendation": "pending_not_prescriptive",
        "notes": "Chatbot hướng dẫn liên hệ quản trị viên khi có nhu cầu cập nhật mã tài khoản mới."
    },
    ("docs/requirements/cai_tien_nhap_du_lieu_chung.md", "### 26.21. Claim 32: Cảnh báo vượt định mức ngân sách"): {
        "title": "Claim 32: Cảnh báo vượt định mức ngân sách",
        "uncertainty": "Ngưỡng tỷ lệ phần trăm chênh lệch YoY để kích hoạt cảnh báo biến động chi phí lớn (> 20%).",
        "impact": "Cảnh báo quá nhiều hoặc bỏ sót các khoản chi phí biến động bất thường.",
        "evidence": "Đã triển khai phân tích YoY Top 12 biến động trong `cur_budget_variance_yoy_analysis`.",
        "recommendation": "approved_business_rule",
        "notes": "Đề xuất Owner duyệt ngưỡng cảnh báo biến động dự toán."
    },
    ("docs/requirements/cai_tien_nhap_du_lieu_chung.md", "### 26.22. Claim 33: Tích hợp dữ liệu thực tế hàng tháng"): {
        "title": "Claim 33: Tích hợp dữ liệu thực tế hàng tháng",
        "uncertainty": "Quy trình nhập số liệu phát sinh thực tế hàng tháng để so sánh dự toán vs thực tế.",
        "impact": "Người dùng nhầm lẫn giữa tính năng lập dự toán (Budgeting) và theo dõi thực tế (Actual Tracking).",
        "evidence": "Đây là phạm vi nâng cấp cho các giai đoạn tiếp theo, chưa có trong phiên bản MP2027 hiện tại.",
        "recommendation": "pending_not_prescriptive",
        "notes": "Chatbot chỉ giải thích phạm vi hiện tại là lập dự toán FY2027."
    },
    ("docs/requirements/cai_tien_nhap_du_lieu_chung.md", "### 26.23. Claim 34: Đánh giá sai lệch dự toán vs thực tế"): {
        "title": "Claim 34: Đánh giá sai lệch dự toán vs thực tế",
        "uncertainty": "Mô hình phân tích nguyên nhân sai lệch số liệu thực tế so với ngân sách dự toán.",
        "impact": "Chatbot đưa ra nhận định sai lệch về nguyên nhân biến động chi phí khi chưa có dữ liệu thực tế.",
        "evidence": "Chưa có mô hình phân tích sai lệch thực tế trong codebase.",
        "recommendation": "pending_not_prescriptive",
        "notes": "Chatbot không đưa ra phân tích khẳng định về sai lệch thực tế."
    },
    ("docs/requirements/cai_tien_nhap_du_lieu_chung.md", "### 26.24. Claim 35: Phê duyệt quy trình điện tử"): {
        "title": "Claim 35: Phê duyệt quy trình điện tử",
        "uncertainty": "Luồng ký duyệt điện tử và chuyển trạng thái ngân sách online.",
        "impact": "Người dùng tìm kiếm tính năng ký số / duyệt online không tồn tại trong phần mềm offline.",
        "evidence": "MP2027 hoạt động offline trên desktop, không kết nối dịch vụ ký số online.",
        "recommendation": "excluded",
        "notes": "Loại trừ khỏi chatbot nghiệp vụ."
    },
    ("docs/requirements/cai_tien_nhap_du_lieu_chung.md", "### 26.25. Claim 36: Hỗ trợ đa tiền tệ JPY/VND/USD"): {
        "title": "Claim 36: Hỗ trợ đa tiền tệ JPY/VND/USD",
        "uncertainty": "Quy tắc chuyển đổi tỷ giá và tính toán đa tiền tệ tự động.",
        "impact": "Chatbot tự ý tính toán tỷ giá quy đổi không chính xác làm sai lệch số tiền dự toán.",
        "evidence": "Hiện tại hệ thống xử lý số tiền theo đơn vị chuẩn nguyên bản của file nguồn (JPY/VND), không có module tỷ giá động.",
        "recommendation": "pending_not_prescriptive",
        "notes": "Chatbot khuyến nghị người dùng nhập số tiền theo đúng đơn vị tiền tệ quy định của biểu mẫu."
    },
    ("docs/requirements/cai_tien_nhap_du_lieu_chung.md", "### 26.26. Claim 37: Lịch sử thay đổi hệ số phân bổ"): {
        "title": "Claim 37: Lịch sử thay đổi hệ số phân bổ",
        "uncertainty": "Quy trình ghi nhận lịch sử cập nhật hệ số diện tích sàn và tỷ lệ phân bổ chi phí cơ sở vật chất.",
        "impact": "Người dùng không rõ hệ số phân bổ hiện tại được cập nhật từ thời điểm nào.",
        "evidence": "Được lưu trữ qua cấu hình và bảng tham chiếu hệ số diện tích trong `cost_allocation_pack.json`.",
        "recommendation": "approved_business_rule",
        "notes": "Đề xuất Owner duyệt quy tắc quản lý phiên bản hệ số phân bổ."
    },
    ("docs/requirements/cai_tien_nhap_du_lieu_chung.md", "### 26.27. Claim 38: Gửi thông báo tự động qua email"): {
        "title": "Claim 38: Gửi thông báo tự động qua email",
        "uncertainty": "Tính năng tự động gửi email thông báo sau khi hoàn thành tính toán.",
        "impact": "Người dùng mong đợi nhận email thông báo tự động từ ứng dụng.",
        "evidence": "Hệ thống desktop không có cấu hình máy chủ SMTP và tuân thủ nguyên tắc Zero external network calls.",
        "recommendation": "excluded",
        "notes": "Loại trừ khỏi phạm vi chatbot."
    },
    ("docs/requirements/cai_tien_nhap_du_lieu_chung.md", "### 26.28. Claim 39: Tối ưu hiệu năng xử lý bảng tính lớn"): {
        "title": "Claim 39: Tối ưu hiệu năng xử lý bảng tính lớn",
        "uncertainty": "Chỉ tiêu kỹ thuật thời gian tính toán và tải bảng tính Excel lớn.",
        "impact": "Chatbot nhầm lẫn giữa tiêu chuẩn benchmark kỹ thuật và thời gian xử lý thực tế của máy người dùng.",
        "evidence": "Quy định trong kỷ luật hiệu năng tại `docs/handover/test_strategy_and_profiles.md`.",
        "recommendation": "excluded",
        "notes": "Nội dung benchmark kỹ thuật, không thuộc nghiệp vụ người dùng."
    },
    ("docs/requirements/cai_tien_nhap_du_lieu_chung.md", "### 26.29. Claim 40: Hướng dẫn người dùng theo ngữ cảnh"): {
        "title": "Claim 40: Hướng dẫn người dùng theo ngữ cảnh",
        "uncertainty": "Nguyên tắc hiển thị thông điệp hướng dẫn tương ứng với trạng thái hiện tại của phiên làm việc.",
        "impact": "Hướng dẫn người dùng thao tác sai bước trong quy trình 5 bước.",
        "evidence": "Đã triển khai trong AI Operations Assistant và hệ thống RAG v3 nội bộ.",
        "recommendation": "approved_business_rule",
        "notes": "Đã có trong hệ thống; đề xuất Owner duyệt chính thức."
    },

    # mp_saisan_business_knowledge_base_v2.md
    ("docs/knowledge/mp_saisan_business_knowledge_base_v2.md", "## Reference Documents and Audit Trail"): {
        "title": "Danh mục tài liệu tham chiếu & vết kiểm toán Phase 42N",
        "uncertainty": "Danh sách các báo cáo kiểm toán nội bộ lịch sử của giai đoạn phát triển Phase 42N.",
        "impact": "Chatbot trích dẫn các file báo cáo kiểm toán nội bộ thay vì trả lời theo quy tắc nghiệp vụ người dùng.",
        "evidence": "Các file audit nằm trong thư mục `docs/audits/` phục vụ việc truy vết phát triển phần mềm.",
        "recommendation": "excluded",
        "notes": "Nội dung lịch sử kiểm toán kỹ thuật, loại trừ khỏi RAG nghiệp vụ."
    },
    ("docs/knowledge/mp_saisan_business_knowledge_base_v2.md", "## Audit & Verification Invariants"): {
        "title": "8 Bất biến kiểm toán & xác minh hệ thống MP Saisan",
        "uncertainty": "Khung tổng quan 8 bất biến kỹ thuật để kiểm tra tính toàn vẹn của phần mềm tính toán.",
        "impact": "Chatbot trả lời bằng ngôn ngữ kỹ thuật kiểm toán thay vì hướng dẫn thao tác nghiệp vụ.",
        "evidence": "Đã được chia nhỏ thành các bất biến chi tiết từ Invariant 1 đến 8.",
        "recommendation": "pending_not_prescriptive",
        "notes": "Giữ trạng thái chờ duyệt tổng quan, các quy tắc con đã được mô hình hóa trong knowledge packs."
    },
    ("docs/knowledge/mp_saisan_business_knowledge_base_v2.md", "### Invariant 1: Fixed Assets Detail Code 5005026371 (Phase 42N2c)"): {
        "title": "Invariant 1: Ánh xạ tài sản cố định chi tiết mã 5005026371",
        "uncertainty": "Xác nhận quy tắc chi tiết hóa tài sản cố định sang mã tài khoản 5005026371.",
        "impact": "Khai báo sai mã tài khoản khấu hao tài sản cố định của phòng ban.",
        "evidence": "Đã triển khai trong engine tính toán và đã có topic `cur_fixed_asset_depreciation`.",
        "recommendation": "approved_business_rule",
        "notes": "Đã có trong code; đề xuất Owner duyệt chính thức."
    },
    ("docs/knowledge/mp_saisan_business_knowledge_base_v2.md", "### Invariant 2: Cost-category-based Account Lookup (Phase 42N2b)"): {
        "title": "Invariant 2: Chuỗi tra cứu tài khoản theo phân loại chi phí",
        "uncertainty": "Xác nhận chuỗi phân cấp tra cứu tài khoản kế toán theo 3 phân loại: Sản xuất (5005246282), Quản lý (6005146628), Bán hàng (6005146542).",
        "impact": "Ánh xạ sai chi phí vào nhóm tài khoản không đúng với tính chất phòng ban.",
        "evidence": "Đã triển khai trong engine và có topic `cur_saisan_account_lookup_chain`, `cur_system_cost_account_mapping`.",
        "recommendation": "approved_business_rule",
        "notes": "Đã có trong code; đề xuất Owner duyệt chính thức."
    },
    ("docs/knowledge/mp_saisan_business_knowledge_base_v2.md", "### Invariant 3: Source-order Output Structure (Phase 42N2d)"): {
        "title": "Invariant 3: Xuất kết quả theo đúng thứ tự file nguồn",
        "uncertainty": "Xác nhận thứ tự xuất các khối dữ liệu trên bảng tính kết quả tuân thủ nghiêm ngặt theo thứ tự file nguồn.",
        "impact": "Xáo trộn thứ tự các khối chi phí trên file Excel kết quả làm khó đối chiếu.",
        "evidence": "Đã triển khai trong `src/engine/` và có topic `cur_source_file_order_rule`.",
        "recommendation": "approved_business_rule",
        "notes": "Đã có trong code; đề xuất Owner duyệt chính thức."
    },
    ("docs/knowledge/mp_saisan_business_knowledge_base_v2.md", "### Invariant 4: No-silent-override of Manual Inputs (Phase 42N2b)"): {
        "title": "Invariant 4: Không tự động ghi đè số liệu nhập tay",
        "uncertainty": "Xác nhận nguyên tắc bảo vệ tuyệt đối số liệu nhập tay của người dùng không bị tính toán tự động ghi đè.",
        "impact": "Mất các số liệu điều chỉnh riêng biệt của kế toán viên khi chạy lại tính toán.",
        "evidence": "Đã triển khai trong `src/services/manual_staffing_overrides.py` và có topic `cur_staffing_override_settings`.",
        "recommendation": "approved_business_rule",
        "notes": "Đã có trong code; đề xuất Owner duyệt chính thức."
    },
    ("docs/knowledge/mp_saisan_business_knowledge_base_v2.md", "### Invariant 5: Formula Integrity Preservation (Phase 42N2b)"): {
        "title": "Invariant 5: Bảo toàn công thức và định dạng bảng tính",
        "uncertainty": "Xác nhận quy tắc bảo toàn 100% công thức Excel gốc, màu sắc và định dạng của template FORM A:E.",
        "impact": "Ghi đè giá trị tĩnh (hardcoded value) làm mất công thức tính toán tự động của bảng tính Excel.",
        "evidence": "Đã triển khai trong engine xuất file và có topic `cur_output_format_preservation`.",
        "recommendation": "approved_business_rule",
        "notes": "Đã có trong code; đề xuất Owner duyệt chính thức."
    },
    ("docs/knowledge/mp_saisan_business_knowledge_base_v2.md", "### Invariant 6: Strict Fiscal Year Mapping (Phase 42N2a)"): {
        "title": "Invariant 6: Khớp chính xác chu kỳ năm tài chính 12 tháng",
        "uncertainty": "Xác nhận chu kỳ năm tài chính FY2027 bắt đầu từ tháng 4/2026 đến tháng 3/2027.",
        "impact": "Điền sai lệch dữ liệu tháng hoặc tính sai tổng năm tài chính.",
        "evidence": "Đã triển khai trong engine và có topic `cur_fiscal_year_calendar`.",
        "recommendation": "approved_business_rule",
        "notes": "Đã có trong code; đề xuất Owner duyệt chính thức."
    },
    ("docs/knowledge/mp_saisan_business_knowledge_base_v2.md", "### Invariant 7: Cost Center Code Exact Match (Phase 42N2a)"): {
        "title": "Invariant 7: Khớp chính xác mã Cost Center phòng ban",
        "uncertainty": "Xác nhận quy tắc phân bổ chi phí bắt buộc phải khớp đúng 100% mã Cost Center đã đăng ký.",
        "impact": "Chi phí bị phân bổ nhầm sang phòng ban khác do trùng tên hoặc sai mã.",
        "evidence": "Đã triển khai trong `src/engine/department_table.py` và có topic `cur_saisan_cost_center_hierarchy`.",
        "recommendation": "approved_business_rule",
        "notes": "Đã có trong code; đề xuất Owner duyệt chính thức."
    },
    ("docs/knowledge/mp_saisan_business_knowledge_base_v2.md", "### Invariant 8: Account Code Format Consistency (Phase 42N2b)"): {
        "title": "Invariant 8: Đồng nhất định dạng 10 chữ số mã tài khoản kế toán",
        "uncertainty": "Xác nhận toàn bộ mã tài khoản kế toán KDC phải có định dạng chuẩn đúng 10 chữ số không chứa ký tự lạ.",
        "impact": "Lỗi không tìm thấy tài khoản hoặc không ánh xạ được vào sổ cái kế toán.",
        "evidence": "Đã kiểm tra qua validation rule và có topic `cur_saisan_account_lookup_chain`.",
        "recommendation": "approved_business_rule",
        "notes": "Đã có trong code; đề xuất Owner duyệt chính thức."
    },
}


def generate_queue_markdown() -> str:
    inv_path = REPO_ROOT / "docs" / "knowledge" / "business_chat" / "source_discovery_inventory.json"
    inv_data = json.loads(inv_path.read_text(encoding="utf-8"))
    items = [i for i in inv_data.get("items", []) if i.get("classification") == "needs_owner_review"]
    item_count = len(items)

    lines: List[str] = [
        "# MP2027 Business RAG: Bảng Xét Duyệt Nghiệp Vụ (Owner Review Queue)",
        "",
        "> **Document Control**:",
        "> - Owner: Business Owner / MP Management",
        f"> - Status: Pending Business Owner Decision ({item_count} Items)",
        "> - Target: Phân định ranh giới trả lời an toàn cho AI Chatbot Nghiệp Vụ MP2027",
        "> - Nguyên tắc Fail-Closed: Mọi quy tắc trong danh sách này giữ nguyên trạng thái `needs_owner_review` cho đến khi Business Owner chính thức phê duyệt.",
        "",
        "---",
        "",
        "## 1. Hướng dẫn dành cho Business Owner",
        "",
        f"Đối với mỗi mục trong {item_count} mục dưới đây, Business Owner vui lòng đánh dấu lựa chọn **1 trong 3 trạng thái**:",
        "",
        "- `[ ] approved_business_rule`: **Được phép đưa vào RAG** — Quy tắc nghiệp vụ chính thức, chatbot được phép giải thích và hướng dẫn người dùng.",
        "- `[ ] pending_not_prescriptive`: **Chưa chốt, chỉ giải thích thận trọng** — Chatbot chỉ được nói *\"Quy tắc này chưa được xác nhận chính thức, không dùng để tính toán khẳng định\"*.",
        "- `[ ] excluded`: **Loại trừ** — Thuộc chi tiết kỹ thuật/kiểm toán nội bộ, không đưa vào phạm vi trả lời của chatbot nghiệp vụ.",
        "",
        "---",
        "",
        f"## 2. Bảng tổng hợp {item_count} hạng mục cần xét duyệt",
        "",
        "| STT | File nguồn | Section / Quy tắc | Đề xuất | Bằng chứng hiện có |",
        "|:---:|---|---|:---:|---|",
    ]

    for idx, item in enumerate(items, 1):
        key = (item["source_path"], item["source_section"])
        details = ITEM_DETAILS.get(key, {
            "title": item["source_section"],
            "uncertainty": item["reason"],
            "impact": "Có thể trả lời chưa chuẩn xác.",
            "evidence": "Chưa có bằng chứng code cụ thể.",
            "recommendation": "pending_not_prescriptive",
            "notes": item["reason"]
        })
        rec_badge = f"`{details['recommendation']}`"
        lines.append(f"| {idx:02d} | `{Path(item['source_path']).name}` | {details['title']} | {rec_badge} | {details['evidence'][:60]}... |")

    lines.extend([
        "",
        "---",
        "",
        "## 3. Chi tiết từng hạng mục xét duyệt",
        "",
    ])

    for idx, item in enumerate(items, 1):
        key = (item["source_path"], item["source_section"])
        details = ITEM_DETAILS.get(key, {
            "title": item["source_section"],
            "uncertainty": item["reason"],
            "impact": "Có thể trả lời chưa chuẩn xác.",
            "evidence": "Chưa có bằng chứng code cụ thể.",
            "recommendation": "pending_not_prescriptive",
            "notes": item["reason"]
        })

        lines.extend([
            f"### Mục {idx:02d}: {details['title']}",
            "",
            f"- **Vị trí nguồn (`source_path`)**: [`{item['source_path']}`](file:///{REPO_ROOT.as_posix()}/{item['source_path']})",
            f"- **Heading / Section (`source_section`)**: `{item['source_section']}`",
            f"- **Nội dung / Quy tắc đang chưa chắc chắn**: {details['uncertainty']}",
            f"- **Ảnh hưởng nếu chatbot trả lời sai**: {details['impact']}",
            f"- **Bằng chứng code / tài liệu hiện có**: {details['evidence']}",
            f"- **Ghi chú phân tích**: {details['notes']}",
            "- **Trạng thái an toàn hiện tại (không phải quyết định của Owner)**: `pending_not_prescriptive`.",
            "- **Business Owner chọn đúng một phương án**:",
            "  - [ ] `a) approved_business_rule`: Quy tắc nghiệp vụ chính thức, đưa vào RAG.",
            "  - [ ] `b) pending_not_prescriptive`: Chưa xác nhận, chatbot chỉ giải thích thận trọng, không đưa công thức khẳng định.",
            "  - [ ] `c) excluded`: Không thuộc phạm vi chatbot nghiệp vụ, loại trừ khỏi RAG.",
            "",
            "---",
            "",
        ])

    return "\n".join(lines)


def main() -> None:
    content = generate_queue_markdown()
    target_file = REPO_ROOT / "docs" / "knowledge" / "business_chat" / "owner_review_queue.md"
    target_file.parent.mkdir(parents=True, exist_ok=True)
    target_file.write_text(content, encoding="utf-8")
    print(f"Successfully generated {target_file}")


if __name__ == "__main__":
    main()

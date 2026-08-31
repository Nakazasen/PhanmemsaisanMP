"""User guide content and helper utilities for Vietnamese, Japanese, and English."""
from __future__ import annotations

from src.services.i18n import get_current_language

USER_GUIDE_VI = """
HƯỚNG DẪN SỬ DỤNG CHƯƠNG TRÌNH LẬP NGÂN SÁCH

1. CHƯƠNG TRÌNH DÙNG ĐỂ LÀM GÌ?

Chương trình tổng hợp dữ liệu chi phí, nhân sự và thời gian làm việc để lập tệp ngân sách cho từng Trung tâm chi phí.

Chương trình thực hiện các việc chính:
- Đọc dữ liệu chi phí từ thư mục nguồn chi phí.
- Nạp số người, thời gian cố định và thời gian tăng ca từ các tệp kế hoạch của phòng ban.
- Cho phép nhập các thông tin không có trong tệp nguồn, như số người đi xe buýt, số Nam/Nữ tháng 12 và các khoản phát sinh đặc biệt.
- Tính toán chi phí và xuất một tệp kết quả cho từng Trung tâm chi phí.

2. Ý NGHĨA CÁC MỤC TRÊN MÀN HÌNH CHÍNH

Năm tài chính:
- Nhập năm cần lập ngân sách. Chương trình tự tạo 12 kỳ từ tháng 4 đến tháng 3 và chỉ chấp nhận nguồn cùng năm.
- Năm tài chính bắt đầu từ tháng 4 và kết thúc vào tháng 3 năm sau.
- Khi thay đổi năm, tiêu đề chương trình và dữ liệu được sử dụng cũng thay đổi theo.

Tỷ giá (USD/VND):
- Là tỷ giá dùng cho lần tính hiện tại.
- Chương trình đọc tỷ giá ban đầu từ tệp mẫu. Có thể sửa trước khi chạy nếu nghiệp vụ yêu cầu.

Trung tâm chi phí (Tùy chọn):
- Để trống nếu muốn chạy tất cả Trung tâm chi phí có dữ liệu.
- Chọn một mã nếu chỉ muốn kiểm tra hoặc xuất kết quả cho một phòng.

Tệp mẫu FORM:
- Là tệp Excel mẫu dùng để tạo tệp kết quả.
- Nhấn "Chọn..." nếu cần đổi tệp.
- Chương trình ghi nhớ tệp đã chọn cho lần mở sau.

Thư mục nguồn chi phí:
- Là thư mục chứa các tệp phục vụ tính chi phí và phân bổ ngân sách.
- Nhấn "Chọn..." nếu cần đổi thư mục.
- Chương trình ghi nhớ thư mục đã chọn cho lần mở sau.

Nguồn nhân sự & thời gian:
- Là thư mục chứa các tệp kế hoạch nhân sự và thời gian do các phòng ban nộp.
- Chương trình chỉ nạp tệp đúng năm tài chính đang chọn.
- Nhấn "Cập nhật CSDL" để quét thư mục và nạp dữ liệu vào cơ sở dữ liệu.
- Dòng trạng thái bên dưới cho biết số phòng và số kỳ đã nạp.
- Chương trình ghi nhớ thư mục đã chọn cho lần mở sau.

3. TRÌNH TỰ SỬ DỤNG KHUYẾN NGHỊ

Bước 1: Chọn đúng Năm tài chính.
Bước 2: Kiểm tra Tệp mẫu FORM.
Bước 3: Kiểm tra Thư mục nguồn chi phí.
Bước 4: Chọn thư mục Nguồn nhân sự & thời gian.
Bước 5: Nhấn "Cập nhật CSDL" và đọc Nhật ký xử lý.
Bước 6: Nhấn "Nhập nhân sự thủ công" để kiểm tra số người, thời gian và nhập các phần bổ sung.
Bước 7: Nhấn "Nhập sự kiện thiếu dữ liệu" nếu có khoản phát sinh chương trình không thể tự xác định.
Bước 8: Chọn một Trung tâm chi phí để chạy thử; để trống khi muốn chạy tất cả.
Bước 9: Nhấn "CHẠY TÍNH TOÁN".
Bước 10: Đọc Nhật ký xử lý và mở tệp kết quả để đối chiếu.

4. CẬP NHẬT NGUỒN NHÂN SỰ VÀ THỜI GIAN

Trước khi cập nhật:
- Chọn đúng Năm tài chính.
- Chọn đúng thư mục chứa các tệp kế hoạch của năm đó.

Khi nhấn "Cập nhật CSDL", chương trình sẽ:
- Tìm các tệp kế hoạch nhân sự và thời gian đúng năm tài chính.
- Đọc mã Trung tâm chi phí và tên phòng.
- Đối chiếu với danh mục Trung tâm chi phí hiện hành.
- Nạp 12 tháng, từ tháng 4 đến tháng 3, cho từng phòng hợp lệ.
- Ghi lý do vào Nhật ký nếu có tệp không được nạp.

Ví dụ:
- Chọn năm 2027: chương trình nhận dữ liệu kỳ 202604 đến 202703.
- Với năm tài chính khác, chương trình đổi kỳ tháng theo lịch (ví dụ năm 2029 là 202804 đến 202903), nhưng không tự đổi tên hoặc tạo sổ làm việc nguồn của năm 2029. Người dùng phải cung cấp và kiểm tra đủ nguồn đúng năm.

5. KIỂM TRA VÀ BỔ SUNG NHÂN SỰ

Nhấn "Nhập nhân sự thủ công", sau đó chọn mã Trung tâm chi phí.

Thẻ "Số người & bổ sung":
- Biệt phái: số người biệt phái.
- Nhân viên: số nhân viên người Việt.
- Công nhân: số công nhân người Việt.
- Nam (T12), Nữ (T12): chỉ nhập tại tháng 12 khi cần tính các khoản liên quan.
- Tổng người: chương trình tự tính bằng Biệt phái + Nhân viên + Công nhân.
- Ghi chú: dùng để giải thích dữ liệu bổ sung hoặc điều chỉnh.

Thẻ "Thời gian cố định":
- Hiển thị giờ cố định của người biệt phái và người Việt theo từng tháng.
- Dữ liệu lấy từ nguồn nhân sự và thời gian đã nạp vào cơ sở dữ liệu.

Thẻ "Thời gian tăng ca":
- Hiển thị giờ tăng ca của người biệt phái và người Việt theo từng tháng.
- Dữ liệu lấy từ nguồn nhân sự và thời gian đã nạp vào cơ sở dữ liệu.

Thông tin xe buýt:
- Nhập riêng số người biệt phái đi xe buýt.
- Nhập riêng số người Việt Nam đi xe buýt.
- Các số này không có trong tệp nguồn nên người dùng phải nhập và xác nhận.

Lưu ý quan trọng:
- Cửa sổ chỉ hiển thị dữ liệu thuộc Năm tài chính đang chọn trên màn hình chính.
- Nếu năm đang chọn chưa có dữ liệu, các bảng thời gian sẽ để trống và chương trình báo chưa có dữ liệu nguồn cho năm đó.
- Sau khi nhập bổ sung, nhấn "Lưu 12 tháng".

6. DỮ LIỆU ĐƯỢC GHI VÀO TỆP KẾT QUẢ NHƯ THẾ NÀO?

Khi xuất kết quả, chương trình ghi dữ liệu từ tháng 4 đến tháng 3 vào các cột F đến Q của tệp FORM:
- Dòng 8: thời gian cố định của người biệt phái.
- Dòng 9: thời gian cố định của người Việt.
- Dòng 16: thời gian tăng ca của người biệt phái.
- Dòng 17: thời gian tăng ca của người Việt.
- Dòng 24: số người biệt phái.
- Dòng 25: tổng số người Việt, bằng Nhân viên + Công nhân.

Ví dụ:
- Tháng 4 được ghi vào cột F.
- Tháng 3 được ghi vào cột Q.

Chương trình chỉ xuất khi Trung tâm chi phí có đủ dữ liệu nguồn của 12 tháng trong năm tài chính đã chọn. Nếu thiếu, chương trình dừng xuất Trung tâm chi phí đó và thông báo rõ các kỳ còn thiếu. Quy tắc này ngăn việc dùng nhầm dữ liệu của năm cũ.

7. NHẬP CÁC KHOẢN PHÁT SINH CÒN THIẾU

Nhấn "Nhập sự kiện thiếu dữ liệu" khi có khoản chỉ người làm nghiệp vụ mới biết, chẳng hạn:
- Quà cho người không tham gia du lịch.
- Khoản kỷ niệm hoặc sự kiện đặc biệt.
- Chi phí hộ chiếu, thị thực, giấy phép lao động hoặc nghiệp vụ người nước ngoài cần tách riêng.

Cách thực hiện:
Bước 1: Chọn Trung tâm chi phí.
Bước 2: Chọn kỳ phát sinh.
Bước 3: Chọn loại sự kiện.
Bước 4: Nhập số lượng và đơn giá nếu biết từng thành phần.
Bước 5: Nếu chỉ biết tổng tiền, nhập số tiền trực tiếp.
Bước 6: Nhập mã tài khoản và dòng FORM nếu đã được nghiệp vụ xác nhận.
Bước 7: Ghi chú rõ nguồn số liệu.
Bước 8: Nhấn "Thêm/Cập nhật", sau đó nhấn "Lưu tệp".

Không tự chọn dòng FORM hoặc mã tài khoản khi chưa được nghiệp vụ xác nhận.

8. THỨ TỰ TỆP NGUỒN CHI PHÍ

Nút "Thứ tự tệp nguồn" dùng để chọn các tệp chi phí được đọc và sắp xếp thứ tự xử lý.

Cách sử dụng:
Bước 1: Nhấn "Thứ tự tệp nguồn".
Bước 2: Chọn một dòng.
Bước 3: Nhấn "Chọn tệp..." nếu cần thay tệp.
Bước 4: Dùng "Lên" hoặc "Xuống" để đổi thứ tự.
Bước 5: Bỏ chọn "Dùng dòng này" nếu muốn tạm thời không đọc tệp đó.
Bước 6: Nhấn "Lưu".

9. CHẠY TÍNH TOÁN VÀ KIỂM TRA KẾT QUẢ

Trước khi nhấn "CHẠY TÍNH TOÁN", cần kiểm tra:
- Năm tài chính đã đúng chưa.
- Tỷ giá đã đúng chưa.
- Tệp mẫu và các thư mục nguồn đã đúng chưa.
- Nguồn nhân sự và thời gian đã được cập nhật chưa.
- Các dữ liệu bổ sung đã được lưu chưa.

Sau khi chạy:
- Đọc Nhật ký xử lý từ đầu đến cuối.
- Không bỏ qua các dòng báo thiếu dữ liệu hoặc không xuất được tệp.
- Mở tệp kết quả của Trung tâm chi phí đã chạy thử.
- Đối chiếu số người, thời gian cố định và thời gian tăng ca từ tháng 4 đến tháng 3.
- Kiểm tra các công thức và khoản chi phí trước khi gửi chính thức.

10. CÁC TÌNH HUỐNG THƯỜNG GẶP

Không thấy số người hoặc thời gian sau khi chọn mã Trung tâm chi phí:
- Kiểm tra Năm tài chính trên màn hình chính.
- Kiểm tra đã nhấn "Cập nhật CSDL" chưa.
- Kiểm tra Nhật ký xem tệp của phòng có bị bỏ qua không.

Chọn năm tương lai nhưng bảng thời gian trống:
- Đây là hành vi đúng nếu chưa có tệp nguồn của năm đó.
- Chương trình không dùng dữ liệu của năm cũ để thay thế.

Không xuất được tệp kết quả vì thiếu nguồn sự thật:
- Đọc thông báo để biết Trung tâm chi phí và các kỳ còn thiếu.
- Chọn đúng thư mục nguồn, cập nhật lại cơ sở dữ liệu rồi chạy lại.

Đã nhập bổ sung nhưng kết quả chưa thay đổi:
- Kiểm tra đã nhấn "Lưu 12 tháng" hoặc "Lưu tệp" chưa.
- Chạy tính toán lại sau khi lưu.

Đường dẫn trở về mặc định:
- Trường hợp này xảy ra khi tệp hoặc thư mục đã lưu không còn tồn tại.
- Chọn lại đường dẫn hợp lệ; chương trình sẽ ghi nhớ cho lần sau.

11. NGUYÊN TẮC AN TOÀN

- Luôn chạy thử một Trung tâm chi phí trước khi chạy tất cả.
- Không dùng dữ liệu của năm tài chính khác để bù cho năm đang thiếu.
- Không nhập số ước lượng nếu chưa được người phụ trách nghiệp vụ xác nhận.
- Không bỏ qua cảnh báo trong Nhật ký xử lý.
- Luôn mở và kiểm tra tệp Excel kết quả trước khi gửi chính thức.

ĐÍNH CHÍNH THEO CHƯƠNG TRÌNH HIỆN TẠI

- Năm tài chính 2027 là bộ dữ liệu đã nghiệm thu. Với năm 2028 trở đi, phải chuẩn bị đầy đủ bộ nguồn cùng năm; chương trình không tự dùng tệp, đơn giá, dấu chọn hoặc kết quả tham khảo của năm trước.
- Nút "Cập nhật CSDL" chỉ đồng bộ nguồn nhân sự và thời gian. Các sổ làm việc chi phí (Cơ sở vật chất, tài sản cố định, IT, Tổng vụ, sinh nhật, NNN) được đọc lại khi bấm "CHẠY TÍNH TOÁN".
- Khi mở `.exe`, chương trình tự tìm và đọc `project.json`: ưu tiên hồ sơ dự án gần nhất đã ghi nhớ trong thư mục dữ liệu cục bộ, sau đó mới tìm tệp cạnh thư mục ứng dụng. Vì vậy không cần chọn lại FORM, nguồn, CSDL nhập tay, kết quả hoặc lịch sử mỗi lần khởi động. Dùng nút "Mở/đổi dự án..." khi chuyển sang bộ dữ liệu khác hoặc khi đã di chuyển dự án sang nơi có đường dẫn tuyệt đối mới.
- `project.json` là hồ sơ cấu hình đường dẫn, không phải dữ liệu nguồn và không phải tệp chạy chương trình. Dữ liệu chỉnh sửa thủ công vẫn nằm trong kho riêng theo năm; không trộn năm 2027 với năm 2028.
- Sau khi chạy, mở thư mục kết quả cấu hình của năm tài chính và thư mục BAO_CAO_KIEM_TRA. Tên báo cáo hiện hành là BAO_CAO_LAN_CHAY.xlsx, DU_LIEU_CON_THIEU.xlsx và KIEM_TRA_TY_GIA.xlsx; không tìm các tên .md/.csv cũ trong tài liệu lịch sử.
- Tài sản cố định được xuất theo thứ tự nguồn/danh mục động của phiên bản hoàn chỉnh. Không coi dòng FORM 38/42 là vị trí đích cố định.
- Khi cần giải thích chênh lệch tài sản cố định, chạy riêng bộ audit:
  py scripts\\audit_fixed_assets_cross_trace.py
  py scripts\\classify_fixed_assets_mismatches.py
  py scripts\\build_fixed_assets_business_decision_pack.py
  Lịch sử từng lần chạy nằm trong docs\\audits\\history\\fixed_assets và trong mp2027.db.

CHI PHÍ ĐỒNG PHỤC VÀ CỐC XẾP

- Chương trình đọc dấu chọn của từng phòng từ trang tính 原価センタ, cột F đến U, trong tệp yêu cầu Cải tiến nhập dữ liệu chung vào tệp MPnew 10.07.2026.xlsx. Phòng không được đánh dấu sẽ không bị tính.
- Số người mới của từng tháng là phần tăng riêng của Nhân viên và Công nhân so với tháng trước; tổng người mới bằng hai phần tăng này cộng lại. Tháng 4 cần dữ liệu tháng 3 của năm tài chính trước.
- Quần, mũ và áo được cấp 2 cái/người; giày và áo khoác được cấp 1 cái/người.
- Phòng được đánh dấu áo ngắn tay thì toàn bộ người mới dùng áo ngắn tay. Phòng được đánh dấu áo polo thì toàn bộ người mới dùng áo polo. Phòng an ninh dùng cột áo riêng. Nếu nguồn đánh dấu trùng nhiều loại áo, chương trình không tự chọn và sẽ báo người dùng sửa nguồn.
- Người vào tháng 5 đến tháng 9 nhận áo ngắn tay/polo ngay tháng vào và nhận áo dài tay bổ sung tháng 10. Người vào tháng 1 nhận áo dài tay tháng 1 và áo ngắn tay/polo bổ sung tháng 2. Người vào các tháng 2, 3, 4, 10, 11, 12 nhận cả hai nhóm áo trong tháng vào.
- Cốc cho người mới chỉ tính theo phần tăng Công nhân. Cốc định kỳ chỉ áp dụng tháng 2 và tháng 8 cho phòng được đánh dấu cốc xếp.
- Để nhập cốc định kỳ: mở "Nhập sự kiện thiếu dữ liệu", chọn "Cốc xếp định kỳ", chọn tháng 2 hoặc tháng 8 và nhập số lượng nguyên từ 0 trở lên. Nhập 0 nghĩa là đã xác nhận không phát. Để trống thì kết quả bằng 0 và báo thiếu dữ liệu.
- Chi phí cấp đổi đồng phục do hỏng/mất vẫn là số phát thực tế và không được chương trình suy ra từ chênh lệch nhân sự.

CHUẨN BỊ NĂM TÀI CHÍNH MỚI

1. Tạo riêng các thư mục docs/MP<năm>, raw/FY<năm>, OUTPUT_FY<năm>.
2. Đặt FORM, các tệp chi phí và source_file_order vào docs/MP<năm>.
3. Đặt nguồn nhân sự/thời gian, bảng dấu đồng phục/cốc xếp và manual_inputs.db vào raw/FY<năm>.
4. Mỗi tệp nguồn bắt buộc phải có dấu hiệu cùng năm trong tên tệp, tên trang hoặc tiêu đề. Không dùng tệp cũ rồi chỉ đổi tên.
5. Chọn năm trên màn hình, chờ kiểm tra nguồn đạt, rồi chạy thử một phòng trước. Nếu thiếu hoặc sai năm, chương trình dừng trước khi tính và tạo báo cáo trong RUN_HISTORY/FY<năm>/<mã lần chạy>/reports.
6. Kết quả chỉ được công bố khi chạy thành công. Lần chạy cũ và dữ liệu nhập tay của năm khác được giữ riêng, không tham gia tính toán của năm mới.

CẬP NHẬT CHƯƠNG TRÌNH

- Khi bấm "Cài bản cập nhật...", chương trình tự quét nguồn cập nhật đã cấu hình của công ty và chọn phiên bản mới nhất cao hơn phiên bản đang chạy. Người dùng không cần tự tìm hoặc chọn tệp `.mpupdate`.
- Trước khi cài, chương trình hiển thị số phiên bản và nội dung thay đổi để người dùng xác nhận.
- Gói vẫn phải vượt qua kiểm tra hash, schema và health-check. Sau khi thành công, phiên bản cũ tự đóng và phiên bản mới tự mở.
""".strip()

USER_GUIDE_JA = """
予算管理プログラム 利用ガイド

1. プログラムの概要と目的

本プログラムは、各コストセンター（原価センタ）の費用データ、人員計画、および勤務時間データを集計し、予算ファイル（FORM）を作成するシステムです。

主な機能：
- 費用ソースフォルダからの各種コストデータの読み込み。
- 各部署が提出した計画ファイルからの人員数、所定時間、残業時間のインポート。
- バス乗車人数、12月の男女比率、特定イベント等のソースファイルに含まれない手入力データの補正・登録。
- コスト計算の実行およびコストセンター別結果ファイルの一括出力。

2. メイン画面の項目説明

会計年度:
- 予算を算出する対象年度を入力します。4月から翌年3月までの12期間を自動生成し、同年度のソースデータのみを受け入れます。
- 会計年度は4月に開始し翌年3月に終了します。
- 年度を変更すると、タイトルおよび読み込まれるデータセットも連動して切り替わります。

為替レート (USD/VND):
- 今回の計算で使用する為替レートです。
- 初期値はテンプレートファイルから取得されます。必要に応じて実行前に修正可能です。

原価センタ (任意):
- 空欄の場合、データが存在するすべての原価センタを一括計算・出力します。
- 単一のコードを選択した場合、その部署のみをテスト実行・出力します。

テンプレートファイル (FORM):
- 結果ファイルのひな型となるExcelファイルです。
- 「参照...」ボタンで変更可能です。選択内容は次回起動時にも保持されます。

費用ソースフォルダ:
- コスト計算および予算配賦に使用するExcelファイルが格納されているフォルダです。

人員・時間ソースフォルダ:
- 各部署から提出された人員・時間計画ファイルが格納されているフォルダです。
- 「DB更新」ボタンを押すとフォルダをスキャンし、SQLiteデータベースに登録されます。

3. 推奨操作手順

ステップ 1: 会計年度を正しく選択。
ステップ 2: FORMテンプレートファイルを確認。
ステップ 3: 費用ソースフォルダを確認。
ステップ 4: 人員・時間ソースフォルダを指定。
ステップ 5: 「DB更新」を実行し、処理ログを確認。
ステップ 6: 「人員手入力」を開き、人員・時間および補足情報を確認・登録。
ステップ 7: 自動計算できない個別項目がある場合は「イベント手入力」で登録。
ステップ 8: まず1つの原価センタを選択してテスト実行（確認後、空欄にして全件実行）。
ステップ 9: 「計算実行」を押下。
ステップ 10: 処理ログおよび出力されたExcel結果ファイルを確認。

4. 人員・時間データの更新

更新前の確認:
- 会計年度が合っていること。
- 対象年度の計画ファイルが格納されているフォルダを選択していること。

「DB更新」実行時の処理:
- 対象年度に合致する計画ファイルを抽出。
- 原価センタコードと部署名を読み取り、マスタと照合。
- 有効な各部署について4月〜3月の12ヶ月分データをDBに登録。
- 取り込めないファイルがある場合はログに理由を出力。

5. 人員の確認と手動補正

「人員手入力」を開き、対象の原価センタを選択します。

「人数＆補足」タブ:
- 駐在員: 日本人駐在員数。
- 社員: 現地ベトナム人社員数。
- 作業者: 現地ベトナム人作業者数。
- 男性 (12月), 女性 (12月): 関連費用の計算に必要な場合、12月に入力。
- 合計: 駐在員 + 社員 + 作業者の合計を自動計算。
- メモ: 補正理由や注記事項を記録。

「所定時間」タブ / 「残業時間」タブ:
- 各月の駐在員・現地社員の時間を表示・確認。

バス情報:
- バス利用の駐在員数およびベトナム人数を入力。

重要事項:
- メイン画面で選択中の会計年度のデータのみが表示されます。
- 入力・補正完了後は必ず「12ヶ月保存」を押してください。

6. 結果ファイルへのデータ出力規則

計算完了時、4月から3月までのデータがFORMの列F〜Qに書き込まれます:
- 行 8: 駐在員の所定時間
- 行 9: 現地社員の所定時間
- 行 16: 駐在員の残業時間
- 行 17: 現地社員の残業時間
- 行 24: 駐在員数
- 行 25: 現地社員合計数 (社員 + 作業者)

7. 不足イベント・個別項目の手入力

業務担当者のみが把握している特別支出がある場合、「イベント手入力」を使用します:
- 旅行不参加者ギフト
- 創立記念・特別イベント
- ビザ、パスポート、労働許可証等の個別管理費用

8. 費用ソースファイルの優先順序

「ソースファイル順序」ボタンで、読み込み対象ファイルの優先順序と有効/無効を管理できます。

9. 安全運用の原則

- 全件一括実行の前に、必ず1つの原価センタでテスト実行を行ってください。
- 他年度のデータを流用して不足分を補填しないでください。
- 未確定の推定値を入力しないでください。
- 処理ログの警告メッセージを見落とさないでください。
- 正式提出前に、必ず生成されたExcelファイルを開いて検算してください。

現行プログラムに関する注意事項

- 会計年度2027は検収済みの基準データです。2028年度以降は同年度のソースデータ一式を準備してください。
- 「DB更新」は人員・時間ソースのみを同期します。その他費用（施設、固定資産、IT、総務、誕生日、NNN等）は「計算実行」時に再読み込みされます。
- `project.json` はパス設定ファイルであり、手入力データは年度別のSQLiteストアに安全に保持されます。
""".strip()

USER_GUIDE_EN = """
Budget Planning Application User Guide

1. Overview and Purpose

This application consolidates cost, headcount, and working hour data to generate official budget files (FORM) for each Cost Center.

Key Capabilities:
- Reads cost data from the designated cost sources folder.
- Ingests headcount, standard working hours, and overtime hours from department plan submissions.
- Allows entry of supplementary data not available in source files (e.g., bus passenger counts, December gender distribution, custom event drivers).
- Computes comprehensive cost allocations and exports individual result workbooks per Cost Center.

2. Main Screen Controls and Fields

Fiscal Year:
- Enter the budget fiscal year (e.g., 2027). The system generates 12 fiscal periods from April to March and only accepts source files matching this year.
- A fiscal year starts in April and ends in March of the following calendar year.
- Changing the fiscal year updates the application window title and active data context accordingly.

Exchange Rate (USD/VND):
- The exchange rate applied to the current calculation run.
- Default value is extracted from the FORM template. Can be modified before running if business requirements change.

Cost Center (Optional):
- Leave blank to calculate and export all Cost Centers with valid data.
- Select a single code to perform a test run or export for a specific department.

FORM Template File:
- The template Excel file used to construct result workbooks.
- Click "Browse..." to change the template. Path preferences are remembered automatically.

Cost Sources Folder:
- The directory containing all expense and budget allocation Excel files.

Headcount & Time Sources Folder:
- The directory containing departmental staffing and working hour plans.
- Click "Update DB" to scan and ingest source records into the local database.

3. Recommended Workflow

Step 1: Set the correct Fiscal Year.
Step 2: Verify the FORM Template File path.
Step 3: Verify the Cost Sources Folder path.
Step 4: Select the Headcount & Time Sources Folder.
Step 5: Click "Update DB" and inspect the Processing Log.
Step 6: Open "Manual Staffing" to verify headcount/hours and add overrides if necessary.
Step 7: Open "Missing Event Drivers" for custom non-standard business expenses.
Step 8: Select one Cost Center for a trial run (or leave blank for batch processing).
Step 9: Click "RUN CALCULATION".
Step 10: Review the Execution Log and open output workbooks to verify results.

4. Headcount and Working Hours Ingestion

Pre-update Checklist:
- Ensure the selected Fiscal Year matches the input plan files.
- Select the directory containing the plan files for that specific year.

When clicking "Update DB", the system will:
- Identify staffing plan files matching the target fiscal year.
- Extract Cost Center codes and department names against current master records.
- Ingest 12 monthly periods (April through March) for each valid department.
- Record any skipped or erroneous files in the log with detailed rationales.

5. Staffing Verification and Manual Adjustments

Click "Manual Staffing" and select a Cost Center code.

"Headcount & Supplements" tab:
- Expat: Japanese expatriate headcount.
- Staff: Local Vietnamese staff headcount.
- Worker: Local Vietnamese direct labor headcount.
- Male (Dec), Female (Dec): Enter for December when gender-dependent costs apply.
- Total: Automatically calculated as Expat + Staff + Worker.
- Notes: Document reasons for any manual adjustment.

"Fixed Hours" / "Overtime Hours" tabs:
- Displays monthly standard and overtime hours for Expats and Local employees.

Bus Transportation:
- Enter Expat and Local bus rider counts separately.

Important Note:
- The editor only displays data for the currently selected Fiscal Year.
- Always click "Save 12 Months" after entering or modifying staffing figures.

6. Output File Structure and Mapping Rules

When calculations complete, figures from April to March are written into columns F through Q of the FORM template:
- Row 8: Expat standard working hours
- Row 9: Local employee standard working hours
- Row 16: Expat overtime hours
- Row 17: Local employee overtime hours
- Row 24: Expat headcount
- Row 25: Total local headcount (Staff + Worker)

7. Entering Custom and Missing Event Drivers

Use "Missing Event Drivers" for business expenses that cannot be inferred automatically:
- Non-participant gifts for company trips
- Anniversary and milestone celebrations
- Visa, passport, and work permit processing fees

8. Cost Source File Processing Order

Click "Source Order Editor" to review detected source files, adjust execution sequence, or temporarily ignore specific files.

9. Safety Invariants and Best Practices

- Always run a trial calculation on a single Cost Center before executing full batch runs.
- Never substitute data from previous fiscal years to fill missing periods.
- Do not enter unconfirmed estimates; leave fields blank and add audit notes when figures are pending.
- Thoroughly review warnings in the processing log before finalizing releases.
- Open and inspect generated output workbooks before submitting to stakeholders.
""".strip()


def get_user_guide_text(lang: str | None = None) -> str:
    """Return the complete localized user guide text for the requested or current language."""
    code = (lang or get_current_language()).lower()
    if code.startswith("ja"):
        return USER_GUIDE_JA
    if code.startswith("en"):
        return USER_GUIDE_EN
    return USER_GUIDE_VI


def get_user_guide_search_suggestions(lang: str | None = None) -> tuple[str, ...]:
    """Return language-appropriate keyword search suggestions for the guide search bar."""
    code = (lang or get_current_language()).lower()
    if code.startswith("ja"):
        return ("更新", "男女", "ソース", "為替レート", "結果")
    if code.startswith("en"):
        return ("update", "gender", "source", "rate", "result")
    return ("cập nhật", "Nam Nữ", "nguồn", "tỷ giá", "kết quả")

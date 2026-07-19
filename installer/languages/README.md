# Bản dịch tiếng Việt cho Inno Setup

`Vietnamese.isl` là bản dịch cộng đồng được lưu trong repository upstream chính thức
của Inno Setup. File được ghim theo commit để build có thể tái lập và không phụ thuộc
vào nội dung thay đổi trên nhánh `main`.

- Upstream: `jrsoftware/issrc`
- Phân loại upstream: `Files/Languages/Unofficial`
- Commit ghim: `5e6e7b7def7ee1ffcaa017c62589a150a05376a5`
- Source: <https://github.com/jrsoftware/issrc/blob/5e6e7b7def7ee1ffcaa017c62589a150a05376a5/Files/Languages/Unofficial/Vietnamese.isl>
- SHA-256: `1ed7f5580df3a302a6955c72ddbfa8e3c3e24d5ed22ea85f55bad548859b3a19`
- Header tương thích: Inno Setup `6.5.0+`
- Trình biên dịch đã xác minh: Inno Setup `6.7.3`
- Độ đầy đủ lúc ghim: `296/296` khóa duy nhất khớp `Default.isl`; không thiếu khóa.

## Cập nhật an toàn

1. Chỉ lấy từ repository upstream `jrsoftware/issrc`.
2. Ghim một commit cụ thể; không build trực tiếp từ URL nhánh động.
3. So toàn bộ khóa dạng `Key=Value` với `Default.isl` của compiler đang dùng.
4. Không chấp nhận file thiếu khóa vì Inno Setup sẽ dùng nội dung tiếng Anh mặc định.
5. Kiểm tra UTF-8, `LanguageName=Tiếng Việt`, `LanguageID=$042A` và
   `LanguageCodePage=1258` trước khi biên dịch.
6. Cập nhật commit và SHA-256 trong tài liệu này sau khi review bản dịch mới.
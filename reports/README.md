# Thư mục `reports`

## Mục đích

Chứa báo cáo JSON sinh ra khi profiling, làm sạch hoặc chuẩn hóa dataset. Đây là bằng chứng
để kiểm tra số dòng, dữ liệu thiếu, dữ liệu trùng và thay đổi trước/sau xử lý.

## Các loại báo cáo

- `profiling_report.json`: thống kê cấu trúc và chất lượng dữ liệu ban đầu.
- `cleaning_report*.json`: số liệu trước/sau cleaning, số bản ghi bị loại hoặc chuẩn hóa.
- `external_cleaning_*.json`: báo cáo làm sạch bộ dữ liệu kiểm thử độc lập.

Các file JSON phụ thuộc dữ liệu thật, được sinh lại bởi `scripts` hoặc service và không
được commit. Chỉ README này được theo dõi trên GitHub.

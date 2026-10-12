# Tầng 1 – Data

## Chức năng đã triển khai

`DataPreprocessingService` thực hiện:

1. Flatten các field cần thiết từ raw JSON.
2. Chỉ giữ bản ghi có `agent.id` và loại Agent `000`.
3. Chuẩn hóa timestamp nhiều định dạng về UTC.
4. Chuyển `rule_level` và `severity_value` thành kiểu số nullable.
5. Giữ Rule ID và Event ID ở dạng biến định danh, không xem là biến số liên tục.
6. Tạo `date` và `hour` phục vụ phân tích thời gian.
7. Tổng hợp chỉ số cơ bản theo Agent và ngày.

Missing không được tự động điền bằng 0 hoặc chuỗi giả vì mỗi loại event có schema khác nhau.

## Kết quả kiểm tra với database cũ

| Chỉ số | Kết quả |
|---|---:|
| Raw event | 109 |
| Event endpoint hợp lệ | 98 |
| Agent sau làm sạch | 8 |
| Dòng tổng hợp theo Agent/ngày | 14 |
| Thiếu Event ID | 77 |
| Thiếu source IP | 77 |

Kết quả missing cho thấy Event ID và source IP chỉ xuất hiện ở một số loại log. Vì vậy không được xóa toàn bộ dòng chỉ do thiếu hai field này.

Database cũ chỉ được dùng để xác nhận logic. Dataset cuối vẫn cần được thu thập riêng và loại dữ liệu mẫu/test.


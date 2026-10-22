# Dữ liệu gốc `data/raw`

## Mục đích

Chứa bản sao log Wazuh chưa qua xử lý, thường lấy từ
`/var/ossec/logs/alerts/alerts.json` hoặc kết quả truy vấn theo thời gian và mức cảnh báo.

## Dữ liệu được chấp nhận

- JSON theo từng dòng của Wazuh.
- JSON array/object mà bộ đọc streaming hỗ trợ.
- CSV nguồn nếu đã có các trường cần thiết.

## Bước xử lý tiếp theo

`scripts/profile_dataset.py` khảo sát cấu trúc; `scripts/clean_dataset.py` gọi các service
để flatten, kiểm tra, loại trùng, chuẩn hóa rồi ghi dữ liệu sang `data/processed`.

Không commit log thật hoặc thông tin nhạy cảm vào GitHub.


# Xử lý dữ liệu

## 1. Mục đích

Chuyển log Wazuh gốc thành CSV có schema ổn định để EDA và mô hình sử dụng. Quá trình
được thiết kế để đọc file lớn, kiểm toán được số dòng bị loại và không sửa raw data.

## 2. Flow

```text
Raw JSON/JSON Lines
  → JsonStreamReader
  → DataProfilingService
  → DataCleaningService
  → data/processed/wazuh_cleaned.csv
  → EdaService
```

CSV sạch do người dùng chọn có thể được `EdaService` kiểm tra và nạp trực tiếp, không cần
chạy lại bước flatten raw JSON.

## 3. Đọc dữ liệu lớn

`json_stream_reader.py` nhận diện JSON Array hoặc JSON Lines và trả từng dictionary bằng
iterator. Dữ liệu không bị nạp toàn bộ vào RAM. `cleaned_csv_reader.py` đọc CSV sạch theo
batch 20 dòng để bảng giao diện không phải dựng hàng trăm nghìn widget cùng lúc.

## 4. Profiling trước khi làm sạch

`data_profiling_service.py` duyệt dữ liệu và thống kê:

- Tổng dòng, số Agent và khoảng timestamp.
- Missing theo trường và kiểu dữ liệu thực tế.
- Duplicate theo `alert.id`.
- Timestamp hoặc `rule.level` không hợp lệ.

Profiling chỉ đo baseline, không sửa dữ liệu và ghi `cleaning_applied = false`.

Kết quả khảo sát bộ raw 30 ngày từng sử dụng:

| Chỉ số | Kết quả |
|---|---:|
| Tổng bản ghi | 499.978 |
| Số Agent | 11 |
| Alert ID duy nhất | 492.696 |
| Dòng trùng `alert.id` | 7.282 |
| Timestamp/level không hợp lệ | 0 |

Các trường Windows, MITRE, IP và user có thể thiếu theo loại event; không được xóa bản ghi
chỉ vì thiếu các trường tùy chọn này.

## 5. Validation và cleaning

`data_cleaning_service.py` thực hiện:

1. Kiểm tra `id`, `timestamp`, `agent.id`, `rule.id`, `rule.level`.
2. Loại Manager `agent.id=000`, timestamp/level lỗi và alert ID trùng.
3. Giữ bản hợp lệ xuất hiện đầu tiên khi trùng ID.
4. Giữ rỗng trường tùy chọn, không tạo dữ liệu giả.
5. Chuẩn hóa timestamp về UTC ISO 8601 và level về số.
6. Ghi file `.tmp`, chỉ thay file đích khi toàn bộ quá trình hoàn tất.

Điều kiện kiểm toán:

```text
input_rows = output_rows + removed_unique_rows
```

Với bộ raw nêu trên, 499.978 dòng đầu vào tạo 492.696 dòng sạch sau khi loại 7.282 dòng
trùng. Raw JSON không bị ghi đè.

## 6. Schema CSV sạch

Một dòng tương ứng một cảnh báo:

```text
timestamp_utc
agent_name
source_ip
src_ip
dst_user
target_user_name
event_id
rule_id
rule_level
rule_firedtimes
rule_description
```

Service hiện không tạo `agent_risk_index` hoặc `alert_risk_level`.

`data_preprocessing_service.py` cung cấp thêm tiện ích flatten dictionary, chuẩn hóa kiểu và
tổng hợp theo Agent/thời gian. Module không sửa object đầu vào.

## 7. Bảng Agent/ngày

EDA tổng hợp CSV sự kiện thành một dòng cho mỗi Agent/ngày với các trường chính:

```text
agent_name, event_date, total_events, high_level_alerts,
unique_rules, unique_event_ids, unique_source_ips, unique_users,
avg_rule_level, max_rule_level
```

Dòng ngày không có log có thể được thêm với `total_events=0` để biểu đồ liên tục, nhưng
không được dùng huấn luyện mô hình.

## 8. Chạy bằng dòng lệnh

```powershell
python scripts/profile_dataset.py <duong-dan-raw.json>
python scripts/clean_dataset.py <duong-dan-raw.json>
```

Kết quả mặc định gồm CSV sạch trong `data/processed` và báo cáo JSON trong `reports`.
Hai script gọi lại cùng service với giao diện, không tạo quy tắc xử lý riêng.

## 9. Thành phần code

| File | Trách nhiệm |
|---|---|
| `json_stream_reader.py` | Đọc JSON lớn theo streaming |
| `cleaned_csv_reader.py` | Đọc CSV theo batch cho bảng giao diện |
| `data_profiling_service.py` | Đo chất lượng trước cleaning |
| `data_cleaning_service.py` | Validation, dedup, chuẩn hóa và xuất CSV |
| `data_preprocessing_service.py` | Flatten và tổng hợp dùng lại |
| `scripts/profile_dataset.py` | Chạy profiling bằng CLI |
| `scripts/clean_dataset.py` | Chạy cleaning bằng CLI |

CSV và báo cáo sinh từ dữ liệu thật không được commit lên GitHub.


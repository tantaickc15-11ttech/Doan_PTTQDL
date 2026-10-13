# Kết quả Validation và Cleaning

Pipeline đã chạy trên toàn bộ `wazuh_dataset_30days_level7_raw.json`.

## Before/After

| Chỉ số | Trước | Sau |
|---|---:|---:|
| Số bản ghi | 499.978 | 492.696 |
| Duplicate `alert.id` | 7.282 dòng | 0 |
| Số cột dataset phân tích | JSON nested | 20 |
| Dung lượng | 837.885.452 bytes | 117.052.194 bytes |

- Tỷ lệ giữ lại: **98,5435%**.
- Quy tắc duplicate: giữ bản ghi hợp lệ xuất hiện đầu tiên.
- Missing tùy chọn được giữ rỗng, không điền giá trị giả.
- Timestamp được chuẩn hóa về UTC ISO 8601.
- Raw JSON không bị ghi đè.

## Nguyên nhân loại

| Nguyên nhân | Số dòng |
|---|---:|
| Trùng `alert.id` | 7.282 |
| Thiếu trường bắt buộc | 0 |
| Timestamp không hợp lệ | 0 |
| `rule.level` không hợp lệ | 0 |
| Agent `000` | 0 |

## Kiểm toán

```text
499.978 = 492.696 + 7.282
```

Đẳng thức `input_rows = output_rows + removed_unique_rows` hợp lệ. Mỗi dòng bị loại chỉ được tính vào một nguyên nhân.

Dataset sạch cục bộ nằm tại `data/processed/wazuh_cleaned.csv`; báo cáo chi tiết nằm tại `reports/cleaning_report.json`. Hai file sinh từ dữ liệu thật không được commit lên GitHub công khai.

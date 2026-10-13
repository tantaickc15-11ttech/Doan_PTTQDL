# Kết quả profiling raw dataset

Kết quả này được tính trực tiếp từ `wazuh_dataset_30days_level7_raw.json` trước cleaning.

| Chỉ số | Kết quả |
|---|---:|
| Kích thước file | 837.885.452 bytes |
| Tổng bản ghi input | 499.978 |
| Số Agent | 11 |
| Alert ID duy nhất | 492.696 |
| Dòng trùng `alert.id` | 7.282 |
| Timestamp không hợp lệ | 0 |
| `rule.level` không hợp lệ | 0 |
| Thiếu trường bắt buộc | 0 |
| Thời gian sớm nhất UTC | 2026-09-13 07:46:24.233 |
| Thời gian muộn nhất UTC | 2026-10-13 07:46:06.397 |

## Missing của một số trường tùy chọn

| Trường | Số dòng thiếu | Tỷ lệ |
|---|---:|---:|
| `rule.mitre` | 179.541 | 35,9098% |
| `data.win.system.eventID` | 471.612 | 94,3266% |
| `data.win.eventdata.targetUserName` | 489.786 | 97,9615% |
| `data.win.eventdata.ipAddress` | 491.186 | 98,2415% |
| `full_log` | 49.837 | 9,9678% |

Các trường Windows và MITRE là trường tùy chọn theo loại event. Không được xóa bản ghi chỉ vì thiếu các trường này.

Profiling chưa loại 7.282 dòng duplicate và ghi nhận `rows_removed = 0`.

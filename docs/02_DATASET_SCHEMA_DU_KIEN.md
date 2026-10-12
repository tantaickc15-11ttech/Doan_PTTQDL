# Schema dataset dự kiến

## Dataset sự kiện

Một dòng tương ứng một cảnh báo Wazuh.

```text
timestamp
date
hour
agent_id
agent_name
agent_ip
rule_id
rule_level
rule_description
event_id
severity_value
target_user
source_ip
status
decoder
location
```

Không yêu cầu mọi loại log phải có đủ tất cả field. Missing sẽ được xử lý theo ý nghĩa của từng cột.

## Dataset tổng hợp

Một dòng tương ứng một Agent trong một khoảng thời gian.

```text
agent_name
time_bucket
total_events
failure_count
success_count
avg_rule_level
max_rule_level
unique_users
unique_source_ips
unique_event_ids
```

Chỉ thêm chỉ số khi dữ liệu thật chứng minh chỉ số đó có giá trị phân tích.


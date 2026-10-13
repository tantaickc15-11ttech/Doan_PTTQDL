# Đối chiếu yêu cầu và kỹ thuật

| Yêu cầu | Kỹ thuật | Nguồn bài giảng | Trường dữ liệu | Kết quả | Module | Kiểm thử |
|---|---|---|---|---|---|---|
| Đọc JSON lớn | Streaming theo chunk, iterator | CHƯA ĐỐI CHIẾU | Toàn bộ JSON object | Từng dictionary | `json_stream_reader.py` | JSON Array qua nhiều chunk, JSON Lines |
| Đếm dòng và Agent | Count và tập giá trị duy nhất | CHƯA ĐỐI CHIẾU | `agent.id` | Baseline input | `data_profiling_service.py` | Dataset mẫu 3 dòng |
| Đo missing | Đếm `None` hoặc chuỗi rỗng | CHƯA ĐỐI CHIẾU | 19 trường profiling | Bảng missing | `data_profiling_service.py` | Thiếu `agent.id` |
| Phát hiện duplicate | So sánh trên `alert.id` | CHƯA ĐỐI CHIẾU | `id` | Số dòng trùng | `data_profiling_service.py` | Hai dòng cùng ID |
| Kiểm tra timestamp/level | Parse datetime và kiểm tra integer | CHƯA ĐỐI CHIẾU | `timestamp`, `rule.level` | Số dòng sai kiểu | `data_profiling_service.py` | Timestamp và level lỗi |
| Loại duplicate | Tập ID đã gặp, giữ lần đầu | CHƯA ĐỐI CHIẾU | `id` | CSV không trùng ID | `data_cleaning_service.py` | Hai dòng cùng ID, kiểm tra dòng đầu |
| Chuẩn hóa dữ liệu | Parse datetime UTC, chuyển kiểu và flatten | CHƯA ĐỐI CHIẾU | Timestamp và các field nested | CSV 20 cột | `data_cleaning_service.py` | Missing tùy chọn vẫn được giữ |
| Kiểm toán cleaning | Đếm nguyên nhân loại loại trừ nhau | CHƯA ĐỐI CHIẾU | Tất cả bản ghi | Before/After | `data_cleaning_service.py` | `input = output + removed` |

Số trang slide sẽ được bổ sung sau khi người dùng cung cấp bài giảng môn Phân tích và Trực quan dữ liệu.

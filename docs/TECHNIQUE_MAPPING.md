# Đối chiếu yêu cầu và kỹ thuật

| Yêu cầu | Kỹ thuật | Nguồn bài giảng | Trường dữ liệu | Kết quả | Module | Kiểm thử |
|---|---|---|---|---|---|---|
| Đọc JSON lớn | Streaming theo chunk, iterator | CHƯA ĐỐI CHIẾU | Toàn bộ JSON object | Từng dictionary | `json_stream_reader.py` | JSON Array qua nhiều chunk, JSON Lines |
| Đếm dòng và Agent | Count và tập giá trị duy nhất | CHƯA ĐỐI CHIẾU | `agent.id` | Baseline input | `data_profiling_service.py` | Dataset mẫu 3 dòng |
| Đo missing | Đếm `None` hoặc chuỗi rỗng | CHƯA ĐỐI CHIẾU | 19 trường profiling | Bảng missing | `data_profiling_service.py` | Thiếu `agent.id` |
| Phát hiện duplicate | So sánh trên `alert.id` | CHƯA ĐỐI CHIẾU | `id` | Số dòng trùng | `data_profiling_service.py` | Hai dòng cùng ID |
| Kiểm tra timestamp/level | Parse datetime và kiểm tra integer | CHƯA ĐỐI CHIẾU | `timestamp`, `rule.level` | Số dòng sai kiểu | `data_profiling_service.py` | Timestamp và level lỗi |
| Loại duplicate | Tập ID đã gặp, giữ lần đầu | CHƯA ĐỐI CHIẾU | `id` | CSV không trùng ID | `data_cleaning_service.py` | Hai dòng cùng ID, kiểm tra dòng đầu |
| Chuẩn hóa dữ liệu | Parse datetime UTC, chuyển kiểu và flatten | CHƯA ĐỐI CHIẾU | Timestamp và các field nested | CSV sạch 11 cột | `data_cleaning_service.py` | Missing tùy chọn vẫn được giữ |
| Kiểm toán cleaning | Đếm nguyên nhân loại loại trừ nhau | CHƯA ĐỐI CHIẾU | Tất cả bản ghi | Before/After | `data_cleaning_service.py` | `input = output + removed` |
| Lọc EDA | Boolean filter theo Agent, Alert Level và timestamp | Bài EDA | `agent_name`, `rule_level`, `timestamp_utc` | Agent + Level + 7/14/30 ngày, một ngày, khoảng ngày | `eda_service.py` | Neo theo timestamp mới nhất |
| Thống kê mô tả | `groupby`, `size`, `nunique`, mean, median | CHƯA ĐỐI CHIẾU | Alert và Agent/ngày | KPI và bảng | `eda_service.py` | Test count/IP/user |
| Xu hướng thời gian | Group theo ngày | CHƯA ĐỐI CHIẾU | `timestamp_utc` | Line chart | `eda_panel.py` | Đối chiếu tổng alert |
| Top-N danh mục | `value_counts`, `groupby`, sắp xếp | CHƯA ĐỐI CHIẾU | Agent, Rule, Event ID | Bar ngang | `eda_service.py` | Ranking giảm dần |
| Outlier | Q1, Q3, IQR, 1.5 x IQR | CHƯA ĐỐI CHIẾU | Chỉ số Agent/ngày | Boxplot + bảng ngưỡng | `outlier_service.py` | Test giá trị 100 là outlier |
| Quan hệ biến số | Pearson correlation | CHƯA ĐỐI CHIẾU | Các chỉ số Agent/ngày | Heatmap, scatter, bảng | `relationship_service.py` | Test quan hệ tuyến tính r=1 |
| So sánh theo Agent | One-way ANOVA | Bài ANOVA | `agent_name`, `total_events` | F và p-value | `relationship_service.py` | Test đủ nhóm và kết luận p-value |
| Chuyển biến phân loại | One-Hot Encoding, bỏ một nhóm tham chiếu | Bài xử lý dữ liệu | `agent_name` | Các cột số 0/1 | `model_service.py` | Pipeline fit/predict cùng quy tắc |
| Điền khuyết | Trung vị cho biến số, mode cho Agent | Bài xử lý dữ liệu | Biến đầu vào mô hình | Dữ liệu số hoàn chỉnh | `model_service.py` | Pipeline học giá trị từ tập train |
| HQTT đa biến | `LinearRegression` trong Pipeline | Bài hồi quy | 7 biến số + Agent | Dự đoán `total_events` | `model_service.py` | MSE và R² |
| HQĐT | Chuẩn hóa + `PolynomialFeatures` + hồi quy | Bài hồi quy đa thức | 7 biến số + Agent | Dự đoán theo bậc | `model_service.py` | So sánh MSE bậc 1–10 |
| Đánh giá holdout | Train/Test Split 80/20 | Bài đánh giá mô hình | Bảng Agent/ngày có log | MSE và R² train/test | `model_service.py` | Test không được fit |
| Kiểm chứng chéo | K-Fold có shuffle | Bài đánh giá mô hình | Bảng Agent/ngày có log | MSE/R² trung bình | `model_service.py` | Pipeline mới ở từng fold |
| Kiểm thử độc lập | Predict-only trên bộ dữ liệu mới | Phần mở rộng đồ án | CSV/JSON mới | MSE và R² ngoài mẫu | `external_validation_panel.py` | Không gọi fit trên dữ liệu mới |

Số trang slide sẽ được bổ sung sau khi người dùng cung cấp bài giảng môn Phân tích và Trực quan dữ liệu.

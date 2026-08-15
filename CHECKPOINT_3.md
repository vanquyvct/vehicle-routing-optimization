# Checkpoint 3 - Đánh giá thuật toán và quản lý dữ liệu

## Mục tiêu

Bổ sung khả năng đánh giá định lượng và thao tác với bộ dữ liệu thử nghiệm.

## Chức năng mới

- Tạo baseline bằng heuristic Greedy nearest-neighbor có kiểm tra sức chứa xe.
- So sánh CVRP/OR-Tools với baseline trên cùng ma trận khoảng cách đường bộ.
- Hiển thị:
  - tổng quãng đường baseline;
  - tổng quãng đường CVRP;
  - quãng đường tiết kiệm;
  - tỷ lệ cải thiện (%);
  - tuyến của baseline.
- Lưu bộ dữ liệu hiện tại trong Local Storage của trình duyệt.
- Tải lại bộ dữ liệu đã lưu.
- Xuất dữ liệu thành file JSON.
- Nhập bộ dữ liệu từ file JSON.

## Ý nghĩa đánh giá

Baseline là một phương pháp tham lam đơn giản: tại mỗi bước, xe chọn điểm chưa giao gần nhất mà vẫn còn đủ tải. Kết quả này được dùng làm mốc so sánh chứ không được coi là nghiệm tối ưu.

Công thức tỷ lệ cải thiện:

improvement(%) = (distance_baseline - distance_CVRP) / distance_baseline × 100

Giá trị dương nghĩa là CVRP tạo tổng quãng đường ngắn hơn baseline.

# Kiểm thử và thực nghiệm

## 1. Kiểm thử validation

Ứng dụng có bộ kiểm thử nhằm đảm bảo backend phát hiện dữ liệu không hợp lệ trước khi giải bài toán.

| STT | Trường hợp | Kết quả mong đợi |
|---:|---|---|
| 1 | Không có phương tiện | Từ chối dữ liệu |
| 2 | Trùng mã đơn hàng | Từ chối dữ liệu |
| 3 | Một đơn vượt sức chứa mọi xe | Từ chối dữ liệu |
| 4 | Tổng nhu cầu vượt tổng sức chứa | Từ chối dữ liệu |
| 5 | Tọa độ không hợp lệ | Từ chối dữ liệu |

Kết quả hiện tại: 5/5 test đạt.

## 2. Phương pháp baseline

Greedy nearest-neighbor được dùng làm phương pháp cơ sở.

Nguyên tắc:

1. Xét phương tiện.
2. Từ vị trí hiện tại, tìm điểm chưa giao gần nhất.
3. Chỉ nhận điểm nếu tải còn lại của xe đáp ứng được demand.
4. Lặp lại cho tới khi xe không nhận thêm được điểm.
5. Chuyển sang phương tiện tiếp theo.

Baseline đơn giản và nhanh, nhưng quyết định cục bộ nên không đảm bảo tối ưu toàn cục.

## 3. Benchmark

Ba bộ dữ liệu:

| Bộ | Điểm giao | Xe |
|---|---:|---:|
| B10 | 10 | 2 |
| B20 | 20 | 4 |
| B30 | 30 | 6 |

Các tọa độ và demand được cố định trong mã nguồn để thí nghiệm có thể chạy lại.

## 4. Kết quả

| Quy mô | Greedy | CVRP | Giảm |
|---|---:|---:|---:|
| 10 điểm | 44.19 km | 33.11 km | 25.08% |
| 20 điểm | 100.58 km | 70.40 km | 30.00% |
| 30 điểm | 153.01 km | 120.41 km | 21.30% |

Mức cải thiện trung bình:

```text
(25.08 + 30.00 + 21.30) / 3
= 25.46%
```

## 5. Chỉ số đánh giá

### Tổng quãng đường

Là tổng chiều dài tuyến của toàn bộ phương tiện.

### Tỷ lệ cải thiện

```text
Improvement =
(Baseline - CVRP) / Baseline × 100%
```

### Runtime

Thời gian backend cần để chạy benchmark của từng kịch bản.

Runtime có thể chịu ảnh hưởng bởi:

- tốc độ máy;
- kết nối Internet;
- thời gian phản hồi OSRM;
- trạng thái public OSRM server.

Do đó runtime benchmark không được xem là đặc tính tuyệt đối của thuật toán.

## 6. Ý nghĩa kết quả

Trong các bộ dữ liệu hiện tại, CVRP/OR-Tools đều tạo tổng quãng đường thấp hơn baseline.

Kết quả cho thấy việc xét bài toán tối ưu tổng thể có khả năng tạo phương án tốt hơn chiến lược lựa chọn điểm gần nhất theo từng bước.

Tuy nhiên ba bộ benchmark vẫn có quy mô nhỏ. Kết quả hiện tại chỉ dùng để đánh giá phiên bản thử nghiệm, chưa đủ để kết luận hiệu quả trên hệ thống logistics quy mô lớn.

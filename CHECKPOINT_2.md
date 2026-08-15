# Checkpoint 2

Checkpoint này nâng giao diện từ nhập JSON thô thành giao diện điều phối trực tiếp.

## Thay đổi

- Leaflet 1.9.4 + OpenStreetMap
- Hiển thị kho và điểm giao trên bản đồ
- Chọn vị trí kho bằng cách click bản đồ
- Thêm điểm giao trực tiếp bằng cách click bản đồ
- Thêm/xóa phương tiện
- Nhập sức chứa từng xe
- Thêm/xóa điểm giao và nhu cầu
- Gửi dữ liệu từ giao diện tới Flask API
- OR-Tools giải CVRP
- Vẽ tuyến kết quả trên bản đồ
- Hiển thị tổng quãng đường, tải và số đơn từng xe
- Kiểm tra dữ liệu đầu vào ở frontend và backend

## Lưu ý

Tuyến ở checkpoint này là đường nối giữa các tọa độ theo thứ tự CVRP. Chi phí tối ưu vẫn sử dụng khoảng cách Haversine, chưa phải quãng đường lái xe thực tế.

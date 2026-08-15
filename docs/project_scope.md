# Phạm vi và mô hình bài toán

## 1. Bài toán

Hệ thống giải một phiên bản của Capacitated Vehicle Routing Problem (CVRP).

Đầu vào:

- một kho;
- tập phương tiện;
- sức chứa của từng phương tiện;
- tập điểm giao;
- nhu cầu hàng hóa của từng điểm;
- ma trận khoảng cách giữa các vị trí.

Đầu ra:

- phương tiện phục vụ từng điểm;
- thứ tự điểm trên mỗi tuyến;
- tổng quãng đường;
- tải của từng phương tiện.

## 2. Mục tiêu

Giảm tổng chi phí di chuyển:

```text
Minimize: tổng khoảng cách của toàn bộ tuyến xe
```

## 3. Ràng buộc

### Mỗi điểm giao được phục vụ đúng một lần

Một đơn hàng không được giao bởi nhiều xe và cũng không được bỏ sót.

### Giới hạn sức chứa

```text
Tổng demand trên tuyến xe <= capacity của xe
```

### Kho

Mỗi tuyến bắt đầu và kết thúc tại kho.

## 4. Phạm vi sản phẩm

Phiên bản hiện tại tập trung vào:

- một kho;
- nhiều phương tiện;
- nhiều điểm giao;
- giới hạn sức chứa;
- khoảng cách đường bộ;
- trực quan hóa bản đồ;
- benchmark cơ bản.

## 5. Ngoài phạm vi

Chưa triển khai:

- nhiều kho;
- cửa sổ thời gian giao hàng;
- giao thông thời gian thực;
- GPS phương tiện;
- tài khoản tài xế;
- thông báo khách hàng;
- thanh toán;
- dự báo bằng Machine Learning.

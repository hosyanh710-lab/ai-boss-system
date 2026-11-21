# thue-dn — Tải hóa đơn & kiểm tra nhà cung cấp

Công cụ chạy trên máy Windows (giai đoạn 1) để:

- Tải hóa đơn **mua vào**, **bán ra** từ cổng hoadondientu.gdt.gov.vn cho nhiều doanh nghiệp; tự tách hóa đơn **điều chỉnh / thay thế / bị hủy**.
- **Kiểm tra người bán** trên hóa đơn đầu vào; cảnh báo **rủi ro CAO** khi hóa đơn lập sau ngày người bán ngừng / chấm dứt hoạt động.
- **Kiểm tra đối tác trước khi ký hợp đồng** (chỉ cần MST): kết luận *Có thể giao dịch / Cần xem thêm / Không nên giao dịch*, lưu lịch sử làm bằng chứng, nhắc tra lại nhà cung cấp đang giao dịch.
- Xuất **bảng kê Excel** (3 sheet: Mua vào, Bán ra, Điều chỉnh - thay thế) và **XML** dạng .zip. Sheet *Điều chỉnh - thay thế* ghi mỗi hóa đơn điều chỉnh / thay thế trên một hàng, **cùng hàng với hóa đơn gốc** mà nó điều chỉnh.

Kế hoạch: https://claude.ai/artifact/EXTBVqygPxvgwozX54Ze9e
Giao diện mẫu: https://claude.ai/artifact/G5HVipgaXqbfMmqopAm14q

## Chạy trên máy Windows

1. Cài **Python** tại python.org (tick ô *Add Python to PATH*) và **Git for Windows** tại git-scm.com.
2. Tải code về:
   ```
   git clone https://github.com/hosyanh710-lab/ai-boss-system.git
   cd ai-boss-system
   git checkout claude/vibrant-franklin-nweumy
   cd thue-dn
   ```
3. Bấm đúp **`run.bat`**. Lần đầu sẽ tự cài thư viện, sau đó trình duyệt mở `http://127.0.0.1:5000`.

## Cách dùng

1. **Doanh nghiệp**: thêm tên, MST, mật khẩu cổng thuế (mật khẩu mã hóa, chỉ lưu trong thư mục `data/` trên máy).
2. Tick các doanh nghiệp, chọn khoảng ngày, loại hóa đơn → **Tải hóa đơn**.
3. **Nhập captcha** lần lượt cho từng DN. DN đã đăng nhập trong phiên thì không phải nhập lại.
4. **Kết quả**: lọc, xuất Excel, tải XML.
5. **Nhà cung cấp**: tra trạng thái từng MST người bán, lưu lại để lần sau không tra lại.
6. **Kiểm tra đối tác**: nhập MST → mở các trang tra cứu → điền trạng thái, ngày thành lập, ngành nghề → xem phiếu đánh giá, tải phiếu Excel. Nhập thêm danh sách DN rủi ro cao / nợ thuế do cơ quan thuế công bố để công cụ tự đối chiếu.

### Quy tắc đánh giá đối tác

| Kết luận | Khi nào |
|---|---|
| Không nên giao dịch | MST tạm ngừng, ngừng hoạt động, chấm dứt, không hoạt động tại địa chỉ; hoặc có trong danh sách rủi ro / nợ thuế |
| Cần xem thêm | Thành lập dưới 12 tháng; ngành nghề không khớp hoặc chưa đối chiếu; thông tin lấy từ trang tổng hợp |
| Chưa đủ thông tin | Chưa tra trạng thái MST |
| Có thể giao dịch | Không vướng điều nào ở trên |

Nhà cung cấp có hóa đơn mua vào mà chưa tra, hoặc tra quá 30 ngày, được liệt kê để tra lại. Các mốc 12 tháng và 30 ngày sửa trong `thuedn/rules.py`.

### Sheet "Bán ra"

Mỗi hàng là một hóa đơn bán ra. Hóa đơn bị điều chỉnh / bị thay thế có **hóa đơn điều chỉnh / thay thế nằm cùng hàng** (các cột nền xanh): ký hiệu, số, ngày, nội dung điều chỉnh, tiền chưa thuế, tiền thuế, tổng thanh toán. Sau đó là **Tổng sau điều chỉnh (tạm tính)**, cột **Đánh giá** ở cuối cùng.

- Hóa đơn bị điều chỉnh nhiều lần: mỗi lần một hàng, từ hàng thứ 2 để trống số tiền hóa đơn gốc để cộng cột không bị trùng.
- Hóa đơn điều chỉnh / thay thế không lặp lại thành hàng riêng.
- Nội dung điều chỉnh: loại (điều chỉnh tăng / giảm / thay thế) + ghi chú lý do hoặc tên hàng hóa đọc từ XML (tick **Tải kèm XML**).
- Đánh giá: Bình thường · Đã điều chỉnh (lần 1, 2…) · Đã thay thế · Hóa đơn đã hủy · các cảnh báo (tô vàng): chưa có HĐ điều chỉnh, HĐ gốc chưa tải, chưa có thông tin HĐ gốc; ghi chú thêm khi HĐ gốc hoặc HĐ điều chỉnh thuộc kỳ khác.

### Sheet "Điều chỉnh - thay thế"

Mỗi hàng là một hóa đơn điều chỉnh hoặc thay thế. Cột chia 3 nhóm, từ trái sang phải: thông tin chung (DN, đối tác, loại, lần điều chỉnh) · hóa đơn gốc (bị điều chỉnh / bị thay thế) · hóa đơn điều chỉnh / thay thế, cuối cùng là tổng sau điều chỉnh (tạm tính) và ghi chú.

- Nhiều lần điều chỉnh cho cùng một hóa đơn gốc nằm liền nhau, đánh số Lần 1, 2…; tổng sau điều chỉnh cộng dồn.
- Hóa đơn gốc được tìm trong **toàn bộ dữ liệu đã tải**, kể cả khác kỳ đang lọc.
- Tô vàng khi: chưa có thông tin hóa đơn gốc, hóa đơn gốc chưa được tải, hoặc hóa đơn bị điều chỉnh mà chưa thấy hóa đơn điều chỉnh.
- Thông tin hóa đơn gốc lấy từ danh sách cổng thuế; nếu tick **Tải kèm XML** thì lấy từ khối `TTHDLQuan` trong XML (chính xác hơn).

## Tình trạng

| Phần | Trạng thái |
|---|---|
| Danh sách DN, mã hóa mật khẩu | Xong, đã kiểm thử |
| Chia khoảng ngày theo tháng, phân loại tính chất HĐ | Xong, đã kiểm thử |
| Xuất Excel, gộp nhiều DN, tô đỏ rủi ro cao | Xong, đã kiểm thử |
| Kết nối cổng hoadondientu (captcha, đăng nhập, tra cứu, XML) | **Đã viết, chưa chạy với cổng thật** — cần thử trên máy anh |
| Kiểm tra đối tác, phiếu đánh giá, lịch sử, nhắc tra lại, danh sách rủi ro | Xong, đã kiểm thử |
| Nối HĐ điều chỉnh / thay thế với HĐ gốc (Excel, trang Kết quả, đọc XML) | Xong, đã kiểm thử với dữ liệu giả. **Cần kiểm tra trên máy anh**: tên trường HĐ gốc trong danh sách cổng thuế, và dấu âm / dương của số tiền HĐ điều chỉnh giảm |
| Tự động lấy thông tin từ trang cơ quan thuế / cổng đăng ký DN | Chưa làm — hiện mở link tra rồi điền bằng tay; cần thử trên máy anh vì các trang này có captcha |

Địa chỉ kết nối cổng thuế nằm trong `thuedn/portal.py`. Nếu cổng đổi, chỉ cần sửa file đó.

## Kiểm thử (không cần mạng)

```
.venv\Scripts\python -m pytest tests
```

## Lưu ý

- Thư mục `data/` chứa mật khẩu đã mã hóa và khóa giải mã: **không gửi cho ai, không đưa lên GitHub** (đã chặn bằng `.gitignore`).
- Kết quả kiểm tra nhà cung cấp chỉ để tham khảo; trường hợp rủi ro cao nên tra lại trên trang cơ quan thuế trước khi kê khai khấu trừ.

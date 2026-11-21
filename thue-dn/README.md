# thue-dn — Tải hóa đơn & kiểm tra nhà cung cấp

Công cụ chạy trên máy Windows (giai đoạn 1) để:

- Tải hóa đơn **mua vào**, **bán ra** từ cổng hoadondientu.gdt.gov.vn cho nhiều doanh nghiệp; tự tách hóa đơn **điều chỉnh / thay thế / bị hủy**.
- **Kiểm tra người bán** trên hóa đơn đầu vào; cảnh báo **rủi ro CAO** khi hóa đơn lập sau ngày người bán ngừng / chấm dứt hoạt động.
- Xuất **bảng kê Excel** (3 sheet: Mua vào, Bán ra, Điều chỉnh - thay thế) và **XML** dạng .zip.

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

## Tình trạng

| Phần | Trạng thái |
|---|---|
| Danh sách DN, mã hóa mật khẩu | Xong, đã kiểm thử |
| Chia khoảng ngày theo tháng, phân loại tính chất HĐ | Xong, đã kiểm thử |
| Xuất Excel, gộp nhiều DN, tô đỏ rủi ro cao | Xong, đã kiểm thử |
| Kết nối cổng hoadondientu (captcha, đăng nhập, tra cứu, XML) | **Đã viết, chưa chạy với cổng thật** — cần thử trên máy anh |
| Tra cứu NCC tự động trên trang cơ quan thuế | Chưa làm — hiện bấm link tra rồi chọn trạng thái bằng tay |

Địa chỉ kết nối cổng thuế nằm trong `thuedn/portal.py`. Nếu cổng đổi, chỉ cần sửa file đó.

## Kiểm thử (không cần mạng)

```
.venv\Scripts\python -m pytest tests
```

## Lưu ý

- Thư mục `data/` chứa mật khẩu đã mã hóa và khóa giải mã: **không gửi cho ai, không đưa lên GitHub** (đã chặn bằng `.gitignore`).
- Kết quả kiểm tra nhà cung cấp chỉ để tham khảo; trường hợp rủi ro cao nên tra lại trên trang cơ quan thuế trước khi kê khai khấu trừ.

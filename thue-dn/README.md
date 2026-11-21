# thue-dn — Tải hóa đơn & kiểm tra nhà cung cấp

Công cụ chạy trên máy Windows (giai đoạn 1) để:

- Tải hóa đơn **mua vào**, **bán ra** từ cổng hoadondientu.gdt.gov.vn cho nhiều doanh nghiệp; tự tách hóa đơn **điều chỉnh / thay thế / bị hủy**.
- **Kiểm tra người bán** trên hóa đơn đầu vào; cảnh báo **rủi ro CAO** khi hóa đơn lập sau ngày người bán ngừng / chấm dứt hoạt động.
- **Kiểm tra đối tác trước khi ký hợp đồng** (chỉ cần MST): kết luận *Có thể giao dịch / Cần xem thêm / Không nên giao dịch*, lưu lịch sử làm bằng chứng, nhắc tra lại nhà cung cấp đang giao dịch.
- Xuất **bảng kê Excel** (6 sheet: Mua vào, Bán ra, Điều chỉnh - thay thế, Chi tiết bán ra, Chi tiết mua vào, Tổng hợp hạch toán) và **XML** dạng .zip. Sheet *Điều chỉnh - thay thế* ghi mỗi hóa đơn điều chỉnh / thay thế trên một hàng, **cùng hàng với hóa đơn gốc** mà nó điều chỉnh.

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

## Dùng cho nhiều công ty (ví dụ 10 công ty)

Một ứng dụng quản lý tất cả các công ty, **không cần cài nhiều bản**:

1. Trang **Doanh nghiệp**: thêm từng công ty (tên, MST, mật khẩu cổng thuế).
2. Tick **chọn tất cả** → chọn khoảng ngày → **Tải hóa đơn** → nhập captcha lần lượt cho từng công ty (mỗi công ty một lần trong phiên).
3. Trang **Kết quả**: chọn ô **Doanh nghiệp** để xem từng công ty hoặc tất cả.
   - **Xuất Excel**: một file gộp các công ty đang chọn (mỗi sheet có cột Doanh nghiệp).
   - **Excel từng DN (.zip)**: mỗi công ty một file Excel riêng, tên file theo MST và tên công ty.
4. Phân loại hàng hóa, kiểm tra đối tác, danh sách rủi ro dùng chung cho tất cả các công ty.

## Các bước test lần đầu trên máy anh (làm với 1 công ty trước)

1. Chạy `run.bat`, thêm **1 công ty**.
2. Tải hóa đơn **1 tháng**, tick **Tải kèm XML**. Nếu lỗi ở bước captcha / đăng nhập / tải: chụp màn hình gửi Claude sửa `thuedn/portal.py`.
3. Mở Excel, kiểm tra:
   - Số hóa đơn mua vào / bán ra khớp với cổng thuế.
   - Một hóa đơn **điều chỉnh giảm** thật: số tiền trong XML là **âm hay dương** (ảnh hưởng cột "sau điều chỉnh" và "Điều chỉnh tăng / giảm").
   - Hóa đơn điều chỉnh có ghép đúng hóa đơn gốc không.
   - Sheet chi tiết hàng hóa có đủ mã hàng, số lượng, đơn giá.
4. Ổn rồi mới thêm 9 công ty còn lại.

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

### Sheet "Mua vào" và "Bán ra"

Hai sheet cùng cách xếp. Mỗi hàng là một hóa đơn. Hóa đơn bị điều chỉnh / bị thay thế có **hóa đơn điều chỉnh / thay thế nằm cùng hàng** (các cột nền xanh): ký hiệu, số, ngày, nội dung điều chỉnh, tiền chưa thuế, tiền thuế, tổng thanh toán. Sau đó là **Tổng sau điều chỉnh (tạm tính)**, cột **Đánh giá** ở cuối cùng.

- Hóa đơn bị điều chỉnh nhiều lần: mỗi lần một hàng, từ hàng thứ 2 để trống số tiền hóa đơn gốc để cộng cột không bị trùng.
- Hóa đơn điều chỉnh / thay thế không lặp lại thành hàng riêng.
- Nội dung điều chỉnh: loại (điều chỉnh tăng / giảm / thay thế) + ghi chú lý do hoặc tên hàng hóa đọc từ XML (tick **Tải kèm XML**).
- Sheet Mua vào có thêm **Trạng thái người bán** và **Mức rủi ro** ngay trước cột Đánh giá; rủi ro CAO (tô đỏ) khi HĐ gốc hoặc HĐ điều chỉnh / thay thế lập sau ngày người bán ngừng hoạt động.
- Đánh giá: Bình thường · Đã điều chỉnh (lần 1, 2…) · Đã thay thế · Hóa đơn đã hủy · các cảnh báo (tô vàng): chưa có HĐ điều chỉnh, HĐ gốc chưa tải, chưa có thông tin HĐ gốc; ghi chú thêm khi HĐ gốc hoặc HĐ điều chỉnh thuộc kỳ khác.

### Sheet "Chi tiết bán ra" và "Chi tiết mua vào"

Mỗi hàng là **một dòng hàng hóa / dịch vụ của một hóa đơn**: thông tin hóa đơn (ngày, ký hiệu, số, đối tác, tính chất, HĐ gốc nếu là HĐ điều chỉnh / thay thế) rồi STT dòng, **mã hàng**, tên hàng, ĐVT, số lượng, đơn giá, chiết khấu, thành tiền, thuế suất, tiền thuế (tính theo thuế suất), tính chất dòng (hàng hóa / khuyến mại / chiết khấu / ghi chú). Có sẵn bộ lọc trên dòng tiêu đề.

- Hóa đơn nhiều mặt hàng: mỗi mặt hàng một hàng, thông tin hóa đơn lặp lại trên từng hàng, cột STT dòng giữ thứ tự trên hóa đơn.
- Dòng của HĐ điều chỉnh / thay thế nằm **ngay dưới** dòng của HĐ gốc (HĐ gốc thuộc kỳ khác vẫn được hiện để đối chiếu).
- Cột **Tính vào tổng**: "Không" (tô xám) cho HĐ bị thay thế, bị hủy, HĐ thuộc kỳ khác; lọc "Có" rồi cộng là ra số đúng của kỳ.
- Cột **SL / Thành tiền sau điều chỉnh** trên dòng HĐ gốc: ghép dòng HĐ điều chỉnh với dòng HĐ gốc theo mã hàng (không có mã thì theo tên). Dòng không ghép được, hoặc mặt hàng có nhiều dòng trên HĐ gốc, tô vàng để ghép tay.
- Chi tiết đọc từ file XML hóa đơn (khối `DSHHDVu`), nên cần tick **Tải kèm XML** (mặc định đã tick).
- Hóa đơn chưa có XML vẫn có một hàng, tô vàng, ghi "Chưa có chi tiết hàng hóa".
- XML không ghi tiền thuế theo từng dòng, nên tiền thuế dòng = thành tiền × thuế suất (có thể lệch vài đồng do làm tròn so với tổng thuế trên hóa đơn).

### Sheet "Tổng hợp hạch toán" và trang Phân loại hàng hóa

- **Phần 1 – Tổng hợp theo loại**: mỗi doanh nghiệp × chiều × loại (Hàng hóa 156, Nguyên vật liệu 152, Công cụ dụng cụ 153, Tài sản cố định 211, Chi phí QLDN 642, Chi phí bán hàng 641, Chi phí SXC 627, Doanh thu bán hàng 5111 / thành phẩm 5112 / dịch vụ 5113, Chiết khấu…): số mặt hàng, thành tiền, tiền thuế, tổng. Có dòng báo số hóa đơn chưa có chi tiết hàng hóa để đối chiếu tổng.
- **Phần 2 – Chi tiết theo mã hàng**: mỗi mặt hàng một dòng: phân loại, TK, người bán, mã hàng, tên, ĐVT, số HĐ, tổng số lượng, đơn giá bình quân, thành tiền, tiền thuế, và đã xác nhận phân loại hay mới là gợi ý (tô vàng).
- Không tính hóa đơn bị thay thế, bị hủy; hóa đơn điều chỉnh cộng theo số tiền ghi trên hóa đơn.
- Phân loại tự gợi ý theo tên hàng và ĐVT (phí, cước, thuê, dịch vụ, tháng, chuyến… → chi phí / doanh thu dịch vụ). Vào trang **Phân loại hàng hóa** để chọn lại và sửa tài khoản; lựa chọn được ghi nhớ cho các kỳ sau. Mua vào nhận diện theo người bán + mã hàng.
- Tài khoản theo hệ thống TT200 / TT133 phổ biến, **chỉ là gợi ý**; kế toán quyết định cuối cùng.

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
| Tổng hợp hạch toán theo loại và mã hàng, trang Phân loại hàng hóa | Xong, đã kiểm thử |
| Chi tiết hàng hóa bán ra / mua vào theo mã hàng (đọc XML) | Xong, đã kiểm thử với XML mẫu. **Cần kiểm tra trên máy anh** với XML thật |
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

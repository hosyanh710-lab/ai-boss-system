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

## Tài khoản và phân quyền (3 cấp)

Lần đầu chạy, công cụ yêu cầu **tạo tài khoản Admin đầu tiên**. Sau đó mọi người phải **đăng nhập** mới dùng được.

| Chức năng | Admin | Quản trị | Người sử dụng |
|---|:-:|:-:|:-:|
| Tải hóa đơn, xem kết quả, xuất Excel / file MISA, đẩy Drive | ✓ | ✓ | ✓ |
| Kiểm tra đối tác, phân loại hàng hóa, cập nhật trạng thái nhà cung cấp | ✓ | ✓ | ✓ |
| Thêm / sửa / xóa doanh nghiệp, kết nối Google Drive, Cài đặt, nhập danh sách rủi ro | ✓ | ✓ | ✗ |
| Tạo / sửa / khóa / đặt lại mật khẩu / xóa tài khoản Quản trị, Người sử dụng | ✓ | ✓ | ✗ |
| Tạo, sửa, khóa, xóa tài khoản **Admin**; nâng ai đó lên Admin | ✓ | ✗ | ✗ |

- Luôn còn ít nhất một Admin đang hoạt động; không ai tự sửa vai trò, khóa hoặc xóa tài khoản của chính mình.
- Mật khẩu tối thiểu 8 ký tự, có chữ và số, lưu dạng băm (không lưu mật khẩu gốc).
- Nhập sai mật khẩu 5 lần: tạm khóa đăng nhập 15 phút.
- Quên mật khẩu: Admin / Quản trị đặt lại ở trang **Tài khoản**; mỗi người tự đổi ở **Đổi mật khẩu**.
- Tạo tài khoản ngay trên máy (không cần trình duyệt; mật khẩu hỏi trực tiếp, không hiện ra màn hình):
  ```
  .venv\Scripts\python tao_tai_khoan.py <email> admin "Họ tên"
  .venv\Scripts\python tao_tai_khoan.py <email> quan_tri "Họ tên"
  ```
  Chạy lại với email đã có để đổi vai trò, mở khóa, đặt lại mật khẩu (Enter để giữ mật khẩu cũ).
- Quyền được kiểm tra ở máy chủ cho từng trang, không chỉ ẩn nút.

## Dùng cho nhiều công ty (ví dụ 10 công ty)

Một ứng dụng quản lý tất cả các công ty, **không cần cài nhiều bản**:

1. Trang **Doanh nghiệp**: thêm từng công ty (tên, MST, mật khẩu cổng thuế).
2. Tick **chọn tất cả** → chọn khoảng ngày → **Tải hóa đơn** → nhập captcha lần lượt cho từng công ty (mỗi công ty một lần trong phiên).
3. Trang **Kết quả**: chọn ô **Doanh nghiệp** để xem từng công ty hoặc tất cả.
   - **Xuất Excel**: một file gộp các công ty đang chọn (mỗi sheet có cột Doanh nghiệp).
   - **Excel từng DN (.zip)**: mỗi công ty một file Excel riêng, tên file theo MST và tên công ty.
4. Phân loại hàng hóa, kiểm tra đối tác, danh sách rủi ro dùng chung cho tất cả các công ty.

## File nhập MISA (không phải hạch toán từng hóa đơn)

Trang **Kết quả** → nút **File nhập MISA** (chọn nhiều công ty thì ra .zip, mỗi công ty một file vì MISA nhập theo từng công ty). File cũng được đẩy lên Google Drive cùng bảng kê.

- Sheet **Mua hàng** / **Bán hàng**: mỗi dòng hàng hóa là một dòng chứng từ, các dòng cùng hóa đơn chung **Số chứng từ** (MV-/BR-<ký hiệu>-<số>), đã điền sẵn: ngày hạch toán, nhà cung cấp / khách hàng (mã = MST), diễn giải, số hóa đơn, mã hàng, kho, **TK Nợ / TK Có / TK thuế**, số lượng, đơn giá, thành tiền, thuế suất, tiền thuế.
  - Mua vào: Nợ TK theo phân loại (156, 152, 153, 211, 6421, 6422, 154…) / Có 331; thuế 1331 (TSCĐ 1332).
  - Bán ra: Nợ 131 / Có TK doanh thu (5111, 5112, 5113); thuế 33311.
- Hóa đơn bị thay thế, bị hủy: **không nhập** (nhập hóa đơn thay thế). Hóa đơn điều chỉnh nhập thành chứng từ riêng, diễn giải ghi rõ điều chỉnh cho hóa đơn nào.
- Sheet **Kiểm tra trước khi nhập**: các dòng cần xem (tô vàng trong sheet chứng từ): phân loại chưa xác nhận, chưa có TK, thiếu mã hàng, hóa đơn chưa có chi tiết hàng hóa; và các hóa đơn không nhập kèm lý do.
- **Mã hàng / mã kho trong MISA** khai một lần ở trang **Phân loại hàng hóa**; để trống thì dùng mã hàng của người bán.
- **Tên cột hiện là bản tạm.** Cần file mẫu nhập khẩu thật từ MISA ASP (Mua hàng, Bán hàng) để sửa `COT_MUA_HANG`, `COT_BAN_HANG` trong `thuedn/misa.py` cho khớp.

## Google Drive riêng cho từng công ty

Mỗi công ty khai một **email Google riêng**; file của công ty nào chỉ đẩy vào Drive của email công ty đó:
`Hóa đơn <MST> - <Tên công ty>/<kỳ>/Bảng kê <MST> <kỳ>.xlsx` (và `XML <MST> <kỳ>.zip`). Kỳ là `2026-10` nếu tải trọn tháng.

1. **Làm một lần**: trang **Cài đặt** có hướng dẫn tạo OAuth client trên Google Cloud (bật Google Drive API, loại *Web application*, redirect URI `http://127.0.0.1:5000/google/callback`, bấm *Publish app*), rồi dán Client ID / Client secret.
2. Trang **Doanh nghiệp**: nhập email Google cho từng công ty → bấm **Kết nối Drive** → đăng nhập **đúng email đó**.
3. Khi tải hóa đơn, để tick **Đẩy lên Google Drive của từng công ty**; hoặc bấm **Đẩy lên Google Drive** ở trang Kết quả.

Chống nhầm công ty:
- Kết nối mà đăng nhập email khác email đã khai → **từ chối, không lưu**, thu hồi quyền vừa cấp.
- Mỗi lần đẩy file đều hỏi lại Google đang là email nào; khác email đã khai → không đẩy.
- Đổi email của công ty → tự ngắt kết nối Drive cũ.
- File chỉ chứa hóa đơn của đúng MST đó (kiểm tra lần cuối trước khi đẩy).
- Quyền xin là `drive.file`: công cụ chỉ thấy file do chính nó tạo, không đọc được file khác trên Drive.
- Token Google và Client secret lưu mã hóa trong thư mục `data/`.

## Các bước test lần đầu trên máy anh (làm với 1 công ty trước)

1. Chạy `run.bat`, tạo tài khoản Admin đầu tiên, thêm **1 công ty**.
2. Tải hóa đơn **1 tháng**, tick **Tải kèm XML**. Nếu lỗi ở bước captcha / đăng nhập / tải: chụp màn hình gửi Claude sửa `thuedn/portal.py`.
3. Mở Excel, kiểm tra:
   - Số hóa đơn mua vào / bán ra khớp với cổng thuế.
   - Một hóa đơn **điều chỉnh giảm** thật: số tiền trong XML là **âm hay dương** (ảnh hưởng cột "sau điều chỉnh" và "Điều chỉnh tăng / giảm").
   - Hóa đơn điều chỉnh có ghép đúng hóa đơn gốc không.
   - Sheet chi tiết hàng hóa có đủ mã hàng, số lượng, đơn giá.
4. Ổn rồi mới thêm 9 công ty còn lại.

## Nhiều máy dùng chung một bộ số liệu (mạng văn phòng / cùng wifi)

Chọn **một máy làm máy chính** (nên là máy luôn bật, ví dụ máy Windows của Quản trị); các máy khác chỉ mở trình duyệt, không cài gì.

1. Trên máy chính (Windows): bấm đúp **`run_mang_noi_bo.bat`** (Mac: `.venv/bin/python app.py --mang-noi-bo`). Windows hỏi tường lửa: chọn **Private networks** → **Allow**.
2. Cửa sổ hiện địa chỉ, ví dụ `http://192.168.1.10:5000`. Máy khác cùng mạng mở địa chỉ đó và **đăng nhập** bằng tài khoản của mình.
3. **Kết nối Google Drive** cho các công ty phải làm **trên chính máy chính** (mở `http://127.0.0.1:5000`).
4. Chỉ một bộ dữ liệu (thư mục `data/` trên máy chính) — không cài thêm bản thứ hai trên máy khác để tránh lệch số liệu.
5. Hai máy ở hai nơi khác mạng: cần máy chủ VPS (xem giai đoạn 2).

## Chạy trên Mac

Mở **Terminal** trong thư mục `thue-dn` và gõ `bash run.sh`. Lần đầu tự cài thư viện (cần Python 3: python.org), sau đó trình duyệt mở `http://127.0.0.1:5000`. Lệnh tạo tài khoản trên Mac: `.venv/bin/python tao_tai_khoan.py <email> admin "Họ tên"`.

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
- Tài khoản gợi ý theo **Thông tư 133** (mặc định: 6421 chi phí bán hàng, 6422 chi phí QLDN, 154 chi phí sản xuất, chiết khấu bán hàng ghi giảm 511) hoặc Thông tư 200, chọn ở trang **Cài đặt**. Tài khoản **chỉ là gợi ý**; kế toán quyết định cuối cùng.

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
| File chứng từ hạch toán sẵn để nhập MISA | Xong phần hạch toán, đã kiểm thử. **Tên cột cần khớp với file mẫu nhập khẩu thật của MISA ASP** |
| Đăng nhập, 3 cấp tài khoản (Admin, Quản trị, Người sử dụng) | Xong, đã kiểm thử |
| Đẩy file lên Google Drive riêng của từng công ty | Xong, đã kiểm thử với Google giả lập. **Cần thử trên máy anh** với tài khoản Google thật |
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

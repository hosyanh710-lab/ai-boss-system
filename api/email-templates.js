// Email HTML templates — AI BOSS SYSTEM
// Dành cho: paying customers (adapted từ 5-day onboarding sequence)

const BRAND = {
  name: 'AI BOSS SYSTEM',
  from: 'Hồ Sỹ Anh',
  zalo: '0918 303 039',
  email: 'hosyanh159@gmail.com',
  primary: '#3B82F6',
  purple: '#7C3AED',
};

function htmlWrapper(content, previewText = '') {
  return `<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="X-UA-Compatible" content="IE=edge">
${previewText ? `<div style="display:none;max-height:0;overflow:hidden;font-size:1px;line-height:1px;color:#fff;opacity:0;">${previewText}&nbsp;&zwnj;&nbsp;&zwnj;</div>` : ''}
</head>
<body style="margin:0;padding:0;background:#F1F5F9;font-family:'Helvetica Neue',Arial,sans-serif;color:#1E293B;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#F1F5F9;padding:32px 16px;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">

  <!-- Header -->
  <tr><td style="background:linear-gradient(135deg,#0F172A,#1E293B);border-radius:16px 16px 0 0;padding:28px 32px;text-align:center;">
    <div style="display:inline-block;width:40px;height:40px;background:linear-gradient(135deg,#3B82F6,#7C3AED);border-radius:10px;text-align:center;line-height:40px;color:#fff;font-weight:900;font-size:20px;vertical-align:middle;margin-right:10px;">A</div>
    <span style="color:#fff;font-size:18px;font-weight:700;vertical-align:middle;">AI BOSS SYSTEM</span>
  </td></tr>

  <!-- Body -->
  <tr><td style="background:#fff;padding:36px 40px;">
    ${content}
  </td></tr>

  <!-- Footer -->
  <tr><td style="background:#0F172A;border-radius:0 0 16px 16px;padding:24px 32px;text-align:center;">
    <p style="color:#94A3B8;font-size:13px;margin:0 0 8px;">Hồ Sỹ Anh · Khata · AI BOSS SYSTEM</p>
    <p style="color:#64748B;font-size:12px;margin:0;">📞 Zalo: ${BRAND.zalo} &nbsp;|&nbsp; 📧 ${BRAND.email}</p>
    <p style="color:#475569;font-size:11px;margin:12px 0 0;">Anh/chị nhận email này vì đã đăng ký AI BOSS SYSTEM. <a href="[UNSUBSCRIBE_URL]" style="color:#64748B;">Hủy đăng ký</a></p>
  </td></tr>

</table>
</td></tr>
</table>
</body>
</html>`;
}

function btn(text, url, color = '#3B82F6') {
  return `<div style="text-align:center;margin:28px 0;">
    <a href="${url}" style="display:inline-block;background:linear-gradient(135deg,${color},#7C3AED);color:#fff;font-size:16px;font-weight:700;text-decoration:none;padding:14px 36px;border-radius:50px;box-shadow:0 4px 15px rgba(59,130,246,.4);">${text}</a>
  </div>`;
}

function divider() {
  return `<hr style="border:none;border-top:1px solid #E2E8F0;margin:28px 0;">`;
}

function highlight(text) {
  return `<div style="background:#EFF6FF;border-left:4px solid #3B82F6;border-radius:0 8px 8px 0;padding:16px 20px;margin:20px 0;color:#1E3A5F;font-size:15px;">${text}</div>`;
}

// ─────────────────────────────────────────────────────────────
// EMAIL #1 — Ngay sau khi admin xác nhận
// ─────────────────────────────────────────────────────────────
function email1({ name, planName, planLabel, courseLink, orderId }) {
  const subject = `🎉 Chào mừng ${name} — Đây là link truy cập AI BOSS SYSTEM của bạn`;
  const preview = 'Link khóa học + Telegram group + hướng dẫn bắt đầu ngay hôm nay.';

  const body = `
    <h1 style="font-size:26px;font-weight:800;color:#0F172A;margin:0 0 8px;">Chào mừng ${name}! 🎉</h1>
    <p style="font-size:15px;color:#475569;margin:0 0 24px;">Thanh toán của anh/chị đã được xác nhận. Đây là tất cả thứ anh/chị cần để bắt đầu ngay hôm nay.</p>

    <div style="background:#F0FDF4;border:2px solid #86EFAC;border-radius:12px;padding:24px;margin-bottom:24px;">
      <p style="margin:0 0 12px;font-weight:700;color:#166534;font-size:16px;">✅ Đơn hàng đã xác nhận</p>
      <p style="margin:0 0 6px;font-size:14px;color:#166534;">🔖 Mã đơn: <strong>${orderId}</strong></p>
      <p style="margin:0 0 6px;font-size:14px;color:#166534;">📦 Gói: <strong>${planName} — ${planLabel}</strong></p>
    </div>

    <h2 style="font-size:18px;font-weight:700;color:#0F172A;margin:0 0 16px;">Bước 1 — Truy cập khóa học</h2>
    ${btn('🚀 Vào Khóa Học Ngay →', courseLink)}

    ${divider()}

    <h2 style="font-size:18px;font-weight:700;color:#0F172A;margin:0 0 16px;">Bước 2 — Tham gia nhóm SME AI Club</h2>
    <p style="font-size:15px;color:#475569;margin:0 0 16px;">Nhóm kín Zalo dành riêng cho học viên — Q&amp;A live 2 lần/tháng, peer review, và cập nhật AI tool hàng tuần.</p>
    ${btn('💬 Vào Nhóm SME AI Club →', 'https://zalo.me/g/aibossclub', '#7C3AED')}

    ${divider()}

    <h2 style="font-size:18px;font-weight:700;color:#0F172A;margin:0 0 16px;">Bước 3 — Làm gì trong 24 giờ đầu?</h2>
    <table cellpadding="0" cellspacing="0" style="width:100%;">
      <tr>
        <td style="padding:10px 0;vertical-align:top;width:36px;"><div style="width:28px;height:28px;background:linear-gradient(135deg,#3B82F6,#7C3AED);border-radius:50%;text-align:center;line-height:28px;color:#fff;font-weight:700;font-size:13px;">1</div></td>
        <td style="padding:10px 0 10px 12px;font-size:15px;color:#334155;">Vào <strong>Module 1</strong> — xem bài 1.1 (30 phút). Tư duy đúng trước khi bắt đầu.</td>
      </tr>
      <tr>
        <td style="padding:10px 0;vertical-align:top;"><div style="width:28px;height:28px;background:linear-gradient(135deg,#3B82F6,#7C3AED);border-radius:50%;text-align:center;line-height:28px;color:#fff;font-weight:700;font-size:13px;">2</div></td>
        <td style="padding:10px 0 10px 12px;font-size:15px;color:#334155;">Tải <strong>Template T01-A</strong> (Business Process Map) — điền vào chiều nay.</td>
      </tr>
      <tr>
        <td style="padding:10px 0;vertical-align:top;"><div style="width:28px;height:28px;background:linear-gradient(135deg,#3B82F6,#7C3AED);border-radius:50%;text-align:center;line-height:28px;color:#fff;font-weight:700;font-size:13px;">3</div></td>
        <td style="padding:10px 0 10px 12px;font-size:15px;color:#334155;">Reply email này và cho tôi biết: <strong>Doanh nghiệp anh/chị ngành gì?</strong> Tôi đọc từng email.</td>
      </tr>
    </table>

    ${highlight('💡 <strong>Mẹo từ học viên đợt đầu:</strong> Đừng cố xem hết tất cả ngay. Xem Module 1 → làm bài tập → rồi mới qua Module 2. Hệ thống được thiết kế theo thứ tự — làm đúng thứ tự sẽ nhanh hơn.')}

    <p style="font-size:15px;color:#475569;margin:24px 0 8px;">Nếu anh/chị gặp vấn đề gì:</p>
    <p style="font-size:15px;color:#475569;margin:0;">📞 Zalo trực tiếp: <strong>${BRAND.zalo}</strong> (Hồ Sỹ Anh) — tôi phản hồi trong vòng 2 giờ trong giờ hành chính.</p>

    <p style="font-size:15px;color:#334155;margin:28px 0 4px;">Chúc anh/chị học tốt và áp dụng nhanh!</p>
    <p style="font-size:15px;font-weight:700;color:#0F172A;margin:0;">Hồ Sỹ Anh</p>
    <p style="font-size:13px;color:#64748B;margin:4px 0 0;">Chủ DN Khata · Founder AI BOSS SYSTEM</p>

    <p style="font-size:13px;color:#94A3B8;margin:24px 0 0;font-style:italic;">P.S. Ngày mai tôi sẽ chia sẻ câu chuyện tôi đã thay đổi doanh nghiệp như thế nào — và 1 mẹo nhanh anh/chị có thể áp dụng ngay trong tuần này.</p>`;

  return { subject, html: htmlWrapper(body, preview) };
}

// ─────────────────────────────────────────────────────────────
// EMAIL #2 — Ngày 1 (24 giờ sau)
// ─────────────────────────────────────────────────────────────
function email2({ name }) {
  const subject = `Tôi đã mất 2 năm để học điều này — anh/chị không cần vậy`;
  const preview = 'Câu chuyện thật từ doanh nghiệp tôi + 1 tip bắt đầu ngay hôm nay.';

  const body = `
    <p style="font-size:15px;color:#475569;margin:0 0 20px;">Chào ${name},</p>
    <h1 style="font-size:24px;font-weight:800;color:#0F172A;margin:0 0 20px;">Anh/chị đã xem Module 1 chưa?</h1>

    <p style="font-size:15px;color:#334155;line-height:1.7;margin:0 0 16px;">Nếu chưa — hoàn toàn bình thường. Hôm nay để tôi kể cho anh/chị nghe <em>tại sao</em> tôi tạo ra khóa học này.</p>

    ${divider()}

    <h2 style="font-size:19px;font-weight:700;color:#0F172A;margin:0 0 16px;">3 năm trước, tôi điều hành Khata với 12 nhân viên.</h2>
    <p style="font-size:15px;color:#334155;line-height:1.7;margin:0 0 16px;">Từ ngoài nhìn vào, mọi thứ tốt. Nhưng tôi đang làm việc <strong>12–14 tiếng mỗi ngày.</strong></p>

    <div style="background:#FFF7ED;border-left:4px solid #F97316;border-radius:0 8px 8px 0;padding:16px 20px;margin:20px 0;">
      <p style="margin:0;color:#7C2D12;font-size:14px;line-height:1.6;">Sáng: duyệt inbox CSKH. Trưa: họp team, xử lý vận hành. Chiều: review content. Tối: tổng hợp báo cáo. Đêm: lo kế hoạch tuần sau. Lặp lại mỗi ngày.</p>
    </div>

    <p style="font-size:15px;color:#334155;line-height:1.7;margin:16px 0;">Tôi không có thời gian để <em>xây dựng</em> doanh nghiệp. Tôi chỉ đang <em>vận hành</em> nó theo kiểu chữa cháy.</p>

    <p style="font-size:15px;color:#334155;line-height:1.7;margin:0 0 16px;">Rồi tôi bắt đầu thử AI — không phải vì "trend", mà vì <strong>tôi quá mệt.</strong></p>

    <p style="font-size:15px;color:#334155;line-height:1.7;margin:0 0 8px;"><strong>Tháng đầu tiên:</strong> Setup quick reply CSKH → inbox thủ công giảm <strong>65%</strong> trong tuần đầu.</p>
    <p style="font-size:15px;color:#334155;line-height:1.7;margin:0 0 8px;"><strong>Tháng hai:</strong> AI hóa content → tiết kiệm 4 giờ/tuần, đăng đều 7 bài/tuần.</p>
    <p style="font-size:15px;color:#334155;line-height:1.7;margin:0 0 20px;"><strong>Tháng ba:</strong> Báo cáo tự động → không còn cuộc họp tổng hợp số liệu nào nữa.</p>

    ${divider()}

    <h2 style="font-size:18px;font-weight:700;color:#0F172A;margin:0 0 16px;">💡 Tip hôm nay — Làm ngay trong 15 phút</h2>
    <p style="font-size:15px;color:#334155;line-height:1.7;margin:0 0 16px;">Mở inbox 30 ngày qua. Đếm <strong>5 câu hỏi xuất hiện nhiều nhất</strong> từ khách hàng.</p>
    <p style="font-size:15px;color:#334155;line-height:1.7;margin:0 0 16px;">Đó là 5 câu hỏi đầu tiên cần tạo template trả lời tự động. Sau khi có template → 70% inbox tự xử lý.</p>
    ${highlight('Ngày mai tôi sẽ chia sẻ đúng cách tạo những template đó bằng AI — copy-paste được ngay.')}

    <p style="font-size:15px;color:#334155;margin:24px 0 4px;">Anh/chị đang làm được đến bước nào rồi? Reply cho tôi biết.</p>
    <p style="font-size:15px;font-weight:700;color:#0F172A;margin:0;">Hồ Sỹ Anh</p>
    <p style="font-size:13px;color:#64748B;margin:4px 0 0;">Chủ DN Khata · Founder AI BOSS SYSTEM</p>

    <p style="font-size:13px;color:#94A3B8;margin:24px 0 0;font-style:italic;">P.S. Anh/chị đang điều hành doanh nghiệp ngành nào? Reply để tôi gợi ý quy trình nên AI hóa đầu tiên theo ngành cụ thể của anh/chị.</p>`;

  return { subject, html: htmlWrapper(body, preview) };
}

// ─────────────────────────────────────────────────────────────
// EMAIL #3 — Ngày 3
// ─────────────────────────────────────────────────────────────
function email3({ name }) {
  const subject = `47 tin nhắn/sáng → 14 tin. Đây là cách làm (copy được ngay)`;
  const preview = 'Quy trình CSKH AI hóa từng bước, áp dụng được trong tuần này.';

  const body = `
    <p style="font-size:15px;color:#475569;margin:0 0 20px;">Chào ${name},</p>
    <h1 style="font-size:24px;font-weight:800;color:#0F172A;margin:0 0 8px;">Hôm nay tôi chia sẻ 1 ví dụ thực tế</h1>
    <p style="font-size:15px;color:#64748B;margin:0 0 24px;">Anh/chị có thể áp dụng ngay trong tuần này — không cần tool trả phí.</p>

    <h2 style="font-size:17px;font-weight:700;color:#EF4444;margin:0 0 12px;">❌ Bài toán quen thuộc:</h2>
    <p style="font-size:15px;color:#334155;line-height:1.7;margin:0 0 20px;">Mỗi sáng inbox có 40–60 tin nhắn. 70% là những câu hỏi giống nhau: "Giá bao nhiêu?", "Ship về tỉnh được không?", "Còn hàng không?". Nhân viên phải đọc và trả lời từng tin. Mất 1–2 tiếng/ngày. Hay bỏ sót. Khách đợi lâu rồi không mua.</p>

    ${divider()}

    <h2 style="font-size:17px;font-weight:700;color:#3B82F6;margin:0 0 16px;">✅ Giải pháp 3 bước (không cần code, không cần tool trả phí):</h2>

    <div style="margin-bottom:16px;padding:20px;background:#F8FAFC;border-radius:10px;border:1px solid #E2E8F0;">
      <p style="margin:0 0 8px;font-weight:700;color:#0F172A;font-size:15px;">Bước 1 — Liệt kê 10 câu hỏi thường gặp nhất</p>
      <p style="margin:0;font-size:14px;color:#475569;line-height:1.6;">Mở chat lịch sử 30 ngày qua, đếm câu nào xuất hiện nhiều nhất. Thường chỉ cần 8–12 câu là cover 70% inbox.</p>
    </div>

    <div style="margin-bottom:16px;padding:20px;background:#F8FAFC;border-radius:10px;border:1px solid #E2E8F0;">
      <p style="margin:0 0 8px;font-weight:700;color:#0F172A;font-size:15px;">Bước 2 — Soạn template trả lời bằng ChatGPT</p>
      <p style="margin:0 0 10px;font-size:14px;color:#475569;line-height:1.6;">Dán prompt này vào ChatGPT (thay thông tin trong [ ]):</p>
      <div style="background:#0F172A;border-radius:8px;padding:16px;font-family:monospace;font-size:12px;color:#94A3B8;line-height:1.6;">"Tôi là chủ shop [tên]. Hãy viết 10 mẫu trả lời ngắn gọn, thân thiện cho các câu hỏi sau: [dán danh sách câu hỏi]. Tone: ấm áp, chuyên nghiệp, có emoji nhẹ. Kết thúc mỗi câu bằng CTA nhẹ."</div>
      <p style="margin:10px 0 0;font-size:13px;color:#64748B;font-style:italic;">Mất 5 phút. Có ngay 10 template chất lượng hơn tự viết.</p>
    </div>

    <div style="padding:20px;background:#F8FAFC;border-radius:10px;border:1px solid #E2E8F0;">
      <p style="margin:0 0 8px;font-weight:700;color:#0F172A;font-size:15px;">Bước 3 — Lưu vào "Quick Reply" của Facebook/Zalo/Instagram</p>
      <p style="margin:0;font-size:14px;color:#475569;line-height:1.6;">Tất cả platform đều có tính năng này (miễn phí). Nhân viên gõ /gia → template bắn ra. Không soạn lại.</p>
    </div>

    ${divider()}

    <div style="background:#F0FDF4;border-radius:10px;padding:20px;margin-bottom:20px;">
      <p style="margin:0 0 8px;font-weight:700;color:#166534;font-size:15px;">📊 Kết quả thực tế tại Khata sau khi áp dụng:</p>
      <p style="margin:0 0 6px;font-size:14px;color:#166534;">✓ Inbox cần xử lý thủ công: giảm <strong>65%</strong></p>
      <p style="margin:0 0 6px;font-size:14px;color:#166534;">✓ Thời gian CSKH mỗi sáng: từ 90 phút → <strong>25 phút</strong></p>
      <p style="margin:0;font-size:14px;color:#166534;">✓ Tốc độ phản hồi nhanh hơn 3x → tỷ lệ chốt đơn tăng</p>
    </div>

    ${highlight('🎯 <strong>Thử làm hôm nay:</strong> Mở inbox, đếm 5 câu hỏi xuất hiện nhiều nhất → dán vào ChatGPT → có template dùng ngay ngày mai. Mất 15 phút.')}

    <p style="font-size:15px;color:#334155;margin:24px 0 4px;">Đây chỉ là 1 trong những quy trình Module 2 đi qua chi tiết hơn. Ngày kia tôi sẽ kể câu chuyện chị H.T. đã áp dụng và giảm inbox từ 47 xuống 14 tin.</p>
    <p style="font-size:15px;font-weight:700;color:#0F172A;margin:0;">Hồ Sỹ Anh</p>`;

  return { subject, html: htmlWrapper(body, preview) };
}

// ─────────────────────────────────────────────────────────────
// EMAIL #4 — Ngày 5
// ─────────────────────────────────────────────────────────────
function email4({ name }) {
  const subject = `Chị H.T. giảm từ 47 tin/sáng xuống 14 — trong tuần đầu tiên`;
  const preview = 'Case study thật: chuỗi spa TP.HCM + AI = tiết kiệm 20 giờ/tuần.';

  const body = `
    <p style="font-size:15px;color:#475569;margin:0 0 20px;">Chào ${name},</p>
    <h1 style="font-size:24px;font-weight:800;color:#0F172A;margin:0 0 8px;">Hôm nay tôi muốn giới thiệu chị H.T.</h1>
    <p style="font-size:15px;color:#64748B;margin:0 0 24px;">Chủ chuỗi spa tại TP.HCM — học viên đầu tiên của AI BOSS SYSTEM.</p>

    <div style="background:#F8FAFC;border-radius:12px;padding:24px;margin-bottom:24px;border:1px solid #E2E8F0;">
      <p style="margin:0 0 12px;font-size:15px;color:#334155;line-height:1.7;font-style:italic;">"Khi đăng ký, tôi nói với anh Sỹ Anh: <strong>Tôi không tin AI làm được cho ngành spa. Khách của tôi cần cảm giác cá nhân hóa.</strong>"</p>
      <p style="margin:0;font-size:13px;color:#64748B;">— Chị H.T., Chủ chuỗi spa · TP.HCM</p>
    </div>

    <p style="font-size:15px;color:#334155;line-height:1.7;margin:0 0 16px;">Tôi hiểu lo ngại đó. Và tôi không cố thuyết phục. Tôi chỉ nói: <em>"Thử Module 2 trước. Nếu không thấy kết quả trong tuần đầu, tôi hoàn tiền ngay."</em></p>

    ${divider()}

    <h2 style="font-size:18px;font-weight:700;color:#0F172A;margin:0 0 16px;">Tuần đầu tiên của chị H.T.:</h2>
    <p style="font-size:15px;color:#334155;line-height:1.7;margin:0 0 20px;">Chị áp dụng đúng quy trình CSKH từ Module 2 — setup template quick reply, phân loại inbox theo 3 nhóm, tạo kịch bản xử lý từng loại.</p>

    <div style="background:#F0FDF4;border-radius:12px;padding:24px;margin-bottom:24px;">
      <p style="margin:0 0 12px;font-weight:700;color:#166534;font-size:16px;">📊 Kết quả sau 7 ngày:</p>
      <p style="margin:0 0 8px;font-size:15px;color:#166534;">✓ Tin nhắn cần xử lý thủ công: <strong>từ 47 xuống còn 14</strong> mỗi sáng</p>
      <p style="margin:0 0 8px;font-size:15px;color:#166534;">✓ Thời gian team CSKH tiết kiệm: <strong>hơn 2 tiếng/ngày</strong></p>
      <p style="margin:0;font-size:14px;color:#166534;font-style:italic;">"Tôi không ngờ kết quả lại nhanh đến vậy." — Chị H.T.</p>
    </div>

    ${highlight('💡 <strong>Điều quan trọng:</strong> AI không "thay thế" cảm giác cá nhân hóa. Nó xử lý những câu hỏi lặp lại → giải phóng team để tập trung vào những khách cần chăm sóc thật sự. Đó là sự khác biệt giữa dùng AI đúng cách và sai cách.')}

    ${divider()}

    <h2 style="font-size:17px;font-weight:700;color:#0F172A;margin:0 0 12px;">Anh/chị đang tiến đến đâu rồi?</h2>
    <p style="font-size:15px;color:#334155;line-height:1.7;margin:0 0 16px;">Nhìn lại checklist Module 1 của anh/chị: đã xác định được 3 quy trình ưu tiên AI hóa chưa?</p>
    <p style="font-size:15px;color:#334155;line-height:1.7;margin:0 0 20px;">Nếu chưa — không sao. Reply email này, tôi sẽ giúp anh/chị xác định nhanh trong 10 phút.</p>

    <p style="font-size:15px;font-weight:700;color:#0F172A;margin:0;">Hồ Sỹ Anh</p>
    <p style="font-size:13px;color:#64748B;margin:4px 0 0;">Chủ DN Khata · Founder AI BOSS SYSTEM</p>

    <p style="font-size:13px;color:#94A3B8;margin:24px 0 0;font-style:italic;">P.S. Ngày kia (Email cuối trong chuỗi này) tôi sẽ chia sẻ cách dùng SME AI Club hiệu quả nhất — và nhắc về Strategy Call 1:1 nếu anh/chị chưa đặt lịch.</p>`;

  return { subject, html: htmlWrapper(body, preview) };
}

// ─────────────────────────────────────────────────────────────
// EMAIL #5 — Ngày 7 (Email cuối chuỗi onboarding)
// ─────────────────────────────────────────────────────────────
function email5({ name, planName, courseLink }) {
  const subject = `Check-in ngày 7 — anh/chị đang ở đâu trong hành trình?`;
  const preview = '7 ngày kể từ khi bắt đầu. Đây là những gì cần làm tiếp theo.';

  const hasStrategyCall = planName === 'BOSS' || planName === 'VIP';

  const body = `
    <p style="font-size:15px;color:#475569;margin:0 0 20px;">Chào ${name},</p>
    <h1 style="font-size:24px;font-weight:800;color:#0F172A;margin:0 0 8px;">Đã 7 ngày rồi! 🎉</h1>
    <p style="font-size:15px;color:#64748B;margin:0 0 24px;">Đây là email cuối trong chuỗi onboarding. Tôi muốn check-in xem anh/chị đang tiến đến đâu.</p>

    <h2 style="font-size:18px;font-weight:700;color:#0F172A;margin:0 0 16px;">Trong 7 ngày qua, tôi đã chia sẻ:</h2>
    <table cellpadding="0" cellspacing="0" style="width:100%;margin-bottom:24px;">
      <tr><td style="padding:8px 0;font-size:15px;color:#334155;">📎 Email #1: Link khóa học + Telegram group + hướng dẫn bắt đầu</td></tr>
      <tr><td style="padding:8px 0;font-size:15px;color:#334155;">📖 Email #2: Câu chuyện của tôi + tip đầu tiên</td></tr>
      <tr><td style="padding:8px 0;font-size:15px;color:#334155;">⚙️ Email #3: Quy trình CSKH AI hóa — 3 bước copy được ngay</td></tr>
      <tr><td style="padding:8px 0;font-size:15px;color:#334155;">📊 Email #4: Case study chị H.T. — từ 47 → 14 tin/sáng</td></tr>
    </table>

    ${divider()}

    <h2 style="font-size:18px;font-weight:700;color:#0F172A;margin:0 0 16px;">Bước tiếp theo — Tuần 2 của anh/chị:</h2>

    <div style="margin-bottom:14px;padding:18px;background:#EFF6FF;border-radius:10px;border:1px solid #BFDBFE;">
      <p style="margin:0 0 6px;font-weight:700;color:#1E40AF;font-size:15px;">📌 Nếu chưa xem Module 1 → làm ngay tuần này</p>
      <p style="margin:0;font-size:14px;color:#1E40AF;">Audit doanh nghiệp + Roadmap 30 ngày là nền tảng của tất cả các module còn lại.</p>
    </div>

    <div style="margin-bottom:14px;padding:18px;background:#F0FDF4;border-radius:10px;border:1px solid #86EFAC;">
      <p style="margin:0 0 6px;font-weight:700;color:#166534;font-size:15px;">✅ Nếu đã xem Module 1 → bắt đầu Module 2 (CSKH)</p>
      <p style="margin:0;font-size:14px;color:#166534;">Setup quick reply + template CSKH = kết quả đầu tiên trong 7 ngày.</p>
    </div>

    ${btn('🚀 Tiếp Tục Khóa Học →', courseLink)}

    ${divider()}

    <h2 style="font-size:18px;font-weight:700;color:#0F172A;margin:0 0 16px;">💬 Dùng SME AI Club hiệu quả nhất:</h2>
    <p style="font-size:15px;color:#334155;line-height:1.7;margin:0 0 8px;"><strong>1.</strong> Đăng câu hỏi cụ thể (không phải câu hỏi chung): "Tôi đang làm [X], gặp vấn đề [Y], tôi đã thử [Z]. Cần hỏi gì?"</p>
    <p style="font-size:15px;color:#334155;line-height:1.7;margin:0 0 8px;"><strong>2.</strong> Share SOP anh/chị vừa viết xong → nhận peer review từ học viên khác.</p>
    <p style="font-size:15px;color:#334155;line-height:1.7;margin:0 0 20px;"><strong>3.</strong> Tham gia Q&amp;A live 2 lần/tháng — đặt câu hỏi trước để được ưu tiên trả lời.</p>

    ${hasStrategyCall ? `
    ${highlight('⚡ <strong>Nhắc nhở: Strategy Call 1:1</strong><br>Anh/chị có 1 suất Strategy Call 60 phút với tôi. Đặt lịch qua Zalo <strong>0918 303 039</strong> để tôi review bản đồ quy trình và roadmap cá nhân hóa cho doanh nghiệp của anh/chị.')}
    ` : ''}

    ${divider()}

    <p style="font-size:15px;color:#334155;line-height:1.7;margin:0 0 16px;">Tôi biết 30 ngày nghe có vẻ nhiều. Nhưng nhớ lại câu hỏi tôi hỏi ban đầu:</p>
    <p style="font-size:16px;font-weight:700;color:#0F172A;margin:0 0 16px;font-style:italic;">"Nếu có thêm 3 giờ/ngày, anh/chị sẽ dùng để làm gì?"</p>
    <p style="font-size:15px;color:#334155;line-height:1.7;margin:0 0 24px;">30 ngày từ bây giờ, câu trả lời đó có thể trở thành thực tế. Hệ thống đã ở trước mắt anh/chị.</p>

    <p style="font-size:15px;color:#334155;margin:0 0 4px;">Tiếp tục tiến về phía trước,</p>
    <p style="font-size:15px;font-weight:700;color:#0F172A;margin:0;">Hồ Sỹ Anh</p>
    <p style="font-size:13px;color:#64748B;margin:4px 0 0;">Chủ DN Khata · Founder AI BOSS SYSTEM</p>

    <p style="font-size:13px;color:#94A3B8;margin:24px 0 0;font-style:italic;">P.S. Sau chuỗi 7 ngày này, tôi sẽ vẫn gửi tips AI hóa mỗi tuần — nhưng tần suất thưa hơn. Anh/chị muốn nhận thêm nội dung về chủ đề nào nhất? Reply email này cho tôi biết.</p>`;

  return { subject, html: htmlWrapper(body, preview) };
}

// ─────────────────────────────────────────────────────────────
// EMAIL #0 — Xác nhận đăng ký (gửi ngay khi khách submit form)
// Chưa có link khóa học — chỉ xác nhận nhận được đơn
// ─────────────────────────────────────────────────────────────
function email0({ name, planName, planLabel, orderId }) {
  const subject = `✅ Đã nhận đăng ký của ${name} — AI BOSS SYSTEM đang xác minh`;
  const preview = 'Chúng tôi đã nhận được đăng ký. Thanh toán sẽ được xác minh trong 1–2 giờ.';

  const body = `
    <h1 style="font-size:26px;font-weight:800;color:#0F172A;margin:0 0 8px;">Cảm ơn ${name}! 🙌</h1>
    <p style="font-size:15px;color:#475569;margin:0 0 24px;">Chúng tôi đã nhận được đăng ký của anh/chị và đang xác minh thanh toán.</p>

    <div style="background:#FFF7ED;border:2px solid #FED7AA;border-radius:12px;padding:24px;margin-bottom:24px;">
      <p style="margin:0 0 10px;font-weight:700;color:#9A3412;font-size:16px;">⏳ Đang xác minh thanh toán</p>
      <p style="margin:0 0 8px;font-size:14px;color:#9A3412;">Thời gian xác minh: <strong>1–2 giờ</strong> trong giờ hành chính.</p>
      <p style="margin:0;font-size:13px;color:#C2410C;">Sau khi xác nhận xong, anh/chị sẽ nhận được email với link truy cập khóa học ngay.</p>
    </div>

    <div style="background:#F8FAFC;border-radius:12px;padding:20px;margin-bottom:24px;">
      <p style="margin:0 0 10px;font-weight:700;color:#0F172A;font-size:15px;">📋 Thông tin đăng ký của anh/chị:</p>
      <div style="font-size:14px;color:#475569;">
        <div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #E2E8F0;">
          <span>Họ tên</span><strong style="color:#0F172A;">${name}</strong>
        </div>
        <div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #E2E8F0;">
          <span>Gói đăng ký</span><strong style="color:#0F172A;">${planName} — ${planLabel}</strong>
        </div>
        <div style="display:flex;justify-content:space-between;padding:8px 0;">
          <span>Mã đơn hàng</span><strong style="color:#3B82F6;font-family:monospace;">${orderId}</strong>
        </div>
      </div>
    </div>

    ${highlight('💡 <strong>Trong lúc chờ xác minh:</strong> Anh/chị có thể nhắn Zalo <strong>0918 303 039</strong> (Hồ Sỹ Anh) kèm ảnh chụp bill chuyển khoản để được xác minh nhanh hơn.')}

    <h2 style="font-size:17px;font-weight:700;color:#0F172A;margin:24px 0 12px;">Tiếp theo anh/chị sẽ nhận được:</h2>
    <table cellpadding="0" cellspacing="0" style="width:100%;">
      <tr>
        <td style="padding:8px 0;vertical-align:top;width:32px;"><div style="width:26px;height:26px;background:#3B82F6;border-radius:50%;text-align:center;line-height:26px;color:#fff;font-weight:700;font-size:12px;">1</div></td>
        <td style="padding:8px 0 8px 10px;font-size:14px;color:#334155;">Email <strong>xác nhận thanh toán</strong> + link truy cập khóa học</td>
      </tr>
      <tr>
        <td style="padding:8px 0;vertical-align:top;"><div style="width:26px;height:26px;background:#7C3AED;border-radius:50%;text-align:center;line-height:26px;color:#fff;font-weight:700;font-size:12px;">2</div></td>
        <td style="padding:8px 0 8px 10px;font-size:14px;color:#334155;">Lời mời vào nhóm <strong>SME AI Club</strong> (Zalo)</td>
      </tr>
      <tr>
        <td style="padding:8px 0;vertical-align:top;"><div style="width:26px;height:26px;background:#10B981;border-radius:50%;text-align:center;line-height:26px;color:#fff;font-weight:700;font-size:12px;">3</div></td>
        <td style="padding:8px 0 8px 10px;font-size:14px;color:#334155;">Chuỗi <strong>7 ngày onboarding</strong> — tips thực chiến AI hóa doanh nghiệp</td>
      </tr>
    </table>

    <p style="font-size:15px;color:#334155;margin:28px 0 4px;">Hẹn gặp anh/chị trong email tiếp theo!</p>
    <p style="font-size:15px;font-weight:700;color:#0F172A;margin:0;">Hồ Sỹ Anh</p>
    <p style="font-size:13px;color:#64748B;margin:4px 0 0;">Chủ DN Khata · Founder AI BOSS SYSTEM</p>
    <p style="font-size:13px;color:#94A3B8;margin:16px 0 0;font-style:italic;">P.S. Nếu anh/chị chưa chuyển khoản — vui lòng bỏ qua email này. Đơn hàng sẽ tự hủy sau 24 giờ nếu không có thanh toán.</p>`;

  return { subject, html: htmlWrapper(body, preview) };
}

// ─────────────────────────────────────────────────────────────
// Exports
// ─────────────────────────────────────────────────────────────
module.exports = {
  getEmail: (emailNum, data) => {
    switch (emailNum) {
      case 0: return email0(data);
      case 1: return email1(data);
      case 2: return email2(data);
      case 3: return email3(data);
      case 4: return email4(data);
      case 5: return email5(data);
      default: return null;
    }
  },
  // Schedule: which day triggers which email
  EMAIL_SCHEDULE: [
    { emailNum: 2, daysAfter: 1 },
    { emailNum: 3, daysAfter: 3 },
    { emailNum: 4, daysAfter: 5 },
    { emailNum: 5, daysAfter: 7 },
  ],
};

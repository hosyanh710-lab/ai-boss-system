// Email HTML templates — AI BOSS SYSTEM
// Hai chuỗi:
//   ONBOARDING (#0–#5): Khách đã thanh toán
//   ABANDONED CART (AC#1–AC#3): Khách chưa thanh toán

// ── Helpers ───────────────────────────────────────────────────
function unsubscribeUrl(email) {
  const siteUrl = process.env.SITE_URL || 'https://ai-boss-system.vercel.app';
  const encoded = Buffer.from(email || '').toString('base64');
  return `${siteUrl}/api/unsubscribe?e=${encoded}`;
}

function paymentUrl() {
  return (process.env.SITE_URL || 'https://ai-boss-system.vercel.app') + '/#dang-ky';
}

function checklistUrl() {
  return process.env.CHECKLIST_PDF_URL || 'https://ai-boss-system.vercel.app/assets/lead-magnets/checklist-ai-sme/CHECKLIST-AI-HOA-SME.md';
}

function btn(text, url, color = '#3B82F6') {
  return `<div style="text-align:center;margin:24px 0;">
    <a href="${url}" style="display:inline-block;background:linear-gradient(135deg,${color},#7C3AED);color:#fff;font-size:15px;font-weight:700;text-decoration:none;padding:13px 32px;border-radius:50px;">${text}</a>
  </div>`;
}

function divider() {
  return `<hr style="border:none;border-top:1px solid #E2E8F0;margin:24px 0;">`;
}

function highlight(text) {
  return `<div style="background:#EFF6FF;border-left:4px solid #3B82F6;border-radius:0 8px 8px 0;padding:14px 18px;margin:18px 0;color:#1E3A5F;font-size:14px;">${text}</div>`;
}

function htmlWrapper(content, previewText, email) {
  const unsub = email ? `<a href="${unsubscribeUrl(email)}" style="color:#64748B;">Hủy đăng ký</a>` : 'Hủy đăng ký';
  return `<!DOCTYPE html><html lang="vi">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
${previewText ? `<div style="display:none;max-height:0;overflow:hidden;font-size:1px;color:#fff;opacity:0;">${previewText}&nbsp;&zwnj;</div>` : ''}
</head>
<body style="margin:0;padding:0;background:#F1F5F9;font-family:'Helvetica Neue',Arial,sans-serif;color:#1E293B;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#F1F5F9;padding:32px 16px;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">
  <tr><td style="background:linear-gradient(135deg,#0F172A,#1E293B);border-radius:16px 16px 0 0;padding:24px 32px;text-align:center;">
    <div style="display:inline-block;width:36px;height:36px;background:linear-gradient(135deg,#3B82F6,#7C3AED);border-radius:8px;text-align:center;line-height:36px;color:#fff;font-weight:900;font-size:18px;vertical-align:middle;margin-right:8px;">A</div>
    <span style="color:#fff;font-size:17px;font-weight:700;vertical-align:middle;">AI BOSS SYSTEM</span>
  </td></tr>
  <tr><td style="background:#fff;padding:32px 36px;">${content}</td></tr>
  <tr><td style="background:#0F172A;border-radius:0 0 16px 16px;padding:20px 32px;text-align:center;">
    <p style="color:#94A3B8;font-size:12px;margin:0 0 6px;">Hồ Sỹ Anh · Khata · AI BOSS SYSTEM</p>
    <p style="color:#64748B;font-size:11px;margin:0;">📞 Zalo: 0918 303 039 &nbsp;|&nbsp; 📧 hosyanh159@gmail.com</p>
    <p style="color:#475569;font-size:11px;margin:10px 0 0;">Anh/chị nhận email này vì đã đăng ký AI BOSS SYSTEM. ${unsub}</p>
  </td></tr>
</table></td></tr></table></body></html>`;
}

// ═══════════════════════════════════════════════════════════
// ONBOARDING SEQUENCE (#0 → #5) — Sau khi thanh toán
// ═══════════════════════════════════════════════════════════

function email0({ name, planName, planLabel, orderId, email }) {
  const subject = `✅ Đã nhận đăng ký của ${name} — AI BOSS SYSTEM đang xác minh`;
  const preview = 'Thanh toán sẽ được xác minh trong 1–2 giờ. Trong lúc chờ, đây là gì sẽ xảy ra tiếp theo.';
  const body = `
    <h1 style="font-size:24px;font-weight:800;color:#0F172A;margin:0 0 6px;">Cảm ơn ${name}! 🙌</h1>
    <p style="font-size:14px;color:#475569;margin:0 0 20px;">Đăng ký đã nhận — đang xác minh thanh toán.</p>
    <div style="background:#FFF7ED;border:2px solid #FED7AA;border-radius:10px;padding:18px 20px;margin-bottom:20px;">
      <p style="margin:0 0 8px;font-weight:700;color:#9A3412;font-size:15px;">⏳ Đang xác minh thanh toán</p>
      <p style="margin:0 0 6px;font-size:13px;color:#9A3412;">🔖 Mã đơn: <strong>${orderId}</strong></p>
      <p style="margin:0 0 6px;font-size:13px;color:#9A3412;">📦 Gói: <strong>${planName} — ${planLabel}</strong></p>
      <p style="margin:0;font-size:12px;color:#C2410C;">Thời gian: 1–2 giờ trong giờ hành chính.</p>
    </div>
    ${highlight('💡 <strong>Xác minh nhanh hơn:</strong> Gửi ảnh chụp bill chuyển khoản về Zalo <strong>0918 303 039</strong>')}
    <p style="font-size:14px;color:#334155;margin:18px 0 6px;font-weight:600;">Anh/chị sẽ nhận được:</p>
    <p style="font-size:14px;color:#475569;margin:0 0 6px;">① Email xác nhận + link truy cập khóa học</p>
    <p style="font-size:14px;color:#475569;margin:0 0 6px;">② Lời mời vào nhóm SME AI Club</p>
    <p style="font-size:14px;color:#475569;margin:0 0 20px;">③ Chuỗi 7 ngày onboarding thực chiến</p>
    <p style="font-size:14px;font-weight:700;color:#0F172A;margin:0;">Hồ Sỹ Anh</p>`;
  return { subject, html: htmlWrapper(body, preview, email) };
}

function email1({ name, planName, planLabel, courseLink, orderId, email }) {
  const subject = `🎉 Chào mừng ${name} — Đây là link truy cập AI BOSS SYSTEM`;
  const preview = 'Link khóa học + Telegram group + làm gì trong 24h đầu.';
  const body = `
    <h1 style="font-size:24px;font-weight:800;color:#0F172A;margin:0 0 6px;">Chào mừng ${name}! 🎉</h1>
    <p style="font-size:14px;color:#475569;margin:0 0 18px;">Thanh toán đã xác nhận — đây là tất cả anh/chị cần để bắt đầu ngay.</p>
    <div style="background:#F0FDF4;border:2px solid #86EFAC;border-radius:10px;padding:16px 18px;margin-bottom:18px;">
      <p style="margin:0 0 6px;font-weight:700;color:#166534;">✅ Đơn hàng: ${planName} — ${planLabel}</p>
      <p style="margin:0;font-size:12px;color:#166534;">Mã: ${orderId}</p>
    </div>
    <p style="font-size:15px;font-weight:700;color:#0F172A;margin:0 0 4px;">Bước 1 — Vào khóa học:</p>
    ${btn('🚀 Vào Khóa Học Ngay →', courseLink)}
    ${divider()}
    <p style="font-size:15px;font-weight:700;color:#0F172A;margin:0 0 4px;">Bước 2 — Tham gia SME AI Club:</p>
    <p style="font-size:13px;color:#475569;margin:0 0 10px;">Nhắn Zalo <strong>0918 303 039</strong> để được thêm vào nhóm Q&A live.</p>
    ${divider()}
    <p style="font-size:15px;font-weight:700;color:#0F172A;margin:0 0 8px;">Làm gì trong 24h đầu?</p>
    <p style="font-size:14px;color:#334155;margin:0 0 4px;">① Xem Module 1 — bài 1.1 (30 phút)</p>
    <p style="font-size:14px;color:#334155;margin:0 0 4px;">② Tải Template T01-A (Business Process Map)</p>
    <p style="font-size:14px;color:#334155;margin:0 0 18px;">③ Reply email này: doanh nghiệp anh/chị ngành gì?</p>
    ${highlight('💡 Đừng cố xem hết ngay. Làm đúng thứ tự Module 1 → 2 → 3 sẽ nhanh hơn.')}
    <p style="font-size:14px;font-weight:700;color:#0F172A;margin:16px 0 0;">Hồ Sỹ Anh</p>
    <p style="font-size:12px;color:#94A3B8;margin:6px 0 0;font-style:italic;">P.S. Ngày mai tôi gửi câu chuyện tôi đã thay đổi doanh nghiệp + 1 mẹo áp dụng ngay tuần này.</p>`;
  return { subject, html: htmlWrapper(body, preview, email) };
}

function email2({ name, email }) {
  const subject = `Tôi đã mất 2 năm để học điều này — anh/chị không cần vậy`;
  const preview = 'Câu chuyện thật từ doanh nghiệp tôi + tip áp dụng ngay hôm nay.';
  const body = `
    <p style="font-size:14px;color:#475569;margin:0 0 16px;">Chào ${name},</p>
    <h1 style="font-size:22px;font-weight:800;color:#0F172A;margin:0 0 16px;">3 năm trước, tôi điều hành Khata với 12 nhân viên</h1>
    <p style="font-size:14px;color:#334155;line-height:1.7;margin:0 0 12px;">Doanh thu ổn. Khách hàng hài lòng. Nhưng tôi làm việc <strong>12–14 tiếng/ngày.</strong></p>
    <div style="background:#FFF7ED;border-left:4px solid #F97316;border-radius:0 8px 8px 0;padding:14px 16px;margin:14px 0;font-size:13px;color:#7C2D12;line-height:1.6;">Sáng: inbox. Trưa: họp team. Chiều: content. Tối: báo cáo. Đêm: kế hoạch tuần sau. Lặp lại mỗi ngày.</div>
    <p style="font-size:14px;color:#334155;line-height:1.7;margin:0 0 12px;">Rồi tôi thử AI — không phải vì "trend", vì <strong>tôi quá mệt.</strong></p>
    <p style="font-size:14px;color:#334155;margin:0 0 4px;"><strong>Tháng 1:</strong> Inbox giảm <strong style="color:#16A34A">65%</strong> trong tuần đầu</p>
    <p style="font-size:14px;color:#334155;margin:0 0 4px;"><strong>Tháng 2:</strong> Tiết kiệm <strong style="color:#16A34A">4 giờ/tuần</strong> tạo content</p>
    <p style="font-size:14px;color:#334155;margin:0 0 18px;"><strong>Tháng 3:</strong> Không còn họp tổng hợp số liệu</p>
    ${divider()}
    <p style="font-size:15px;font-weight:700;color:#0F172A;margin:0 0 8px;">💡 Tip hôm nay — làm trong 15 phút:</p>
    <p style="font-size:14px;color:#334155;line-height:1.7;margin:0 0 12px;">Mở inbox 30 ngày qua → đếm <strong>5 câu hỏi xuất hiện nhiều nhất</strong>.</p>
    <p style="font-size:14px;color:#334155;line-height:1.7;margin:0 0 18px;">Đó là 5 template đầu tiên cần tạo. Sau khi có template → 70% inbox tự xử lý.</p>
    ${highlight('Module 2 sẽ hướng dẫn anh/chị tạo toàn bộ hệ thống này — từng bước, có template sẵn.')}
    <p style="font-size:14px;font-weight:700;color:#0F172A;margin:16px 0 0;">Hồ Sỹ Anh</p>
    <p style="font-size:12px;color:#94A3B8;margin:6px 0 0;font-style:italic;">P.S. Doanh nghiệp anh/chị ngành gì? Reply để tôi gợi ý quy trình AI hóa phù hợp nhất.</p>`;
  return { subject, html: htmlWrapper(body, preview, email) };
}

function email3({ name, email }) {
  const subject = `47 tin nhắn/sáng → 14 tin. Đây là cách làm (copy được ngay)`;
  const preview = 'Quy trình CSKH AI hóa 3 bước — không cần code, không cần tool trả phí.';
  const body = `
    <p style="font-size:14px;color:#475569;margin:0 0 16px;">Chào ${name},</p>
    <h1 style="font-size:22px;font-weight:800;color:#0F172A;margin:0 0 14px;">Giải pháp 3 bước — không cần code</h1>
    <p style="font-size:14px;color:#334155;margin:0 0 16px;"><strong>Bài toán:</strong> 40–60 tin/ngày, 70% câu hỏi giống nhau. Nhân viên mất 1–2 tiếng trả lời thủ công.</p>
    <div style="padding:16px;background:#F8FAFC;border-radius:10px;border:1px solid #E2E8F0;margin-bottom:12px;">
      <p style="margin:0 0 6px;font-weight:700;color:#0F172A;font-size:14px;">Bước 1 — Liệt kê 10 câu hỏi thường gặp</p>
      <p style="margin:0;font-size:13px;color:#475569;">Mở inbox 30 ngày → đếm câu nào xuất hiện nhiều nhất.</p>
    </div>
    <div style="padding:16px;background:#F8FAFC;border-radius:10px;border:1px solid #E2E8F0;margin-bottom:12px;">
      <p style="margin:0 0 8px;font-weight:700;color:#0F172A;font-size:14px;">Bước 2 — Dán vào ChatGPT</p>
      <div style="background:#0F172A;border-radius:6px;padding:12px;font-family:monospace;font-size:12px;color:#94A3B8;line-height:1.6;">"Tôi là chủ [shop tên]. Viết 10 mẫu trả lời thân thiện cho: [dán câu hỏi]. Tone: ấm áp, emoji nhẹ, kết thúc bằng CTA."</div>
    </div>
    <div style="padding:16px;background:#F8FAFC;border-radius:10px;border:1px solid #E2E8F0;margin-bottom:16px;">
      <p style="margin:0 0 6px;font-weight:700;color:#0F172A;font-size:14px;">Bước 3 — Lưu vào Quick Reply</p>
      <p style="margin:0;font-size:13px;color:#475569;">Facebook/Zalo/Instagram đều có tính năng này (miễn phí). Nhân viên gõ /gia → template bắn ra.</p>
    </div>
    <div style="background:#F0FDF4;border-radius:10px;padding:14px 16px;margin-bottom:16px;">
      <p style="margin:0 0 6px;font-weight:700;color:#166534;font-size:14px;">📊 Kết quả tại Khata:</p>
      <p style="margin:0 0 4px;font-size:13px;color:#166534;">✓ Inbox thủ công giảm <strong>65%</strong></p>
      <p style="margin:0;font-size:13px;color:#166534;">✓ CSKH mỗi sáng: từ 90 phút → <strong>25 phút</strong></p>
    </div>
    ${highlight('🎯 Thử ngay hôm nay — mất 15 phút, có template dùng ngày mai.')}
    <p style="font-size:14px;font-weight:700;color:#0F172A;margin:16px 0 0;">Hồ Sỹ Anh</p>`;
  return { subject, html: htmlWrapper(body, preview, email) };
}

function email4({ name, email }) {
  const subject = `Chị H.T. giảm từ 47 tin/sáng xuống 14 — trong tuần đầu tiên`;
  const preview = 'Case study thật: chủ chuỗi spa TP.HCM + AI = tiết kiệm 20 giờ/tuần.';
  const body = `
    <p style="font-size:14px;color:#475569;margin:0 0 16px;">Chào ${name},</p>
    <h1 style="font-size:22px;font-weight:800;color:#0F172A;margin:0 0 14px;">Hôm nay tôi giới thiệu chị H.T.</h1>
    <div style="background:#F8FAFC;border-radius:10px;padding:18px;margin-bottom:16px;border:1px solid #E2E8F0;">
      <p style="margin:0 0 10px;font-size:14px;color:#334155;font-style:italic;">"Tôi không tin AI làm được cho ngành spa — khách của tôi cần cảm giác cá nhân."</p>
      <p style="margin:0;font-size:12px;color:#64748B;">— Chị H.T., Chủ chuỗi spa · TP.HCM</p>
    </div>
    <p style="font-size:14px;color:#334155;line-height:1.7;margin:0 0 14px;">Tôi chỉ nói: <em>"Thử Module 2 trước. Không thấy kết quả trong tuần đầu — hoàn tiền ngay."</em></p>
    <div style="background:#F0FDF4;border-radius:10px;padding:16px;margin-bottom:16px;">
      <p style="margin:0 0 8px;font-weight:700;color:#166534;font-size:14px;">📊 Kết quả sau 7 ngày:</p>
      <p style="margin:0 0 4px;font-size:14px;color:#166534;">✓ Inbox thủ công: <strong>từ 47 → 14 tin/sáng</strong></p>
      <p style="margin:0 0 8px;font-size:14px;color:#166534;">✓ Thời gian CSKH: <strong>từ 90 phút → 25 phút</strong></p>
      <p style="margin:0;font-size:13px;color:#166534;font-style:italic;">"Tôi không ngờ kết quả lại nhanh đến vậy." — Chị H.T.</p>
    </div>
    ${highlight('💡 AI không thay thế cảm giác cá nhân hóa — nó xử lý câu hỏi lặp lại để team tập trung vào khách cần chăm sóc thật sự.')}
    <p style="font-size:14px;color:#334155;margin:14px 0 18px;">Anh/chị đã tiến đến đâu rồi? <strong>Reply email này</strong> — tôi đọc từng phản hồi.</p>
    <p style="font-size:14px;font-weight:700;color:#0F172A;margin:0;">Hồ Sỹ Anh</p>`;
  return { subject, html: htmlWrapper(body, preview, email) };
}

function email5({ name, planName, courseLink, email }) {
  const hasStrategyCall = planName === 'BOSS' || planName === 'VIP';
  const subject = `Check-in Ngày 7 — anh/chị đang ở đâu? Tôi có thể giúp gì?`;
  const preview = '7 ngày rồi — tiếp tục hay cần hỗ trợ? Tôi đọc từng reply.';
  const body = `
    <p style="font-size:14px;color:#475569;margin:0 0 16px;">Chào ${name},</p>
    <h1 style="font-size:22px;font-weight:800;color:#0F172A;margin:0 0 8px;">Đã 7 ngày rồi! 🎉</h1>
    <p style="font-size:14px;color:#64748B;margin:0 0 18px;">Chuỗi onboarding đã hoàn tất. Anh/chị đang ở đâu trong hành trình?</p>
    <div style="border:1px solid #E2E8F0;border-radius:10px;padding:16px;margin-bottom:14px;">
      <p style="margin:0 0 8px;font-weight:700;color:#0F172A;font-size:14px;">Anh/chị đang ở đâu?</p>
      <p style="margin:0 0 6px;font-size:14px;color:#334155;"><strong>(A)</strong> Đã xem Module 1 → đang làm Module 2 ✅</p>
      <p style="margin:0 0 6px;font-size:14px;color:#334155;"><strong>(B)</strong> Chưa bắt đầu vì bận — cần 30 phút cuối tuần này</p>
      <p style="margin:0;font-size:14px;color:#334155;"><strong>(C)</strong> Gặp khó khăn → <strong>reply email này</strong>, tôi hỗ trợ trực tiếp</p>
    </div>
    ${btn('🚀 Tiếp Tục Khóa Học →', courseLink)}
    ${divider()}
    <p style="font-size:14px;font-weight:700;color:#0F172A;margin:0 0 8px;">Dùng SME AI Club hiệu quả:</p>
    <p style="font-size:13px;color:#475569;margin:0 0 4px;">① Đăng câu hỏi cụ thể: "Tôi đang làm X, gặp vấn đề Y, đã thử Z"</p>
    <p style="font-size:13px;color:#475569;margin:0 0 4px;">② Share SOP vừa viết → nhận peer review</p>
    <p style="font-size:13px;color:#475569;margin:0 0 16px;">③ Tham gia Q&A live 2 lần/tháng — đặt câu hỏi trước</p>
    ${hasStrategyCall ? highlight('⚡ <strong>Strategy Call 1:1 của anh/chị:</strong> Nhắn Zalo <strong>0918 303 039</strong> để đặt lịch với tôi trực tiếp.') : ''}
    <p style="font-size:14px;font-weight:700;color:#0F172A;margin:16px 0 0;">Hồ Sỹ Anh</p>
    <p style="font-size:12px;color:#94A3B8;margin:6px 0 0;font-style:italic;">P.S. Sau hôm nay tôi vẫn gửi tips AI hóa hàng tuần. Anh/chị muốn nhận thêm chủ đề nào nhất?</p>`;
  return { subject, html: htmlWrapper(body, preview, email) };
}

// ═══════════════════════════════════════════════════════════
// ABANDONED CART SEQUENCE (AC#1 → AC#3) — Chưa thanh toán
// ═══════════════════════════════════════════════════════════

function emailAC1({ name, plan, planLabel, email }) {
  const subject = `🎁 Tặng anh/chị checklist này — dùng được ngay hôm nay`;
  const preview = '15 quy trình SME có thể AI hóa ngay + nhắc nhỏ về đăng ký của anh/chị.';
  const body = `
    <p style="font-size:14px;color:#475569;margin:0 0 14px;">Chào ${name},</p>
    <p style="font-size:14px;color:#334155;line-height:1.7;margin:0 0 14px;">Hôm qua anh/chị đã đăng ký AI BOSS SYSTEM — thanh toán vẫn đang chờ xác minh.</p>
    <p style="font-size:14px;color:#334155;margin:0 0 16px;">Trong lúc đó, tôi muốn <strong>tặng anh/chị một tài liệu miễn phí</strong> — dùng được ngay, không cần học khóa học.</p>
    <div style="background:linear-gradient(135deg,#EFF6FF,#F5F3FF);border-radius:12px;padding:20px 22px;text-align:center;margin-bottom:16px;border:2px solid #BFDBFE;">
      <div style="font-size:36px;margin-bottom:8px;">🎁</div>
      <h2 style="font-size:17px;font-weight:800;color:#1E40AF;margin:0 0 6px;">Checklist 15 Quy Trình SME</h2>
      <p style="font-size:13px;color:#3B82F6;margin:0 0 14px;">Có Thể AI Hóa Ngay Hôm Nay — Tiết Kiệm 3–5 Giờ/Ngày</p>
      ${btn('📥 Tải Checklist Miễn Phí →', checklistUrl(), '#1D4ED8')}
      <p style="font-size:11px;color:#93C5FD;margin:0;">PDF 1 trang · In được · Không cần đăng ký thêm</p>
    </div>
    ${highlight('💡 <strong>Cách dùng:</strong> Đánh dấu những việc đang làm thủ công. Check 6+ ô = đang lãng phí ít nhất <strong>15–25 giờ/tuần</strong>. Đây là preview nhỏ của những gì anh/chị giải quyết triệt để trong khóa học.')}
    ${divider()}
    <p style="font-size:13px;color:#64748B;margin:0 0 10px;">Nếu anh/chị đã chuyển khoản nhưng chưa thấy xác nhận → gửi bill về Zalo <strong>0918 303 039</strong>.</p>
    <p style="font-size:13px;color:#64748B;margin:0 0 14px;">Nếu chưa chuyển:</p>
    ${btn('Hoàn Tất Đăng Ký ' + planLabel + ' →', paymentUrl(), '#7C3AED')}
    <p style="font-size:14px;font-weight:700;color:#0F172A;margin:0;">Hồ Sỹ Anh</p>
    <p style="font-size:12px;color:#94A3B8;margin:6px 0 0;font-style:italic;">P.S. Checklist này là của anh/chị — dù đăng ký hay không, tôi tặng thật lòng.</p>`;
  return { subject, html: htmlWrapper(body, preview, email) };
}

function emailAC2({ name, plan, planLabel, email }) {
  const subject = `Chị H.T. dùng checklist này → 47 tin/sáng xuống còn 14 (trong tuần đầu)`;
  const preview = 'Kết quả thật từ chủ chuỗi spa TP.HCM. Còn vài suất Early Bird.';
  const body = `
    <p style="font-size:14px;color:#475569;margin:0 0 14px;">Chào ${name},</p>
    <p style="font-size:14px;color:#334155;margin:0 0 14px;">Hy vọng anh/chị đã xem checklist tôi gửi hôm qua.</p>
    <p style="font-size:14px;color:#334155;margin:0 0 16px;">Hôm nay tôi muốn kể về <strong>chị H.T.</strong> — chủ chuỗi spa TP.HCM.</p>
    <div style="background:#F8FAFC;border-radius:10px;padding:16px;margin-bottom:14px;border-left:4px solid #7C3AED;">
      <p style="margin:0 0 8px;font-size:14px;color:#334155;font-style:italic;">"Tôi không tin AI làm được cho ngành spa — khách cần cảm giác cá nhân hóa."</p>
    </div>
    <p style="font-size:14px;color:#334155;margin:0 0 14px;">Kết quả sau <strong>7 ngày</strong> áp dụng Module 2:</p>
    <div style="background:#F0FDF4;border-radius:10px;padding:16px;margin-bottom:16px;">
      <p style="margin:0 0 4px;font-size:14px;color:#166534;">✓ Inbox thủ công: <strong>từ 47 → 14 tin/sáng</strong></p>
      <p style="margin:0 0 8px;font-size:14px;color:#166534;">✓ Thời gian CSKH tiết kiệm: <strong>hơn 2 tiếng/ngày</strong></p>
      <p style="margin:0;font-size:13px;color:#166534;font-style:italic;">"Tôi không ngờ kết quả lại nhanh đến vậy."</p>
    </div>
    <p style="font-size:14px;color:#334155;line-height:1.7;margin:0 0 14px;">Checklist tôi tặng anh/chị là <strong>preview nhỏ</strong>. Trong AI BOSS SYSTEM, anh/chị có đầy đủ: 20 template viết sẵn, script tư vấn chuẩn, SOP 15 quy trình + 5 module còn lại.</p>
    <div style="background:#FFF7ED;border-radius:10px;padding:14px 16px;margin-bottom:16px;border:1px solid #FED7AA;">
      <p style="margin:0 0 4px;font-weight:700;color:#9A3412;font-size:14px;">⚠️ Còn vài suất Early Bird</p>
      <p style="margin:0;font-size:13px;color:#C2410C;">Giá 4.990.000₫ → sau khi đủ 50 người sẽ về 7.990.000₫</p>
    </div>
    ${btn('🔥 Hoàn Tất Đăng Ký ' + planLabel + ' →', paymentUrl())}
    <p style="font-size:14px;font-weight:700;color:#0F172A;margin:0;">Hồ Sỹ Anh</p>
    <p style="font-size:12px;color:#94A3B8;margin:6px 0 0;font-style:italic;">P.S. Anh/chị có câu hỏi nào về khóa học trước khi quyết định? Reply email này — tôi đọc từng email.</p>`;
  return { subject, html: htmlWrapper(body, preview, email) };
}

function emailAC3({ name, plan, planLabel, email }) {
  const subject = `Đây là email cuối tôi gửi — và tôi tôn trọng quyết định của anh/chị`;
  const preview = 'Dù thế nào, checklist vẫn là của anh/chị mãi mãi.';
  const body = `
    <p style="font-size:14px;color:#475569;margin:0 0 14px;">Chào ${name},</p>
    <p style="font-size:14px;color:#334155;line-height:1.7;margin:0 0 14px;">Đây là email cuối tôi gửi về <strong>AI BOSS SYSTEM</strong>.</p>
    <p style="font-size:15px;font-weight:700;color:#0F172A;margin:0 0 8px;">Tôi hiểu — mỗi người có thời điểm phù hợp riêng.</p>
    <p style="font-size:14px;color:#334155;line-height:1.7;margin:0 0 16px;">Có thể anh/chị đang bận. Có thể chưa phải lúc. Có thể có điều gì đó chưa rõ. Tất cả đều hoàn toàn bình thường.</p>
    ${divider()}
    <p style="font-size:14px;color:#334155;margin:0 0 6px;">Nếu anh/chị <strong>muốn tham gia</strong> trước khi hết suất Early Bird:</p>
    ${btn('Hoàn Tất Đăng Ký ' + planLabel + ' →', paymentUrl())}
    <p style="font-size:12px;color:#94A3B8;text-align:center;margin:-12px 0 16px;">Bảo đảm hoàn tiền 30 ngày · Không rủi ro</p>
    ${divider()}
    <p style="font-size:14px;color:#334155;line-height:1.7;margin:0 0 12px;">Nếu anh/chị <strong>chưa sẵn sàng lúc này</strong> — hoàn toàn không sao.</p>
    <p style="font-size:14px;color:#334155;line-height:1.7;margin:0 0 12px;">Anh/chị giữ lại checklist tôi tặng — <strong>miễn phí mãi mãi, không điều kiện.</strong></p>
    <p style="font-size:14px;color:#334155;line-height:1.7;margin:0 0 18px;">Và nếu sau này anh/chị muốn quay lại — tôi vẫn ở đây.</p>
    <p style="font-size:14px;color:#334155;line-height:1.7;margin:0 0 20px;">Cảm ơn anh/chị đã quan tâm. Tôi chúc anh/chị xây dựng doanh nghiệp thành công theo cách của mình.</p>
    <p style="font-size:14px;font-weight:700;color:#0F172A;margin:0;">Hồ Sỹ Anh</p>
    <p style="font-size:12px;color:#64748B;margin:6px 0 0;">Chủ DN Khata · Founder AI BOSS SYSTEM</p>`;
  return { subject, html: htmlWrapper(body, preview, email) };
}

// ═══════════════════════════════════════════════════════════
// Exports
// ═══════════════════════════════════════════════════════════
module.exports = {
  // Onboarding sequence (post-payment)
  getEmail: (num, data) => {
    switch (num) {
      case 0: return email0(data);
      case 1: return email1(data);
      case 2: return email2(data);
      case 3: return email3(data);
      case 4: return email4(data);
      case 5: return email5(data);
      default: return null;
    }
  },
  OB_SCHEDULE: [
    { emailNum: 2, daysAfter: 1 },
    { emailNum: 3, daysAfter: 3 },
    { emailNum: 4, daysAfter: 5 },
    { emailNum: 5, daysAfter: 7 },
  ],

  // Abandoned cart sequence (pre-payment)
  getACEmail: (num, data) => {
    switch (num) {
      case 1: return emailAC1(data);
      case 2: return emailAC2(data);
      case 3: return emailAC3(data);
      default: return null;
    }
  },
  AC_SCHEDULE: [
    { emailNum: 1, daysAfter: 1 },
    { emailNum: 2, daysAfter: 3 },
    { emailNum: 3, daysAfter: 5 },
  ],

  // Keep backward compat
  EMAIL_SCHEDULE: [
    { emailNum: 2, daysAfter: 1 },
    { emailNum: 3, daysAfter: 3 },
    { emailNum: 4, daysAfter: 5 },
    { emailNum: 5, daysAfter: 7 },
  ],
};

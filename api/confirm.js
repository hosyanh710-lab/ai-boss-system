// Vercel Serverless Function — Admin xác nhận thanh toán
// GET /api/confirm?token=TOKEN&email=X&name=X&phone=X&plan=boss&planLabel=4.990.000%E2%82%AB&orderId=X&telegram=X
//
// Khi admin click link này từ Telegram:
//   1. Gửi Email #1 ngay lập tức (welcome + course access)
//   2. Lên lịch Email #2 → +1 ngày, #3 → +3 ngày, #4 → +5 ngày, #5 → +7 ngày
//   3. Gửi Telegram cho khách (link nhóm + link khóa học)
//   4. Thông báo admin: "✅ Đã xác nhận"
//
// KHÔNG cần database, KHÔNG cần cron job.
// Resend tự quản lý lịch gửi email.

const https = require('https');
const { getEmail, EMAIL_SCHEDULE } = require('./email-templates');

const COURSE_LINKS = {
  starter: 'https://t.me/+MQ_ugnQPINcyNTc1',
  boss:    'https://t.me/+8nY7V6gmv9RjYjBl',
  vip:     'https://t.me/+AFeLlegMOu43ZDc9',
};

// ── Resend: gửi email (có thể lên lịch) ──────────────────────
async function sendEmail(to, subject, html, scheduledAt = null) {
  const RESEND_KEY = process.env.RESEND_API_KEY;
  const FROM_EMAIL = process.env.FROM_EMAIL || 'AI BOSS SYSTEM <onboarding@resend.dev>';

  if (!RESEND_KEY) {
    console.warn('RESEND_API_KEY chưa được cấu hình');
    return { ok: false, reason: 'no_resend_key' };
  }

  const body = { from: FROM_EMAIL, to: [to], subject, html };
  if (scheduledAt) body.scheduled_at = scheduledAt; // Resend scheduled delivery

  const payload = JSON.stringify(body);

  return new Promise((resolve) => {
    const req = https.request({
      hostname: 'api.resend.com',
      path: '/emails',
      method: 'POST',
      headers: {
        Authorization: `Bearer ${RESEND_KEY}`,
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(payload),
      },
    }, (res) => {
      const chunks = [];
      res.on('data', c => chunks.push(c));
      res.on('end', () => {
        try {
          const data = JSON.parse(Buffer.concat(chunks).toString());
          resolve({ ok: res.statusCode === 200 || res.statusCode === 201, data, status: res.statusCode });
        } catch { resolve({ ok: false, reason: 'parse_error' }); }
      });
    });
    req.on('error', e => resolve({ ok: false, reason: e.message }));
    req.write(payload);
    req.end();
  });
}

// ── Telegram request ──────────────────────────────────────────
function tgRequest(token, path, body) {
  return new Promise((resolve) => {
    const payload = JSON.stringify(body);
    const req = https.request({
      hostname: 'api.telegram.org',
      path: `/bot${token}${path}`,
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(payload) },
    }, (res) => {
      const chunks = [];
      res.on('data', c => chunks.push(c));
      res.on('end', () => {
        try { resolve(JSON.parse(Buffer.concat(chunks).toString())); }
        catch { resolve({ ok: false }); }
      });
    });
    req.on('error', () => resolve({ ok: false }));
    req.write(payload);
    req.end();
  });
}

// ── Gửi Telegram cho khách ────────────────────────────────────
async function notifyCustomerViaTelegram(botToken, adminChat, telegramUsername, name, planKey) {
  if (!telegramUsername || !botToken) return false;
  const username = telegramUsername.replace('@', '').trim();
  if (!username) return false;

  const chatData = await tgRequest(botToken, '/getChat', { chat_id: '@' + username });

  if (!chatData.ok) {
    // Báo admin giao thủ công
    await tgRequest(botToken, '/sendMessage', {
      chat_id: adminChat,
      text: `⚠️ Khách <b>${name}</b> chưa /start @AIBossNotifyBot.\n`
          + `Telegram: @${username}\n`
          + `→ Gửi link khóa học thủ công!`,
      parse_mode: 'HTML',
    });
    return false;
  }

  const courseLink = COURSE_LINKS[planKey] || COURSE_LINKS.boss;
  const msg = `🎉 Chào <b>${name}</b>!\n\n`
    + `Thanh toán đã được <b>xác nhận</b> 🎊\n\n`
    + `📚 <b>Link truy cập khóa học:</b>\n👉 ${courseLink}\n\n`
    + `📧 Email hướng dẫn đã gửi vào hộp thư của bạn.\n`
    + `💬 Nhắn tôi qua Zalo <b>0918 303 039</b> để vào nhóm SME AI Club.\n\n`
    + `Chúc bạn học tốt! 🚀\n— Hồ Sỹ Anh`;

  await tgRequest(botToken, '/sendMessage', {
    chat_id: chatData.result.id,
    text: msg,
    parse_mode: 'HTML',
  });
  return true;
}

// ── Main handler ──────────────────────────────────────────────
module.exports = async function handler(req, res) {
  const BOT_TOKEN   = process.env.TELEGRAM_BOT_TOKEN;
  const ADMIN_CHAT  = process.env.TELEGRAM_ADMIN_CHAT;
  const ADMIN_TOKEN = process.env.ADMIN_CONFIRM_TOKEN;

  // Lấy params từ GET hoặc POST
  const params = req.method === 'GET' ? req.query : (req.body || {});
  const { token, email, name, phone, plan, planLabel, orderId, telegram } = params;

  // Xác thực admin token
  if (!ADMIN_TOKEN || token !== ADMIN_TOKEN) {
    res.setHeader('Content-Type', 'text/html; charset=utf-8');
    return res.status(401).send(errorPage('Token không hợp lệ hoặc đã hết hạn.'));
  }

  // Validate
  if (!email || !name || !plan || !orderId) {
    res.setHeader('Content-Type', 'text/html; charset=utf-8');
    return res.status(400).send(errorPage('Thiếu thông tin. Cần: email, name, plan, orderId.'));
  }

  const planKey    = plan.toLowerCase();
  const planName   = plan.toUpperCase();
  const courseLink = COURSE_LINKS[planKey] || COURSE_LINKS.boss;
  const now        = new Date();

  const results = {
    email1: false,
    scheduledEmails: [],
    telegram: false,
  };

  // ── 1. Gửi Email #1 ngay lập tức ─────────────────────────
  try {
    const tpl = getEmail(1, { name, planName, planLabel: planLabel || '', courseLink, orderId });
    const r = await sendEmail(email, tpl.subject, tpl.html);
    results.email1 = r.ok;
    console.log(`Email #1 → ${email}: ${r.ok ? 'OK' : 'FAIL'} (${r.reason || r.status || ''})`);
  } catch (e) {
    console.error('Email #1 error:', e.message);
  }

  // ── 2. Lên lịch Email #2 → #5 ────────────────────────────
  for (const { emailNum, daysAfter } of EMAIL_SCHEDULE) {
    try {
      // Tính thời điểm gửi: confirmedAt + daysAfter ngày, lúc 9:00 SA giờ VN (UTC+7)
      const scheduledDate = new Date(now);
      scheduledDate.setDate(scheduledDate.getDate() + daysAfter);
      scheduledDate.setUTCHours(2, 0, 0, 0); // 9:00 SA VN = 02:00 UTC
      const scheduledAt = scheduledDate.toISOString();

      const tpl = getEmail(emailNum, { name, planName, planLabel: planLabel || '', courseLink, orderId });
      const r = await sendEmail(email, tpl.subject, tpl.html, scheduledAt);

      results.scheduledEmails.push({
        emailNum,
        scheduledAt: scheduledDate.toLocaleString('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh' }),
        ok: r.ok,
      });
      console.log(`Email #${emailNum} scheduled ${scheduledAt}: ${r.ok ? 'OK' : 'FAIL'}`);
    } catch (e) {
      console.error(`Email #${emailNum} schedule error:`, e.message);
      results.scheduledEmails.push({ emailNum, ok: false, error: e.message });
    }
  }

  // ── 3. Gửi Telegram cho khách ─────────────────────────────
  if (BOT_TOKEN && telegram) {
    results.telegram = await notifyCustomerViaTelegram(BOT_TOKEN, ADMIN_CHAT, telegram, name, planKey);
  }

  // ── 4. Thông báo admin trên Telegram ──────────────────────
  if (BOT_TOKEN && ADMIN_CHAT) {
    const nowVN = now.toLocaleString('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh' });
    const scheduleLines = results.scheduledEmails
      .map(s => `• Email #${s.emailNum} → ${s.scheduledAt}: ${s.ok ? '✅' : '❌'}`)
      .join('\n');

    await tgRequest(BOT_TOKEN, '/sendMessage', {
      chat_id: ADMIN_CHAT,
      text: `✅ <b>XÁC NHẬN HOÀN TẤT</b>\n\n`
          + `👤 Khách: <b>${name}</b> (${email})\n`
          + `📦 Gói: <b>${planName}</b>\n`
          + `🔖 Đơn: <code>${orderId}</code>\n`
          + `🕐 Thời gian: ${nowVN}\n\n`
          + `📨 Email #1: ${results.email1 ? '✅ Đã gửi' : '❌ Lỗi — kiểm tra RESEND_API_KEY'}\n`
          + `📅 Lịch email tiếp theo:\n${scheduleLines}\n\n`
          + `📱 Telegram khách: ${results.telegram ? '✅ Đã gửi' : telegram ? '⚠️ Lỗi' : '⚠️ Chưa điền'}`,
      parse_mode: 'HTML',
    });
  }

  // ── 5. Trả về trang xác nhận cho admin ───────────────────
  res.setHeader('Content-Type', 'text/html; charset=utf-8');
  res.status(200).send(successPage(name, email, planName, results));
};

// ── HTML pages ────────────────────────────────────────────────
function successPage(name, email, planName, results) {
  const rows = results.scheduledEmails.map(s =>
    `<div class="row"><span>Email #${s.emailNum}</span><span class="${s.ok ? 'ok' : 'err'}">${s.ok ? '✅ Lên lịch' : '❌ Lỗi'}</span><span class="date">${s.scheduledAt || ''}</span></div>`
  ).join('');

  return `<!DOCTYPE html><html lang="vi">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Xác nhận thành công</title>
<style>
  body{font-family:system-ui,sans-serif;background:#0F172A;color:#fff;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0;padding:16px}
  .card{background:#1E293B;border-radius:16px;padding:36px;max-width:500px;width:100%;text-align:center;border:1px solid rgba(255,255,255,.1)}
  .icon{font-size:56px;margin-bottom:12px}
  h1{font-size:22px;margin:0 0 6px;color:#fff}
  .sub{color:#94A3B8;font-size:14px;margin-bottom:24px}
  .table{background:#0F172A;border-radius:10px;padding:16px;text-align:left;margin:0 0 20px}
  .row{display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid rgba(255,255,255,.07);font-size:13px;gap:8px}
  .row:last-child{border:none}
  .date{color:#64748B;font-size:11px}
  .ok{color:#4ADE80}.err{color:#F87171}
  .note{color:#64748B;font-size:12px;margin-top:16px;line-height:1.6}
</style></head>
<body><div class="card">
  <div class="icon">✅</div>
  <h1>Xác nhận thành công!</h1>
  <div class="sub">Đơn hàng của <strong>${name}</strong> (${email}) — Gói ${planName}</div>
  <div class="table">
    <div class="row" style="font-weight:700;color:#fff"><span>Email</span><span>Trạng thái</span><span class="date">Lịch gửi (VN)</span></div>
    <div class="row"><span>Email #1 — Welcome</span><span class="${results.email1 ? 'ok' : 'err'}">${results.email1 ? '✅ Đã gửi' : '❌ Lỗi'}</span><span class="date">Ngay bây giờ</span></div>
    ${rows}
  </div>
  <div class="note">Resend sẽ tự động giao email theo lịch.<br>Không cần làm gì thêm.</div>
</div></body></html>`;
}

function errorPage(msg) {
  return `<!DOCTYPE html><html lang="vi"><head><meta charset="UTF-8"><title>Lỗi</title>
<style>body{font-family:system-ui,sans-serif;background:#0F172A;color:#fff;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0}
.card{background:#1E293B;border-radius:16px;padding:40px;text-align:center;border:1px solid rgba(255,0,0,.3)}</style></head>
<body><div class="card"><div style="font-size:48px">❌</div><h2>${msg}</h2></div></body></html>`;
}

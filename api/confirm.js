// Vercel Serverless Function — Admin xác nhận thanh toán
// GET /api/confirm?token=TOKEN&email=X&name=X&phone=X&plan=boss&planLabel=4.990.000%E2%82%AB&orderId=X&telegram=X
//
// Khi admin click link từ Telegram:
//   1. Gửi Email #1 ngay (welcome + course access) qua Gmail SMTP
//   2. Gửi Telegram cho khách (link nhóm + link khóa học)
//   3. Thông báo admin: "✅ Đã xác nhận"
//   4. Email #2–5 gửi theo sequence (xem send-sequence.js + Vercel Cron)

const https = require('https');
const { getEmail, EMAIL_SCHEDULE } = require('./email-templates');
const { sendMail } = require('./mailer');

const COURSE_LINKS = {
  starter: 'https://t.me/+MQ_ugnQPINcyNTc1',
  boss:    'https://t.me/+8nY7V6gmv9RjYjBl',
  vip:     'https://t.me/+AFeLlegMOu43ZDc9',
};

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
    await tgRequest(botToken, '/sendMessage', {
      chat_id: adminChat,
      text: `⚠️ Khách <b>${name}</b> chưa /start @AIBossNotifyBot.\nTelegram: @${username}\n→ Giao link thủ công!`,
      parse_mode: 'HTML',
    });
    return false;
  }

  const courseLink = COURSE_LINKS[planKey] || COURSE_LINKS.boss;
  const msg = `🎉 Chào <b>${name}</b>!\n\n`
    + `Thanh toán đã được <b>xác nhận</b> 🎊\n\n`
    + `📚 <b>Link truy cập khóa học:</b>\n👉 ${courseLink}\n\n`
    + `📧 Email hướng dẫn đã gửi vào hộp thư của bạn.\n`
    + `💬 Nhắn Zalo <b>0918 303 039</b> để vào nhóm SME AI Club.\n\n`
    + `Chúc bạn học tốt! 🚀\n— Hồ Sỹ Anh`;

  await tgRequest(botToken, '/sendMessage', { chat_id: chatData.result.id, text: msg, parse_mode: 'HTML' });
  return true;
}

// ── Lưu subscriber cho email sequence ────────────────────────
// Dùng Vercel Blob nếu có — bỏ qua nếu chưa cấu hình
async function saveSubscriber(data) {
  const token = process.env.BLOB_READ_WRITE_TOKEN;
  if (!token) {
    console.warn('[Confirm] BLOB_READ_WRITE_TOKEN chưa cấu hình — bỏ qua lưu subscriber');
    return false;
  }
  try {
    const key = `subscriber-${data.email.replace(/[^a-z0-9]/gi, '_')}.json`;
    const payload = JSON.stringify({ ...data, emailsSent: [0, 1], confirmedAt: new Date().toISOString() });
    const res = await fetch(`https://blob.vercel-storage.com/${key}`, {
      method: 'PUT',
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json', 'x-content-type': 'application/json' },
      body: payload,
    });
    return res.ok;
  } catch (e) {
    console.error('[Confirm] Blob save error:', e.message);
    return false;
  }
}

// ── Main handler ──────────────────────────────────────────────
module.exports = async function handler(req, res) {
  const BOT_TOKEN   = process.env.TELEGRAM_BOT_TOKEN;
  const ADMIN_CHAT  = process.env.TELEGRAM_ADMIN_CHAT;
  const ADMIN_TOKEN = process.env.ADMIN_CONFIRM_TOKEN;

  const params = req.method === 'GET' ? req.query : (req.body || {});
  const { token, email, name, phone, plan, planLabel, orderId, telegram } = params;

  // Xác thực admin token
  if (!ADMIN_TOKEN || token !== ADMIN_TOKEN) {
    res.setHeader('Content-Type', 'text/html; charset=utf-8');
    return res.status(401).send(errorPage('Token không hợp lệ.'));
  }
  if (!email || !name || !plan || !orderId) {
    res.setHeader('Content-Type', 'text/html; charset=utf-8');
    return res.status(400).send(errorPage('Thiếu thông tin: email, name, plan, orderId.'));
  }

  const planKey    = plan.toLowerCase();
  const planName   = plan.toUpperCase();
  const courseLink = COURSE_LINKS[planKey] || COURSE_LINKS.boss;
  const now        = new Date();

  const results = { email1: false, savedSubscriber: false, telegram: false };

  // 1. Gửi Email #1 ngay lập tức qua Gmail SMTP
  try {
    const tpl = getEmail(1, { name, planName, planLabel: planLabel || '', courseLink, orderId });
    const r = await sendMail(email, tpl.subject, tpl.html);
    results.email1 = r.ok;
  } catch (e) {
    console.error('Email #1 error:', e.message);
  }

  // 2. Lưu subscriber để cron job gửi Email #2–5
  results.savedSubscriber = await saveSubscriber({
    email, name, phone: phone || '', planKey, planName,
    planLabel: planLabel || '', orderId, telegram: telegram || '', courseLink,
  });

  // 3. Gửi Telegram cho khách
  if (BOT_TOKEN && telegram) {
    results.telegram = await notifyCustomerViaTelegram(BOT_TOKEN, ADMIN_CHAT, telegram, name, planKey);
  }

  // 4. Thông báo admin
  if (BOT_TOKEN && ADMIN_CHAT) {
    const nowVN = now.toLocaleString('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh' });
    await tgRequest(BOT_TOKEN, '/sendMessage', {
      chat_id: ADMIN_CHAT,
      text: `✅ <b>XÁC NHẬN HOÀN TẤT</b>\n\n`
          + `👤 Khách: <b>${name}</b> (${email})\n`
          + `📦 Gói: <b>${planName}</b>\n`
          + `🔖 Đơn: <code>${orderId}</code>\n`
          + `🕐 ${nowVN}\n\n`
          + `📨 Email #1: ${results.email1 ? '✅ Đã gửi' : '❌ Lỗi — kiểm tra GMAIL_USER/GMAIL_APP_PASS'}\n`
          + `💾 Subscriber: ${results.savedSubscriber ? '✅ Lưu → Email #2-5 sẽ tự gửi' : '⚠️ Chưa lưu (BLOB chưa cấu hình)'}\n`
          + `📱 Telegram: ${results.telegram ? '✅' : telegram ? '❌' : '⚠️ Chưa điền'}`,
      parse_mode: 'HTML',
    });
  }

  res.setHeader('Content-Type', 'text/html; charset=utf-8');
  res.status(200).send(successPage(name, email, planName, results));
};

// ── HTML pages ────────────────────────────────────────────────
function successPage(name, email, planName, results) {
  return `<!DOCTYPE html><html lang="vi">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Xác nhận thành công</title>
<style>body{font-family:system-ui,sans-serif;background:#0F172A;color:#fff;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0;padding:16px}
.card{background:#1E293B;border-radius:16px;padding:36px;max-width:480px;width:100%;text-align:center;border:1px solid rgba(255,255,255,.1)}
.icon{font-size:52px;margin-bottom:12px}h1{font-size:22px;margin:0 0 6px}
.sub{color:#94A3B8;font-size:14px;margin-bottom:20px}
.table{background:#0F172A;border-radius:10px;padding:16px;text-align:left;margin:0 0 16px}
.row{display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid rgba(255,255,255,.07);font-size:14px}
.row:last-child{border:none}.ok{color:#4ADE80}.err{color:#F87171}.warn{color:#FBBF24}</style></head>
<body><div class="card">
  <div class="icon">✅</div>
  <h1>Xác nhận thành công!</h1>
  <div class="sub"><strong>${name}</strong> (${email}) — Gói ${planName}</div>
  <div class="table">
    <div class="row"><span>Email #1 — Welcome</span><span class="${results.email1 ? 'ok' : 'err'}">${results.email1 ? '✅ Đã gửi' : '❌ Lỗi Gmail'}</span></div>
    <div class="row"><span>Email #2–5 sequence</span><span class="${results.savedSubscriber ? 'ok' : 'warn'}">${results.savedSubscriber ? '✅ Lưu → cron tự gửi' : '⚠️ Cần cấu hình Blob'}</span></div>
    <div class="row"><span>Telegram khách</span><span class="${results.telegram ? 'ok' : 'warn'}">${results.telegram ? '✅ Đã gửi' : '⚠️ Chưa gửi'}</span></div>
  </div>
</div></body></html>`;
}

function errorPage(msg) {
  return `<!DOCTYPE html><html lang="vi"><head><meta charset="UTF-8"><title>Lỗi</title>
<style>body{font-family:system-ui;background:#0F172A;color:#fff;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0}
.c{background:#1E293B;border-radius:16px;padding:40px;text-align:center}</style></head>
<body><div class="c"><div style="font-size:48px">❌</div><h2>${msg}</h2></div></body></html>`;
}

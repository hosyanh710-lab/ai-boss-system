// Vercel Serverless Function — Telegram Notifications
// POST /api/notify
// Body: { action: 'admin', name, phone, telegram, planName, planLabel, orderId, des }
//     | { action: 'customer', telegram, name, planKey, planName, planLabel }

const https = require('https');

const COURSE_LINKS = {
  starter: 'https://t.me/+MQ_ugnQPINcyNTc1',
  boss:    'https://t.me/+8nY7V6gmv9RjYjBl',
  vip:     'https://t.me/+AFeLlegMOu43ZDc9',
};

function telegramRequest(token, path, body) {
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

module.exports = async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  const BOT_TOKEN  = process.env.TELEGRAM_BOT_TOKEN;
  const ADMIN_CHAT = process.env.TELEGRAM_ADMIN_CHAT;

  if (!BOT_TOKEN || !ADMIN_CHAT) {
    return res.status(500).json({ error: 'Telegram not configured' });
  }

  const { action, name, phone, email, telegram, planKey, planName, planLabel, orderId, des } = req.body || {};
  const now = new Date().toLocaleString('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh' });
  const SITE_URL = process.env.SITE_URL || '';
  const ADMIN_TOKEN = process.env.ADMIN_CONFIRM_TOKEN || '';

  try {
    if (action === 'admin') {
      const tg = (telegram || '').replace('@', '').trim();

      // Build confirm link cho admin click để xác nhận thanh toán
      const confirmParams = new URLSearchParams({
        token: ADMIN_TOKEN,
        email: email || '',
        name: name || '',
        phone: phone || '',
        plan: planKey || 'boss',
        planLabel: planLabel || '',
        orderId: orderId || '',
        telegram: tg,
      });
      const confirmLink = SITE_URL
        ? `${SITE_URL}/api/confirm?${confirmParams}`
        : `(Cấu hình SITE_URL để tạo link xác nhận)`;

      const msg = '🎉 <b>ĐƠN HÀNG MỚI — AI BOSS SYSTEM</b>\n\n'
        + '🔖 Mã đơn: <code>' + (orderId || '-') + '</code>\n'
        + '👤 Khách: <b>' + (name || '-') + '</b>\n'
        + '📞 SĐT: ' + (phone || '-') + '\n'
        + (email ? '📧 Email: ' + email + '\n' : '')
        + (tg ? '📱 Telegram: @' + tg + '\n' : '📱 Telegram: Chưa điền\n')
        + '📦 Gói: <b>' + planName + ' — ' + planLabel + '</b>\n'
        + '🔖 Nội dung CK: <code>' + (des || '-') + '</code>\n'
        + '🕐 Thời gian: ' + now + '\n\n'
        + '─────────────────────\n'
        + '✅ <b>Sau khi xác nhận chuyển khoản:</b>\n'
        + '<a href="' + confirmLink + '">👉 CLICK ĐÂY ĐỂ XÁC NHẬN ĐƠN HÀNG</a>\n'
        + '(Hệ thống tự gửi email + Telegram cho khách)\n'
        + '─────────────────────';

      await telegramRequest(BOT_TOKEN, '/sendMessage', { chat_id: ADMIN_CHAT, text: msg, parse_mode: 'HTML' });
      return res.status(200).json({ ok: true });
    }

    if (action === 'customer') {
      const username = (telegram || '').replace('@', '').trim();
      if (!username) return res.status(200).json({ ok: false, reason: 'no_username' });

      const chatData = await telegramRequest(BOT_TOKEN, '/getChat', { chat_id: '@' + username });

      if (!chatData.ok) {
        await telegramRequest(BOT_TOKEN, '/sendMessage', {
          chat_id: ADMIN_CHAT,
          text: '⚠️ Khách <b>' + name + '</b> chưa /start bot.\n'
            + 'Telegram: @' + username + '\n'
            + 'Gói: ' + planName + '\n'
            + '→ Giao link thủ công!',
          parse_mode: 'HTML',
        });
        return res.status(200).json({ ok: false, reason: 'customer_not_started_bot' });
      }

      const courseLink = COURSE_LINKS[planKey] || COURSE_LINKS.boss;
      const accessCode = 'AIBOSS-' + Math.random().toString(36).substring(2, 8).toUpperCase();

      const msg = '🎉 Chào <b>' + name + '</b>!\n\n'
        + 'Cảm ơn bạn đã đăng ký <b>AI BOSS SYSTEM</b> — Gói ' + planName + '.\n\n'
        + '📚 <b>Link truy cập khóa học:</b>\n'
        + '👉 ' + courseLink + '\n\n'
        + '🔑 Mã truy cập: <code>' + accessCode + '</code>\n\n'
        + '📞 Hỗ trợ: Zalo <b>0918 303 039</b> (Hồ Sỹ Anh)\n\n'
        + 'Chúc bạn học tốt! 🚀';

      await telegramRequest(BOT_TOKEN, '/sendMessage', {
        chat_id: chatData.result.id,
        text: msg,
        parse_mode: 'HTML',
      });
      return res.status(200).json({ ok: true });
    }

    return res.status(400).json({ error: 'Unknown action' });
  } catch (err) {
    console.error('notify error:', err.message);
    return res.status(500).json({ error: 'Internal error' });
  }
};

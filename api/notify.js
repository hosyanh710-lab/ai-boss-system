// POST /api/notify
// action: 'admin' → thông báo admin + gửi Email #0 + lưu subscriber vào Blob
// action: 'customer' → gửi Telegram cho khách

const https = require('https');
const { getEmail }    = require('./email-templates');
const { sendMail }    = require('./mailer');
const { saveSubscriber, getSubscriber } = require('./blob');

const COURSE_LINKS = {
  starter: 'https://t.me/+MQ_ugnQPINcyNTc1',
  boss:    'https://t.me/+8nY7V6gmv9RjYjBl',
  vip:     'https://t.me/+AFeLlegMOu43ZDc9',
};

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

module.exports = async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  const BOT_TOKEN  = process.env.TELEGRAM_BOT_TOKEN;
  const ADMIN_CHAT = process.env.TELEGRAM_ADMIN_CHAT;

  if (!BOT_TOKEN || !ADMIN_CHAT) {
    return res.status(500).json({ error: 'Telegram not configured' });
  }

  const {
    action, name, phone, email, telegram,
    planKey, planName, planLabel, orderId, des,
  } = req.body || {};

  const now       = new Date().toLocaleString('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh' });
  const SITE_URL  = process.env.SITE_URL || '';
  const ADMIN_TK  = process.env.ADMIN_CONFIRM_TOKEN || '';

  try {
    // ── ACTION: admin ──────────────────────────────────────
    if (action === 'admin') {
      const tg = (telegram || '').replace('@', '').trim();

      // Confirm link cho admin
      const confirmParams = new URLSearchParams({
        token: ADMIN_TK, email: email || '', name: name || '',
        phone: phone || '', plan: planKey || 'boss',
        planLabel: planLabel || '', orderId: orderId || '', telegram: tg,
      });
      const confirmLink = SITE_URL
        ? `${SITE_URL}/api/confirm?${confirmParams}`
        : '(Cấu hình SITE_URL để có link xác nhận)';

      // Telegram → admin
      const msg = '🎉 <b>ĐƠN HÀNG MỚI — AI BOSS SYSTEM</b>\n\n'
        + `🔖 Mã đơn: <code>${orderId || '-'}</code>\n`
        + `👤 Khách: <b>${name || '-'}</b>\n`
        + `📞 SĐT: ${phone || '-'}\n`
        + (email ? `📧 Email: ${email}\n` : '')
        + (tg ? `📱 Telegram: @${tg}\n` : '📱 Telegram: Chưa điền\n')
        + `📦 Gói: <b>${planName} — ${planLabel}</b>\n`
        + `🔖 Nội dung CK: <code>${des || '-'}</code>\n`
        + `🕐 ${now}\n\n`
        + '─────────────────────\n'
        + '✅ <b>Sau khi xác nhận chuyển khoản:</b>\n'
        + `<a href="${confirmLink}">👉 CLICK ĐÂY ĐỂ XÁC NHẬN ĐƠN HÀNG</a>\n`
        + '(Hệ thống tự gửi email + Telegram cho khách)\n'
        + '─────────────────────';

      await tgRequest(BOT_TOKEN, '/sendMessage', { chat_id: ADMIN_CHAT, text: msg, parse_mode: 'HTML' });

      // Email #0 → khách (xác nhận đăng ký)
      if (email) {
        try {
          const tpl = getEmail(0, {
            name: name || 'Anh/Chị',
            planName: planName || '',
            planLabel: planLabel || '',
            orderId: orderId || '-',
            email,
          });
          if (tpl) {
            const r = await sendMail(email, tpl.subject, tpl.html);
            console.log(`[notify] Email #0 → ${email}: ${r.ok ? '✅' : '❌ ' + r.error}`);
          }
        } catch (e) { console.error('[notify] Email #0 error:', e.message); }
      }

      // Lưu subscriber vào Blob (status: pending)
      if (email) {
        try {
          const existing = await getSubscriber(email);
          if (!existing) {
            const tags = [
              planKey || 'boss',
              'pending_payment',
              'sme_owner',
              'source_landing',
            ];
            await saveSubscriber({
              email,
              name:        name || '',
              phone:       phone || '',
              plan:        planKey || 'boss',
              planName:    planName || '',
              planLabel:   planLabel || '',
              orderId:     orderId || '',
              telegram:    tg,
              courseLink:  COURSE_LINKS[planKey] || COURSE_LINKS.boss,
              status:      'pending',
              segment:     'abandoned_cart',
              tags,
              createdAt:   new Date().toISOString(),
              confirmedAt: null,
              unsubscribedAt: null,
              obEmailsSent:   [0],
              acEmailsSent:   [],
            });
            console.log(`[notify] Subscriber saved: ${email} | plan: ${planKey} | tags: ${tags.join(',')}`);
          }
        } catch (e) { console.error('[notify] Blob save error:', e.message); }
      }

      return res.status(200).json({ ok: true });
    }

    // ── ACTION: customer (Telegram delivery) ─────────────
    if (action === 'customer') {
      const username = (telegram || '').replace('@', '').trim();
      if (!username) return res.status(200).json({ ok: false, reason: 'no_username' });

      const chatData = await tgRequest(BOT_TOKEN, '/getChat', { chat_id: '@' + username });
      if (!chatData.ok) {
        await tgRequest(BOT_TOKEN, '/sendMessage', {
          chat_id: ADMIN_CHAT,
          text: `⚠️ Khách <b>${name}</b> chưa /start bot.\nTelegram: @${username}\n→ Giao link thủ công!`,
          parse_mode: 'HTML',
        });
        return res.status(200).json({ ok: false, reason: 'customer_not_started_bot' });
      }

      const courseLink  = COURSE_LINKS[planKey] || COURSE_LINKS.boss;
      const accessCode  = 'AIBOSS-' + Math.random().toString(36).substring(2, 8).toUpperCase();
      const tgMsg = `🎉 Chào <b>${name}</b>!\n\n`
        + `Thanh toán đã xác nhận 🎊\n\n`
        + `📚 <b>Link khóa học:</b>\n👉 ${courseLink}\n\n`
        + `🔑 Mã: <code>${accessCode}</code>\n\n`
        + `📞 Hỗ trợ: Zalo <b>0918 303 039</b>\n\nChúc học tốt! 🚀`;

      await tgRequest(BOT_TOKEN, '/sendMessage', { chat_id: chatData.result.id, text: tgMsg, parse_mode: 'HTML' });
      return res.status(200).json({ ok: true });
    }

    return res.status(400).json({ error: 'Unknown action' });
  } catch (err) {
    console.error('[notify] Error:', err.message);
    return res.status(500).json({ error: 'Internal error' });
  }
};

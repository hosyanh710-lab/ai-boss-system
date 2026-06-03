// Vercel Serverless Function — SePay Webhook
// POST /api/webhook

const https = require('https');

function sendTelegram(token, chatId, text) {
  return new Promise((resolve) => {
    const body = JSON.stringify({ chat_id: chatId, text, parse_mode: 'HTML' });
    const req = https.request({
      hostname: 'api.telegram.org',
      path: `/bot${token}/sendMessage`,
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(body) },
    }, resolve);
    req.on('error', resolve);
    req.write(body);
    req.end();
  });
}

module.exports = async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });
  res.status(200).json({ received: true });

  try {
    const data = req.body || {};
    if (data.transferType !== 'in' || !data.transferAmount) return;

    const BOT   = process.env.TELEGRAM_BOT_TOKEN;
    const ADMIN = process.env.TELEGRAM_ADMIN_CHAT;
    if (!BOT || !ADMIN) return;

    const amount  = Number(data.transferAmount).toLocaleString('vi-VN');
    const content = data.content || '(không có nội dung)';
    const time    = new Date().toLocaleString('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh' });
    const isOrder = content.toUpperCase().includes('AIBOSS');

    const msg = (isOrder ? '🎉' : '💰') + ' <b>TIỀN VÀO ACB</b>\n\n'
      + '💵 Số tiền: <b>' + amount + '₫</b>\n'
      + '📝 Nội dung: <code>' + content + '</code>\n'
      + '🕐 Thời gian: ' + time
      + (isOrder ? '\n\n✅ <b>ĐƠN AI BOSS — Giao hàng ngay!</b>' : '');

    await sendTelegram(BOT, ADMIN, msg);
  } catch (err) {
    console.error('Webhook error:', err.message);
  }
};

// Vercel Serverless Function — SePay Webhook Handler
// SePay gửi POST về đây khi có giao dịch ACB

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  // Trả 200 ngay để SePay không retry
  res.status(200).json({ received: true });

  try {
    const data = req.body;

    // Chỉ xử lý giao dịch tiền VÀO
    if (data.transferType !== 'in' || !data.transferAmount) return;

    const BOT_TOKEN  = process.env.TELEGRAM_BOT_TOKEN  || '8697943146:AAFVoIgms1-WDiNATe1MMfQ85wOa9xyFKqI';
    const ADMIN_CHAT = process.env.TELEGRAM_ADMIN_CHAT || '8528681036';

    const amount  = Number(data.transferAmount).toLocaleString('vi-VN');
    const content = data.content || data.description || '(không có nội dung)';
    const time    = new Date().toLocaleString('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh' });

    // Kiểm tra có phải đơn AI BOSS không
    const isAIBoss = content.toUpperCase().includes('AIBOSS');

    const msg = (isAIBoss ? '🎉' : '💰') + ' <b>TIỀN VÀO ACB</b>\n\n'
      + '💵 Số tiền: <b>' + amount + '₫</b>\n'
      + '📝 Nội dung: <code>' + content + '</code>\n'
      + '🏦 Ngân hàng: ' + (data.gateway || 'ACB') + '\n'
      + '🕐 Thời gian: ' + time + '\n'
      + (isAIBoss ? '\n✅ <b>Đơn AI BOSS SYSTEM — Giao hàng ngay!</b>' : '');

    // Gửi Telegram
    await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/sendMessage`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        chat_id:    ADMIN_CHAT,
        text:       msg,
        parse_mode: 'HTML',
      }),
    });

  } catch (err) {
    console.error('Webhook error:', err.message);
  }
}

// Gmail SMTP mailer — dùng chung cho notify.js và confirm.js
// Env vars cần thiết:
//   GMAIL_USER      = hosyanh159@gmail.com
//   GMAIL_APP_PASS  = xxxx xxxx xxxx xxxx  (App Password 16 ký tự)

const nodemailer = require('nodemailer');

let _transporter = null;

function getTransporter() {
  if (_transporter) return _transporter;

  const user = process.env.GMAIL_USER;
  const pass = process.env.GMAIL_APP_PASS;

  if (!user || !pass) {
    console.error('[Mailer] GMAIL_USER hoặc GMAIL_APP_PASS chưa được cấu hình');
    return null;
  }

  _transporter = nodemailer.createTransport({
    host: 'smtp.gmail.com',
    port: 587,
    secure: false, // STARTTLS
    auth: { user, pass },
    tls: { rejectUnauthorized: false },
  });

  return _transporter;
}

/**
 * Gửi email qua Gmail SMTP
 * @param {string} to      - Email người nhận
 * @param {string} subject - Tiêu đề
 * @param {string} html    - Nội dung HTML
 * @returns {Promise<{ok: boolean, error?: string}>}
 */
async function sendMail(to, subject, html) {
  const transporter = getTransporter();

  if (!transporter) {
    return { ok: false, error: 'Mailer not configured' };
  }

  if (!to) {
    return { ok: false, error: 'Missing recipient email' };
  }

  const fromName = process.env.FROM_NAME || 'AI BOSS SYSTEM';
  const fromUser = process.env.GMAIL_USER;

  try {
    console.log(`[Mailer] Đang gửi email tới: ${to} | Subject: ${subject}`);

    const info = await transporter.sendMail({
      from: `"${fromName}" <${fromUser}>`,
      to,
      subject,
      html,
    });

    console.log(`[Mailer] ✅ Gửi thành công → MessageId: ${info.messageId}`);
    return { ok: true, messageId: info.messageId };

  } catch (err) {
    console.error(`[Mailer] ❌ Lỗi gửi email tới ${to}:`, err.message);
    return { ok: false, error: err.message };
  }
}

module.exports = { sendMail };

// GET /api/unsubscribe?e=BASE64(email)
// Khách click link này trong email → cập nhật status unsubscribed

const { updateSubscriber } = require('./blob');

module.exports = async function handler(req, res) {
  const encoded = req.query?.e || '';
  if (!encoded) {
    return res.status(400).send(page('Thiếu thông tin', 'Link hủy đăng ký không hợp lệ.', false));
  }

  let email;
  try {
    email = Buffer.from(encoded, 'base64').toString('utf8');
    if (!email.includes('@')) throw new Error('invalid');
  } catch {
    return res.status(400).send(page('Không hợp lệ', 'Link hủy đăng ký đã hết hạn hoặc không đúng.', false));
  }

  await updateSubscriber(email, {
    status: 'unsubscribed',
    unsubscribedAt: new Date().toISOString(),
    tags: ['unsubscribed'],
  });

  console.log(`[Unsubscribe] ${email} đã hủy nhận email`);

  res.setHeader('Content-Type', 'text/html; charset=utf-8');
  return res.status(200).send(page(
    'Đã hủy đăng ký',
    `Địa chỉ <strong>${email}</strong> đã được xóa khỏi danh sách email của AI BOSS SYSTEM.<br><br>Anh/chị sẽ không nhận được email từ chúng tôi nữa.`,
    true
  ));
};

function page(title, message, success) {
  const icon = success ? '✅' : '❌';
  const color = success ? '#4ADE80' : '#F87171';
  return `<!DOCTYPE html><html lang="vi"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>${title} — AI BOSS SYSTEM</title>
<style>body{font-family:system-ui,sans-serif;background:#0F172A;color:#fff;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0;padding:16px}
.card{background:#1E293B;border-radius:16px;padding:40px;max-width:460px;width:100%;text-align:center;border:1px solid rgba(255,255,255,.1)}
.icon{font-size:52px;margin-bottom:16px}
h1{font-size:22px;color:${color};margin:0 0 12px}
p{color:#94A3B8;font-size:15px;line-height:1.7;margin:0 0 24px}
a{color:#3B82F6;text-decoration:none}a:hover{text-decoration:underline}</style></head>
<body><div class="card">
  <div class="icon">${icon}</div>
  <h1>${title}</h1>
  <p>${message}</p>
  <p style="font-size:13px;color:#64748B">Nếu đây là nhầm lẫn, hãy liên hệ <a href="mailto:hosyanh159@gmail.com">hosyanh159@gmail.com</a></p>
</div></body></html>`;
}

// GET /api/confirm?token=TOKEN&email=X&name=X&phone=X&plan=boss&planLabel=X&orderId=X&telegram=X
// Admin xác nhận thanh toán → gửi Email #1 + update subscriber + gửi Telegram

const https   = require('https');
const { getEmail }    = require('./email-templates');
const { sendMail }    = require('./mailer');
const { getSubscriber, saveSubscriber } = require('./blob');

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
      res.on('end', () => { try { resolve(JSON.parse(Buffer.concat(chunks).toString())); } catch { resolve({ ok: false }); } });
    });
    req.on('error', () => resolve({ ok: false }));
    req.write(payload); req.end();
  });
}

module.exports = async function handler(req, res) {
  const BOT_TOKEN   = process.env.TELEGRAM_BOT_TOKEN;
  const ADMIN_CHAT  = process.env.TELEGRAM_ADMIN_CHAT;
  const ADMIN_TOKEN = process.env.ADMIN_CONFIRM_TOKEN;

  const p = req.method === 'GET' ? req.query : (req.body || {});
  const { token, email, name, phone, plan, planLabel, orderId, telegram } = p;

  if (!ADMIN_TOKEN || token !== ADMIN_TOKEN) {
    res.setHeader('Content-Type', 'text/html; charset=utf-8');
    return res.status(401).send(errPage('Token không hợp lệ.'));
  }
  if (!email || !name || !plan || !orderId) {
    res.setHeader('Content-Type', 'text/html; charset=utf-8');
    return res.status(400).send(errPage('Thiếu thông tin.'));
  }

  const planKey    = plan.toLowerCase();
  const planName   = plan.toUpperCase();
  const courseLink = COURSE_LINKS[planKey] || COURSE_LINKS.boss;
  const confirmedAt = new Date().toISOString();
  const results    = { email1: false, blobUpdated: false, telegram: false };

  // 1. Gửi Email #1 (welcome + access)
  try {
    const tpl = getEmail(1, { name, planName, planLabel: planLabel || '', courseLink, orderId, email });
    const r   = await sendMail(email, tpl.subject, tpl.html);
    results.email1 = r.ok;
    console.log(`[confirm] Email #1 → ${email}: ${r.ok ? '✅' : '❌ ' + r.error}`);
  } catch (e) { console.error('[confirm] Email #1 error:', e.message); }

  // 2. Cập nhật subscriber: pending → confirmed + tags
  try {
    const existing = await getSubscriber(email);
    const base = existing || {
      email, name, phone: phone || '', plan: planKey, planName, planLabel: planLabel || '',
      orderId, telegram: (telegram || '').replace('@', '').trim(), courseLink,
      createdAt: confirmedAt, acEmailsSent: [],
    };

    const updatedTags = [
      planKey,
      'confirmed_payment',
      'sme_owner',
      'source_landing',
      `plan_${planKey}`,
    ];

    results.blobUpdated = await saveSubscriber({
      ...base,
      status:      'confirmed',
      segment:     'onboarded',
      tags:        updatedTags,
      confirmedAt,
      obEmailsSent: [...(base.obEmailsSent || [0]), 1],
    });
    console.log(`[confirm] Blob updated: ${email} → confirmed | tags: ${updatedTags.join(',')}`);
  } catch (e) { console.error('[confirm] Blob error:', e.message); }

  // 3. Gửi Telegram cho khách
  if (BOT_TOKEN && telegram) {
    const username = telegram.replace('@', '').trim();
    if (username) {
      const chatData = await tgRequest(BOT_TOKEN, '/getChat', { chat_id: '@' + username });
      if (chatData.ok) {
        const msg = `🎉 Chào <b>${name}</b>!\n\nThanh toán đã <b>xác nhận</b> 🎊\n\n`
          + `📚 <b>Link khóa học:</b>\n👉 ${courseLink}\n\n`
          + `📧 Email hướng dẫn đã gửi vào hộp thư.\n`
          + `💬 Zalo <b>0918 303 039</b> để vào nhóm SME AI Club.\n\nChúc học tốt! 🚀`;
        await tgRequest(BOT_TOKEN, '/sendMessage', { chat_id: chatData.result.id, text: msg, parse_mode: 'HTML' });
        results.telegram = true;
      } else {
        await tgRequest(BOT_TOKEN, '/sendMessage', {
          chat_id: ADMIN_CHAT,
          text: `⚠️ Khách <b>${name}</b> chưa /start bot → Giao link thủ công!`,
          parse_mode: 'HTML',
        });
      }
    }
  }

  // 4. Thông báo admin
  if (BOT_TOKEN && ADMIN_CHAT) {
    const nowVN = new Date().toLocaleString('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh' });
    await tgRequest(BOT_TOKEN, '/sendMessage', {
      chat_id: ADMIN_CHAT,
      text: `✅ <b>XÁC NHẬN HOÀN TẤT</b>\n\n`
          + `👤 <b>${name}</b> (${email})\n`
          + `📦 Gói: <b>${planName}</b> · 🔖 <code>${orderId}</code>\n`
          + `🕐 ${nowVN}\n\n`
          + `📨 Email #1: ${results.email1 ? '✅' : '❌'} | `
          + `💾 Blob: ${results.blobUpdated ? '✅' : '⚠️'} | `
          + `📱 Telegram: ${results.telegram ? '✅' : '⚠️'}\n\n`
          + `🏷️ Tags: plan_${planKey}, confirmed_payment, onboarded\n`
          + `📅 Onboarding #2→#5 sẽ tự gửi theo cron hàng ngày.`,
      parse_mode: 'HTML',
    });
  }

  res.setHeader('Content-Type', 'text/html; charset=utf-8');
  return res.status(200).send(okPage(name, email, planName, results));
};

function okPage(name, email, planName, r) {
  return `<!DOCTYPE html><html lang="vi"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Xác nhận thành công</title>
<style>body{font-family:system-ui,sans-serif;background:#0F172A;color:#fff;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0;padding:16px}
.c{background:#1E293B;border-radius:16px;padding:36px;max-width:460px;width:100%;text-align:center;border:1px solid rgba(255,255,255,.1)}
.icon{font-size:50px;margin-bottom:12px}h1{font-size:20px;margin:0 0 6px}
.sub{color:#94A3B8;font-size:14px;margin-bottom:20px}
.t{background:#0F172A;border-radius:10px;padding:14px;text-align:left;margin-bottom:14px}
.row{display:flex;justify-content:space-between;padding:7px 0;border-bottom:1px solid rgba(255,255,255,.07);font-size:13px}
.row:last-child{border:none}.ok{color:#4ADE80}.err{color:#F87171}.warn{color:#FBBF24}</style></head>
<body><div class="c">
  <div class="icon">✅</div><h1>Xác nhận thành công!</h1>
  <div class="sub"><strong>${name}</strong> (${email}) — Gói ${planName}</div>
  <div class="t">
    <div class="row"><span>Email #1 — Welcome</span><span class="${r.email1 ? 'ok' : 'err'}">${r.email1 ? '✅ Đã gửi' : '❌ Lỗi'}</span></div>
    <div class="row"><span>Cập nhật Blob + Tags</span><span class="${r.blobUpdated ? 'ok' : 'warn'}">${r.blobUpdated ? '✅ OK' : '⚠️ Chưa có Blob'}</span></div>
    <div class="row"><span>Telegram khách</span><span class="${r.telegram ? 'ok' : 'warn'}">${r.telegram ? '✅ Đã gửi' : '⚠️ Chưa gửi'}</span></div>
  </div>
  <p style="font-size:12px;color:#64748B">Onboarding email #2→#5 tự gửi theo cron hàng ngày.</p>
</div></body></html>`;
}

function errPage(msg) {
  return `<!DOCTYPE html><html lang="vi"><head><meta charset="UTF-8"><title>Lỗi</title>
<style>body{font-family:system-ui;background:#0F172A;color:#fff;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0}
.c{background:#1E293B;border-radius:16px;padding:40px;text-align:center}</style></head>
<body><div class="c"><div style="font-size:48px">❌</div><h2>${msg}</h2></div></body></html>`;
}

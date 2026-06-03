// Vercel Serverless Function — Cron Job gửi Email Sequence
// Chạy hàng ngày lúc 9:00 SA giờ Việt Nam (2:00 UTC)
// POST /api/send-sequence (triggered by Vercel Cron)
//
// Logic:
//   - Đọc tất cả subscribers từ KV
//   - Với mỗi subscriber, tính số ngày kể từ confirmedAt
//   - Gửi email đúng ngày (Day1→#2, Day3→#3, Day5→#4, Day7→#5)
//   - Đánh dấu email đã gửi để không gửi lại

const https = require('https');
const { getEmail, EMAIL_SCHEDULE } = require('./email-templates');

// ── Resend ────────────────────────────────────────────────────
async function sendEmail(to, subject, html) {
  const RESEND_KEY = process.env.RESEND_API_KEY;
  const FROM_EMAIL = process.env.FROM_EMAIL || 'AI BOSS SYSTEM <noreply@aiboss.vn>';
  if (!RESEND_KEY) return { ok: false, reason: 'no_key' };

  const payload = JSON.stringify({ from: FROM_EMAIL, to: [to], subject, html });
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
          resolve({ ok: res.statusCode === 200 || res.statusCode === 201 });
        } catch { resolve({ ok: false }); }
      });
    });
    req.on('error', e => resolve({ ok: false, error: e.message }));
    req.write(payload);
    req.end();
  });
}

// ── Vercel KV helpers ─────────────────────────────────────────
async function kvCommand(...args) {
  const KV_URL   = process.env.KV_REST_API_URL;
  const KV_TOKEN = process.env.KV_REST_API_TOKEN;
  if (!KV_URL || !KV_TOKEN) return null;
  try {
    const res = await fetch(KV_URL, {
      method: 'POST',
      headers: { Authorization: `Bearer ${KV_TOKEN}`, 'Content-Type': 'application/json' },
      body: JSON.stringify(args),
    });
    return res.json();
  } catch { return null; }
}

async function kvGetSubscriber(key) {
  const result = await kvCommand('GET', key);
  if (!result?.result) return null;
  try { return JSON.parse(result.result); } catch { return null; }
}

async function kvSetSubscriber(key, value) {
  return kvCommand('SET', key, JSON.stringify(value));
}

async function kvGetAllSubscriberKeys() {
  const result = await kvCommand('KEYS', 'subscriber:*');
  return result?.result || [];
}

// ── Tính số ngày đã trôi qua ──────────────────────────────────
function daysSince(isoDate) {
  const confirmed = new Date(isoDate);
  const now = new Date();
  return Math.floor((now - confirmed) / (1000 * 60 * 60 * 24));
}

// ── Main handler ──────────────────────────────────────────────
module.exports = async function handler(req, res) {
  // Bảo vệ endpoint — chỉ Vercel Cron hoặc admin mới gọi được
  const cronSecret  = process.env.CRON_SECRET;
  const authHeader  = req.headers['authorization'] || '';
  const queryToken  = req.query?.token || '';

  if (cronSecret) {
    const isVercelCron = authHeader === `Bearer ${cronSecret}`;
    const isAdminCall  = queryToken === process.env.ADMIN_CONFIRM_TOKEN;
    if (!isVercelCron && !isAdminCall) {
      return res.status(401).json({ error: 'Unauthorized' });
    }
  }

  if (!process.env.KV_REST_API_URL) {
    return res.status(200).json({ ok: false, reason: 'KV not configured', sent: 0 });
  }

  const keys = await kvGetAllSubscriberKeys();
  if (!keys.length) {
    return res.status(200).json({ ok: true, message: 'No subscribers', sent: 0 });
  }

  const log = [];
  let sent = 0;

  for (const key of keys) {
    const sub = await kvGetSubscriber(key);
    if (!sub || !sub.email || !sub.confirmedAt) continue;

    const days = daysSince(sub.confirmedAt);
    const emailsSent = sub.emailsSent || [1];

    // Tìm email cần gửi hôm nay
    for (const { emailNum, daysAfter } of EMAIL_SCHEDULE) {
      if (days < daysAfter) continue;               // Chưa đến ngày
      if (emailsSent.includes(emailNum)) continue;  // Đã gửi rồi

      // Gửi email
      const template = getEmail(emailNum, {
        name: sub.name,
        planName: sub.planName,
        planLabel: sub.planLabel,
        courseLink: sub.courseLink,
        orderId: sub.orderId,
      });

      if (!template) continue;

      const result = await sendEmail(sub.email, template.subject, template.html);

      if (result.ok) {
        // Cập nhật danh sách email đã gửi
        sub.emailsSent = [...emailsSent, emailNum];
        await kvSetSubscriber(key, sub);
        sent++;
        log.push({ email: sub.email, emailNum, days, status: 'sent' });
      } else {
        log.push({ email: sub.email, emailNum, days, status: 'failed', reason: result.reason });
      }

      break; // Mỗi subscriber chỉ gửi tối đa 1 email/ngày
    }
  }

  const now = new Date().toLocaleString('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh' });
  console.log(`[send-sequence] ${now} — Processed ${keys.length} subscribers, sent ${sent} emails`);

  return res.status(200).json({
    ok: true,
    processedAt: now,
    total: keys.length,
    sent,
    log,
  });
};

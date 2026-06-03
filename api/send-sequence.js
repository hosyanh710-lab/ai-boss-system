// Vercel Serverless Function — Cron Job gửi Email Sequence
// Chạy hàng ngày lúc 9:00 SA giờ Việt Nam (2:00 UTC)
// POST /api/send-sequence
//
// Logic:
//   - Đọc tất cả subscribers từ Vercel Blob
//   - Với mỗi subscriber, tính số ngày kể từ confirmedAt
//   - Gửi email đúng ngày: Day1→#2, Day3→#3, Day5→#4, Day7→#5
//   - Đánh dấu email đã gửi để không gửi lại

const { sendMail } = require('./mailer');
const { getEmail, EMAIL_SCHEDULE } = require('./email-templates');

// ── Vercel Blob helpers ───────────────────────────────────────
async function listSubscribers() {
  const token = process.env.BLOB_READ_WRITE_TOKEN;
  if (!token) {
    console.warn('[Sequence] BLOB_READ_WRITE_TOKEN chưa cấu hình');
    return [];
  }
  try {
    const res = await fetch('https://blob.vercel-storage.com?prefix=subscriber-', {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) return [];
    const data = await res.json();
    return data.blobs || [];
  } catch (e) {
    console.error('[Sequence] List blobs error:', e.message);
    return [];
  }
}

async function getSubscriber(url) {
  try {
    const res = await fetch(url);
    if (!res.ok) return null;
    return await res.json();
  } catch { return null; }
}

async function updateSubscriber(email, data) {
  const token = process.env.BLOB_READ_WRITE_TOKEN;
  if (!token) return;
  try {
    const key = `subscriber-${email.replace(/[^a-z0-9]/gi, '_')}.json`;
    await fetch(`https://blob.vercel-storage.com/${key}`, {
      method: 'PUT',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
        'x-content-type': 'application/json',
      },
      body: JSON.stringify(data),
    });
  } catch (e) {
    console.error('[Sequence] Update blob error:', e.message);
  }
}

// ── Tính số ngày đã trôi qua ─────────────────────────────────
function daysSince(isoDate) {
  const confirmed = new Date(isoDate);
  const now = new Date();
  return Math.floor((now - confirmed) / (1000 * 60 * 60 * 24));
}

// ── Main handler ─────────────────────────────────────────────
module.exports = async function handler(req, res) {
  // Bảo vệ endpoint
  const cronSecret = process.env.CRON_SECRET;
  const adminToken = process.env.ADMIN_CONFIRM_TOKEN;
  const auth       = req.headers['authorization'] || '';
  const queryToken = req.query?.token || '';

  const isVercelCron = cronSecret && auth === `Bearer ${cronSecret}`;
  const isAdminCall  = adminToken && queryToken === adminToken;

  if (!isVercelCron && !isAdminCall) {
    return res.status(401).json({ error: 'Unauthorized' });
  }

  if (!process.env.BLOB_READ_WRITE_TOKEN) {
    return res.status(200).json({ ok: false, reason: 'Blob not configured', sent: 0 });
  }

  const blobs = await listSubscribers();
  if (!blobs.length) {
    return res.status(200).json({ ok: true, message: 'No subscribers yet', sent: 0 });
  }

  const log = [];
  let sent = 0;

  for (const blob of blobs) {
    const sub = await getSubscriber(blob.url);
    if (!sub?.email || !sub?.confirmedAt) continue;

    const days       = daysSince(sub.confirmedAt);
    const emailsSent = sub.emailsSent || [1];

    for (const { emailNum, daysAfter } of EMAIL_SCHEDULE) {
      if (days < daysAfter) continue;          // Chưa đến ngày
      if (emailsSent.includes(emailNum)) continue; // Đã gửi rồi

      const tpl = getEmail(emailNum, {
        name:      sub.name,
        planName:  sub.planName,
        planLabel: sub.planLabel,
        courseLink: sub.courseLink,
        orderId:   sub.orderId,
      });
      if (!tpl) continue;

      const result = await sendMail(sub.email, tpl.subject, tpl.html);

      if (result.ok) {
        sub.emailsSent = [...emailsSent, emailNum];
        await updateSubscriber(sub.email, sub);
        sent++;
        log.push({ email: sub.email, emailNum, days, status: 'sent' });
        console.log(`[Sequence] ✅ Email #${emailNum} → ${sub.email} (Day ${days})`);
      } else {
        log.push({ email: sub.email, emailNum, days, status: 'failed', error: result.error });
        console.error(`[Sequence] ❌ Email #${emailNum} → ${sub.email}: ${result.error}`);
      }

      break; // Mỗi subscriber chỉ gửi tối đa 1 email/ngày
    }
  }

  const nowVN = new Date().toLocaleString('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh' });
  console.log(`[Sequence] ${nowVN} — ${blobs.length} subscribers, sent ${sent} emails`);

  return res.status(200).json({ ok: true, processedAt: nowVN, total: blobs.length, sent, log });
};

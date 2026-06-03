// Vercel Cron Job — Chạy hàng ngày lúc 9:00 SA (02:00 UTC)
// Xử lý 2 chuỗi email:
//   - ONBOARDING (#2–#5): subscribers đã xác nhận thanh toán
//   - ABANDONED CART (#1–#3): subscribers chưa thanh toán sau 24h

const { sendMail }    = require('./mailer');
const { getEmail, OB_SCHEDULE, getACEmail, AC_SCHEDULE } = require('./email-templates');
const { listSubscribers, saveSubscriber } = require('./blob');

function daysSince(isoDate) {
  return Math.floor((Date.now() - new Date(isoDate).getTime()) / 86400000);
}

module.exports = async function handler(req, res) {
  // Bảo vệ endpoint
  const cronSecret = process.env.CRON_SECRET;
  const adminToken = process.env.ADMIN_CONFIRM_TOKEN;
  const auth       = req.headers['authorization'] || '';
  const qToken     = req.query?.token || '';

  if (cronSecret && auth !== `Bearer ${cronSecret}` && qToken !== adminToken) {
    return res.status(401).json({ error: 'Unauthorized' });
  }

  if (!process.env.BLOB_READ_WRITE_TOKEN) {
    return res.status(200).json({ ok: false, reason: 'Blob not configured' });
  }

  const subscribers = await listSubscribers();
  if (!subscribers.length) {
    return res.status(200).json({ ok: true, message: 'No subscribers', sent: 0 });
  }

  const log = []; let sent = 0;

  for (const sub of subscribers) {
    if (!sub?.email || sub.status === 'unsubscribed') continue;

    // ── ONBOARDING sequence (confirmed) ──────────────────────
    if (sub.status === 'confirmed' && sub.confirmedAt) {
      const days       = daysSince(sub.confirmedAt);
      const emailsSent = sub.obEmailsSent || [1];

      for (const { emailNum, daysAfter } of OB_SCHEDULE) {
        if (days < daysAfter || emailsSent.includes(emailNum)) continue;

        const tpl = getEmail(emailNum, {
          name: sub.name, planName: sub.planName, planLabel: sub.planLabel,
          courseLink: sub.courseLink, orderId: sub.orderId, email: sub.email,
        });
        if (!tpl) continue;

        const r = await sendMail(sub.email, tpl.subject, tpl.html);
        if (r.ok) {
          sub.obEmailsSent = [...emailsSent, emailNum];
          await saveSubscriber(sub);
          sent++; log.push({ email: sub.email, type: 'OB', emailNum, days });
          console.log(`[Cron] ✅ OB #${emailNum} → ${sub.email}`);
        } else {
          log.push({ email: sub.email, type: 'OB', emailNum, status: 'failed', error: r.error });
        }
        break;
      }
    }

    // ── ABANDONED CART sequence (pending) ────────────────────
    if (sub.status === 'pending' && sub.createdAt) {
      const days       = daysSince(sub.createdAt);
      const acSent     = sub.acEmailsSent || [];

      for (const { emailNum, daysAfter } of AC_SCHEDULE) {
        if (days < daysAfter || acSent.includes(emailNum)) continue;

        const tpl = getACEmail(emailNum, {
          name: sub.name, plan: sub.plan,
          planLabel: sub.planLabel, email: sub.email,
        });
        if (!tpl) continue;

        const r = await sendMail(sub.email, tpl.subject, tpl.html);
        if (r.ok) {
          sub.acEmailsSent = [...acSent, emailNum];
          await saveSubscriber(sub);
          sent++; log.push({ email: sub.email, type: 'AC', emailNum, days });
          console.log(`[Cron] ✅ AC #${emailNum} → ${sub.email}`);
        } else {
          log.push({ email: sub.email, type: 'AC', emailNum, status: 'failed', error: r.error });
        }
        break;
      }
    }
  }

  const nowVN = new Date().toLocaleString('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh' });
  console.log(`[Cron] ${nowVN} — ${subscribers.length} subs, sent ${sent}`);
  return res.status(200).json({ ok: true, processedAt: nowVN, total: subscribers.length, sent, log });
};

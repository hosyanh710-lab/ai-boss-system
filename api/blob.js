// Vercel Blob helper — quản lý subscriber data
// Tất cả API calls đến Vercel Blob Storage

const BLOB_BASE = 'https://blob.vercel-storage.com';

function token() { return process.env.BLOB_READ_WRITE_TOKEN || ''; }

function subscriberKey(email) {
  return `subscriber-${email.toLowerCase().replace(/[^a-z0-9@._-]/g, '_')}.json`;
}

/** Lấy 1 subscriber theo email */
async function getSubscriber(email) {
  if (!token()) return null;
  try {
    const key = subscriberKey(email);
    const res = await fetch(`${BLOB_BASE}/${key}`, {
      headers: { Authorization: `Bearer ${token()}` },
    });
    if (!res.ok) return null;
    return await res.json();
  } catch { return null; }
}

/** Lưu hoặc cập nhật subscriber */
async function saveSubscriber(data) {
  if (!token()) { console.warn('[Blob] BLOB_READ_WRITE_TOKEN chưa cấu hình'); return false; }
  try {
    const key = subscriberKey(data.email);
    const res = await fetch(`${BLOB_BASE}/${key}`, {
      method: 'PUT',
      headers: {
        Authorization: `Bearer ${token()}`,
        'Content-Type': 'application/json',
        'x-content-type': 'application/json',
      },
      body: JSON.stringify(data),
    });
    return res.ok;
  } catch (e) {
    console.error('[Blob] Save error:', e.message);
    return false;
  }
}

/** Cập nhật một số fields của subscriber */
async function updateSubscriber(email, updates) {
  const existing = await getSubscriber(email);
  if (!existing) return false;
  return saveSubscriber({ ...existing, ...updates });
}

/** Liệt kê tất cả subscribers */
async function listSubscribers() {
  if (!token()) return [];
  try {
    const res = await fetch(`${BLOB_BASE}?prefix=subscriber-`, {
      headers: { Authorization: `Bearer ${token()}` },
    });
    if (!res.ok) return [];
    const data = await res.json();
    // Fetch nội dung từng subscriber
    const blobs = data.blobs || [];
    const subscribers = await Promise.all(
      blobs.map(async (b) => {
        try {
          const r = await fetch(b.url);
          return r.ok ? await r.json() : null;
        } catch { return null; }
      })
    );
    return subscribers.filter(Boolean);
  } catch (e) {
    console.error('[Blob] List error:', e.message);
    return [];
  }
}

module.exports = { getSubscriber, saveSubscriber, updateSubscriber, listSubscribers, subscriberKey };

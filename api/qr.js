// Vercel Serverless Function — SePay VietQR Generator
// /api/qr?bank=ACB&acc=126295629&amount=4990000&des=AIBOSS...&name=HO+SY+ANH

export default async function handler(req, res) {
  const {
    bank = 'ACB',
    acc  = '126295629',
    amount,
    des  = '',
    name = 'HO SY ANH',
  } = req.query;

  const SEPAY_TOKEN = process.env.SEPAY_API_TOKEN;

  // Thử SePay trước (nếu có token)
  if (SEPAY_TOKEN) {
    try {
      const sePayUrl = `https://qr.sepay.vn/img?acc=${acc}&bank=${bank}`
        + (amount ? `&amount=${amount}` : '')
        + (des ? `&des=${encodeURIComponent(des)}` : '')
        + `&template=compact`;

      const r = await fetch(sePayUrl, {
        headers: {
          'Authorization': `Bearer ${SEPAY_TOKEN}`,
          'Accept': 'image/png,image/*',
        },
      });

      if (r.ok && r.headers.get('content-type')?.includes('image')) {
        const buf = await r.arrayBuffer();
        res.setHeader('Content-Type', 'image/png');
        res.setHeader('Cache-Control', 'public, max-age=300');
        res.setHeader('Access-Control-Allow-Origin', '*');
        return res.status(200).send(Buffer.from(buf));
      }
    } catch (_) {}
  }

  // Fallback: VietQR.io (server-side, không bị hotlink chặn)
  try {
    const p = new URLSearchParams({
      amount:      amount || '',
      addInfo:     des,
      accountName: name,
    });
    const vietqrUrl = `https://img.vietqr.io/image/${bank}-${acc}-compact2.png?${p}`;

    const r = await fetch(vietqrUrl, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer':    'https://vietqr.io/',
        'Accept':     'image/png,image/*,*/*;q=0.8',
      },
    });

    if (r.ok) {
      const buf = await r.arrayBuffer();
      res.setHeader('Content-Type', r.headers.get('content-type') || 'image/png');
      res.setHeader('Cache-Control', 'public, max-age=300');
      res.setHeader('Access-Control-Allow-Origin', '*');
      return res.status(200).send(Buffer.from(buf));
    }
  } catch (_) {}

  // Last resort: trả 404
  res.status(502).json({ error: 'Could not generate QR. Please transfer manually.' });
}

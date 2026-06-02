// Vercel Serverless Function — VietQR Image Proxy
// URL: /api/qr?bank=ACB&acc=126295629&amount=4990000&des=AIBOSS...&name=HO+SY+ANH

export default async function handler(req, res) {
  const { bank = 'ACB', acc, amount, des = '', name = 'HO SY ANH' } = req.query;

  if (!acc) {
    return res.status(400).json({ error: 'Missing account number' });
  }

  // Build VietQR.io URL (server-side — không bị hotlink chặn)
  const params = new URLSearchParams({
    amount:      amount || '',
    addInfo:     des,
    accountName: name,
  });
  const vietqrUrl = `https://img.vietqr.io/image/${bank}-${acc}-compact2.png?${params}`;

  try {
    const response = await fetch(vietqrUrl, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (compatible; AI-BOSS-SYSTEM/1.0)',
        'Referer':    'https://vietqr.io/',
        'Accept':     'image/png,image/*,*/*',
      },
    });

    if (!response.ok) throw new Error(`VietQR status: ${response.status}`);

    const imageBuffer = await response.arrayBuffer();
    const contentType = response.headers.get('content-type') || 'image/png';

    res.setHeader('Content-Type', contentType);
    res.setHeader('Cache-Control', 'public, max-age=300'); // cache 5 phút
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.status(200).send(Buffer.from(imageBuffer));

  } catch (err) {
    // Fallback: trả về ảnh 1x1 transparent PNG nếu lỗi
    res.status(500).json({ error: err.message });
  }
}

// Vercel Serverless Function — VietQR Image Proxy
// /api/qr?bank=ACB&acc=126295629&amount=4990000&des=AIBOSS...

const https = require('https');
const http  = require('http');

function fetchImage(url) {
  return new Promise((resolve, reject) => {
    const client = url.startsWith('https') ? https : http;
    const req = client.get(url, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Referer':    'https://vietqr.io/',
        'Accept':     'image/png,image/*,*/*',
      }
    }, (res) => {
      if (res.statusCode === 301 || res.statusCode === 302) {
        return fetchImage(res.headers.location).then(resolve).catch(reject);
      }
      const chunks = [];
      res.on('data', c => chunks.push(c));
      res.on('end', () => resolve({ status: res.statusCode, type: res.headers['content-type'], data: Buffer.concat(chunks) }));
    });
    req.on('error', reject);
  });
}

module.exports = async function handler(req, res) {
  const { bank = 'ACB', acc = '126295629', amount = '', des = '', name = 'HO SY ANH' } = req.query;

  const SEPAY_TOKEN = process.env.SEPAY_API_TOKEN;

  // URL SePay
  let sePayUrl = `https://qr.sepay.vn/img?acc=${acc}&bank=${bank}&template=compact`;
  if (amount) sePayUrl += `&amount=${amount}`;
  if (des)    sePayUrl += `&des=${encodeURIComponent(des)}`;

  // Thử SePay với token
  if (SEPAY_TOKEN) {
    try {
      const r = await fetchImage(sePayUrl + `&apikey=${SEPAY_TOKEN}`);
      if (r.status === 200 && r.type && r.type.includes('image')) {
        res.setHeader('Content-Type', r.type);
        res.setHeader('Cache-Control', 'public, max-age=300');
        return res.status(200).send(r.data);
      }
    } catch (_) {}
  }

  // Fallback VietQR.io
  try {
    const p = new URLSearchParams({ amount, addInfo: des, accountName: name });
    const vietqrUrl = `https://img.vietqr.io/image/${bank}-${acc}-compact2.png?${p}`;
    const r = await fetchImage(vietqrUrl);
    if (r.status === 200 && r.data.length > 500) {
      res.setHeader('Content-Type', r.type || 'image/png');
      res.setHeader('Cache-Control', 'public, max-age=300');
      return res.status(200).send(r.data);
    }
  } catch (_) {}

  res.status(502).json({ error: 'QR generation failed' });
};

#!/bin/bash
# Chạy công cụ trên Mac / Linux: bấm đúp không được thì mở Terminal, gõ:  bash run.sh
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  echo "Đang cài đặt lần đầu, vui lòng chờ..."
  python3 -m venv .venv || { echo "Chưa có Python 3. Cài tại python.org rồi chạy lại."; exit 1; }
  .venv/bin/pip install -r requirements.txt
fi
( sleep 2; open http://127.0.0.1:5000 2>/dev/null || xdg-open http://127.0.0.1:5000 2>/dev/null ) &
.venv/bin/python app.py

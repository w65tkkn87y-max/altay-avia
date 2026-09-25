#!/bin/bash
# Постоянный публичный адрес сайта через ngrok (нужен настроенный authtoken: ngrok config add-authtoken …).
#   ./build/ngrok.sh            сайт должен работать на localhost:3000 (cd site && python3 -m http.server 3000)
#   Остановить: pkill -f ngrok.sh; pkill -x ngrok
cd "$(dirname "$0")/.."
DOMAIN=${DOMAIN:-ragweed-banked-reptilian.ngrok-free.dev}; PORT=${PORT:-3000}
lsof -iTCP:$PORT -sTCP:LISTEN >/dev/null 2>&1 || (cd site && nohup python3 -m http.server $PORT --bind 0.0.0.0 >/dev/null 2>&1 &)
while true; do
  ngrok http --url="https://$DOMAIN" $PORT --log=stdout --log-format=logfmt >> build/ngrok.log 2>&1
  echo "$(date '+%H:%M:%S') ngrok завершился, перезапуск через 5 с" >> build/ngrok.log; sleep 5
done

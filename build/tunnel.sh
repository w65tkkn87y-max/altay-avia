#!/bin/bash
# Временный публичный «мост» к локальному сайту (для показа из РФ): SSH-туннель pinggy.io по порту 443.
# Бесплатная сессия живёт 60 минут — скрипт сам переподключается; актуальная ссылка — в build/tunnel_url.txt.
#   ./build/tunnel.sh            (сайт должен быть запущен на localhost:3000: cd site && python3 -m http.server 3000)
#   Остановить: Ctrl+C или pkill -f tunnel.sh; pkill -f a.pinggy.io
cd "$(dirname "$0")/.."
PORT=${PORT:-3000}; OUT=build/tunnel_url.txt; LOG=build/tunnel.log
while true; do
  : > "$LOG"
  ssh -p 443 -o StrictHostKeyChecking=accept-new -o ServerAliveInterval=30 -o ServerAliveCountMax=3 \
      -o ExitOnForwardFailure=yes -R0:localhost:$PORT a.pinggy.io > "$LOG" 2>&1 &
  SSH=$!
  for i in $(seq 1 30); do
    URL=$(grep -Eo 'https://[a-z0-9.-]+\.free\.pinggy\.net' "$LOG" | head -1)
    [ -n "$URL" ] && break; sleep 1
  done
  if [ -n "$URL" ]; then echo "$URL" > "$OUT"; echo "$(date '+%H:%M:%S') туннель: $URL"; else echo "$(date '+%H:%M:%S') не удалось получить адрес, повтор…"; fi
  wait $SSH; echo "$(date '+%H:%M:%S') туннель закрылся, переподключение через 3 с"; sleep 3
done

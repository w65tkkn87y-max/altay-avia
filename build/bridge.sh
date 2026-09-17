#!/bin/bash
# «Мост» для показа сайта из любой сети (в т.ч. из РФ), без аккаунтов:
#   сайт  → localhost:3000  (python3 -m http.server)
#   pinggy-туннель (tunnel.sh, https, адрес меняется раз в час) → build/tunnel_url.txt
#   redirect_server.py :3001 → bore.pub:40412 (фиксированный адрес) → редирект на текущий pinggy-адрес
# Друзьям даётся ПОСТОЯННАЯ ссылка http://bore.pub:40412 . Всё держится под caffeinate (Mac не уснёт при открытой крышке).
#   ./build/bridge.sh          остановить: pkill -f bridge.sh; pkill -f tunnel.sh; pkill -f a.pinggy.io; pkill -f "bore local"; pkill -f redirect_server.py
cd "$(dirname "$0")/.."
BORE_PORT=${BORE_PORT:-40412}
lsof -iTCP:3000 -sTCP:LISTEN >/dev/null 2>&1 || (cd site && nohup python3 -m http.server 3000 --bind 0.0.0.0 >/dev/null 2>&1 &)
pgrep -f "build/tunnel.sh" >/dev/null || (nohup ./build/tunnel.sh > build/tunnel_watch.log 2>&1 &)
lsof -iTCP:3001 -sTCP:LISTEN >/dev/null 2>&1 || (nohup python3 build/redirect_server.py 3001 > build/redirect.log 2>&1 &)
sleep 2
while true; do
  bore local 3001 --to bore.pub --port $BORE_PORT >> build/bore.log 2>&1
  echo "$(date '+%H:%M:%S') bore закрылся, переподключение через 3 с" >> build/bore.log; sleep 3
done

#!/bin/bash
# build/shot.sh <page> <out.png> [WxH]  — скриншот страницы headless Chrome
P="$1"; O="$2"; S="${3:-1366,2400}"
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --disable-gpu --hide-scrollbars --window-size="$S" --virtual-time-budget=8000 --screenshot="$O" "http://localhost:${PORT:-3000}/$P" >/dev/null 2>&1

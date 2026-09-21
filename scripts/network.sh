#!/bin/bash
# waybar custom network: icon-only text + rich tooltip (essid, signal, IPv4, gateway)
PATH=/usr/local/bin:/usr/bin:/bin
NL=$'\n'
ICON=$'\U000f05a9'
OFF=$'\U000f05aa'
IFACE=$(ip route show default 2>/dev/null | awk '{print $5; exit}')
GW=$(ip route show default 2>/dev/null | awk '{print $3; exit}')

if [ -z "$IFACE" ]; then
  python3 -c 'import json,sys;print(json.dumps({"text":sys.argv[1],"tooltip":"offline","class":"disconnected"}))' "$OFF"
  exit 0
fi

IP4=$(ip -4 addr show dev "$IFACE" scope global 2>/dev/null | awk '/inet /{print $2; exit}' | cut -d/ -f1)
SIG=$(nmcli -t -f ACTIVE,SIGNAL dev wifi 2>/dev/null | awk -F: '$1=="yes"{print $2; exit}')
ESSID=$(nmcli -t -f ACTIVE,SIGNAL,SSID dev wifi 2>/dev/null | awk -F: '$1=="yes"{print $3; exit}')

TIP=""
[ -n "$ESSID" ] && TIP="$ESSID"
[ -n "$SIG" ] && TIP="${TIP:+$TIP$NL}signal: ${SIG}%"
[ -n "$IP4" ] && TIP="${TIP:+$TIP$NL}ip: $IP4"
[ -n "$GW" ] && TIP="${TIP:+$TIP$NL}gateway: $GW"
[ -z "$TIP" ] && TIP="$IFACE"

python3 - "$ICON" "$TIP" <<'PYEOF'
import json, sys
print(json.dumps({"text": sys.argv[1], "tooltip": sys.argv[2]}))
PYEOF

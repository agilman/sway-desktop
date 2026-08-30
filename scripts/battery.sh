#!/usr/bin/env bash

display_device=/org/freedesktop/UPower/devices/DisplayDevice

parse_device() {
  local device=$1

  upower -i "$device" 2>/dev/null | awk -F': *' '
    {
      sub(/^[[:space:]]+/, "", $1)
    }
    $1 == "percentage" { gsub(/%/, "", $2); pct = $2 }
    $1 == "state" { state = $2 }
    $1 == "energy-rate" { rate = $2 }
    $1 == "energy" { energy = $2 }
    $1 == "energy-full" { efull = $2 }
    $1 == "time to full" { full = $2 }
    $1 == "time to empty" { empty = $2 }
    END { printf "%s|%s|%s|%s|%s|%s|%s\n", pct, state, rate, full, empty, energy, efull }
  '
}

round_pct() {
  awk -v value="$1" 'BEGIN { if (value == "") { print "" } else { printf "%d", value + 0.5 } }'
}

format_rate() {
  awk -v value="$1" 'BEGIN { if (value == "") { printf "0.0" } else { printf "%.1f", value + 0 } }'
}

format_time() {
  local raw=$1 value unit minutes hours mins

  [ -n "$raw" ] || return 1

  set -- $raw
  value=${1:-}
  unit=${2:-}

  case $unit in
    hour|hours)
      minutes=$(awk -v value="$value" 'BEGIN { printf "%d", (value * 60) + 0.5 }')
      ;;
    minute|minutes)
      minutes=$(awk -v value="$value" 'BEGIN { printf "%d", value + 0.5 }')
      ;;
    *)
      return 1
      ;;
  esac

  hours=$((minutes / 60))
  mins=$((minutes % 60))
  printf '%dh %02dm' "$hours" "$mins"
}

estimate_time() {
  # hours = (energy_full - energy) / rate -> h/mm
  awk -v e="$1" -v f="$2" -v r="$3" 'BEGIN {
    if (r <= 0 || f <= 0 || f <= e) exit
    minutes = (f - e) / r * 60 + 0.5
    printf "%dh %02dm", int(minutes / 60), int(minutes) % 60
  }'
}

text_for_state() {
  local pct=$1 state=$2 full=$3 empty=$4 rate=$5 energy=$6 efull=$7
  local icon suffix time_text

  case $state in
    charging)
      icon=󰂄
      # bar stays compact; time estimate goes to the tooltip only
      ;;
    pending-charge)
      icon=󰂄
      ;;
    discharging)
      icon=󰁹
      ;;
    fully-charged)
      icon=󰁹
      ;;
    *)
      icon=󰁹
      ;;
  esac

  printf '%s %s%%%s' "$icon" "$pct" "$suffix"
}

tooltip_line_for_battery() {
  local name=$1 device=/org/freedesktop/UPower/devices/battery_"$1"
  local parsed pct state rate full empty

  parsed=$(parse_device "$device" 2>/dev/null) || return 1
  IFS='|' read -r pct state rate full empty <<EOF
$parsed
EOF

  [ -n "$pct" ] || return 1

  pct=$(round_pct "$pct")
  rate=$(format_rate "$rate")
  printf '%s %s%% %s %sW' "$name" "$pct" "$state" "$rate"
}

display_parsed=$(parse_device "$display_device" 2>/dev/null)
IFS='|' read -r display_pct display_state display_rate display_full display_empty display_energy display_efull <<EOF
$display_parsed
EOF

display_pct=$(round_pct "$display_pct")
if [ -n "$display_pct" ]; then
  display_text=$(text_for_state "$display_pct" "$display_state" "$display_full" "$display_empty" "$display_rate" "$display_energy" "$display_efull")
else
  display_text="󰁹 --"
fi

class=""
if [ -n "$display_pct" ]; then
  if [ "$display_pct" -le 10 ] 2>/dev/null; then
    class=critical
  elif [ "$display_pct" -le 20 ] 2>/dev/null; then
    class=warning
  fi
fi

tooltip=""
# First tooltip line: aggregate status incl. time estimate
time_text=""
if [ "$display_state" = charging ]; then
  time_text=$(format_time "$display_full")
  if [ -z "$time_text" ] && awk -v r="$display_rate" 'BEGIN{exit !(r>0.05)}'; then
    time_text=$(estimate_time "$display_energy" "$display_efull" "$display_rate")
  fi
  if [ -n "$time_text" ]; then
    tooltip="Aggregate: charging · ${time_text} to full"
  else
    tooltip="Aggregate: idle on AC (no charge current)"
  fi
elif [ "$display_state" = pending-charge ]; then
  tooltip="Aggregate: waiting to charge"
elif [ "$display_state" = discharging ]; then
  time_text=$(format_time "$display_empty")
  if [ -n "$time_text" ]; then
    tooltip="Aggregate: on battery · ${time_text} left"
  else
    tooltip="Aggregate: on battery"
  fi
elif [ "$display_state" = fully-charged ]; then
  tooltip="Aggregate: fully charged"
fi
for battery in BAT0 BAT1; do
  line=$(tooltip_line_for_battery "$battery") || continue
  if [ -n "$tooltip" ]; then
    tooltip="${tooltip}
$line"
  else
    tooltip=$line
  fi
done

if [ -n "$class" ]; then
  jq -cn --arg text "$display_text" --arg tooltip "$tooltip" --arg class "$class" \
    '{text: $text, tooltip: $tooltip, class: $class}'
else
  jq -cn --arg text "$display_text" --arg tooltip "$tooltip" \
    '{text: $text, tooltip: $tooltip}'
fi

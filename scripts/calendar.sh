#!/usr/bin/env bash
# Clock module click action: pinned calendar popup (dunst) with today marked.
# Hover tooltip already shows a calendar; a click dismisses GTK tooltips, so
# this gives the click a purpose instead of making the calendar vanish.
# Modes: notify (default) | text (print, for tests)

mode="${1:-notify}"
title="$(date '+%A, %B %-d, %Y')"

# Non-tty cal(1) emits no highlighting; mark today with brackets ourselves.
day=$(date +%-d)
body=$(cal | sed -E "1d;s/(^| )($day)( |$)/[\2]\3/" | sed -E 's/ +$//')
if [ "$mode" = text ]; then
  printf '%s\n%s\n' "$title" "$body"
  exit 0
fi
notify-send -a calendar -t 20000 -h string:x-dunst-stack-tag:calendar \
  "$title" "<tt>${body}</tt>" 2>/dev/null
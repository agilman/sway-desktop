#!/usr/bin/env python3
"""24h rain + temperature + wind forecast chart -> dunst image notification.

Architecture (fast clicks):
  --render   fetch forecast -> JSON cache + base PNG (used by systemd timer)
  (default)  overlay a "now" line on the cached base PNG via PIL (~0.2s),
             then show. Only falls back to a full fetch+render if the
             cache is stale (>3h) or missing.

Base PNG has fixed geometry (560x320, top ax rect [0.10, 0.47, 0.80, 0.31],
wind ax rect [0.10, 0.27, 0.80, 0.14]), so the time->pixel mapping for the
"now" line is exact.
IMPORTANT: dunst's visible window is only ~200px (y≈80..280 of the image —
dunst crops the TOP of the icon, not just the bottom; 2026-08-25 measurement:
frame top y=74, bottom y=377, constant for any icon height). Title (y≈13)
and footer (y≈0.045 -> ~306) both sit below the crop; the notification body
carries the summary. Do NOT move panels above y=80 without re-measuring.
Config: ~/.config/wayland-plus/config.env (LAT/LON/TZ/CITY/UNITS).
"""
import datetime
import json
import math
import os
import subprocess
import sys
import time
import urllib.request

CONFIG = os.path.join(os.environ.get("XDG_CONFIG_HOME",
                                      os.path.expanduser("~/.config")),
                      "wayland-plus", "config.env")
USER = os.environ.get("USER", "user")
JSON_CACHE = f"/tmp/wayland-plus-weather-forecast-{USER}.json"
BASE_PNG = f"/tmp/wayland-plus-weather-chart-base-{USER}.png"
OUT = f"/tmp/wayland-plus-weather-chart-{USER}.png"
MAX_AGE = 3 * 3600  # base cache considered stale after 3 hours

# plot area geometry (must match fig.add_axes below): figsize 5.6x3.2 @100dpi
# now line spans from the top of the upper axes to the bottom of the wind axes
AX_X0, AX_W = 0.10 * 560, 0.80 * 560
AX_Y0 = (1 - (0.41 + 0.425)) * 320   # top of upper axes (rain/prob/temp)
AX_Y1 = (1 - 0.1625) * 320           # bottom of wind axes

def load_config():
    cfg = {}
    try:
        for line in open(CONFIG):
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            cfg[k.strip()] = v.strip()
    except OSError:
        pass
    return cfg

_cfg = load_config()
LAT, LON = _cfg.get("LAT"), _cfg.get("LON")
CITY = _cfg.get("CITY", "")
UNITS = _cfg.get("UNITS", "metric")
if not LAT or not LON or LAT == "0.0":
    raise SystemExit(f"wayland-plus: set LAT/LON in {CONFIG}")

if UNITS == "imperial":
    _UP = "&temperature_unit=fahrenheit&wind_speed_unit=mph&precipitation_unit=inch"
    TU, RU, WU_ = "°F", "in", "mph"
else:
    _UP = ""
    TU, RU, WU_ = "°C", "mm", "km/h"

URL = ("https://api.open-meteo.com/v1/forecast"
       f"?latitude={LAT}&longitude={LON}"
       "&hourly=temperature_2m,precipitation_probability,precipitation,"
       "wind_speed_10m,wind_direction_10m"
       "&daily=precipitation_sum,precipitation_probability_max,"
       "temperature_2m_max,temperature_2m_min"
       f"&forecast_hours=24&timezone=auto{_UP}")

def fetch():
    with urllib.request.urlopen(URL, timeout=15) as r:
        d = json.load(r)
    json.dump(d, open(JSON_CACHE, "w"))
    return d

def load_cached():
    if os.path.exists(JSON_CACHE) and os.path.exists(BASE_PNG):
        if time.time() - os.path.getmtime(BASE_PNG) < MAX_AGE:
            try:
                d = json.load(open(JSON_CACHE))
            except (OSError, ValueError):
                return None
            # pre-wind-panel caches lack the wind arrays; force re-fetch
            if "wind_speed_10m" not in d.get("hourly", {}):
                return None
            return d
    return None

def compass(deg):
    return "N NNE NE ENE E SE SSE S SSW SW WSW W WNW NW NNW".split()[int(deg / 45 + 0.5) % 16]

def render_base(d):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyArrowPatch

    h = d["hourly"]
    times = [datetime.datetime.fromisoformat(t) for t in h["time"]]
    temp = h["temperature_2m"]
    prob = h["precipitation_probability"]
    rain = h["precipitation"]
    ws = h["wind_speed_10m"]
    wd = h["wind_direction_10m"]
    dy = d["daily"]

    fig = plt.figure(figsize=(5.6, 3.2), dpi=100)   # 560x320, fits dunst window
    fig.patch.set_facecolor("#1e1e2e")
    ax = fig.add_axes([0.10, 0.41, 0.80, 0.425])
    ax.set_facecolor("#181825")

    x = list(range(len(rain)))
    ax.bar(x, [r or 0 for r in rain], color="#89b4fa", alpha=0.85, width=0.8)
    ax.set_ylabel(RU, color="#89b4fa", fontsize=8, weight="bold")
    ax.set_ylim(0, max(1.5 if UNITS != "imperial" else 0.1,
                       max((r or 0) for r in rain) * 1.3))
    ax.tick_params(axis="y", colors="#89b4fa", labelsize=7, width=1.5, length=4)

    # prob dashed line on its own hidden 0-100 axis (max prob is in the
    # footer text); temperature gets a separate auto-scaled axis so the
    # line uses the full plot height instead of hugging the top.
    ax2 = ax.twinx()
    ax2.plot(x, [p or 0 for p in prob], color="#74c7ec", lw=1.4, ls="--")
    ax2.set_ylim(0, 100)
    ax2.set_yticks([])
    ax2.spines["right"].set_visible(False)

    ax3 = ax.twinx()
    ax3.plot(x, temp, color="#fab387", lw=2.0)
    tmin, tmax = min(temp), max(temp)
    pad = max(2.0, (tmax - tmin) * 0.15)
    ax3.set_ylim(tmin - pad, tmax + pad)
    ax3.tick_params(axis="y", colors="#fab387", labelsize=7, width=1.5, length=4)
    ax3.set_ylabel(TU, color="#fab387", fontsize=8, weight="bold")

    step = max(1, len(times) // 6)
    ax.set_xticks(range(0, len(times), step))
    ax.set_xticklabels([times[i].strftime("%H:%M") for i in range(0, len(times), step)],
                       color="#cdd6f4", fontsize=8, weight="bold")
    ax.tick_params(axis="x", colors="#cdd6f4", labelsize=7, width=1.5, length=4)

    # --- wind panel (bottom): speed line + direction arrows (WU style) ---
    axw = fig.add_axes([0.10, 0.1625, 0.80, 0.175])
    axw.set_facecolor("#181825")
    wmax = max(v or 0 for v in ws)
    axw.plot(x, [v or 0 for v in ws], color="#89b4fa", lw=1.8)
    axw.set_ylim(0, max(10.0, wmax * 1.5))
    axw.set_ylabel(WU_, color="#89b4fa", fontsize=8, weight="bold")
    axw.tick_params(axis="y", colors="#89b4fa", labelsize=7, width=1.5, length=4)
    axw.grid(axis="y", color="#45475a", lw=0.8)
    axw.set_xlim(-0.5, len(times) - 0.5)
    axw.set_xticks([])
    # direction arrows every 2 h. Met direction is "from"; WU arrows point
    # where the wind blows TO. Computed in display space so the arrow
    # angle isn't skewed by the axes' aspect ratio, then mapped back.
    fig.canvas.draw()
    inv = axw.transData.inverted()
    L = 13.0  # arrow length, display points
    for i in range(0, len(ws), 2):
        if wd[i] is None:
            continue
        theta = math.radians((wd[i] + 180) % 360)   # to-direction, 0=N up
        x0, y0 = axw.transData.transform((x[i], ws[i] or 0))
        x1 = x0 + L * math.sin(theta)
        y1 = y0 + L * math.cos(theta)
        (px0, py0), (px1, py1) = inv.transform([(x0, y0), (x1, y1)])
        axw.add_patch(FancyArrowPatch((px0, py0), (px1, py1),
                                      arrowstyle="-|>", mutation_scale=11,
                                      lw=1.4, color="#a6c8ff",
                                      transform=axw.transData))

    for s in (list(ax.spines.values()) + list(ax2.spines.values()) +
              list(ax3.spines.values()) + list(axw.spines.values())):
        s.set_color("#45475a")
        s.set_linewidth(1.5)
    ax.grid(axis="y", color="#45475a", lw=0.8)
    ax.set_xlim(-0.5, len(times) - 0.5)

    total = sum(r or 0 for r in rain)
    peak_i = max(range(len(rain)), key=lambda i: rain[i] or 0)
    city = f" — {CITY}" if CITY else ""
    ax.set_title(f"Rain{city} — next {len(rain)} h  ·  total {total:.2f} {RU}",
                 color="#cdd6f4", fontsize=9, weight="bold", loc="left", pad=3)
    if (rain[peak_i] or 0) > 0:
        ax.annotate(f"{rain[peak_i]:.2f} {RU}",
                    xy=(peak_i, rain[peak_i]), xytext=(4, 4),
                    textcoords="offset points", color="#89b4fa", fontsize=8)

    # footer sits at y≈275px, inside dunst's visible window (ends y≈280)
    fig.text(0.10, 0.056,
             f"prob max {dy['precipitation_probability_max'][0]}% · "
             f"{dy['temperature_2m_min'][0]:.0f}–{dy['temperature_2m_max'][0]:.0f} {TU} · "
             f"bars rain · dashed prob · orange temp | wind {WU_} + dir arrows",
             color="#cdd6f4", fontsize=8, va="baseline")

    fig.savefig(BASE_PNG, facecolor=fig.get_facecolor())

def overlay_now(d):
    """Copy base PNG and draw a vertical 'now' line at the current time."""
    from PIL import Image, ImageDraw
    times = [datetime.datetime.fromisoformat(t) for t in d["hourly"]["time"]]
    now = datetime.datetime.now()
    n = len(times)
    # fractional index of 'now' (hourly slots, times[0] = forecast start)
    fi = (now - times[0]).total_seconds() / 3600
    frac = (fi + 0.5) / n                     # xlim is (-0.5, n-0.5)
    frac = max(0.0, min(1.0, frac))
    x = AX_X0 + frac * AX_W

    img = Image.open(BASE_PNG).convert("RGB")
    dr = ImageDraw.Draw(img)
    dr.line([(x, AX_Y0), (x, AX_Y1)], fill="#f38ba8", width=2)
    img.save(OUT)

def show(d):
    h, dy = d["hourly"], d["daily"]
    rain = h["precipitation"]
    times = [datetime.datetime.fromisoformat(t) for t in h["time"]]
    total = sum(r or 0 for r in rain)
    peak_i = max(range(len(rain)), key=lambda i: rain[i] or 0)
    ws, wd = h["wind_speed_10m"], h["wind_direction_10m"]
    wmax_i = max(range(len(ws)), key=lambda i: ws[i] or 0)
    # circular mean for prevailing direction
    sx = sum(math.sin(math.radians(dd)) for dd in wd)
    sy = sum(math.cos(math.radians(dd)) for dd in wd)
    avg_dir = (math.degrees(math.atan2(sx, sy)) + 360) % 360
    body = (f"Next 24h: {total:.2f} {RU} rain · "
            f"peak {rain[peak_i] or 0:.2f} {RU} at {times[peak_i].strftime('%H:%M')}\n"
            f"Prob max {dy['precipitation_probability_max'][0]}% · "
            f"{dy['temperature_2m_min'][0]:.0f}–{dy['temperature_2m_max'][0]:.0f} {TU}\n"
            f"Wind: {sum(v or 0 for v in ws) / len(ws):.1f} avg, "
            f"peak {ws[wmax_i]:.1f} {WU_} at {times[wmax_i].strftime('%H:%M')} "
            f"from {compass(wd[wmax_i])}")
    subprocess.run(["notify-send", "-a", "weather-chart", "-t", "20000",
                    "-i", OUT, " ", " "])

def main():
    if "--render" in sys.argv:
        render_base(fetch())
        return
    d = load_cached()
    if d is None:
        d = fetch()
        render_base(d)
    overlay_now(d)
    show(d)

if __name__ == "__main__":
    main()

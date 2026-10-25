#!/usr/bin/env bash
# Render PTrack's icons from the SVGs in this folder. Needs `resvg`
# (https://github.com/linebender/resvg; Arch: pacman -S resvg). Run from anywhere:
#
#     bash app/icon/build.sh
#
# The Android adaptive icon (Android 8+) is a vector drawing kept by hand in
# android/app/src/main/res/drawable/ic_launcher_foreground.xml; keep it in step
# with these SVGs. Everything else is generated here:
#   - legacy Android launcher icons (round and rounded-square), every density
#   - Android launch screen images (blue with the icon in the middle)
#   - the iPhone home-screen icon and the browser favicon (app/public/)

set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
RES=../android/app/src/main/res
PUBLIC=../public
BLUE='#3b5bdb'
command -v resvg >/dev/null || { echo "resvg is required (Arch: pacman -S resvg)"; exit 1; }

# Legacy launcher icons: 48 dp at each screen density.
for pair in mdpi:48 hdpi:72 xhdpi:96 xxhdpi:144 xxxhdpi:192; do
  density=${pair%%:*} size=${pair##*:}
  resvg -w "$size" -h "$size" icon-rounded.svg "$RES/mipmap-$density/ic_launcher.png"
  resvg -w "$size" -h "$size" icon-round.svg "$RES/mipmap-$density/ic_launcher_round.png"
done

# Launch screens: PTrack blue, icon centred at a third of the shorter side.
for png in "$RES"/drawable*/splash.png; do
  read -r w h < <(python3 -c "
import struct, sys
d = open(sys.argv[1], 'rb').read(24)
print(*struct.unpack('>II', d[16:24]))" "$png")
  s=$(( (w < h ? w : h) / 3 ))
  tmp=$(mktemp --suffix=.svg)
  cat > "$tmp" <<SVG
<svg xmlns="http://www.w3.org/2000/svg" width="$w" height="$h">
  <rect width="$w" height="$h" fill="$BLUE"/>
  <image href="$PWD/icon-square.svg" x="$(( (w - s) / 2 ))" y="$(( (h - s) / 2 ))" width="$s" height="$s"/>
</svg>
SVG
  resvg "$tmp" "$png"
  rm "$tmp"
done

# Web: favicon (SVG) and the iPhone "Add to Home Screen" icon.
mkdir -p "$PUBLIC"
cp favicon.svg "$PUBLIC/favicon.svg"
resvg -w 180 -h 180 icon-square.svg "$PUBLIC/apple-touch-icon.png"

echo "Icons rendered."

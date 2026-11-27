#!/bin/bash
# E6: downloads all 160 VCD clips (1080p MP4; th, th-bb, th-m, th-ob) next to the 40 talking-head clips already here.
# Skips clips already downloaded; safe to run again. Needs Wi-Fi. ~3-6 GB. Log: out_e6_download.txt
D=$(cd "$(dirname "$0")" && pwd); . "$D/../settings.sh"
exec > >(tee -a "$D/out_e6_download.txt") 2>&1
echo; echo "== E6 download START  $(date '+%a %d %b %I:%M %p')"
mkdir -p "$VCD1080"; cd "$VCD1080" || exit 1
[ -f VCD/download/mp4_list.txt ] || git clone -q --depth 1 https://github.com/microsoft/VCD.git || { echo "== cannot get the VCD clip list (Wi-Fi on?)"; exit 1; }
touch "$VCD1080/.e6_downloading"
n=0; got=0; fail=0
while read p; do
  case "$p" in mp4/*) ;; *) continue;; esac
  n=$((n+1)); out="$VCD1080/$p"; mkdir -p "$(dirname "$out")"
  [ -s "$out" ] && continue
  rm -f "$out.part"   # the server does not resume (no byte ranges): always start a clip from the beginning
  if curl -sS -L --fail --retry 5 -o "$out.part" "https://vcdpublic.blob.core.windows.net/vcd1/$p"; then
    mv "$out.part" "$out"; got=$((got+1)); echo "[$n] ok $p $(ls -lh "$out" | awk '{print $5}')"
  else fail=$((fail+1)); echo "[$n] FAILED $p"; fi
done < VCD/download/mp4_list.txt
rm -f "$VCD1080/.e6_downloading"
echo "== E6 download END  $(date '+%I:%M %p'): $got new, $fail failed; clips present: $(find "$VCD1080/mp4" -name '*_30.mp4' | wc -l | tr -d ' ') of 160 (th-m are portrait, 1080x1920); $(du -sh "$VCD1080/mp4" | cut -f1)"

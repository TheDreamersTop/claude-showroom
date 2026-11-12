#!/bin/bash
# webenc.sh <video_master.mp4> <mastered_a.m4a> <out.mp4> [kbps]  -> 2-pass H.264 web encode, audio copied, faststart
set -euo pipefail
V=$1; A=$2; O=$3; R=${4:-3900}
P=$(dirname "$O")/passlog_$$
ffmpeg -y -loglevel error -i "$V" -an -c:v libx264 -preset slow -tune grain -b:v ${R}k -pass 1 -passlogfile "$P" -pix_fmt yuv420p -f mp4 /dev/null
ffmpeg -y -loglevel error -i "$V" -i "$A" -map 0:v -map 1:a -c:v libx264 -preset slow -tune grain -b:v ${R}k -maxrate $((R*2))k -bufsize $((R*4))k -pass 2 -passlogfile "$P" -pix_fmt yuv420p -c:a copy -movflags +faststart "$O"
rm -f "$P"*
ls -la "$O"

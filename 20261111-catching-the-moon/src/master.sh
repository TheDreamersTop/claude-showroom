#!/bin/bash
# master.sh <video_only.mp4> <mix_pre.wav> <out.mp4>
# Two-pass loudnorm -> 4x oversampled limiter -> AAC, muxed separately with -c copy (never one-pass).
set -euo pipefail
V=$1; A=$2; O=$3
D=$(dirname "$O"); B=$(basename "$O" .mp4)
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$V")
M=$(ffmpeg -hide_banner -i "$A" -t "$DUR" -af loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json -f null - 2>&1 | sed -n '/{/,/}/p')
g(){ echo "$M" | grep "\"$1\"" | sed 's/.*: "\(.*\)".*/\1/'; }
ffmpeg -y -loglevel error -i "$A" -t "$DUR" -af "loudnorm=I=-16:TP=-1.5:LRA=11:measured_I=$(g input_i):measured_TP=$(g input_tp):measured_LRA=$(g input_lra):measured_thresh=$(g input_thresh):offset=$(g target_offset):linear=true,aresample=192000,aformat=sample_fmts=fltp:channel_layouts=stereo,alimiter=limit=0.79:attack=0.5:release=60:level=false,aresample=48000" -c:a pcm_s16le "$D/${B}_mix.wav"
ffmpeg -y -loglevel error -i "$D/${B}_mix.wav" -c:a aac -b:a 192k "$D/${B}_a.m4a"
ffmpeg -y -loglevel error -i "$V" -i "$D/${B}_a.m4a" -map 0:v -map 1:a -c copy -movflags +faststart "$O"
echo "== loudness"; ffmpeg -hide_banner -i "$O" -vn -af ebur128=peak=true -f null - 2>&1 | sed -n '/Summary/,$p' | grep -E "I:|LRA:|Peak:"
echo "== streams"; ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate,duration -of compact "$O"
echo "== aac packet gaps (pts jumps > 1 frame)"
ffprobe -v error -select_streams a -show_entries packet=pts_time,duration_time -of csv=p=0 "$O" | awk -F, 'NR>1 && ($1-p) > 0.05 {print "gap at", p, "->", $1; n++} {p=$1} END {print (n+0), "gaps"}'
echo "== faststart"; ffprobe -v trace "$O" 2>&1 | grep -m2 -oE "type:'(moov|mdat)'" | tr '\n' ' '; echo
ls -la "$O"

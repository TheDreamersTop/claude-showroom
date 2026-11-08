#!/bin/bash
# usage: sheets.sh video.mp4 outdir  -> contact sheets, 2 fps, 30 s per sheet, timestamps burned in
set -e
v=$1; out=$2; mkdir -p $out; rm -f $out/sheet_*.png
dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 $v)
n=$(python3 -c "import math;print(math.ceil($dur/30))")
for i in $(seq 0 $((n-1))); do
  ss=$((i*30))
  ffmpeg -v error -y -ss $ss -t 30 -i $v -vf "fps=2,scale=240:240,drawtext=text='%{eif\:t+$ss\:d}.%{eif\:mod(t*10\,10)\:d}s':x=4:y=4:fontsize=16:fontcolor=white,tile=10x6" -frames:v 1 $out/sheet_$(printf %02d $i).png
done
ls $out

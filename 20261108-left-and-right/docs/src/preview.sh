#!/bin/bash
# usage: preview.sh name size [scale]  -> renders/name_size.mp4 from renders/name.wav
set -e
name=$1; size=${2:-540}; scale=${3:-0.44}
fr=frames/${name}_${size}
rm -rf $fr
~/anaconda3/bin/python src/render.py renders/$name.wav $fr --video --size $size --scale $scale --power "${POWER:-0:0,1.2:0,2.5:1,1000:1}"
ffmpeg -v error -y -f concat -safe 0 -i $fr/list.txt -i renders/$name.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 256k -shortest renders/${name}_${size}.mp4
echo renders/${name}_${size}.mp4

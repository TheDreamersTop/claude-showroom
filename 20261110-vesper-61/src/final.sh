#!/bin/bash
# parallel compose: 5 chunks -> concat -> mux audio.  usage: final.sh out/name.mp4 [--preview]
cd "$(dirname "$0")/.."
OUT=$1; shift
N=$(python -c "import json;print(int(round(json.load(open('edit.json'))['total']*24)))")
K=5; step=$(( (N + K - 1) / K ))
rm -f out/_chunk*.mp4 out/_list.txt
for i in $(seq 0 $((K-1))); do
  a=$((i*step)); b=$(((i+1)*step))
  python scripts/compose.py out/_chunk$i.mp4 --frames $a $b "$@" > out/_chunk$i.log 2>&1 &
done
wait
for i in $(seq 0 $((K-1))); do echo "file '_chunk$i.mp4'" >> out/_list.txt; done
ffmpeg -hide_banner -loglevel error -y -f concat -safe 0 -i out/_list.txt -c copy out/_video.mp4
python scripts/compose.py $OUT --mux out/_video.mp4 "$@"
echo FINAL_DONE $OUT

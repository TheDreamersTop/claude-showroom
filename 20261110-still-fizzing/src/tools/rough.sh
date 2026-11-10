#!/bin/bash
# usage: rough.sh name [preset] [crf]
cd /home/pmli/workspace/claude-showroom/work/src
N=$1; P=${2:-veryfast}; C=${3:-22}
rm -f ../out/${N}_video.mp4 ../out/${N}.mp4
PRESET=$P CRF=$C ../../tools/venv/bin/python compose.py ../out/${N}_video.mp4 > ../out/compose_${N}.log 2>&1
cd ..
ffmpeg -y -loglevel error -i out/${N}_video.mp4 -i audio/mix.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 256k -af loudnorm=I=-16:TP=-1.5:LRA=11 -shortest out/${N}.mp4
echo DONE $N

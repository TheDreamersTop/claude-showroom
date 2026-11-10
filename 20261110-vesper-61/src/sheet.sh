#!/bin/bash
# contact sheets: one frame per second, 6 columns, labelled with timecode. usage: sheet.sh video.mp4 outprefix
V=$1; P=$2
ffmpeg -hide_banner -loglevel error -y -i "$V" -vf "fps=1,crop=iw:ih*0.756:0:ih*0.122,scale=480:-1,drawtext=fontfile=C\\:/Windows/Fonts/segoeui.ttf:text='%{pts\:hms}':x=6:y=6:fontsize=16:fontcolor=yellow:box=1:boxcolor=black@0.5,tile=6x6" "${P}_%d.png"

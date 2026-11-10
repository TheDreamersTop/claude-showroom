cd /home/pmli/workspace/claude-showroom/work
B=../tools/blender-4.5.3-linux-x64/blender
for s in "$@"; do set -- $s
 [ -f renders/$1-$2.png ] && continue
 $B -b -P src/scenes.py -- $1 $2 final renders/$1-$2.tmp.png 2>&1 | grep -E "RENDER_SECONDS|Error|Traceback" && mv renders/$1-$2.tmp.png renders/$1-$2.png
done
echo QUEUE_DONE

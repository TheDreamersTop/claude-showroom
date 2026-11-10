cd /home/pmli/workspace/claude-showroom/work
rm -rf renders/pop_tmp
../tools/blender-4.5.3-linux-x64/blender -b -P src/pop_anim.py -- renders/pop_tmp 1 48 2>&1 | grep -E "POP_FRAME|Error" >> renders/queue2.log
mv renders/pop_tmp renders/pop && echo POP_DONE >> renders/queue2.log

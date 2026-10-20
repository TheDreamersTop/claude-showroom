#!/bin/bash
PLAN='[["intro",3.2,"intro768"],[null,10,null,"__pd()"],["rewind",1.0,"rew"],[null,10,null,"window.__autoLetter([[0.58,0.1,500],[0.58,0.9,1500],[0.3,0.75,9000]],3600)"],["gallery",0.5,"orig"],[null,10,null,"window.__printv=__S.letters[0].code;document.querySelector(\"#twin\").click()"],["gallery",2.0,"twins"]]'
VW=1600 VH=900 timeout 2400 node phases.mjs "http://localhost:8080/20261019-letters-from-the-sky/?fixdt=0.1&mute=1&speed=20&nocap=80" ../shots/v3u- "$PLAN"

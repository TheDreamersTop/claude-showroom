#!/bin/bash
A='window.__autoLetter([[0.58,0.1,500],[0.58,0.9,1800],[0.62,0.1,9000]],4200)'
B='window.__autoLetter([[0.58,0.9,9000]],3000)'
C='window.__autoLetter([[0.15,0.8,9000]],2600)'
PLAN='[["intro",3.5,"01-intro"],[null,10,null,"__pd()"],["rewind",0.9,"02-rewind"],["grow",0.3,null],[null,10,null,"__mv(1150,160)"],["grow",4.0,"03-grow"],[null,10,null,"__mv(1100,820)"],["grow",8.0,"04-grow-dry"],
[null,10,null,"'$A'"],["land",1.9,"05-sweep"],["land",4.6,"06-replay"],["land",8.6,"07-letter"],[null,10,null,"'$B'"],[null,10,null,"'$C'"],["gallery",3.0,"08-gallery"],[null,10,null,"__mv(760,620)"],[null,1200,"09-hover"],[null,10,null,"__pd()"],[null,3500,"10-focus"],[null,10,null,"document.querySelector(\"#card-save\").click()"],[null,6000,null]]'
VW=1920 VH=1080 timeout 4000 node phases.mjs "http://localhost:8080/20261019-letters-from-the-sky/?fixdt=0.1&mute=1&speed=14&nocap=60" ../shots/final- "$PLAN"

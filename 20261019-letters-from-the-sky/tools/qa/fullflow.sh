#!/bin/bash
TAG=$1; N=${2:-512}; EXTRA=$3
PLAN='[["intro",2.5,"01-intro"],[null,10,null,"__pd()"],["rewind",0.8,"02-rewind"],["grow",0.5,"03-seed"],
[null,10,null,"__mv(950,120)"],["grow",3.0,"04-grow3"],[null,10,null,"__mv(1350,700)"],["grow",6.0,"05-grow6"],
[null,10,null,"__mv(800,430);window.__S.breathing=true"],["grow",7.0,"06-breath"],[null,10,null,"window.__S.breathing=false"],
[null,10,null,"__sp()"],["land",1.0,"08-land1"],["land",2.2,"09-flash"],["land",4.5,"10-replay"],["land",7.5,"11-card"],["gallery",1.5,"12-gallery1"],
[null,10,null,"__sp()"],["rise",0.5,"13-rise"],[null,10,null,"__mv(300,200)"],["grow",5.0,"14-grow-b"],[null,10,null,"__sp()"],["gallery",2.5,"15-gallery2"],
[null,10,null,"__mv(800,450)"],[null,1500,"16-hover"]]'
VW=1600 VH=900 timeout 2400 node phases.mjs "http://localhost:8080/20261019-letters-from-the-sky/?n=$N&fixdt=0.1&mute=1&speed=14&nocap=60$EXTRA" ../shots/$TAG- "$PLAN"

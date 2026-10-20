#!/bin/bash
TAG=$1; N=${2:-512}
A='window.__autoLetter([[0.58,0.1,500],[0.58,0.9,1500],[0.62,0.1,9000]],3400)'
B='window.__autoLetter([[0.2,0.75,9000]],2400)'
C='window.__autoLetter([[0.58,0.1,1200],[0.58,0.9,9000]],3000)'
D='window.__autoLetter([[0.9,0.6,2500],[0.4,0.85,1200],[0.6,0.15,9000]],4200)'
PLAN='[[null,2000,null,"'$A'"],["gallery",0.3,null],[null,10,null,"'$B'"],[null,10,null,"'$C'"],[null,10,null,"'$D'"],["land",2.3,"sweep"],["land",4.2,"replay"],["land",8.0,"card"],["gallery",3.0,"g4"],[null,10,null,"__mv(620,330)"],[null,1500,"hover"],[null,10,null,"__pd()"],[null,4000,"focus"],[null,10,null,"document.querySelector(\"#card-save\").click()"],[null,6000,null]]'
VW=1600 VH=900 timeout 2400 node phases.mjs "http://localhost:8080/20261019-letters-from-the-sky/?n=$N&fixdt=0.1&mute=1&t0=5" ../shots/$TAG- "$PLAN"

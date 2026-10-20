#!/bin/bash
A='window.__autoLetter([[0.58,0.1,500],[0.58,0.9,1800],[0.62,0.1,9000]],4200)'
B='window.__autoLetter([[0.58,0.9,9000]],3000)'
C='window.__autoLetter([[0.9,0.6,2500],[0.4,0.85,1500],[0.6,0.15,9000]],4500)'
D='window.__autoLetter([[0.15,0.8,9000]],2600)'
PLAN='[[null,1500,null,"'$A'"],["land",8.0,"A-card"],[null,10,null,"'$B'"],[null,10,null,"'$C'"],["land",2.4,"C-close"],[null,10,null,"'$D'"],["gallery",3.0,"g4"],[null,10,null,"__mv(700,420)"],[null,1200,"hover"],[null,10,null,"__pd()"],[null,3500,"focus"]]'
VW=1600 VH=900 timeout 3000 node phases.mjs "http://localhost:8080/20261019-letters-from-the-sky/?fixdt=0.1&mute=1" ../shots/v8- "$PLAN"

#!/bin/bash
A='window.__autoLetter([[0.58,0.1,500],[0.58,0.85,1600],[0.58,0.35,500],[0.62,0.1,9000]],4200)'
B='window.__autoLetter([[0.58,0.9,9000]],3000)'
C='window.__autoLetter([[0.15,0.8,9000]],2400)'
PLAN='[[null,1500,null,"'$A'"],["land",9.0,"letter"],[null,10,null,"document.querySelector(\"#card-save\").click()"],[null,9000,null],[null,10,null,"'$B'"],[null,10,null,"'$C'"],["gallery",3.0,"gallery"]]'
VW=1600 VH=900 timeout 3000 node phases.mjs "http://localhost:8080/20261019-letters-from-the-sky/?fixdt=0.1&mute=1" ../shots/last- "$PLAN"

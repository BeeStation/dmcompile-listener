#!/bin/bash
cp /app/code/* .
DreamMaker test.dme
echo "---------------------------"
DreamDaemon test.dmb -close -verbose -ultrasafe

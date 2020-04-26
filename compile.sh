#!/bin/bash
cp /app/code/* .
DreamMaker test.dme
DreamDaemon test.dmb -close -verbose -ultrasafe

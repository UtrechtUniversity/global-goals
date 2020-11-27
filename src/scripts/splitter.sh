#!/bin/bash
mkdir splitting
cp data.csv splitting/
cd splitting
split -n l/$1 data.csv -d

# Remove unnecessaries
rm data.csv

# Rename to dataX.csv
rename 's/x(\d\d)/data$1.csv/' *
rename 's/data0(\d).csv/data$1.csv/' *



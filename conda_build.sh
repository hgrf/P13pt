#!/bin/bash

for py_ver in 2.7 3.6 3.7
do
    conda build --python $py_ver conda
done
#!/bin/bash

PKG_FILE="$(conda build --python 2.7 conda --output)"
PKG_DIR=$(dirname "${PKG_FILE}")
CONDA_BLD_DIR=$(dirname "${PKG_DIR}")
PKG_BASENAME=$(basename "${PKG_FILE}")

for PLATFORM in linux-32 linux-64 win-32 win-64 osx-64
do
    conda convert --platform $PLATFORM $PKG_FILE -o $CONDA_BLD_DIR
    anaconda upload $CONDA_BLD_DIR/$PLATFORM/$PKG_BASENAME
done

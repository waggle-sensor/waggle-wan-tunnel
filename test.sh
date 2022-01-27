#!/bin/bash

(
    cd ROOTFS/usr/bin
    python3 -m unittest discover ../../../tests
)

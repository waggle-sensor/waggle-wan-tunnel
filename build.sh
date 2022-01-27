#!/bin/bash -e

docker run -it --rm \
  -e NAME="waggle-wan-tunnel" \
  -e DESCRIPTION="Service which managers WAN traffic tunnel." \
  -e "MAINTAINER=sagecontinuum.org" \
  -v "$PWD:/repo" \
  waggle/waggle-deb-builder $*

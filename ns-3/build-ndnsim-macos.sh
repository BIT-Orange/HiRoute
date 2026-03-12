#!/bin/zsh
set -euo pipefail

export PKG_CONFIG_PATH="/opt/homebrew/opt/libxml2/lib/pkgconfig:/opt/homebrew/lib/pkgconfig"

./waf configure \
  --disable-python \
  --enable-examples \
  --boost-includes=/opt/homebrew/include \
  --boost-libs=/opt/homebrew/lib \
  --with-openssl=/opt/homebrew/opt/openssl@3

./waf -j"$(sysctl -n hw.ncpu)"

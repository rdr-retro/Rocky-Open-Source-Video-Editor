#!/bin/bash
# Detect OS to set correct classpath separator
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" || "$OSTYPE" == "cygwin" ]]; then
  SEP=";"
else
  SEP=":"
fi

java -Xmx4G -Xms2G -XX:+UseG1GC -XX:MaxGCPauseMillis=10 -Dsun.java2d.metal=true -Dapple.awt.graphics.UseQuartz=true --enable-native-access=ALL-UNNAMED -cp "lib/*${SEP}bin_user" rocky.app.RockyMain

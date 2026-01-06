#!/bin/bash
# Detect OS to set correct classpath separator
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" || "$OSTYPE" == "cygwin" ]]; then
  SEP=";"
else
  SEP=":"
fi

# AGGRESSIVE MODE: Allocate 16GB heap for HEVC 4K @ 60fps
# -Xmx16g = Maximum heap 16GB
# -Xms4g = Initial heap 4GB (faster startup)
# -XX:+UseG1GC = G1 Garbage Collector (better for large heaps)
java -Xmx16g -Xms4g -XX:+UseG1GC -cp "lib/*${SEP}bin_user" rocky.app.RockyMain


#!/bin/bash
# Detect OS to set correct classpath separator
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" || "$OSTYPE" == "cygwin" ]]; then
  SEP=";"
else
  SEP=":"
fi

java -cp "lib/*${SEP}bin_temp" MainAB

# Rocky Video Editor

High-performance video editing workstation with a C++ rendering core and Python PyQt5 interface.

## Minimum Requirements

* **OS**: macOS (Intel/Apple Silicon), Windows, or Linux.
* **Python**: 3.12 or higher.
* **C++ Compiler**: Clang or GCC with C++17 support.
* **FFmpeg**: System libraries (avcodec, avformat, swscale, swresample, swr).
* **Python Packages**: PyQt5, NumPy, pybind11.

## Fast Start (Compile and Run)

To automatically install dependencies, compile the C++ core, and launch the editor, run the following command in your terminal:

```bash
chmod +x run.sh && ./run.sh
```

## Project Structure

* `src/core/`: C++ Rendering Engine and Media Handling.
* `src/ui/`: PyQt5 User Interface and Timeline Logic.
* `run.sh`: Unified build and execution script.

---
*Copyright 2026 Rocky Video Editor.*

# Rocky Video Editor: The Ultimate Hybrid NLE Engine

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![PySide6](https://img.shields.io/badge/UI-PySide6-green.svg)](https://www.qt.io/qt-for-python)
[![C++](https://img.shields.io/badge/Core-C%2B%2B17-orange.svg)](https://isocpp.org/)
[![OpenFX](https://img.shields.io/badge/Plugins-OpenFX-purple.svg)](https://openfx.org/)
[![Performance](https://img.shields.io/badge/Performance-ZeroCopy-red.svg)](#)

Rocky Video Editor is a state-of-the-art, high-performance non-linear video editing (NLE) system designed for professionals who demand both ease of use and extreme computational efficiency. Built on a hybrid architecture, Rocky pairs a modern **PySide6** (Qt) frontend with a high-octane **C++17** rendering engine.

---

## 🏛️ System Architecture: The Hybrid Masterpiece

Rocky's unique strength lies in its "Engine-Frontend separation" philosophy.

### 🐍 Python Frontend (The Brain)
- **Framework**: Developed entirely in **PySide6**, providing a smooth 60Hz UI experience.
- **Workflow**: Orchestrates project models, handles non-destructive editing logic, and manages background workers for thumbnails, waveforms, and proxies.
- **Interoperability**: Uses **Pybind11** for low-latency communication with the core engine.

### ⚙️ Rocky Core C++ Engine (The Muscle)
- **High-Performance Rendering**: A multi-threaded C++17 library localized in `src/core`.
- **Zero-Copy Memory**: Uses direct memory descriptors to pass 4K frames between C++ and Python with almost zero overhead.
- **Master Clock Sync**: Ensures sub-millisecond synchronization between audio and video tracks, eliminating drift even in long projects.

---

## 🔥 Key Features

### 🎞️ Advanced Timeline & Editing
- **Professional Standard**: Support for Ripple Edits, Rolling Edits, and multi-track snapping.
- **Dynamic Fades**: Real-time crossfades and opacity/gain handles for every clip.
- **Multi-Format Support**: Native handling of various aspect ratios (16:9, 9:16, 21:9, 1:1) and variable frame rates.

### 🎵 Pro Audio Signal Chain
- **64-bit Internal Mixing**: Audio is mixed in high-precision 64-bit float space for infinite dynamic range.
- **Sample-Accurate Sync**: Every audio sample is aligned to the video master clock.
- **Mastering Suite**: Real-time VU meters and master gain limiters to prevent clipping.

### 🧩 OpenFX Plugin Ecosystem
- **Industry Standard**: Full support for the **OFX (OpenFX)** standard.
- **Custom Plugins**: Includes high-performance native plugins like "Invert Color".
- **Extensibility**: Easily add new effects by dropping shared libraries into the `plugins/` folder.

### ⚡ Smart Workflows
- **Background Proxies**: Automatic generation of lightweight proxies for seamless 4K editing on any hardware.
- **Localized Waveforms**: High-resolution audio peak analysis computed in the background.
- **Smart Thumbnailing**: Start, middle, and end keyframe extraction for visual navigation.

---

## 🏎️ Technical Performance & Optimization

Rocky is engineered to be **hardware-sympathetic**:

- **Predictive Seeking**: The engine maps I-frame (keyframe) locations to allow instantaneous seeking across huge video files.
- **Speculative Decoding**: While you view frame $N$, the engine is already preparing frame $N+1$ in a pre-fetch buffer.
- **SIMD Acceleration**: Core pixel blending loops utilize **AVX-512** and **SSE** instructions for massive throughput.
- **Apple Silicon Native**: Leveraging Apple’s **AMX** and Accelerate framework for elite performance on M1/M2/M3 chips.

---

## 🛠️ Installation & Build Guide

### Prerequisites
- **Python 3.12+**
- **FFmpeg 6.0+** (Development libraries: `libavcodec`, `libavformat`, `libswscale`, `libswresample`)
- **PySide6** and **Numpy**
- **Clang/GCC** with C++17 support

### Setup Instructions
1. Clone the repository and navigate to the project root.
2. Initialize and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Compile the C++ core:
   ```bash
   ./compile.sh
   ```
5. Run the editor:
   ```bash
   ./run.sh
   ```

---

## 🇪🇸 Versión en Castellano (Manual Extendido)

### El Futuro de la Edición de Vídeo
Rocky Video Editor no es solo una herramienta, es una plataforma de procesamiento multimedia diseñada para la era del vídeo 8K. Su núcleo C++ permite una manipulación de píxeles a velocidad nativa, mientras que PySide6 ofrece una interfaz flexible y moderna.

### Características Pro
1. **Motor Híbrido**: La potencia del C++17 combinada con la agilidad de Python.
2. **OpenFX Nativo**: Soporte para el estándar de la industria en plugins de efectos.
3. **Flujo de Trabajo Pro**: Proxies automáticos, edición Ripple/Rolling y gestión de color profesional.
4. **Audio de 64 bits**: Calidad de audio de estudio para tus producciones de vídeo.

### Optimizaciones de Hardware
Rocky está optimizado para procesadores multinúcleo modernos. En sistemas Mac, aprovechamos al máximo los chips **Apple Silicon** mediante el framework **Accelerate**, permitiendo una edición de vídeo 4K HDR fluida y sin interrupciones.

---

## 📂 Project Structure
- `src/core/`: The C++ high-performance engine source code.
- `src/ui/`: The PySide6 frontend logic and widgets.
- `src/infrastructure/`: Background workers and resource management.
- `plugins/`: OpenFX plugin source code and binaries.
- `venv/`: Local Python environment.

---
*Copyright © 2026 Rocky Video Editor Project. All Rights Reserved.*
*Engineered with precision. Rendered with excellence.*

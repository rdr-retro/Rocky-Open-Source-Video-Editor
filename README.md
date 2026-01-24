# Rocky Video Editor: The Ultimate Hybrid NLE Engine

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![PySide6](https://img.shields.io/badge/UI-PySide6-green.svg)](https://www.qt.io/qt-for-python)
[![C++](https://img.shields.io/badge/Core-C%2B%2B17-orange.svg)](https://isocpp.org/)
[![OpenFX](https://img.shields.io/badge/Plugins-OpenFX-purple.svg)](https://openfx.org/)
[![Performance](https://img.shields.io/badge/Performance-ZeroCopy-red.svg)](#)

Rocky Video Editor is a state-of-the-art, high-performance non-linear video editing (NLE) system designed for professionals who demand both ease of use and extreme computational efficiency. 

---

## 🏗 System Architecture Deep-Dive

Rocky's unique strength lies in its **"Engine-Frontend separation"** philosophy, bridging the gap between high-level GUI flexibility and low-level hardware performance.

### 🗺 Full System Schema

```mermaid
graph TD
    subgraph "UI LAYER (Python / PySide6)"
        MainWin[RockyApp] --> DockSystem[Flexible Docking System]
        DockSystem --> Panels[Panels: Timeline, Viewer, Assets, Subtitles]
        Panels --> Models[TimelineModel / ClipModel]
    end

    subgraph "INFRASTRUCTURE & WORKERS"
        Models -.-> Workers[Background Workers]
        Workers --> ProxyGen[Proxy Generator]
        Workers --> Waveform[Waveform Processor]
        Workers --> Thumbnails[Thumbnail Extractor]
        ProxyGen --> FFmpeg[FFmpeg Utils]
    end

    subgraph "NATIVE BRIDGE (pybind11)"
        Models <==> Bindings[bindings.cpp]
    end

    subgraph "ROCKY CORE (C++17)"
        Bindings <==> Engine[core::RockyEngine]
        Engine --> Tracks[core::Track System]
        Tracks --> Clips[core::Clip Rendering]
        Clips --> Sources[core::MediaSource]
        Sources --> VideoSrc[VideoSource - AVCodec/FFmpeg]
        Sources --> ImageSrc[ImageSource - AVCodec]
        Sources --> ColorSrc[ColorSource - Procedural]
        
        Clips --> Transforms[Affine Transformations: Rotate, Scale, Translate]
        Engine --> Blending[Multi-threaded Pixel Blending]
        Engine --> PluginHost[OpenFX Host]
        PluginHost --> Plugins[OpenFX Plugins: .ofx]
    end

    subgraph "HARDWARE ACCELERATION"
        Blending --> SIMD[SIMD: SSE / AVX-512]
        Blending --> Accelerate[macOS: Accelerate / AMX]
        VideoSrc --> HWDec[NVENC / VideoToolbox / QSV]
    end

### 🎞 Frame Rendering Pipeline (Data Flow)

```mermaid
sequenceDiagram
    participant UI as PySide6 (Python)
    participant ENG as RockyEngine (C++)
    participant CLIP as Clip::render()
    participant SRC as MediaSource (FFmpeg/Image)
    
    UI->>ENG: evaluate(timestamp, resolution)
    ENG->>ENG: Find active clips (Interval Tree)
    loop For each Active Clip
        ENG->>CLIP: render(localTime, w, h)
        CLIP->>SRC: getFrame(-1, -1) [Raw Access]
        SRC-->>CLIP: Raw Pixel Buffer
        CLIP->>CLIP: Apply Affine Transforms (Rotate/Scale/Translate)
        CLIP->>CLIP: Apply Opacity Envelope
        CLIP-->>ENG: Transformed Frame
    end
    ENG->>ENG: Multi-track Pixel Blending (Alpha Compositing)
    ENG-->>UI: Final Rendered Frame (Zero-Copy)
```

---

## 🛠 Component Breakdown

### 1. ⚡️ Rocky Core C++ (The Muscle)
Located in `src/core/`, this is a multi-threaded C++17 library responsible for the heavy lifting.
- **Engine**: Orchestrates the global playback head, master clock, and track-to-screen composition.
- **Interval Tree**: Uses advanced data structures to find active clips at any timestamp in $O(\log n)$ time.
- **Zero-Copy Performance**: Uses direct memory descriptors to pass high-res frames between C++ and Python with near-zero latency.
- **Transform Engine**: Handles complex visual math (Rotation, Scaling, Opacity) at the pixel buffer level.

### 2. 🔌 OpenFX Plugin Ecosystem
Rocky implements the **OpenFX (OFX)** standard, allowing third-party integration of high-performance effects.
- Direct host implementation in `src/core/ofx/`.
- Dynamic loading of `.ofx` or `.so` plugin files.
- Sample plugins provided in `plugins/` (e.g., Inversion, Color Correction).

### 3. 🐍 Python Frontend (The Brain)
Developed in **PySide6**, the UI provides a smooth, frame-accurate experience.
- **Dynamic Panels**: A Blender-inspired layout system where every panel can be split, joined, or swapped.
- **Asynchronous Workflow**: Workers handle heavy processing (FFmpeg) in separate threads to keep the UI at a constant 60Hz.

### 4. 🔤 Professional Subtitle Engine
- **Direct Transcription**: Integrated with OpenAI's **Whisper** for automatic subtitle generation.
- **WYSIWYG Positioning**: Drag and drop subtitles in the preview. Position is calculated in project-relative pixels for consistent export.
- **Anti-Distortion Tech**: Smart scaling logic ensures fonts maintain their native aspect ratio regardless of the project format (YouTube vs Shorts).

---

## 🚀 Build & Deployment

Rocky is now a fully **Multi-Platform** tool with robust automation scripts.

### 💻 Local Build

| OS | Build Command | Run Command |
| :--- | :--- | :--- |
| **macOS** | `./compile.sh` (Homebrew auto-setup) | `./run.sh` |
| **Linux** | `./compile.sh` (APT/DNF/Pacman) | `./run.sh` |
| **Windows** | `compile.bat` (Python/FFmpeg auto) | `run.bat` |

### 📦 Automated Windows Releases (CI/CD)
The project is configured with **GitHub Actions** (`.github/workflows/build-windows.yml`). 
- Simply push code from your Mac/Linux environment.
- Our cloud servers will compile the C++ core and bundle a standalone **Windows .exe** for you.
- Download the final binary from the **Actions > Artifacts** tab in GitHub.

---

## 🇪🇸 Versión en Castellano (Guía Técnica)

Rocky Video Editor no es solo un editor; es un motor híbrido diseñado para la eficiencia extrema.

### Características Principales:
1. **Núcleo de Alto Rendimiento**: Composición multi-hilo en C++17.
2. **Arquitectura Flexible**: Interfaz modular que se adapta a cualquier flujo de trabajo (de cine a TikTok).
3. **Subtítulos con IA**: Generación automática con precisión de píxel.
4. **Optimización de Hardware**: Soporte nativo para **Apple Silicon (M1/M2/M3)** mediante el framework Accelerate y HDR.

---

## 📂 Project Structure
- `src/core/`: High-performance C++ engine and OFX host.
- `src/ui/`: UI logic, panels, and custom widgets.
- `src/infrastructure/`: Background workers and FFmpeg integration tools.
- `src/platform/`: OS-specific hardware detection logic.
- `plugins/`: Creative effect libraries.
- `.github/workflows/`: Automated CI/CD configurations.

---
*Engineered with precision. Rendered with excellence.*

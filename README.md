# Rocky Video Editor
### Extreme Performance NLE | Powered by Rocky Core C++

Rocky Video Editor is a high-performance, professional-grade Non-Linear Editor (NLE) built for speed and precision. By combining a lightning-fast C++ Rendering Core with a premium PyQt5 User Interface, Rocky delivers a workstation-class experience on desktop systems.

---

## Key Features

### Rocky Core (C++ Engine)
*   **Hardware Accelerated Rendering**: Native support for Apple Silicon (Accelerate Framework) and high-performance vector processing.
*   **Time-Based Compositing**: Advanced interval-tree architecture for frame-accurate clip management and real-time preview.
*   **Smart Aspect Ratio Engine**: Automatic letterboxing, pillarboxing, and uniform scaling to preserve content integrity across different formats (16:9, 4:3, 9:16, 21:9).
*   **High-Fidelity Audio**: 44.1kHz/48kHz master bus with soft-limiting and linear gain control.

### Premium Workspace
*   **Unified UI Design**: High-contrast, dark-mode architecture with tailored workstation aesthetics.
*   **Advanced Aspect Ratio Presets**: One-click switching between Cinematic (21:9), Panorámico (16:9), Clásico (4:3), Vertical (9:16), and Social (1:1).
*   **Pro Video Settings**: Granular control over Frame Rates (Hz), Scale Filtering (Lanczos, Bicubic), and Custom Project Dimensions up to 8K.
*   **Dynamic Sidebar & Timeline**: Professional track management with live VU meters and synchronized playback tools.

### Optimization & Workflow
*   **Hybrid Proxy System**: Background proxy generation for smooth editing of high-bitrate 4K footage.
*   **Hardware Optimizer**: Automatically detects CPU cores, GPU VRAM, and RAM to configure optimal thread counts and cache sizes.
*   **Thread-Safe Architecture**: Mutex-protected engine access to prevent crashes during concurrent audio/video rendering.

---

## Project Structure

```bash
rocky-video-editor/
├── src/
│   ├── core/           # C++ Rendering Engine (Rocky Core)
│   ├── infrastructure/ # Background workers & hardware optimization
│   ├── platform/       # OS-specific integrations
│   └── ui/             # PyQt5 Modern Workstation Interface
├── venv/               # Python environment
└── run.sh              # Unified entry point
```

---

## Installation & Build

### Prerequisites
*   **Python 3.12+**
*   **FFmpeg Libraries** (avcodec, avformat, swscale, swresample)
*   **Clang/GCC** with C++17 support
*   **PyQt5** & **NumPy**

### Fast Start (macOS/Linux)
1. Clone the repository.
2. Ensure FFmpeg is installed via Homebrew or APT.
3. Run the setup and compile script:
   ```bash
   chmod +x run.sh
   ./run.sh
   ```

---

## Project Configuration
Settings can be adjusted in the Project Settings window (Gear icon), including:
*   **Video**: Target Hz, Resolution (Width/Height), Interpolation.
*   **Audio**: Sample Rate (Hz), Buffer latency.
*   **Proxies**: Auto-generation, resolution, and codec selection.
*   **Preview**: UI Hardware acceleration (Metal/DX12) and Preview scaling (1/2, 1/4).

---

## Author & Credits
Developed by Antigravity Team.
Specialized in Advanced Agentic Coding and High-Performance Media Frameworks.

---
*Copyright 2026 Rocky Video Editor. All rights reserved.*

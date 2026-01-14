# Rocky Video Editor

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![PySide6](https://img.shields.io/badge/UI-PySide6-green.svg)](https://www.qt.io/qt-for-python)
[![C++](https://img.shields.io/badge/Core-C%2B%2B17-orange.svg)](https://isocpp.org/)

## 🚀 Nueva Versión: Migración a PySide6

La característica principal de esta versión es la **migración completa de PyQt5 a PySide6** (Qt for Python). Este cambio estratégico proporciona una base más sólida y moderna para el desarrollo futuro, mejorando la compatibilidad con las últimas versiones de Qt y optimizando el rendimiento de la interfaz en sistemas de alta resolución (High DPI).

### ¿Por qué PySide6?
*   **Licencia más flexible**: Permite un desarrollo más abierto y alineado con los estándares actuales.
*   **Mejor integración con Python**: Soporte nativo para tipos de datos modernos y mejores herramientas de tipado.
*   **Rendimiento mejorado**: Mayor fluidez en la gestión de eventos y renderizado de la interfaz.

---

## English Version

Rocky Video Editor is a high-performance, non-linear video editing software designed to bridge the gap between ease of use and professional computational power. The architecture is a hybrid masterpiece: a low-level C++ rendering core (Rocky Core) paired with a modern, high-contrast **PySide6** user interface.

### Core Philosophy

The project was born from the need for a video editor that maximizes hardware potential, specifically targeting modern multi-core processors and specialized multimedia instruction sets like Apple's Accelerate framework. Unlike many script-based editors, Rocky leverages C++ for every pixel manipulation and audio mix, ensuring that the interface remains fluid while the engine performs heavy lifting in background threads.

### Key Features

1.  **PySide6 UI**: Modern, fluid workstation interface following professional NLE standards.
2.  **Rocky Core C++ Engine**: A high-performance library built on C++17 that handles video decoding via FFmpeg, real-time compositing, and audio processing.
3.  **Master Clock Synchronization**: Implemented using high-precision wall-clock timing to ensure zero audio-video drift.
4.  **Multi-Format Support**: Native support for 16:9, 9:16, 21:9, 4:3, and 1:1 aspect ratios.
5.  **Advanced Timeline**: Custom-built component supporting ripple edits, rolling edits, snapping, and fades.
6.  **Audio Mastering**: Real-time VU meters and master gain controls.
7.  **Proxy Workflow**: Automatic background proxy generation for 4K editing.

---

## Versión en Castellano

Rocky Video Editor es un software de edición de vídeo no lineal de alto rendimiento diseñado para cerrar la brecha entre la facilidad de uso y la potencia computacional profesional. La arquitectura es una obra maestra híbrida: un núcleo de renderizado de bajo nivel en C++ (Rocky Core) emparejado con una interfaz moderna de alto contraste en **PySide6**.

### Filosofía del Proyecto

El proyecto maximiza el potencial del hardware, apuntando a procesadores multinúcleo modernos y aceleración por GPU. Rocky utiliza C++ para cada manipulación de píxeles, asegurando que la interfaz de **PySide6** permanezca fluida incluso durante procesos de renderizado intensivos.

### Características Clave

1.  **Interfaz PySide6**: Estética profesional de estación de trabajo con flujo de trabajo NLE estándar.
2.  **Motor Rocky Core C++**: Librería de alto rendimiento construida en C++17 para decodificación y composición.
3.  **Sincronización Maestra**: Cero deriva de audio-vídeo mediante temporización de alta precisión.
4.  **Soporte Multiformato**: Relaciones de aspecto nativas para YouTube, TikTok, Cine y Redes Sociales.
5.  **Timeline Pro**: Soporte para ediciones complejas, imantado y fundidos automáticos.
6.  **Control de Audio**: Medidores VU en tiempo real y limitadores para evitar distorsión.
7.  **Proxies Automáticos**: Edición fluida de material 4K incluso en equipos estándar.

### Requisitos Mínimos

-   **Sistema Operativo**: macOS 11+, Windows 10/11, o Linux moderno.
-   **CPU**: Mínimo 4 núcleos (recomendado 8+).
-   **RAM**: 8GB (ideal 16GB+).
-   **Python**: 3.12 o superior.
-   **Dependencias**: FFmpeg (librerías de desarrollo) y PySide6.

### Instalación y Ejecución

Asegúrate de tener instalados los archivos de desarrollo de FFmpeg. Luego, ejecuta:

```bash
chmod +x run.sh && ./run.sh
```

---
*Copyright 2026 Rocky Video Editor. Todos los derechos reservados.*

# 🪨 Rocky Open Source Video Editor 🎬

**Rocky Open Source Video Editor** es un motor de edición de vídeo cinematográfico y profesional desarrollado íntegramente en **Java**. Diseñado para ofrecer una arquitectura de alta fidelidad, Rocky separa los conceptos de datos brutos, composición lógica y visualización dinámica para garantizar que tu visión creativa nunca se vea comprometida por limitaciones técnicas.

Este proyecto nace de la necesidad de un editor de código abierto que priorice el rendimiento en tiempo real y la precisión de color, utilizando tecnologías modernas de procesamiento de señales y gráficos vectoriales.

---

## 🚀 Arquitectura de Vanguardia: El Sistema de 3 Espacios

A diferencia de editores básicos que estiran las imágenes para que encajen en el visor, Rocky implementa un sistema vectorial de transformación inspirado en software de gama alta (Premiere, DaVinci Resolve, Vegas):

### 1. Espacio del Asset (Local)
Maneja la resolución real del medio original.
- **Independencia de Resolución**: Ya sea que trabajes con fotos 4K o vídeos 720p, Rocky mantiene los datos originales intactos.
- **Metadatos de Media**: Almacenamos el aspect ratio nativo para calcular escalas correctas en los pasos siguientes.

### 2. Espacio del Proyecto (Lienzo Lógico)
Es el espacio donde ocurre la magia. Todo se compone sobre un lienzo definido por la resolución del proyecto (ej. 1080p).
- **Transformaciones Lógicas**: Las coordenadas de posición, escala y rotación se guardan relativas al tamaño del proyecto, no al tamaño de la ventana.
- **Composición Multi-Capa**: El motor procesa todas las pistas activas en este espacio antes de enviarlas al visor.

### 3. Espacio del Visor (Viewport)
Una ventana inteligente que escala el lienzo del proyecto para que quepa en tu pantalla.
- **Letterboxing/Pillarboxing**: Si cambias el tamaño de la ventana, Rocky añade barras negras automáticamente para preservar la composición cinematográfica.
- **Pipeline de Visualización**: Convierte las coordenadas del ratón en el visor a coordenadas del proyecto para una interacción 1:1.

---

## ✨ Características Principales

### 🎞️ Línea de Tiempo Profesional (Core B)
- **Multitrack Dinámico**: Capas ilimitadas de vídeo y audio con gestión de profundidad.
- **Visualización de Ondas**: Renderizado de picos de audio asíncrono. El `PeakManager` escanea los archivos en hilos paralelos para mostrar la forma de onda sin ralentizar la UI.
- **Sistema de Fundidos (Fades)**: Control de opacidad avanzado con curvas de velocidad matemáticas:
    - **Linear**: Transición constante.
    - **Smooth**: Curva de suavizado Bézier (3x^2 - 2x^3).
    - **Fast/Slow**: Curvas de aceleración y desaceleración.
    - **Sharp**: Transiciones de alto contraste.
- **Control de Clips**: Menú contextual de propiedades y botón de acceso rápido "fx" para ajustes de transformación.

### 🎥 Motor de Renderizado & Review (Engine)
- **Layered Composition**: El `FrameServer` procesa y compone las imágenes. Las pistas inferiores en el índice (V1, V2...) se dibujan como capas superiores.
- **Transformaciones Vectoriales**:
    - **Posición**: Movimiento libre en píxeles de proyecto.
    - **Escala**: Ampliación uniforme sin pérdida de nitidez lógica.
    - **Rotación**: Rotación completa en grados sobre un punto de anclaje definido.
    - **Anchor Point**: Centro de transformación personalizable (0.5, 0.5 por defecto).
- **Espacio de Expansión**: Hemos rediseñado la interfaz para incluir un panel de **550px** a la izquierda del visor, dedicado a las futuras herramientas de efectos y control de colores (Grading/LUTs).

### ⌨️ Experiencia de Usuario Ágil
- **Atajos Globales**: Control de Play/Pause universal mediante la tecla **Espacio**. Gracias a un `KeyEventDispatcher` personalizado, el espacio funciona incluso si el foco está en un botón o barra de herramientas.
- **Pausa Inteligente**: El cabezal se detiene exactamente en el fotograma actual, permitiendo revisiones precisas cuadro a cuadro.
- **Estética Vibrant Dark**: Interfaz premium con diseño oscuro curado, fuentes Inter/Serif y micro-animaciones para feedback táctil.

---

## 🛠️ Estructura Detallada del Proyecto

Cada paquete en Rocky tiene una responsabilidad única y desacoplada:

### `MainAB.java`
El orquestador principal. Encargado de inicializar el entorno Swing, configurar el Look & Feel y ensamblar los componentes de las partes A, B y C en un layout `GridBagLayout` robusto.

### `egine/` (El Motor Central)
- **`engine.FrameServer`**: El compositor. Decide qué fotograma de qué clip debe mostrarse basándose en el tiempo del `AudioServer`.
- **`engine.AudioServer`**: El motor de audio que actúa como reloj maestro (Master Clock). Asegura que el vídeo siga al audio para evitar desincronizaciones.
- **`media/`**: Decodificadores nativos que utilizan **JavaCV** y **FFmpeg**. Optimizados para Apple Silicon (M4) mediante **VideoToolbox**.
- **`blueline/`**: Gestiona el estado de reproducción y la posición del playhead en microsegundos y fotogramas.

### `a/` y `b/` (Interfaz y Visualización)
- **`visor.VisualizerPanel`**: Implementa la lógica de Viewport Adaptativo y renderizado de alta calidad con interpolación bilineal.
- **`mastersound.MasterSoundPanel`**: Monitorización de audio con vúmetros que soportan picos dinámicos y colorimetría profesional.
- **`timeline.TimelinePanel`**: El componente más complejo, encargado de la interacción con el usuario, drag-and-drop de archivos y renderizado de clips.

---

## ⚙️ Especificaciones Técnicas y Compilación

### Requisitos del Sistema
- **Java**: JDK 17 o superior.
- **Memoria**: Mínimo 8GB RAM (Recomendado 16GB para edición 4K).
- **Procesador**: Optimizado para Apple Silicon (M1-M4) y procesadores multinúcleo x64.

### Dependencias Nativas
Rocky descarga automáticamente los binarios de FFmpeg adaptados a tu sistema operativo:
- **macOS**: `macosx-arm64` y `macosx-x86_64`.
- **Windows**: `windows-x86_64`.
- **Linux**: `linux-x86_64`.

### Guía de Compilación Profesional
```bash
# Otorgar permisos al script
chmod +x compile.sh
./compile.sh
```

### Ejecución
```bash
# Iniciar el editor
chmod +x run.sh
./run.sh
```

## 🌊 Deep Dive: El Pipeline de Sincronización

Uno de los mayores retos de Rocky es mantener la sincronización entre el audio y el vídeo. El sistema utiliza un modelo de **Master Clock** basado en el `AudioServer`:

-   **Pre-fetching**: El `FrameServer` no espera a que se necesite un fotograma; predice los siguientes 5 fotogramas y los decodifica de forma asíncrona.
-   **Drop Frame Logic**: Si el procesador no puede mantener el ritmo (ej. archivos 8K en hardware antiguo), Rocky prioriza el audio y "salta" fotogramas en el visor, asegurando que nunca haya un retraso acumulado.
-   **Interpolación Temporal**: El sistema calcula la posición del playhead en nanosegundos para una suavidad extrema en el movimiento de los clips.

---

## 🔬 Componentes del Motor (Deep Dive)

### FrameServer: El Compositor Inteligente
El `FrameServer` es un servicio desacoplado que utiliza un `ExecutorService` de un solo hilo para evitar colisiones de memoria en el renderizado. Su flujo es:
1.  Recibe una petición de tiempo (segundos).
2.  Busca los clips en el `TimelinePanel` que se solapan con ese tiempo.
3.  Ordena los clips por índice de pista para gestionar la transparencia (Z-index).
4.  Solicita los fotogramas al `MediaPool`.
5.  Aplica la pila de transformaciones (`ClipTransform`): **Translate -> Rotate -> Scale**.
6.  Dibuja el resultado en un `BufferedImage` del tamaño del proyecto.

### PeakManager: El Escáner de Audio
Para que el editor sea fluido, no podemos procesar el audio en tiempo real mientras dibujamos la línea de tiempo. El `PeakManager`:
-   Genera archivos de caché `.peaks` para evitar re-procesar archivos conocidos.
-   Utiliza un algoritmo de **Root Mean Square (RMS)** para calcular la potencia visual del audio.
-   Dibuja la onda de forma vectorial, permitiendo hacer zoom infinito en la línea de tiempo sin perder detalle.

---

## 📘 Glosario Técnico de Rocky

-   **Blueline**: La abstracción lógica de la línea de tiempo que contiene el estado de reproducción.
-   **Playhead**: El cabezal de reproducción (la línea roja) que marca el tiempo actual.
-   **ClipTransform**: Objeto que encapsula todos los datos espaciales de un clip (X, Y, Rot, Scale).
-   **Low-Res Preview**: Modo que reduce el lienzo del proyecto a una resolución de preview (ej. 360p) para edición fluida.
-   **Handle**: Los puntos de interacción en los bordes de los clips para ajustar duración o fundidos.

---

## 🛠️ Guía para Desarrolladores: Cómo Contribuir

Si quieres añadir una nueva funcionalidad, sigue esta guía de estilo y flujo:

### 1. Manejo de la UI (Swing)
-   Usa **Vanilla Swing**. Evita librerías externas de UI para mantener el proyecto ligero.
-   Dibuja directamente en `paintComponent` para componentes de alto rendimiento como la línea de tiempo.
-   Usa códigos hexadecimales para colores (`Color.decode("#121212")`) para mantener la coherencia estética.

### 2. Gestión de Memoria
-   Libera siempre los contextos de `Graphics2D` (`g.dispose()`).
-   No instancies objetos pesados dentro de bucles de renderizado.
-   Usa el `MediaPool` para acceder a recursos compartidos; nunca cargues el mismo archivo dos veces fuera del pool.

### 3. Workflow de Git
```bash
# Limpiar antes de subir (Muy importante)
sudo find . -name "*.class" -delete

# Crear una rama descriptiva
git checkout -b feature/panel-efectos

# Documentar cambios
# Asegúrate de actualizar el archivo walkthrough.md si añades una feature mayor.
```

---

## ❓ Solución de Problemas (Troubleshooting)

| Problema | Causa Probable | Solución |
| :--- | :--- | :--- |
| **Error de Compilación** | Java no está en el PATH. | Verifica con `javac -version`. |
| **Vídeo Lentificado** | El bitrate del original es muy alto. | Activa "Vista Previa de Baja Resolución". |
| **Audio Desfasado** | Diferente Sample Rate (44.1k vs 48k). | Rocky resampleará automáticamente, pero usar 48kHz es recomendado. |
| **Error de Permisos** | Archivos .class creados por root. | Usa `sudo ./compile.sh` para resetear permisos. |

---

## 🏁 Hoja de Ruta (Roadmap) y Futuro

El desarrollo de Rocky sigue una metodología de "Composición Primero".

### Fase 1: Cimientos (Completado ✅)
- [x] **Arquitectura de 3 espacios**: Independencia Asset -> Proyecto -> Viewport.
- [x] **Motor de reproducción**: Sincronización precisa audio/vídeo.
- [x] **Transformaciones Vectoriales**: Posición, escala y rotación funcional.
- [x] **Atajos de teclado**: Control global por barra de espacio.

### Fase 2: Edición Avanzada (En progreso 🚧)
- [ ] **Efectos de Clip**: Implementación de filtros en tiempo real (Brillo, Contraste, Blur).
- [ ] **Corrección de Color**: Soporte para curvas RGB y carga de LUTs (.cube).
- [ ] **Transiciones**: Sistema de solapamiento para fundidos cruzados automáticos.
- [ ] **Keyframes**: Animación de transformaciones a lo largo del tiempo.

### Fase 3: Post-Producción (Próximamente 🔮)
- [ ] **Generador de Títulos**: Capas de texto con soporte para fuentes personalizadas.
- [ ] **Exportación Multi-Perfil**: Presets para YouTube, Instagram (9:16) y ProRes.
- [ ] **Audio Mixer**: Panel de mezcla por canales individuales.

---

## 📄 Licencia y Créditos

Este proyecto se distribuye bajo la licencia Open Source propia del equipo Rocky.
-   **Core Lead**: Desarrollado con tecnología Java Modern.
-   **Librerías**: Gracias a los equipos de **JavaCV** y **FFmpeg**.

**Rocky Open Source Video Editor** - *Diseñado para el editor, construido para el rendimiento.*

© 2026 Rocky Project Team. *Desarrollado con ❤️ para la comunidad creativa mundial.*

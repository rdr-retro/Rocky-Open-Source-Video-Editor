# Rocky Open Source Video Editor

**Rocky Open Source Video Editor** es un motor de edición de vídeo cinematográfico y profesional desarrollado íntegramente en **Java**. Diseñado para ofrecer una arquitectura de alta fidelidad, Rocky separa los conceptos de datos brutos, composición lógica y visualización dinámica para garantizar que tu visión creativa nunca se vea comprometida por limitaciones técnicas.

Este proyecto nace de la necesidad de un editor de código abierto que priorice el rendimiento en tiempo real y la precisión de color, utilizando tecnologías modernas de procesamiento de señales y gráficos vectoriales.

---

## Arquitectura de Vanguardia: El Sistema de 3 Espacios

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

## Características Principales

### Línea de Tiempo Profesional (Core B)
- **Multitrack Dinámico**: Capas ilimitadas de vídeo y audio con gestión de profundidad.
- **Visualización de Ondas**: Renderizado de picos de audio asíncrono. El `PeakManager` escanea los archivos en hilos paralelos para mostrar la forma de onda sin ralentizar la UI.
- **Sistema de Fundidos (Fades)**: Control de opacidad avanzado con curvas de velocidad matemáticas.
- **Dithering de Transición**: Implementación de un patrón de *stippling* (punteado) en las áreas de fade para una visualización técnica y estética superior en el timeline.
- **Control de Clips**: Menú contextual de propiedades y botón de acceso rápido "fx" para ajustes de transformación.

### Motor de Renderizado & Review (Engine)
- **Layered Composition**: El `FrameServer` procesa y compone las imágenes. Las pistas inferiores en el índice (V1, V2...) se dibujan como capas superiores.
- **Transformaciones Vectoriales**:
    - **Posición**: Movimiento libre en píxeles de proyecto.
    - **Escala**: Ampliación uniforme sin pérdida de nitidez lógica.
    - **Rotación**: Rotación completa en grados sobre un punto de anclaje definido.
- **Espacio de Expansión**: Interfaz rediseñada con un panel de **550px** lateral para herramientas de efectos y corrección de color.

---

## Sistema de Undo/Redo (Historial Infinito)

Rocky implementa un sistema de gestión de estado basado en el patrón **Command**. Cada acción significativa en el timeline se encapsula en un objeto que sabe cómo aplicarse y cómo revertirse.

### Arquitectura del HistoryManager
El `HistoryManager` gestiona dos pilas (vía `java.util.Stack`):
1.  **Undo Stack**: Almacena acciones realizadas.
2.  **Redo Stack**: Almacena acciones revertidas.

### Acciones Soportadas
- **Clip Movement**: Movimiento horizontal (tiempo) y vertical (cambio de pista).
- **Media Ingestion**: Adición de nuevos archivos mediante drag-and-drop.
- **Property Changes**: Ajustes en curvas de fade, transformaciones y nombres de clips.

> [!NOTE]
> El sistema de Undo es atómico. Si una acción de movimiento desplaza múltiples clips, se trata como un único evento en el historial.

---

## Persistencia: El Formato .rocky

Hemos abandonado los formatos genéricos para implementar nuestra propia estructura de serialización basada en archivos `.rocky`.

### Estructura del Archivo
Los archivos `.rocky` (anteriormente `.berga`) son archivos XML/JSON estructurados que contienen:
-   **Project Metadata**: Resolución base (1920x1080), FPS nativo y duración total.
-   **Track Definitions**: Listado de pistas de vídeo y audio con sus estados (Mute, Solo, Lock).
-   **Clip Data**: Referencias absolutas a archivos de media, puntos de entrada/salida (In/Out points) y su posición en el timeline.
-   **Transformation Keyframes**: Datos de animación para posición, escala y rotación.

### ProjectManager
El `ProjectManager` es la clase encargada de:
-   **Auto-Save**: Sistema de guardado preventivo cada 5 minutos.
-   **Relative Path Mapping**: Intenta resolver rutas de archivos si el proyecto se mueve de carpeta o unidad de disco.

---

## Guía Interna para Desarrolladores (Internal API)

Para extender Rocky, es fundamental entender los tres niveles de interacción:

### 1. El Nivel de Datos (`egine.media`)
Para añadir soporte a un nuevo formato de archivo, debes extender `MediaDecoder`.
-   `decodeFrame(long microsecond)`: Debe devolver un `BufferedImage` o un frame nativo de FFmpeg.
-   `getDuration()`: Precisión necesaria en microsegundos.

### 2. El Nivel de Interacción (`b.timeline`)
La lógica de la línea de tiempo se divide en:
-   **`TimelinePanel`**: El lienzo principal de dibujo.
-   **`TimelineInteractionHandler`**: Gestiona los clics, drags y selecciones.
-   **`TimelineRenderer`**: Optimiza el dibujo de clips visibles (Culling).

### 3. El Nivel de Playback (`egine.blueline`)
Si deseas controlar el playhead programáticamente:
```java
Blueline master = Blueline.getInstance();
master.seek(5000000); // Salta a los 5 segundos
master.play();        // Inicia la reproducción
```

---

## Estructura de Archivos del Proyecto

| Directorio | Propósito |
| :--- | :--- |
| `src/rocky/core` | Lógica de negocio, motores de audio/video y persistencia. |
| `src/rocky/ui` | Componentes Swing, paneles de timeline y visor. |
| `bin/` | Clases compiladas organizadas por paquetes. |
| `lib/` | Dependencias externas (JavaCV, FFmpeg, FlatLaf). |
| `egine/` | Paquete histórico que contiene el "Engine" (legacy/core mix). |

---

## Especificaciones Técnicas y Compilación

### Requisitos del Sistema
- **Java**: JDK 17 o superior.
- **Memoria**: Mínimo 8GB RAM (Recomendado 16GB).
- **Procesador**: Optimizado para Apple Silicon (M1-M4) vía hardware acceleration.

### Guía de Compilación
```bash
# 1. Limpiar versiones previas
sudo find . -name "*.class" -delete

# 2. Otorgar permisos
chmod +x compile.sh

# 3. Compilar
./compile.sh
```

---

## Hoja de Ruta (Roadmap)

### Fase 2: Edición Avanzada (En progreso [/])
- [x] **Undo/Redo System**: Integración total de acciones.
- [x] **Visual Dithering**: Estética de fades mejorada.
- [ ] **Efectos en Tiempo Real**: Blur y corrección gamma básica.
- [ ] **Multi-Select**: Selección de varios clips para movimiento en bloque.

### Fase 3: Post-Producción (Próximamente [.])
- [ ] **Generador de Títulos**: Capas de texto enriquecido.
- [ ] **Exportación ProRes/H264**: Pipeline de renderizado final.
- [ ] **Audio Mixer**: Mezcla por bus y efectos de audio (EQ/Reverb).

---

## Licencia y Créditos

Este proyecto se distribuye bajo la licencia Open Source propia del equipo Rocky.
-   **Core Lead**: Desarrollado con tecnología Java Modern.
-   **Librerías**: JavaCV, FFmpeg, y FlatLaf para la UI.

**Rocky Open Source Video Editor** - *Simplificando la complejidad del cine digital.*

© 2026 Rocky Project Team. *Desarrollado para la comunidad creativa mundial.*

---

## Notas de Desarrollo Adicionales

### El Desafío de la Sincronía
Rocky utiliza el `AudioServer` como reloj de referencia. Si el sistema detecta un retraso en el renderizado de vídeo superior a 50ms, el `FrameServer` saltará automáticamente al siguiente fotograma clave disponible para re-sincronizar el flujo visual.

### Renderizado de Ondas de Audio
Para evitar bloqueos en la interfaz (UI Freezing), el `PeakManager` utiliza un pool de hilos (`FixedThreadPool`) proporcional al número de núcleos de la CPU. Las ondas se dibujan mediante un sistema de caché de memoria de dos niveles:
1.  **L1 Cache**: Datos de picos en memoria RAM.
2.  **L2 Cache**: Archivos binarios temporales en disco.

---

## Preguntas Frecuentes (FAQ)

**¿Por qué Java para un editor de vídeo?**
Java ofrece una portabilidad excelente y, gracias a librerías como JavaCV (Ffmpeg wrapper), podemos acceder a aceleración por hardware nativa mientras mantenemos una lógica de UI segura y fácil de mantener.

**¿Cómo funciona el escalado en el visor?**
El `VisualizerPanel` calcula una matriz de transformación afín basada en el ratio del proyecto vs. el ratio del componente Swing. Esto asegura que los píxeles siempre se interpelen de forma correcta, ya sea usando *Nearest Neighbor* para velocidad o *Bicubic* para calidad final.

**¿Puedo usar plugins externos?**
Próximamente implementaremos un sistema de carga dinámica de clases (.jar) que permitirá crear filtros y exportadores personalizados sin modificar el núcleo del motor.

---

### Mantenimiento y Limpieza
Para mantener el repositorio limpio de binarios, se recomienda ejecutar el siguiente comando antes de realizar cualquier commit:
```bash
# Elimina todos los archivos compilados en bin y src
find . -type f -name "*.class" -delete
```

---

*Fin del documento de especificaciones de Rocky Open Source Video Editor.*

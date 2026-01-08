# Rocky Open Source Video Editor

Rocky es un editor de video de código abierto de alto rendimiento desarrollado en Java y optimizado específicamente para la arquitectura Apple Silicon (M4). Diseñado con una filosofía de baja latencia y fluidez extrema.

## Estado Actual: Reproducción Fluida Garantizada
Tras una profunda reestructuración del motor de renderizado, Rocky ahora ofrece una experiencia de reproducción fluida a 60 FPS incluso con archivos 4K HDR.

## Arquitectura y Optimización Técnica

Para conseguir esta estabilidad, se han implementado las siguientes mejoras estructurales:

### 1. Eliminación del bucle de invalidación de caché
Se ha implementado un sistema de revisión de diseño que solo permite invalidar la caché cuando hay un cambio real en la estructura del proyecto. Esto protege la persistencia de los datos precargados durante la reproducción, evitando lecturas de disco innecesarias.

### 2. Optimización multihilo para Apple Silicon M4
El servidor de fotogramas utiliza 10 hilos de ejecución para aprovechar todos los núcleos del procesador. Se ha sustituido el procesamiento en paralelo de clips superpuestos por una ejecución secuencial optimizada para evitar la contención de recursos en las librerías nativas.

### 3. Estabilización de la memoria de video (VRAM)
Se ha corregido el error en el pipeline de renderizado de macOS mediante un intercambio atómico de imágenes en memoria RAM. Esto permite que el sistema operativo gestione la aceleración Metal de forma nativa y segura, eliminando fallos en el hilo de flasheo de Java2D.

### 4. Gestión del hilo de interfaz (EDT)
Se ha optimizado la carga de la interfaz de usuario suspendiendo el renderizado de miniaturas en el timeline durante la reproducción. Las etiquetas de información se actualizan de forma regulada (10Hz) para dedicar la máxima prioridad al flujo de video.

### 5. Sincronización robusta del decodificador
Los bloqueos de seguridad en la capa de medios aseguran que la decodificación y la clonación del buffer de imagen ocurran de forma atómica, eliminando parpadeos o corrupciones visuales en el motor de pre-renderizado.

### 6. Configuración de la Máquina Virtual Java (JVM)
El sistema utiliza el recolector de basura G1GC optimizado para latencias bajas, activación forzosa de Metal y una asignación de 4GB de memoria dedicada para garantizar la estabilidad a altas frecuencias de cuadro.

## Características Principales
*   Arquitectura de 3 Capas: Separación estricta entre Fuente, Motor y UI.
*   Soporte Proxy: Generación automática de proxies para flujos de trabajo en alta resolución.
*   Sistema de Plugins: Efectos, transiciones y generadores modulares.
*   Audio Master Clock: Sincronización A/V perfecta basada en hardware de audio.
*   Vegas-Style UX: Interfaz familiar diseñada para la velocidad y la eficiencia.

## Instalación y Uso

### Prerrequisitos
*   Java 21 o superior.
*   FFmpeg (incluido en las librerías nativas).

### Compilación
Primero, asegúrate de que los scripts tengan permisos de ejecución y luego compila el proyecto:
```bash
chmod +x compile.sh run.sh
./compile.sh
```

### Ejecución
Para iniciar el editor con las optimizaciones para Mac M4:
```bash
./run.sh
```

---
Desarrollado para la comunidad de creadores.

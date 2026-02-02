import sys
import os
import time
import subprocess

def run_diagnosis():
    # Detect project root (two levels up from src/diagnostics)
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
    os.chdir(project_root)
    
    print("====================================================")
    print("   ROCKYCORE MULTIMEDIA DIAGNOSTIC SYSTEM v1.0")
    print("====================================================\n")
    
    print("[1/3] Iniciando el editor con la sonda de diagnóstico activada...")
    # Lanza el editor y captura la salida
    log_file = "diagnostic_session.log"
    
    try:
        # Ejecutar el comando run.sh redirigiendo la salida
        print("INFO: Reproduce el audio que falla y luego cierra el editor para generar el reporte.")
        
        with open(log_file, "w") as f:
            process = subprocess.Popen(["./run.sh"], stdout=f, stderr=subprocess.STDOUT)
            process.wait()
            
    except Exception as e:
        print(f"ERROR: Fallo al iniciar el editor: {e}")
        return

    print("\n[2/3] Analizando los datos capturados...")
    
    anomalies = {
        "REWIND": 0,
        "GAP": 0,
        "STARVATION": 0,
        "BUFFER_FULL": 0
    }
    
    if os.path.exists(log_file):
        with open(log_file, "r") as f:
            lines = f.readlines()
            for line in lines:
                if "[REWIND_DETECTED]" in line: anomalies["REWIND"] += 1
                if "[GAP_DETECTED]" in line: anomalies["GAP"] += 1
                if "[STARVATION]" in line: anomalies["STARVATION"] += 1
                if "[BUFFER_FULL]" in line: anomalies["BUFFER_FULL"] += 1
    else:
        print(f"ERROR: No se encontró el archivo de log {log_file}")
        return

    print("\n[3/3] REPORTE DE DIAGNÓSTICO FINAL")
    print("----------------------------------------------------")
    
    if sum(anomalies.values()) == 0:
        print("✅ No se detectaron anomalías críticas en el flujo de datos.")
        print("Sugerencia: Si el audio sigue fallando, podría ser un problema del driver de audio del sistema o de la tasa de muestreo del hardware.")
    else:
        print(f"❌ SE DETECTARON {sum(anomalies.values())} ANOMALÍAS:")
        
        if anomalies["REWIND"] > 0:
            print(f"   - {anomalies['REWIND']} Eventos de REBOBINADO: El motor solicitó datos de un tiempo pasado.")
            print("     DIAGNÓSTICO: Hay un error en la lógica de 'playback_start_tick' o en el incremento de muestras.")
            
        if anomalies["STARVATION"] > 0:
            print(f"   - {anomalies['STARVATION']} Eventos de HAMBRUNA: El buffer de C++ se vació por completo.")
            print("     DIAGNÓSTICO: El hilo de Python (AudioWorker) es demasiado lento o el buffer es demasiado pequeño.")

        if anomalies["GAP"] > 0:
            print(f"   - {anomalies['GAP']} Saltos de Audio: Faltan muestras entre bloques.")
            print("     DIAGNÓSTICO: Redondeo matemático incorrecto en el TPF (Ticks Per Frame).")

    print("----------------------------------------------------")
    print(f"Detalles guardados en: {os.path.abspath(log_file)}")
    print("====================================================")

if __name__ == "__main__":
    run_diagnosis()

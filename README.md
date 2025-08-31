# Análisis de Tráfico de Red con PowerShell y Python

Este proyecto permite **capturar y analizar tráfico de red en Windows** utilizando un script en **PowerShell** y un analizador en **Python**.  
  
  Se generan métricas clave como:
  - Paquetes enviados/recibidos por segundo  
  - Bytes por segundo (bps)  
  - Distribuciones de tamaños de paquetes  
  - Serie temporal del tráfico  
  
Además, se incluyen visualizaciones gráficas para facilitar la interpretación.
---

##  Aviso importante de seguridad
El análisis de tráfico de red puede exponer **información sensible** (IPs, conexiones activas, patrones de tráfico).  
Este proyecto es **únicamente con fines educativos y de investigación personal**.  

---

## 👥 Autores
- **Julian Rincón**  
- **Paula Caballero**

---

## 🔧 Requisitos

### Windows
- PowerShell (incluido en Windows 10/11)
- Permisos de ejecución de scripts:  
  ```powershell
  Set-ExecutionPolicy Bypass -Scope Process
  ```
  
  # Python
  - Python 3.12+
  - Librerías:
    ```bash
    pip install pandas matplotlib
    ```
---

# Metodología
Captura de datos
  - Herramienta: PowerShell (Get-NetAdapterStatistics)
  - Adaptador: Ethernet
  - Intervalo de muestreo: 0.2 segundos
  - Duración: 600 segundos (10 minutos)
  - Salida: net_samples.jsonl

# Procesamiento y análisis

- Lenguaje: Python 3.12
- Librerías: pandas, matplotlib, numpy
- Técnicas aplicadas:

  - Cálculo de diferencias acumuladas (delta_recv, delta_sent, delta_time)
  - Análisis de distribución de tamaños de paquetes
  - Cálculo de frecuencia de arribos de tráfico 
  - Serie temporal de bytes por segundo (bps)

---

# Ejecución
  1. Captura de tráfico con PowerShell
  Ruta del script: `Analisis de trafico/paquetesred.ps1`
  ```bash
  powershell -ExecutionPolicy Bypass -File "C:\Users\<usuario>\paquetesred.ps1"
  ```
  El script genera un archivo `net_samples.jsonl` donde cada línea corresponde a un registro JSON independiente.
  
  Ejemplo (simplificado y censurado por seguridad):
  ```jsonl
    {
    "Timestamp": "2025-08-31T12:00:01Z",
    "BytesReceived": 123456,
    "BytesSent": 654321,
    "PacketsReceived": 120,
    "PacketsSent": 98
  }
  ```
# Análisis en Python

  Archivo: `analizar_paquetes.py`
  ```python
  import pandas as pd
  import json
  import matplotlib.pyplot as plt
  
  # Leer archivo JSONL con BOM seguro
  registros = []
  with open("net_samples.jsonl", "r", encoding="utf-8-sig") as f:
      for linea in f:
          registros.append(json.loads(linea))
  
  # Convertir a DataFrame
  df = pd.DataFrame(registros)
  
  # Calcular diferencias (delta)
  df["delta_time"] = df["Timestamp"].diff().dt.total_seconds().fillna(1)
  df["delta_recv"] = df["BytesReceived"].diff().fillna(0)
  df["delta_sent"] = df["BytesSent"].diff().fillna(0)
  
  # Serie temporal de bytes por segundo
  df["bps_recv"] = df["delta_recv"] / df["delta_time"].replace(0, pd.NA)
  df["bps_sent"] = df["delta_sent"] / df["delta_time"].replace(0, pd.NA)
  
  # --- Gráficas ---
  plt.figure(figsize=(12,6))
  plt.plot(df["Timestamp"], df["bps_recv"], label="Bytes recibidos/s", color="blue")
  plt.plot(df["Timestamp"], df["bps_sent"], label="Bytes enviados/s", color="orange")
  plt.xlabel("Tiempo")
  plt.ylabel("Bytes por segundo")
  plt.title("Serie temporal de tráfico de red")
  plt.legend()
  plt.grid()
  plt.tight_layout()
  plt.show()
  ```
---
# Resultados del Análisis

1. Escala de paquetes en el tiempo

  - Se observan picos pronunciados en momentos específicos (hasta ~30 MB transferidos en un instante). 
  - La mayor parte del tiempo la actividad fue baja, con ráfagas puntuales.
  **Conclusión: Tráfico en ráfagas, no uniforme.**

2. Frecuencia relativa de tamaños de paquetes

  - Predominio de paquetes pequeños (ACKs, DNS, mensajes de control).
  - Pocos paquetes grandes (MB), vinculados a transferencias intensivas.
  **Conclusión: Distribución asimétrica, típica de tráfico de Internet.**

3. Frecuencia relativa de tiempos entre arribos

  - La mayoría de arribos se dieron cada 0.2 – 0.25 s, coherente con el muestreo.
  - Intervalos largos → periodos de baja actividad.
  **Conclusión: Tráfico en ráfagas regulares con picos de congestión.**

4. Serie temporal de bytes por segundo (bps)

  - Promedio de recepción: ~2.79 MB/s
  - Promedio de envío: ~2.56 MB/s
  - Máximo de recepción: ~71.5 MB/s
  - Máximo de envío: ~114.4 MB/s
    
**Conclusión:
La red soportó ráfagas superiores a 100 MB/s.
Recepción promedio mayor, pero el envío alcanzó picos más altos.**

# Comparación con análisis de archivos en disco

Similitud con tráfico de red:

  - Muchos elementos pequeños.
  - Pocos elementos grandes que concentran el volumen.

Diferencia clave:

  - Archivos en disco → estáticos.
  
  - Tráfico de red → dinámico, con variaciones en el tiempo.   

# Conclusiones Generales

  - Tráfico típico de redes de datos: predominio de paquetes pequeños y picos ocasionales.
  - Distribución de larga cola: muchos paquetes pequeños, pocos muy grandes que concentran la mayoría del volumen.
  - La red mostró capacidad de sostener ráfagas intensas sin pérdida de datos aparente.
  - La comparación con el sistema de archivos confirma un patrón estadístico común en sistemas de información.
---
# Graficas 

<img width="1252" height="712" alt="image" src="https://github.com/user-attachments/assets/35f606bf-9091-4df1-a9e6-67ac35ee67b1" />
Escala de paquetes en el tiempo

---
<img width="1002" height="712" alt="image" src="https://github.com/user-attachments/assets/44732e98-52e1-4aa9-9307-bc8f86953935" />
Frecuencia relativa de tamaños de paquiete

---
<img width="1002" height="712" alt="image" src="https://github.com/user-attachments/assets/fe136f11-9747-4ec6-b3eb-93c23e0d0497" />
Frecuencia relativa de tiempos dentre arribos

---
<img width="1252" height="712" alt="image" src="https://github.com/user-attachments/assets/6d9e4d81-5daa-41d3-9327-5f132cd6bd2b" />
Serie temporal de bytes por segundo

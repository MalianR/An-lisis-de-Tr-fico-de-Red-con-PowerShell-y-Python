# Análisis de Tráfico de Red con PowerShell y Python

Este proyecto captura, almacena y analiza estadísticas de tráfico de red en Windows, complementado con un análisis comparativo de tamaños de archivos en disco.

El objetivo es observar el comportamiento del tráfico (bytes, paquetes, tamaños promedio, tiempos entre arribos) y compararlo con distribuciones de datos en sistemas de archivos.
  
---

##  Aviso importante de seguridad
El análisis de tráfico de red puede exponer **información sensible** (IPs, conexiones activas, patrones de tráfico).  
Este proyecto es **únicamente con fines educativos y de investigación personal**.  

---

## Objetivo de la actividad

  1. Captura de tráfico de red en un adaptador específico durante un periodo extendido (1h 30m).
  
  2. Análisis de los paquetes capturados:
  
    - Escala del tráfico en el tiempo.
    
    - Frecuencia relativa de tamaños de paquetes.
    
    - Frecuencia relativa de los tiempos entre arribos.
  
  3. Análisis de disco duro:
  
    - Distribución de tamaños de archivos.
    
    - Comparación con el comportamiento del tráfico de red.
---

## 🔧 Requisitos

### Windows
- PowerShell (incluido en Windows 10/11)
- Permisos de ejecución de scripts:  
  ```powershell
  Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy Bypass
  ```
  
  # Python
  - Python 3.12+
  - Librerías:
    ```bash
    pip install pandas matplotlib numpy
    ```
## Librerías utilizadas en el análisis

  - json (incluida en Python estándar): leer los registros del archivo JSONL.
  
  - pandas: manejo de datos, diferencias entre valores, rolling windows, estadísticas.
  
  - matplotlib: graficar resultados (series de tiempo, histogramas, CCDF).
  
  - numpy: cálculos numéricos (percentiles, transformaciones logarítmicas).
  
  - os / pathlib: recorrer el disco y obtener tamaños de archivos.
---

# Codigo Utilizado
  # Script PowerShell – Captura de tráfico
  Archivo: `Analisis de trafico/paquetesred.ps1`
  El script usa `Get-NetAdapterStatistics` para capturar métricas de red y exportarlas a un archivo `.jsonl`.
  
  ```powershell
  param(
  [string]$AdapterName = "Ethernet",    # Nombre del adaptador (por defecto Ethernet)
  [double]$Interval = 0.2,              # Intervalo de muestreo en segundos
  [int]$Duration = 5400,                # Duración total en segundos (1h 30m)
  [string]$OutFile = "C:\Users\jrinc\Desktop\net_samples.jsonl"
)

if ([string]::IsNullOrEmpty($AdapterName)) {
  Write-Host "Adaptadores disponibles:"
  Get-NetAdapter | Select-Object -Property Name, Status, LinkSpeed | Format-Table -AutoSize
  exit
}

$dir = Split-Path $OutFile -Parent
if (!(Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
if (Test-Path $OutFile) { Remove-Item $OutFile -Force }

Write-Host "Iniciando captura en $AdapterName durante $Duration segundos..."
$end = (Get-Date).AddSeconds($Duration)

while ((Get-Date) -lt $end) {
  $now = [DateTime]::UtcNow.ToString("o")
  $s = Get-NetAdapterStatistics -Name $AdapterName -ErrorAction Stop
  $obj = @{
    timestamp = $now
    received_bytes = $s.ReceivedBytes
    sent_bytes = $s.SentBytes
    received_unicast_packets = $s.ReceivedUnicastPackets
    sent_unicast_packets = $s.SentUnicastPackets
    received_discards = $s.ReceivedDiscardedPackets
    received_errors = $s.ReceivedErrors
  }
  $obj | ConvertTo-Json -Compress | Out-File -FilePath $OutFile -Append -Encoding utf8
  Start-Sleep -Milliseconds ([int]($Interval * 1000))
}

Write-Host "Captura completada. Archivo generado: $OutFile"

 ```
  
 Ejecución desde Windows PowerShell:
  ```Powershell
    {
  powershell -ExecutionPolicy Bypass -File "C:\Users\jrinc\Desktop\Analisis de trafico\paquetesred.ps1" -AdapterName "Ethernet" -Duration 5400  
    }
  ```
# Script Python – Análisis del tráfico

  Archivo: `analizar_paquetes.py`
  Este script procesa el archivo `net_samples.jsonl`, calcula métricas, genera gráficos y analiza tamaños de archivos en disco.

  Incluye:

    - Escala de tráfico en tiempo (bps y pps).
    
    - Histogramas de tamaños promedio de paquetes.
    
    - Histogramas de tiempos entre arribos (interarrival times).
    
    - Estadísticas rápidas (media, p50, p95, p99, máximo).
    
    - Escaneo de tamaños de archivos en disco y comparación.
  
  ```python
  import json
import os
import math
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# -------------------------- Parámetros --------------------------
RUTA_JSON = r"C:\Users\jrinc\Desktop\net_samples.jsonl"  # archivo JSONL del PowerShell
OUT_DIR = r"C:\Users\jrinc\Desktop\analisis_trafico"     # carpeta de salida para gráficos y CSV
ROLL_WINDOW = 30                                         # muestras para suavizado (ajusta según tu intervalo)
GUARDAR_FIGS = True

# Escaneo de disco (ajusta la raíz y exclusiones)
DISK_ROOT = r"C:\Users\jrinc"                            # carpeta a analizar
EXCLUDE_DIRS = {r"C:\Windows", r"C:\Program Files", r"C:\Program Files (x86)"}  # puedes vaciar este set
MAX_FILES = None  # None = sin límite; o p.ej. 500000 para acotar

# ---------------------- Utilidades de plotting -------------------
def ensure_dir(p):
    Path(p).mkdir(parents=True, exist_ok=True)

def savefig(name):
    if GUARDAR_FIGS:
        ensure_dir(OUT_DIR)
        plt.savefig(os.path.join(OUT_DIR, f"{name}.png"), bbox_inches="tight", dpi=150)

def log_bins(series, bins=50, offset=1.0):
    """Construye bins logarítmicos para series positivas. offset evita log(0)."""
    s = series[np.isfinite(series) & (series > 0)]
    if s.empty:
        return np.linspace(0, 1, bins)
    mn, mx = s.min(), s.max()
    if mn <= 0:
        mn = offset
    return np.logspace(math.log10(mn), math.log10(mx), bins)

def robust_diff(s):
    """Diferencia con protección contra resets: negativos -> NaN -> 0."""
    d = s.diff()
    d[d < 0] = np.nan
    return d.fillna(0)

def percentiles(x, qs=(50, 95, 99)):
    return {f"p{q}": np.nanpercentile(x, q) for q in qs}

# ------------------------- Carga JSONL ---------------------------
if not os.path.exists(RUTA_JSON):
    raise FileNotFoundError(f"No existe el archivo: {RUTA_JSON}")

registros = []
with open(RUTA_JSON, "r", encoding="utf-8-sig") as f:
    for linea in f:
        linea = linea.strip()
        if not linea:
            continue
        registros.append(json.loads(linea))

df = pd.DataFrame(registros)

# Validación de columnas esperadas
cols_req = {
    "timestamp",
    "received_bytes", "sent_bytes",
    "received_unicast_packets", "sent_unicast_packets",
    "received_discards", "received_errors",
}
faltan = cols_req - set(df.columns)
if faltan:
    raise ValueError(f"Faltan columnas en el JSONL: {faltan}")

df["timestamp"] = pd.to_datetime(df["timestamp"])
df = df.sort_values("timestamp").reset_index(drop=True)

# --------------------- Deltas y métricas base --------------------
df["delta_time"] = df["timestamp"].diff().dt.total_seconds().fillna(0)
df.loc[df["delta_time"] <= 0, "delta_time"] = np.nan  # proteger

df["delta_recv_bytes"] = robust_diff(df["received_bytes"])
df["delta_sent_bytes"]  = robust_diff(df["sent_bytes"])

df["delta_recv_pkts"] = robust_diff(df["received_unicast_packets"])
df["delta_sent_pkts"] = robust_diff(df["sent_unicast_packets"])

# bps / pps (bytes/seg y paquetes/seg)
df["bps_recv"] = df["delta_recv_bytes"] / df["delta_time"]
df["bps_sent"] = df["delta_sent_bytes"]  / df["delta_time"]
df["pps_recv"] = df["delta_recv_pkts"]   / df["delta_time"]
df["pps_sent"] = df["delta_sent_pkts"]   / df["delta_time"]

# Tamaño promedio de paquete por intervalo (bytes / pkt)
df["avg_pkt_size_recv"] = df["delta_recv_bytes"] / df["delta_recv_pkts"].replace(0, np.nan)
df["avg_pkt_size_sent"] = df["delta_sent_bytes"] / df["delta_sent_pkts"].replace(0, np.nan)

# Interarribo aproximado (segundos por paquete) = 1 / pps
df["iat_recv"] = 1.0 / df["pps_recv"]
df["iat_sent"] = 1.0 / df["pps_sent"]

# Suavizados (rolling)
df["bps_recv_smooth"] = df["bps_recv"].rolling(ROLL_WINDOW, min_periods=1).median()
df["bps_sent_smooth"] = df["bps_sent"].rolling(ROLL_WINDOW, min_periods=1).median()
df["pps_recv_smooth"] = df["pps_recv"].rolling(ROLL_WINDOW, min_periods=1).median()
df["pps_sent_smooth"] = df["pps_sent"].rolling(ROLL_WINDOW, min_periods=1).median()

# ---------------------- 1) Escala en el tiempo -------------------
plt.figure(figsize=(11,5))
plt.plot(df["timestamp"], df["bps_recv"], label="bps recibidos", linewidth=0.8)
plt.plot(df["timestamp"], df["bps_sent"], label="bps enviados", linewidth=0.8, alpha=0.8)
plt.plot(df["timestamp"], df["bps_recv_smooth"], label="bps recv (mediana móvil)", linewidth=1.8)
plt.plot(df["timestamp"], df["bps_sent_smooth"], label="bps sent (mediana móvil)", linewidth=1.8)
plt.title("Escala de tráfico (Bytes por segundo) en el tiempo")
plt.xlabel("Tiempo"); plt.ylabel("Bytes/segundo"); plt.legend(); plt.tight_layout()
savefig("01_escala_bps")
plt.show()

plt.figure(figsize=(11,5))
plt.plot(df["timestamp"], df["pps_recv"], label="pps recibidos", linewidth=0.8)
plt.plot(df["timestamp"], df["pps_sent"], label="pps enviados", linewidth=0.8, alpha=0.8)
plt.plot(df["timestamp"], df["pps_recv_smooth"], label="pps recv (mediana móvil)", linewidth=1.8)
plt.plot(df["timestamp"], df["pps_sent_smooth"], label="pps sent (mediana móvil)", linewidth=1.8)
plt.title("Escala de tráfico (Paquetes por segundo) en el tiempo")
plt.xlabel("Tiempo"); plt.ylabel("Paquetes/segundo"); plt.legend(); plt.tight_layout()
savefig("02_escala_pps")
plt.show()

# --------------- 2) Frecuencia relativa: tamaño de paquetes ------
# Usamos tamaño promedio por intervalo como proxy (no hay tamaño por paquete individual)
bins_size = log_bins(pd.concat([df["avg_pkt_size_recv"], df["avg_pkt_size_sent"]]), bins=50, offset=1.0)

plt.figure(figsize=(9,5))
plt.hist(df["avg_pkt_size_recv"].dropna(), bins=bins_size, alpha=0.6, label="Recv (avg pkt size)", density=True)
plt.hist(df["avg_pkt_size_sent"].dropna(), bins=bins_size, alpha=0.6, label="Sent (avg pkt size)", density=True)
plt.xscale("log")
plt.title("Frecuencia relativa de tamaños de paquetes (promedio por intervalo)")
plt.xlabel("Bytes por paquete (promedio, escala log)"); plt.ylabel("Densidad")
plt.legend(); plt.tight_layout()
savefig("03_frecuencia_tamano_paquetes")
plt.show()

# --- 3) Frecuencia relativa de tiempos entre arribos (aprox 1/pps) ---
bins_iat = log_bins(pd.concat([df["iat_recv"], df["iat_sent"]]), bins=50, offset=1e-6)

plt.figure(figsize=(9,5))
plt.hist(df["iat_recv"].replace([np.inf, -np.inf], np.nan).dropna(), bins=bins_iat, alpha=0.6, label="Recv IAT", density=True)
plt.hist(df["iat_sent"].replace([np.inf, -np.inf], np.nan).dropna(), bins=bins_iat, alpha=0.6, label="Sent IAT", density=True)
plt.xscale("log")
plt.title("Frecuencia relativa de tiempos entre arribos (aprox)")
plt.xlabel("Segundos entre paquetes (escala log)"); plt.ylabel("Densidad")
plt.legend(); plt.tight_layout()
savefig("04_frecuencia_interarribos")
plt.show()

# --------------------- Estadísticas rápidas ----------------------
def stats_block(name, s):
    s = s.replace([np.inf, -np.inf], np.nan)
    out = {
        "mean": float(np.nanmean(s)),
        "max": float(np.nanmax(s)),
        **{k: float(v) for k, v in percentiles(s).items()},
    }
    print(f"\n{name}:")
    for k, v in out.items():
        print(f"  {k:>6}: {v:,.4f}")
    return out

ensure_dir(OUT_DIR)
summary = {}
summary["bps_recv"] = stats_block("Bytes/seg (recv)", df["bps_recv"])
summary["bps_sent"] = stats_block("Bytes/seg (sent)", df["bps_sent"])
summary["pps_recv"] = stats_block("Paquetes/seg (recv)", df["pps_recv"])
summary["pps_sent"] = stats_block("Paquetes/seg (sent)", df["pps_sent"])
summary["avg_pkt_size_recv"] = stats_block("Tamaño promedio paquete (recv)", df["avg_pkt_size_recv"])
summary["avg_pkt_size_sent"] = stats_block("Tamaño promedio paquete (sent)", df["avg_pkt_size_sent"])

pd.DataFrame(summary).to_csv(os.path.join(OUT_DIR, "resumen_estadistico.csv"))

# ================== Análisis de disco: tamaños de archivos ==================
def iter_files(root, exclude_dirs=None, max_files=None):
    n = 0
    for dirpath, dirnames, filenames in os.walk(root):
        # Excluir directorios pesados/sistema si se especifica
        if exclude_dirs:
            if any(os.path.abspath(dirpath).startswith(os.path.abspath(ed)) for ed in exclude_dirs):
                continue
        for fn in filenames:
            fp = os.path.join(dirpath, fn)
            try:
                size = os.path.getsize(fp)
                yield size
                n += 1
                if max_files is not None and n >= max_files:
                    return
            except Exception:
                # Permisos/corrupción/etc.
                continue

print("\nEscaneando tamaños de archivos del disco (esto puede tardar, según la ruta y los permisos)...")
sizes = list(iter_files(DISK_ROOT, EXCLUDE_DIRS, MAX_FILES))
sizes_array = np.array(sizes, dtype=float)

if sizes_array.size == 0:
    print("No se pudieron leer tamaños de archivos (revisa permisos/ruta).")
else:
    # Histograma de tamaños (log)
    bins_files = log_bins(pd.Series(sizes_array), bins=60, offset=1.0)

    plt.figure(figsize=(9,5))
    plt.hist(sizes_array, bins=bins_files, density=True, alpha=0.75)
    plt.xscale("log")
    plt.title(f"Frecuencia relativa de tamaños de archivos\nRuta: {DISK_ROOT}")
    plt.xlabel("Tamaño de archivo (bytes, escala log)"); plt.ylabel("Densidad")
    plt.tight_layout(); savefig("05_frecuencia_tamanos_archivos")
    plt.show()

    # CCDF (cola complementaria) para ver heavy-tail
    s_sorted = np.sort(sizes_array[np.isfinite(sizes_array) & (sizes_array > 0)])
    ccdf = 1.0 - np.arange(1, len(s_sorted)+1) / len(sorted(s_sorted))
    plt.figure(figsize=(9,5))
    plt.loglog(s_sorted, ccdf)
    plt.title("CCDF de tamaños de archivos (log-log)")
    plt.xlabel("Tamaño (bytes)"); plt.ylabel("P(X > x)")
    plt.grid(True, which="both", ls="--", alpha=0.4)
    plt.tight_layout(); savefig("06_ccdf_tamanos_archivos")
    plt.show()

    # Resumen estadístico de archivos
    print("\nEstadísticas tamaños de archivos:")
    file_stats = {
        "count": int(len(s_sorted)),
        "mean": float(np.mean(s_sorted)),
        "median": float(np.median(s_sorted)),
        "p95": float(np.percentile(s_sorted, 95)),
        "p99": float(np.percentile(s_sorted, 99)),
        "max": float(np.max(s_sorted)),
    }
    for k, v in file_stats.items():
        print(f"  {k:>6}: {v:,.2f}")

    # Guardar CSV de tamaños (muestra si es enorme)
    df_files = pd.DataFrame({"size_bytes": s_sorted})
    # Si hay demasiados, muestrea para CSV
    if len(df_files) > 1_000_000:
        df_files = df_files.sample(1_000_000, random_state=42).sort_values("size_bytes")
    df_files.to_csv(os.path.join(OUT_DIR, "tamanos_archivos.csv"), index=False)
  ```
---
# Resultados obtenidos

1. Escala de paquetes en el tiempo
   <img width="1634" height="731" alt="01_escala_bps" src="https://github.com/user-attachments/assets/6ad033d7-9d69-4be5-b6b2-a14c42f278f9" />
   <img width="1634" height="731" alt="02_escala_pps" src="https://github.com/user-attachments/assets/84af780e-8964-4b95-9a7c-6d09f6e4a91c" />

  Las gráficas de bytes por segundo (BPS) y paquetes por segundo (PPS) muestran un comportamiento irregular con picos muy elevados en momentos específicos.
  
    - En recepción (recv), los bytes por segundo alcanzaron hasta 67 MB/s, mientras que el promedio fue de ~911 KB/s.
    
    - En envío (sent), los bytes por segundo llegaron a un máximo de 125 MB/s, con un promedio mucho menor de ~529 KB/s.
  
  Esto indica que la red presenta ráfagas de tráfico donde se concentran grandes volúmenes de datos en intervalos muy cortos, típicos de descargas o transmisiones de alto consumo.
  Los PPS reflejan la misma dinámica: la mayoría de los intervalos con baja actividad, pero con picos de hasta 84 mil paquetes por segundo.

2. Distribución de tamaños promedio de paquetes
  <img width="1334" height="729" alt="03_frecuencia_tamano_paquetes" src="https://github.com/user-attachments/assets/5b73aa3a-a202-4677-ad7b-e023d67c91a6" />

  El histograma de tamaños promedio de paquetes revela una fuerte concentración en los valores bajos:
    
    - Recepción: la mediana fue de 116 bytes, y el promedio ~402 bytes.
    
    - Envío: la mediana fue de ~90 bytes, con un promedio de ~143 bytes.
  
  Esto sugiere que gran parte del tráfico está compuesto por paquetes pequeños (posiblemente de control, ACKs o protocolos interactivos), aunque se observan también paquetes grandes cercanos al límite de MTU (1500 bytes), relacionados con transferencia de archivos o streaming.
  
  La dualidad de tamaños (muy pequeños y algunos grandes) es típica en redes heterogéneas.

3. Distribución de tiempos entre arribos
   <img width="1334" height="729" alt="04_frecuencia_interarribos" src="https://github.com/user-attachments/assets/f980c474-c445-47c0-aa32-c4d749d7094b" />

  La gráfica de tiempos entre arribos (interarrival times) muestra que:
  
    - La mayoría de los paquetes tienen intervalos muy cortos (10⁻⁴ a 10⁻³ segundos), lo que refleja alta concurrencia y tráfico sostenido.
    
    - Existen también intervalos mayores, pero mucho menos frecuentes, que corresponden a períodos de baja actividad o espera entre ráfagas.
  
  Este patrón evidencia una red donde predomina un flujo continuo de paquetes con ráfagas muy densas en ciertos momentos.

4. Análisis de tamaños de archivos en disco
  <img width="1334" height="725" alt="05_frecuencia_tamanos_archivos" src="https://github.com/user-attachments/assets/7a407ad2-322d-45a3-970d-e7d03128bace" />
  <img width="1333" height="729" alt="06_ccdf_tamanos_archivos" src="https://github.com/user-attachments/assets/cfb63ab7-a230-48bb-82a6-ad0d7c622c54" />


  El análisis de 384,820 archivos muestra una distribución claramente heavy-tailed (cola pesada):
  
    - La mayoría de los archivos son muy pequeños (mediana de apenas 3 KB).
    
    - El promedio se eleva a 290 KB, pero este valor está fuertemente influenciado por unos pocos archivos muy grandes.
    
    - El 95% de los archivos son menores a ~158 KB, pero en el 1% superior aparecen archivos de varios MB y hasta 25.4 GB.
  
  La gráfica CCDF en escala log-log confirma la existencia de una cola larga, donde pocos archivos representan una porción desproporcionada del espacio en disco.
  
5. Comparación entre red y disco
   
  - Similitud: Tanto en la red como en el disco, las distribuciones siguen patrones de cola pesada. En ambos casos, la mayoría de los eventos son pequeños (paquetes pequeños, archivos pequeños), pero unos pocos casos extremos concentran gran parte de los recursos (ráfagas masivas de tráfico o archivos enormes).
  
  - Diferencia: En la red, los extremos se deben a la dinámica temporal (picos de transmisión), mientras que en disco se deben a la naturaleza del contenido almacenado (documentos pequeños vs. archivos ultimedia grandes).  

6. Estadísticas principales

  1. Red – Bytes/segundo (recv/sent):
  
    - Recv → media: 911,144 / máx: 67,373,730 / p95: 5,371,910
    
    - Sent → media: 528,880 / máx: 125,574,091 / p95: 94,260
  
  2. Red – Paquetes/segundo (recv/sent):
  
    - Recv → media: 764 / máx: 45,884 / p95: 4,326
    
    - Sent → media: 600 / máx: 84,230 / p95: 1,236
  
  3. Tamaño promedio de paquete:
  
    - Recv → media: 401 bytes / máx: 2,328 / p95: 1,462
    
    - Sent → media: 142 bytes / máx: 1,492 / p95: 550
  
  4. Archivos en disco:
  
    - Count: 384,820
    
    - Tamaño medio: 290 KB
    
    - Mediana: 3 KB
    
    - p95: 158 KB
    
    - p99: 1.4 MB
    
    - Máx: 25.4 GB
---

## Conclusión:
  1. El tráfico de red es altamente variable: predominan periodos de baja actividad intercalados con picos extremos de bytes y paquetes por segundo.
  
  2. Los paquetes pequeños son los más frecuentes, pero los paquetes grandes (cercanos al MTU) marcan la diferencia en los momentos de alta transmisión.
  
  3. Los tiempos entre arribos cortos confirman la concurrencia de múltiples flujos de datos simultáneos.
  
  4. Los tamaños de archivos en disco y el tráfico de red comparten un comportamiento estadístico de cola pesada, aunque por razones distintas.
  
  5. El análisis comparativo muestra cómo los sistemas de datos (en tránsito y en reposo) presentan estructuras similares: muchos elementos pequeños y pocos elementos grandes que dominan el uso de recursos.

  6. El tráfico de red presenta picos extremos que elevan las colas de la distribución (heavy-tail).
  
  7. Los tamaños de paquetes promedios muestran concentración en valores bajos (paquetes de control y tráfico interactivo) y algunos cercanos al MTU (~1500 bytes).
  
  8. Los tiempos entre arribos son muy cortos, mostrando alta concurrencia de paquetes en instantes específicos.
  
  9. El análisis de disco confirma que los tamaños de archivos también son heavy-tailed: la mayoría pequeños, unos pocos extremadamente grandes.
  
  10. Comparativamente, tanto tráfico de red como archivos en disco siguen distribuciones asimétricas con colas largas, aunque por razones distintas:
  
    - En red → eventos de transmisión/descarga.
    
    - En disco → naturaleza de los datos almacenados (muchos pequeños documentos, pocos grandes multimedia).

---
## Autores

  - Julian Rincón
  
  - Paula Caballero


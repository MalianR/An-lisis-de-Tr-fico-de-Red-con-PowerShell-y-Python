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

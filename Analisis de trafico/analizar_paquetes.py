import json
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import numpy as np


# Ruta del archivo generado por PowerShell
ruta_json = r"C:\Users\jrinc\Desktop\net_samples.jsonl"

# Leer JSONL (usando utf-8-sig para evitar BOM)
registros = []
with open(ruta_json, "r", encoding="utf-8-sig") as f:
    for linea in f:
        registros.append(json.loads(linea.strip()))

df = pd.DataFrame(registros)

# Convertir timestamps a datetime
df["timestamp"] = pd.to_datetime(df["timestamp"])

# Calcular diferencias (bytes y tiempo)
df["delta_recv"] = df["received_bytes"].diff().fillna(0)
df["delta_sent"] = df["sent_bytes"].diff().fillna(0)
df["delta_time"] = df["timestamp"].diff().dt.total_seconds().fillna(0)

# --------------- Escala de paquetes -----------------
plt.figure(figsize=(10,5))
plt.plot(df["timestamp"], df["delta_recv"], label="Bytes recibidos")
plt.plot(df["timestamp"], df["delta_sent"], label="Bytes enviados")
plt.title("Escala de paquetes en el tiempo")
plt.xlabel("Tiempo")
plt.ylabel("Bytes")
plt.legend()
plt.tight_layout()
plt.show()

# --------------- Frecuencia relativa de tamaños -----------------
plt.figure(figsize=(8,5))
plt.hist(df["delta_recv"], bins=50, alpha=0.6, label="Recv")
plt.hist(df["delta_sent"], bins=50, alpha=0.6, label="Sent")
plt.title("Frecuencia relativa de tamaños de paquetes")
plt.xlabel("Bytes")
plt.ylabel("Frecuencia")
plt.legend()
plt.tight_layout()
plt.show()

# --------------- Frecuencia relativa de tiempos entre arribos -----------------
plt.figure(figsize=(8,5))
plt.hist(df["delta_time"][df["delta_time"] > 0], bins=50, color="purple", alpha=0.7)
plt.title("Frecuencia relativa de tiempos entre arribos")
plt.xlabel("Segundos")
plt.ylabel("Frecuencia")
plt.tight_layout()
plt.show()

# --------------- Serie temporal de bytes por segundo -----------------
df["bps_recv"] = df["delta_recv"] / df["delta_time"].replace(0, np.nan)
df["bps_sent"] = df["delta_sent"] / df["delta_time"].replace(0, np.nan)

# Opcional: reemplazar NaN por 0 para graficar sin huecos
df["bps_recv"] = df["bps_recv"].fillna(0)
df["bps_sent"] = df["bps_sent"].fillna(0)

plt.figure(figsize=(10,5))
plt.plot(df["timestamp"], df["bps_recv"], label="bps recibidos", color="blue")
plt.plot(df["timestamp"], df["bps_sent"], label="bps enviados", color="red")
plt.title("Serie temporal de bytes por segundo")
plt.xlabel("Tiempo")
plt.ylabel("Bytes por segundo")
plt.legend()
plt.tight_layout()
plt.show()


# Estadísticas rápidas
print("\n📊 Estadísticas de tráfico (bytes/segundo):")
print("Promedio recv:", df["bps_recv"].mean(skipna=True))
print("Promedio sent:", df["bps_sent"].mean(skipna=True))
print("Máximo recv:", df["bps_recv"].max(skipna=True))
print("Máximo sent:", df["bps_sent"].max(skipna=True))

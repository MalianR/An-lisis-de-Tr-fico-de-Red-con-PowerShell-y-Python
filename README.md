# Analisis-de-Trafico-de-Red-con-PowerShell-y-Python
Este proyecto permite capturar y analizar tráfico de red en **Windows** utilizando un script en **PowerShell** y un analizador en **Python**.  
Se generan métricas clave como paquetes enviados/recibidos y bytes por segundo, además de visualizaciones gráficas.

# **Aviso importante de seguridad:**  
El análisis de tráfico de red puede exponer información sensible (IPs, conexiones activas, patrones de tráfico).  
Este proyecto es **únicamente con fines educativos y de investigación personal**.  

---

# Autores
  - **Julian Rincón**  
  - **Paula Caballero**

---

# Requisitos

  # Windows
  - PowerShell (incluido en Windows 10/11)
  - Permisos de ejecución de scripts (`Set-ExecutionPolicy`)
  
  # Python
  - Python 3.12+
  - Librerías:
    ```bash
    pip install pandas matplotlib
    ```
# Captura de tráfico

El script [paquetesred.ps1](Analisis%20de%20trafico/paquetesred.ps1 captura estadísticas de red cada segundo durante 10 minutos y las guarda en formato JSONL.

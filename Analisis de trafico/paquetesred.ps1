param(
  [string]$AdapterName = "Ethernet",    # Nombre del adaptador (por defecto Ethernet)
  [double]$Interval = 0.2,              # Intervalo de muestreo en segundos
  [int]$Duration = 600,                 # Duración total en segundos (10 minutos)
  [string]$OutFile = "C:\Users\jrinc\Desktop\net_samples.jsonl"
)

if ([string]::IsNullOrEmpty($AdapterName)) {
  Write-Host "Adaptadores disponibles:"
  Get-NetAdapter | Select-Object -Property Name, Status, LinkSpeed | Format-Table -AutoSize
  Write-Host "`nReejecuta con -AdapterName 'Ethernet' (ejemplo)."
  exit
}

# Crear carpeta si no existe
$dir = Split-Path $OutFile -Parent
if (!(Test-Path $dir)) {
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
}

# Borrar archivo previo si existe
if (Test-Path $OutFile) { Remove-Item $OutFile -Force }

Write-Host "Iniciando captura en adaptador $AdapterName durante $Duration segundos..."
Write-Host "Guardando en: $OutFile"

$end = (Get-Date).AddSeconds($Duration)
while ((Get-Date) -lt $end) {
  $now = [DateTime]::UtcNow.ToString("o")   # Timestamp ISO 8601 UTC
  try {
    $s = Get-NetAdapterStatistics -Name $AdapterName -ErrorAction Stop
  } catch {
    Write-Error "No se pudo leer estadísticas del adaptador $AdapterName. Revisa nombre/privilegios."
    exit
  }

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

Write-Host "✅ Captura completada. Archivo generado: $OutFile"

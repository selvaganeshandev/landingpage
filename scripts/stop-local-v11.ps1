# Stops only the C:\promptmaxxv11 processes (leaves the other install running).
Get-CimInstance Win32_Process | Where-Object {
  $_.CommandLine -match 'promptmaxxv11' -or
  ($_.CommandLine -match 'runserver 900[01]') -or
  ($_.CommandLine -match 'v11(default|seo)@') -or
  ($_.CommandLine -match 'port 9080')
} | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
# beat has no distinguishing arg; match by working directory via parent python path
Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -like 'C:\promptmaxxv11\*' } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Write-Host "stopped promptmaxxv11 processes"

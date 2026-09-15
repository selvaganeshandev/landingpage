# Starts the C:\promptmaxxv11 local stack headless (SETUP-LOCAL.md §7), isolated
# from the "Orginal promptmaxx" install on the same machine:
#   backend :9000   engine :9001   frontend :9080   DB llm_monitor_v11   Redis db 6
$root = "C:\promptmaxxv11"
$py   = "$root\backend\.venv\Scripts\python.exe"
New-Item -ItemType Directory -Force "$root\logs" | Out-Null
$env:PYTHONIOENCODING = "utf-8"

function Svc($name, $dir, $exe, $argline) {
  Start-Process -FilePath $exe -ArgumentList $argline -WorkingDirectory $dir `
    -WindowStyle Hidden `
    -RedirectStandardOutput "$root\logs\$name.log" `
    -RedirectStandardError  "$root\logs\$name.err.log"
}

Svc backend  "$root\backend"  $py "manage.py runserver 9000 --noreload"
Svc engine   "$root\engine"   $py "manage.py runserver 9001 --noreload"
# node names carry a v11 prefix so they do not clash with the other install's default@/seo@ workers
Svc worker   "$root\engine"   $py "-m celery -A llm_monitor_engine worker --pool=solo -n v11default@%h -Q celery --loglevel=info"
Svc seo      "$root\engine"   $py "-m celery -A llm_monitor_engine worker --pool=solo -n v11seo@%h -Q seo,seo_instant --loglevel=info"
Svc beat     "$root\engine"   $py "-m celery -A llm_monitor_engine beat --loglevel=info"
Svc frontend "$root\frontend" "npm.cmd" "run dev -- --port 9080 --strictPort"
Write-Host "started; check $root\logs\*.err.log"

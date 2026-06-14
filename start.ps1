$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$VenvPython = Join-Path $Backend ".venv\Scripts\python.exe"
$EnvFile = Join-Path $Root ".env"
$Requirements = Join-Path $Backend "requirements.txt"
$ReadyFile = Join-Path $Backend ".venv\.ready"

function Import-EnvFile {
    param([string] $Path)

    if (!(Test-Path $Path)) {
        return
    }

    foreach ($rawLine in Get-Content $Path) {
        $line = $rawLine.Trim()
        if ($line.Length -eq 0 -or $line.StartsWith("#") -or !$line.Contains("=")) {
            continue
        }

        $parts = $line.Split("=", 2)
        [Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim(), "Process")
    }
}

Import-EnvFile $EnvFile

if (!(Test-Path $VenvPython)) {
    Write-Host "Creating backend virtual environment..."
    python -m venv (Join-Path $Backend ".venv")
}

if (Test-Path $ReadyFile) {
    $readyHash = Get-Content $ReadyFile -ErrorAction SilentlyContinue | Select-Object -First 1
    $requirementsHash = (Get-FileHash $Requirements -Algorithm SHA256).Hash
} else {
    $readyHash = ""
    $requirementsHash = (Get-FileHash $Requirements -Algorithm SHA256).Hash
}

if ($readyHash -ne $requirementsHash) {
    Write-Host "Installing backend dependencies..."
    & $VenvPython -m pip install -r $Requirements
    Set-Content -Path $ReadyFile -Value $requirementsHash
}

if (!(Test-Path (Join-Path $Frontend "node_modules"))) {
    Write-Host "Installing frontend dependencies..."
    Push-Location $Frontend
    try {
        npm.cmd install
    }
    finally {
        Pop-Location
    }
}

Write-Host ""
Write-Host "VeriLens AI is starting..."
Write-Host "Frontend: http://localhost:5173"
Write-Host "Backend:  http://localhost:8000"
Write-Host "Press Ctrl+C to stop."
Write-Host ""

$backendJob = Start-Job -Name "VeriLensBackend" -ScriptBlock {
    param($BackendPath, $PythonPath)

    Set-Location $BackendPath
    & $PythonPath -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
} -ArgumentList $Backend, $VenvPython

try {
    Push-Location $Frontend
    npm.cmd run dev -- --host 127.0.0.1 --port 5173
}
finally {
    Pop-Location
    Stop-Job $backendJob -ErrorAction SilentlyContinue
    Remove-Job $backendJob -Force -ErrorAction SilentlyContinue
}

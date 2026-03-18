# setup.ps1 — Porypal setup for Windows PowerShell

Write-Host ""
Write-Host "  Porypal setup"
Write-Host "  -------------"
Write-Host ""

# -- Python check --------------------------------------------------------------
# Windows uses 'python', not 'python3'
$pythonCmd = $null
foreach ($cmd in @("python", "python3", "py")) {
    $found = Get-Command $cmd -ErrorAction SilentlyContinue
    if ($found) {
        $version = & $cmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
        $major   = & $cmd -c "import sys; print(sys.version_info.major)" 2>$null
        $minor   = & $cmd -c "import sys; print(sys.version_info.minor)" 2>$null
        if ([int]$major -ge 3 -and [int]$minor -ge 10) {
            $pythonCmd = $cmd
            Write-Host "  + Python $version ($cmd)"
            break
        } else {
            Write-Host "  ! Python $version found but 3.10+ required, skipping $cmd"
        }
    }
}

if (-not $pythonCmd) {
    Write-Host ""
    Write-Host "  x Python 3.10+ not found."
    Write-Host "    Download from: https://python.org"
    Write-Host "    Make sure to check 'Add Python to PATH' during install."
    exit 1
}

# -- Node check ----------------------------------------------------------------
$nodeFound = Get-Command node -ErrorAction SilentlyContinue
if (-not $nodeFound) {
    Write-Host ""
    Write-Host "  x Node.js not found."
    Write-Host "    Download from: https://nodejs.org"
    exit 1
}

$nodeVersion = & node --version
$nodeMajor = [int]($nodeVersion -replace "v(\d+)\..*", '$1')
if ($nodeMajor -lt 18) {
    Write-Host ""
    Write-Host "  x Node $nodeVersion found but 18+ required."
    Write-Host "    Download from: https://nodejs.org"
    exit 1
}
Write-Host "  + Node $nodeVersion"

# -- Python venv ---------------------------------------------------------------
Write-Host ""
if (-not (Test-Path "venv")) {
    Write-Host "  Creating Python virtual environment..."
    & $pythonCmd -m venv venv
}

& .\venv\Scripts\Activate.ps1

Write-Host "  Installing Python dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt
Write-Host "  + Python dependencies installed"

# -- Frontend ------------------------------------------------------------------
Write-Host ""
Write-Host "  Building frontend..."
Set-Location frontend
npm install
npm run build
Set-Location ..
Write-Host "  + Frontend built"

# -- Required directories ------------------------------------------------------
New-Item -ItemType Directory -Force -Path "palettes/defaults", "palettes/user", "palette_library", "presets" | Out-Null

Write-Host ""
Write-Host "  -------------------------------------"
Write-Host "  Setup complete!"
Write-Host ""
Write-Host "  To run Porypal:"
Write-Host "    .\venv\Scripts\Activate.ps1"
Write-Host "    python main.py"
Write-Host ""
Write-Host "  Then open http://127.0.0.1:7860"
Write-Host ""
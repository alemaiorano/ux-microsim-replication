param(
  [switch]$SkipAssets,
  [switch]$SkipPdf,
  [string]$LogDir = "reports\\logs"
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$logDirPath = Join-Path $repoRoot $LogDir
New-Item -ItemType Directory -Force -Path $logDirPath | Out-Null
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logPath = Join-Path $logDirPath "paper_ux_build_${timestamp}.log"

function Write-Log {
  param([string]$Message)
  $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
  $line = "[$stamp] $Message"
  $line | Tee-Object -FilePath $logPath -Append
}

function Invoke-Logged {
  param(
    [string]$Label,
    [scriptblock]$Command
  )
  Write-Log $Label
  $global:LASTEXITCODE = 0
  try {
    & $Command 2>&1 | Tee-Object -FilePath $logPath -Append
  } catch {
    throw "$Label failed: $($_.Exception.Message)"
  }
  $exitCode = $global:LASTEXITCODE
  if ($null -ne $exitCode -and "$exitCode" -ne "" -and $exitCode -ne 0) {
    throw "$Label failed with exit code $exitCode."
  }
}

Push-Location $repoRoot
try {
  Write-Log "Starting paper_ux build."

  if (-not $SkipAssets) {
    Invoke-Logged "Promoting latest UX run (if any)" { python scripts\ux_promote_run.py }
    Invoke-Logged "Rebuilding alignment table" { python scripts\ux_alignment_table.py }
    Invoke-Logged "Computing Appstore baseline eval (optional)" { python scripts\ux_appstore_baseline_eval.py }
    Invoke-Logged "Exporting UX paper tables" { python scripts\export_paper_ux_tables.py }
    Invoke-Logged "Exporting UX paper figures" { python scripts\export_paper_ux_figures.py }
  }

  if (-not $SkipPdf) {
    Invoke-Logged "Building PDF (pdflatex pass 1)" { pdflatex -interaction=nonstopmode -halt-on-error -output-directory paper_ux paper_ux\main.tex }
    Invoke-Logged "Running bibtex" { bibtex paper_ux\main }
    Invoke-Logged "Building PDF (pdflatex pass 2)" { pdflatex -interaction=nonstopmode -halt-on-error -output-directory paper_ux paper_ux\main.tex }
    Invoke-Logged "Building PDF (pdflatex pass 3)" { pdflatex -interaction=nonstopmode -halt-on-error -output-directory paper_ux paper_ux\main.tex }
  }

  Write-Log "Build completed."
  Write-Host "Build log: $logPath"
} finally {
  Pop-Location
}

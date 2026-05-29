$ErrorActionPreference = "Stop"

Set-Location -LiteralPath $PSScriptRoot

$bundledPython = "C:\Users\darpa\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if (Test-Path -LiteralPath $bundledPython) {
    $python = $bundledPython
} else {
    $python = "python"
}

if ($args.Count -eq 0) {
    Write-Host 'Usage:'
    Write-Host '  .\run_agent.ps1 "Your heritage question here"'
    Write-Host ''
    Write-Host 'Example:'
    Write-Host '  .\run_agent.ps1 "What does the UNESCO Hampi document say about Hampi heritage?"'
    exit 1
}

& $python scripts\heritage_agent.py @args

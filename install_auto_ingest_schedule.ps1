$ErrorActionPreference = "Stop"

$projectRoot = $PSScriptRoot
$scriptPath = Join-Path $projectRoot "run_auto_ingest.bat"

if (-not (Test-Path -LiteralPath $scriptPath)) {
    throw "Could not find $scriptPath"
}

$taskName = "IndianHeritageAI-AutoIngest"
$action = New-ScheduledTaskAction `
    -Execute $scriptPath `
    -Argument '--validate-limit 25 --source-limit 10 --pdf-limit-per-source 5 --embed-limit 10'

$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 10:00am
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew

Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Validate links, discover PDFs, and update embeddings for Indian Heritage AI weekly." `
    -Force | Out-Null

Write-Host "Scheduled task installed: $taskName"
Write-Host "Runs weekly on Sunday at 10:00."
Write-Host "Log file: $(Join-Path $projectRoot 'data\logs\auto_ingest.log')"

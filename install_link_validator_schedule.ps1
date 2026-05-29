$ErrorActionPreference = "Stop"

$projectRoot = $PSScriptRoot
$scriptPath = Join-Path $projectRoot "run_validate_links.bat"

if (-not (Test-Path -LiteralPath $scriptPath)) {
    throw "Could not find $scriptPath"
}

$taskName = "IndianHeritageAI-LinkValidation"
$action = New-ScheduledTaskAction `
    -Execute $scriptPath `
    -Argument '--mode stale --stale-days 30 --limit 25 --add-replacements'

$trigger = New-ScheduledTaskTrigger -Daily -At 9:00am
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
    -Description "Validate pending and stale Indian Heritage AI links daily." `
    -Force | Out-Null

Write-Host "Scheduled task installed: $taskName"
Write-Host "Runs daily at 09:00, validates up to 25 pending/stale links, and adds redirect/replacement candidates."
Write-Host "Log file: $(Join-Path $projectRoot 'data\logs\link_validation.log')"

param(
    [Parameter(Mandatory = $true)][string]$ApiBaseUrl,
    [Parameter(Mandatory = $true)][string]$FrontendUrl,
    [string]$ExpectedOrigin = $FrontendUrl
)

$ErrorActionPreference = "Stop"
$api = $ApiBaseUrl.TrimEnd("/")
$frontend = $FrontendUrl.TrimEnd("/")

if (-not $api.StartsWith("https://") -or -not $frontend.StartsWith("https://")) {
    throw "Beta verification requires HTTPS API and frontend URLs."
}

$health = Invoke-RestMethod -Uri "$api/health" -Method Get
if ($health.status -ne "ok") { throw "API health check failed." }

$ready = Invoke-RestMethod -Uri "$api/ready" -Method Get
if ($ready.status -ne "ready") {
    throw "API readiness failed: $($ready.configuration_issues -join '; ')"
}

$page = Invoke-WebRequest -Uri $frontend -Method Get
if ($page.StatusCode -ne 200 -or $page.Content -notmatch 'id="root"') {
    throw "Frontend did not return the application shell."
}

$preflight = Invoke-WebRequest -Uri "$api/health" -Method Options -Headers @{
    Origin = $ExpectedOrigin
    "Access-Control-Request-Method" = "GET"
}
if ($preflight.Headers["Access-Control-Allow-Origin"] -ne $ExpectedOrigin) {
    throw "CORS does not allow the deployed frontend origin."
}

Write-Host "Growth Atlas deployment checks passed: health, readiness, frontend, HTTPS, and CORS."

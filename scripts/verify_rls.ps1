param(
    [Parameter(Mandatory = $true)][string]$ApiBaseUrl,
    [Parameter(Mandatory = $true)][string]$OwnerAccessToken,
    [Parameter(Mandatory = $true)][string]$OtherUserAccessToken,
    [Parameter(Mandatory = $true)][string]$OwnerEpisodeId
)

$ErrorActionPreference = "Stop"
$uri = "$($ApiBaseUrl.TrimEnd('/'))/decision-episodes/$OwnerEpisodeId"

$owner = Invoke-WebRequest -Uri $uri -Headers @{ Authorization = "Bearer $OwnerAccessToken" }
if ($owner.StatusCode -ne 200) { throw "Owner cannot read the test episode." }

try {
    Invoke-WebRequest -Uri $uri -Headers @{ Authorization = "Bearer $OtherUserAccessToken" } | Out-Null
    throw "RLS isolation failed: a second user read the owner's episode."
} catch {
    if ($_.Exception.Response.StatusCode.value__ -ne 404) { throw }
}

Write-Host "Live RLS isolation passed: owner can read; second user receives 404."

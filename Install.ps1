[CmdletBinding()]
param(
    [ValidateSet('Validate', 'Local', 'Tenant')]
    [string]$Action = 'Validate',
    [ValidateSet('Demo', 'CSV', 'SharePoint')]
    [string]$SourceMode = 'Demo',
    [string]$TenantId,
    [string]$WorkspaceId,
    [string]$DataFolder,
    [string]$SharePointSite,
    [string]$SharePointFolder,
    [string]$InstallFolder = (Join-Path $env:LOCALAPPDATA 'CopilotTokenDashboard\1.0.0'),
    [switch]$InstallDependencies,
    [switch]$Update
)

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$python = Get-Command python -ErrorAction Stop
$env:PYTHONPATH = Join-Path $root 'src'
$project = Join-Path $root 'powerbi'
$tables = if ($SourceMode -eq 'Demo') { Join-Path $root 'sample_data' } else { $DataFolder }
if (-not $tables -or -not (Test-Path -LiteralPath $tables -PathType Container)) {
    throw 'A complete reporting-table folder is required.'
}
if ($InstallDependencies) {
    & $python.Source -m pip install $root
    if ($LASTEXITCODE -ne 0) { throw 'Declared runtime dependencies could not be installed.' }
}
& $python.Source -c 'import requests, msal'
if ($LASTEXITCODE -ne 0) {
    throw 'Runtime dependencies are missing. Re-run with -InstallDependencies or install the package first.'
}
$validation = @('-m', 'copilot_token_dashboard.cli', 'validate-data', '--input', $tables)
if ($SourceMode -ne 'Demo') { $validation += '--production' }
& $python.Source @validation
if ($LASTEXITCODE -ne 0) { throw 'Data validation failed; installation stopped.' }
if ($Action -eq 'Validate') {
    'Data and dependency checks passed. No tenant resources were created.'
    return
}
if ($Action -eq 'Local') {
    if (Test-Path -LiteralPath $InstallFolder) {
        throw 'The installation directory already exists. Use a new version directory; existing configuration was not changed.'
    }
    New-Item -ItemType Directory -Path $InstallFolder -Force | Out-Null
    Copy-Item -LiteralPath $project -Destination $InstallFolder -Recurse
    $localProject = Join-Path $InstallFolder 'powerbi'
    $modelPath = Join-Path $localProject 'Copilot Token Dashboard.SemanticModel\model.bim'
    $model = Get-Content -LiteralPath $modelPath -Raw | ConvertFrom-Json
    $values = @{
        SourceMode = $SourceMode
        DataFolder = $tables
        SharePointSite = $SharePointSite
        SharePointFolder = $SharePointFolder
    }
    foreach ($expression in $model.model.expressions) {
        if ($values.ContainsKey($expression.name)) {
            $metadata = $expression.expression.Substring($expression.expression.IndexOf(' meta '))
            $expression.expression = '"' + ([string]$values[$expression.name]).Replace('"', '""') + '"' + $metadata
        }
    }
    $model | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $modelPath -Encoding utf8
    $file = Join-Path $localProject 'Copilot Token Dashboard.pbip'
    Start-Process -FilePath $file
    "Opened the installed project: $file"
    'Refresh in Power BI Desktop, verify the data banner, then publish into your own tenant.'
    return
}
if (-not $TenantId -or -not $WorkspaceId) {
    throw 'Tenant deployment requires explicit TenantId and WorkspaceId. No default tenant is used.'
}
[guid]$TenantId | Out-Null
[guid]$WorkspaceId | Out-Null
if (-not $env:CTD_FABRIC_ACCESS_TOKEN) {
    $az = Get-Command az -ErrorAction SilentlyContinue
    if (-not $az) {
        throw 'Install Azure CLI and authenticate to your own tenant, or set CTD_FABRIC_ACCESS_TOKEN in your process environment.'
    }
    & $az.Source login --tenant $TenantId --allow-no-subscriptions --output none
    if ($LASTEXITCODE -ne 0) { throw 'Tenant authentication failed.' }
    $token = (& $az.Source account get-access-token --tenant $TenantId --resource 'https://api.fabric.microsoft.com' --output json) | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0 -or -not $token.accessToken) { throw 'The Fabric access token could not be acquired.' }
    $env:CTD_FABRIC_ACCESS_TOKEN = $token.accessToken
}
$arguments = @(
    (Join-Path $root 'tools\deploy_tenant.py'),
    '--project', $project, '--tenant', $TenantId, '--workspace', $WorkspaceId,
    '--mode', $SourceMode, '--output', (Join-Path $root 'runtime\deployment.json')
)
if ($SourceMode -ne 'Demo') { $arguments += @('--data-folder', $tables) }
if ($SharePointSite) { $arguments += @('--sharepoint-site', $SharePointSite) }
if ($SharePointFolder) { $arguments += @('--sharepoint-folder', $SharePointFolder) }
if ($Update) { $arguments += '--update' }
& $python.Source @arguments
if ($LASTEXITCODE -ne 0) { throw 'Tenant provisioning did not complete. Inspect the workspace before retrying.' }
'Provisioning completed. Follow the reported security, credential, refresh, and Viewer smoke-test steps before sharing.'

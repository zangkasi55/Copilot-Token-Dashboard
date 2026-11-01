[CmdletBinding()]
param(
    [string]$Compiler = (Join-Path $PSScriptRoot '..\.tools\pbi-tools-core\pbi-tools.core.exe'),
    [string]$BuildFolder = (Join-Path $PSScriptRoot ('..\.work\template-build-' + [guid]::NewGuid().ToString('N')))
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$compilerPath = (Resolve-Path -LiteralPath $Compiler -ErrorAction Stop).Path
if (Test-Path -LiteralPath $BuildFolder) {
    throw 'The build folder already exists. Choose a new directory; existing build data is not deleted.'
}
$env:PYTHONPATH = Join-Path $root 'src'
New-Item -ItemType Directory -Path $BuildFolder -Force | Out-Null
$modelFolder = Join-Path $BuildFolder 'model'
$sourceFolder = Join-Path $BuildFolder 'pbit'
$outputFolder = Join-Path $root 'dist'
New-Item -ItemType Directory -Path $outputFolder -Force | Out-Null
$template = Join-Path $outputFolder 'Copilot-Token-Dashboard-1.0.1.pbit'

python (Join-Path $root 'tools\build_powerbi.py') --data (Join-Path $root 'sample_data') --output (Join-Path $root 'powerbi')
if ($LASTEXITCODE -ne 0) { throw 'Power BI project generation failed.' }
python (Join-Path $root 'tools\validate_powerbi.py') --project (Join-Path $root 'powerbi') --cache (Join-Path $root '.work\schema-cache')
if ($LASTEXITCODE -ne 0) { throw 'The generated Power BI project did not validate.' }
& $compilerPath convert (Join-Path $root 'powerbi\Copilot Token Dashboard.SemanticModel\model.bim') -outPath $modelFolder -modelSerialization Tmdl
if ($LASTEXITCODE -ne 0) { throw 'The semantic model serializer rejected the generated model.' }
python (Join-Path $root 'tools\build_pbit_sources.py') --project (Join-Path $root 'powerbi') --model $modelFolder --output $sourceFolder
if ($LASTEXITCODE -ne 0) { throw 'Power BI template source generation failed.' }
& $compilerPath compile $sourceFolder -outPath $template -format PBIT -overwrite
if ($LASTEXITCODE -ne 0) { throw 'Power BI template compilation failed.' }
python -c 'import sys; from pathlib import Path; sys.path.insert(0,sys.argv[1]); from build_release import verify_template; print(verify_template(Path(sys.argv[2])))' (Join-Path $root 'tools') $template
if ($LASTEXITCODE -ne 0) { throw 'The compiled template does not contain the complete dashboard.' }
"Validated template: $template"

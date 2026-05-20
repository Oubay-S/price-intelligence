Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
python "$PSScriptRoot\price_analysis.py" --source local

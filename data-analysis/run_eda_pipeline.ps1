Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

python "$PSScriptRoot\run_eda_pipeline.py" @args

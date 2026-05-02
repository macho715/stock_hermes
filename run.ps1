param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]] $ArgsForProgram
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path

$candidates = @(
    (Join-Path $root ".venv\Scripts\python.exe"),
    "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
    "python"
)

$python = $null
foreach ($candidate in $candidates) {
    if ($candidate -eq "python") {
        $cmd = Get-Command python -ErrorAction SilentlyContinue
        if ($cmd) {
            $python = $cmd.Source
            break
        }
    } elseif (Test-Path -LiteralPath $candidate) {
        $python = $candidate
        break
    }
}

if (-not $python) {
    Write-Error "No Python runtime found. Install Python 3.11 or 3.12, then run setup from docs/SETUP.md."
    exit 1
}

if (-not $ArgsForProgram -or $ArgsForProgram.Count -eq 0) {
    $ArgsForProgram = @("self-test")
}

Push-Location $root
try {
    & $python "main.py" @ArgsForProgram
    exit $LASTEXITCODE
} finally {
    Pop-Location
}

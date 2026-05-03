param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]] $ArgsForProgram
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path

function Invoke-TensorFlowCheck {
    $tfPython = Join-Path $root ".venv-tf312\Scripts\python.exe"
    if (-not (Test-Path -LiteralPath $tfPython)) {
        Write-Error "TensorFlow venv not found: $tfPython. Create it with: py -3.12 -m venv .venv-tf312; .\.venv-tf312\Scripts\python.exe -m pip install tensorflow"
        $script:RunPs1ExitCode = 1
        return
    }

    $script = @'
import json
import os

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

import tensorflow as tf

print("TF_VERSION=" + tf.__version__)
devices = [d.name + ":" + d.device_type for d in tf.config.list_physical_devices()]
print("DEVICES=" + json.dumps(devices))

model = tf.keras.Sequential([
    tf.keras.layers.Input(shape=(4, 3)),
    tf.keras.layers.LSTM(4),
    tf.keras.layers.Dense(1, activation="sigmoid"),
])
model.compile(optimizer="adam", loss="binary_crossentropy")
x = tf.random.uniform((8, 4, 3), seed=43)
y = tf.cast(tf.reduce_mean(x, axis=[1, 2]) > 0.5, tf.float32)
history = model.fit(x, y, epochs=1, verbose=0)
pred = model.predict(x[:2], verbose=0)

print("LSTM_SMOKE=PASS")
print("LOSS=" + str(round(float(history.history["loss"][-1]), 6)))
print("PRED_SHAPE=" + str(tuple(pred.shape)))
'@

    Push-Location $root
    try {
        $script | & $tfPython -
        $script:RunPs1ExitCode = $LASTEXITCODE
    } finally {
        Pop-Location
    }
}

function Invoke-TensorFlowGpuWslCheck {
    $wslDistro = if ($env:STOCK_TF_WSL_DISTRO) { $env:STOCK_TF_WSL_DISTRO } else { "Ubuntu" }
    $wslPython = if ($env:STOCK_TF_WSL_PYTHON) { $env:STOCK_TF_WSL_PYTHON } else { "/root/.venvs/stock-rtx4060-tf-gpu/bin/python" }
    $wslNvidiaRoot = if ($env:STOCK_TF_WSL_NVIDIA_ROOT) { $env:STOCK_TF_WSL_NVIDIA_ROOT } else { "/root/.venvs/stock-rtx4060-tf-gpu/lib/python3.12/site-packages/nvidia" }

    if ($wslDistro -match "'") {
        Write-Error "WSL distro names containing single quotes are not supported by this wrapper."
        $script:RunPs1ExitCode = 1
        return
    }
    if ($wslPython -match "'") {
        Write-Error "STOCK_TF_WSL_PYTHON paths containing single quotes are not supported by this wrapper."
        $script:RunPs1ExitCode = 1
        return
    }
    if ($wslNvidiaRoot -match "'") {
        Write-Error "STOCK_TF_WSL_NVIDIA_ROOT paths containing single quotes are not supported by this wrapper."
        $script:RunPs1ExitCode = 1
        return
    }

    $pythonScript = @'
import json
import os
import sys
import time

import numpy as np
import tensorflow as tf

print(f"PYTHON={sys.version.split()[0]}")
print(f"TF_VERSION={tf.__version__}")
print(f"BUILD_CUDA={tf.test.is_built_with_cuda()}")
print(f"LD_LIBRARY_PATH_SET={bool(os.environ.get('LD_LIBRARY_PATH'))}")

gpus = tf.config.list_physical_devices("GPU")
print("TF_GPUS=" + json.dumps([gpu.name for gpu in gpus]))
if not gpus:
    raise SystemExit("NO_TF_GPU_DETECTED")

for gpu in gpus:
    try:
        tf.config.experimental.set_memory_growth(gpu, True)
    except Exception as exc:
        print(f"MEMORY_GROWTH_WARN={type(exc).__name__}:{exc}")

with tf.device("/GPU:0"):
    start = time.perf_counter()
    a = tf.random.uniform((2048, 2048), dtype=tf.float32)
    b = tf.random.uniform((2048, 2048), dtype=tf.float32)
    c = tf.matmul(a, b)
    checksum = float(tf.reduce_sum(c).numpy())
    elapsed = time.perf_counter() - start
print(f"GPU_MATMUL=PASS device={c.device} seconds={elapsed:.4f} checksum={checksum:.4f}")

rng = np.random.default_rng(20260503)
X = rng.normal(size=(64, 12, 5)).astype("float32")
y = (X[:, -1, 0] > 0).astype("float32")

model = tf.keras.Sequential([
    tf.keras.layers.Input(shape=(12, 5)),
    tf.keras.layers.LSTM(8),
    tf.keras.layers.Dense(1, activation="sigmoid"),
])
model.compile(optimizer="adam", loss="binary_crossentropy")
with tf.device("/GPU:0"):
    history = model.fit(X, y, epochs=2, batch_size=8, verbose=0)
    pred = model.predict(X[:3], verbose=0)
loss_value = history.history["loss"][-1]
print(f"LSTM_SMOKE=PASS final_loss={loss_value:.6f} pred_shape={pred.shape}")
'@

    $encodedScript = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($pythonScript))
    $wslPythonQuoted = "'$wslPython'"
    $wslNvidiaRootQuoted = "'$wslNvidiaRoot'"
    $encodedScriptQuoted = "'$encodedScript'"

    $bash = @"
set -euo pipefail
PY=$wslPythonQuoted
NVIDIA_ROOT=$wslNvidiaRootQuoted
if [ ! -x "`$PY" ]; then
  echo "TF_WSL_PYTHON_NOT_FOUND=`$PY" >&2
  exit 21
fi
if [ ! -d "`$NVIDIA_ROOT" ]; then
  echo "TF_WSL_NVIDIA_ROOT_NOT_FOUND=`$NVIDIA_ROOT" >&2
  exit 22
fi
NVIDIA_LIBS=`$(find "`$NVIDIA_ROOT" -type d -name lib | paste -sd: -)
if [ -z "`$NVIDIA_LIBS" ]; then
  echo "TF_WSL_NVIDIA_LIBS_NOT_FOUND=`$NVIDIA_ROOT" >&2
  exit 23
fi
printf %s $encodedScriptQuoted | base64 -d | env LD_LIBRARY_PATH="`$NVIDIA_LIBS" TF_CPP_MIN_LOG_LEVEL=1 "`$PY" -
"@

    $bash = $bash -replace "`r`n", "`n"
    $bash = $bash -replace "`r", "`n"
    $encodedBash = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($bash))
    & wsl.exe -d $wslDistro -- bash -lc "printf %s '$encodedBash' | base64 -d | bash"
    $script:RunPs1ExitCode = $LASTEXITCODE
}

if ($ArgsForProgram -and $ArgsForProgram.Count -gt 0) {
    $wrapperCommand = $ArgsForProgram[0]
    if ($wrapperCommand -in @("tensorflow-check", "tf-check", "tf-smoke")) {
        $script:RunPs1ExitCode = 1
        Invoke-TensorFlowCheck
        exit $script:RunPs1ExitCode
    }
    if ($wrapperCommand -in @("tensorflow-gpu-wsl-check", "tf-gpu-wsl", "tf-gpu-smoke")) {
        $script:RunPs1ExitCode = 1
        Invoke-TensorFlowGpuWslCheck
        exit $script:RunPs1ExitCode
    }
}

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

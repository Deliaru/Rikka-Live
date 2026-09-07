param(
    [string]$ServiceDir = "local_services\index-tts",
    [string]$ReferenceAudio = "private\voice\rikka_voice_clone.wav",
    [string]$HostName = "127.0.0.1",
    [int]$Port = 7861,
    [switch]$Fp16,
    [switch]$CudaKernel,
    [switch]$DeepSpeed,
    [string]$Device = "",
    [string]$ManualRuntimeModelDir = "manual_hf",
    [switch]$AllowRuntimeDownloads,
    [switch]$VerboseLogs
)

$ErrorActionPreference = "Stop"

function Resolve-ProjectPath([string]$PathValue) {
    if ([System.IO.Path]::IsPathRooted($PathValue)) {
        return [System.IO.Path]::GetFullPath($PathValue)
    }
    return [System.IO.Path]::GetFullPath((Join-Path (Get-Location) $PathValue))
}

$servicePath = Resolve-ProjectPath $ServiceDir
$pythonExe = Join-Path $servicePath ".venv\Scripts\python.exe"
if (!(Test-Path $pythonExe)) {
    throw "IndexTTS2 isolated Python is not available. Run scripts\setup_indextts2.ps1 -SyncEnvironment first."
}

$scriptPath = Resolve-ProjectPath "scripts\run_indextts2_service.py"
$referencePath = Resolve-ProjectPath $ReferenceAudio

$argsList = @(
    $scriptPath,
    "--repo-dir",
    $servicePath,
    "--host",
    $HostName,
    "--port",
    "$Port",
    "--reference-audio",
    $referencePath,
    "--manual-runtime-model-dir",
    $ManualRuntimeModelDir
)

if ($Fp16) {
    $argsList += "--fp16"
}
if ($CudaKernel) {
    $argsList += "--cuda-kernel"
}
if ($DeepSpeed) {
    $argsList += "--deepspeed"
}
if ($Device) {
    $argsList += @("--device", $Device)
}
if ($AllowRuntimeDownloads) {
    $argsList += "--allow-runtime-downloads"
}
if ($VerboseLogs) {
    $argsList += "--verbose"
}

Push-Location $servicePath
try {
    & $pythonExe @argsList
}
finally {
    Pop-Location
}

param(
    [string]$ServiceDir = "local_services\index-tts",
    [string]$RepoUrl = "https://github.com/index-tts/index-tts.git",
    [string]$PipIndexUrl = "https://mirrors.zju.edu.cn/pypi/web/simple",
    [string]$TorchBackend = "auto",
    [switch]$PullLfs,
    [switch]$SyncEnvironment,
    [switch]$DownloadModel,
    [ValidateSet("modelscope", "huggingface")]
    [string]$ModelSource = "modelscope"
)

$ErrorActionPreference = "Stop"

function Resolve-ProjectPath([string]$PathValue) {
    if ([System.IO.Path]::IsPathRooted($PathValue)) {
        return [System.IO.Path]::GetFullPath($PathValue)
    }
    return [System.IO.Path]::GetFullPath((Join-Path (Get-Location) $PathValue))
}

function Invoke-Checked([string]$FilePath, [string[]]$ArgumentList, [string]$Description) {
    & $FilePath @ArgumentList
    if ($LASTEXITCODE -ne 0) {
        throw "$Description failed with exit code $LASTEXITCODE"
    }
}

$servicePath = Resolve-ProjectPath $ServiceDir
$serviceParent = Split-Path -Parent $servicePath
if (!(Test-Path $serviceParent)) {
    New-Item -ItemType Directory -Path $serviceParent | Out-Null
}

if (!(Test-Path (Join-Path $servicePath ".git"))) {
    $env:GIT_LFS_SKIP_SMUDGE = "1"
    git clone --depth 1 $RepoUrl $servicePath
}

git -C $servicePath lfs install
if ($PullLfs) {
    git -C $servicePath lfs pull
}

$bootstrap = Join-Path $servicePath ".uv-bootstrap"
$uvExe = Join-Path $bootstrap "Scripts\uv.exe"
if (!(Test-Path $uvExe)) {
    $python = Join-Path (Get-Location) ".venv\Scripts\python.exe"
    if (!(Test-Path $python)) {
        $python = "python"
    }
    Invoke-Checked $python @("-m", "venv", $bootstrap) "uv bootstrap venv creation"
    Invoke-Checked (Join-Path $bootstrap "Scripts\python.exe") @(
        "-m",
        "pip",
        "install",
        "-U",
        "pip",
        "uv",
        "-i",
        $PipIndexUrl
    ) "uv bootstrap install"
}

if ($SyncEnvironment) {
    Push-Location $servicePath
    try {
        try {
            Invoke-Checked $uvExe @(
                "sync",
                "--extra",
                "webui",
                "--default-index",
                $PipIndexUrl,
                "--torch-backend",
                $TorchBackend
            ) "IndexTTS2 locked uv sync"
        }
        catch {
            Write-Warning "Locked uv sync failed: $_"
            Write-Warning "Falling back to unlocked install from the configured domestic mirror."
            Invoke-Checked $uvExe @(
                "pip",
                "install",
                "-e",
                ".",
                "--extra",
                "webui",
                "--default-index",
                $PipIndexUrl,
                "--index-strategy",
                "unsafe-best-match",
                "--no-verify-hashes",
                "--torch-backend",
                $TorchBackend,
                "--no-config"
            ) "IndexTTS2 unlocked dependency install"
        }
    }
    finally {
        Pop-Location
    }
}

if ($DownloadModel) {
    Push-Location $servicePath
    try {
        if ($ModelSource -eq "modelscope") {
            & $uvExe tool install "modelscope"
            $modelscope = Get-Command modelscope -ErrorAction SilentlyContinue
            if ($modelscope) {
                & $modelscope.Source download --model IndexTeam/IndexTTS-2 --local_dir checkpoints
            }
            else {
                & $uvExe tool run modelscope download --model IndexTeam/IndexTTS-2 --local_dir checkpoints
            }
        }
        else {
            & $uvExe tool install "huggingface-hub[cli,hf_xet]"
            $hf = Get-Command hf -ErrorAction SilentlyContinue
            if ($hf) {
                & $hf.Source download IndexTeam/IndexTTS-2 --local-dir checkpoints
            }
            else {
                & $uvExe tool run --from "huggingface-hub[cli,hf_xet]" hf download IndexTeam/IndexTTS-2 --local-dir checkpoints
            }
        }
    }
    finally {
        Pop-Location
    }
}

Write-Host "IndexTTS2 checkout is ready at $servicePath"
Write-Host "Run with -SyncEnvironment to install the isolated .venv."
Write-Host "Run with -DownloadModel to fetch IndexTeam/IndexTTS-2 into checkpoints."

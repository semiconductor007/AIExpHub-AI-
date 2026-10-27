param(
    [ValidateSet('start', 'stop', 'diagnose')][string]$Action = 'start',
    [switch]$NoBrowser,
    [ValidateRange(1, 60)][int]$TimeoutSeconds = 60
)

# Windows PowerShell 5.1 compatible. Dot-source to test without starting services.
$ErrorActionPreference = 'Stop'
$script:ProjectRoot = Split-Path -Parent $PSScriptRoot
$script:RuntimeDir = Join-Path $script:ProjectRoot '.runtime'
$script:StatePath = Join-Path $script:RuntimeDir 'services.json'
$script:LogDir = Join-Path $script:RuntimeDir 'logs'
$script:FrontendUrl = 'http://127.0.0.1:5173/'

function Get-ServiceSpec([string]$Name) {
    if ($Name -eq 'backend') {
        $directory = Join-Path $script:ProjectRoot 'backend'
        return @{
            Name = $Name; Port = 8000; Directory = $directory
            File = Join-Path $directory '.venv\Scripts\python.exe'
            Arguments = '-m uvicorn app.main:app --app-dir "' + $directory + '" --host 127.0.0.1 --port 8000'
        }
    }
    $directory = Join-Path $script:ProjectRoot 'frontend'
    return @{
        Name = $Name; Port = 5173; Directory = $directory
        File = (Get-Command node.exe -ErrorAction Stop).Source
        Arguments = '"' + (Join-Path $directory 'node_modules\vite\bin\vite.js') + '" --host 127.0.0.1 --port 5173 --strictPort'
    }
}

function Assert-Environment {
    $python = Join-Path $script:ProjectRoot 'backend\.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
        throw "缺少后端虚拟环境。请在 backend 中使用 Python 3.12 执行 python -m venv .venv，再执行 .\.venv\Scripts\python.exe -m pip install -r requirements.txt。"
    }
    foreach ($relative in @('backend\app\main.py', 'frontend\package.json', 'frontend\vite.config.ts', 'frontend\package-lock.json')) {
        if (-not (Test-Path -LiteralPath (Join-Path $script:ProjectRoot $relative) -PathType Leaf)) {
            throw "缺少项目文件：$relative。请确认项目下载完整。"
        }
    }
    # Imports third-party packages only: never import app.main or initialize a DB here.
    $pythonCode = 'import sys; assert sys.version_info[:2] == (3, 12), "Python 3.12 required"; import fastapi, uvicorn, sqlalchemy, pydantic, httpx, dotenv; assert int(pydantic.__version__.split(".")[0]) == 2, "Pydantic 2 required"; print(sys.version.split()[0])'
    $encodedPython = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($pythonCode))
    $pythonCheck = Invoke-NativeProbe $python @('-c', "exec(__import__('base64').b64decode('$encodedPython'))")
    if ($pythonCheck.Code -ne 0) {
        throw "后端 Python 3.12 或依赖不可用。请检查虚拟环境，并执行 .\backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt。详情：$($pythonCheck.Output)"
    }
    if (-not (Get-Command node.exe -ErrorAction SilentlyContinue)) { throw '找不到 Node.js。请安装符合项目要求的 Node.js 后重新打开终端。' }
    if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) { throw '找不到 npm.cmd。请检查 Node.js 安装和 PATH。' }
    $frontend = Join-Path $script:ProjectRoot 'frontend'
    if (-not (Test-Path -LiteralPath (Join-Path $frontend 'node_modules\vite\bin\vite.js') -PathType Leaf)) {
        throw '缺少前端依赖。请进入 frontend 执行 npm ci，然后重新启动。'
    }
    # Only resolve direct runtime packages; startup itself validates Vite's transitive dependencies.
    $probe = 'const {createRequire}=require("node:module");const r=createRequire(process.argv[1]);const v=process.versions.node.split(".").map(Number);if(!((v[0]===20&&v[1]>=19)||(v[0]===22&&v[1]>=12)||v[0]>22))throw Error("Node version incompatible with Vite 8");for(const p of ["vite","vue","vue-router","axios","element-plus","echarts","@vitejs/plugin-vue"])r.resolve(p);console.log(process.versions.node)'
    $encodedNode = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($probe))
    $nodeCheck = Invoke-NativeProbe 'node.exe' @('-e', "eval(Buffer.from('$encodedNode','base64').toString())", (Join-Path $frontend 'package.json'))
    if ($nodeCheck.Code -ne 0) { throw "Node.js 版本或前端依赖不可用。Vite 8 需要 Node 20.19+（20.x）或 22.12+；请检查版本，并在 frontend 执行 npm ci。详情：$($nodeCheck.Output)" }
    return @{ Python = $pythonCheck.Output; Node = $nodeCheck.Output }
}

function Invoke-NativeProbe([string]$File, [string[]]$Arguments) {
    # Windows PowerShell turns native stderr into ErrorRecord: capture it for a useful error.
    $ErrorActionPreference = 'Continue'
    $output = & $File @Arguments 2>&1
    return @{ Code = $LASTEXITCODE; Output = ($output -join ' ') }
}

function New-State {
    return @{ version = 1; root = $script:ProjectRoot; services = @{} }
}

function Read-State {
    $state = New-State
    if (-not (Test-Path -LiteralPath $script:StatePath)) { return $state }
    try {
        $saved = Get-Content -LiteralPath $script:StatePath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($saved.version -ne 1 -or $saved.root -ne $script:ProjectRoot -or $null -eq $saved.services) { throw '记录格式或项目路径不匹配' }
        foreach ($name in @('backend', 'frontend')) {
            $entry = $saved.services.$name
            if ($null -ne $entry) { $state.services[$name] = $entry }
        }
    } catch { throw "无法读取运行记录 $script:StatePath。请运行 diagnose 查看进程，确认后再移走损坏的记录；不会根据端口强行停止服务。$($_.Exception.Message)" }
    return $state
}

function Write-State($State) {
    $temporary = $script:StatePath + '.tmp'
    $State | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $temporary -Encoding UTF8
    Move-Item -LiteralPath $temporary -Destination $script:StatePath -Force
}

function Get-ProcessInfo([int]$ProcessId) {
    return Get-CimInstance Win32_Process -Filter "ProcessId = $ProcessId" -ErrorAction Stop
}

function Get-Identity($Process) {
    return @{
        pid = [int]$Process.ProcessId
        created = $Process.CreationDate.ToUniversalTime().Ticks.ToString()
        executable = [string]$Process.ExecutablePath
        command = [string]$Process.CommandLine
    }
}

function Test-Identity($Saved, $Current) {
    return ($null -ne $Current -and $Saved.pid -eq $Current.ProcessId -and
        $Saved.created -eq $Current.CreationDate.ToUniversalTime().Ticks.ToString() -and
        $Saved.executable -eq $Current.ExecutablePath -and $Saved.command -ceq $Current.CommandLine)
}

function Test-ManagedProcess([string]$Name, $Saved) {
    if ($null -eq $Saved) { return $false }
    $current = Get-ProcessInfo $Saved.pid
    if (-not (Test-Identity $Saved $current)) { return $false }
    $spec = Get-ServiceSpec $Name
    # Never trust a PID file alone. The actual command must include this project's absolute path.
    return ($current.ExecutablePath -eq $spec.File -and
        $current.CommandLine.TrimEnd().EndsWith(' ' + $spec.Arguments, [StringComparison]::OrdinalIgnoreCase))
}

function Get-ProcessTree([int]$RootId) {
    $all = @(Get-CimInstance Win32_Process)
    $root = $all | Where-Object ProcessId -eq $RootId | Select-Object -First 1
    if ($null -eq $root) { return @() }
    $tree = @($root)
    for ($index = 0; $index -lt $tree.Count; $index++) {
        $parent = $tree[$index]
        $tree += @($all | Where-Object { $_.ParentProcessId -eq $parent.ProcessId -and $_.CreationDate -ge $parent.CreationDate -and $_.ProcessId -ne $parent.ProcessId })
    }
    return $tree
}

function Get-PortOwners([int]$Port) {
    # The common cold-start case has no listeners; avoid loading NetTCPIP just to prove absence.
    $listeners = [Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners()
    if (@($listeners | Where-Object Port -eq $Port).Count -eq 0) { return @() }
    $owners = @(Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique)
    if ($owners.Count -eq 0) {
        $stillListening = [Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners()
        if (@($stillListening | Where-Object Port -eq $Port).Count -gt 0) { throw "端口 $Port 正在监听，但无法查询进程归属；请执行 diagnose 核查。" }
    }
    return $owners
}

function Assert-PortOwnership([string]$Name, $Saved) {
    $spec = Get-ServiceSpec $Name
    $owners = @(Get-PortOwners $spec.Port)
    if ($owners.Count -eq 0) { return }
    $treeIds = @()
    if (Test-ManagedProcess $Name $Saved) { $treeIds = @(Get-ProcessTree $Saved.pid | ForEach-Object { $_.ProcessId }) }
    $foreign = @($owners | Where-Object { $_ -notin $treeIds })
    if ($foreign.Count -gt 0) {
        throw "$Name 所需端口 $($spec.Port) 已被未受本工具管理的进程占用（PID：$($foreign -join ', ')）。请先确认并手动关闭原服务，或执行 diagnose 查看详情；不会自动换端口或结束该进程。"
    }
}

function Start-ManagedService([string]$Name) {
    $spec = Get-ServiceSpec $Name
    foreach ($stream in @('stdout', 'stderr')) {
        Get-ChildItem -LiteralPath $script:LogDir -Filter "$Name-*-$stream.log" -File |
            Sort-Object LastWriteTime -Descending | Select-Object -Skip 4 |
            ForEach-Object { Remove-Item -LiteralPath $_.FullName }
    }
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
    $process = Start-Process -FilePath $spec.File -ArgumentList $spec.Arguments -WorkingDirectory $spec.Directory -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $script:LogDir "$Name-$stamp-stdout.log") `
        -RedirectStandardError (Join-Path $script:LogDir "$Name-$stamp-stderr.log")
    $info = Get-ProcessInfo $process.Id
    if ($null -eq $info) { throw "$Name 启动后立即退出，请查看 $script:LogDir。" }
    return Get-Identity $info
}

function Stop-ManagedService([string]$Name, $Saved) {
    if (-not (Test-ManagedProcess $Name $Saved)) {
        if (Test-Identity $Saved (Get-ProcessInfo $Saved.pid)) {
            throw "$Name 进程身份与记录一致，但启动命令不符合当前项目规则；保留记录并拒绝停止，请执行 diagnose 核查。"
        }
        Write-Host "$Name：运行记录已过期或身份不匹配，跳过停止。"
        return
    }
    $tree = @(Get-ProcessTree $Saved.pid | ForEach-Object { Get-Identity $_ })
    # Snapshot and recheck every identity; terminate children before their launcher.
    [array]::Reverse($tree)
    foreach ($entry in $tree) {
        if (Test-Identity $entry (Get-ProcessInfo $entry.pid)) {
            Stop-Process -Id $entry.pid -Force -ErrorAction Stop
        }
    }
    Write-Host "$Name：已停止。"
}

function Test-HttpReady([string]$Url, [switch]$Health) {
    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        if ($response.StatusCode -ne 200) { return $false }
        if ($Health) {
            $body = $response.Content | ConvertFrom-Json
            return ($body.status -eq 'ok' -and $body.service -eq 'AIExpHub API')
        }
        return ($response.Content -match '<div\s+id="app"')
    } catch { return $false }
}

function Wait-Ready($State, [int]$Limit) {
    $clock = [Diagnostics.Stopwatch]::StartNew()
    $checks = @(
        @{ url = 'http://127.0.0.1:8000/health'; health = $true },
        @{ url = $script:FrontendUrl; health = $false },
        @{ url = 'http://127.0.0.1:5173/api/health'; health = $true }
    )
    $ready = @{}
    while ($clock.Elapsed.TotalSeconds -lt $Limit) {
        foreach ($name in @('backend', 'frontend')) {
            if (-not (Test-ManagedProcess $name $State.services[$name])) { throw "$name 进程已退出或身份发生变化，请查看 $script:LogDir。" }
            Assert-PortOwnership $name $State.services[$name]
        }
        foreach ($check in $checks) {
            if ($clock.Elapsed.TotalSeconds -ge $Limit) { break }
            if (-not $ready[$check.url]) { $ready[$check.url] = Test-HttpReady $check.url -Health:$check.health }
        }
        if (@($checks | Where-Object { -not $ready[$_.url] }).Count -eq 0) { return }
        if ($clock.Elapsed.TotalSeconds -lt $Limit) { Start-Sleep -Milliseconds 500 }
    }
    $missing = @($checks | Where-Object { -not $ready[$_.url] } | ForEach-Object { $_.url })
    throw "服务在 $Limit 秒内未就绪：$($missing -join ', ')。请查看 $script:LogDir。"
}

function Start-Platform([switch]$SkipBrowser, [int]$Limit = 60) {
    $total = [Diagnostics.Stopwatch]::StartNew()
    Write-Host '[1/3] 检查运行环境'
    $versions = Assert-Environment
    $state = Read-State
    foreach ($name in @('backend', 'frontend')) { Assert-PortOwnership $name $state.services[$name] }
    $checkSeconds = $total.Elapsed.TotalSeconds
    Write-Host ('环境检查完成（{0:N2} 秒），Python {1} / Node {2}' -f $checkSeconds, $versions.Python, $versions.Node)
    $created = @()
    try {
        Write-Host '[2/3] 启动后端和前端'
        foreach ($name in @('backend', 'frontend')) {
            if (Test-ManagedProcess $name $state.services[$name]) { Write-Host "$name：复用已管理的服务。"; continue }
            # Recheck before each launch; Vite strictPort prevents silent fallback.
            Assert-PortOwnership $name $null
            $state.services[$name] = Start-ManagedService $name
            $created += $name
            Write-State $state
        }
        Write-Host '[3/3] 确认服务可用'
        Wait-Ready $state $Limit
        Write-Host ("AIExpHub 已启动：$script:FrontendUrl（总计 {0:N2} 秒）" -f $total.Elapsed.TotalSeconds)
        Write-Host "日志：$script:LogDir；停止请使用项目根目录的停止平台.cmd。"
        if (-not $SkipBrowser) {
            try { Start-Process $script:FrontendUrl } catch { Write-Host "浏览器未能自动打开，请手动访问 $script:FrontendUrl" }
        }
    } catch {
        $reason = $_
        foreach ($name in $created) {
            try {
                Stop-ManagedService $name $state.services[$name]
                $state.services.Remove($name)
            } catch { Write-Warning "清理 $name 失败：$($_.Exception.Message)。请执行 stop 重试。" }
        }
        Write-State $state
        throw $reason
    }
}

function Stop-Platform {
    $state = Read-State
    foreach ($name in @('frontend', 'backend')) {
        if ($null -ne $state.services[$name]) {
            Stop-ManagedService $name $state.services[$name]
            $state.services.Remove($name)
            Write-State $state
        }
    }
    Write-Host '停止完成。仅处理本工具记录且身份核验通过的进程。'
}

function Show-Diagnostics {
    Write-Host "项目：$script:ProjectRoot"
    Write-Host "运行记录：$script:StatePath"
    Write-Host "日志：$script:LogDir"
    try { $versions = Assert-Environment; Write-Host "基础环境正常：Python $($versions.Python)，Node $($versions.Node)" } catch { Write-Host $_.Exception.Message }
    $python = Join-Path $script:ProjectRoot 'backend\.venv\Scripts\python.exe'
    if (Test-Path -LiteralPath $python) {
        $result = Invoke-NativeProbe $python @('-m', 'pip', 'check')
        Write-Host "pip check（退出码 $($result.Code)）：$($result.Output)"
    }
    if (Get-Command npm.cmd -ErrorAction SilentlyContinue) {
        $result = Invoke-NativeProbe 'npm.cmd' @('--prefix', (Join-Path $script:ProjectRoot 'frontend'), 'ls', '--depth=0')
        Write-Host "npm ls（退出码 $($result.Code)）：$($result.Output)"
    }
    try { $state = Read-State } catch { Write-Host $_.Exception.Message; $state = New-State }
    foreach ($name in @('backend', 'frontend')) {
        $port = if ($name -eq 'backend') { 8000 } else { 5173 }
        foreach ($ownerId in @(Get-PortOwners $port)) {
            $info = Get-ProcessInfo $ownerId
            Write-Host "端口 $port / PID $ownerId / $($info.ExecutablePath)"
            Write-Host $info.CommandLine
        }
        try { Write-Host "$name 受本工具管理：$(Test-ManagedProcess $name $state.services[$name])" } catch { Write-Host $_.Exception.Message }
    }
    foreach ($url in @('http://127.0.0.1:8000/health', 'http://127.0.0.1:5173/api/health')) { Write-Host "$url 可用：$(Test-HttpReady $url -Health)" }
    if (Test-Path -LiteralPath $script:LogDir) {
        Get-ChildItem -LiteralPath $script:LogDir -Filter '*-stderr.log' | Sort-Object LastWriteTime -Descending | Select-Object -First 2 | ForEach-Object {
            Write-Host "最近错误日志：$($_.FullName)"
            Get-Content -LiteralPath $_.FullName -Tail 12
        }
    }
}

function Invoke-Manager {
    if ($Action -eq 'diagnose') { Show-Diagnostics; return }
    New-Item -ItemType Directory -Path $script:LogDir -Force | Out-Null
    $lock = $null
    try {
        try { $lock = [IO.File]::Open((Join-Path $script:RuntimeDir 'manager.lock'), 'OpenOrCreate', 'ReadWrite', 'None') }
        catch { throw '另一个启动或停止操作正在进行，请稍后重试。' }
        if ($Action -eq 'start') { Start-Platform -SkipBrowser:$NoBrowser -Limit $TimeoutSeconds } else { Stop-Platform }
    } finally { if ($null -ne $lock) { $lock.Dispose() } }
}

if ($MyInvocation.InvocationName -ne '.') {
    try { Invoke-Manager; exit 0 }
    catch { Write-Host "操作失败：$($_.Exception.Message)" -ForegroundColor Red; exit 1 }
}

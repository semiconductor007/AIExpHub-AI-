# Run with Windows PowerShell 5.1; no Pester, network, real services or business DB required.
$ErrorActionPreference = 'Stop'
$manager = Join-Path (Split-Path -Parent $PSScriptRoot) 'manage-local.ps1'
$script:passed = 0
$script:failed = 0

function Assert-True($Value, [string]$Message) { if (-not $Value) { throw $Message } }
function Assert-Throws([scriptblock]$Body, [string]$Pattern) {
    try { & $Body } catch {
        if ($_.Exception.Message -match $Pattern) { return }
        throw "Unexpected error: $($_.Exception.Message)"
    }
    throw 'Expected an error'
}
function Test-Case([string]$Name, [scriptblock]$Body) {
    try {
        . $manager
        & $Body
        $script:passed++
        Write-Host "PASS $Name"
    } catch { $script:failed++; Write-Host "FAIL $Name : $($_.Exception.Message)" }
}

Test-Case 'Identity requires PID, creation time, executable and exact command' {
    $current = [pscustomobject]@{ ProcessId = 42; CreationDate = [datetime]::UtcNow; ExecutablePath = 'C:\node.exe'; CommandLine = 'node fixture' }
    $saved = Get-Identity $current
    Assert-True (Test-Identity $saved $current) 'Matching process rejected'
    $saved.created = '0'
    Assert-True (-not (Test-Identity $saved $current)) 'Reused PID accepted'
    Assert-True (-not (Test-Identity $saved $null)) 'Missing process accepted'
}

Test-Case 'An unrelated command cannot become managed just by editing state' {
    $script:fake = [pscustomobject]@{ ProcessId = 42; CreationDate = [datetime]::UtcNow; ExecutablePath = 'C:\node.exe'; CommandLine = 'unrelated' }
    function Get-ProcessInfo { return $script:fake }
    Assert-True (-not (Test-ManagedProcess 'frontend' (Get-Identity $script:fake))) 'Unrelated command trusted'
}

Test-Case 'Windows PowerShell trailing command whitespace is supported' {
    $spec = Get-ServiceSpec backend
    $script:fake = [pscustomobject]@{ ProcessId = 42; CreationDate = [datetime]::UtcNow; ExecutablePath = $spec.File; CommandLine = ('"' + $spec.File + '" ' + $spec.Arguments + ' ') }
    function Get-ProcessInfo { return $script:fake }
    Assert-True (Test-ManagedProcess 'backend' (Get-Identity $script:fake)) 'Valid launcher command rejected'
}

Test-Case 'Foreign port is rejected without stopping anything' {
    function Get-PortOwners { return @(42) }
    function Test-ManagedProcess { return $false }
    Assert-Throws { Assert-PortOwnership 'backend' $null } '8000.*42'
}

Test-Case 'Managed launcher may own a port through its Python child' {
    function Get-PortOwners { return @(43) }
    function Test-ManagedProcess { return $true }
    function Get-ProcessTree { return @([pscustomobject]@{ ProcessId = 42 }, [pscustomobject]@{ ProcessId = 43 }) }
    Assert-PortOwnership 'backend' @{ pid = 42 }
}

Test-Case 'An additional foreign listener is still a conflict' {
    function Get-PortOwners { return @(43, 99) }
    function Test-ManagedProcess { return $true }
    function Get-ProcessTree { return @([pscustomobject]@{ ProcessId = 42 }, [pscustomobject]@{ ProcessId = 43 }) }
    Assert-Throws { Assert-PortOwnership 'backend' @{ pid = 42 } } '99'
}

Test-Case 'Stop skips a stale identity' {
    function Test-ManagedProcess { return $false }
    function Stop-Process { throw 'Must never stop an unrelated PID' }
    Stop-ManagedService 'frontend' @{ pid = 42 }
}

Test-Case 'Stop rechecks children and stops child before parent' {
    $script:stopped = @()
    $script:parent = [pscustomobject]@{ ProcessId = 42; CreationDate = [datetime]::UtcNow; ExecutablePath = 'p'; CommandLine = 'p' }
    $script:child = [pscustomobject]@{ ProcessId = 43; CreationDate = [datetime]::UtcNow; ExecutablePath = 'c'; CommandLine = 'c' }
    function Test-ManagedProcess { return $true }
    function Get-ProcessTree { return @($script:parent, $script:child) }
    function Get-ProcessInfo([int]$ProcessId) { if ($ProcessId -eq 42) { return $script:parent }; return $script:child }
    function Stop-Process([int]$Id, [switch]$Force) { $script:stopped += $Id }
    Stop-ManagedService 'backend' @{ pid = 42 }
    Assert-True (($script:stopped -join ',') -eq '43,42') 'Wrong shutdown order'
}

Test-Case 'Partial launch failure cleans only newly started services' {
    $script:stopped = @()
    function Assert-Environment { return @{ Python = 'test'; Node = 'test' } }
    function Read-State { return (New-State) }
    function Assert-PortOwnership {}
    function Test-ManagedProcess { return $false }
    function Start-ManagedService([string]$Name) { if ($Name -eq 'frontend') { throw 'fixture launch failure' }; return @{ pid = 42 } }
    function Write-State {}
    function Stop-ManagedService([string]$Name, $Saved) { $script:stopped += $Name }
    Assert-Throws { Start-Platform -SkipBrowser } 'fixture launch failure'
    Assert-True (($script:stopped -join ',') -eq 'backend') 'New backend not cleaned'
}

Test-Case 'Readiness failure preserves the backend that was already running' {
    $script:stopped = @()
    function Assert-Environment { return @{ Python = 'test'; Node = 'test' } }
    function Read-State { $s = New-State; $s.services.backend = @{ pid = 42 }; return $s }
    function Assert-PortOwnership {}
    function Test-ManagedProcess([string]$Name, $Saved) { return ($Name -eq 'backend') }
    function Start-ManagedService { return @{ pid = 43 } }
    function Write-State {}
    function Wait-Ready { throw 'fixture health failure' }
    function Stop-ManagedService([string]$Name, $Saved) { $script:stopped += $Name }
    Assert-Throws { Start-Platform -SkipBrowser } 'fixture health failure'
    Assert-True (($script:stopped -join ',') -eq 'frontend') 'Existing backend was touched'
}

Test-Case 'Repeated start reuses both services' {
    $script:waited = 0
    function Assert-Environment { return @{ Python = 'test'; Node = 'test' } }
    function Read-State { $s = New-State; $s.services.backend = @{ pid = 42 }; $s.services.frontend = @{ pid = 43 }; return $s }
    function Assert-PortOwnership {}
    function Test-ManagedProcess { return $true }
    function Start-ManagedService { throw 'Must not launch another process' }
    function Wait-Ready { $script:waited++ }
    Start-Platform -SkipBrowser
    Assert-True ($script:waited -eq 1) 'Existing services not checked'
}

Test-Case 'Browser opens only after all readiness checks pass' {
    $script:ready = $false
    $script:opened = ''
    function Assert-Environment { return @{ Python = 'test'; Node = 'test' } }
    function Read-State { $s = New-State; $s.services.backend = @{ pid = 42 }; $s.services.frontend = @{ pid = 43 }; return $s }
    function Assert-PortOwnership {}
    function Test-ManagedProcess { return $true }
    function Wait-Ready { $script:ready = $true }
    function Start-Process([string]$FilePath) {
        Assert-True $script:ready 'Browser opened before readiness'
        $script:opened = $FilePath
    }
    Start-Platform
    Assert-True ($script:opened -eq 'http://127.0.0.1:5173/') 'Wrong browser URL'
}

Test-Case 'Failed cleanup retains the process record for a later stop' {
    $script:saved = $null
    function Assert-Environment { return @{ Python = 'test'; Node = 'test' } }
    function Read-State { return (New-State) }
    function Assert-PortOwnership {}
    function Test-ManagedProcess { return $false }
    function Start-ManagedService([string]$Name) { if ($Name -eq 'frontend') { throw 'fixture launch failure' }; return @{ pid = 42 } }
    function Write-State($State) { $script:saved = $State }
    function Stop-ManagedService { throw 'fixture cleanup failure' }
    Assert-Throws { Start-Platform -SkipBrowser } 'fixture launch failure'
    Assert-True ($script:saved.services.backend.pid -eq 42) 'Cleanup failure lost process record'
}

Test-Case 'Readiness includes backend, HTML and frontend proxy, then returns' {
    $script:urls = @()
    function Test-ManagedProcess { return $true }
    function Assert-PortOwnership {}
    function Test-HttpReady([string]$Url, [switch]$Health) { $script:urls += $Url; return $true }
    Wait-Ready (New-State) 1
    Assert-True ($script:urls.Count -eq 3 -and $script:urls[2] -like '*/api/health') 'Missing end-to-end proxy check'
}

Test-Case 'Readiness timeout is bounded and reports unavailable endpoint' {
    function Test-ManagedProcess { return $true }
    function Assert-PortOwnership {}
    function Test-HttpReady { return $false }
    $timer = [Diagnostics.Stopwatch]::StartNew()
    Assert-Throws { Wait-Ready (New-State) 1 } 'api/health'
    Assert-True ($timer.Elapsed.TotalSeconds -lt 3) 'Readiness did not stop'
}

Test-Case 'Missing virtualenv gives actionable error without installing anything' {
    $script:ProjectRoot = Join-Path ([IO.Path]::GetTempPath()) ('missing-aiexphub-' + [guid]::NewGuid())
    Assert-Throws { Assert-Environment } 'python -m venv'
}

Test-Case 'Malformed state is rejected without process operations' {
    $testDirectory = Join-Path ([IO.Path]::GetTempPath()) ('aiexphub-state-' + [guid]::NewGuid())
    New-Item -ItemType Directory -Path $testDirectory | Out-Null
    $script:StatePath = Join-Path $testDirectory 'services.json'
    try {
        '{broken' | Set-Content -LiteralPath $script:StatePath
        Assert-Throws { Read-State } 'services.json'
    } finally { Remove-Item -LiteralPath $script:StatePath; Remove-Item -LiteralPath $testDirectory }
}

Test-Case 'State roundtrip retains identity and rejects another project root' {
    $testDirectory = Join-Path ([IO.Path]::GetTempPath()) ('aiexphub-state-' + [guid]::NewGuid())
    New-Item -ItemType Directory -Path $testDirectory | Out-Null
    $script:StatePath = Join-Path $testDirectory 'services.json'
    try {
        $state = New-State
        $state.services.backend = @{ pid = 42; created = '123'; executable = 'p'; command = 'c' }
        Write-State $state
        $loaded = Read-State
        Assert-True ($loaded.services.backend.pid -eq 42 -and $loaded.services.backend.created -eq '123') 'Identity lost'
        $script:ProjectRoot = 'C:\another-project'
        Assert-Throws { Read-State } 'services.json'
    } finally { Remove-Item -LiteralPath $script:StatePath; Remove-Item -LiteralPath $testDirectory }
}

Write-Host "$script:passed passed, $script:failed failed"
if ($script:failed -gt 0) { exit 1 }

<#
.SYNOPSIS
    ProcessGuard - watches the apps you open, offers to clean up processes an
    app leaves running after you close it, and warns when CPU or RAM stays high.

.DESCRIPTION
    Every few seconds ProcessGuard:
      * shows a live dashboard: CPU %, RAM %, and the top processes by usage
      * remembers every app that has a window open
      * when an app's last window closes but its processes keep running
        (after a grace period), asks you whether to end them
      * when CPU or RAM stays above the alert level, lists the biggest apps
        and asks whether to close the top one

    Nothing is ever closed without you clicking "Yes". Windows system
    processes and security software are never offered for closing.

    Settings (apps you chose "never ask" for) are saved in
    %LOCALAPPDATA%\ProcessGuard\settings.json, and every action is logged to
    %LOCALAPPDATA%\ProcessGuard\log.txt.

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File .\ProcessGuard.ps1

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File .\ProcessGuard.ps1 -RamAlertPercent 80 -GraceSeconds 30
#>
param(
    # How often to check, in seconds.
    [int]$IntervalSeconds = 5,
    # How long an app may keep running after its last window closes before you are asked.
    [int]$GraceSeconds = 20,
    # Alert when total CPU usage is at or above this percentage...
    [int]$CpuAlertPercent = 85,
    # ...or when RAM usage is at or above this percentage...
    [int]$RamAlertPercent = 85,
    # ...for at least this many seconds in a row.
    [int]$SustainSeconds = 30,
    # Minimum time between two high-usage alerts.
    [int]$AlertCooldownMinutes = 10
)

Add-Type -AssemblyName System.Windows.Forms

$DataDir      = Join-Path $env:LOCALAPPDATA 'ProcessGuard'
$SettingsFile = Join-Path $DataDir 'settings.json'
$LogFile      = Join-Path $DataDir 'log.txt'
New-Item -ItemType Directory -Path $DataDir -Force | Out-Null

# Never offered for closing: Windows itself, security software, and the console running this script.
$ProtectedSet = New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::OrdinalIgnoreCase)
@(
    'System', 'Idle', 'Registry', 'Memory Compression', 'Secure System', 'smss', 'csrss', 'wininit',
    'winlogon', 'services', 'lsass', 'LsaIso', 'svchost', 'dwm', 'explorer', 'sihost', 'ctfmon',
    'fontdrvhost', 'taskhostw', 'RuntimeBroker', 'dllhost', 'conhost', 'audiodg', 'spoolsv',
    'ShellExperienceHost', 'StartMenuExperienceHost', 'SearchHost', 'SearchApp', 'SearchIndexer',
    'TextInputHost', 'ShellHost', 'ApplicationFrameHost', 'SystemSettings', 'LockApp',
    'backgroundTaskHost', 'UserOOBEBroker', 'dasHost', 'WUDFHost', 'WmiPrvSE', 'smartscreen',
    'MsMpEng', 'NisSrv', 'SecurityHealthService', 'SecurityHealthSystray', 'MpDefenderCoreService',
    'Taskmgr', 'powershell', 'pwsh', 'powershell_ise', 'WindowsTerminal', 'OpenConsole', 'cmd'
) | ForEach-Object { [void]$ProtectedSet.Add($_) }

# Apps the user chose "never ask" for (tray apps such as Discord, Teams, OneDrive).
$Ignored = New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::OrdinalIgnoreCase)
if (Test-Path $SettingsFile) {
    try {
        $saved = Get-Content $SettingsFile -Raw | ConvertFrom-Json
        foreach ($name in @($saved.IgnoredApps)) { if ($name) { [void]$Ignored.Add($name) } }
    } catch {
        Write-Warning "Could not read $SettingsFile; starting with an empty ignore list."
    }
}

function Save-Settings {
    @{ IgnoredApps = @($Ignored | Sort-Object) } | ConvertTo-Json | Set-Content -Path $SettingsFile -Encoding UTF8
}

$Events = New-Object System.Collections.Generic.List[string]
function Write-Event([string]$Message) {
    $line = '{0:HH:mm:ss}  {1}' -f (Get-Date), $Message
    $Events.Add($line)
    while ($Events.Count -gt 8) { $Events.RemoveAt(0) }
    Add-Content -Path $LogFile -Value ('{0:yyyy-MM-dd} {1}' -f (Get-Date), $line)
}

# Shows a dialog on top of all windows and returns 'Yes', 'No' or 'Cancel'. "No" is the default button.
function Ask-User([string]$Text, [string]$Buttons = 'YesNo') {
    [System.Windows.Forms.MessageBox]::Show(
        $Text, 'ProcessGuard',
        [System.Windows.Forms.MessageBoxButtons]$Buttons,
        [System.Windows.Forms.MessageBoxIcon]::Question,
        [System.Windows.Forms.MessageBoxDefaultButton]::Button2,
        [System.Windows.Forms.MessageBoxOptions]::DefaultDesktopOnly).ToString()
}

function Format-MB([double]$MB) { '{0:N0} MB' -f $MB }

# Returns the ids of the given processes plus every process they started (children, grandchildren, ...).
function Get-ProcessTree([int[]]$RootIds) {
    $all = @(Get-CimInstance Win32_Process -Property ProcessId, ParentProcessId, Name, CreationDate)
    $byId = @{}
    $children = @{}
    foreach ($p in $all) {
        $byId[[int]$p.ProcessId] = $p
        $parent = [int]$p.ParentProcessId
        if (-not $children.ContainsKey($parent)) { $children[$parent] = New-Object System.Collections.Generic.List[object] }
        $children[$parent].Add($p)
    }
    $result = New-Object 'System.Collections.Generic.HashSet[int]'
    $queue = New-Object System.Collections.Generic.Queue[int]
    foreach ($id in $RootIds) { if ($result.Add($id)) { $queue.Enqueue($id) } }
    while ($queue.Count -gt 0) {
        $id = $queue.Dequeue()
        if (-not $children.ContainsKey($id) -or -not $byId.ContainsKey($id)) { continue }
        foreach ($child in $children[$id]) {
            $childName = [IO.Path]::GetFileNameWithoutExtension($child.Name)
            # A child started before its "parent" means the parent id was reused; skip it.
            if ($child.CreationDate -lt $byId[$id].CreationDate) { continue }
            if ($ProtectedSet.Contains($childName)) { continue }
            if ($result.Add([int]$child.ProcessId)) { $queue.Enqueue([int]$child.ProcessId) }
        }
    }
    , @($result)
}

# Force-ends the given process ids. Returns how many could not be ended.
function Stop-ProcessIds([int[]]$Ids) {
    $failed = 0
    foreach ($id in $Ids) {
        try {
            Stop-Process -Id $id -Force -ErrorAction Stop
        } catch {
            # Already gone (for example a child that exited with its parent) counts as success.
            if (Get-Process -Id $id -ErrorAction SilentlyContinue) { $failed++ }
        }
    }
    $failed
}

function Get-Snapshot {
    $now = Get-Date
    $elapsed = ($now - $script:PrevTime).TotalSeconds
    $script:PrevTime = $now
    $newCpu = @{}
    $rows = foreach ($p in Get-Process) {
        $cpuSeconds = $p.CPU
        $cpuPct = 0.0
        if ($null -ne $cpuSeconds) {
            $newCpu[$p.Id] = $cpuSeconds
            if ($script:PrevCpu.ContainsKey($p.Id) -and $elapsed -gt 0) {
                $cpuPct = [math]::Max(0, ($cpuSeconds - $script:PrevCpu[$p.Id]) / $elapsed / $Cores * 100)
            }
        }
        [pscustomobject]@{
            Name      = $p.ProcessName
            Id        = $p.Id
            MB        = $p.WorkingSet64 / 1MB
            Cpu       = $cpuPct
            HasWindow = ($p.MainWindowHandle -ne [IntPtr]::Zero)
            Mine      = ($p.SessionId -eq $MySession -and $p.Id -ne $PID -and -not $ProtectedSet.Contains($p.ProcessName))
        }
    }
    $script:PrevCpu = $newCpu

    $os = Get-CimInstance Win32_OperatingSystem -Property TotalVisibleMemorySize, FreePhysicalMemory
    $totalGB = $os.TotalVisibleMemorySize / 1MB
    $usedGB = ($os.TotalVisibleMemorySize - $os.FreePhysicalMemory) / 1MB
    try {
        $cpuTotal = [double](Get-CimInstance Win32_PerfFormattedData_PerfOS_Processor -Filter "Name='_Total'" -ErrorAction Stop).PercentProcessorTime
    } catch {
        $cpuTotal = [double](Get-CimInstance Win32_Processor | Measure-Object LoadPercentage -Average).Average
    }

    [pscustomobject]@{
        Time    = $now
        Rows    = @($rows)
        CpuPct  = $cpuTotal
        RamPct  = 100 * $usedGB / $totalGB
        UsedGB  = $usedGB
        TotalGB = $totalGB
    }
}

function Get-Groups($Rows) {
    foreach ($g in ($Rows | Group-Object Name)) {
        $mb = 0.0; $cpu = 0.0
        foreach ($r in $g.Group) { $mb += $r.MB; $cpu += $r.Cpu }
        [pscustomobject]@{ Name = $g.Name; Count = $g.Count; MB = $mb; Cpu = $cpu }
    }
}

# Called when a tracked app has had no window for $GraceSeconds but still has processes running.
function Invoke-LeftoverCleanup([string]$AppName, $Snapshot) {
    $rootIds = @($Snapshot.Rows | Where-Object { $_.Mine -and $_.Name -eq $AppName } | ForEach-Object { $_.Id })
    $treeIds = Get-ProcessTree $rootIds
    $targets = @($Snapshot.Rows | Where-Object { $treeIds -contains $_.Id })
    $mb = ($targets | Measure-Object MB -Sum).Sum
    $otherNames = @($targets | Where-Object { $_.Name -ne $AppName } | ForEach-Object { $_.Name } | Sort-Object -Unique)
    $extra = ''
    if ($otherNames.Count) { $extra = "`n(includes helper processes: $($otherNames -join ', '))" }

    $answer = Ask-User ("'$AppName' was closed, but $($targets.Count) of its processes are still running " +
        "in the background, using $(Format-MB $mb) of RAM.$extra`n`n" +
        "Some apps keep running on purpose (tray icon, sync, notifications).`n`n" +
        "Yes  = end them now`n" +
        "No  = leave them running (ask again next time you close it)`n" +
        "Cancel  = never ask about '$AppName' again") 'YesNoCancel'

    switch ($answer) {
        'Yes' {
            # The dialog may have been open for a while; don't kill an app the user has reopened.
            $reopened = Get-Process -Name $AppName -ErrorAction SilentlyContinue |
                Where-Object { $_.MainWindowHandle -ne [IntPtr]::Zero }
            if ($reopened) {
                Write-Event "Skipped $AppName (it was reopened)"
                return
            }
            $failed = Stop-ProcessIds @($targets | ForEach-Object { $_.Id })
            if ($failed) {
                Write-Event "Ended $AppName, but $failed process(es) refused (run as administrator to end them)"
            } else {
                Write-Event "Ended $AppName ($($targets.Count) processes, freed ~$(Format-MB $mb))"
            }
        }
        'Cancel' {
            [void]$Ignored.Add($AppName)
            Save-Settings
            Write-Event "Will never ask about $AppName (edit $SettingsFile to undo)"
        }
        default { Write-Event "Kept $AppName running in background" }
    }
}

# Called when CPU or RAM has stayed above the alert level for $SustainSeconds.
function Invoke-HighUsageAlert($Snapshot) {
    $byRam = $Snapshot.RamPct -ge $RamAlertPercent
    $what = if ($byRam) { 'RAM usage has been at {0:N0}%' -f $Snapshot.RamPct } else { 'CPU usage has been at {0:N0}%' -f $Snapshot.CpuPct }
    $sortKey = if ($byRam) { 'MB' } else { 'Cpu' }
    $top = @(Get-Groups @($Snapshot.Rows | Where-Object Mine) | Sort-Object $sortKey -Descending | Select-Object -First 5)
    if (-not $top.Count) { return }

    $list = ($top | ForEach-Object { '  {0,-28} {1,10}   CPU {2,3:N0}%   ({3} proc)' -f $_.Name, (Format-MB $_.MB), $_.Cpu, $_.Count }) -join "`n"
    $first = $top[0]
    $answer = Ask-User ("$what for over $SustainSeconds seconds.`n`nBiggest apps right now:`n$list`n`n" +
        "Close '$($first.Name)'?`n`n" +
        "Apps with an open window are asked to close normally, so they can offer to save your work.") 'YesNo'

    if ($answer -ne 'Yes') { Write-Event "High-usage alert: kept $($first.Name)"; return }

    $procs = @(Get-Process -Name $first.Name -ErrorAction SilentlyContinue | Where-Object { $_.SessionId -eq $MySession })
    $windowed = @($procs | Where-Object { $_.MainWindowHandle -ne [IntPtr]::Zero })
    if ($windowed.Count) {
        foreach ($p in $windowed) { [void]$p.CloseMainWindow() }
        # Any background processes it leaves behind are then offered by the leftover check.
        Write-Event "Asked $($first.Name) to close its window(s)"
    } else {
        $ids = Get-ProcessTree @($procs | ForEach-Object { $_.Id })
        $failed = Stop-ProcessIds $ids
        if ($failed) { Write-Event "Ended $($first.Name), but $failed process(es) refused (run as administrator)" }
        else { Write-Event "Ended $($first.Name) (freed ~$(Format-MB $first.MB))" }
    }
}

function Get-Bar([double]$Pct) {
    $n = [int][math]::Round([math]::Min(100, [math]::Max(0, $Pct)) / 5)
    ('#' * $n).PadRight(20, '.')
}

function Get-LevelColor([double]$Pct, [int]$Limit) {
    if ($Pct -ge $Limit) { 'Red' } elseif ($Pct -ge $Limit - 15) { 'Yellow' } else { 'Green' }
}

function Show-Dashboard($Snapshot) {
    Clear-Host
    Write-Host ('ProcessGuard   {0:HH:mm:ss}   (press Ctrl+C to stop)' -f $Snapshot.Time) -ForegroundColor Cyan
    Write-Host ''
    Write-Host 'CPU  ' -NoNewline
    Write-Host ('[{0}] {1,3:N0}%' -f (Get-Bar $Snapshot.CpuPct), $Snapshot.CpuPct) -ForegroundColor (Get-LevelColor $Snapshot.CpuPct $CpuAlertPercent)
    Write-Host 'RAM  ' -NoNewline
    Write-Host ('[{0}] {1,3:N0}%   {2:N1} / {3:N1} GB' -f (Get-Bar $Snapshot.RamPct), $Snapshot.RamPct, $Snapshot.UsedGB, $Snapshot.TotalGB) -ForegroundColor (Get-LevelColor $Snapshot.RamPct $RamAlertPercent)
    Write-Host ''

    $open = @($Apps.Keys | Where-Object { $Apps[$_].State -eq 'open' } | Sort-Object)
    $openText = $open -join ', '
    if ($openText.Length -gt 100) { $openText = $openText.Substring(0, 97) + '...' }
    Write-Host ("Open apps ({0}): {1}" -f $open.Count, $openText)
    $closing = @($Apps.Keys | Where-Object { $Apps[$_].State -eq 'closing' } | Sort-Object)
    if ($closing.Count) { Write-Host ("Closed, still running: {0}" -f ($closing -join ', ')) -ForegroundColor Yellow }
    Write-Host ''

    Write-Host ('{0,-30} {1,6} {2,10} {3,7}' -f 'Top processes', 'Procs', 'RAM', 'CPU') -ForegroundColor Cyan
    foreach ($g in (Get-Groups $Snapshot.Rows | Sort-Object MB -Descending | Select-Object -First 12)) {
        $label = $g.Name
        if ($ProtectedSet.Contains($g.Name)) { $label += ' (system)' }
        Write-Host ('{0,-30} {1,6} {2,10} {3,6:N1}%' -f $label, $g.Count, (Format-MB $g.MB), $g.Cpu)
    }
    Write-Host ''
    Write-Host 'Recent events' -ForegroundColor Cyan
    if ($Events.Count) { $Events | ForEach-Object { Write-Host "  $_" } } else { Write-Host '  (none yet)' }
}

# --- main loop ---------------------------------------------------------------

$Cores = [Environment]::ProcessorCount
$MySession = (Get-Process -Id $PID).SessionId
$PrevCpu = @{}
$PrevTime = Get-Date
$Apps = @{}          # app name -> @{ State = 'open' | 'closing' | 'handled'; Since = [datetime] }
$HighSince = $null
$LastAlert = [datetime]::MinValue
$FirstTick = $true

Write-Event 'ProcessGuard started'
try {
    while ($true) {
        $snap = Get-Snapshot
        $now = $snap.Time

        # Track every app that currently has a window.
        $windowed = @($snap.Rows | Where-Object { $_.Mine -and $_.HasWindow } | ForEach-Object { $_.Name } | Sort-Object -Unique)
        foreach ($name in $windowed) {
            if (-not $FirstTick -and (-not $Apps.ContainsKey($name) -or $Apps[$name].State -ne 'open')) {
                Write-Event "Opened $name"
            }
            $Apps[$name] = @{ State = 'open'; Since = $now }
        }
        if ($FirstTick) { Write-Event "Watching $($windowed.Count) open apps" }
        $FirstTick = $false

        # Check apps whose windows are all gone.
        foreach ($name in @($Apps.Keys)) {
            if ($windowed -contains $name) { continue }
            $app = $Apps[$name]
            $left = @($snap.Rows | Where-Object { $_.Mine -and $_.Name -eq $name })
            if (-not $left.Count) {
                if ($app.State -ne 'handled') { Write-Event "Closed $name (nothing left running)" }
                $Apps.Remove($name)
                continue
            }
            if ($app.State -eq 'open') {
                $app.State = 'closing'
                $app.Since = $now
            } elseif ($app.State -eq 'closing' -and ($now - $app.Since).TotalSeconds -ge $GraceSeconds) {
                $app.State = 'handled'
                if (-not $Ignored.Contains($name)) { Invoke-LeftoverCleanup $name $snap }
            }
        }

        # Sustained high CPU or RAM.
        if ($snap.CpuPct -ge $CpuAlertPercent -or $snap.RamPct -ge $RamAlertPercent) {
            if (-not $HighSince) { $HighSince = $now }
            if (($now - $HighSince).TotalSeconds -ge $SustainSeconds -and
                ($now - $LastAlert).TotalMinutes -ge $AlertCooldownMinutes) {
                $LastAlert = $now
                Invoke-HighUsageAlert $snap
            }
        } else {
            $HighSince = $null
        }

        Show-Dashboard $snap
        Start-Sleep -Seconds $IntervalSeconds
    }
} finally {
    Write-Event 'ProcessGuard stopped'
}

param(
  [string]$Platform = "",
  [string]$SourceRoot = "./kuno-workflow-onboard-skills",
  [string]$ProjectRoot = "",
  [ValidateSet("", "init", "reset")]
  [string]$Action = "",
  [ValidateSet("", "global", "project", "none")]
  [string]$SkillsScope = "",
  [switch]$SkipProjectAgents,
  [string]$GlobalAgentsPath = "",
  [string]$GlobalSkillsDir = "",
  [string]$ProjectSkillsDir = "",
  [string]$TrellisUser = "",
  [string[]]$TrellisPlatform = @(),
  [switch]$SkipTrellisInit,
  [switch]$SkipTrellisBootstrap,
  [switch]$NoMcp,
  [switch]$DryRun,
  [switch]$Yes,
  [switch]$NoColor,
  [switch]$Help
)

$ErrorActionPreference = "Stop"

$ExternalSkills = @(
  "diagnosing-bugs",
  "tdd",
  "grill-me",
  "grill-with-docs",
  "grilling",
  "domain-modeling",
  "codebase-design",
  "handoff",
  "writing-great-skills",
  "to-prd",
  "to-issues",
  "impeccable",
  "ui-ux-pro-max",
  "web-ui-autotest-generator",
  "shadcn"
)

function Show-Usage {
  @"
Kuno workflow installer

Usage:
  .\install.ps1 [options]

Options:
  -Platform <codex|claude|kimi|oh-my-pi|omp>
      Target coding agent tool. "omp" is an alias for "oh-my-pi".
  -SourceRoot <path>
      Path to the kuno-workflow-onboard-skills directory.
      Defaults to ./kuno-workflow-onboard-skills.
  -ProjectRoot <path>
      Target project root for project AGENTS.md, .gitignore, and project skills.
  -Action <init|reset>
      Onboard operation to run.
  -SkillsScope <global|project|none>
      Install bundled skills globally, into the project, or skip them.
  -SkipProjectAgents
      Do not install project AGENTS.md.
  -GlobalAgentsPath <path>
      Override the global AGENTS.md target.
  -GlobalSkillsDir <path>
      Override global skills directory.
  -ProjectSkillsDir <path>
      Override project-level skills directory.
  -TrellisUser <name>
      Developer username for trellis init -u when the project has no .trellis/.
  -TrellisPlatform <name[,name...]>
      Trellis init platform flag without leading dashes. May be repeated.
      Examples: codex, claude, cursor, opencode, gemini, pi.
  -SkipTrellisInit
      Skip post-install trellis init for project roots without .trellis/.
  -SkipTrellisBootstrap
      Skip post-install bootstrap task detection.
  -NoMcp
      Skip MCP configuration.
  -DryRun
      Print commands and MCP writes without making changes.
  -Yes
      Skip the final execution confirmation.
  -NoColor
      Disable ANSI color.
  -Help
      Show this help.
"@
}

function Stop-WithMessage {
  param([string]$Message)
  Write-Error $Message
  exit 1
}

function Write-Warn {
  param([string]$Message)
  Write-Warning $Message
}

function Use-Color {
  return (-not $NoColor.IsPresent) -and (-not $env:NO_COLOR) -and ($Host.UI.RawUI -ne $null)
}

function Write-Colored {
  param(
    [string]$Text,
    [ConsoleColor]$Color = [ConsoleColor]::Magenta
  )
  if (Use-Color) {
    Write-Host $Text -ForegroundColor $Color
  }
  else {
    Write-Host $Text
  }
}

function Show-Logo {
  if (Use-Color) {
    Write-Host "    K  K" -ForegroundColor DarkMagenta
    Write-Host "    K K " -ForegroundColor DarkMagenta
    Write-Host "    KK  " -ForegroundColor Magenta
    Write-Host "    K K " -ForegroundColor Magenta
    Write-Host "    K  K" -ForegroundColor Magenta
  }
  else {
    Write-Host "    K  K"
    Write-Host "    K K"
    Write-Host "    KK"
    Write-Host "    K K"
    Write-Host "    K  K"
  }
  Write-Host ""
  Write-Colored "Kuno Workflow Installer" Magenta
  Write-Host ""
}

function Normalize-Platform {
  param([string]$Value)
  $normalized = $Value.ToLowerInvariant().Replace("_", "-")
  switch ($normalized) {
    "codex" { return "codex" }
    "claude" { return "claude" }
    "claude-code" { return "claude" }
    "claudecode" { return "claude" }
    "kimi" { return "kimi" }
    "kimi-code" { return "kimi" }
    "kimicode" { return "kimi" }
    "oh-my-pi" { return "oh-my-pi" }
    "ohmypi" { return "oh-my-pi" }
    "omp" { return "oh-my-pi" }
    default { Stop-WithMessage "Unsupported platform: $Value" }
  }
}

function Platform-Label {
  param([string]$Value)
  switch ($Value) {
    "codex" { return "Codex" }
    "claude" { return "Claude Code" }
    "kimi" { return "Kimi Code" }
    "oh-my-pi" { return "Oh My Pi" }
    default { return $Value }
  }
}

function Prompt-Text {
  param(
    [string]$Prompt,
    [string]$Default = ""
  )
  if ($Default) {
    $value = Read-Host "$Prompt [$Default]"
    if ([string]::IsNullOrWhiteSpace($value)) { return $Default }
    return $value
  }
  return (Read-Host $Prompt)
}

function Prompt-YesNo {
  param(
    [string]$Prompt,
    [string]$Default = "n"
  )
  $suffix = if ($Default -eq "y") { "[Y/n]" } else { "[y/N]" }
  while ($true) {
    $value = Read-Host "$Prompt $suffix"
    if ([string]::IsNullOrWhiteSpace($value)) { $value = $Default }
    switch ($value.ToLowerInvariant()) {
      "y" { return $true }
      "yes" { return $true }
      "n" { return $false }
      "no" { return $false }
      default { Write-Host "Please answer y or n." }
    }
  }
}

function Select-One {
  param(
    [string]$Prompt,
    [string[]]$Options
  )
  Write-Host $Prompt
  for ($i = 0; $i -lt $Options.Count; $i++) {
    Write-Host ("  {0}) {1}" -f ($i + 1), $Options[$i])
  }
  while ($true) {
    $choice = Read-Host "Select one"
    $number = 0
    if ([int]::TryParse($choice, [ref]$number) -and $number -ge 1 -and $number -le $Options.Count) {
      return $Options[$number - 1]
    }
    Write-Host "Invalid choice."
  }
}

function Validate-SourceRoot {
  param([string]$Path)
  if (-not (Test-Path -LiteralPath $Path -PathType Container)) {
    Write-Error @"
Kuno Onboard skill was not found.

Expected:
  $Path

This installer requires -SourceRoot to point directly to the
kuno-workflow-onboard-skills directory.
"@
    exit 1
  }

  $resolved = (Resolve-Path -LiteralPath $Path).Path
  $required = @(
    "SKILL.md",
    "REFERENCE.md",
    "scripts/onboard.py",
    "templates/agents/AGENTS.global.md",
    "templates/agents/AGENTS.project.md",
    "templates/skills"
  )
  $missing = @()
  foreach ($item in $required) {
    if (-not (Test-Path -LiteralPath (Join-Path $resolved $item))) {
      $missing += $item
    }
  }
  if ($missing.Count -gt 0) {
    Write-Error @"
Kuno Onboard skill was not found or is incomplete.

Provided:
  $resolved

Missing:
  $($missing -join "`n  ")

Please pass a valid kuno-workflow-onboard-skills directory.
"@
    exit 1
  }
  $script:SourceRoot = $resolved
}

function Find-Python {
  $python = Get-Command python -ErrorAction SilentlyContinue
  if ($python) {
    $script:PythonExe = $python.Source
    $script:PythonPrefix = @()
    return
  }
  $py = Get-Command py -ErrorAction SilentlyContinue
  if ($py) {
    $script:PythonExe = $py.Source
    $script:PythonPrefix = @("-3")
    return
  }
  Stop-WithMessage "python or py is required to run $SourceRoot\scripts\onboard.py"
}

function Invoke-External {
  param(
    [string]$FilePath,
    [string[]]$Arguments
  )
  $line = @($FilePath) + $Arguments
  Write-Host ("+ " + ($line -join " "))
  if ($DryRun) { return }
  & $FilePath @Arguments
  if ($LASTEXITCODE -ne 0) {
    throw "Command failed with exit code $LASTEXITCODE`: $($line -join ' ')"
  }
}

function Get-OnboardPy {
  return (Join-Path $SourceRoot "scripts/onboard.py")
}

function Get-CommonArgs {
  $args = @()
  if ($ProjectRoot) { $args += @("--project-root", $ProjectRoot) }
  if ($SkipProjectAgents) { $args += "--skip-project-agents" }
  if ($SkillsScope) { $args += @("--skills-scope", $SkillsScope) }
  if ($GlobalAgentsPath) { $args += @("--global-agents-path", $GlobalAgentsPath) }
  if ($GlobalSkillsDir) { $args += @("--global-skills-dir", $GlobalSkillsDir) }
  if ($ProjectSkillsDir) { $args += @("--project-skills-dir", $ProjectSkillsDir) }
  if ($TrellisUser) { $args += @("--trellis-user", $TrellisUser) }
  foreach ($platformName in $TrellisPlatform) {
    if ($platformName) { $args += @("--trellis-platform", $platformName) }
  }
  if ($SkipTrellisInit) { $args += "--skip-trellis-init" }
  if ($SkipTrellisBootstrap) { $args += "--skip-trellis-bootstrap" }
  return $args
}

function Invoke-Onboard {
  param(
    [string]$Mode,
    [string[]]$Extra = @()
  )
  $arguments = $PythonPrefix + @((Get-OnboardPy), $Mode) + $Extra
  if ($Mode -eq "check" -or $Mode -eq "plan") {
    Write-Host ("+ " + (@($PythonExe) + $arguments -join " "))
    & $PythonExe @arguments
    if ($LASTEXITCODE -ne 0) {
      throw "Command failed with exit code $LASTEXITCODE`: $($arguments -join ' ')"
    }
  }
  else {
    Invoke-External $PythonExe $arguments
  }
}

function Update-Check {
  $script:CheckJsonPath = [System.IO.Path]::GetTempFileName()
  $arguments = $PythonPrefix + @((Get-OnboardPy), "check") + (Get-CommonArgs) + @("--json")
  if ($DryRun) {
    Write-Host ("+ " + (@($PythonExe) + $arguments -join " "))
  }
  & $PythonExe @arguments | Set-Content -LiteralPath $CheckJsonPath -Encoding UTF8
  $script:Check = Get-Content -LiteralPath $CheckJsonPath -Raw | ConvertFrom-Json
}

function Show-Check {
  Invoke-Onboard "check" (Get-CommonArgs)
}

function Tool-ByName {
  param([string]$Name)
  return @($script:Check.tools | Where-Object { $_.name -eq $Name } | Select-Object -First 1)[0]
}

function Skill-ByName {
  param([string]$Name)
  return @($script:Check.skills | Where-Object { $_.name -eq $Name } | Select-Object -First 1)[0]
}

function Runtime-Installed {
  param([string]$Name)
  $item = $script:Check.runtime.$Name
  return [bool]$item.installed
}

function Tool-Installed {
  param([string]$Name)
  $item = Tool-ByName $Name
  return [bool]($item -and $item.installed)
}

function Skill-Installed {
  param([string]$Name)
  $item = Skill-ByName $Name
  return [bool]($item -and $item.installed)
}

function Resolve-ProjectRoot {
  param([string]$Path)
  if ([string]::IsNullOrWhiteSpace($Path)) { return "" }
  if (-not (Test-Path -LiteralPath $Path -PathType Container)) {
    Stop-WithMessage "Project root does not exist: $Path"
  }
  return (Resolve-Path -LiteralPath $Path).Path
}

function Resolve-InteractiveInputs {
  if ($Platform) {
    $script:Platform = Normalize-Platform $Platform
  }
  else {
    $selected = Select-One "Target coding agent tool:" @("Codex", "Claude Code", "Kimi Code", "Oh My Pi")
    switch ($selected) {
      "Codex" { $script:Platform = "codex" }
      "Claude Code" { $script:Platform = "claude" }
      "Kimi Code" { $script:Platform = "kimi" }
      "Oh My Pi" { $script:Platform = "oh-my-pi" }
    }
  }

  if (-not $Action) {
    $script:Action = Select-One "Onboard action:" @("init", "reset")
  }

  if ($ProjectRoot) {
    $script:ProjectRoot = Resolve-ProjectRoot $ProjectRoot
  }
  else {
    $cwd = (Get-Location).Path
    if (Prompt-YesNo "Is $cwd the target project root?" "y") {
      $script:ProjectRoot = $cwd
    }
    else {
      $provided = Prompt-Text "Enter target project root, or leave blank to skip project AGENTS"
      if ($provided) {
        $script:ProjectRoot = Resolve-ProjectRoot $provided
      }
      else {
        $script:SkipProjectAgents = $true
      }
    }
  }

  if ($ProjectRoot -and -not $SkipProjectAgents) {
    if (-not (Prompt-YesNo "Install project AGENTS.md into $ProjectRoot?" "y")) {
      $script:SkipProjectAgents = $true
    }
  }
  if (-not $ProjectRoot) {
    $script:SkipProjectAgents = $true
  }

  if (-not $SkillsScope) {
    $script:SkillsScope = Select-One "Bundled skills install scope:" @("global", "project", "none")
  }
  if ($SkillsScope -eq "project" -and -not $ProjectRoot -and -not $ProjectSkillsDir) {
    $path = Prompt-Text "Project root is required for project skills. Enter project root"
    if (-not $path) { Stop-WithMessage "Project skills require -ProjectRoot or -ProjectSkillsDir" }
    $script:ProjectRoot = Resolve-ProjectRoot $path
  }
}

function Install-MissingRuntimeAndSkills {
  Write-Host ""
  Write-Colored "Preflight check" Cyan
  Show-Check
  Update-Check

  if (-not (Runtime-Installed "npm")) {
    if (Prompt-YesNo "npm is missing. Install nvm + Node.js LTS now?" "n") {
      Invoke-Onboard "ensure-npm" @("--yes")
      Update-Check
    }
    else {
      Write-Warn "npm install skipped. npm-backed CLI checks may remain not-checked."
    }
  }

  if (-not (Tool-Installed "rtk")) {
    $rtk = Tool-ByName "rtk"
    if ($rtk -and $rtk.wrongPackageSuspected) {
      if (Prompt-YesNo "rtk exists but may be the wrong package. Replace with rtk-ai/rtk?" "n") {
        Invoke-Onboard "install-rtk" @("--replace-wrong", "--yes")
      }
    }
    elseif ($rtk -and $rtk.verificationFailed) {
      if (Prompt-YesNo "rtk verification failed. Reinstall rtk-ai/rtk?" "n") {
        Invoke-Onboard "install-rtk" @("--reinstall", "--yes")
      }
    }
    elseif (Prompt-YesNo "rtk is missing. Install rtk-ai/rtk?" "n") {
      Invoke-Onboard "install-rtk" @("--yes")
    }
    Update-Check
  }

  if (-not (Tool-Installed "trellis") -and (Runtime-Installed "npm")) {
    if (Prompt-YesNo "Trellis CLI is missing. Install @mindfoldhq/trellis globally?" "n") {
      Invoke-External "npm" @("install", "-g", "@mindfoldhq/trellis@latest")
      Update-Check
    }
  }

  if (-not (Tool-Installed "gitnexus") -and (Runtime-Installed "npm")) {
    if (Prompt-YesNo "GitNexus CLI is missing. Install gitnexus globally?" "n") {
      Invoke-External "npm" @("install", "-g", "gitnexus")
      Update-Check
    }
  }

  if (-not (Skill-Installed "caveman")) {
    if (Prompt-YesNo "caveman skill is missing. Install it as a user-level global skill?" "n") {
      Invoke-Onboard "install-caveman" @("--yes")
      Update-Check
    }
  }

  $missingExternal = @($script:Check.skills | Where-Object {
    ($ExternalSkills -contains $_.name) -and (-not $_.installed)
  } | ForEach-Object { $_.name })
  if ($missingExternal.Count -gt 0) {
    Write-Host ""
    Write-Host ("Missing external skills: " + ($missingExternal -join ","))
    if ($SkillsScope -eq "none") {
      Write-Warn "Bundled skills scope is none, so external skill installation is skipped."
      return
    }
    $decision = Select-One "External skills install decision:" @("install recommended missing skills", "custom select skills", "skip external skills")
    $selected = ""
    if ($decision -eq "install recommended missing skills") {
      $selected = $missingExternal -join ","
    }
    elseif ($decision -eq "custom select skills") {
      Write-Host ("Known missing external skills: " + ($missingExternal -join ","))
      $selected = Prompt-Text "Enter comma-separated skill names to install"
    }
    if ($selected) {
      $args = @("--skills", $selected, "--scope", $SkillsScope, "--yes")
      if ($SkillsScope -eq "project") {
        if ($ProjectRoot) { $args += @("--project-root", $ProjectRoot) }
        if ($ProjectSkillsDir) { $args += @("--project-skills-dir", $ProjectSkillsDir) }
      }
      else {
        if ($GlobalSkillsDir) { $args += @("--global-skills-dir", $GlobalSkillsDir) }
      }
      Invoke-Onboard "install-external-skills" $args
      Update-Check
    }
  }
}

function Split-TrellisPlatforms {
  param([string]$Value)
  if ([string]::IsNullOrWhiteSpace($Value)) { return @() }
  return @($Value -replace "\s", "" -split "," | Where-Object { $_ } | ForEach-Object { $_.TrimStart("-") })
}

function Resolve-TrellisProjectSetupInputs {
  if ($SkipTrellisInit) { return }
  if (-not $ProjectRoot) { return }
  if (Test-Path -LiteralPath (Join-Path $ProjectRoot ".trellis")) { return }

  Update-Check
  if (-not (Tool-Installed "trellis")) {
    Write-Warn "Trellis CLI is required before project trellis init; onboard.py will report the setup as blocked."
    return
  }

  while ([string]::IsNullOrWhiteSpace($script:TrellisUser)) {
    $script:TrellisUser = Prompt-Text "Trellis developer username for trellis init -u"
    if ([string]::IsNullOrWhiteSpace($script:TrellisUser)) {
      if (Prompt-YesNo "Skip trellis init for this project?" "n") {
        $script:SkipTrellisInit = $true
        return
      }
    }
  }

  if ($script:TrellisPlatform.Count -eq 0) {
    $rawPlatforms = Prompt-Text "Trellis platform flags, comma-separated without --, or blank for none"
    $script:TrellisPlatform = @(Split-TrellisPlatforms $rawPlatforms)
  }
}

function Prompt-EnvPairs {
  $pairs = @{}
  while ($true) {
    $key = Prompt-Text "Env key for this MCP server, or blank to finish"
    if (-not $key) { break }
    if ($key -match "TOKEN|PASSWORD|SECRET|KEY") {
      $secure = Read-Host "Value for $key" -AsSecureString
      $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
      try {
        $value = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
      }
      finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
      }
    }
    else {
      $value = Prompt-Text "Value for $key"
    }
    $pairs[$key] = $value
  }
  return $pairs
}

function Ensure-MaestroReady {
  Update-Check
  if (-not (Tool-Installed "java")) {
    Write-Warn "Maestro MCP requires Java 17+. Native Windows auto-install is not enabled by this installer."
    Write-Warn "Install Java 17+ manually, then rerun this script."
    return $false
  }

  if (-not (Tool-Installed "maestro")) {
    Write-Warn "Maestro CLI is missing or not verified. Native Windows Maestro install is manual-required."
    Write-Warn "Install Maestro CLI or use WSL, then rerun this script."
    return $false
  }
  return $true
}

function Get-MaestroEnv {
  $config = Get-ManualMcpConfig "Maestro MCP"
  if ($config -and $config.env) {
    return $config.env
  }
  return @{}
}

function Get-ManualMcpConfig {
  param([string]$Name)
  foreach ($item in $script:Check.manualChecks) {
    if ($item.name -eq $Name -and $item.PSObject.Properties["mcpServerConfig"]) {
      return $item.mcpServerConfig
    }
  }
  return $null
}

function Convert-EnvObjectToHash {
  param($EnvObject)
  $envHash = @{}
  if ($null -eq $EnvObject) {
    return $envHash
  }
  foreach ($property in $EnvObject.PSObject.Properties) {
    $envHash[$property.Name] = [string]$property.Value
  }
  return $envHash
}

function Configure-StdioMcp {
  param(
    [string]$Name,
    [string]$Command,
    [string[]]$Args,
    [hashtable]$ServerEnv = @{}
  )

  switch ($Platform) {
    "codex" {
      if (-not (Get-Command codex -ErrorAction SilentlyContinue)) {
        Write-Warn "codex CLI not found; skipped MCP server $Name."
        return
      }
      $cmdArgs = @("mcp", "add", $Name)
      foreach ($key in $ServerEnv.Keys) {
        $cmdArgs += @("--env", "$key=$($ServerEnv[$key])")
      }
      $cmdArgs += @("--", $Command) + $Args
      Invoke-External "codex" $cmdArgs
    }
    "claude" {
      if (-not (Get-Command claude -ErrorAction SilentlyContinue)) {
        Write-Warn "claude CLI not found; skipped MCP server $Name."
        return
      }
      $scope = if ($SkillsScope -eq "project") { "project" } else { "user" }
      $cmdArgs = @("mcp", "add", "--transport", "stdio", "--scope", $scope)
      foreach ($key in $ServerEnv.Keys) {
        $cmdArgs += @("--env", "$key=$($ServerEnv[$key])")
      }
      $cmdArgs += @($Name, "--", $Command) + $Args
      Invoke-External "claude" $cmdArgs
    }
    "kimi" {
      if (-not (Get-Command kimi -ErrorAction SilentlyContinue)) {
        Write-Warn "kimi CLI not found; skipped MCP server $Name."
        return
      }
      $cmdArgs = @("mcp", "add", "--transport", "stdio")
      foreach ($key in $ServerEnv.Keys) {
        $cmdArgs += @("--env", "$key=$($ServerEnv[$key])")
      }
      $cmdArgs += @($Name, "--", $Command) + $Args
      Invoke-External "kimi" $cmdArgs
    }
    "oh-my-pi" {
      Configure-OmpStdio $Name $Command $Args $ServerEnv
    }
  }
}

function Configure-OmpStdio {
  param(
    [string]$Name,
    [string]$Command,
    [string[]]$Args,
    [hashtable]$ServerEnv = @{}
  )
  if ($SkillsScope -eq "project") {
    if (-not $ProjectRoot) {
      Write-Warn "Project root is required for project-level Oh My Pi MCP config."
      return
    }
    $target = Join-Path $ProjectRoot ".omp/mcp.json"
  }
  else {
    $target = Join-Path $HOME ".omp/agent/mcp.json"
  }

  if ($DryRun) {
    Write-Host "+ write Oh My Pi MCP server $Name to $target"
    return
  }

  if (Test-Path -LiteralPath $target) {
    $config = Get-Content -LiteralPath $target -Raw | ConvertFrom-Json
  }
  else {
    $config = [pscustomobject]@{}
  }
  if (-not $config.PSObject.Properties["mcpServers"]) {
    $config | Add-Member -MemberType NoteProperty -Name "mcpServers" -Value ([pscustomobject]@{})
  }
  $server = [ordered]@{
    type = "stdio"
    command = $Command
    args = $Args
    env = $ServerEnv
  }
  $config.mcpServers | Add-Member -MemberType NoteProperty -Name $Name -Value $server -Force
  New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target) | Out-Null
  $config | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $target -Encoding UTF8
  Write-Host "wrote $Name MCP server to $target"
}

function Select-AndConfigureMcp {
  if ($NoMcp) {
    Write-Host ""
    Write-Host "MCP configuration skipped by -NoMcp."
    return
  }
  if (-not (Prompt-YesNo "Configure MCP servers for $(Platform-Label $Platform) now?" "y")) {
    Write-Host "MCP configuration skipped by user."
    return
  }

  Write-Host ""
  Write-Host "Available MCP options:"
  Write-Host "  1) Chrome DevTools MCP"
  Write-Host "  2) Playwright MCP"
  Write-Host "  3) Maestro MCP"
  Write-Host "  4) GitNexus MCP (auto from gitnexus CLI)"
  Write-Host "  5) Custom stdio MCP server"
  $raw = Read-Host "Select comma-separated options, or blank for none"
  if (-not $raw) { return }
  $items = $raw -replace "\s", "" -split ","
  foreach ($item in $items) {
    switch ($item) {
      "1" {
        Configure-StdioMcp "chrome-devtools" "npx" @("-y", "chrome-devtools-mcp@latest") @{}
      }
      "2" {
        Configure-StdioMcp "playwright" "npx" @("-y", "@playwright/mcp@latest") @{}
      }
      "3" {
        if (Ensure-MaestroReady) {
          $envObject = Get-MaestroEnv
          $envHash = Convert-EnvObjectToHash $envObject
          Configure-StdioMcp "maestro" "maestro" @("mcp") $envHash
        }
      }
      "4" {
        $config = Get-ManualMcpConfig "GitNexus MCP"
        if ($config -and $config.command) {
          $serverArgs = @()
          if ($config.args) {
            foreach ($arg in $config.args) {
              $serverArgs += [string]$arg
            }
          }
          $envHash = Convert-EnvObjectToHash $config.env
          Configure-StdioMcp "gitnexus" ([string]$config.command) $serverArgs $envHash
        }
        else {
          Write-Warn "GitNexus CLI path was not detected; falling back to manual MCP command input."
          $command = Prompt-Text "GitNexus MCP command, or blank to skip"
          if (-not $command) {
            Write-Warn "Skipped GitNexus MCP: command is required."
            continue
          }
          $argsLine = Prompt-Text "GitNexus MCP args as a simple space-separated list"
          $serverArgs = if ($argsLine) { $argsLine -split "\s+" } else { @() }
          $envHash = Prompt-EnvPairs
          Configure-StdioMcp "gitnexus" $command $serverArgs $envHash
        }
      }
      "5" {
        $name = Prompt-Text "MCP server name"
        $command = Prompt-Text "MCP command"
        if (-not $name -or -not $command) {
          Write-Warn "Skipped custom MCP: name and command are required."
          continue
        }
        $argsLine = Prompt-Text "MCP args as a simple space-separated list"
        $serverArgs = if ($argsLine) { $argsLine -split "\s+" } else { @() }
        $envHash = Prompt-EnvPairs
        Configure-StdioMcp $name $command $serverArgs $envHash
      }
      default {
        Write-Warn "Invalid MCP selection ignored: $item"
      }
    }
  }
}

function Show-PlanAndExecute {
  $common = Get-CommonArgs
  Write-Host ""
  Write-Colored "Final plan" Cyan
  Invoke-Onboard "plan" $common

  Write-Host ""
  Write-Host ("Target platform: " + (Platform-Label $Platform))
  Write-Host "Source root: $SourceRoot"
  Write-Host "Action: $Action"
  Write-Host ("Project root: " + ($(if ($ProjectRoot) { $ProjectRoot } else { "<none>" })))
  Write-Host ("Project AGENTS: " + ($(if ($SkipProjectAgents) { "skip" } else { "install" })))
  Write-Host "Skills scope: $SkillsScope"
  Write-Host ("MCP: " + ($(if ($NoMcp) { "skip" } else { "configure interactively" })))

  if (-not $Yes) {
    if (-not (Prompt-YesNo "Proceed with onboard $Action?" "n")) {
      Stop-WithMessage "Installation cancelled."
    }
  }

  if ($DryRun) {
    Write-Host ""
    Write-Host "Dry run: skipped onboard $Action writes."
  }
  else {
    Invoke-Onboard $Action ($common + @("--yes"))
  }
}

function Final-Checks {
  Write-Host ""
  Write-Colored "Final check" Cyan
  Invoke-Onboard "check" (Get-CommonArgs)

  switch ($Platform) {
    "codex" {
      if (Get-Command codex -ErrorAction SilentlyContinue) {
        Invoke-External "codex" @("mcp", "list")
      }
      else { Write-Warn "codex CLI not found; MCP list skipped." }
    }
    "claude" {
      if (Get-Command claude -ErrorAction SilentlyContinue) {
        Invoke-External "claude" @("mcp", "list")
      }
      else { Write-Warn "claude CLI not found; MCP list skipped." }
    }
    "kimi" {
      if (Get-Command kimi -ErrorAction SilentlyContinue) {
        Invoke-External "kimi" @("mcp", "list")
      }
      else { Write-Warn "kimi CLI not found; MCP list skipped." }
    }
    "oh-my-pi" {
      if ($SkillsScope -eq "project" -and $ProjectRoot) {
        Write-Host "Oh My Pi MCP config: $(Join-Path $ProjectRoot '.omp/mcp.json')"
      }
      else {
        Write-Host "Oh My Pi MCP config: $(Join-Path $HOME '.omp/agent/mcp.json')"
      }
    }
  }
}

if ($Help) {
  Show-Usage
  exit 0
}

Validate-SourceRoot $SourceRoot
Find-Python
Show-Logo
Resolve-InteractiveInputs
Install-MissingRuntimeAndSkills
Select-AndConfigureMcp
Resolve-TrellisProjectSetupInputs
Show-PlanAndExecute
Final-Checks

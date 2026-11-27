<#
.SYNOPSIS
  gate <card> [-As <ROLE>] [-Hosts ps5,ps7]  - secret scan of every zone file (file + line + rule only, never the value)
  + every *.Tests.ps1 in the zones on each host it needs -> <cards>/<card>/receipts/gate.json
  {manifest_digest, tests, result, at} (+ secrets, skipped, by). Exit 0 only on PASS.
  Hosts per test file: config gate.hosts (default ps5 + ps7); ps7 only for a test under config paths.scripts whose first lines hold '#Requires -Version 7'
  (the bundle's own scripts are PowerShell 7 only). gate itself runs on PowerShell 7 only.
.EXAMPLE
  .\gate.ps1 001-demo-hello -As BUILD
#>
[CmdletBinding()]
param(
    [Parameter(Position = 0)][string]$Card,
    [string]$As = '',
    [ValidateSet('ps5', 'ps7', 'current')][string[]]$Hosts = @(),   # empty -> config gate.hosts (default ps5, ps7)
    [string]$Root = ''
)
if ($PSVersionTable.PSVersion.Major -lt 7) { [Console]::Out.WriteLine('REFUSED: gate.ps1 needs PowerShell 7 (pwsh); this is Windows PowerShell ' + $PSVersionTable.PSVersion + '.'); exit 1 }
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'CardFlow.psm1') -Force -DisableNameChecking
Invoke-CfMain { Invoke-CfGate -Root (Resolve-CfRoot $Root $PSScriptRoot) -Card $Card -As $As -Hosts $Hosts }
exit (Get-CfExitCode)

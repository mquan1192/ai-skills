<#
.SYNOPSIS
  release <card> -IfSafe -As LEAD [-DryRun]  - LEAD only. There is no release without -IfSafe and no switch that skips
  a check (Q3). Checks: REVIEW ticket DONE with PASS / FIX-VERIFIED (old FIXES_VERIFIED read) at the current manifest digest, gate receipt PASS at
  that digest, no other open ticket, live target unchanged since baseline.manifest, every changed protected path in
  protected_paths with the owner's quoted sentence in Decisions. Then: closes the last ticket, card -> RELEASED (+ State log; old MERGED read),
  log.md line, prints the install request for DOCS for shared-path installs. Copies nothing anywhere.
  Limit: -As LEAD is logged, not proven - without worktrees a script cannot prove which session calls it.
.EXAMPLE
  .\release.ps1 001-demo-hello -IfSafe -As LEAD -DryRun
#>
[CmdletBinding()]
param(
    [Parameter(Position = 0)][string]$Card,
    [switch]$IfSafe, [switch]$DryRun, [string]$As = '',
    [string]$Root = ''
)
if ($PSVersionTable.PSVersion.Major -lt 7) { [Console]::Out.WriteLine('REFUSED: release.ps1 needs PowerShell 7 (pwsh); this is Windows PowerShell ' + $PSVersionTable.PSVersion + '.'); exit 1 }
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'CardFlow.psm1') -Force -DisableNameChecking
Invoke-CfMain { Invoke-CfRelease -Root (Resolve-CfRoot $Root $PSScriptRoot) -Card $Card -As $As -IfSafe:$IfSafe -DryRun:$DryRun }
exit (Get-CfExitCode)

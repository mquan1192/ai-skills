<#
.SYNOPSIS
  checkpoint <card> -As <ROLE> -Done <t> -Doing <t> -Next <t> -Check <t>  - appends ONE line to <cards>/<card>/log.md.
  Refused when -As is not the turn holder of the open ticket; with no open ticket only LEAD may write (Q2).
.EXAMPLE
  .\checkpoint.ps1 001-demo-hello -As BUILD -Done 'ticket.ps1 + tests' -Doing 'gate.ps1' -Next 'release.ps1' -Check 'ticket tests green'
#>
[CmdletBinding()]
param(
    [Parameter(Position = 0)][string]$Card,
    [string]$As, [string]$Done, [string]$Doing, [string]$Next, [string]$Check,
    [string]$Root = ''
)
if ($PSVersionTable.PSVersion.Major -lt 7) { [Console]::Out.WriteLine('REFUSED: checkpoint.ps1 needs PowerShell 7 (pwsh); this is Windows PowerShell ' + $PSVersionTable.PSVersion + '.'); exit 1 }
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'CardFlow.psm1') -Force -DisableNameChecking
Invoke-CfMain { Invoke-CfCheckpoint -Root (Resolve-CfRoot $Root $PSScriptRoot) -Card $Card -As $As -Done $Done -Doing $Doing -Next $Next -Check $Check }
exit (Get-CfExitCode)

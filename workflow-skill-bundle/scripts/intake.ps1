<#
.SYNOPSIS
  intake <card>  - read-only (LEAD): open ticket, manifest digest vs the last frozen ticket, gate state, changed protected
  paths, the release -IfSafe dry-run reasons (same check as release) and one suggested next step. Writes nothing.
.EXAMPLE
  .\intake.ps1 001-demo-hello
#>
[CmdletBinding()]
param(
    [Parameter(Position = 0)][string]$Card,
    [string]$Root = ''
)
if ($PSVersionTable.PSVersion.Major -lt 7) { [Console]::Out.WriteLine('REFUSED: intake.ps1 needs PowerShell 7 (pwsh); this is Windows PowerShell ' + $PSVersionTable.PSVersion + '.'); exit 1 }
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'CardFlow.psm1') -Force -DisableNameChecking
Invoke-CfMain { Invoke-CfIntake -Root (Resolve-CfRoot $Root $PSScriptRoot) -Card $Card }
exit (Get-CfExitCode)

<#
.SYNOPSIS
  manifest <card>                       - prints the manifest (added / changed / removed vs baseline.manifest, target paths,
                                          "<sha256>  <path>", removed = "-") and its digest (AGENTS.md "Versioning without git").
  manifest <card> -Baseline -As BUILD   - BUILD start: writes <cards>/<card>/baseline.manifest from the live target folders.
                                          Write-once (Q4): refused when it exists.
  Zone <YYYY-MM>/<DD_NN-task>/out/<target> maps to the live target <target>. A missing baseline is never treated as empty.
.EXAMPLE
  .\manifest.ps1 001-demo-hello -Baseline -As BUILD
  .\manifest.ps1 001-demo-hello
#>
[CmdletBinding()]
param(
    [Parameter(Position = 0)][string]$Card,
    [switch]$Baseline, [string]$As = '',
    [string]$Root = ''
)
if ($PSVersionTable.PSVersion.Major -lt 7) { [Console]::Out.WriteLine('REFUSED: manifest.ps1 needs PowerShell 7 (pwsh); this is Windows PowerShell ' + $PSVersionTable.PSVersion + '.'); exit 1 }
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'CardFlow.psm1') -Force -DisableNameChecking
Invoke-CfMain { Invoke-CfManifest -Root (Resolve-CfRoot $Root $PSScriptRoot) -Card $Card -Baseline:$Baseline -As $As }
exit (Get-CfExitCode)

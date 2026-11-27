<#
.SYNOPSIS
  board  - regenerates <process_docs>/PROGRESS.md from <cards>/*/ (cards, tickets, gate receipts, log.md).
  Errors are warnings only: exit code is always 0. ticket / checkpoint / release refresh the board the same way.
.EXAMPLE
  .\board.ps1
#>
[CmdletBinding()]
param([string]$Root = '')
if ($PSVersionTable.PSVersion.Major -lt 7) { [Console]::Out.WriteLine('REFUSED: board.ps1 needs PowerShell 7 (pwsh); this is Windows PowerShell ' + $PSVersionTable.PSVersion + '.'); exit 1 }
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'CardFlow.psm1') -Force -DisableNameChecking
Invoke-CfMain {
    try { Invoke-CfBoard -Root (Resolve-CfRoot $Root $PSScriptRoot) }
    catch { Write-Warning "board: $($_.Exception.Message) (warning only)" }
}
exit 0

<#
.SYNOPSIS
  ticket send|accept|done|hold|takeover <card> -As <ROLE> ...  - writes <cards>/<card>/handoff/H-NN.json, re-reads it,
  prints the 4-line bell on send (<cards>/README.md). One open ticket per card; only the receiver changes a ticket.
  A send to REVIEW (or -Freeze) freezes the manifest: manifest_digest + manifest lines go into the ticket.
  REVIEW closes with -Note PASS | FAIL | FIX-VERIFIED and only at the frozen digest (else OUTDATED, no verdict).
  Old names (phases P1 / GATE / FIXES / VERIFY, states HOLD / TAKEOVER, NG, FIXES_VERIFIED, STALE) are read; new ones written.
  PowerShell 7 only.
.EXAMPLE
  .\ticket.ps1 send 001-demo-hello -As BUILD -To REVIEW -Phase REVIEW -Session Dev -Agent 'model' -Note 'BUILD done'
  .\ticket.ps1 accept 001-demo-hello -As REVIEW
  .\ticket.ps1 done 001-demo-hello -As REVIEW -Note 'PASS no findings'
#>
[CmdletBinding()]
param(
    [Parameter(Position = 0)][string]$Action,
    [Parameter(Position = 1)][string]$Card,
    [string]$As, [string]$To, [string]$Phase, [string]$Note = '', [string]$Agent = '', [string]$Session = '',
    [switch]$Freeze,
    [string]$Root = '',
    [Parameter(DontShow)][string]$SessionMap = ''   # test only; default config session_map_file
)
if ($PSVersionTable.PSVersion.Major -lt 7) { [Console]::Out.WriteLine('REFUSED: ticket.ps1 needs PowerShell 7 (pwsh); this is Windows PowerShell ' + $PSVersionTable.PSVersion + '.'); exit 1 }
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'CardFlow.psm1') -Force -DisableNameChecking
Invoke-CfMain { Invoke-CfTicket -Root (Resolve-CfRoot $Root $PSScriptRoot) -Action $Action -Card $Card -As $As -To $To -Phase $Phase -Note $Note -Agent $Agent -Session $Session -Freeze:$Freeze -SessionMap $SessionMap }
exit (Get-CfExitCode)

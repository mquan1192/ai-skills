<#
.SYNOPSIS
  stale  - lists open tickets that wait too long: SENT > 30 min; ACCEPTED / TAKEN-OVER (old TAKEOVER read) with no file change in the card zones
  for > 3 h. Skips RELEASED / CANCELLED cards (old MERGED / CLOSED read). Output word STALE = waiting too long. Local clock (history[].at has no time zone). Output on this machine only.
.EXAMPLE
  .\stale.ps1
#>
[CmdletBinding()]
param(
    [string]$Root = '',
    [Parameter(DontShow)][string]$Now = ''   # test only (read-only command): 'yyyy-MM-ddTHH:mm'
)
if ($PSVersionTable.PSVersion.Major -lt 7) { [Console]::Out.WriteLine('REFUSED: stale.ps1 needs PowerShell 7 (pwsh); this is Windows PowerShell ' + $PSVersionTable.PSVersion + '.'); exit 1 }
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'CardFlow.psm1') -Force -DisableNameChecking
Invoke-CfMain {
    $t = Get-Date
    if ($Now) { $t = [datetime]::ParseExact($Now, 'yyyy-MM-ddTHH:mm', [Globalization.CultureInfo]::InvariantCulture) }
    Invoke-CfStale -Root (Resolve-CfRoot $Root $PSScriptRoot) -Now $t
}
exit (Get-CfExitCode)

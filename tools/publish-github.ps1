#requires -Version 7.0
<#
.SYNOPSIS
Publishes the reviewed main commit to maro-comu/NCS_Maro and configures /docs Pages.
.DESCRIPTION
Setup pushes the existing clean main commit without force, creates Pages only if
absent, and requests a build when no current build exists. Status makes read-only
API requests. GitHub credentials are retrieved from Git's credential helper into
memory and are never printed, written to disk, or placed in a process argument.
.EXAMPLE
./tools/publish-github.ps1 -Mode Setup
.EXAMPLE
./tools/publish-github.ps1 -Mode Status
#>
[CmdletBinding()]
param(
    [ValidateSet('Setup', 'Status')]
    [string]$Mode = 'Status'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$VerbosePreference = 'SilentlyContinue'
$DebugPreference = 'SilentlyContinue'
$PSNativeCommandUseErrorActionPreference = $false
$repositoryRoot = Split-Path -Parent $PSScriptRoot
$apiRepository = '/repos/maro-comu/NCS_Maro'
$expectedRemote = 'https://github.com/maro-comu/NCS_Maro.git'
$expectedSite = 'https://maro-comu.github.io/NCS_Maro/'
$originalPrompt = [Environment]::GetEnvironmentVariable('GIT_TERMINAL_PROMPT', 'Process')
$originalInteractive = [Environment]::GetEnvironmentVariable('GCM_INTERACTIVE', 'Process')
$credentialParts = @{}
$apiHeaders = @{}
$credentialLines = $null
$token = $null
$pushOutput = $null

function Invoke-GitHubRequest {
    param(
        [ValidateSet('Get', 'Post')][string]$Method,
        [ValidatePattern('^/[A-Za-z0-9_./-]+$')][string]$ApiPath,
        [hashtable]$Body,
        [int[]]$AllowedStatus = @(200)
    )
    $request = @{
        Uri = 'https://api.github.com' + $ApiPath
        Method = $Method
        Headers = $apiHeaders
        SkipHttpErrorCheck = $true
        MaximumRedirection = 0
        TimeoutSec = 30
        ErrorAction = 'Stop'
    }
    if ($null -ne $Body) {
        $request.Body = $Body | ConvertTo-Json -Depth 5 -Compress
        $request.ContentType = 'application/json'
    }
    try {
        $response = Invoke-WebRequest @request
    } catch {
        throw "GitHub API request failed for $ApiPath (network or transport error)."
    }
    $statusCode = [int]$response.StatusCode
    if ($statusCode -notin $AllowedStatus) {
        throw "GitHub API request failed for $ApiPath (HTTP $statusCode)."
    }
    $data = @{}
    if (-not [string]::IsNullOrWhiteSpace($response.Content)) {
        try {
            $data = $response.Content | ConvertFrom-Json -AsHashtable
        } catch {
            throw "GitHub API returned invalid JSON for $ApiPath (HTTP $statusCode)."
        }
    }
    return @{ StatusCode = $statusCode; Data = $data }
}

try {
    $env:GIT_TERMINAL_PROMPT = '0'
    $env:GCM_INTERACTIVE = 'Never'
    $gitCommand = Get-Command git -ErrorAction SilentlyContinue
    if ($null -eq $gitCommand) { throw 'git must be available on PATH.' }

    if ($Mode -eq 'Setup') {
        $branch = & git -C $repositoryRoot symbolic-ref --short HEAD 2>$null
        if ($LASTEXITCODE -ne 0 -or $branch -ne 'main') {
            throw 'Setup requires an existing local main branch and commit.'
        }
        $localCommit = & git -C $repositoryRoot rev-parse --verify HEAD 2>$null
        if ($LASTEXITCODE -ne 0 -or $localCommit -notmatch '^[a-f0-9]{40}$') {
            throw 'Setup requires a valid committed HEAD.'
        }
        foreach ($remoteArguments in @(@('get-url', '--all', 'origin'), @('get-url', '--push', '--all', 'origin'))) {
            $remoteUrls = @(& git -C $repositoryRoot remote @remoteArguments 2>$null)
            if ($LASTEXITCODE -ne 0 -or $remoteUrls.Count -ne 1 -or $remoteUrls[0] -notin @($expectedRemote, 'https://github.com/maro-comu/NCS_Maro')) {
                throw 'origin fetch and push URLs must both identify the expected HTTPS repository.'
            }
        }
        $dirty = & git -C $repositoryRoot status --porcelain 2>$null
        if ($LASTEXITCODE -ne 0 -or $dirty) {
            throw 'Commit the reviewed changes before Setup; the working tree must be clean.'
        }
        $null = & git -C $repositoryRoot cat-file -e 'HEAD:docs/index.html' 2>$null
        if ($LASTEXITCODE -ne 0) { throw 'The reviewed commit must contain docs/index.html.' }
    } else {
        $localCommit = $null
    }

    $credentialInput = "protocol=https`nhost=github.com`n`n"
    $credentialLines = $credentialInput | & git -C $repositoryRoot -c credential.interactive=never credential fill 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw 'No noninteractive GitHub credential is available from the Git credential helper.'
    }
    foreach ($line in $credentialLines) {
        if ($line -match '^([^=]+)=(.*)$') { $credentialParts[$matches[1]] = $matches[2] }
    }
    if (-not $credentialParts.ContainsKey('password') -or [string]::IsNullOrWhiteSpace($credentialParts['password'])) {
        throw 'The Git credential helper did not supply a GitHub credential.'
    }
    $token = $credentialParts['password']
    $apiHeaders = @{
        'User-Agent' = 'NCS-Maro-Publisher'
        'Accept' = 'application/vnd.github+json'
        'X-GitHub-Api-Version' = '2022-11-28'
        'Authorization' = 'Bearer ' + $token
    }
    $identity = Invoke-GitHubRequest -Method Get -ApiPath '/user'
    if ($identity.Data['login'] -ne 'maro-comu') {
        throw 'The stored credential must authenticate the repository owner maro-comu.'
    }
    $repository = Invoke-GitHubRequest -Method Get -ApiPath $apiRepository
    if ($repository.Data['full_name'] -ne 'maro-comu/NCS_Maro' -or -not $repository.Data['permissions']['admin']) {
        throw 'The authenticated owner must have administrator access to maro-comu/NCS_Maro.'
    }
    if ($repository.Data['default_branch'] -ne 'main') {
        throw 'The expected repository default branch is main.'
    }

    $pages = Invoke-GitHubRequest -Method Get -ApiPath "$apiRepository/pages" -AllowedStatus @(200, 404)
    if ($Mode -eq 'Setup' -and $pages.StatusCode -eq 200) {
        $source = $pages.Data['source']
        if ($null -eq $source -or $source['branch'] -ne 'main' -or $source['path'] -ne '/docs' -or $pages.Data['build_type'] -eq 'workflow') {
            throw 'Existing Pages settings use another source; inspect them before publishing.'
        }
    }

    $pushed = $false
    $pagesCreated = $false
    $buildRequested = $false
    if ($Mode -eq 'Setup') {
        $pushOutput = & git -C $repositoryRoot -c credential.interactive=never push origin main 2>&1
        if ($LASTEXITCODE -ne 0) { throw "Git push failed (exit code $LASTEXITCODE); no force push was attempted." }
        $pushed = $true
        if ($pages.StatusCode -eq 404) {
            $pages = Invoke-GitHubRequest -Method Post -ApiPath "$apiRepository/pages" -Body @{ build_type = 'legacy'; source = @{ branch = 'main'; path = '/docs' } } -AllowedStatus @(201)
            $pagesCreated = $true
        }
    }

    $latestBuild = $null
    if ($pages.StatusCode -in @(200, 201)) {
        $latestBuild = Invoke-GitHubRequest -Method Get -ApiPath "$apiRepository/pages/builds/latest" -AllowedStatus @(200, 404)
        if ($Mode -eq 'Setup') {
            $buildInProgress = $latestBuild.StatusCode -eq 200 -and $latestBuild.Data['status'] -in @('queued', 'building')
            $currentCommitBuilt = $latestBuild.StatusCode -eq 200 -and $latestBuild.Data['status'] -eq 'built' -and $latestBuild.Data['commit'] -eq $localCommit
            if (-not $buildInProgress -and -not $currentCommitBuilt) {
                $null = Invoke-GitHubRequest -Method Post -ApiPath "$apiRepository/pages/builds" -AllowedStatus @(201)
                $buildRequested = $true
                $latestBuild = Invoke-GitHubRequest -Method Get -ApiPath "$apiRepository/pages/builds/latest" -AllowedStatus @(200, 404)
            }
        }
        $pages = Invoke-GitHubRequest -Method Get -ApiPath "$apiRepository/pages" -AllowedStatus @(200)
    }

    $summary = [ordered]@{
        mode = $Mode
        repository = 'maro-comu/NCS_Maro'
        authenticatedOwner = 'maro-comu'
        adminAccess = $true
        pushed = $pushed
        localCommit = $localCommit
        pagesCreated = $pagesCreated
        buildRequested = $buildRequested
        pagesEnabled = $pages.StatusCode -eq 200
        url = if ($pages.StatusCode -eq 200 -and $pages.Data['html_url']) { $pages.Data['html_url'] } else { $expectedSite }
        pagesStatus = if ($pages.StatusCode -eq 200) { $pages.Data['status'] } else { 'not-configured' }
        latestBuildStatus = if ($null -ne $latestBuild -and $latestBuild.StatusCode -eq 200) { $latestBuild.Data['status'] } else { $null }
        latestBuildCommit = if ($null -ne $latestBuild -and $latestBuild.StatusCode -eq 200) { $latestBuild.Data['commit'] } else { $null }
    }
    $summary | ConvertTo-Json -Depth 4
} finally {
    if ($apiHeaders.ContainsKey('Authorization')) { $apiHeaders.Remove('Authorization') }
    $credentialParts.Clear()
    $credentialLines = $null
    $token = $null
    $line = $null
    $Matches = $null
    $pushOutput = $null
    [Environment]::SetEnvironmentVariable('GIT_TERMINAL_PROMPT', $originalPrompt, 'Process')
    [Environment]::SetEnvironmentVariable('GCM_INTERACTIVE', $originalInteractive, 'Process')
}

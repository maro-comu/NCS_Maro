param([int]$Port=8850)
$ErrorActionPreference='Stop'
$studyRoot=$PSScriptRoot
$studyUrl="http://127.0.0.1:$Port/private-study/web/"
if(-not(Test-Path -LiteralPath (Join-Path $studyRoot 'private-study\web\index.html'))){throw '개인 학습 자료가 아직 준비되지 않았습니다.'}
$studyPython=(Get-Command python -ErrorAction Stop).Source
try { $studyResponse=Invoke-WebRequest -Uri $studyUrl -UseBasicParsing -TimeoutSec 2 } catch { $studyResponse=$null }
if($studyResponse -and -not $studyResponse.Content.Contains('MARO')){throw '다른 앱이 이 포트를 사용하고 있습니다. -Port 값으로 다른 포트를 지정해 주세요.'}
if(-not $studyResponse){
  $studyArguments=@('-u','-m','http.server',"$Port",'--bind','127.0.0.1','--directory',('"'+$studyRoot+'"'))
  Start-Process -FilePath $studyPython -ArgumentList $studyArguments -WorkingDirectory $studyRoot -WindowStyle Hidden
  for($studyAttempt=0;$studyAttempt -lt 20;$studyAttempt++){
    try{$studyResponse=Invoke-WebRequest -Uri $studyUrl -UseBasicParsing -TimeoutSec 1;if($studyResponse.StatusCode -eq 200){break}}catch{Start-Sleep -Milliseconds 250}
  }
  if(-not $studyResponse -or $studyResponse.StatusCode -ne 200){throw '학습 페이지를 열지 못했습니다. 포트를 확인해 주세요.'}
}
Start-Process $studyUrl

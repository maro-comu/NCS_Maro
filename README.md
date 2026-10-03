# MARO · 신보 IT 스터디

신용보증기금 **IT·전산 직렬**을 준비하는 HTML / CSS / JavaScript 학습 웹입니다.

**웹페이지:** https://maro-comu.github.io/NCS_Maro/

## 학습 범위

- NCS: 의사소통능력, 문제해결능력, 수리능력, 자원관리능력
- 프로그래밍: Python, JavaScript, 알고리즘, 자료구조, 객체지향, 운영체제, 보안
- DB: SQL, JOIN·NULL·집계, 정규화, 키, 트랜잭션, 격리 수준, 인덱스

공개 웹에는 자체 제작 연습문제 **60개**(과목별 20개), 별도 정답·해설, 개념 학습 **9개**를 제공합니다. 답 선택, 채점, 해설, 오답 재풀이, 북마크, 영역별 학습, 학습 기록 백업을 지원합니다. 기록은 브라우저의 로컬 저장소에 보관되며 다른 기기로 자동 동기화되지 않습니다.

## 공식 NCS 자료

`data/sources.json`과 웹의 자료실에 한국산업인력공단의 공식 채용모델 공개자료를 연결했습니다. **공식 예시문항은 신용보증기금 실제 기출문제가 아닙니다.** 모든 연도·기관의 비공개 기출을 확보했다고 주장하지 않습니다.

공식 자료 중 제3자 지문을 포함하거나 재배포 허락이 확인되지 않은 원본·분리본은 공개 저장소에 넣지 않습니다. 제작 PC에서는 `downloads/`에 원본을 보관하고 `private-study/`에 문제·정답을 분리한 개인 학습용 자료를 제공합니다. 두 폴더는 Git에서 제외됩니다. 공개 웹은 공식 사이트로 연결하여 원문을 받을 수 있도록 합니다.

## 구조와 실행

```text
study-web/dist/       HTML·CSS·JavaScript 원본 및 생성된 공개 데이터
data/                자체 문제, 정답, 개념 학습, 공식 출처 목록
docs/                GitHub Pages 공개 파일
tools/               공개 파일 생성·검증·GitHub Pages 설정 도구
downloads/           공식 다운로드 원본 (로컬 전용, Git 제외)
private-study/       공식 원문을 사용하는 개인 학습 웹 (로컬 전용, Git 제외)
```

별도 프레임워크나 패키지 설치가 필요하지 않습니다. 공개용 `docs/index.html`을 브라우저에서 직접 열어도 문제 풀이가 동작합니다. HTTP 미리보기:

```powershell
node tools/build-public.mjs
node tools/validate-content.mjs --deploy docs
python -m http.server 8843 --bind 127.0.0.1 --directory docs
```

`http://127.0.0.1:8843/`에서 열 수 있습니다. 데이터 수정 후 `build-public.mjs`를 실행하면 `study-web/dist/data/`와 `docs/`를 함께 갱신합니다. GitHub Pages는 `main` 브랜치의 `/docs`를 공개합니다.

제작 PC에서는 `학습앱-열기.cmd`를 더블클릭하면 공식 원문과 분리 답안을 사용하는 개인 학습 웹을 엽니다. 내려받은 공식 파일이 없는 다른 PC에서는 공개 웹을 사용하세요.

## 문제와 정답 분리

`data/practice-questions.json`에는 문항·보기만, `data/practice-answers.json`에는 문제 ID별 0부터 시작하는 `correctIndex`와 해설을 저장합니다. 배포본도 `questions.json` / `answers.json`, `question-bank.js` / `answer-key.js`로 나뉩니다.

정적 웹의 답안 파일은 내려받아 확인할 수 있습니다. 이 구조는 개인 학습을 위한 분리이며 시험 보안 기능은 아닙니다. 채점 전에는 문제 풀이 화면에 정답을 표시하지 않습니다.

## 검증

문제와 정답 ID의 일치, 정답 인덱스, 질문의 정답 필드 제외, NCS 네 영역, 전 과목 개념 학습, 배포 경로를 확인했습니다. 코드 실행·SQL 결과·NCS 수리와 자원관리 계산을 검산하고, 실제 브라우저에서 과목 이동·채점·오답 재풀이를 확인했습니다. PostgreSQL 전용 동작은 공식 문서 기준입니다.

# MARO · 신보 IT 스터디

신용보증기금 **IT·전산 직렬**을 준비하는 HTML / CSS / JavaScript 학습 웹입니다.

**웹페이지:** https://maro-comu.github.io/NCS_Maro/

## 학습 범위

- NCS: 의사소통능력, 문제해결능력, 수리능력, 자원관리능력
- 프로그래밍: Python, JavaScript, 알고리즘, 자료구조, 객체지향, 운영체제, 보안
- DB: SQL, JOIN·NULL·집계, 정규화, 키, 트랜잭션, 격리 수준, 인덱스

공개 웹에는 자체 제작 연습문제 **1,200개**(NCS·프로그래밍·DB 각각 400개), 별도 정답·해설, 개념 학습 **9개**를 제공합니다. NCS는 의사소통·문제해결·수리·자원관리 각각 100개입니다. 기존 60개의 문제 ID를 유지하여 이전 오답·북마크 기록을 계속 사용할 수 있습니다.

서로 다른 지문·조건·코드·자료를 사용하는 문제를 추가했습니다. 같은 학습 개념을 반복 연습하는 변형 문항도 포함하며, 신규 문제에는 학습 주제와 문제 구조 ID를 기록합니다. 문제 검색, 주제·난이도·미풀이/오답/북마크 필터, 문제 목록 페이지 이동을 지원합니다. 답 선택, 채점, 해설, 오답 재풀이와 기록 백업도 사용할 수 있습니다. 기록은 브라우저의 로컬 저장소에 보관되며 다른 기기로 자동 동기화되지 않습니다.

## 공식 NCS 자료

`data/sources.json`과 웹의 자료실에 한국산업인력공단의 공식 채용모델 공개자료를 연결했습니다. **공식 예시문항은 신용보증기금 실제 기출문제가 아닙니다.** 모든 연도·기관의 비공개 기출을 확보했다고 주장하지 않습니다.

공식 자료 중 제3자 지문을 포함하거나 재배포 허락이 확인되지 않은 원본·분리본은 공개 저장소에 넣지 않습니다. 제작 PC에서는 `downloads/`에 원본을 보관하고 `private-study/`에 문제·정답을 분리한 개인 학습용 자료를 제공합니다. 두 폴더는 Git에서 제외됩니다. 공개 웹은 공식 사이트로 연결하여 원문을 받을 수 있도록 합니다.

## 구조와 실행

```text
study-web/dist/       HTML·CSS·JavaScript 원본 및 생성된 공개 데이터
data/                자체 문제, 정답, 개념 학습, 공식 출처 목록
data/expansion/      추가 연습문제 및 별도 정답·해설
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

추가 문항을 재생성하려면 Node.js와 Python을 사용합니다. 프로그래밍 생성기는 `STUDY_PYTHON` 환경변수 또는 PATH의 `python`을 선택하고, 실제 코드 실행과 독립 계산 검증까지 수행합니다.

```powershell
node tools/generate-ncs-expansion.mjs
node tools/generate-programming-expansion.mjs
python -X utf8 tools/generate-database-expansion.py
node tools/build-public.mjs
node tools/validate-content.mjs --deploy docs
```

DB 데이터 재현과 SQL 결과 대조는 `python -X utf8 tools/generate-database-expansion.py --check`, 프로그래밍 독립 검증은 `python -X utf8 tools/validate-programming-expansion.py`로 수행합니다.

제작 PC에서는 `학습앱-열기.cmd`를 더블클릭하면 공식 예시 **1,040문항**과 자체 연습 **1,200문항**, 합계 **2,240문항**을 사용하는 개인 학습 웹을 엽니다. **PDF 뷰어는 표시하지 않습니다.** 표·수식·그림은 문항 부분을 추출한 이미지로 보여주고, 정답과 해설은 제출 후에 표시합니다. 내려받은 공식 파일이 없는 다른 PC에서는 공개 웹을 사용하세요.

로컬 원본 16개 첨부의 표기상 문항 수는 1,530개이며, 이 중 이전 HWP 자료 490개는 다운로드 자료로 제공합니다. 판본 간 중복 여부는 전수 조사하지 않았습니다.

## 문제와 정답 분리

기존 `data/practice-questions.json`과 신규 `data/expansion/*-questions.json`에는 문항·보기만 저장합니다. 각각의 `*-answers.json`에는 문제 ID별 0부터 시작하는 `correctIndex`와 해설을 저장합니다. 배포본도 `questions.json` / `answers.json`, `question-bank.js` / `answer-key.js`로 나뉩니다. `tools/load-practice-bank.mjs`가 기존 문항과 추가 문항을 결합하며, 목표 수량은 `data/practice-bank-manifest.json`에서 관리합니다.

정적 웹의 답안 파일은 내려받아 확인할 수 있습니다. 이 구조는 개인 학습을 위한 분리이며 시험 보안 기능은 아닙니다. 채점 전에는 문제 풀이 화면에 정답을 표시하지 않습니다.

## 검증

문제와 정답 ID의 일치, 정답 인덱스, 질문의 정답 필드 제외, NCS 네 영역, 전 과목 개념 학습, 배포 경로를 확인합니다. 완전히 동일한 문항·보기 조합을 검출하고, 추가 문제의 구조 수와 구조당 반복 수를 검사합니다. 실행형 문항은 Python·Node.js·SQLite로 결과를 대조하고, NCS 계산·조건 문항은 수리·논리 검산을 사용합니다. 코드 실행으로 확인한 문항은 `computed-verified`, 작성·검토한 개념/지문 문항은 `original-reviewed`로 구분합니다. PostgreSQL 전용 동작은 공식 문서 기준입니다.

import fs from 'node:fs';
import assert from 'node:assert/strict';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

// All passages below are original fictional workplace scenarios. This generator
// never copies an examination, official source passage, or previous question.
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const questions = [], answers = {}, checks = [];
const categories = ['의사소통능력', '문제해결능력', '수리능력', '자원관리능력'];
const names = ['가온', '다온', '라온', '마루', '보람'];
const contexts = ['보증 상담 예약', '전산 장비 점검', '신입 직원 교육', '자료 보관 업무', '지역 기업 설명회'];
const sum = xs => xs.reduce((a, b) => a + b, 0);
const round = n => Number(n.toFixed(6));
const fmt = n => Number.isInteger(n) ? n.toLocaleString('ko-KR') : String(round(n));
function add(category, family, title, prompt, options, explanation, extras = {}, correctIndex = 0, verify) {
  assert.equal(options.length, 4);
  assert.equal(new Set(options).size, 4, `${family}: duplicate options`);
  const n = questions.length + 1, shift = (n * 7 + family.length) % 4;
  const id = `extra-ncs-${String(n).padStart(4, '0')}`;
  const shuffled = options.map((_, i) => options[(i + shift) % 4]);
  const answerIndex = (correctIndex - shift + 4) % 4;
  questions.push({ id, track: 'ncs', category, title, prompt: `자체 제작 연습문제 · ${prompt}`, options: shuffled,
    difficulty: extras.difficulty || '보통', sourceId: 'original', kind: 'original', learningTopic: title,
    templateId: `ncs-${family}`, ...extras });
  answers[id] = { correctIndex: answerIndex, explanation, verification: verify ? 'computed-verified' : 'original-reviewed' };
  if (verify) {
    checks.push({ id, family, run: () => {
      const actual = verify();
      assert.equal(actual, options[correctIndex], `${id}: independent solution disagrees: ${actual}`);
      assert.equal(shuffled[answerIndex], actual);
    }});
  }
}
const text = (family, title, prompt, passage, correct, wrong, why, difficulty = '보통') =>
  add(categories[0], family, title, prompt, [correct, ...wrong], why, { passage, difficulty });

// Communication: 19 reasoning/writing structures, five different situations each.
const notices = [
 ['상담 예약','평일 09:00~17:00','온라인 예약','신청 번호','화요일 16:00에 온라인으로 예약하고 신청 번호를 입력했다.','토요일 10:00에 온라인으로 예약하고 신청 번호를 입력했다.','화요일 16:00에 전화로 예약하고 신청 번호를 알렸다.','화요일 16:00에 온라인으로 예약하되 신청 번호를 생략했다.'],
 ['장비 반출','반출 하루 전 15:00까지','자산 관리 시스템','책임자 승인','반출 이틀 전 14:00에 자산 관리 시스템으로 신청하고 책임자 승인을 받았다.','반출 당일 10:00에 시스템 신청과 승인을 마쳤다.','반출 이틀 전 14:00에 개인 메신저로만 신청하고 승인을 받았다.','반출 이틀 전 14:00에 시스템 신청만 하고 승인 없이 반출했다.'],
 ['교육 신청','교육 시작 이틀 전까지','인사 포털','부서장 확인','교육 사흘 전에 인사 포털로 신청하고 부서장 확인을 받았다.','교육 당일 포털로 신청하고 확인을 받았다.','교육 사흘 전에 전자우편으로만 신청하고 확인을 받았다.','교육 사흘 전에 포털로 신청했지만 부서장 확인을 받지 않았다.'],
 ['서고 이용','평일 10:00~16:00','방문 기록부 작성','사원증 제시','수요일 11:00에 방문 기록부를 작성하고 사원증을 제시했다.','일요일 11:00에 기록부를 작성하고 사원증을 제시했다.','수요일 11:00에 기록부를 생략하고 사원증만 제시했다.','수요일 11:00에 기록부를 작성하고 사원증은 제시하지 않았다.'],
 ['설명회 발표 자료','행사 전날 12:00까지','공유 폴더','PDF 형식','행사 이틀 전 11:00에 공유 폴더에 PDF를 올렸다.','행사 당일 09:00에 공유 폴더에 PDF를 올렸다.','행사 이틀 전 11:00에 개인 메일함으로만 PDF를 보냈다.','행사 이틀 전 11:00에 공유 폴더에 편집용 파일만 올렸다.']
];
notices.forEach(([topic, deadline, route, required, good, ...bad]) => text('notice-conditions','공지의 복수 조건','공지의 조건을 모두 충족한 행동은?', `${topic} 안내: 허용 시간 또는 마감은 ${deadline}이다. ${route} 절차와 ${required} 요건을 모두 지켜야 한다. 다른 경로나 요건 생략은 인정하지 않는다.`, good, bad, '시간, 처리 경로, 필수 요건 세 조건을 따로 확인하면 정답의 행동만 모두 충족한다.','기초'));

const causes = [
 ['예약 안내 문자','대기 시간','새 예약 창구도 추가했다','대기 시간이 감소했다','예약 안내 문자 때문에만'],
 ['자동 점검 도구','장애 신고','노후 장비도 교체했다','장애 신고가 감소했다','자동 점검 도구 때문에만'],
 ['교육 교재 개편','시험 평균','교육 시간도 늘렸다','시험 평균이 상승했다','교재 개편 때문에만'],
 ['파일 분류 표','자료 탐색 시간','서고 위치도 바꾸었다','탐색 시간이 감소했다','분류 표 때문에만'],
 ['행사 안내 영상','참석 인원','초청 대상 범위도 넓혔다','참석 인원이 증가했다','안내 영상 때문에만']
];
causes.forEach(([change, metric, concurrent, observed, blame]) => text('causal-caution','관찰과 원인 구분','시범 사업 결과를 과장하지 않은 문장은?', `한 부서가 ${change}를 도입한 기간에 ${concurrent}. 조사 결과 ${observed}. 비교 부서는 조사하지 않았고 요인별 효과는 분석하지 않았다.`, `${observed}는 관찰되었지만 ${change}의 독립적 효과는 추가 검토가 필요하다.`, [`${blame} ${observed}.`, `모든 부서에서 ${metric} 개선이 입증되었다.`, `함께 시행한 다른 조치는 ${metric}에 영향을 주지 않았다.`], '동시에 바뀐 요인을 분리하지 않았으므로 변화의 관찰은 말할 수 있지만 단일 원인이나 전 부서 효과를 단정할 수 없다.'));

const requests = [
 ['상담팀','4월 지역별 신규 상담 건수','CSV','목요일 14:00','통계 공유 폴더'],
 ['전산팀','2분기 장비별 고장 이력','XLSX','금요일 11:00','점검 문서함'],
 ['교육팀','신입 교육 참석자 명단과 이수 여부','표준 양식','수요일 17:00','인사 포털'],
 ['기록팀','작년 폐기 대상 문서 목록','PDF','월요일 10:00','감사 자료 폴더'],
 ['행사팀','다음 설명회 확정 참가 기업 목록','CSV','화요일 16:00','행사 공유 폴더']
];
requests.forEach(([who, scope, format, deadline, location]) => text('request-specificity','업무 요청의 필수 정보','재확인 없이 실행하기 가장 쉬운 요청은?', `${who}에게 ${scope}를 요청하려고 한다. 필요한 형식은 ${format}, 마감은 ${deadline}, 전달 위치는 ${location}이다.`, `${scope}를 ${format}로 정리해 ${deadline}까지 ${location}에 올려 주세요.`, ['관련 자료를 적당히 정리해 빠른 시일 안에 보내 주세요.', `${scope}를 알아서 올려 주세요.`, `가능한 모든 자료를 ${deadline}까지 보내 주세요. 형식과 위치는 자유입니다.`], '범위, 형식, 마감, 전달 위치가 모두 특정되어 요청한 결과물을 식별할 수 있다.','기초'));

const minutes = [
 ['상담 대기 개선','안내문 초안','상담팀','금요일','지점장 검토 후 게시'],
 ['계정 정비','미사용 계정 목록','전산팀','수요일','담당자 확인 후 비활성화'],
 ['교육 개편','시범 교재','교육팀','월요일','한 부서 시범 운영 후 확대 판단'],
 ['기록 정리','보존 기간 목록','기록팀','화요일','감사팀 승인 후 폐기'],
 ['행사 준비','참가 신청 집계','행사팀','목요일','확정 기업에만 안내 발송']
];
minutes.forEach(([subject, deliverable, owner, deadline, gate]) => text('meeting-action','회의록에서 실행 항목 찾기','회의 결과와 일치하는 후속 행동은?', `${subject} 회의: ${owner}이 ${deadline}까지 ${deliverable}을 작성한다. 이후 ${gate}한다. 회의는 앞 절차를 생략하지 않기로 했다.`, `${owner}이 기한 내 ${deliverable}을 작성하고 정해진 후속 확인 절차를 거친다.`, [`${deliverable} 작성 담당을 정하지 않고 각자 자유롭게 처리한다.`, '마감과 관계없이 최종 조치를 먼저 실행한다.', '초안을 작성하지 않고 후속 확인 절차도 생략한다.'], '담당자, 기한, 결과물과 후속 조건을 회의에서 합의했다. 이 네 요소를 유지한 행동만 일치한다.'));

const mainClaims = [
 ['상담 기록','동일한 항목으로 기록해야 상담 이력을 비교할 수 있다. 다만 특이 사항은 별도 칸에 적어 획일적인 기록을 보완한다.','기록 항목을 표준화하되 특이 사항도 남겨야 한다.','상담 기록을 전부 자유 형식으로 바꾸어야 한다.','특이 사항은 비교에 방해되므로 삭제해야 한다.','상담의 질은 기록량에만 비례한다.'],
 ['장애 공지','빠른 공지는 필요하지만 확인하지 않은 원인을 적으면 혼란이 커진다. 먼저 영향 범위와 다음 안내 시간을 알리고 원인은 검증 후 추가한다.','확인된 영향과 다음 안내 시간을 먼저 제공하고 원인은 검증 후 알린다.','원인이 확정될 때까지 어떤 공지도 하지 않는다.','빠르면 추정 원인을 사실로 적어도 된다.','영향 범위는 이용자에게 필요하지 않다.'],
 ['교육 평가','만족도는 교육 경험을 보여 주지만 실제 업무 활용도를 직접 나타내지는 않는다. 일정 기간 뒤 업무 적용 사례를 조사해 평가를 보완한다.','만족도와 업무 적용 자료를 함께 평가해야 한다.','만족도가 높으면 모든 교육 목표가 달성되었다.','업무 적용 사례만 조사하면 교육 경험은 전혀 중요하지 않다.','만족도는 어떤 경우에도 쓸모가 없다.'],
 ['문서 검색','분류 기준이 자주 바뀌면 이용자가 위치를 기억하기 어렵다. 기준은 안정적으로 유지하면서 신규 유형은 정기 검토를 통해 추가한다.','분류 기준의 안정성과 새 유형 반영을 함께 고려한다.','분류 기준은 매일 바꾸어야 한다.','새 유형의 문서는 영구적으로 분류하지 않는다.','파일 수가 많으면 분류는 불필요하다.'],
 ['설명회 안내','전문 용어만 나열하면 처음 참여한 기업은 이해하기 어렵다. 핵심 용어를 간단히 설명하고 신청 절차를 사례로 보여 주면 이해를 돕는다.','용어 설명과 절차 사례를 제공해 이해를 돕는다.','참여 기업은 사전에 모든 용어를 알고 있어야 한다.','안내문에서 신청 절차는 제외해야 한다.','전문 용어를 많이 쓰는 것 자체가 이해도를 보장한다.']
];
mainClaims.forEach(([topic, passage, good, ...bad]) => text('main-point','중심 주장 찾기', `${topic}에 대한 글의 핵심 주장으로 적절한 것은?`, passage, good, bad, '정답은 글의 두 핵심 요구를 함께 반영한다. 다른 보기는 일부를 배제하거나 글에 없는 단정을 추가한다.','기초'));

const evidence = [
 ['새 예약 화면이 입력 오류를 줄인다','동일한 조건에서 기존 화면과 새 화면을 무작위로 배정했더니 새 화면의 오류율이 더 낮았다.','화면 색상이 직원에게 인기가 높았다.','새 화면을 만든 업체의 사무실이 가까웠다.','기존 화면의 이름이 길었다.'],
 ['점검 교육이 장애 대응 정확도를 높인다','유사한 경력의 직원들을 교육군과 비교군으로 나누어 같은 사례를 평가하니 교육군의 정확도가 더 높았다.','교육 안내 포스터가 보기 좋았다.','강의실의 의자가 많았다.','교육군의 참석 시간이 기록되어 있다.'],
 ['새 분류표가 자료 검색 시간을 줄인다','같은 난이도의 검색 과제를 두 분류 방식에 교차 배정했더니 새 분류표에서 평균 시간이 짧았다.','분류표 파일의 용량이 작았다.','분류표 작성자가 자료를 오래 보관했다.','서고 이름이 바뀌었다.'],
 ['사전 안내가 설명회 불참을 줄인다','참가 예정 기업을 무작위로 나누어 한 집단만 사전 안내를 보냈더니 그 집단의 불참 비율이 낮았다.','안내문에 기관 로고가 들어갔다.','행사장의 층수가 높았다.','참가 예정 기업의 이름을 가나다순으로 정리했다.'],
 ['검토 목록이 보고서 누락을 줄인다','동일한 자료의 보고서를 검토 목록 사용 여부에 따라 비교하니 사용 집단의 누락 항목이 더 적었다.','검토 목록을 인쇄한 종이가 두꺼웠다.','보고서 제목을 바꾸었다.','회의 참석자의 자리가 바뀌었다.']
];
evidence.forEach(([claim, good, ...bad]) => text('relevant-evidence','주장을 뒷받침하는 근거','주장에 가장 직접적인 근거는?', `검토할 주장: “${claim}.” 다른 조건을 가급적 같게 유지한 비교 자료를 찾고 있다.`, good, bad, '주장의 결과 지표를 직접 비교하고 다른 조건을 통제한 자료가 관련성과 설명력이 가장 높다.','보통'));

const stats = [
 ['상담 오류율',12,8,'오류 건수는 각각 12건과 16건, 처리 건수는 각각 100건과 200건이었다.'],
 ['장애 비율',10,5,'장애 장비는 각각 5대와 10대, 점검 장비는 각각 50대와 200대였다.'],
 ['교육 미이수율',20,10,'미이수자는 각각 4명과 6명, 대상자는 각각 20명과 60명이었다.'],
 ['서류 반려율',15,10,'반려는 각각 15건과 20건, 제출은 각각 100건과 200건이었다.'],
 ['행사 불참률',25,20,'불참은 각각 10개사와 20개사, 신청은 각각 40개사와 100개사였다.']
];
stats.forEach(([metric, oldRate, newRate, data]) => text('count-versus-rate','건수와 비율 구분','자료와 일치하는 보고 문장은?', `1기와 2기의 ${metric}를 비교한다. ${data}`, `2기의 ${metric}는 ${newRate}%로 1기의 ${oldRate}%보다 낮지만 해당 건수는 늘었다.`, [`2기에는 해당 건수와 비율이 모두 감소했다.`, `2기의 ${metric}는 ${oldRate-newRate}%이다.`, '분모가 다르므로 어떤 비율도 계산할 수 없다.'], `각 비율은 해당 건수÷전체 대상 수로 계산한다. 비율의 감소와 건수의 증가는 분모 증가 때문에 동시에 가능하다.`, '보통'));

const exemptions = [
 ['방문 상담','예약자','긴급 장애 신고자','온라인 신청','긴급 장애 신고자는 예약 없이 상담할 수 있으나 온라인 신청 기록은 남겨야 한다.'],
 ['야간 서버실 출입','사전 승인자','당직 사고 대응자','출입 기록','당직 사고 대응자는 사전 승인 없이 출입할 수 있으나 출입 기록은 남겨야 한다.'],
 ['외부 교육 수강','부서 추천자','필수 자격 갱신 대상자','수료증 제출','필수 자격 갱신 대상자는 부서 추천 없이 수강할 수 있으나 수료증은 제출해야 한다.'],
 ['문서 긴급 열람','담당자 승인자','감사 현장 요청자','열람 대장 기록','감사 현장 요청자는 담당자 승인 없이 열람할 수 있으나 열람 대장에는 기록해야 한다.'],
 ['행사 현장 등록','사전 신청 기업','초청 기관 담당자','참석 확인','초청 기관 담당자는 사전 신청 없이 등록할 수 있으나 참석 확인은 해야 한다.']
];
exemptions.forEach(([act, normal, exceptional, still, good]) => text('exception-scope','예외 적용 범위','규정을 정확하게 이해한 것은?', `${act}은 원칙적으로 ${normal}만 가능하다. 단, ${exceptional}에게는 이 요건을 면제한다. ${still} 의무는 모든 이용자에게 적용된다.`, good, [`${exceptional}는 모든 절차를 면제받는다.`, `${exceptional}도 예외 없이 일반 요건을 먼저 충족해야 한다.`, `${still} 의무는 일반 이용자에게만 적용된다.`], '예외는 명시된 한 요건에만 적용된다. 모든 이용자에게 적용되는 별도 의무는 그대로 유지된다.'));

const processes = [
 ['상담 접수','신청서 제출','서류 확인','보완 요청 또는 접수 확정'],
 ['장비 도입','구매 요청','예산 확인','승인 후 발주'],
 ['교육 개설','수요 조사','과정 설계','시범 평가 후 확정'],
 ['자료 폐기','대상 선정','보존 기간 확인','승인 후 폐기'],
 ['행사 초청','대상 추출','명단 검토','확정 명단에 발송']
];
processes.forEach(([topic,a,b,c]) => text('process-reading','설명문에서 절차 복원','안내에 맞는 처리 순서는?', `${topic} 업무는 먼저 ${a}를 한다. 이 결과를 바탕으로 ${b}를 거쳐 ${c}한다. 앞 단계 없이 뒤 단계를 진행할 수 없다.`, `${a} → ${b} → ${c}`, [`${b} → ${a} → ${c}`,`${c} → ${b} → ${a}`,`${a} → ${c} → ${b}`], '시간 표현과 선행 조건을 연결하면 첫 단계, 중간 확인, 최종 조치의 순서가 확정된다.','기초'));

const reconciliations = [
 ['예약 처리',40,30,10,'예약 40건 중 30건 확정, 10건 검토 중'],
 ['장비 점검',60,48,12,'장비 60대 중 48대 완료, 12대 대기'],
 ['교육 이수',50,45,5,'대상 50명 중 45명 이수, 5명 미이수'],
 ['문서 분류',80,56,24,'문서 80건 중 56건 분류, 24건 미분류'],
 ['기업 초청',100,70,30,'대상 100개사 중 70개사 발송, 30개사 미발송']
];
reconciliations.forEach(([topic,total,done,pending,source]) => text('fact-check-summary','원자료와 보고문 대조','원자료에 근거한 정확한 문장은?', `원자료: ${source}. 모든 대상은 두 상태 중 하나에만 속하며 누락은 없다.`, `${topic} 완료 비율은 ${done/total*100}%이며 나머지 ${pending}개 대상은 아직 완료되지 않았다.`, [`${topic} 완료 비율은 ${pending/total*100}%이다.`, `전체 ${total+pending}개 대상 중 ${done}개가 완료되었다.`, `미완료 ${pending}개 대상도 완료 건수에 포함해야 한다.`], `두 상태를 더하면 전체 ${total}개이며 완료율은 ${done}÷${total}×100=${done/total*100}%이다.`,'기초'));

const meanings = [
 ['검토 범위를 한정한다','이번 보고서는 신규 신청만 검토하고 기존 신청은 별도 보고서에서 다룬다.','대상을 일정한 범위로 제한한다.','검토 대상 전체를 폐기한다.','서로 다른 대상들을 같은 것으로 본다.','검토 시기를 무기한 연장한다.'],
 ['근거를 보완한다','초기 조사에 표본이 적어 추가 자료로 결론의 근거를 보완한다.','부족한 부분을 더 채운다.','이미 있는 모든 근거를 삭제한다.','결론을 먼저 확정하고 자료를 숨긴다.','조사를 시작하지 않는다.'],
 ['절차를 간소화한다','중복 입력 칸을 줄여 신청 절차를 간소화한다. 단 필수 확인은 유지한다.','불필요한 복잡함을 줄인다.','필수 요건을 모두 없앤다.','신청을 영구적으로 금지한다.','같은 입력을 반복하게 한다.'],
 ['변경 내용을 유보한다','원인이 불명확해 운영 방식 변경을 유보하고 추가 검증을 한다.','결정을 당장 실행하지 않고 미룬다.','변경을 이미 완료한다.','검증 없이 변경을 확정한다.','모든 검토 기록을 폐기한다.'],
 ['결과를 교차 확인한다','두 담당자가 서로 다른 원자료를 비교해 결과를 교차 확인한다.','여러 자료나 방법으로 맞는지 대조한다.','한 자료만 보고 다른 자료는 버린다.','근거 없이 다수결로 정한다.','숫자를 서로 바꾸어 적는다.']
];
meanings.forEach(([word,passage,good,...bad])=>text('context-vocabulary','문맥 속 업무 용어',`글에서 “${word}”의 의미로 가장 적절한 것은?`,passage,good,bad,'앞뒤 문장이 설명하는 실제 행동을 기준으로 용어의 의미를 해석해야 한다.','기초'));

const intents = [
 ['첨부 자료의 기준일이 지난달로 되어 있네요. 오늘 회의에서는 이번 달 현황이 필요합니다.','이번 달 기준 자료로 갱신해 달라는 요청이다.','이번 달 현황이 불필요하다는 뜻이다.','지난달 자료만 앞으로 사용하자는 뜻이다.','오늘 회의를 무조건 취소하자는 뜻이다.'],
 ['장애 공지에 다음 안내 시간이 빠져 있어 이용자가 계속 문의합니다.','다음 안내 시간을 명시해 달라는 요청이다.','이용자의 문의를 무시하라는 뜻이다.','장애 공지를 영구 삭제하라는 뜻이다.','문의가 있다는 사실을 부정하는 뜻이다.'],
 ['교육 자료 글씨가 작아 뒷자리에서는 읽기 어렵다는 의견이 있었습니다.','가독성을 높이도록 자료를 수정해 달라는 요청이다.','교육 참가자를 줄이라는 뜻이다.','내용 검토를 중단하라는 뜻이다.','앞자리의 참석을 금지하라는 뜻이다.'],
 ['파일명이 모두 최종본이라 어느 문서를 써야 할지 모르겠습니다.','버전을 구분할 수 있는 파일명을 사용해 달라는 요청이다.','최종본을 더 많이 복사하라는 뜻이다.','자료를 모두 인쇄하라는 뜻이다.','파일의 내용을 전부 지우라는 뜻이다.'],
 ['초청 메일에는 장소가 있지만 찾아오는 길이 없어 문의가 많습니다.','오시는 길 정보를 보완해 달라는 요청이다.','행사 장소를 없애자는 뜻이다.','초청 대상 명단을 공개하라는 뜻이다.','문의가 없어질 때까지 메일을 보내지 말라는 뜻이다.']
];
intents.forEach(([passage,good,...bad])=>text('indirect-request','간접 표현의 의도','발언의 업무상 의도로 가장 타당한 것은?',passage,good,bad,'문제 상황과 원하는 결과를 연결하면 표현하지 않은 구체적 보완 요청을 파악할 수 있다.'));

const conflicts = [
 ['신청 자료가 약속한 기한보다 하루 늦어 접수가 지연되었다.','약속한 기한과 실제 도착일을 확인하고 이후 전달 일정과 알림 방법을 합의한다.'],
 ['점검 기록의 장비 번호가 서로 달라 같은 장비의 이력이 분산되었다.','실제 장비 번호를 원자료와 대조하고 번호 기록 규칙을 합의한다.'],
 ['교육 담당자와 부서 담당자의 참석 인원 집계가 다르다.','출석 기준과 명단을 함께 대조하고 집계 기준을 통일한다.'],
 ['정리 담당자들이 같은 파일을 서로 다른 폴더에 저장했다.','폴더 기준을 확인하고 공통 저장 위치와 책임자를 합의한다.'],
 ['행사 시작 시간을 두 부서가 다르게 안내했다.','승인된 행사 계획에서 시간을 확인한 뒤 통일된 정정 안내를 발송한다.']
];
conflicts.forEach(([passage,good])=>text('conflict-fact','갈등 상황의 사실 중심 대화','문제를 해결하는 대화 방식으로 가장 적절한 것은?',passage,good,['원자료를 확인하지 않고 상대방의 성격을 비난한다.','문제가 반복되어도 이야기하지 않고 기록을 없앤다.','담당자 수가 더 많은 부서의 말이 항상 맞다고 결정한다.'],'관찰 가능한 사실을 함께 확인하고 재발 방지를 위한 절차를 합의하는 방식이 업무 갈등 해결에 적절하다.'));

const plain = [
 ['이중 인증','로그인할 때 비밀번호에 더해 문자로 받은 확인 번호도 입력해 주세요.','인증 체계의 다중화된 정합성 메커니즘을 이행하십시오.','보안을 위해 여러 가지를 알아서 처리하세요.','비밀번호는 입력하지 않아도 됩니다.'],
 ['서류 보완','신청서의 서명 칸을 채운 뒤 목요일까지 접수 화면에 다시 올려 주세요.','보완의무의 이행에 따른 제반 사항을 준수하십시오.','서류에 문제가 있으니 적당히 고쳐 주세요.','누락된 서명은 앞으로도 제출하지 마세요.'],
 ['교육 이수 확인','교육을 마친 뒤 마지막 화면의 수료 확인 버튼을 눌러 주세요.','수료 실적의 후행적 확증 처리를 수행하십시오.','교육을 보면 뭐든 자동으로 끝납니다.','수료 확인 버튼은 누르지 마세요.'],
 ['파일 접근 제한','이 자료는 지정 담당자만 열 수 있습니다. 접근이 필요하면 문서 관리자에게 신청하세요.','접근권한 정책의 차등화된 실효성을 담보하십시오.','자료는 필요한 사람에게 자유롭게 복사해 주세요.','접근 신청 방법은 안내하지 않습니다.'],
 ['행사 참석 변경','참석 인원이 바뀌면 행사 전날까지 신청 화면에서 인원을 수정해 주세요.','참여 규모 변동에 따른 제반 후속 처리를 이행하십시오.','인원이 바뀌어도 아무 조치 없이 오세요.','인원 수정은 행사 후에만 가능합니다.']
];
plain.forEach(([topic,good,...bad])=>text('audience-language','이용자 눈높이 안내',`처음 이용하는 사람에게 ${topic} 행동을 명확히 안내한 문장은?`,`수신자는 내부 전문 용어를 모르는 이용자이다. 해야 할 행동과 방법을 쉬운 말로 안내해야 한다.`,good,bad,'구체적인 행동과 방법을 익숙한 말로 제시했다. 추상적인 표현, 모호한 지시 또는 반대 행동은 안내 목적에 맞지 않는다.','기초'));

const sources = [
 ['상담 대기 시간','최근 한 달의 전체 접수·상담 시각 기록과 계산 방법을 담은 보고서','직원 한 명의 오래된 기억','출처와 기간이 없는 온라인 댓글','대기 시간이 짧다는 행사 홍보 문구'],
 ['장비 고장률','점검 대상 수와 고장 판정 기준을 함께 적은 최신 점검 대장','판매 업체의 근거 없는 우수성 문구','장비 이름만 담긴 오래된 목록','고장 난 한 대를 찍은 사진만'],
 ['교육 이수 현황','대상 명단, 출석 기준, 수료 기록을 함께 대조한 집계','한 참가자의 만족도 후기','강사 소개 자료','신청 인원만 적고 수료 여부가 없는 표'],
 ['문서 보존 현황','보존 기준과 조사 기준일을 명시한 전체 문서 관리 대장','폴더가 많다는 담당자의 인상','기준일을 알 수 없는 일부 화면 캡처','정리 성과를 강조한 구호'],
 ['설명회 참석률','신청 기업과 실제 참석 기업을 중복 제거해 비교한 현장 기록','행사장의 최대 좌석 수만','오래전 다른 행사 참석률','참가 신청 광고의 조회 수만']
];
sources.forEach(([topic,good,...bad])=>text('source-quality','자료의 신뢰성과 적합성',`${topic}를 검증할 자료로 가장 적합한 것은?`,`수치의 출처, 기준, 범위와 조사 시기를 확인할 수 있는 자료가 필요하다.`,good,bad,'판정 기준과 대상 범위를 가진 원자료 또는 이를 대조한 집계가 목적에 직접 부합한다. 홍보, 인상, 기간 불명 자료는 검증력이 부족하다.'));

const versions = [
 ['상담 예약','10월 1일','예약 가능 기간 7일','예약 가능 기간 14일','10월 3일'],
 ['장비 점검','11월 1일','점검 주기 30일','점검 주기 20일','11월 5일'],
 ['교육 신청','9월 15일','담당자 승인 필요','부서장 승인 필요','9월 20일'],
 ['문서 제출','12월 1일','전자우편 제출','공유 시스템 제출','12월 2일'],
 ['행사 취소','8월 10일','취소 요청은 전화 접수','취소 요청은 신청 화면 접수','8월 12일']
];
versions.forEach(([topic,effective,oldRule,newRule,now])=>text('effective-version','시행일과 문서 버전','문의에 적용할 규정은?', `${topic} 규정 구버전은 “${oldRule}”라고 되어 있다. 개정판은 ${effective}부터 “${newRule}”를 적용한다고 명시한다. 별도 유예나 예외는 없고 문의일은 ${now}이다.`, `${newRule}를 적용한다.`, [`${oldRule}를 계속 적용한다.`,'작성 날짜와 시행일을 무시하고 두 규정을 동시에 적용한다.','최신 규정이 있어도 담당자 개인 취향에 따른다.'],'문의일이 시행일 이후이고 유예 규정이 없으므로 개정판을 적용한다.'));

const gaps = [
 ['상담 월별 실적','어느 기간의 어떤 상담 유형을 집계해야 하나요?','상담 실적 자료를 보내 주세요.'],
 ['장비 구매 견적','필요 장비의 사양과 수량은 무엇인가요?','장비를 사려고 하니 견적을 받아 주세요.'],
 ['교육 장소 예약','참석 인원과 사용 날짜·시간은 언제인가요?','교육 장소를 예약해 주세요.'],
 ['문서 변환','변환할 파일 목록과 원하는 파일 형식은 무엇인가요?','문서를 변환해 주세요.'],
 ['기업 초청','초청 대상 기준과 행사 일시는 무엇인가요?','기업에 초청장을 보내 주세요.']
];
gaps.forEach(([topic,good,request])=>text('clarify-missing','빠진 정보를 확인하는 질문','업무를 시작하기 전에 우선 확인할 질문은?',`전달받은 요청: “${request}” 현재 추가 자료나 합의는 없다.`,good,['요청한 사람의 개인 취미는 무엇인가요?','완료와 상관없는 다른 행사 이름은 무엇인가요?','일을 수행하지 않아도 된다는 뜻인가요?'],'업무 결과물과 수행 조건을 정하는 정보를 먼저 확인하면 잘못된 범위로 작업하는 일을 줄일 수 있다.','기초'));

const connectors = [
 ['안내 화면을 단순하게 바꾸었다.','필수 입력 항목은 여전히 남겨 두었다.','그러나','단순화와 필수 항목 유지가 대조된다.'],
 ['같은 문서를 두 번 입력하면 오류 가능성이 커진다.','한 번 입력한 자료를 재사용하도록 개선한다.','따라서','앞 문장의 문제에서 뒤 문장의 조치를 도출한다.'],
 ['교육 신청 인원이 예상보다 많았다.','추가 강의실도 확보했다.','이에 따라','앞 상황을 원인으로 추가 조치가 뒤따른다.'],
 ['파일명에 기준일을 적어야 한다.','작성 부서도 함께 적어야 한다.','또한','동일한 목적의 추가 요구를 연결한다.'],
 ['장애 원인은 아직 확정되지 않았다.','확인된 영향 범위는 즉시 안내할 수 있다.','다만','앞 진술의 제한 속에서 가능한 사항을 덧붙인다.']
];
connectors.forEach(([a,b,good,why],i)=>{const all=['그러나','따라서','또한','예를 들어','이에 따라','다만'];const bad=all.filter(x=>x!==good && !(good==='따라서'&&x==='이에 따라')&&!(good==='이에 따라'&&x==='따라서')&&!(good==='그러나'&&x==='다만')&&!(good==='다만'&&x==='그러나')).slice(0,3);text('sentence-relation','문장 사이의 관계','빈칸에 넣을 연결 표현으로 가장 자연스러운 것은?',`${a} (     ) ${b}`,good,bad,`${why} 해당 관계를 나타내는 연결 표현을 선택해야 한다.`);});

const common = [
 ['예약 절차는 짧아야 이용자가 편리하다.','필수 정보가 누락되지 않아야 업무가 정확하다.','편의를 높이면서 필수 정보의 정확성도 확보한다.'],
 ['장비 점검은 업무 중단 시간을 줄여야 한다.','점검 항목을 빠짐없이 수행해야 장애를 예방한다.','업무 영향과 점검의 충실성을 함께 고려한다.'],
 ['교육 자료는 쉽게 이해할 수 있어야 한다.','교육 내용은 실제 업무 기준에 정확히 맞아야 한다.','이해하기 쉬우면서 업무 기준에 정확한 자료를 만든다.'],
 ['문서 저장 체계는 찾기 쉬워야 한다.','민감 자료의 접근 권한은 지켜야 한다.','검색 편의와 접근 통제를 함께 충족한다.'],
 ['설명회 참가 절차는 간단해야 한다.','행사 운영에 필요한 참석 정보는 확인해야 한다.','간단한 참가 절차로 필수 참석 정보를 확인한다.']
];
common.forEach(([a,b,good])=>text('integrate-viewpoints','서로 다른 관점 통합','두 의견을 함께 반영한 합의안은?',`A: “${a}”\nB: “${b}”`,good,['A의 요구만 반영하고 B의 요구는 모두 버린다.','B의 요구만 반영하고 A의 요구는 모두 버린다.','두 요구가 다르다는 이유만으로 업무를 영구 중단한다.'],'두 의견은 서로 다른 평가 기준을 제시한다. 동시에 충족할 수 있는 방식으로 합의하면 한쪽의 중요 요구를 버리지 않는다.'));

// Subsequent sections generate logic, numerical and resource questions.
function permutations(xs) { return xs.length ? xs.flatMap((x,i) => permutations(xs.filter((_,j)=>i!==j)).map(p=>[x,...p])) : [[]]; }
function subsets(xs) { return Array.from({length:2**xs.length},(_,mask)=>xs.filter((_,i)=>mask&(1<<i))); }
function logic(family,title,prompt,passage,options,why,verify,difficulty='보통') {
  add(categories[1],family,title,prompt,options,why,{passage,difficulty},0,verify);
}
for(let i=0;i<5;i++) {
  const taskSets = [['자료 수집','사실 대조','초안 작성','최종 승인'],['장비 인수','연결 시험','보안 점검','사용 승인'],['수요 조사','일정 확정','참가 모집','교육 실시'],['목록 작성','기간 확인','폐기 승인','폐기 실행'],['기업 선정','연락처 확인','초청 발송','참석 집계']];
  const t=taskSets[i], correct=t.join(' → ');
  logic('precedence-order','선행 조건에 따른 순서','모든 조건을 충족한 작업 순서는?',`${t[2]}는 ${t[1]} 뒤에, ${t[1]}는 ${t[0]} 뒤에, ${t[3]}는 ${t[2]} 뒤에 해야 한다. 네 작업은 한 번씩 수행한다.`,[correct,[t[1],t[0],t[2],t[3]].join(' → '),[t[0],t[2],t[1],t[3]].join(' → '),[t[0],t[1],t[3],t[2]].join(' → ')],`세 선행 관계를 연결하면 ${correct}만 가능하다.`,()=>{const ok=permutations(t).filter(p=>p.indexOf(t[0])<p.indexOf(t[1])&&p.indexOf(t[1])<p.indexOf(t[2])&&p.indexOf(t[2])<p.indexOf(t[3]));assert.equal(ok.length,1);return ok[0].join(' → ');});
}
for(let i=0;i<5;i++) {
  const p=[names[i],names[(i+1)%5],names[(i+2)%5]], jobs=['자료 확인','고객 안내','결과 집계'];
  const assign=permutations(jobs).filter(a=>a[0]!==jobs[0]&&a[0]!==jobs[2]&&a[1]!==jobs[1]&&a[2]!==jobs[0]);
  assert.equal(assign.length,1);
  const answer=assign[0].map((j,k)=>`${p[k]}: ${j}`).join(' / ');
  const wrong=permutations(jobs).filter(a=>a.join()!==assign[0].join()).slice(0,3).map(a=>a.map((j,k)=>`${p[k]}: ${j}`).join(' / '));
  logic('one-to-one-assignment','일대일 업무 배정','조건에 맞는 배정은?',`${p.join(', ')} 세 사람에게 ${jobs.join(', ')}를 하나씩 중복 없이 배정한다. ${p[0]}은 ${jobs[0]}도 ${jobs[2]}도 맡지 않는다. ${p[1]}은 ${jobs[1]}을 맡지 않고, ${p[2]}는 ${jobs[0]}을 맡지 않는다.`,[answer,...wrong],`${p[0]}은 ${jobs[1]}만 가능하다. 남은 두 작업 중 ${p[2]}는 ${jobs[0]}을 못 맡으므로 ${jobs[2]}, ${p[1]}은 ${jobs[0]}이다.`,()=>{const solutions=permutations(jobs).filter(a=>a[0]!==jobs[0]&&a[0]!==jobs[2]&&a[1]!==jobs[1]&&a[2]!==jobs[0]);assert.equal(solutions.length,1);return solutions[0].map((j,k)=>`${p[k]}: ${j}`).join(' / ');});
}
const implications=[
 ['신속 심사 대상이다','서류 확인을 마쳤다','담당자 검토를 받았다'],
 ['운영 서버에 반영되었다','보안 검사를 통과했다','검사 기록이 있다'],
 ['교육 수료자로 등록되었다','출석 기준을 충족했다','출석 기록이 남았다'],
 ['폐기가 승인되었다','보존 기간이 끝났다','기간 확인을 받았다'],
 ['초청장이 발송되었다','명단이 확정되었다','연락처가 확인되었다']
];
implications.forEach(([a,b,c])=>logic('contrapositive-chain','조건문의 연쇄와 대우','반드시 참인 결론은?',`모든 대상에 대해 “${a}면 ${b}”, “${b}면 ${c}”가 성립한다. 대상 X는 “${c}”가 거짓이다.`,[`${a}는 거짓이다.`,`${a}는 참이다.`,`${b}는 참이다.`,`${c}는 참이다.`],`A→B→C와 C가 거짓이라는 조건에서 대우를 차례로 적용하면 B도 A도 거짓이다.`,()=>{const models=subsets(['a','b','c']).map(s=>({a:s.includes('a'),b:s.includes('b'),c:s.includes('c')})).filter(m=>(!m.a||m.b)&&(!m.b||m.c)&&!m.c);assert(models.length>0&&models.every(m=>!m.a));return `${a}는 거짓이다.`;}));
for(let i=0;i<5;i++) {
  const p=[names[i],names[(i+1)%5],names[(i+2)%5]];
  const subject=['접수 목록 누락','시험 장비 미반납','출석 기록 누락','문서 이름 오기','초청 대상 누락'][i];
  logic('truth-count','발언의 참·거짓 개수','누가 해당 실수를 했는가?',`세 사람 중 정확히 한 사람이 ${subject} 실수를 했다. 세 발언 중 정확히 두 개가 참이다.\n${p[0]}: “${p[1]}가 했다.”\n${p[1]}: “${p[0]}이 했다.”\n${p[2]}: “${p[1]}는 하지 않았다.”`,[p[0],p[1],p[2],'누구인지 확정할 수 없다.'],`${p[0]}이 실수한 경우 발언은 거짓·참·참이다. ${p[1]}이면 참·거짓·거짓, ${p[2]}이면 거짓·거짓·참이므로 조건을 충족하는 사람은 ${p[0]}이다.`,()=>{const ok=p.filter(who=>sum([who===p[1],who===p[0],who!==p[1]].map(Number))===2);assert.equal(ok.length,1);return ok[0];});
}
for(let i=0;i<5;i++) {
  const total=40+10*i, a=20+4*i,b=15+3*i,both=5+i, neither=total-a-b+both;
  logic('set-overlap','중복 집계와 집합','두 요건을 모두 충족하지 않는 대상 수는?',`전체 ${total}개 ${contexts[i]} 대상 중 요건 A 충족은 ${a}개, 요건 B 충족은 ${b}개이다. 두 요건을 모두 충족한 대상은 ${both}개이다. 여기서 “모두 충족하지 않는”은 A도 B도 충족하지 않는다는 뜻이다.`,[`${neither}개`,`${total-a-b}개`,`${neither+both}개`,`${total-both}개`],`A 또는 B를 충족한 대상은 ${a}+${b}−${both}=${a+b-both}개이다. 전체에서 빼면 ${neither}개이다.`,()=>{const onlyA=a-both,onlyB=b-both;const cells=[both,onlyA,onlyB,total-both-onlyA-onlyB];assert.equal(sum(cells),total);return `${cells[3]}개`;});
}
for(let i=0;i<5;i++) {
  const emergency=i%2===0, sensitive=i%3===0, needCheck=i%2===1;
  const answer=emergency?'즉시 대응':sensitive?'보안 담당 검토':needCheck?'보완 요청':'일반 처리';
  const labels=['즉시 대응','보안 담당 검토','보완 요청','일반 처리'];
  logic('priority-rule','우선 적용 규칙','이 건의 처리 결과는?',`가상 ${contexts[i]} 처리 규칙은 위에서부터 처음 충족하는 항목 하나를 적용한다.\n1. 긴급 건이면 즉시 대응\n2. 긴급이 아니고 민감 자료가 있으면 보안 담당 검토\n3. 앞 두 항목이 아니고 필수 항목이 빠졌으면 보완 요청\n4. 나머지는 일반 처리\n현재 건: 긴급 ${emergency?'해당':'미해당'}, 민감 자료 ${sensitive?'있음':'없음'}, 필수 항목 누락 ${needCheck?'있음':'없음'}.`,[answer,...labels.filter(x=>x!==answer)],'첫 번째 해당 규칙을 적용하고 이후 규칙을 더 적용하지 않는다. 긴급 여부, 민감 자료, 필수 누락을 정해진 순서로 확인한다.',()=>{const rules=[{when:emergency,result:labels[0]},{when:sensitive,result:labels[1]},{when:needCheck,result:labels[2]},{when:true,result:labels[3]}];return rules.find(r=>r.when).result;},'기초');
}
const diagnoses=[
 ['신청 화면 오류','브라우저 캐시','캐시를 지운 동일 계정에서 정상 작동하고 캐시를 유지한 계정에서만 오류가 재현된다.'],
 ['장비 연결 실패','케이블','같은 장비에서 케이블을 바꾸면 정상이고 문제 케이블을 다른 장비에 연결하면 실패한다.'],
 ['수료 기록 미반영','이수 연계 작업','수료 원자료는 정상인데 연계 작업을 다시 실행한 대상만 기록이 나타난다.'],
 ['문서 검색 누락','검색 색인','원본 파일과 권한은 정상이며 색인을 재작성하면 같은 검색어로 파일이 나타난다.'],
 ['초청 메일 반송','수신 주소','내용과 발송 서버를 유지한 채 확인된 주소로 고치면 정상 전달된다.']
];
diagnoses.forEach(([symptom,cause,observed])=>logic('controlled-diagnosis','한 요인씩 비교하는 진단','우선 검토할 원인으로 가장 근거가 강한 것은?',`${symptom}이 발생했다. 다른 조건은 유지한 채 한 요인씩 바꾸었다. ${observed}`,[cause,'담당자의 이름','시험 날짜의 요일만','원자료 파일 제목의 글자 수'],'해당 요인만 바꾸었을 때 증상이 달라지고 문제 조건에서 재현되므로 제시된 후보 중 가장 직접적인 원인 근거가 있다. 실제 최종 확정은 추가 검증할 수 있다.'));
for(let i=0;i<5;i++) {
  const d=2+i, people=4+2*i, tests=Math.ceil(Math.log2(people));
  logic('binary-identification','예·아니오 검사와 정보량','최악의 경우를 보장하려면 이론상 최소 몇 번의 검사가 필요한가?',`서로 다른 원인 후보가 ${people}개이며 정확히 하나가 원인이다. 각 검사는 예·아니오 두 결과만 낸다. 후보를 원하는 집합으로 나누는 검사를 만들 수 있고 결과에 따라 다음 검사를 선택할 수 있다.`,[`${tests}번`,`${tests-1}번`,`${tests+1}번`,`${people}번`],`k번의 이진 결과는 최대 2^k가지 후보를 구분한다. 2^${tests-1}<${people}≤2^${tests}이므로 ${tests}번이 필요하고 균형 있게 나누면 달성할 수 있다.`,()=>{let leaves=1,k=0;while(leaves<people){leaves*=2;k++;}return `${k}번`;},'심화');
}
for(let i=0;i<5;i++) {
  const costs={AB:2+i,AC:4+i,BC:1,BD:6,CD:2};
  const routes=[['A','B','D'],['A','C','D'],['A','B','C','D']];
  const routeCost=p=>sum(p.slice(1).map((v,k)=>costs[p[k]+v]));
  const best=routes.reduce((a,b)=>routeCost(a)<routeCost(b)?a:b);
  const out=p=>`${p.join('→')} (${routeCost(p)}분)`;
  logic('network-path','경로 탐색과 제약','총 이동 시간이 가장 짧은 허용 경로는?',`가상 ${contexts[i]} 업무 동선이다. A→B ${costs.AB}분, A→C ${costs.AC}분, B→C ${costs.BC}분, B→D ${costs.BD}분, C→D ${costs.CD}분이다. 표에 없는 이동은 불가능하고 되돌아갈 수 없다. A에서 D로 간다.`,[out(best),...routes.filter(p=>p!==best).map(out),'A→D (1분)'],`가능한 세 경로의 시간은 ${routes.map(out).join(', ')}이다. 가장 작은 합의 경로가 답이다.`,()=>{const walk=(node,cost,visited)=>node==='D'?[{path:visited,cost}]:Object.entries(costs).filter(([e])=>e[0]===node).flatMap(([e,c])=>walk(e[1],cost+c,[...visited,e[1]]));const all=walk('A',0,['A']).sort((a,b)=>a.cost-b.cost);assert(all[0].cost<all[1].cost);return `${all[0].path.join('→')} (${all[0].cost}분)`;});
}
for(let i=0;i<5;i++) {
  const a=3+i,b=5+i,c=2+i,d=4+i;
  const total=a+Math.max(b,c)+d;
  logic('dependency-time','병렬 작업의 완료 시점','전체 작업의 최소 완료 시간은?',`${contexts[i]}에서 A(${a}시간)를 마친 뒤 B(${b}시간)와 C(${c}시간)를 서로 다른 담당자가 동시에 시작할 수 있다. D(${d}시간)는 B와 C가 모두 끝난 뒤 시작한다. 준비 시간은 없고 중단 없이 수행한다.`,[`${total}시간`,`${a+b+c+d}시간`,`${a+c+d}시간`,`${Math.max(a,b,c,d)}시간`],`A 이후 B와 C의 긴 작업이 끝날 때까지 기다린다. ${a}+max(${b},${c})+${d}=${total}시간이다.`,()=>{const finishA=a,finishB=finishA+b,finishC=finishA+c,finishD=Math.max(finishB,finishC)+d;return `${finishD}시간`;});
}
for(let i=0;i<5;i++) {
  const tasks=['요청','확인','승인']; const cycleEdges=[['요청','확인'],['확인','승인'],['승인','요청']];
  logic('dependency-cycle','선행 조건의 모순','업무가 시작되지 않는 핵심 이유는?',`${contexts[i]} 업무에서 확인은 요청 후, 승인은 확인 후, 요청은 승인 후에만 시작할 수 있다. 이미 완료된 단계는 없고 예외도 없다.`,['세 단계의 선행 관계가 순환하여 시작 가능한 단계가 없다.','확인과 승인을 동시에 하면 모든 선행 조건을 만족한다.','담당자 수만 늘리면 현재 규칙 그대로 시작할 수 있다.','요청부터 시작해도 모든 선행 조건이 지켜진다.'],'요청→확인→승인→요청 순환 때문에 각 단계가 아직 완료되지 않은 다른 단계를 기다린다. 규칙을 수정하거나 시작 예외를 정해야 한다.',()=>{const available=tasks.filter(t=>!cycleEdges.some(([,to])=>to===t));assert.equal(available.length,0);return '세 단계의 선행 관계가 순환하여 시작 가능한 단계가 없다.';});
}
const assumptions=[
 ['예약 가능 시간을 늘리면 이용자가 편리해질 것이다.','늘어난 시간에 실제로 예약을 원하는 이용자가 있다.','예약 화면 글자 색상이 반드시 바뀐다.','예약 건수가 정확히 두 배가 된다.','모든 이용자가 같은 시간만 선호한다.'],
 ['자동 점검을 추가하면 담당자의 반복 업무가 줄 것이다.','자동 점검 결과를 업무에서 활용할 수 있다.','점검 장비의 이름이 짧아진다.','수동 점검이 법적으로 모두 금지된다.','담당자는 새로운 도구를 전혀 사용하지 않는다.'],
 ['기초 용어 설명을 추가하면 초보자의 이해가 나아질 것이다.','설명할 용어가 초보자가 어려워하는 내용과 관련이 있다.','모든 참가자가 이미 전문가이다.','설명 자료가 반드시 한 장이어야 한다.','교육 장소가 더 넓어진다.'],
 ['검색 기준을 통일하면 원하는 문서를 찾기 쉬워질 것이다.','이용자가 통일된 기준을 알고 적용할 수 있다.','문서의 내용을 모두 공개한다.','파일 수를 반드시 절반으로 줄인다.','검색은 앞으로 전혀 하지 않는다.'],
 ['설명회 전에 교통편을 안내하면 지각을 줄일 수 있을 것이다.','일부 지각이 이동 경로 정보 부족과 관련이 있다.','모든 기업의 사무실 위치가 같다.','행사 시간을 반드시 밤으로 바꾼다.','교통편 안내가 모든 사고를 예방한다.']
];
assumptions.forEach(([claim,good,...bad])=>logic('necessary-assumption','제안이 성립하는 핵심 가정','제안의 논리 연결에 필요한 가정으로 가장 적절한 것은?',`제안: “${claim}” 제시된 조치와 예상 효과를 연결하는 전제를 찾는다.`,[good,...bad],'조치가 예상 효과에 영향을 줄 수 있는 연결 조건이 필요하다. 부수적인 변화, 과도한 보장, 효과를 부정하는 조건은 핵심 가정이 아니다.'));
const universal=[
 ['모든 접수 오류는 서류 누락 때문에 생긴다.','서류가 완비되었는데 접수 번호 중복으로 오류가 난 사례'],
 ['모든 장비 장애는 케이블 문제 때문에 생긴다.','정상 케이블을 사용했는데 전원 장치 고장으로 장애가 난 사례'],
 ['모든 교육 미이수자는 출석 시간이 부족하다.','출석 기준을 충족했지만 필수 평가를 보지 않아 미이수된 사례'],
 ['모든 검색 실패는 파일이 없기 때문에 생긴다.','파일이 존재하지만 권한이 없어 검색에서 보이지 않은 사례'],
 ['모든 행사 불참 기업은 장소를 몰랐다.','장소를 정확히 알았지만 갑작스러운 업무로 불참한 기업 사례']
];
universal.forEach(([claim,counter])=>logic('counterexample','전칭 주장의 반례','이 주장을 반박하는 사례는?',`검토할 주장: “${claim}”`,[counter,'주장이 설명하는 원인으로 실제 문제가 생긴 사례','원인과 결과를 모두 조사하지 않은 사례','문제가 생기지 않은 사례만 있는 자료'],'“모든”이라는 주장은 결과가 있으면서 제시한 원인이 없는 사례 하나로 반박된다. 주장에 맞는 사례를 추가하는 것은 반례가 아니다.'));
const hypotheses=[
 ['일부 예약만 확인 메시지를 받지 못했다.','실패 건 모두 같은 번호 형식을 사용했으며 정상 건에는 그 형식이 없다.','해당 번호 형식의 처리 규칙을 우선 재현 시험한다.'],
 ['한 종류의 장비만 재부팅 후 연결이 끊겼다.','끊긴 장비는 같은 드라이버 버전을 사용하며 다른 버전은 정상이다.','동일 장비에서 드라이버 버전만 바꾸어 비교한다.'],
 ['특정 과정의 수료 기록만 늦게 나타났다.','해당 과정만 다른 연계 작업 시간표를 사용한다.','연계 시간표와 실제 실행 이력을 대조한다.'],
 ['특정 폴더의 문서만 검색에서 누락되었다.','그 폴더만 최근 권한 설정을 바꾸었다.','파일 존재와 권한·색인 반영 여부를 함께 확인한다.'],
 ['일부 기업의 초청 메일만 반송되었다.','반송 기업의 주소는 모두 이전 명단에서 가져왔다.','최신 연락처와 반송 주소를 대조한다.']
];
hypotheses.forEach(([symptom,pattern,good])=>logic('testable-hypothesis','관찰에서 검증 계획 만들기','관찰 자료를 바탕으로 한 다음 검증으로 가장 적절한 것은?',`${symptom} ${pattern} 아직 원인은 확정하지 않았다.`,[good,'담당자 이름을 바꾸고 원인 조사를 끝낸다.','관찰된 차이와 관계없는 문서 색상을 바꾼다.','상관관계만으로 원인을 이미 증명했다고 선언한다.'],'실패와 정상 사례의 차이를 구체적인 재현·대조 시험으로 검증해야 한다. 관찰된 관련성을 곧바로 인과 확정으로 바꾸면 안 된다.'));
for(let i=0;i<5;i++) {
  const n=7+3*i, threshold=10+i, result=n<threshold?n+5:n-3;
  logic('flowchart-trace','조건 분기 추적','절차 실행 후 값은?',`${contexts[i]} 분류 코드 x의 초깃값은 ${n}이다.\n① x가 ${threshold}보다 작으면 x에 5를 더하고, 아니면 3을 뺀다.\n② 변경된 x를 결과로 출력한다.\n분기는 한 번만 실행한다.`,[String(result),String(n),String(n<threshold?n-3:n+5),String(n+10)],`초깃값 ${n}과 기준 ${threshold}을 비교하면 ${n<threshold?'작으므로 5를 더한다':'작지 않으므로 3을 뺀다'}. 결과는 ${result}이다.`,()=>{let value=n;if(value<threshold)value+=5;else value-=3;return String(value);},'기초');
}
for(let i=0;i<5;i++) {
  const complete=i!==0, verifyOk=i%2===0, category=complete?(verifyOk?'즉시 접수':'확인 대기'):'서류 보완';
  const labels=['즉시 접수','확인 대기','서류 보완','무조건 반려'];
  logic('decision-table','두 조건의 결정표','현재 대상의 처리 상태는?',`${contexts[i]} 규칙: 서류가 완비되고 확인이 끝나면 즉시 접수, 서류가 완비되었으나 확인이 안 끝나면 확인 대기, 서류가 빠졌으면 확인 여부와 관계없이 서류 보완이다.\n현재 대상: 서류 ${complete?'완비':'누락'}, 확인 ${verifyOk?'완료':'미완료'}.`,[category,...labels.filter(x=>x!==category)],'서류 완비 여부를 먼저 확인한다. 완비된 경우에만 확인 완료 여부에 따라 접수 또는 대기로 나눈다.',()=>{const table=new Map([['0,0','서류 보완'],['0,1','서류 보완'],['1,0','확인 대기'],['1,1','즉시 접수']]);return table.get(`${Number(complete)},${Number(verifyOk)}`);},'기초');
}
for(let i=0;i<5;i++) {
  const m=[[5+i,9+i],[7+i,7+i],[3+i,12+i]];
  const worst=m.map(xs=>Math.max(...xs)), idx=worst.indexOf(Math.min(...worst));
  const opts=['A안','B안','C안','어느 안이든 최악 시간이 같다'];
  logic('minimax-choice','최악 상황을 줄이는 선택','최악의 처리 시간을 최소화하는 안은?',`서로 다른 두 상황 중 어느 것이 올지 모른다. ${contexts[i]} 처리 시간(분)은 A안 [${m[0]}], B안 [${m[1]}], C안 [${m[2]}]이다. 발생 확률은 주어지지 않았고 가장 느린 상황의 시간을 최소화하려고 한다.`,[opts[idx],...opts.filter((_,j)=>j!==idx)],`각 안의 최악 시간은 A ${worst[0]}, B ${worst[1]}, C ${worst[2]}분이다. 그중 최소인 ${opts[idx]}를 선택한다. 평균이나 최고 속도가 기준이 아니다.`,()=>{const rowMaximum=m.map(row=>row.reduce((a,b)=>a>b?a:b));const min=rowMaximum.reduce((a,b)=>a<b?a:b);return opts[rowMaximum.indexOf(min)];},'심화');
}
for(let i=0;i<5;i++) {
  const required=['실시간 기록','권한 통제','복구 기능'], plans=[{label:'A안',features:[true,true,false],cost:5+i},{label:'B안',features:[true,false,true],cost:4+i},{label:'C안',features:[true,true,true],cost:8+i},{label:'D안',features:[true,true,true],cost:10+i}];
  logic('feasibility-first','필수 조건과 비용 비교','필수 조건을 모두 충족하면서 비용이 가장 낮은 안은?',`${contexts[i]} 개선안은 ${required.join(', ')} 기능을 모두 갖춰야 한다.\n${plans.map(p=>`${p.label}: ${required.map((r,k)=>`${r} ${p.features[k]?'있음':'없음'}`).join(', ')}, 비용 ${p.cost}단위`).join('\n')}`,['C안','A안','B안','D안'],'필수 기능이 빠진 A와 B는 비용이 낮아도 제외한다. C와 D 중 비용이 작은 C가 답이다.',()=>{const feasible=plans.filter(p=>p.features.every(Boolean)).sort((a,b)=>a.cost-b.cost);assert(feasible[0].cost<feasible[1].cost);return feasible[0].label;});
}
for(let i=0;i<5;i++) {
  const labels=['상담','점검','교육','기록','행사'], start=[labels[i],labels[(i+1)%5],labels[(i+2)%5]], steps=2+i;
  let out=[...start];for(let k=0;k<steps;k++)out=[out[2],out[0],out[1]];
  const expected=out.join(' / '), wrong=permutations(start).map(p=>p.join(' / ')).filter(x=>x!==expected).slice(0,3);
  logic('rotation-rule','자리 이동 규칙','규칙을 적용한 뒤 왼쪽부터 배열은?',`처음 배열은 [${start.join(' / ')}]이다. 한 번 이동할 때 맨 오른쪽 항목을 맨 왼쪽으로 옮기고 나머지는 한 칸 오른쪽으로 이동한다. 이 규칙을 ${steps}번 적용한다.`,[expected,...wrong],`세 항목이므로 세 번 이동하면 원상태다. ${steps}번은 ${steps%3}번 이동과 같으며 결과는 ${expected}이다.`,()=>{const count=steps%start.length;return start.map((_,k)=>start[(k-count+start.length)%start.length]).join(' / ');},'기초');
}
function numeric(category,family,title,prompt,value,distractors,why,solve,unit='',extras={}) {
  const formatted = n => `${fmt(round(n))}${unit}`;
  const good=formatted(value), wrong=[];
  for(const n of distractors) {const s=formatted(n);if(s!==good&&!wrong.includes(s))wrong.push(s);}
  for(let d=1;wrong.length<3;d++) {const s=formatted(value+d);if(s!==good&&!wrong.includes(s))wrong.push(s);}
  add(category,family,title,prompt,[good,...wrong.slice(0,3)],why,extras,0,()=>formatted(solve()));
}
const math=(...args)=>numeric(categories[2],...args);
for(let i=0;i<5;i++) {
  const old=120+40*i, rate=[15,20,25,30,35][i], current=old*(1+rate/100);
  math('percentage-base','증가율의 기준',`${contexts[i]}의 처리 건수가 ${fmt(old)}건에서 ${fmt(current)}건으로 늘었다. 이전 건수를 기준으로 한 증가율은?`,rate,[(current-old)/current*100,rate+5,current-old],`증가량 ${fmt(current-old)}을 이전 ${old}로 나누면 ${rate}%다. 증가 후 수량을 분모로 쓰지 않는다.`,()=>current/old*100-100,'%');
}
for(let i=0;i<5;i++) {
  const up=10+5*i, down=up, initial=1000+500*i, end=initial*(1+up/100)*(1-down/100), change=(end-initial)/initial*100;
  math('successive-percent','연속 증감의 복합 효과',`${contexts[i]} 업무량이 ${up}% 증가한 뒤 증가한 수량을 기준으로 ${down}% 감소했다. 처음과 비교한 최종 변화율은? 음수는 감소를 뜻한다.`,change,[0,-up,up-down+1],`최종 배율은 (1+${up}/100)×(1−${down}/100)=${round(end/initial)}이다. 같은 비율의 증감이어도 기준이 달라 ${round(change)}% 변화한다.`,()=>((100+up)*(100-down)-10000)/100,'%');
}
for(let i=0;i<5;i++) {
  const nA=10+5*i,nB=30-2*i,tA=4+i,tB=10+i,result=(nA*tA+nB*tB)/(nA+nB);
  math('weighted-mean','가중 평균 처리 시간',`${contexts[i]} A반은 ${nA}건을 건당 평균 ${tA}분, B반은 ${nB}건을 건당 평균 ${tB}분에 처리했다. 전체 건당 평균 시간은? 소수는 최대 여섯 자리로 반올림한다.`,result,[(tA+tB)/2,result+1,tA+tB],`총 시간 ${nA*tA+nB*tB}분을 총 ${nA+nB}건으로 나누면 ${fmt(result)}분이다.`,()=>{const samples=[...Array(nA).fill(tA),...Array(nB).fill(tB)];return sum(samples)/samples.length;},'분');
}
for(let i=0;i<5;i++) {
  const fast=3+i,slow=2+i,work=(fast+slow)*(4+i),result=work/(fast+slow);
  math('work-rate','동시 작업의 처리율',`가상의 ${contexts[i]}에서 A는 시간당 ${fast}건, B는 시간당 ${slow}건을 처리한다. 서로 간섭하지 않고 함께 ${work}건을 처리하면 필요한 시간은?`,result,[work/fast,work/slow,fast+slow],`두 사람의 처리율을 더하면 시간당 ${fast+slow}건이다. ${work}÷${fast+slow}=${result}시간이다.`,()=>{let done=0,h=0;while(done<work){done+=fast+slow;h++;}assert.equal(done,work);return h;},'시간');
}
for(let i=0;i<5;i++) {
  const a=2+i,b=3+i,total=(a+b)*(12+i),first=total*a/(a+b);
  math('ratio-allocation','비율에 따른 분배',`${contexts[i]} 자료 ${total}건을 A와 B에 ${a}:${b} 비율로 나누려고 한다. A에 배정할 수량은?`,first,[total*b/(a+b),total/a,total/(a+b)],`전체를 ${a+b}비율 단위로 나누면 한 단위는 ${total/(a+b)}건이다. A는 ${a}단위이므로 ${first}건이다.`,()=>{for(let x=0;x<=total;x++)if(x*b===(total-x)*a)return x;throw Error('no allocation');},'건');
}
for(let i=0;i<5;i++) {
  const red=3+i,blue=4+i,total=red+blue,result=red*(red-1)/(total*(total-1))*100;
  math('sampling-no-replacement','비복원 추출 확률',`검토 카드 ${total}장 중 재확인 표시 카드는 ${red}장, 일반 카드는 ${blue}장이다. 임의로 두 장을 차례로 뽑고 첫 장을 돌려놓지 않는다. 두 장 모두 재확인 표시일 확률은? 소수는 최대 여섯 자리로 반올림한다.`,result,[red/total*red/total*100,red/total*100,(red-1)/(total-1)*100],`첫 장 확률 ${red}/${total}와 두 번째 조건부 확률 ${red-1}/${total-1}을 곱하면 ${fmt(result)}%이다.`,()=>{let all=0,favorable=0;for(let a=0;a<total;a++)for(let b=0;b<total;b++){if(a===b)continue;all++;if(a<red&&b<red)favorable++;}return favorable/all*100;},'%',{difficulty:'심화'});
}
for(let i=0;i<5;i++) {
  const approved=30+10*i,verified=12+4*i,total=80+20*i,result=verified/approved*100;
  math('conditional-proportion','조건부 비율의 분모',`가상의 ${contexts[i]} 전체 ${total}건 중 승인 건은 ${approved}건이다. 승인 건 중 추가 확인을 거친 건은 ${verified}건이다. 승인된 건을 하나 고를 때 추가 확인을 거쳤을 비율은?`,result,[verified/total*100,approved/total*100,(approved-verified)/approved*100],`이미 승인된 범위로 한정했으므로 분모는 ${approved}건이다. ${verified}÷${approved}×100=${fmt(result)}%이다.`,()=>{const approvedFlags=Array.from({length:approved},(_,k)=>k<verified);return approvedFlags.filter(Boolean).length/approvedFlags.length*100;},'%');
}
for(let i=0;i<5;i++) {
  const scores=[65+i*2,75+i,80+i,90+i*2],missing=70+i*3,target=(sum(scores)+missing)/5;
  math('missing-mean','평균에서 누락값 역산',`가상 교육 점수 다섯 개의 평균은 ${target}점이다. 확인된 네 점수는 ${scores.join(', ')}점이다. 누락된 점수는?`,missing,[target,sum(scores)/4,missing+10],`다섯 점수 합은 ${target}×5=${target*5}이다. 알려진 합 ${sum(scores)}를 빼면 ${missing}점이다.`,()=>{for(let n=0;n<=100;n++)if(round((sum(scores)+n)/5)===round(target))return n;throw Error('no missing score');},'점');
}
for(let i=0;i<5;i++) {
  const raw=[12+i,3+i,20+i,7+i,9+i],sorted=[...raw].sort((a,b)=>a-b),median=sorted[2];
  math('median-outlier','중앙값과 정렬',`${contexts[i]} 다섯 건의 처리 시간은 ${raw.join(', ')}분이다. 중앙값은?`,median,[sum(raw)/5,sorted[1],sorted[3]],`시간을 정렬하면 ${sorted.join(', ')}이다. 다섯 값의 가운데인 세 번째 값 ${median}분을 선택한다.`,()=>{const candidates=raw.filter(v=>raw.filter(x=>x<v).length===2&&raw.filter(x=>x>v).length===2);assert.equal(candidates.length,1);return candidates[0];},'분',{difficulty:'기초'});
}
for(let i=0;i<5;i++) {
  const minutes=75+15*i,result=minutes/60,unitCost=1200+300*i,total=result*unitCost;
  math('time-unit','시간 단위와 금액 환산',`${contexts[i]} 장소 사용료는 시간당 ${unitCost}원이며 분 단위로 비례 계산한다. ${minutes}분 사용한 요금은? 추가 요금은 없다.`,total,[minutes*unitCost,total+unitCost,(minutes%60)*unitCost/60],`${minutes}분은 ${fmt(result)}시간이다. ${fmt(result)}×${unitCost}=${fmt(total)}원이다.`,()=>minutes*(unitCost/60),'원',{difficulty:'기초'});
}
for(let i=0;i<5;i++) {
  const fixed=1200+400*i,variable=100,other=140,breakEven=fixed/(other-variable);
  math('break-even','고정비와 변동비의 손익분기',`${contexts[i]} 출력 업체 A는 기본료 ${fixed}원과 건당 ${variable}원, B는 기본료 없이 건당 ${other}원이다. 두 업체 총비용이 같은 건수는?`,breakEven,[fixed/(variable+other),breakEven+10,fixed/other],`${fixed}+${variable}x=${other}x이므로 x=${fixed}/40=${breakEven}건이다.`,()=>{for(let x=0;x<1000;x++)if(fixed+variable*x===other*x)return x;throw Error('no break even');},'건');
}
for(let i=0;i<5;i++) {
  const distance=60+30*i,v1=30+10*i,v2=60+20*i,result=2*distance/(distance/v1+distance/v2);
  math('round-trip-speed','왕복 평균 속력',`현장 방문에서 같은 거리 ${distance}km를 갈 때 시속 ${v1}km, 돌아올 때 시속 ${v2}km로 이동했다. 정차 시간은 없다. 왕복 평균 속력은?`,result,[(v1+v2)/2,v1+v2,result+10],`총거리 ${2*distance}km를 총시간 ${fmt(distance/v1+distance/v2)}시간으로 나누면 시속 ${fmt(result)}km이다. 속력의 산술평균은 시간이 다른 왕복에 맞지 않는다.`,()=>2*v1*v2/(v1+v2),'km/h');
}
for(let i=0;i<5;i++) {
  const start=25+5*i,incoming=[12+i,18+i,9+i],outgoing=[10+i,15+i,11+i],end=start+sum(incoming)-sum(outgoing);
  math('balance-flow','누적 유입·처리 잔량',`${contexts[i]}의 월요일 시작 미처리량은 ${start}건이다. 월·화·수 신규 접수는 ${incoming.join(', ')}건, 같은 날 처리 완료는 ${outgoing.join(', ')}건이다. 재개통이나 취소는 없다. 수요일 종료 미처리량은?`,end,[start+sum(incoming),sum(incoming)-sum(outgoing),start+sum(outgoing)-sum(incoming)],`미처리량=처음 ${start}+신규 ${sum(incoming)}−처리 ${sum(outgoing)}=${end}건이다.`,()=>{let backlog=start;for(let day=0;day<3;day++){backlog+=incoming[day];backlog-=outgoing[day];}return backlog;},'건');
}
for(let i=0;i<5;i++) {
  const base=10000+5000*i,rate=10,years=2+i%2,result=base*(1+rate/100)**years;
  math('compound-growth','누적 성장률 계산',`가상의 자료 저장량이 현재 ${fmt(base)}MB이며 매년 직전 연도 말 저장량의 ${rate}%씩 증가한다고 가정한다. 삭제는 없다. ${years}년 뒤 저장량은?`,result,[base*(1+rate/100*years),base*(1+rate/100),result+base*0.1],`각 해의 증가 기준이 달라 ${base}×1.1^${years}=${fmt(result)}MB이다. 이는 주어진 성장 가정에 따른 계산이다.`,()=>{let storage=base;for(let y=0;y<years;y++)storage+=storage*rate/100;return storage;},'MB');
}
for(let i=0;i<5;i++) {
  const base=80+20*i,current=100+25*i,index=current/base*100;
  math('base-index','기준 연도의 지수',`${contexts[i]} 실적은 기준 연도 ${base}건, 올해 ${current}건이다. 기준 연도를 100으로 놓은 올해 지수는?`,index,[current-base,(current-base)/base*100,index+25],`지수는 올해 실적÷기준 실적×100이다. ${current}÷${base}×100=${index}이며 증가율 ${index-100}%와 구분한다.`,()=>{const unit=base/100;return current/unit;});
}
for(let i=0;i<5;i++) {
  const data=[{label:'A',total:50+10*i,good:40+8*i},{label:'B',total:30+5*i,good:27+4.5*i},{label:'C',total:100+20*i,good:70+14*i}];
  // Keep records integral while preserving rates 80%, 90%, 70%.
  data[1]={label:'B',total:40+10*i,good:36+9*i};
  const correct='B팀';
  add(categories[2],'rate-ranking','표의 비율 비교','처리 완료율이 가장 높은 팀은?',[correct,'A팀','C팀','완료 건수가 가장 많은 팀이 항상 완료율도 가장 높다.'],`A 80%, B 90%, C 70%로 분모가 다른 팀들을 비율로 비교하면 B가 가장 높다.`,{passage:data.map(d=>`${d.label}팀: 접수 ${d.total}건 / 완료 ${d.good}건`).join('\n')},0,()=>data.reduce((a,b)=>a.good/a.total>b.good/b.total?a:b).label+'팀');
}
for(let i=0;i<5;i++) {
  const low=10+i*2,high=30+i*2,a=4+i,b=6+i,total=a+b,result=(low*a+high*b)/total;
  math('mixture-weight','두 집단을 합친 평균',`가상 ${contexts[i]}에서 단순 건 ${a}건은 평균 ${low}분, 복잡 건 ${b}건은 평균 ${high}분이 필요하다. 두 종류를 합한 ${total}건의 평균 필요 시간은? 소수는 최대 여섯 자리로 반올림한다.`,result,[(low+high)/2,low+high,result+2],`유형별 총 필요 시간 ${low*a}분과 ${high*b}분을 더한 뒤 전체 ${total}건으로 나누면 ${fmt(result)}분이다.`,()=>low+(high-low)*(b/total),'분');
}
for(let i=0;i<5;i++) {
  const n=5+i,result=n*(n-1)/2;
  math('choose-two','순서 없는 조합',`가상 ${contexts[i]} 검토자 ${n}명 중 서로 다른 두 명을 공동 검토자로 뽑는다. 두 사람의 역할은 같아 순서는 구분하지 않는다. 가능한 조합 수는?`,result,[n*(n-1),n*n,n+1],`순서를 구분한 선택 n(n−1)을 두 번씩 중복 세므로 2로 나눈다. ${n}×${n-1}÷2=${result}가지이다.`,()=>{let count=0;for(let a=0;a<n;a++)for(let b=a+1;b<n;b++)count++;return count;},'가지');
}
for(let i=0;i<5;i++) {
  const first=18+4*i,step=3+i,nth=6,last=first+(nth-1)*step;
  math('arithmetic-sequence','등차 증가 가정',`${contexts[i]}의 주간 예상량은 1주 차 ${first}건이며 매주 직전 주보다 정확히 ${step}건씩 늘어난다고 가정한다. 6주 차 예상량은?`,last,[first+nth*step,first*6,last-step],`1주 차에서 6주 차까지 증가는 다섯 번이므로 ${first}+5×${step}=${last}건이다. 현실 예측이 아니라 제시한 등차 증가 가정의 계산이다.`,()=>{let value=first;for(let week=2;week<=nth;week++)value+=step;return value;},'건',{difficulty:'기초'});
}
const resource=(...args)=>numeric(categories[3],...args);
function planning(family,title,prompt,passage,options,why,verify,difficulty='보통') {
  add(categories[3],family,title,prompt,options,why,{passage,difficulty},0,verify);
}
for(let i=0;i<5;i++) {
  const scale=i+1,budget=9*scale,projects=[{n:'A',c:6*scale,v:7},{n:'B',c:4*scale,v:6},{n:'C',c:3*scale,v:5},{n:'D',c:5*scale,v:8}];
  const feasible=subsets(projects).filter(s=>sum(s.map(p=>p.c))<=budget).sort((a,b)=>sum(b.map(p=>p.v))-sum(a.map(p=>p.v)));
  assert(sum(feasible[0].map(p=>p.v))>sum(feasible[1].map(p=>p.v)));
  const label=s=>s.map(p=>p.n).sort().join('+'),best=label(feasible[0]);
  planning('budget-benefit-subset','예산 안에서 편익 최대화','총편익이 가장 큰 사업 조합은?',`${contexts[i]} 개선사업을 중복 없이 선택한다. 사업은 쪼갤 수 없고 편익은 합산된다. 예산은 ${budget}단위다.\n${projects.map(p=>`${p.n}: 비용 ${p.c}, 편익 ${p.v}`).join('\n')}`,[best,'A+C','B+C','C+D'],`B+D의 비용은 ${9*scale}, 편익은 14다. A+C는 12, B+C는 11, C+D는 13이며 다른 예산 내 조합도 14를 넘지 않는다.`,()=>{let max=-1,result='';for(let mask=0;mask<16;mask++){let cost=0,value=0,list=[];for(let j=0;j<4;j++)if(mask&(1<<j)){cost+=projects[j].c;value+=projects[j].v;list.push(projects[j].n);}if(cost<=budget&&value>max){max=value;result=list.sort().join('+');}}return result;},'심화');
}
for(let i=0;i<5;i++) {
  const capacity=5+i,work=17+4*i,need=Math.ceil(work/capacity);
  resource('staff-capacity','처리 능력에 따른 최소 인력',`${contexts[i]} 업무 ${work}건을 한 시간 안에 끝내야 한다. 직원 한 명은 같은 시간에 최대 ${capacity}건 처리한다. 업무는 건 단위로 배정하고 다른 준비 시간은 없다. 필요한 최소 인원은?`,need,[Math.floor(work/capacity),need+1,capacity],`필요 인원은 ${work}÷${capacity}를 올림한 ${need}명이다. ${need-1}명의 최대 처리량은 ${(need-1)*capacity}건으로 부족하다.`,()=>{let people=0;while(people*capacity<work)people++;return people;},'명');
}
for(let i=0;i<5;i++) {
  const offset=i*5,slots=[[0,30],[10,40],[20,50],[45,60]].map(([a,b])=>[a+offset,b+offset]),peak=3;
  resource('overlapping-bookings','동시 예약과 공간 수',`회의 네 건의 예약 구간(분)은 ${slots.map(([a,b])=>`[${a}, ${b})`).join(', ')}이다. 시작 시각은 포함하고 종료 시각은 제외한다. 한 회의실에서 겹치는 회의를 받을 수 없다. 필요한 최소 회의실 수는?`,peak,[2,4,1],`세 회의가 동시에 진행되는 구간이 있어 최소 3실이다. 네 번째 회의는 처음 두 회의가 끝난 뒤 시작하므로 기존 회의실을 재사용할 수 있다.`,()=>{let max=0;for(let t=0;t<100;t++)max=Math.max(max,slots.filter(([a,b])=>a<=t&&t<b).length);return max;},'실');
}
for(let i=0;i<5;i++) {
  const daily=8+2*i,days=4,stock=35+5*i,safety=10+2*i,ordered=6+i,needed=Math.max(0,daily*days+safety-stock-ordered);
  resource('stock-safety-order','안전 재고와 추가 주문',`${contexts[i]}용 소모품은 하루 ${daily}개씩 필요하다. 앞으로 ${days}일을 지나도 안전 재고 ${safety}개를 남겨야 한다. 현재 재고 ${stock}개와 기간 시작 전에 도착하는 확정 주문 ${ordered}개가 있다. 추가로 주문할 최소 수량은?`,needed,[daily*days-stock,daily*days+safety-stock,needed+safety],`기간 수요 ${daily*days}개+안전 재고 ${safety}개−현재 ${stock}개−확정 입고 ${ordered}개=${needed}개이다.`,()=>{let order=0;while(stock+ordered+order-daily*days<safety)order++;return order;},'개');
}
for(let i=0;i<5;i++) {
  const count=30+20*i,costs=[{n:'A업체',base:1000,unit:120},{n:'B업체',base:2500,unit:70},{n:'C업체',base:0,unit:150},{n:'D업체',base:4000,unit:60}];
  const totals=costs.map(c=>c.base+c.unit*count),min=Math.min(...totals),idx=totals.indexOf(min);assert.equal(totals.filter(x=>x===min).length,1);
  planning('vendor-total-cost','견적의 총비용 비교','총비용이 가장 낮은 업체는?',`${contexts[i]} 자료 ${count}부를 제작한다. 품질·납기 조건은 모두 같다.\n${costs.map(c=>`${c.n}: 기본료 ${c.base}원, 부당 ${c.unit}원`).join('\n')}\n다른 비용은 없다.`,[costs[idx].n,...costs.filter((_,j)=>j!==idx).map(c=>c.n)],`총비용은 ${costs.map((c,j)=>`${c.n} ${fmt(totals[j])}원`).join(', ')}이다. 단가만 보지 말고 기본료도 더해야 한다.`,()=>{const ranked=costs.map(c=>({name:c.n,total:sum([c.base,...Array(count).fill(c.unit)])})).sort((a,b)=>a.total-b.total);return ranked[0].name;});
}
for(let i=0;i<5;i++) {
  const assigned=2+i,per=12,required=55+10*i,extra=Math.max(0,Math.ceil(required/per)-assigned);
  resource('additional-staff','기존 자원을 반영한 증원',`${contexts[i]} ${required}건을 오늘 처리해야 한다. 직원 한 명의 오늘 최대 처리량은 ${per}건이고 이미 ${assigned}명이 배정되어 있다. 기존 직원도 같은 능력이다. 최소 몇 명을 추가 배정해야 하는가?`,extra,[Math.ceil(required/per),extra+1,Math.floor(required/per)-assigned],`전체 필요 인원은 ceil(${required}/12)=${Math.ceil(required/per)}명이다. 기존 ${assigned}명을 빼면 추가 ${extra}명이다.`,()=>{let x=0;while((assigned+x)*per<required)x++;return x;},'명');
}
const urgent=[
 ['상담 시스템이 중단되어 지금 접수 고객이 전혀 신청할 수 없다.','운영 장애에 즉시 대응하면서 고객에게 확인된 영향과 안내 시간을 알린다.'],
 ['오늘 마감하는 외부 제출 자료에서 누락 항목이 발견되었다.','누락 범위를 확인해 제출 기한 안에 필수 항목을 보완한다.'],
 ['교육 시작 30분 전 강의실 예약 중복이 확인되었다.','대체 공간과 안내를 즉시 조정해 교육 운영 차질을 줄인다.'],
 ['공개 예정 문서에 접근 제한 정보가 포함되었다.','공개를 잠시 멈추고 담당자 검토로 제한 정보를 제거한다.'],
 ['행사 시작 직전 안전 통로에 물품이 쌓여 이동을 막고 있다.','통로의 물품을 즉시 치우고 안전한 이동을 확보한다.']
];
urgent.forEach(([situation,good])=>planning('urgent-important','긴급성과 중요성에 따른 우선순위','제시된 상황에서 우선 조치는?',`${situation} 동시에 다음 달 홍보물 색상 선택, 정기 회의 간식 주문, 개인 책상 정리도 대기 중이다.`,[good,'다음 달 홍보물 색상만 먼저 결정한다.','간식 주문을 끝낼 때까지 상황 확인을 미룬다.','개인 책상 정리 후 중요 업무를 확인한다.'],'현재 고객·마감·운영·정보·안전에 직접 영향이 있는 긴급하고 중요한 문제를 우선 처리한다.'));
for(let i=0;i<5;i++) {
  const cap=[20+4*i,14+3*i,18+4*i],max=Math.min(...cap);
  resource('process-bottleneck','처리 공정의 병목',`${contexts[i]}의 세 단계 처리 능력은 시간당 접수 ${cap[0]}건, 검토 ${cap[1]}건, 확정 ${cap[2]}건이다. 모든 건은 세 단계를 거치며 장기간 안정적으로 운영한다. 충분한 수요가 있을 때 전체의 시간당 최대 완료량은?`,max,[Math.max(...cap),sum(cap),sum(cap)/3],`전체 흐름은 가장 낮은 단계 처리량 ${max}건/시간에 제한된다. 빠른 다른 단계의 능력을 더해도 병목을 넘을 수 없다.`,()=>{let feasible=0;for(let rate=0;rate<=100;rate++)if(cap.every(c=>c>=rate))feasible=rate;return feasible;},'건');
}
for(let i=0;i<5;i++) {
  const deadline=16*60,start=9*60+i*15,duration=240+i*10,buffer=30,latest=deadline-duration-buffer,slack=latest-start;
  resource('deadline-slack','마감과 여유 시간',`${contexts[i]} 작업은 오늘 16:00까지 끝내야 한다. 작업에 ${duration}분, 완료 후 검토에 ${buffer}분이 필요하다. ${Math.floor(start/60)}:${String(start%60).padStart(2,'0')}에 시작할 수 있을 때 시작을 미룰 수 있는 최대 시간은?`,slack,[deadline-start-duration,deadline-start,slack+buffer],`작업과 검토를 합하면 ${duration+buffer}분이다. 시작 가능 시각부터 마감까지 ${deadline-start}분이므로 여유는 ${slack}분이다.`,()=>{let delay=0;while(start+delay+duration+buffer<=deadline)delay++;return delay-1;},'분');
}
for(let i=0;i<5;i++) {
  const need=73+11*i,pack=20,boxes=Math.ceil(need/pack);
  resource('indivisible-batch','묶음 구매와 최소 수량',`${contexts[i]}에 소모품 ${need}개가 필요하다. 한 상자에는 ${pack}개가 들어 있고 상자 단위로만 구매할 수 있다. 현재 재고는 없다. 최소 구매 상자 수는?`,boxes,[Math.floor(need/pack),boxes+1,need],`필요량을 상자 크기로 나눈 값을 올림한다. ${boxes-1}상자는 ${(boxes-1)*pack}개로 부족하고 ${boxes}상자는 ${boxes*pack}개로 충족한다.`,()=>{for(let n=0;n<100;n++)if(n*pack>=need)return n;throw Error('no boxes');},'상자',{difficulty:'기초'});
}
for(let i=0;i<5;i++) {
  const total=100+20*i,committed=45+5*i,minReserve=15+3*i,available=total-committed-minReserve;
  resource('earmarked-budget','확정 지출과 예비비',`${contexts[i]} 예산은 ${total}만원이다. 계약상 확정 지출은 ${committed}만원이고 최소 예비비 ${minReserve}만원을 남겨야 한다. 신규 사업에 배정할 수 있는 최대 금액은?`,available,[total-committed,total-minReserve,committed+minReserve],`확정 지출과 최소 예비비를 먼저 제외하면 ${total}−${committed}−${minReserve}=${available}만원이다.`,()=>{let highest=0;for(let allocation=0;allocation<=total;allocation++)if(total-allocation-committed>=minReserve)highest=allocation;return highest;},'만원');
}
for(let i=0;i<5;i++) {
  const durations=[20+5*i,30+5*i,15+5*i],prep=10,deadline=120,total=sum(durations)+prep,slack=deadline-total;
  resource('single-resource-timeline','공유 자원의 연속 일정',`같은 장비 한 대로 ${contexts[i]} 세 작업을 수행한다. 작업 시간은 ${durations.join(', ')}분이고 겹쳐 실행할 수 없다. 처음 준비 10분만 필요하고 작업 사이 준비는 없다. 시작 후 120분까지 모두 완료해야 한다. 최대 유휴 시간은?`,slack,[deadline-sum(durations),Math.max(...durations),deadline-Math.max(...durations)],`장비 점유 시간은 준비 ${prep}+작업 ${sum(durations)}=${total}분이다. 기한 ${deadline}분에서 빼면 유휴 여유는 ${slack}분이다.`,()=>{const events=[prep,...durations];let clock=0;for(const event of events)clock+=event;return deadline-clock;},'분');
}
for(let i=0;i<5;i++) {
  const p=[names[i],names[(i+1)%5],names[(i+2)%5]],jobs=['데이터 검증','이용자 안내','서류 정리'];
  const can=[[true,false,false],[true,true,false],[false,true,true]],opts=permutations(jobs).map(a=>a.map((job,k)=>`${p[k]}-${job}`).join(' / '));
  const good=opts[0];
  planning('skill-matching','자격에 맞춘 인력 배치','세 업무를 한 사람당 하나씩 맡길 때 가능한 배치는?',`${contexts[i]} 지원 업무다. ${p[0]}은 데이터 검증만, ${p[1]}은 데이터 검증 또는 이용자 안내, ${p[2]}는 이용자 안내 또는 서류 정리를 할 수 있다. 세 업무는 모두 수행해야 한다.`,[good,...opts.filter(x=>x!==good).slice(0,3)],`${p[0]}은 데이터 검증만 가능하다. 서류 정리를 할 수 있는 사람은 ${p[2]}뿐이다. 남은 이용자 안내는 ${p[1]}에게 배정한다.`,()=>{const valid=permutations([0,1,2]).filter(a=>a.every((job,k)=>can[k][job]));assert.equal(valid.length,1);return valid[0].map((j,k)=>`${p[k]}-${jobs[j]}`).join(' / ');});
}
for(let i=0;i<5;i++) {
  const blocked=[[0,40],[90,120]],duration=35+5*i,possible=duration<=50,good=possible?'40분에 시작해 90분 이전 또는 같은 시각에 끝낸다.':'허용된 빈 구간에는 연속 작업을 배치할 수 없다.';
  const options=[good, '20분에 시작해 이용 시간과 겹치게 수행한다.','100분에 시작해 이용 시간과 겹치게 수행한다.',possible?'이용 시간과 겹치지 않는 시작 시각은 전혀 없다.':'40분에 시작하면 90분 전에 끝난다.'];
  planning('maintenance-window','연속 작업의 허용 구간','이용 중단을 피하면서 가능한 계획은?',`시설은 시작 후 [0,40)분과 [90,120)분에 이용자가 사용한다. 정비는 시작 후 120분 이내에 마쳐야 하고 ${duration}분 동안 중단 없이 수행한다. 종료 시각과 다음 이용 시작 시각이 같아도 된다.`,options,`비어 있는 유일한 구간은 [40,90)분으로 50분이다. 필요한 ${duration}분을 ${possible?'이 구간 안에 배치할 수 있다':'배치하기에는 부족하다'}.`,()=>{const starts=Array.from({length:121},(_,t)=>t).filter(t=>t+duration<=120&&blocked.every(([a,b])=>t+duration<=a||t>=b));return starts.length?'40분에 시작해 90분 이전 또는 같은 시각에 끝낸다.':'허용된 빈 구간에는 연속 작업을 배치할 수 없다.';});
}
for(let i=0;i<5;i++) {
  const budget=60+5*i,plans=[{n:'A안',cost:55+i,quality:80,delivery:90},{n:'B안',cost:50+i,quality:90,delivery:80},{n:'C안',cost:70+5*i,quality:100,delivery:100},{n:'D안',cost:45+i,quality:70,delivery:75}];
  const score=p=>p.quality*0.7+p.delivery*0.3,ok=plans.filter(p=>p.cost<=budget).sort((a,b)=>score(b)-score(a));
  planning('weighted-vendor-score','예산 제약과 가중 평가','예산을 지키면서 종합 점수가 가장 높은 안은?',`${contexts[i]} 용역 예산은 ${budget}만원이다. 종합 점수는 품질 점수의 70%+납기 점수의 30%다.\n${plans.map(p=>`${p.n}: 비용 ${p.cost}, 품질 ${p.quality}, 납기 ${p.delivery}`).join('\n')}`,[ok[0].n,...plans.filter(p=>p.n!==ok[0].n).map(p=>p.n)],`C는 예산을 초과해 제외한다. 가능한 안의 점수는 A 83, B 87, D 71.5로 B가 가장 높다.`,()=>{let best=null;for(const p of plans){if(p.cost>budget)continue;const integerScore=p.quality*7+p.delivery*3;if(!best||integerScore>best.score)best={name:p.n,score:integerScore};}return best.name;});
}
for(let i=0;i<5;i++) {
  const stock=52+13*i,daily=9+2*i,days=Math.floor(stock/daily);
  resource('stock-full-days','재고로 운영 가능한 완전한 일수',`${contexts[i]} 소모품 재고는 ${stock}개이다. 운영하는 날마다 정확히 ${daily}개를 사용하며 추가 입고는 없다. 하루 수요를 전부 충족할 수 있는 최대 일수는?`,days,[Math.ceil(stock/daily),days+1,stock-daily],`재고÷하루 수요의 몫을 내림한다. ${days}일은 ${days*daily}개를 사용하지만 ${days+1}일에는 ${(days+1)*daily}개가 필요해 부족하다.`,()=>{let remaining=stock,d=0;while(remaining>=daily){remaining-=daily;d++;}return d;},'일');
}
for(let i=0;i<5;i++) {
  const labels=['A','B','C'],initial=labels[i%3],jobs=[{type:'A',time:10+i},{type:'B',time:12+i},{type:'A',time:15+i},{type:'C',time:9+i}],setup=5;
  const processing=sum(jobs.map(j=>j.time));
  const totalFor=p=>{let current=initial,minutes=0;for(const job of p){if(job.type!==current)minutes+=setup;minutes+=job.time;current=job.type;}return minutes;};
  const best=Math.min(...permutations(jobs).map(totalFor));
  resource('setup-grouping','전환 시간을 줄이는 순서',`한 장비로 네 작업 A형(${jobs[0].time}분), B형(${jobs[1].time}분), A형(${jobs[2].time}분), C형(${jobs[3].time}분)을 수행한다. 현재 설정은 ${initial}형이다. 작업 형식이 현재 설정과 달라지면 전환에 ${setup}분이 추가된다. 작업 순서는 자유이고 전환 후 설정은 유지된다. 최소 총시간은?`,best,[processing,processing+15,best+5],`작업 자체의 합은 ${processing}분이다. 현재 형식부터 시작해 같은 형식을 모으면 나머지 두 형식으로 전환 두 번만 필요하다. ${processing}+2×5=${best}분이다.`,()=>{const types=new Set(jobs.map(j=>j.type));const transitions=types.size-(types.has(initial)?1:0);return sum(jobs.map(j=>j.time))+transitions*setup;},'분',{difficulty:'심화'});
}
for(let i=0;i<5;i++) {
  const volume=100+50*i,manualPer=2,autoPer=1,setup=80,manualError=.1,autoError=.02,rework=5;
  const manual=volume*manualPer+volume*manualError*rework,auto=setup+volume*autoPer+volume*autoError*rework,best=Math.min(manual,auto);
  resource('expected-rework-cost','재작업을 포함한 기대 비용',`${contexts[i]} ${volume}건 처리에서 수동 방식은 건당 2단위, 오류율 10%다. 자동 방식은 초기 80단위+건당 1단위, 오류율 2%다. 오류 한 건의 추가 재작업 비용은 5단위이고 오류는 재작업으로 끝난다. 기대 총비용이 더 낮은 방식의 비용은?`,best,[volume*autoPer+setup,manual,best+20],`수동은 ${volume}×2+${volume}×0.1×5=${manual}, 자동은 80+${volume}×1+${volume}×0.02×5=${auto}단위다. 자동의 기대 비용 ${auto}가 더 낮다.`,()=>{const baselineAuto=80+volume;const expectedErrors=volume/50;const baselineManual=volume*2;const manualErrors=volume/10;return Math.min(baselineAuto+expectedErrors*5,baselineManual+manualErrors*5);},'단위',{difficulty:'심화'});
}
for(let i=0;i<5;i++) {
  const jobs=[8+i,5+i,4+i,3+i],partitions=subsets(jobs),load=sum(jobs),optimal=Math.min(...partitions.map(s=>Math.max(sum(s),load-sum(s))));
  resource('two-staff-balancing','두 담당자의 작업량 균형',`${contexts[i]} 네 작업의 시간은 ${jobs.join(', ')}분이다. 같은 능력의 두 직원에게 작업 단위로 나누고 각 직원은 맡은 일을 연속 수행한다. 작업을 쪼갤 수 없다. 두 직원이 모두 끝내는 시간을 최소화하면 몇 분인가?`,optimal,[load,Math.max(...jobs),optimal+1],`한 직원의 작업 합과 다른 직원의 합 중 큰 값이 완료 시간이다. 모든 분할을 비교하면 최소 ${optimal}분이다. 단순히 가장 큰 작업 시간만으로 전체 완료를 계산할 수 없다.`,()=>{let minimum=Infinity;for(let mask=0;mask<16;mask++){let a=0,b=0;for(let j=0;j<4;j++)if(mask&(1<<j))a+=jobs[j];else b+=jobs[j];minimum=Math.min(minimum,Math.max(a,b));}return minimum;},'분',{difficulty:'심화'});
}

for(const check of checks)check.run();
assert.equal(questions.length,380);
assert.equal(new Set(questions.map(q=>q.id)).size,380);
assert.equal(new Set(questions.map(q=>`${q.prompt}\n${q.passage||''}\n${q.options.join('\n')}`)).size,380);
const counts=Object.fromEntries(categories.map(c=>[c,questions.filter(q=>q.category===c).length]));
for(const count of Object.values(counts))assert.equal(count,95);
const families=Object.fromEntries([...new Set(questions.map(q=>q.templateId))].map(f=>[f,questions.filter(q=>q.templateId===f).length]));
assert.equal(Object.keys(families).length,76);
assert(Object.values(families).every(n=>n===5));
const distribution=Array.from({length:4},(_,i)=>Object.values(answers).filter(a=>a.correctIndex===i).length);
assert(distribution.every(n=>n>=85&&n<=105));
for(const q of questions){assert.equal(q.options.length,4);assert.equal(new Set(q.options).size,4);assert(answers[q.id].explanation.length>=25,`${q.id}: explanation too short`);}
const out=path.join(root,'data','expansion');fs.mkdirSync(out,{recursive:true});
fs.writeFileSync(path.join(out,'ncs-questions.json'),JSON.stringify(questions,null,2)+'\n');
fs.writeFileSync(path.join(out,'ncs-answers.json'),JSON.stringify(answers,null,2)+'\n');
const report={questions:questions.length,counts,structures:Object.keys(families).length,variantsPerStructure:5,independentlyComputed:checks.length,reviewedQualitative:questions.length-checks.length,correctIndexDistribution:distribution,limitations:['직접 작성한 가상 업무 연습문제로 실제 기출이 아니다.','모형의 수치와 단순화된 가정은 문제 풀이를 위한 것이며 실제 기관 규정이 아니다.','독립 검산은 계산·논리 문항에 적용하고 정성 문항은 문맥과 보기의 배타성으로 검토한다.']};
fs.writeFileSync(path.join(out,'ncs-generation-report.json'),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report,null,2));

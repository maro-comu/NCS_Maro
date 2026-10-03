(() => {
  'use strict';
  const questions = window.STUDY_QUESTIONS || [];
  const answers = window.STUDY_ANSWERS || {};
  const lessons = window.STUDY_LESSONS || [];
  const sources = window.STUDY_SOURCES || [];
  const tracks = { ncs: 'NCS 직업기초', programming: '프로그래밍', db: '데이터베이스' };
  const categories = ['의사소통능력', '문제해결능력', '수리능력', '자원관리능력'];
  const labels = { quiz: '문제 풀기', lessons: '개념 학습', review: '오답 노트', sources: '자료실' };
  const icons = {
    book: '<path d="M4 4h6a3 3 0 0 1 3 3v14a4 4 0 0 0-4-3H4z"/><path d="M20 4h-4a3 3 0 0 0-3 3v14a4 4 0 0 1 4-3h3z"/>',
    layers: '<path d="m12 3 10 6-10 6L2 9z"/><path d="m2 14 10 6 10-6M2 18l10 6 10-6"/>',
    repeat: '<path d="M3 10a9 9 0 0 1 15-6l3 3M21 3v4h-4M21 14a9 9 0 0 1-15 6l-3-3M3 21v-4h4"/>',
    folder: '<path d="M3 6h6l2 3h10v12H3z"/><path d="M3 6V3h6l2 3h9v3"/>',
    code: '<path d="m7 6-5 6 5 6m10-12 5 6-5 6m-4-15-2 18"/>',
    database: '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 4 16 4 16 0V5M4 12c0 4 16 4 16 0"/>',
    check: '<path d="m5 12 4 4L19 6"/><circle cx="12" cy="12" r="10"/>',
    target: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
    bookmark: '<path d="M6 3h12v19l-6-4-6 4z"/>',
    clock: '<circle cx="12" cy="12" r="9"/><path d="M12 6v6l4 2"/>',
    shuffle: '<path d="M3 5h2c5 0 9 14 14 14h3m-4-4 4 4-4 4M3 19h2c2 0 4-3 6-6m2-3c2-3 4-5 6-5h3m-4-4 4 4-4 4"/>',
    bulb: '<path d="M8 17c0-3-3-4-3-8a7 7 0 0 1 14 0c0 4-3 5-3 8M8 17h8M9 20h6M10 23h4"/>',
    file: '<path d="M5 2h9l5 5v15H5zM14 2v6h5M8 12h8M8 16h8"/>'
  };
  const icon = name => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${icons[name] || icons.book}</svg>`;
  const escape = text => String(text ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const safeUrl = value => {
    try { const u = new URL(value, location.href); return ['https:', 'http:'].includes(u.protocol) || (u.protocol === 'file:' && !/^[a-z]+:/i.test(value)) ? escape(value) : '#'; } catch { return '#'; }
  };
  let progress;
  let storageAvailable = true;
  try { progress = JSON.parse(localStorage.getItem('maro-study-v1') || '{}'); } catch { progress = {}; storageAvailable = false; }
  if (!progress || typeof progress !== 'object' || Array.isArray(progress)) progress = {};
  if (!progress.attempts || typeof progress.attempts !== 'object' || Array.isArray(progress.attempts)) progress.attempts = {};
  if (!Array.isArray(progress.bookmarks)) progress.bookmarks = [];
  if (!Array.isArray(progress.readLessons)) progress.readLessons = [];
  const validIds = new Set(questions.map(q => q.id));
  const localOfficial = questions.some(q => q.kind === 'official-sample');
  progress.bookmarks = progress.bookmarks.filter(id => validIds.has(id));
  const state = { view: 'quiz', track: 'ncs', category: '전체', index: 0, selected: null, submitted: false, reviewMode: 'wrong', lessonId: null, startedAt: Date.now(), elapsed: 0, sessionCount: 0, focusId: null };
  const $ = selector => document.querySelector(selector);
  const save = () => { try { localStorage.setItem('maro-study-v1', JSON.stringify(progress)); } catch { storageAvailable = false; toast('학습 기록을 저장할 수 없습니다. 브라우저 저장 공간을 확인해 주세요.'); } };
  let toastTimer;
  function toast(message) { $('#toast').textContent = message; $('#toast').hidden = false; clearTimeout(toastTimer); toastTimer = setTimeout(() => $('#toast').hidden = true, 3000); }
  const wrongIds = () => Object.entries(progress.attempts).filter(([id, a]) => validIds.has(id) && a?.correct === false).map(([id]) => id);
  const filtered = () => questions.filter(q => q.track === state.track && (state.category === '전체' || q.category === state.category));
  const current = () => state.focusId ? questions.find(q => q.id === state.focusId) : filtered()[state.index];
  const kindLabel = q => q.kind === 'official-sample' ? '공식 예시' : q.kind === 'past-exam' ? '공개 기출' : '자체 연습';
  const sourceFor = q => sources.find(s => s.id === q.sourceId);
  function tabs() {
    return `<div class="track-tabs" role="tablist" aria-label="학습 과목">${Object.entries(tracks).map(([id, name]) => `<button role="tab" aria-selected="${state.track === id}" class="track-tab ${state.track === id ? 'active' : ''}" data-action="track" data-id="${id}">${icon(id === 'db' ? 'database' : id === 'programming' ? 'code' : 'book')}${name}<span class="tab-count">${questions.filter(q => q.track === id).length}</span></button>`).join('')}</div>`;
  }
  function stats() {
    const attempts = Object.entries(progress.attempts).filter(([id]) => validIds.has(id));
    const correct = attempts.filter(([, a]) => a?.correct).length;
    $('#stats').innerHTML = [
      ['학습 가능한 문제', questions.length, '문제', 'book'],
      ['풀어 본 문제', attempts.length, '문제', 'check'],
      ['나의 정답률', attempts.length ? Math.round(correct / attempts.length * 100) : 0, '%', 'target'],
      ['다시 풀 오답', wrongIds().length, '문제', 'repeat']
    ].map(([label, value, unit, name]) => `<article class="stat"><div><div class="stat-label">${label}</div><div class="stat-value">${value}<span class="stat-unit">${unit}</span></div></div><span class="stat-icon">${icon(name)}</span></article>`).join('');
    $('#wrong-nav-count').textContent = wrongIds().length;
  }
  function sidePanel() {
    return `<aside class="side-panel" aria-label="학습 현황"><section class="focus-card"><span class="tiny-label">ONE QUESTION AT A TIME</span><h2>오늘의 집중,<br><em>내일의 가능성.</em></h2><p>작은 이해가 쌓이면<br>낯선 문제도 익숙해집니다.</p><div class="focus-rule"></div><div class="focus-foot"><span>이번 방문에 푼 문제</span><strong>${state.sessionCount}문제</strong></div></section><section class="progress-card"><div class="panel-heading"><h3>과목별 학습 현황</h3><small>풀어 본 문제 기준</small></div>${Object.entries(tracks).map(([id, name]) => {
      const bank = questions.filter(q => q.track === id); const done = bank.filter(q => progress.attempts[q.id]).length;
      return `<div class="progress-item"><div class="progress-text"><span>${name}</span><strong>${done} / ${bank.length}</strong></div><div class="progress-bar" role="progressbar" aria-label="${name} 학습 진도" aria-valuenow="${done}" aria-valuemin="0" aria-valuemax="${bank.length || 1}"><span style="width:${bank.length ? done / bank.length * 100 : 0}%"></span></div></div>`;
    }).join('')}</section><section class="tip-card"><div class="tip-head">${icon('bulb')}STUDY NOTE</div><p>NCS는 의사소통·문제해결·수리·자원관리 네 영역을 학습합니다. 해설을 확인한 뒤, 틀린 문제를 다시 풀어 보세요.</p><button data-view="review">오답 노트 열기</button></section></aside>`;
  }
  function questionCard(q) {
    if (!q) return empty('준비된 문제가 없습니다', '다른 영역을 선택해 주세요.');
    const answer = answers[q.id]; const source = sourceFor(q);
    return `<article class="quiz-card"><div class="quiz-top"><div class="quiz-meta"><span class="pill">${escape(q.category)}</span><span class="pill blue">${kindLabel(q)}</span><span class="pill gold">${escape(q.difficulty || '보통')}</span></div><button class="icon-button ${progress.bookmarks.includes(q.id) ? 'saved' : ''}" data-action="bookmark" aria-label="${progress.bookmarks.includes(q.id) ? '북마크 해제' : '문제 북마크'}" aria-pressed="${progress.bookmarks.includes(q.id)}">${icon('bookmark')}</button></div><div class="quiz-body"><div class="question-heading"><span class="question-number">Q.</span><h2>${escape(q.prompt || q.title)}</h2></div>${q.passage ? `<div class="passage">${escape(q.passage)}</div>` : ''}${q.code ? `<pre class="code-block"><code>${escape(q.code)}</code></pre>` : ''}${q.images?.length ? q.images.map((src,i) => `<figure class="question-figure"><img class="question-image" src="${safeUrl(typeof src === 'string' ? src : src.src)}" alt="${escape(q.category)} ${escape(q.number || '')}번 ${i + 1}번째 문제 자료" loading="lazy"><figcaption>${escape(typeof src === 'string' ? '문제 자료' : src.caption || '문제 자료')}</figcaption></figure>`).join('') : ''}${q.image ? `<a href="${safeUrl(q.image)}" target="_blank" rel="noopener"><img class="question-image" src="${safeUrl(q.image)}" alt="${escape(q.category)} 공식 예시 ${escape(q.number || '')}번 문제" loading="lazy"></a>` : ''}<div class="option-list" role="group" aria-label="답 선택">${q.options.map((option, i) => {
      let style = state.selected === i ? 'selected' : '';
      let status = '';
      if (state.submitted && answer) { if (answer.correctIndex === i) { style = 'correct'; status = '정답'; } else if (state.selected === i) { style = 'incorrect'; status = '나의 선택'; } }
      return `<button class="option ${style}" data-action="select" data-index="${i}" aria-pressed="${state.selected === i}" ${state.submitted ? 'disabled' : ''}><span class="option-num">${i + 1}</span><span>${escape(option)}</span>${status ? `<span class="option-state">${status}</span>` : ''}</button>`;
    }).join('')}</div>${state.submitted && answer ? `<div class="explanation ${state.selected !== answer.correctIndex ? 'wrong' : ''}"><strong>${state.selected === answer.correctIndex ? '정답입니다! 잘 이해했어요.' : `정답은 ${answer.correctIndex + 1}번입니다.`}</strong>${escape(answer.explanation)}${answer.images?.length ? answer.images.map(src => `<figure class="question-figure"><img class="question-image" src="${safeUrl(typeof src === 'string' ? src : src.src)}" alt="공식 정답 해설" loading="lazy"><figcaption>${escape(typeof src === 'string' ? '공식 풀이' : src.caption || '공식 풀이')}</figcaption></figure>`).join('') : ''}${answer.detailedSteps?.length ? `<ol>${answer.detailedSteps.map(step => `<li>${escape(step)}</li>`).join('')}</ol>` : ''}<div class="source-line">${answer.verification === 'derived' ? '풀이로 산출한 답안 · 공식 정답 수록 여부와 구분' : answer.verification === 'official-answer' ? '원문 공식 정답 대조' : '자체 제작 연습문제 해설'}</div></div>` : ''}<div class="source-line">${source ? `출처: <a href="${safeUrl(source.url)}" target="_blank" rel="noopener">${escape(source.publisher)} · ${escape(source.title)}</a>${q.page ? ` / 원문 ${q.page}쪽` : ''}${q.number ? ` / ${escape(q.number)}번` : ''}` : 'MARO 자체 제작 연습문제 · 실제 신용보증기금 기출문제가 아닙니다.'}</div></div><div class="quiz-bottom"><span class="timer">${icon('clock')}<span id="question-timer">00:00</span></span><div class="quiz-actions">${state.submitted ? `<button class="secondary-button" data-action="retry">다시 풀기</button><button class="primary-button" data-action="next">다음 문제</button>` : `<button class="primary-button" data-action="submit" ${state.selected === null || !answer ? 'disabled' : ''}>정답 확인하기</button>`}</div></div></article>`;
  }
  function quizView() {
    const bank = filtered(); if (state.index >= bank.length) state.index = 0;
    const cats = state.track === 'ncs' ? categories : [...new Set(questions.filter(q => q.track === state.track).map(q => q.category))];
    $('#view-root').innerHTML = `<div class="study-layout"><div class="study-main">${tabs()}<div class="filter-row" aria-label="문제 영역">${['전체', ...cats].map(cat => `<button class="filter-chip ${state.category === cat ? 'active' : ''}" data-action="category" data-id="${escape(cat)}" aria-pressed="${state.category === cat}">${escape(cat)}</button>`).join('')}</div>${state.focusId ? '<div class="notice">오답·북마크에서 선택한 문제를 다시 풀고 있습니다. 영역을 선택하면 일반 문제 풀이로 돌아갑니다.</div>' : ''}${questionCard(current())}<div class="question-nav"><button class="quiet-button" data-action="shuffle">${icon('shuffle')}무작위 문제</button><div class="nav-group"><span>${bank.length ? state.index + 1 : 0} / ${bank.length} 문제</span><button class="secondary-button" data-action="prev" ${!state.focusId && state.index === 0 ? 'disabled' : ''}>이전</button><button class="secondary-button" data-action="next" ${!state.focusId && state.index === bank.length - 1 ? 'disabled' : ''}>다음</button></div></div></div>${sidePanel()}</div>`;
    updateTimer();
  }
  function empty(title, body, action = '') { return `<div class="empty-state">${icon('book')}<h2>${title}</h2><p>${body}</p>${action}</div>`; }
  function lessonsView() {
    const lesson = lessons.find(l => l.id === state.lessonId);
    if (lesson) {
      $('#view-root').innerHTML = `<article class="lesson-detail"><button class="quiet-button" data-action="lesson-back">개념 학습 목록</button><div class="lesson-meta">${escape(tracks[lesson.track])} · ${escape(lesson.minutes)}분 학습</div><h2>${escape(lesson.title)}</h2><p>${escape(lesson.summary)}</p>${lesson.sections.map(s => `<section class="lesson-section"><h3>${escape(s.title)}</h3><p>${escape(s.body)}</p>${s.code ? `<pre class="code-block"><code>${escape(s.code)}</code></pre>` : ''}</section>`).join('')}<section class="lesson-section"><h3>더 읽어 보기</h3><ul class="reference-list">${(lesson.references || []).map(r => `<li><a href="${safeUrl(r.url)}" target="_blank" rel="noopener">${escape(r.title)}</a></li>`).join('')}</ul></section><button class="primary-button" data-action="lesson-complete" data-id="${escape(lesson.id)}">${progress.readLessons.includes(lesson.id) ? '학습 완료됨' : '이 개념 학습 완료'}</button> <button class="secondary-button" data-action="lesson-practice" data-id="${lesson.track}">관련 문제 풀기</button></article>`;
      return;
    }
    $('#view-root').innerHTML = `${tabs()}<div class="section-toolbar"><p>개념을 이해하고, 문제로 확인하세요.</p><span class="lesson-meta">완료 ${progress.readLessons.length} / ${lessons.length}</span></div><div class="lesson-grid">${lessons.filter(l => l.track === state.track).map(l => `<article class="lesson-card"><span class="lesson-meta">${l.minutes}분 · ${progress.readLessons.includes(l.id) ? '학습 완료' : '개념 학습'}</span><h3>${escape(l.title)}</h3><p>${escape(l.summary)}</p><button class="primary-button" data-action="lesson" data-id="${escape(l.id)}">학습하기</button></article>`).join('')}</div>`;
  }
  function reviewView() {
    const ids = state.reviewMode === 'wrong' ? wrongIds() : progress.bookmarks;
    $('#view-root').innerHTML = `<div class="section-toolbar"><div class="review-tabs"><button class="filter-chip ${state.reviewMode === 'wrong' ? 'active' : ''}" data-action="review-mode" data-id="wrong">오답 ${wrongIds().length}</button><button class="filter-chip ${state.reviewMode === 'bookmarks' ? 'active' : ''}" data-action="review-mode" data-id="bookmarks">북마크 ${progress.bookmarks.length}</button></div><p>다시 풀어 맞히면 오답 목록에서 빠집니다.</p></div>${ids.length ? ids.map(id => { const q = questions.find(q => q.id === id); return q ? `<article class="review-row"><div><span class="pill">${escape(q.category)}</span><h3>${escape(q.title || q.prompt)}</h3><p>${kindLabel(q)} · ${escape(tracks[q.track])}</p></div><button class="secondary-button" data-action="open-question" data-id="${escape(q.id)}">다시 풀기</button></article>` : ''; }).join('') : empty(state.reviewMode === 'wrong' ? '아직 기록된 오답이 없어요.' : '북마크한 문제가 없어요.', state.reviewMode === 'wrong' ? '문제를 풀면 다시 공부할 오답이 여기에 모입니다.' : '문제 위의 북마크 버튼으로 기억해 둘 문제를 저장하세요.', '<button class="primary-button" data-view="quiz">문제 풀기</button>')}`;
  }
  function sourcesView() {
    $('#view-root').innerHTML = `<div class="notice">${localOfficial ? '개인 학습용 자료입니다. 공식 공식 문항의 지문·그림과 해설을 이 PC에서 제공합니다. ' : '공개 웹의 문제는 자체 제작 연습문제입니다. 공식 원문은 아래 출처에서 확인하세요. '}공식 예시는 NCS 채용모델 공개 문항이며, 신용보증기금 실제 기출과 구분됩니다. 모든 연도·기관의 기출을 확보한 자료집은 아닙니다.</div><div class="source-grid">${sources.map(s => `<article class="source-card"><span class="pill blue">${s.kind === 'official-sample' ? '공식 예시' : s.kind === 'past-exam' ? '공개 기출' : '공식 안내'}</span><h3>${escape(s.title)}</h3><p>${escape(s.publisher)}${s.questionCount ? ` · ${s.questionCount}문항` : ''}<br>${escape(s.note || '')}</p><div class="source-actions"><a class="secondary-button" href="${safeUrl(s.url)}" target="_blank" rel="noopener">공식 출처</a>${s.file ? `<a class="secondary-button" href="${safeUrl(s.file)}" download>원본 다운로드</a>` : ''}${s.questionFile ? `<a class="secondary-button" href="${safeUrl(s.questionFile)}" download>문제 PDF</a>` : ''}${s.answerFile ? `<a class="secondary-button" href="${safeUrl(s.answerFile)}" download>정답·해설 PDF</a>` : ''}</div></article>`).join('')}</div><section class="downloads-box"><h3>문제와 정답을 따로 보관하기</h3><p>문항에는 정답을 포함하지 않습니다. 정답·해설은 문제 ID로 연결되는 별도 파일입니다.</p><div class="source-actions"><a class="secondary-button" href="data/questions.json" download>문제 전체 JSON</a><a class="secondary-button" href="data/answers.json" download>정답·해설 JSON</a><button class="secondary-button" data-action="export-progress">학습 기록 백업</button></div><p style="margin-top:16px;margin-bottom:0">문제 ${questions.length}개 · 정답 ${Object.keys(answers).length}개 · 학습 기록은 이 기기와 브라우저에 저장됩니다.</p></section>`;
  }
  function render() {
    stats();
    $('.nav-item.active')?.classList.remove('active');
    document.querySelector(`.nav-item[data-view="${state.view}"]`)?.classList.add('active');
    $('#page-name').textContent = labels[state.view];
    const headings = { quiz: ['오늘도 한 걸음, 합격에 가까이.', 'NCS부터 전산 전공까지, 필요한 공부를 한곳에서.'], lessons: ['문제 앞에서, 개념부터 탄탄하게.', '프로그래밍과 데이터베이스의 기초를 차근차근 정리해요.'], review: ['한 번 더 풀면, 내 실력이 됩니다.', '틀렸던 문제와 기억해 둔 문제를 다시 확인해요.'], sources: ['공부의 시작, 믿을 수 있는 자료.', '공식 원문을 확인하고 문제·정답을 따로 내려받으세요.'] };
    $('#page-title').textContent = headings[state.view][0]; $('#page-description').textContent = headings[state.view][1];
    ({ quiz: quizView, lessons: lessonsView, review: reviewView, sources: sourcesView })[state.view]();
  }
  function resetQuestion() { state.selected = null; state.submitted = false; state.startedAt = Date.now(); state.elapsed = 0; }
  function navigate(view) { if (!labels[view]) return; state.view = view; state.lessonId = null; history.replaceState(null, '', '#' + view); render(); }
  function setTrack(track) { if (!tracks[track]) return; state.track = track; state.category = '전체'; state.index = 0; state.focusId = null; resetQuestion(); render(); }
  function move(step) {
    const bank = filtered(); if (!bank.length) return;
    if (state.focusId) { const i = bank.findIndex(q => q.id === state.focusId); state.index = i >= 0 ? i : 0; state.focusId = null; }
    state.index = Math.max(0, Math.min(bank.length - 1, state.index + step)); resetQuestion(); render();
  }
  function select(index) { const q = current(); if (!q || state.submitted || !Number.isInteger(index) || index < 0 || index >= q.options.length) throw new Error('유효한 답 번호를 선택해 주세요.'); state.selected = index; quizView(); }
  function submit() {
    const q = current(); if (!q || !answers[q.id] || state.selected === null || state.submitted) return;
    const correct = state.selected === answers[q.id].correctIndex;
    progress.attempts[q.id] = { choice: state.selected, correct, at: new Date().toISOString() };
    state.elapsed = Math.floor((Date.now() - state.startedAt) / 1000); state.submitted = true; state.sessionCount++; save(); render();
    return { questionId: q.id, correct, correctIndex: answers[q.id].correctIndex, explanation: answers[q.id].explanation };
  }
  function updateTimer() { const el = $('#question-timer'); if (!el) return; const seconds = state.submitted ? state.elapsed : Math.floor((Date.now() - state.startedAt) / 1000); el.textContent = `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`; }
  document.addEventListener('click', event => {
    const button = event.target.closest('[data-action],[data-view]'); if (!button || button.disabled) return;
    if (button.dataset.view) return navigate(button.dataset.view);
    const { action, id, index } = button.dataset;
    if (action === 'track') setTrack(id);
    else if (action === 'category') { state.category = id; state.index = 0; state.focusId = null; resetQuestion(); render(); }
    else if (action === 'select') select(Number(index));
    else if (action === 'submit') submit();
    else if (action === 'next') move(1);
    else if (action === 'prev') move(-1);
    else if (action === 'shuffle') { const bank = filtered(); if (!bank.length) return; state.focusId = null; const candidates = bank.map((_, i) => i).filter(i => i !== state.index); state.index = candidates.length ? candidates[Math.floor(Math.random() * candidates.length)] : 0; resetQuestion(); render(); }
    else if (action === 'retry') { resetQuestion(); render(); }
    else if (action === 'bookmark') { const q = current(); if (!q) return; progress.bookmarks = progress.bookmarks.includes(q.id) ? progress.bookmarks.filter(id => id !== q.id) : [...progress.bookmarks, q.id]; save(); render(); }
    else if (action === 'review-mode') { state.reviewMode = id; render(); }
    else if (action === 'open-question') { const q = questions.find(q => q.id === id); if (!q) return; state.track = q.track; state.category = '전체'; state.index = filtered().findIndex(q => q.id === id); state.focusId = id; resetQuestion(); navigate('quiz'); }
    else if (action === 'lesson') { state.lessonId = id; render(); }
    else if (action === 'lesson-back') { state.lessonId = null; render(); }
    else if (action === 'lesson-complete') { if (!progress.readLessons.includes(id)) progress.readLessons.push(id); save(); toast('개념 학습을 완료했습니다.'); render(); }
    else if (action === 'lesson-practice') { state.track = id; state.category = '전체'; state.index = 0; state.focusId = null; resetQuestion(); navigate('quiz'); }
    else if (action === 'export-progress') { const blob = new Blob([JSON.stringify(progress, null, 2)], { type: 'application/json' }); const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = 'maro-study-progress.json'; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); }
  });
  document.querySelectorAll('[data-icon]').forEach(el => el.innerHTML = icon(el.dataset.icon));
  $('#today-date').textContent = new Intl.DateTimeFormat('ko-KR', { timeZone: 'Asia/Seoul', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date());
  const initialView = location.hash.slice(1); if (labels[initialView]) state.view = initialView;
  render(); setInterval(updateTimer, 1000);
  if (!storageAvailable) toast('이 브라우저에서는 학습 기록 저장을 사용할 수 없습니다.');
  // Feature-detected agent access uses the same actions as the visible controls.
  if (document.modelContext?.registerTool) {
    const lifecycle = new AbortController();
    const toolList = [
      { name: 'read_study_question', title: '현재 문제 읽기', description: '현재 선택된 문제와 학습 상태를 읽습니다. 채점 전에는 정답을 반환하지 않습니다.', inputSchema: { type: 'object', properties: {}, additionalProperties: false }, annotations: { readOnlyHint: true, untrustedContentHint: false }, execute: () => ({ question: current(), submitted: state.submitted, selectedIndex: state.selected }) },
      { name: 'start_study_track', title: '과목 문제 풀이 시작', description: '선택한 과목의 첫 문제를 열고 화면을 문제 풀이로 이동합니다.', inputSchema: { type: 'object', properties: { track: { type: 'string', enum: ['ncs', 'programming', 'db'] } }, required: ['track'], additionalProperties: false }, annotations: { readOnlyHint: false, untrustedContentHint: false }, execute: input => { if (!input || !tracks[input.track]) throw new Error('학습 과목이 올바르지 않습니다.'); state.view = 'quiz'; setTrack(input.track); return { track: state.track, question: current() }; } },
      { name: 'submit_study_answer', title: '답 선택 및 채점', description: '현재 문제에서 선택한 답을 제출하고 채점합니다. 학습 기록이 이 브라우저에 저장됩니다.', inputSchema: { type: 'object', properties: { choiceIndex: { type: 'integer', minimum: 0, maximum: 4 } }, required: ['choiceIndex'], additionalProperties: false }, annotations: { readOnlyHint: false, untrustedContentHint: false }, execute: input => { if (state.view !== 'quiz' || state.submitted) throw new Error('풀고 있는 미제출 문제가 없습니다.'); if (!input || !Number.isInteger(input.choiceIndex)) throw new Error('답 번호가 올바르지 않습니다.'); select(input.choiceIndex); return submit(); } }
    ];
    for (const tool of toolList) { try { Promise.resolve(document.modelContext.registerTool(tool, { signal: lifecycle.signal })).catch(() => {}); } catch {} }
    window.addEventListener('pagehide', () => lifecycle.abort(), { once: true });
  }
})();

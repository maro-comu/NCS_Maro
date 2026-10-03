import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { loadPracticeBank, loadBankManifest } from './load-practice-bank.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const readJson = relative => JSON.parse(readFileSync(path.join(root, relative), 'utf8').replace(/^\uFEFF/, ''));
const tracks = new Set(['ncs', 'programming', 'db']);
const expectedNcs = ['의사소통능력', '문제해결능력', '수리능력', '자원관리능력'].sort();
const answerOnlyFields = new Set(['correctIndex', 'correctAnswer', 'correctOption', 'answerIndex', 'answer', 'explanation', 'detailedSteps', 'verification']);
const nonempty = value => typeof value === 'string' && value.trim().length > 0;

function assertSeparated(value, location) {
  if (!value || typeof value !== 'object') return;
  for (const [key, child] of Object.entries(value)) {
    assert(!answerOnlyFields.has(key), `${location}: answer field ${key} leaked into a question`);
    assertSeparated(child, `${location}.${key}`);
  }
}

function validateBank(questions, answers, label) {
  assert(Array.isArray(questions) && questions.length > 0, `${label}: questions must be a nonempty array`);
  assert(answers && typeof answers === 'object' && !Array.isArray(answers), `${label}: answers must be an ID map`);
  const ids = new Set();
  for (const q of questions) {
    assert(nonempty(q.id) && !ids.has(q.id), `${label}: duplicate or invalid question ID ${q.id}`);
    ids.add(q.id);
    assert(tracks.has(q.track), `${q.id}: unknown track ${q.track}`);
    assert(nonempty(q.category), `${q.id}: missing category`);
    assert(nonempty(q.prompt) || nonempty(q.title), `${q.id}: missing question text`);
    assert(Array.isArray(q.options) && [4, 5].includes(q.options.length), `${q.id}: expected four or five options`);
    assert(q.options.every(nonempty), `${q.id}: options must be nonempty text`);
    assert(new Set(q.options).size === q.options.length, `${q.id}: duplicate options`);
    assertSeparated(q, q.id);
    assert(Object.hasOwn(answers, q.id), `${q.id}: missing separated answer`);
    const answer = answers[q.id];
    assert(answer && typeof answer === 'object', `${q.id}: invalid answer`);
    assert(Number.isInteger(answer.correctIndex) && answer.correctIndex >= 0 && answer.correctIndex < q.options.length, `${q.id}: invalid correctIndex`);
    assert(nonempty(answer.explanation), `${q.id}: missing explanation`);
    assert(['original-reviewed', 'computed-verified', 'derived', 'official-answer'].includes(answer.verification), `${q.id}: missing verification provenance`);
    if (answer.detailedSteps !== undefined) assert(Array.isArray(answer.detailedSteps) && answer.detailedSteps.every(nonempty), `${q.id}: invalid detailedSteps`);
  }
  assert.deepEqual(Object.keys(answers).sort(), [...ids].sort(), `${label}: question and answer IDs differ`);
  assert.deepEqual([...new Set(questions.filter(q => q.track === 'ncs').map(q => q.category))].sort(), expectedNcs, `${label}: NCS must contain exactly the four requested categories`);
  return ids;
}

const { questions, answers } = loadPracticeBank();
const manifest = loadBankManifest();
const lessons = readJson('data/lessons.json');
validateBank(questions, answers, 'original practice');
assert.equal(questions.length, manifest.totalQuestions, 'practice question count must match manifest');
for (const track of tracks) assert.equal(questions.filter(q => q.track === track).length, manifest.trackCounts[track], `${track} count must match manifest`);
for (const [category,count] of Object.entries(manifest.ncsCategoryCounts)) assert.equal(questions.filter(q => q.track === 'ncs' && q.category === category).length, count, `${category} count must match manifest`);
const fingerprints = new Map();
for (const q of questions) {
  assert.equal(q.kind, 'original', `${q.id}: original practice must be labeled original`);
  assert.equal(q.sourceId, 'original', `${q.id}: original practice source must be original`);
  assert(['original-reviewed','computed-verified'].includes(answers[q.id].verification), `${q.id}: practice answer provenance invalid`);
  const fingerprint = JSON.stringify([q.prompt || q.title,q.passage || '',q.code || '',[...q.options].sort()]).normalize('NFKC').replace(/\s+/g,' ').toLowerCase();
  assert(!fingerprints.has(fingerprint), `${q.id}: duplicates ${fingerprints.get(fingerprint)}`);
  fingerprints.set(fingerprint,q.id);
}
for (const track of tracks) {
  const positions = [0,0,0,0];
  for (const q of questions.filter(q => q.track === track)) positions[answers[q.id].correctIndex]++;
  for (const [index,count] of positions.entries()) assert(count >= manifest.trackCounts[track] * .15 && count <= manifest.trackCounts[track] * .35, `${track}: answer position ${index + 1} is disproportionately frequent (${count})`);
  const expansion = questions.filter(q => q.track === track && q.id.startsWith('extra-'));
  const structures = new Map();
  for (const q of expansion) {
    assert(nonempty(q.learningTopic) && nonempty(q.templateId), `${q.id}: expansion topic/structure metadata missing`);
    structures.set(q.templateId,(structures.get(q.templateId) || 0) + 1);
  }
  assert(structures.size >= manifest.minimumExpansionStructures[track], `${track}: insufficient distinct expansion structures`);
  for (const [id,count] of structures) assert(count <= manifest.maximumQuestionsPerStructure, `${id}: too many repetitions (${count})`);
}

assert(Array.isArray(lessons) && lessons.length > 0, 'lessons must be a nonempty array');
const lessonIds = new Set();
const lessonTracks = new Set();
for (const lesson of lessons) {
  assert(nonempty(lesson.id) && !lessonIds.has(lesson.id), `duplicate or invalid lesson ID ${lesson.id}`);
  lessonIds.add(lesson.id);
  assert(tracks.has(lesson.track), `${lesson.id}: unknown track`);
  lessonTracks.add(lesson.track);
  assert(nonempty(lesson.title) && nonempty(lesson.summary), `${lesson.id}: missing title or summary`);
  assert(Number.isFinite(lesson.minutes) && lesson.minutes > 0, `${lesson.id}: invalid study duration`);
  assert(Array.isArray(lesson.sections) && lesson.sections.length > 0, `${lesson.id}: missing sections`);
  for (const section of lesson.sections) assert(nonempty(section.title) && nonempty(section.body), `${lesson.id}: section requires title and body`);
  for (const ref of lesson.references ?? []) {
    assert(nonempty(ref.title), `${lesson.id}: unnamed reference`);
    const url = new URL(ref.url);
    assert(['https:', 'http:'].includes(url.protocol), `${lesson.id}: unsafe reference URL`);
  }
}
assert.deepEqual([...lessonTracks].sort(), [...tracks].sort(), 'lessons must cover all three tracks');

const deployFlag = process.argv.indexOf('--deploy');
if (deployFlag >= 0) {
  assert(process.argv[deployFlag + 1], '--deploy requires a directory path');
  const deployRoot = path.resolve(root, process.argv[deployFlag + 1]);
  const deployedQuestions = JSON.parse(readFileSync(path.join(deployRoot, 'data/questions.json'), 'utf8').replace(/^\uFEFF/, ''));
  const deployedAnswers = JSON.parse(readFileSync(path.join(deployRoot, 'data/answers.json'), 'utf8').replace(/^\uFEFF/, ''));
  validateBank(deployedQuestions, deployedAnswers, 'deployment');
  assert.equal(deployedQuestions.length,questions.length,'deployed question count differs from source');
  assert.deepEqual(deployedAnswers, answers, 'deployed separated answers differ from source');
  const deployedById = new Map(deployedQuestions.map(q => [q.id, q]));
  for (const q of questions) assert.deepEqual(deployedById.get(q.id), q, `${q.id}: deployed practice differs from source`);
  for (const q of deployedQuestions) {
    if (q.image && !/^[a-z][a-z\d+.-]*:/i.test(q.image) && !q.image.startsWith('//')) {
      const imagePath = path.resolve(deployRoot, q.image.split(/[?#]/)[0]);
      assert(existsSync(imagePath), `${q.id}: missing local question image ${q.image}`);
      assert(!q.image.startsWith('/'), `${q.id}: root-relative images break project GitHub Pages paths`);
    }
  }
}

console.log(`PASS: ${questions.length} separated original questions and answers, four NCS categories, all three tracks, ${lessons.length} lessons${deployFlag >= 0 ? ', deployment payload checked' : ''}.`);

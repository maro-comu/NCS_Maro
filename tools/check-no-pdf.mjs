import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const read = relative => fs.readFileSync(path.join(root, relative), 'utf8').replace(/^\uFEFF/, '');
const json = relative => JSON.parse(read(relative));
const unavailablePrompt = /원문\s*PDF에서|PDF의\s*(?:이전\s*)?페이지|(?:원문|PDF).{0,25}(?:보고|보세요|확인(?:해)?\s*주세요|참조)/i;
const answerFields = new Set(['correctIndex', 'correctAnswer', 'answerIndex', 'answer', 'explanation', 'detailedSteps']);
const localSourceFields = new Set(['file', 'questionFile', 'answerFile', 'localFile', 'localQuestionFile', 'localAnswerFile']);

function checkPublicValue(value, where) {
  if (typeof value === 'string') {
    assert(!/(?:^|[\\/])downloads[\\/]/i.test(value), `${where}: local downloads path leaked into public data`);
    assert(!/(?:^|[\\/])private-study[\\/]/i.test(value), `${where}: private-study path leaked into public data`);
    assert(!/^(?:file:|[A-Za-z]:[\\/])/.test(value), `${where}: absolute filesystem URL leaked into public data`);
    return;
  }
  if (!value || typeof value !== 'object') return;
  for (const [key, child] of Object.entries(value)) {
    assert(!localSourceFields.has(key), `${where}.${key}: local source file field must be excluded from public data`);
    checkPublicValue(child, `${where}.${key}`);
  }
}

function checkUi(directory) {
  for (const file of ['index.html', 'app.js', 'styles.css']) {
    const contents = read(`${directory}/${file}`);
    assert(!/<\s*(?:iframe|embed|object)\b/i.test(contents), `${directory}/${file}: embedded document viewer remains`);
    assert(!/pdf-viewer|pdf-question|pdf-toolbar|pdfjs/i.test(contents), `${directory}/${file}: PDF viewer reference remains`);
    if (file === 'app.js') assert(!/\bq\.pdf\b/.test(contents), `${directory}/${file}: question UI still depends on q.pdf`);
  }
  assert(!fs.existsSync(path.join(root, directory, 'pdf-viewer.html')), `${directory}: obsolete pdf-viewer.html remains in delivered app`);
}

checkUi('docs');
checkUi('study-web/dist');

const publicQuestions = json('docs/data/questions.json');
const publicAnswers = json('docs/data/answers.json');
assert.equal(publicQuestions.length, 60, 'public web must contain 60 original questions');
assert.equal(Object.keys(publicAnswers).length, 60, 'public answer file must contain 60 entries');
for (const q of publicQuestions) {
  assert.equal(q.kind, 'original', `${q.id}: public question must be labeled original`);
  assert(!unavailablePrompt.test(q.prompt ?? ''), `${q.id}: question asks learner to consult hidden PDF`);
  assert(!Object.hasOwn(q, 'pdf'), `${q.id}: obsolete PDF field remains in public bank`);
  for (const key of Object.keys(q)) assert(!answerFields.has(key), `${q.id}: question contains answer field ${key}`);
  assert(Object.hasOwn(publicAnswers, q.id), `${q.id}: answer missing from separate answer file`);
}
for (const directory of ['docs', 'study-web/dist']) {
  checkPublicValue(json(`${directory}/data/sources.json`), `${directory}/data/sources.json`);
  checkPublicValue(json(`${directory}/data/questions.json`), `${directory}/data/questions.json`);
}

let privateQuestionCount = null;
if (process.argv.includes('--private')) {
  checkUi('private-study/web');
  const privateQuestions = json('private-study/web/data/questions.json');
  const privateAnswers = json('private-study/web/data/answers.json');
  privateQuestionCount = privateQuestions.length;
  assert.equal(Object.keys(privateAnswers).length, privateQuestions.length, 'private question/answer count differs');
  const official = privateQuestions.filter(q => q.kind === 'official-sample');
  assert.equal(official.length, 1040, 'private learning app must retain all 1040 official examples');
  const privateRoot = path.resolve(root, 'private-study');
  const privateWebRoot = path.resolve(root, 'private-study/web');
  for (const q of official) {
    assert(typeof q.prompt === 'string' && q.prompt.trim().length > 10, `${q.id}: extracted question prompt missing`);
    assert(!unavailablePrompt.test(q.prompt), `${q.id}: official question still relies on hidden PDF`);
    assert(!Object.hasOwn(q, 'pdf'), `${q.id}: obsolete q.pdf field remains`);
    const imageValues = [q.image, ...(Array.isArray(q.images) ? q.images : [])].filter(Boolean);
    const verifiedImagePaths = imageValues.map(image => {
      const imageSource = typeof image === 'string' ? image : image.src ?? image.path ?? image.url;
      assert(typeof imageSource === 'string' && imageSource.length > 0, `${q.id}: image source missing`);
      assert(!/^(?:[a-z][a-z\d+.-]*:|\/\/)/i.test(imageSource), `${q.id}: local official image must be a relative file`);
      const imagePath = path.resolve(privateWebRoot, imageSource.split(/[?#]/)[0]);
      const relative = path.relative(privateRoot, imagePath);
      assert(relative !== '..' && !relative.startsWith(`..${path.sep}`) && !path.isAbsolute(relative), `${q.id}: official image leaves private-study`);
      assert(fs.existsSync(imagePath) && fs.statSync(imagePath).isFile() && fs.statSync(imagePath).size > 0, `${q.id}: question image missing or empty (${imageSource})`);
      assert(/\.(?:png|jpe?g|webp)$/i.test(imagePath), `${q.id}: question visual must be a raster crop`);
      return imagePath;
    });
    assert(Array.isArray(q.options) && q.options.length >= 4 && q.options.every(option => typeof option === 'string' && option.trim().length > 0), `${q.id}: invalid official options`);
    const placeholderOptions = q.options.some(option => /^[①②③④⑤⑥⑦⑧⑨⑩\d]+\s*(?:번|[.)])?$/.test(option.trim()));
    assert(!placeholderOptions || verifiedImagePaths.length > 0, `${q.id}: numbered options require an existing crop containing the original alternatives`);
    assert(Object.hasOwn(privateAnswers, q.id), `${q.id}: separated official answer missing`);
    for (const key of Object.keys(q)) assert(!answerFields.has(key), `${q.id}: official question contains answer field ${key}`);
  }
}

console.log(`PASS: public 60 questions and separated answers; no PDF viewer UI or private/local source paths${privateQuestionCount === null ? '' : `; ${privateQuestionCount} private text questions checked`}.`);

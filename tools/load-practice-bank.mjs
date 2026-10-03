import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

export const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const read = relative => JSON.parse(fs.readFileSync(path.join(projectRoot, relative), 'utf8').replace(/^\uFEFF/, ''));

export function loadPracticeBank() {
  const questions = read('data/practice-questions.json');
  const answers = read('data/practice-answers.json');
  for (const name of ['ncs', 'programming', 'database']) {
    const questionPath = `data/expansion/${name}-questions.json`;
    const answerPath = `data/expansion/${name}-answers.json`;
    if (!fs.existsSync(path.join(projectRoot, questionPath)) && !fs.existsSync(path.join(projectRoot, answerPath))) continue;
    const addition = read(questionPath), key = read(answerPath);
    for (const q of addition) {
      if (Object.hasOwn(answers, q.id)) throw new Error(`Duplicate practice ID: ${q.id}`);
      questions.push(q);
    }
    Object.assign(answers, key);
  }
  return { questions, answers };
}

export function loadBankManifest() { return read('data/practice-bank-manifest.json'); }

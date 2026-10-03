"""Convert local official examples into question crops and separate plain-text answers.

Only the conversion code is public. Official text and rendered fragments remain
inside the ignored private-study directory. No PDF viewer is used by the app.
"""
import json
import re
from collections import defaultdict
from pathlib import Path

import pypdfium2 as pdfium

ROOT = Path(__file__).resolve().parent.parent
PRIVATE = ROOT / 'private-study'
LEGACY = PRIVATE / 'ncs-questions-source.json'
if not LEGACY.exists():
    LEGACY.write_bytes((PRIVATE / 'ncs-questions.json').read_bytes())
questions = json.loads(LEGACY.read_text(encoding='utf-8'))
answers = json.loads((PRIVATE / 'ncs-answers.json').read_text(encoding='utf-8'))
analysis = json.loads((ROOT / 'tmp/pdfs/analysis.json').read_text(encoding='utf-8'))
OUT = PRIVATE / 'question-images'
OUT.mkdir(exist_ok=True)
groups = defaultdict(list)
for q in questions:
    groups[q['sourceId']].append(q)
report = {'questions': 0, 'crops': 0, 'optionsAsText': 0, 'explanationsAsText': 0, 'warnings': []}


def normalized(text):
    text = text.replace('\r', '').replace('\u00a0', ' ')
    return re.sub(r'\n{3,}', '\n\n', text).strip()


def box_at(textpage, text_index):
    char_index = pdfium.raw.FPDFText_GetCharIndexFromTextIndex(textpage, text_index)
    if char_index < 0:
        return None
    return textpage.get_charbox(char_index)


def locate(q, texts, pages):
    index = q['page'] - 1
    number = q.get('printedNumber', q['number'])
    raw = texts[index]
    pattern = r'(?m)(?:^|\n)[ \t\r]*(?:R|P-)?0?' + str(number) + r'[.](?!\d)[ \t\r\n]*'
    matches = list(re.finditer(pattern, raw))
    if not matches and q['sourceId'] == 'ncs-2023-communication' and q['number'] == 28:
        matches = list(re.finditer(r'(?m)(?:^|\n)[ \t\r]*28[ \t]+', raw))
    if not matches:
        matches = list(re.finditer(r'(?<!\d)(?:R|P-)?0?' + str(number) + r'[.](?!\d)[ \t\r\n]*',raw))
    valid = []
    for m in matches:
        digit = re.search(r'\d', m.group())
        b = box_at(pages[index].get_textpage(), m.start() + digit.start())
        if b and 25 < b[0] < 140:
            y = pages[index].get_height() - b[3]
            if 30 < y < pages[index].get_height() - 40:
                valid.append((y, m, b))
    if not valid:
        raise ValueError(f"Question header not found: {q['id']} page {q['page']}")
    y, match, box = sorted(valid, key=lambda item: item[0])[0]
    tail = normalized(raw[match.end():])
    prompt = tail.split('①')[0].strip()
    # Keep the actual stem short; the complete question is in its exact crop.
    lines = [line.strip() for line in prompt.splitlines() if line.strip()]
    prompt = ' '.join(lines[:3])
    if len(prompt) > 250:
        prompt = prompt[:250].rsplit(' ', 1)[0] + '…'
    if len(prompt) < 10:
        prompt = f"{q['category']} 공식 예시 {q['number']}번: 아래 문제의 정답을 선택하세요."
    return {'page': index, 'top': y, 'match': match, 'prompt': prompt}


def render_fragment(pdf, page_idx, top, bottom, filename):
    page = pdf[page_idx]
    width, height = page.get_size()
    top = max(36, top)
    bottom = min(height - 47, bottom)
    if bottom - top < 15:
        return None
    target = OUT / filename
    if not target.exists():
        # PDFium renders only this document region; no page UI/header/footer.
        image = page.render(scale=1.65, crop=(48, height - bottom, 48, top))
        image.to_pil().save(target, format='WEBP', quality=92)
        image.close()
    report['crops'] += 1
    return {'src': target.relative_to(ROOT).as_posix(), 'sourcePage': page_idx + 1,
            'cropTop': round(top, 2), 'cropBottom': round(bottom, 2)}


for source_id, bank in groups.items():
    pdf = pdfium.PdfDocument(str(ROOT / bank[0]['pdf']))
    pages = [pdf[i] for i in range(len(pdf))]
    texts = [page.get_textpage().get_text_range() for page in pages]
    positions = [locate(q, texts, pages) for q in bank]
    starts_by_page = defaultdict(list)
    for q, position in zip(bank, positions):
        starts_by_page[position['page']].append((position['top'], q['number']))
    own_images = {}
    own_texts = {}
    for i, (q, position) in enumerate(zip(bank, positions)):
        start_page = position['page']
        end_position = positions[i + 1] if i + 1 < len(positions) else None
        end_page = end_position['page'] if end_position else len(pages) - 1
        first_on_page = min(starts_by_page[start_page])[1] == q['number']
        page_margin = 40 if '-2023-' in source_id else 68
        top = page_margin if first_on_page else position['top'] - 7
        # Once all four alternatives are on this page, later pages are new
        # material. Avoid carrying the next question's passage into this one.
        if end_page > start_page:
            start_text = pages[start_page].get_textpage().get_text_bounded(left=48,
                bottom=54, right=pages[start_page].get_width()-48,
                top=pages[start_page].get_height()-top)
            if all(mark in start_text for mark in '①②③④'):
                end_page = start_page
        images = []
        fragment_text = []
        for page_idx in range(start_page, end_page + 1):
            page = pages[page_idx]
            region_top = top if page_idx == start_page else page_margin
            region_bottom = end_position['top'] - 12 if end_position and page_idx == end_position['page'] else page.get_height() - 54
            fragment = render_fragment(pdf, page_idx, region_top, region_bottom, f"{q['id']}-{page_idx + 1}.webp")
            if fragment:
                fragment['caption'] = f"문제 {q['number']}번" + (' · 이어지는 자료' if page_idx > start_page else '')
                images.append(fragment)
                textpage = page.get_textpage()
                fragment_text.append(textpage.get_text_bounded(left=48, bottom=page.get_height() - region_bottom,
                                                               right=page.get_width() - 48, top=page.get_height() - region_top))
        if not images:
            raise ValueError('Empty question crop: ' + q['id'])
        own_images[q['number']] = images
        own_texts[q['number']] = normalized('\n'.join(fragment_text))
    shared_ranges = []
    for page_idx, raw in enumerate(texts):
        for m in re.finditer(r'(?m)(?:^|\n)[ \t\r]*\[?0?(\d{1,3})[ \t]*[~～][ \t]*0?(\d{1,3})', raw):
            a, b = map(int, m.groups())
            if 1 <= a <= b <= len(bank):
                shared_ranges.append((a, b, page_idx))
    for q, position in zip(bank, positions):
        number = q['number']
        images = []
        relevant = [(a, b, p) for a, b, p in shared_ranges if a <= number <= b]
        if relevant:
            a, b, passage_page = relevant[-1]
            first_pos = positions[a - 1]
            # Material before the first group question, potentially across pages.
            for page_idx in range(passage_page, first_pos['page'] + 1):
                end = first_pos['top'] - 12 if page_idx == first_pos['page'] else pages[page_idx].get_height() - 54
                shared = render_fragment(pdf, page_idx, 40 if '-2023-' in source_id else 68, end, f"{source_id}-shared-{a}-{b}-{page_idx + 1}.webp")
                if shared:
                    shared['caption'] = f"{a}~{b}번 공통 자료"
                    images.append(shared)
            # Some layouts put the common material inside the first question.
            if number != a:
                for img in own_images[a]:
                    images.append({**img, 'caption': f"{a}~{b}번 공통 자료 · {a}번 문항 포함"})
        images += own_images[number]
        seen = set()
        q['images'] = [img for img in images if not (img['src'] in seen or seen.add(img['src']))]
        q['prompt'] = position['prompt']
        q['sourcePdf'] = q.pop('pdf')
        q['imageContainsOptions'] = True
        # Exact option wording is supplemental to the complete visual fragment.
        text = own_texts[number]
        option_matches = list(re.finditer(r'([①②③④])[ \t]*', text))
        sequence = []
        for k in range(len(option_matches) - 3):
            if ''.join(m.group(1) for m in option_matches[k:k + 4]) == '①②③④':
                sequence = option_matches[k:k + 4]
        extracted = []
        if sequence:
            for k, marker in enumerate(sequence):
                end = sequence[k + 1].start() if k < 3 else len(text)
                option = ' '.join(text[marker.end():end].split())
                extracted.append(option)
        if len(extracted) == 4 and all(1 <= len(option) <= 200 for option in extracted) and not any('\ue000' <= c <= '\uf8ff' for option in extracted for c in option):
            q['options'] = extracted
            report['optionsAsText'] += 1
        else:
            q['options'] = ['①번', '②번', '③번', '④번']
        q['rendering'] = 'question-fragments'
        report['questions'] += 1
    pdf.close()
    print(json.dumps({'source': source_id, 'questions': len(bank), 'finished': report['questions']}), flush=True)

# The latest publication was already parsed into complete explanations.
for q in questions:
    answer = answers[q['id']]
    if '-2024-' in q['id']:
        slug = q['sourceId'].removeprefix('ncs-2024-')
        explanation = analysis[slug]['answers'].get(str(q['number']), {}).get('explanation', '')
        if len(explanation) > 0:
            answer['explanation'] = normalized(explanation)
            report['explanationsAsText'] += 1
    if answer.get('note') and answer['note'] not in answer['explanation']:
        answer['explanation'] += '\n\n' + answer['note']
    if 'pdf' in answer:
        answer['sourcePdf'] = answer.pop('pdf')

# Extract older explanatory paragraphs between numbered answer headings.
for source_id, bank in groups.items():
    if '-2023-' not in source_id:
        continue
    answer_path = ROOT / answers[bank[0]['id']]['sourcePdf']
    pdf = pdfium.PdfDocument(str(answer_path))
    content = '\n'.join(normalized(page.get_textpage().get_text_range()) for page in pdf)
    matches = list(re.finditer(r'(?<!\d)(\d{1,3})[.]\s*정답\s*([①②③④⑤])', content))
    for i, match in enumerate(matches):
        number = int(match.group(1))
        qid = f"{source_id}-{number:03d}"
        if qid not in answers or answers[qid]['verification'] == 'derived':
            continue
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        explanation = normalized(content[match.end():end])
        explanation = re.sub(r'정답 및 해설\s*\d*', '', explanation)
        if len(explanation) > 0:
            answers[qid]['explanation'] = explanation
            report['explanationsAsText'] += 1
    pdf.close()

assert len(questions) == len(answers) == 1040
assert all(q['images'] and len(q['prompt']) > 10 for q in questions)
for name, value in [('ncs-questions.json', questions), ('ncs-answers.json', answers), ('conversion-report.json', report)]:
    (PRIVATE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(report), flush=True)

"""Keep equations in local official explanations legible without embedding PDFs."""
import json,re
from pathlib import Path
from collections import defaultdict
import pypdfium2 as pdfium
ROOT=Path(__file__).resolve().parent.parent
PRIVATE=ROOT/'private-study'
answers=json.loads((PRIVATE/'ncs-answers.json').read_text('utf-8'))
questions=json.loads((PRIVATE/'ncs-questions.json').read_text('utf-8'))
groups=defaultdict(list)
for q in questions:groups[q['sourceId']].append(q)
out=PRIVATE/'answer-images';out.mkdir(exist_ok=True)
image_count=0
for source,bank in groups.items():
 pdf=pdfium.PdfDocument(str(ROOT/answers[bank[0]['id']]['sourcePdf']))
 pages=[pdf[i] for i in range(len(pdf))]
 texts=[page.get_textpage().get_text_range() for page in pages]
 positions={}
 for q in bank:
  a=answers[q['id']];page_idx=a['page']-1;raw=texts[page_idx]
  number=17 if source=='ncs-2024-math' and q['number']==97 else q['number']
  if '-2024-' in source:
   category=re.escape(q['category']) if q['category']!='문제해결능력' else r'문제해결(?:능력|력)?'
   pattern=category+r'(?:\s*\([^)]*\))?\s+'+str(number)+r'(?!\d)'
  else:pattern=r'(?<!\d)'+str(number)+r'[.]\s*정답'
  candidates=[]
  for m in re.finditer(pattern,raw):
   tp=pages[page_idx].get_textpage();ci=pdfium.raw.FPDFText_GetCharIndexFromTextIndex(tp,m.start());box=tp.get_charbox(ci);top=pages[page_idx].get_height()-box[3]
   if 25<top<pages[page_idx].get_height()-35:candidates.append(top)
  positions[q['id']]=(page_idx,min(candidates) if candidates else 45)
 for i,q in enumerate(bank):
  a=answers[q['id']]
  has_equations=any('\ue000'<=c<='\uf8ff' for c in a['explanation'])
  if q['category']!='수리능력' and not has_equations:continue
  page_idx,top=positions[q['id']]
  nextpos=positions[bank[i+1]['id']] if i+1<len(bank) else (len(pages)-1,pages[-1].get_height()-45)
  last_idx=max(page_idx,nextpos[0]);images=[]
  for n in range(page_idx,last_idx+1):
   page=pages[n];start=max(35,top-7) if n==page_idx else 38
   end=nextpos[1]-9 if n==nextpos[0] else page.get_height()-42
   if end-start<15:continue
   file=out/f"{q['id']}-{n+1}.webp"
   if not file.exists():page.render(scale=1.65,crop=(38,page.get_height()-end,38,start)).to_pil().save(file,format='WEBP',quality=93)
   images.append({'src':file.relative_to(ROOT).as_posix(),'caption':f"{q['number']}번 공식 풀이",'sourcePage':n+1})
  if images:
   a['images']=images;image_count+=len(images)
   if has_equations:
    a['explanation']=f"정답은 {a['correctIndex']+1}번입니다. 수식을 포함한 공식 풀이를 아래에 표시했습니다."
    if a.get('note'):a['explanation']+='\n\n'+a['note']
 pdf.close()
for a in answers.values():
 if '원본 해설 PDF' in a['explanation']:
  a['explanation']=f"공식 정답은 {a['correctIndex']+1}번입니다. 이 문항은 공식 정답 확인을 제공합니다."
  if a.get('note'):a['explanation']+='\n\n'+a['note']
(PRIVATE/'ncs-answers.json').write_text(json.dumps(answers,ensure_ascii=False,indent=2)+'\n','utf-8')
print(json.dumps({'answerImages':image_count,'remainingPDFInstructions':sum('원본 해설 PDF' in a['explanation'] for a in answers.values())}))

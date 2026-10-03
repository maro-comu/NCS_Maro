"""Check local question crops, alternatives, separate answers and source pages."""
import json,re
from pathlib import Path
import pypdfium2 as pdfium
ROOT=Path(__file__).resolve().parent.parent
questions=json.loads((ROOT/'private-study/ncs-questions.json').read_text('utf-8'))
answers=json.loads((ROOT/'private-study/ncs-answers.json').read_text('utf-8'))
assert len(questions)==len(answers)==1040
assert len({q['id'] for q in questions})==1040
assert set(answers)=={q['id'] for q in questions}
pdfs={}
warnings=[]
for q in questions:
 assert 'pdf' not in q and 'correctIndex' not in q and 'explanation' not in q
 assert 0<=answers[q['id']]['correctIndex']<len(q['options'])
 assert q['images'] and len(q['prompt'])>10
 assert '원본 해설 PDF' not in answers[q['id']]['explanation']
 pdf=pdfs.setdefault(q['sourcePdf'],pdfium.PdfDocument(str(ROOT/q['sourcePdf']))) if q['sourcePdf'] not in pdfs else pdfs[q['sourcePdf']]
 text=''
 for image in q['images']:
  file=ROOT/image['src'];assert file.is_file() and file.stat().st_size>500
  assert file.resolve().is_relative_to((ROOT/'private-study').resolve())
  if image['caption'].startswith('문제 '+str(q['number'])+'번'):
   page=pdf[image['sourcePage']-1]
   text+=page.get_textpage().get_text_bounded(left=48,right=page.get_width()-48,bottom=page.get_height()-image['cropBottom'],top=page.get_height()-image['cropTop'])
 if not all(marker in text for marker in '①②③④'):
  warnings.append({'id':q['id'],'present':[x for x in '①②③④' if x in text]})
 for image in answers[q['id']].get('images',[]):
  assert (ROOT/image['src']).is_file()
report={'officialQuestions':1040,'answerCoverage':1040,'choiceMarkerWarnings':warnings}
(ROOT/'private-study/crop-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf-8')
print(json.dumps(report,ensure_ascii=False))
for pdf in pdfs.values():pdf.close()

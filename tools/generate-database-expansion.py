"""Reproducible original DB exercises. SQL choices are evaluated with sqlite3.

Only writes data/expansion/database-*.json. No exam/publisher text is used.
Run: python tools/generate-database-expansion.py [--check]
"""
from __future__ import annotations
import collections
import json
import math
import pathlib
import re
import sqlite3
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEST = ROOT / 'data' / 'expansion'
QUESTIONS = []
ANSWERS = {}
AUDIT = []
DOCS = [
    {'title': 'SQLite SELECT 공식 문서', 'url': 'https://www.sqlite.org/lang_select.html'},
    {'title': 'SQLite 윈도 함수 공식 문서', 'url': 'https://www.sqlite.org/windowfunctions.html'},
    {'title': 'SQLite SQL 표현식 공식 문서', 'url': 'https://www.sqlite.org/lang_expr.html'},
    {'title': 'PostgreSQL 제약 조건 공식 문서', 'url': 'https://www.postgresql.org/docs/current/ddl-constraints.html'},
    {'title': 'PostgreSQL 트랜잭션 격리 공식 문서', 'url': 'https://www.postgresql.org/docs/current/transaction-iso.html'},
    {'title': 'PostgreSQL 복합 인덱스 공식 문서', 'url': 'https://www.postgresql.org/docs/current/indexes-multicolumn.html'},
]


def scalar(v):
    if v is None:
        return 'NULL'
    if isinstance(v, float):
        return str(round(v, 4)).rstrip('0').rstrip('.') if not v.is_integer() else str(int(v))
    return str(v)


def result(rows):
    if not rows:
        return '반환 행 없음'
    return ' / '.join('(' + ', '.join(scalar(x) for x in row) + ')' for row in rows)


def add(question, correct, choices, explanation, steps, verification='original-reviewed'):
    assert len(choices) == 4 and len(set(choices)) == 4, (question, choices)
    i = len(QUESTIONS)
    offset = (choices.index(correct) - i % 4) % 4
    shifted = choices[offset:] + choices[:offset]
    qid = f'extra-db-{i + 1:04d}'
    question.update(id=qid, track='db', sourceId='original', kind='original', options=shifted)
    QUESTIONS.append(question)
    ANSWERS[qid] = {
        'correctIndex': shifted.index(correct),
        'explanation': explanation,
        'detailedSteps': steps,
        'verification': verification,
    }
    return qid


SCENARIOS = [
    ('상담 배정', [[1,'A',30,1,'A-접수',None,None],[2,'A',50,0,'A-보완',5,1],
                 [3,'B',50,1,'B-상담',None,1],[4,'B',80,1,'B-심사',10,3],
                 [5,'C',20,0,'A-완료',0,3],[6,'C',None,1,'C-대기',4,None]],
     [[1,1,2],[2,1,4],[3,2,3],[4,3,5],[5,4,1],[6,None,7]], 40),
    ('전산 작업', [[1,'B',65,0,'A-백업',9,None],[2,'A',25,1,'B-점검',None,1],
                 [3,'A',65,1,'A-배포',3,1],[4,'C',10,1,'C-복구',None,2],
                 [5,'B',None,0,'B-감사',8,2],[6,'C',45,1,'A-설치',0,3]],
     [[1,2,4],[2,2,2],[3,3,8],[4,5,3],[5,5,6],[6,None,1]], 35),
    ('교육 신청', [[1,'C',15,1,'B-보안',None,None],[2,'B',70,1,'A-SQL',0,1],
                 [3,'C',90,0,'C-설계',7,1],[4,'A',70,1,'A-통계',None,2],
                 [5,'A',40,0,'B-실습',2,2],[6,'B',None,1,'A-기초',6,None]],
     [[1,1,5],[2,3,1],[3,3,9],[4,4,4],[5,6,2],[6,None,6]], 50),
    ('보증 서류', [[1,'A',55,1,'C-초안',1,None],[2,'C',85,0,'A-검토',None,1],
                 [3,'B',35,1,'A-수정',4,1],[4,'C',85,1,'B-확인',3,3],
                 [5,'B',10,0,'A-제출',None,3],[6,'A',None,1,'B-대기',0,4]],
     [[1,1,7],[2,4,1],[3,4,5],[4,6,3],[5,6,8],[6,None,2]], 45),
]

# Different population sizes and tail states make the same SQL structure operate
# on different cardinalities and NULL/duplicate patterns rather than reskinning IDs.
SCENARIOS[1][1].append([7,'A',35,1,'C-전환',2,3])
SCENARIOS[2][1].extend([[7,'B',50,0,'B-연습',None,4], [8,'C',20,1,'C-복습',3,4]])
SCENARIOS[3][1].extend([[7,'C',45,1,'A-접수',None,4], [8,'B',65,1,'B-검증',5,6], [9,'A',25,0,'C-보완',2,6]])


def database(seed):
    name, rows, work, threshold = SCENARIOS[seed]
    con = sqlite3.connect(':memory:')
    con.executescript('''
      CREATE TABLE items(id INTEGER PRIMARY KEY, team TEXT, value INTEGER,
                         active INTEGER, title TEXT, extra INTEGER, parent_id INTEGER);
      CREATE TABLE groups(team TEXT PRIMARY KEY, label TEXT);
      CREATE TABLE work(id INTEGER PRIMARY KEY, item_id INTEGER, units INTEGER);
    ''')
    con.executemany('INSERT INTO items VALUES (?,?,?,?,?,?,?)', rows)
    con.executemany('INSERT INTO groups VALUES (?,?)', [('A','지원'),('B','심사'),('D','미배정')])
    con.executemany('INSERT INTO work VALUES (?,?,?)', work)
    con.commit()
    return con


def fixture_text(seed, query):
    name, rows, work, threshold = SCENARIOS[seed]
    chunks = [f'가상의 {name} 데이터. 각 표의 첫 줄은 열 이름이며 NULL은 값 없음이다.']
    if re.search(r'\bitems\b', query):
        allcols = ['id','team','value','active','title','extra','parent_id']
        cols = [c for c in allcols if re.search(r'\b' + c + r'\b', query)]
        if not cols or 'SELECT *' in query.upper():
            cols = allcols
        # The input rows keep their identifiers even when a query only aggregates a value.
        if 'id' not in cols:
            cols.insert(0, 'id')
        ix = [allcols.index(c) for c in cols]
        chunks += ['items(' + ', '.join(cols) + ')',
                   '\n'.join(' | '.join(scalar(row[n]) for n in ix) for row in rows)]
    if re.search(r'\bgroups\b', query):
        chunks += ['groups(team, label)', 'A | 지원\nB | 심사\nD | 미배정']
    if re.search(r'\bwork\b', query):
        chunks += ['work(id, item_id, units)', '\n'.join(' | '.join(scalar(x) for x in row) for row in work)]
    return '\n\n'.join(chunks)


SQL = []


def sql(key, topic, category, title, query, wrong, reasoning, difficulty='보통', mutation=None):
    SQL.append(dict(key=key, topic=topic, category=category, title=title, query=query,
                    wrong=wrong, reasoning=reasoning, difficulty=difficulty, mutation=mutation))


sql('distinct', 'DISTINCT 중복 제거', 'SQL 기초', '중복 팀 제거',
    'SELECT DISTINCT team FROM items ORDER BY team;',
    ['SELECT team FROM items ORDER BY team;', 'SELECT DISTINCT team FROM groups ORDER BY team;', 'SELECT team FROM items WHERE active=0 ORDER BY team;'],
    'DISTINCT는 SELECT에 나온 team 값이 같은 행을 하나로 합친다. items의 팀만 대상으로 하며 groups의 미배정 팀을 포함하지 않는다.', '기초')
sql('projection', '산술식과 별칭', 'SQL 기초', '보정 점수 계산',
    'SELECT id, value + COALESCE(extra,0) AS total FROM items WHERE id<=3 ORDER BY id;',
    ['SELECT id,value FROM items WHERE id<=3 ORDER BY id;', 'SELECT id,value+extra FROM items WHERE id<=3 ORDER BY id;', 'SELECT id,value-COALESCE(extra,0) FROM items WHERE id<=3 ORDER BY id;'],
    'COALESCE(extra,0)는 추가 점수가 NULL이면 0으로 바꾼다. 그 다음 value에 더한다. 별칭 total은 계산값의 열 이름이며 행 수를 바꾸지 않는다.')
sql('and', 'AND 조건', '조건과 NULL', '두 조건을 함께 만족하는 행',
    'SELECT id FROM items WHERE value>{t} AND active=1 ORDER BY id;',
    ['SELECT id FROM items WHERE value>{t} OR active=1 ORDER BY id;', 'SELECT id FROM items WHERE value>{t} ORDER BY id;', 'SELECT id FROM items WHERE active=1 ORDER BY id;'],
    'AND는 두 조건이 모두 참인 행만 남긴다. value가 NULL인 행의 비교는 UNKNOWN이므로 active=1이어도 통과하지 않는다.', '기초')
sql('or', 'OR 조건', '조건과 NULL', '어느 하나를 만족하는 행',
    "SELECT id FROM items WHERE team='A' OR value>{t} ORDER BY id;",
    ["SELECT id FROM items WHERE team='A' AND value>{t} ORDER BY id;", "SELECT id FROM items WHERE team='A' ORDER BY id;", 'SELECT id FROM items WHERE value>{t} ORDER BY id;'],
    'OR는 팀 A 또는 기준 점수 초과 중 하나만 참이어도 선택한다. 두 조건을 동시에 만족한 행도 한 번만 반환한다.', '기초')
sql('precedence', 'AND와 OR 우선순위', '조건과 NULL', '괄호 없는 복합 조건',
    "SELECT id FROM items WHERE team='A' OR team='B' AND active=1 ORDER BY id;",
    ["SELECT id FROM items WHERE (team='A' OR team='B') AND active=1 ORDER BY id;", "SELECT id FROM items WHERE team='B' AND active=1 ORDER BY id;", "SELECT id FROM items WHERE team IN ('A','B') ORDER BY id;"],
    'AND가 OR보다 먼저 결합하므로 team=A OR (team=B AND active=1)로 읽는다. 팀 A는 active 값과 관계없이 포함된다.')
sql('parentheses', '괄호로 조건 묶기', '조건과 NULL', '팀 범위 안의 활성 행',
    "SELECT id FROM items WHERE (team='A' OR team='B') AND active=1 ORDER BY id;",
    ["SELECT id FROM items WHERE team='A' OR team='B' AND active=1 ORDER BY id;", "SELECT id FROM items WHERE active=1 ORDER BY id;", "SELECT id FROM items WHERE team='A' AND active=1 ORDER BY id;"],
    '괄호로 팀 조건을 먼저 묶고 활성 여부를 검사한다. 팀 C나 비활성 행은 결과에서 제외된다.')
sql('between', 'BETWEEN 양끝 포함', '조건과 NULL', '구간 점수 필터',
    'SELECT id FROM items WHERE value BETWEEN {t} AND 80 ORDER BY id;',
    ['SELECT id FROM items WHERE value>{t} AND value<80 ORDER BY id;', 'SELECT id FROM items WHERE value<{t} OR value>80 ORDER BY id;', 'SELECT id FROM items WHERE value>={t} ORDER BY id;'],
    'BETWEEN a AND b는 value>=a AND value<=b와 같아 양 끝값을 포함한다. NULL은 이 비교에서 참이 아니다.', '기초')
sql('in-list', 'IN 목록 검사', '조건과 NULL', '지정 팀 목록 조회',
    "SELECT id FROM items WHERE team IN ('A','C') ORDER BY id;",
    ["SELECT id FROM items WHERE team='A' ORDER BY id;", "SELECT id FROM items WHERE team='C' ORDER BY id;", "SELECT id FROM items WHERE team NOT IN ('A','C') ORDER BY id;"],
    'IN은 목록 중 같은 값이 하나라도 있으면 참이다. A와 C 팀의 행을 모두 고르고 B 팀은 제외한다.', '기초')
sql('like-prefix', 'LIKE 접두사', '문자열 함수', '제목 시작 문자 조회',
    "SELECT id FROM items WHERE title LIKE 'A-%' ORDER BY id;",
    ["SELECT id FROM items WHERE title='A-%' ORDER BY id;", "SELECT id FROM items WHERE title LIKE '%A' ORDER BY id;", "SELECT id FROM items WHERE title NOT LIKE 'A-%' ORDER BY id;"],
    'LIKE의 %는 길이 0 이상인 문자열을 뜻한다. A-%는 A-로 시작하는 제목을 선택하며 문자열 A-% 자체와 같다는 뜻이 아니다.', '기초')
sql('like-character', 'LIKE 한 문자 와일드카드', '문자열 함수', '하이픈 앞 한 글자 패턴',
    "SELECT id FROM items WHERE title LIKE '_-__' ORDER BY id;",
    ["SELECT id FROM items WHERE title LIKE 'A-%' ORDER BY id;", "SELECT id FROM items WHERE title LIKE '_-___' ORDER BY id;", "SELECT id FROM items WHERE title LIKE '%SQL' ORDER BY id;"],
    '밑줄 _는 정확히 한 문자를 뜻한다. _-__는 한 글자, 하이픈, 두 글자로 이루어진 제목과 일치한다. 한글도 이 예에서는 문자 하나로 계산된다.')
sql('is-null', 'IS NULL', '조건과 NULL', '추가값이 없는 행',
    'SELECT id FROM items WHERE extra IS NULL ORDER BY id;',
    ['SELECT id FROM items WHERE extra=NULL ORDER BY id;', 'SELECT id FROM items WHERE extra=0 ORDER BY id;', 'SELECT id FROM items WHERE extra IS NOT NULL ORDER BY id;'],
    '값이 없는 상태는 IS NULL로 검사한다. extra=NULL은 UNKNOWN을 만들어 WHERE를 통과하지 않고 0은 NULL과 다르다.', '기초')
sql('is-not-null', 'IS NOT NULL', '조건과 NULL', '추가값이 존재하는 행',
    'SELECT id FROM items WHERE extra IS NOT NULL ORDER BY id;',
    ['SELECT id FROM items WHERE extra IS NULL ORDER BY id;', 'SELECT id FROM items WHERE extra>0 ORDER BY id;', 'SELECT id FROM items WHERE extra<>NULL ORDER BY id;'],
    'IS NOT NULL은 값 0도 포함한다. 양수 조건 extra>0은 값이 존재해도 0인 행을 버리므로 다르다.', '기초')
sql('null-equality', 'NULL 비교의 UNKNOWN', '조건과 NULL', 'NULL과 같다는 비교',
    'SELECT id FROM items WHERE value=NULL ORDER BY id;',
    ['SELECT id FROM items WHERE value IS NULL ORDER BY id;', 'SELECT id FROM items WHERE value IS NOT NULL ORDER BY id;', 'SELECT id FROM items ORDER BY id;'],
    'NULL은 미확정 값이므로 =NULL의 결과는 참이 아니라 UNKNOWN이다. WHERE는 참인 행만 남겨 결과가 없다. NULL 자체를 찾으려면 IS NULL을 써야 한다.')
sql('coalesce', 'COALESCE 기본값', '조건과 NULL', '빈 추가값 대체',
    'SELECT id,COALESCE(extra,-1) FROM items WHERE id<=4 ORDER BY id;',
    ['SELECT id,extra FROM items WHERE id<=4 ORDER BY id;', 'SELECT id,COALESCE(extra,0) FROM items WHERE id<=4 ORDER BY id;', 'SELECT id,COALESCE(value,-1) FROM items WHERE id<=4 ORDER BY id;'],
    'COALESCE는 왼쪽부터 첫 NULL이 아닌 값을 반환한다. extra가 NULL인 행만 -1로 대체하고, 0을 포함한 실제 값은 그대로 둔다.', '기초')
sql('case', 'CASE 조건 분기', 'SQL 기초', '점수 구간 분류',
    "SELECT id,CASE WHEN value>{t} THEN '높음' WHEN value IS NULL THEN '미입력' ELSE '일반' END FROM items ORDER BY id;",
    ["SELECT id,CASE WHEN value>={t} THEN '높음' ELSE '일반' END FROM items ORDER BY id;", "SELECT id,CASE WHEN active=1 THEN '높음' ELSE '일반' END FROM items ORDER BY id;", "SELECT id,CASE WHEN value>{t} THEN '일반' ELSE '높음' END FROM items ORDER BY id;"],
    'CASE는 처음 참이 된 WHEN의 결과를 선택한다. 기준을 초과하면 높음, NULL이면 미입력, 나머지는 일반이다. NULL 비교가 참이 아니므로 별도 IS NULL 분기가 필요하다.')
sql('count-null', 'COUNT(*)와 COUNT(열)', '집계와 그룹', '전체 건수와 입력 건수',
    'SELECT COUNT(*),COUNT(value),COUNT(extra) FROM items;',
    ['SELECT COUNT(value),COUNT(*),COUNT(extra) FROM items;', 'SELECT COUNT(*),COUNT(*),COUNT(*) FROM items;', 'SELECT COUNT(DISTINCT team),COUNT(value),COUNT(extra) FROM items;'],
    'COUNT(*)는 모든 행을 세고 COUNT(열)은 그 열이 NULL인 행을 세지 않는다. 0이나 중복 값은 NULL이 아니므로 COUNT(열)에 포함된다.', '기초')
sql('sum', 'SUM과 NULL', '집계와 그룹', '활성 점수의 합',
    'SELECT SUM(value) FROM items WHERE active=1;',
    ['SELECT SUM(value) FROM items;', 'SELECT SUM(extra) FROM items WHERE active=1;', 'SELECT COUNT(value) FROM items WHERE active=1;'],
    'WHERE로 활성 행을 먼저 고른 다음 value를 더한다. SUM은 NULL을 제외하고 실제 값만 더하며 COUNT는 합계가 아니라 건수다.', '기초')
sql('average', 'AVG 분모의 의미', '집계와 그룹', '입력된 점수의 평균',
    'SELECT ROUND(AVG(value),2) FROM items;',
    ['SELECT ROUND(SUM(value)*1.0/COUNT(*),2) FROM items;', 'SELECT ROUND(AVG(COALESCE(value,0)),2) FROM items;', 'SELECT ROUND(AVG(extra),2) FROM items;'],
    'AVG(value)의 분모는 value가 NULL이 아닌 행 수다. 빈 값을 0으로 채우거나 COUNT(*)로 나누면 원래 평균과 다른 결과가 된다.')
sql('min-max', 'MIN과 MAX', '집계와 그룹', '점수 범위 확인',
    'SELECT MIN(value),MAX(value) FROM items;',
    ['SELECT MAX(value),MIN(value) FROM items;', 'SELECT MIN(extra),MAX(extra) FROM items;', 'SELECT MIN(id),MAX(id) FROM items;'],
    'MIN과 MAX는 NULL을 제외한 점수의 최솟값과 최댓값을 순서대로 반환한다. id나 extra의 범위는 value의 범위와 다르다.', '기초')
sql('count-distinct', 'COUNT(DISTINCT)', '집계와 그룹', '서로 다른 점수 수',
    'SELECT COUNT(DISTINCT value) FROM items;',
    ['SELECT COUNT(value) FROM items;', 'SELECT COUNT(*) FROM items;', 'SELECT COUNT(DISTINCT team) FROM items;'],
    'COUNT(DISTINCT value)는 NULL을 제외하고 같은 점수를 한 번만 센다. 중복된 점수와 전체 행 수를 구분해야 한다.')
sql('group-count', 'GROUP BY 건수', '집계와 그룹', '팀별 신청 수',
    'SELECT team,COUNT(*) FROM items GROUP BY team ORDER BY team;',
    ['SELECT team,COUNT(value) FROM items GROUP BY team ORDER BY team;', 'SELECT team,SUM(active) FROM items GROUP BY team ORDER BY team;', 'SELECT team,COUNT(*) FROM items WHERE active=1 GROUP BY team ORDER BY team;'],
    'GROUP BY team은 팀마다 한 그룹을 만들고 COUNT(*)는 각 그룹의 모든 행을 센다. 값이 NULL이거나 비활성인 행도 제외하지 않는다.')
sql('group-sum', 'GROUP BY 합계', '집계와 그룹', '팀별 점수 합계',
    'SELECT team,SUM(value) FROM items GROUP BY team ORDER BY team;',
    ['SELECT team,MAX(value) FROM items GROUP BY team ORDER BY team;', 'SELECT team,SUM(COALESCE(extra,0)) FROM items GROUP BY team ORDER BY team;', 'SELECT team,COUNT(*) FROM items GROUP BY team ORDER BY team;'],
    '팀별로 나눈 뒤 각 그룹의 value를 더한다. SUM은 NULL을 제외한다. MAX는 그룹의 대표 최댓값일 뿐 합계가 아니다.')
sql('having-count', 'HAVING 집계 조건', '집계와 그룹', '활성 건수가 있는 팀',
    'SELECT team,COUNT(*) FROM items WHERE active=1 GROUP BY team HAVING COUNT(*)>=2 ORDER BY team;',
    ['SELECT team,COUNT(*) FROM items GROUP BY team HAVING COUNT(*)>=2 ORDER BY team;', 'SELECT team,COUNT(*) FROM items WHERE active=1 GROUP BY team ORDER BY team;', 'SELECT team,COUNT(*) FROM items WHERE active=0 GROUP BY team ORDER BY team;'],
    'WHERE는 활성 행만 남기고, GROUP BY가 팀별로 묶으며, HAVING은 그 결과에서 건수가 2 이상인 그룹만 남긴다.')
sql('having-sum', 'HAVING 합계 비교', '집계와 그룹', '합계 기준을 넘는 팀',
    'SELECT team,SUM(value) FROM items GROUP BY team HAVING SUM(value)>100 ORDER BY team;',
    ['SELECT team,SUM(value) FROM items WHERE value>100 GROUP BY team ORDER BY team;', 'SELECT team,SUM(value) FROM items GROUP BY team ORDER BY team;', 'SELECT team,MAX(value) FROM items GROUP BY team HAVING MAX(value)>100 ORDER BY team;'],
    'HAVING SUM(value)>100은 한 행의 점수가 아니라 팀의 총합에 적용한다. WHERE value>100으로 바꾸면 합계를 내기 전에 행이 제거된다.')
sql('where-group', 'WHERE와 GROUP BY 순서', '집계와 그룹', '구간 필터 이후 팀별 합',
    'SELECT team,SUM(value) FROM items WHERE value>{t} GROUP BY team ORDER BY team;',
    ['SELECT team,SUM(value) FROM items GROUP BY team HAVING SUM(value)>{t} ORDER BY team;', 'SELECT team,SUM(value) FROM items GROUP BY team ORDER BY team;', 'SELECT team,COUNT(*) FROM items WHERE value>{t} GROUP BY team ORDER BY team;'],
    'WHERE로 개별 점수가 기준을 넘는 행만 남긴 뒤 팀별 합계를 계산한다. 합계가 기준을 넘는 팀을 고르는 HAVING과 처리 대상이 다르다.')
sql('empty-aggregate', '빈 집합 집계', '집계와 그룹', '조회 대상이 없을 때',
    "SELECT COUNT(*),SUM(value),AVG(value) FROM items WHERE team='Z';",
    ["SELECT COUNT(*),COALESCE(SUM(value),0),COALESCE(AVG(value),0) FROM items WHERE team='Z';", 'SELECT COUNT(*),SUM(value),AVG(value) FROM items;', "SELECT team,COUNT(*) FROM items WHERE team='Z' GROUP BY team;"],
    'GROUP BY가 없는 집계는 대상 행이 없어도 한 행을 반환한다. COUNT(*)는 0, SUM과 AVG는 NULL이다. GROUP BY를 넣으면 빈 입력에서 그룹 자체가 없다.')
sql('inner-join', 'INNER JOIN', '조인', '팀 이름이 등록된 항목',
    'SELECT i.id,g.label FROM items i JOIN groups g ON i.team=g.team ORDER BY i.id;',
    ['SELECT i.id,g.label FROM items i LEFT JOIN groups g ON i.team=g.team ORDER BY i.id;', 'SELECT i.id,g.label FROM items i CROSS JOIN groups g ORDER BY i.id,g.team;', 'SELECT i.id,g.label FROM items i JOIN groups g ON i.team<>g.team ORDER BY i.id,g.team;'],
    'INNER JOIN은 두 표의 team이 같은 조합만 남긴다. groups에 없는 C 팀은 결과에서 빠지며 groups의 D 팀도 연결할 items 행이 없다.', '기초')
sql('left-join', 'LEFT JOIN의 NULL 보충', '조인', '등록 여부와 관계없이 항목 보존',
    'SELECT i.id,g.label FROM items i LEFT JOIN groups g ON i.team=g.team ORDER BY i.id;',
    ['SELECT i.id,g.label FROM items i JOIN groups g ON i.team=g.team ORDER BY i.id;', 'SELECT i.id,g.label FROM items i LEFT JOIN groups g ON i.team=g.team WHERE g.team IS NULL ORDER BY i.id;', 'SELECT i.id,COALESCE(g.label,\'미등록\') FROM items i LEFT JOIN groups g ON i.team=g.team ORDER BY i.id;'],
    'LEFT JOIN은 왼쪽 items의 각 행을 유지한다. 오른쪽에서 같은 team을 못 찾으면 g.label을 NULL로 채우며 자동으로 미등록 문자열로 바꾸지 않는다.')
sql('anti-join', 'LEFT JOIN으로 미매칭 찾기', '조인', '등록되지 않은 팀의 항목',
    'SELECT i.id FROM items i LEFT JOIN groups g ON i.team=g.team WHERE g.team IS NULL ORDER BY i.id;',
    ['SELECT i.id FROM items i JOIN groups g ON i.team=g.team ORDER BY i.id;', 'SELECT i.id FROM items i LEFT JOIN groups g ON i.team=g.team WHERE g.team IS NOT NULL ORDER BY i.id;', 'SELECT i.id FROM items i ORDER BY i.id;'],
    '매칭된 groups.team은 기본키라 NULL이 될 수 없다. 따라서 LEFT JOIN 후 g.team IS NULL이면 같은 팀을 찾지 못한 items 행이다.')
sql('on-filter', '외부 조인의 ON 조건', '조인', '조인 단계에서 심사 팀만 연결',
    "SELECT i.id,g.label FROM items i LEFT JOIN groups g ON i.team=g.team AND g.label='심사' ORDER BY i.id;",
    ["SELECT i.id,g.label FROM items i LEFT JOIN groups g ON i.team=g.team WHERE g.label='심사' ORDER BY i.id;", 'SELECT i.id,g.label FROM items i LEFT JOIN groups g ON i.team=g.team ORDER BY i.id;', "SELECT i.id,g.label FROM items i JOIN groups g ON i.team=g.team AND g.label='심사' ORDER BY i.id;"],
    'ON의 추가 조건은 오른쪽 행을 연결할 수 있는지를 정한다. 연결되지 않아도 LEFT JOIN이므로 items 행을 보존하고 g.label을 NULL로 채운다.', '심화')
sql('where-filter', '외부 조인 후 WHERE 조건', '조인', '연결 후 심사 팀만 남기기',
    "SELECT i.id,g.label FROM items i LEFT JOIN groups g ON i.team=g.team WHERE g.label='심사' ORDER BY i.id;",
    ["SELECT i.id,g.label FROM items i LEFT JOIN groups g ON i.team=g.team AND g.label='심사' ORDER BY i.id;", 'SELECT i.id,g.label FROM items i LEFT JOIN groups g ON i.team=g.team ORDER BY i.id;', "SELECT i.id,g.label FROM items i LEFT JOIN groups g ON i.team=g.team WHERE g.label IS NULL ORDER BY i.id;"],
    'WHERE는 조인 결과에 적용된다. g.label이 NULL인 보충 행은 심사와의 비교가 UNKNOWN이라 제외되어 심사 팀의 매칭 행만 남는다.', '심화')
sql('join-multiplicity', '일대다 조인의 행 증가', '조인', '여러 작업을 가진 항목',
    'SELECT i.id,w.units FROM items i JOIN work w ON i.id=w.item_id ORDER BY i.id,w.id;',
    ['SELECT i.id,SUM(w.units) FROM items i JOIN work w ON i.id=w.item_id GROUP BY i.id ORDER BY i.id;', 'SELECT i.id,MAX(w.units) FROM items i JOIN work w ON i.id=w.item_id GROUP BY i.id ORDER BY i.id;', 'SELECT i.id,w.units FROM items i LEFT JOIN work w ON i.id=w.item_id ORDER BY i.id,w.id;'],
    '조인은 연결되는 작업마다 결과 행을 만든다. 항목 하나에 작업 둘이 있으면 id가 두 번 나타난다. GROUP BY로 묶기 전에는 합계로 축약되지 않는다.')
sql('cross-join', 'CROSS JOIN 행 수', '조인', '모든 팀과 항목 조합',
    'SELECT COUNT(*) FROM items CROSS JOIN groups;',
    ['SELECT COUNT(*) FROM items JOIN groups ON items.team=groups.team;', 'SELECT COUNT(*) FROM items;', 'SELECT COUNT(*) FROM groups;'],
    'CROSS JOIN은 모든 왼쪽 행과 모든 오른쪽 행을 조합한다. items의 행 수에 groups의 행 수 3을 곱해 결과 건수를 구한다. 키 값이 같은지 검사하지 않는다.', '기초')
sql('self-join', '자기 조인', '조인', '상위 항목 연결',
    'SELECT c.id,p.id FROM items c JOIN items p ON c.parent_id=p.id ORDER BY c.id;',
    ['SELECT c.id,p.id FROM items c LEFT JOIN items p ON c.parent_id=p.id ORDER BY c.id;', 'SELECT c.id,c.parent_id FROM items c WHERE c.parent_id IS NULL ORDER BY c.id;', 'SELECT c.id,p.id FROM items c JOIN items p ON c.id=p.parent_id ORDER BY c.id,p.id;'],
    '동일한 표를 c와 p라는 서로 다른 별칭으로 읽는다. c.parent_id와 p.id가 같은 행을 연결하므로 상위 id가 없는 행은 INNER JOIN에서 제외된다.')
sql('exists', 'EXISTS', '서브쿼리', '작업이 하나라도 존재하는 항목',
    'SELECT i.id FROM items i WHERE EXISTS(SELECT 1 FROM work w WHERE w.item_id=i.id) ORDER BY i.id;',
    ['SELECT i.id FROM items i WHERE NOT EXISTS(SELECT 1 FROM work w WHERE w.item_id=i.id) ORDER BY i.id;', 'SELECT i.id FROM items i JOIN work w ON w.item_id=i.id ORDER BY i.id,w.id;', 'SELECT id FROM items ORDER BY id;'],
    'EXISTS는 연결되는 행의 존재 여부만 검사한다. 작업이 여러 개여도 바깥 items 행은 한 번만 선택된다. SELECT 1의 1은 결과 값의 비교 대상이 아니다.')
sql('not-exists', 'NOT EXISTS', '서브쿼리', '연결 작업이 없는 항목',
    'SELECT i.id FROM items i WHERE NOT EXISTS(SELECT 1 FROM work w WHERE w.item_id=i.id) ORDER BY i.id;',
    ['SELECT i.id FROM items i WHERE EXISTS(SELECT 1 FROM work w WHERE w.item_id=i.id) ORDER BY i.id;', 'SELECT id FROM items WHERE id NOT IN(SELECT item_id FROM work) ORDER BY id;', 'SELECT id FROM items ORDER BY id;'],
    'NOT EXISTS는 해당 id와 같은 item_id가 없는 항목을 고른다. work의 NULL item_id는 어떤 id와도 같지 않아 모든 항목을 배제하는 원인이 되지 않는다.')
sql('in-subquery', 'IN 서브쿼리', '서브쿼리', '대량 작업이 연결된 항목',
    'SELECT id FROM items WHERE id IN(SELECT item_id FROM work WHERE units>=5) ORDER BY id;',
    ['SELECT id FROM items WHERE id IN(SELECT item_id FROM work) ORDER BY id;', 'SELECT id FROM items WHERE id NOT IN(SELECT item_id FROM work WHERE units>=5) ORDER BY id;', 'SELECT id FROM items WHERE value>=5 ORDER BY id;'],
    '안쪽 쿼리에서 units가 5 이상인 작업의 item_id를 만든 뒤 바깥 id의 포함 여부를 검사한다. 안쪽에 같은 id가 중복돼도 바깥 행이 중복 반환되지는 않는다.')
sql('not-in-null', 'NOT IN과 NULL 함정', '서브쿼리', 'NULL이 포함된 제외 목록',
    'SELECT id FROM items WHERE id NOT IN(SELECT item_id FROM work) ORDER BY id;',
    ['SELECT id FROM items WHERE id NOT IN(SELECT item_id FROM work WHERE item_id IS NOT NULL) ORDER BY id;', 'SELECT id FROM items WHERE id IN(SELECT item_id FROM work) ORDER BY id;', 'SELECT id FROM items ORDER BY id;'],
    '제외 목록에 NULL이 있다. 목록에서 같은 id를 찾으면 NOT IN은 거짓이고, 못 찾아도 NULL과의 비교 때문에 UNKNOWN이 된다. 따라서 참인 행이 없다.', '심화')
sql('correlated-average', '상관 서브쿼리 평균', '서브쿼리', '자기 팀 평균을 넘는 점수',
    'SELECT o.id FROM items o WHERE o.value>(SELECT AVG(i.value) FROM items i WHERE i.team=o.team) ORDER BY o.id;',
    ['SELECT id FROM items WHERE value>(SELECT AVG(value) FROM items) ORDER BY id;', 'SELECT o.id FROM items o WHERE o.value>=(SELECT AVG(i.value) FROM items i WHERE i.team=o.team) ORDER BY o.id;', 'SELECT id FROM items WHERE value>{t} ORDER BY id;'],
    '바깥 행의 team을 이용해 같은 팀의 평균을 매번 계산한다. 팀에 입력된 점수가 하나뿐이면 그 값은 평균과 같아 > 조건을 통과하지 않는다.', '심화')
sql('scalar-max', '스칼라 집계 서브쿼리', '서브쿼리', '전체 최고 점수의 동점자',
    'SELECT id FROM items WHERE value=(SELECT MAX(value) FROM items) ORDER BY id;',
    ['SELECT id FROM items ORDER BY value DESC,id LIMIT 1;', 'SELECT id FROM items WHERE value>(SELECT AVG(value) FROM items) ORDER BY id;', 'SELECT id FROM items WHERE value=(SELECT MIN(value) FROM items) ORDER BY id;'],
    'MAX(value)는 하나의 최댓값을 만든다. 바깥에서 그 값과 같은 모든 행을 선택하므로 최고 점수가 동점이면 모두 반환한다.')
sql('union', 'UNION 중복 제거', '집합 연산', '팀과 등록 팀의 합집합',
    'SELECT team FROM items UNION SELECT team FROM groups ORDER BY team;',
    ['SELECT team FROM items UNION ALL SELECT team FROM groups ORDER BY team;', 'SELECT team FROM items INTERSECT SELECT team FROM groups ORDER BY team;', 'SELECT team FROM items EXCEPT SELECT team FROM groups ORDER BY team;'],
    'UNION은 두 결과에 존재하는 값을 모으고 중복 행을 제거한다. items의 C와 groups의 D도 포함된다. UNION ALL은 중복을 남긴다.')
sql('union-all', 'UNION ALL 중복 유지', '집합 연산', '목록을 그대로 이어 붙이기',
    'SELECT team FROM items UNION ALL SELECT team FROM groups ORDER BY team;',
    ['SELECT team FROM items UNION SELECT team FROM groups ORDER BY team;', 'SELECT team FROM items ORDER BY team;', 'SELECT team FROM groups ORDER BY team;'],
    'UNION ALL은 두 결과의 행을 모두 유지한다. 팀 이름이 여러 번 나와도 삭제하지 않으며 마지막 ORDER BY가 결합된 전체 결과를 정렬한다.')
sql('intersect', 'INTERSECT 공통 행', '집합 연산', '양쪽 모두 존재하는 팀',
    'SELECT team FROM items INTERSECT SELECT team FROM groups ORDER BY team;',
    ['SELECT team FROM items UNION SELECT team FROM groups ORDER BY team;', 'SELECT team FROM items EXCEPT SELECT team FROM groups ORDER BY team;', 'SELECT team FROM groups EXCEPT SELECT team FROM items ORDER BY team;'],
    'INTERSECT는 두 결과에 공통으로 있는 행만 중복 없이 반환한다. C는 items에만 있고 D는 groups에만 있어 제외된다.')
sql('except', 'EXCEPT 방향', '집합 연산', '항목에만 나타나는 팀',
    'SELECT team FROM items EXCEPT SELECT team FROM groups ORDER BY team;',
    ['SELECT team FROM groups EXCEPT SELECT team FROM items ORDER BY team;', 'SELECT team FROM items INTERSECT SELECT team FROM groups ORDER BY team;', 'SELECT team FROM items UNION SELECT team FROM groups ORDER BY team;'],
    'EXCEPT는 왼쪽 결과에서 오른쪽에도 있는 행을 뺀다. 순서를 바꾸면 등록 팀에만 있는 D를 구하게 되어 결과가 달라진다.')
sql('cte-filter', 'CTE로 중간 결과 이름 짓기', 'CTE와 재귀', '활성 데이터에서 재조회',
    'WITH chosen AS(SELECT id,value FROM items WHERE active=1) SELECT id FROM chosen WHERE value>{t} ORDER BY id;',
    ['SELECT id FROM items WHERE value>{t} ORDER BY id;', 'SELECT id FROM items WHERE active=1 ORDER BY id;', 'SELECT id FROM items WHERE active=0 AND value>{t} ORDER BY id;'],
    'CTE chosen에는 먼저 활성 행만 들어간다. 바깥 쿼리는 그 중 점수가 기준을 넘는 행을 고른다. CTE 이름은 영구 표를 만드는 명령이 아니다.')
sql('cte-aggregate', '집계 CTE 후 필터', 'CTE와 재귀', '팀 평균 보고서',
    'WITH stats AS(SELECT team,AVG(value) AS mean FROM items GROUP BY team) SELECT team,ROUND(mean,2) FROM stats WHERE mean>{t} ORDER BY team;',
    ['SELECT team,ROUND(AVG(value),2) FROM items WHERE value>{t} GROUP BY team ORDER BY team;', 'SELECT team,ROUND(AVG(value),2) FROM items GROUP BY team ORDER BY team;', 'SELECT team,SUM(value) FROM items GROUP BY team HAVING SUM(value)>{t} ORDER BY team;'],
    'CTE에서 전체 입력 점수의 팀별 평균을 먼저 만든다. 이후 mean을 기준으로 팀을 고른다. 평균 계산 전에 낮은 점수를 지우면 다른 평균이 된다.', '심화')
sql('recursive-cte', '재귀 CTE 종료 조건', 'CTE와 재귀', '연속 번호 만들기',
    'WITH RECURSIVE seq(n) AS(SELECT 1 UNION ALL SELECT n+1 FROM seq WHERE n<{n}) SELECT n FROM seq ORDER BY n;',
    ['WITH RECURSIVE seq(n) AS(SELECT 1 UNION ALL SELECT n+1 FROM seq WHERE n<={n}) SELECT n FROM seq ORDER BY n;', 'WITH RECURSIVE seq(n) AS(SELECT 0 UNION ALL SELECT n+1 FROM seq WHERE n<{n}) SELECT n FROM seq ORDER BY n;', 'WITH RECURSIVE seq(n) AS(SELECT 1 UNION ALL SELECT n+2 FROM seq WHERE n<{n}) SELECT n FROM seq ORDER BY n;'],
    '초기 항은 1이다. 현재 n이 상한보다 작을 때 n+1을 추가하므로 상한까지 만들고 종료한다. 종료 조건에서 <=를 쓰면 상한+1이 한 번 더 생긴다.', '심화')
sql('row-number', 'ROW_NUMBER 고유 순번', '윈도 함수', '동점에도 다른 순번',
    'SELECT id,ROW_NUMBER() OVER(ORDER BY value DESC,id) FROM items WHERE value IS NOT NULL ORDER BY id;',
    ['SELECT id,RANK() OVER(ORDER BY value DESC) FROM items WHERE value IS NOT NULL ORDER BY id;', 'SELECT id,DENSE_RANK() OVER(ORDER BY value DESC) FROM items WHERE value IS NOT NULL ORDER BY id;', 'SELECT id,ROW_NUMBER() OVER(ORDER BY value ASC,id) FROM items WHERE value IS NOT NULL ORDER BY id;'],
    'ROW_NUMBER는 정렬 순서대로 서로 다른 순번을 붙인다. 점수 동점에서는 id 오름차순으로 순서를 확정한다. 최종 ORDER BY id는 출력 순서만 정한다.', '심화')
sql('rank', 'RANK 동점 뒤 순위 건너뛰기', '윈도 함수', '동점 순위와 다음 순위',
    'SELECT id,RANK() OVER(ORDER BY value DESC) FROM items WHERE value IS NOT NULL ORDER BY id;',
    ['SELECT id,DENSE_RANK() OVER(ORDER BY value DESC) FROM items WHERE value IS NOT NULL ORDER BY id;', 'SELECT id,ROW_NUMBER() OVER(ORDER BY value DESC,id) FROM items WHERE value IS NOT NULL ORDER BY id;', 'SELECT id,RANK() OVER(ORDER BY value ASC) FROM items WHERE value IS NOT NULL ORDER BY id;'],
    'RANK는 동점에 같은 순위를 주고 그 다음 순위를 동점 행 수만큼 건너뛴다. 순위 계산의 ORDER BY에는 id가 없어 동일 점수가 동점이다.', '심화')
sql('dense-rank', 'DENSE_RANK 연속 순위', '윈도 함수', '순위를 비우지 않는 동점 처리',
    'SELECT id,DENSE_RANK() OVER(ORDER BY value DESC) FROM items WHERE value IS NOT NULL ORDER BY id;',
    ['SELECT id,RANK() OVER(ORDER BY value DESC) FROM items WHERE value IS NOT NULL ORDER BY id;', 'SELECT id,ROW_NUMBER() OVER(ORDER BY value DESC,id) FROM items WHERE value IS NOT NULL ORDER BY id;', 'SELECT id,DENSE_RANK() OVER(ORDER BY value ASC) FROM items WHERE value IS NOT NULL ORDER BY id;'],
    'DENSE_RANK는 같은 점수에 같은 순위를 주며, 다음 서로 다른 점수의 순위는 바로 1 증가한다. RANK와 달리 동점 행 수 때문에 빈 순위가 생기지 않는다.', '심화')
sql('lag', 'LAG 이전 행', '윈도 함수', '바로 전 항목 점수',
    'SELECT id,LAG(value) OVER(ORDER BY id) FROM items ORDER BY id;',
    ['SELECT id,LEAD(value) OVER(ORDER BY id) FROM items ORDER BY id;', 'SELECT id,LAG(value,1,0) OVER(ORDER BY id) FROM items ORDER BY id;', 'SELECT id,value FROM items ORDER BY id;'],
    'LAG(value)는 윈도 정렬에서 이전 행의 value를 가져온다. 첫 행은 이전 행이 없어 기본값 NULL을 반환한다. 현재 값이나 다음 행 값과 혼동하지 않아야 한다.', '심화')
sql('lead', 'LEAD 다음 행', '윈도 함수', '다음 항목 점수',
    'SELECT id,LEAD(value,1,-1) OVER(ORDER BY id) FROM items ORDER BY id;',
    ['SELECT id,LAG(value,1,-1) OVER(ORDER BY id) FROM items ORDER BY id;', 'SELECT id,LEAD(value) OVER(ORDER BY id) FROM items ORDER BY id;', 'SELECT id,COALESCE(LEAD(value) OVER(ORDER BY id),-1) FROM items ORDER BY id;'],
    'LEAD의 세 번째 인수 -1은 다음 행이 없는 경우에만 적용된다. 다음 행이 실제로 존재하고 그 value가 NULL이면 NULL을 그대로 가져온다.', '심화')
sql('running-sum', 'ROWS 누적 합', '윈도 함수', '번호순 누적 점수',
    'SELECT id,SUM(value) OVER(ORDER BY id ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) FROM items ORDER BY id;',
    ['SELECT id,SUM(value) OVER() FROM items ORDER BY id;', 'SELECT id,SUM(value) OVER(ORDER BY id ROWS BETWEEN 1 PRECEDING AND CURRENT ROW) FROM items ORDER BY id;', 'SELECT id,value FROM items ORDER BY id;'],
    '프레임은 첫 행부터 현재 행까지다. id순으로 점수를 계속 더하며 현재 value가 NULL이면 그 행에서 합이 추가로 늘어나지 않는다. 전체 합 반복이나 직전 두 행 합과 다르다.', '심화')
sql('partition', 'PARTITION BY 그룹별 윈도', '윈도 함수', '각 팀 합계를 행마다 표시',
    'SELECT id,SUM(value) OVER(PARTITION BY team) FROM items ORDER BY id;',
    ['SELECT id,SUM(value) OVER() FROM items ORDER BY id;', 'SELECT id,MAX(value) OVER(PARTITION BY team) FROM items ORDER BY id;', 'SELECT id,COUNT(*) OVER(PARTITION BY team) FROM items ORDER BY id;'],
    'PARTITION BY team은 팀별로 합계 범위를 나눈다. GROUP BY와 달리 원래 행을 합쳐 없애지 않고 각 행에 자기 팀 합계를 표시한다.', '심화')
sql('window-filter', '윈도 결과를 CTE에서 필터', '윈도 함수', '각 팀 최고 점수 한 건',
    'WITH ranked AS(SELECT id,team,value,ROW_NUMBER() OVER(PARTITION BY team ORDER BY value DESC,id) AS rn FROM items) SELECT id FROM ranked WHERE rn=1 ORDER BY id;',
    ['SELECT id FROM items ORDER BY value DESC,id LIMIT 1;', 'WITH ranked AS(SELECT id,team,value,ROW_NUMBER() OVER(PARTITION BY team ORDER BY value ASC,id) AS rn FROM items) SELECT id FROM ranked WHERE rn=1 ORDER BY id;', 'WITH ranked AS(SELECT id,team,value,RANK() OVER(PARTITION BY team ORDER BY value DESC) AS rn FROM items) SELECT id FROM ranked WHERE rn=1 ORDER BY id;'],
    'CTE에서 각 팀 안의 점수 내림차순과 id 오름차순으로 순번을 붙인다. rn=1을 바깥에서 선택하면 팀별로 정확히 한 행을 얻고 동점은 id가 작은 행이 이긴다.', '심화')
sql('limit-offset', 'LIMIT와 OFFSET', '정렬과 페이징', '정렬 결과의 두 번째 페이지',
    'SELECT id FROM items ORDER BY value DESC,id LIMIT 2 OFFSET 2;',
    ['SELECT id FROM items ORDER BY value DESC,id LIMIT 2;', 'SELECT id FROM items ORDER BY value DESC,id LIMIT 2 OFFSET 1;', 'SELECT id FROM items ORDER BY id LIMIT 2 OFFSET 2;'],
    '전체를 점수 내림차순, 동점 id 오름차순으로 정렬한 후 앞의 2행을 건너뛰고 2행을 반환한다. OFFSET은 행 번호가 아니라 생략할 행 수다.')
sql('concat', '문자열 연결 연산자', '문자열 함수', '표시용 식별자 만들기',
    "SELECT id,team || ':' || title FROM items WHERE id<=3 ORDER BY id;",
    ["SELECT id,title || ':' || team FROM items WHERE id<=3 ORDER BY id;", "SELECT id,team || title FROM items WHERE id<=3 ORDER BY id;", "SELECT id,team || ':' || COALESCE(extra,'없음') FROM items WHERE id<=3 ORDER BY id;"],
    'SQLite에서 ||는 문자열을 순서대로 이어 붙인다. team, 콜론, title의 순서를 지켜 표시 문자열을 만든다. 값을 더하는 산술 연산이 아니다.', '기초')
sql('substring', 'SUBSTR와 LENGTH', '문자열 함수', '문자 단위 제목 잘라내기',
    'SELECT id,SUBSTR(title,3),LENGTH(title) FROM items WHERE id<=3 ORDER BY id;',
    ['SELECT id,SUBSTR(title,2),LENGTH(title) FROM items WHERE id<=3 ORDER BY id;', 'SELECT id,SUBSTR(title,3),LENGTH(title)-2 FROM items WHERE id<=3 ORDER BY id;', 'SELECT id,SUBSTR(title,1,2),LENGTH(title) FROM items WHERE id<=3 ORDER BY id;'],
    'SUBSTR의 시작 위치는 1부터 센다. 세 번째 문자부터 마지막까지 반환하며 LENGTH(title)은 잘라낸 문자열이 아니라 원래 전체 제목의 문자 수다.')
sql('null-arithmetic', '산술식의 NULL 전파', '조건과 NULL', '빈 값이 포함된 덧셈',
    'SELECT id,value+extra FROM items WHERE id<=4 ORDER BY id;',
    ['SELECT id,value+COALESCE(extra,0) FROM items WHERE id<=4 ORDER BY id;', 'SELECT id,COALESCE(value,0)+COALESCE(extra,0) FROM items WHERE id<=4 ORDER BY id;', 'SELECT id,value FROM items WHERE id<=4 ORDER BY id;'],
    '일반적인 덧셈에서 한 피연산자가 NULL이면 결과도 NULL이다. extra가 NULL이라고 자동으로 0으로 취급하지 않는다. 기본값을 원하면 COALESCE를 명시해야 한다.')
sql('real-division', '실수 나눗셈과 ROUND', 'SQL 기초', '점수의 비율 계산',
    'SELECT id,ROUND(value/3.0,2) FROM items WHERE id<=3 ORDER BY id;',
    ['SELECT id,value/3 FROM items WHERE id<=3 ORDER BY id;', 'SELECT id,ROUND(value/3.0,0) FROM items WHERE id<=3 ORDER BY id;', 'SELECT id,value*3 FROM items WHERE id<=3 ORDER BY id;'],
    '분모 3.0으로 실수 나눗셈을 하고 소수 둘째 자리로 반올림한다. SQLite에서 두 정수의 나눗셈은 소수 부분이 잘려 /3과 /3.0은 다를 수 있다.')
sql('update', 'UPDATE 조건과 식', '데이터 변경', '활성 점수 일괄 조정',
    'SELECT id,value FROM items ORDER BY id;',
    ['SELECT id,value-10 FROM items ORDER BY id;', 'SELECT id,value+10 FROM items ORDER BY id;', 'SELECT id,value FROM items WHERE active=1 ORDER BY id;'],
    'UPDATE는 active=1인 행의 value에 10을 더한다. 비활성 행은 그대로이고, NULL에 10을 더해도 NULL이다. 변경 후 SELECT는 모든 항목을 읽는다.',
    mutation='UPDATE items SET value=value+10 WHERE active=1;')
sql('delete', 'DELETE 조건', '데이터 변경', '비활성 항목 삭제',
    'SELECT id FROM items ORDER BY id;',
    ['SELECT id FROM items WHERE active=0 ORDER BY id;', 'SELECT id FROM items WHERE value>{t} ORDER BY id;', 'SELECT id FROM items WHERE id<=3 ORDER BY id;'],
    'DELETE의 WHERE가 참인 비활성 행만 삭제한다. 이후 전체 표를 조회하므로 남아 있는 활성 행의 id를 순서대로 읽는다.',
    mutation='DELETE FROM items WHERE active=0;')
sql('insert-select', 'INSERT SELECT', '데이터 변경', '활성 항목을 별도 표에 복사',
    'SELECT id,value FROM selected ORDER BY id;',
    ['SELECT id,value FROM items ORDER BY id;', 'SELECT id,value FROM items WHERE active=0 ORDER BY id;', 'SELECT id,value FROM items WHERE active=1 AND value>{t} ORDER BY id;'],
    'INSERT SELECT는 SELECT가 반환한 행들을 대상 표에 추가한다. active=1 조건을 충족하면 value가 NULL이어도 복사되고 원본 items는 바뀌지 않는다.',
    mutation='CREATE TABLE selected(id INTEGER,value INTEGER);\nINSERT INTO selected SELECT id,value FROM items WHERE active=1;')
sql('rollback', 'ROLLBACK 변경 취소', '트랜잭션', '취소한 점수 변경',
    'SELECT id,value FROM items WHERE id<=2 ORDER BY id;',
    ['SELECT id,value+100 FROM items WHERE id<=2 ORDER BY id;', 'SELECT id,0 FROM items WHERE id<=2 ORDER BY id;', 'SELECT id,value FROM items WHERE id<=3 ORDER BY id;'],
    'BEGIN 이후 UPDATE한 내용은 COMMIT 전에 ROLLBACK으로 취소된다. 따라서 SELECT는 초기 점수를 반환한다. 다른 트랜잭션의 변경은 없다는 가정이다.',
    mutation='BEGIN;\nUPDATE items SET value=value+100 WHERE id<=2;\nROLLBACK;')
sql('savepoint', 'SAVEPOINT 일부 취소', '트랜잭션', '중간 저장점으로 돌아가기',
    'SELECT id,value FROM items WHERE id<=2 ORDER BY id;',
    ['SELECT id,value-10 FROM items WHERE id<=2 ORDER BY id;', 'SELECT id,value+20 FROM items WHERE id<=2 ORDER BY id;', 'SELECT id,value+10 FROM items WHERE id<=2 ORDER BY id;'],
    '저장점 s 전에 한 +10은 유지되고 저장점 이후의 +20만 ROLLBACK TO s로 취소된다. COMMIT하면 첫 번째 변경만 확정된다.', '심화',
    mutation='BEGIN;\nUPDATE items SET value=value+10 WHERE id<=2;\nSAVEPOINT s;\nUPDATE items SET value=value+20 WHERE id<=2;\nROLLBACK TO s;\nRELEASE s;\nCOMMIT;')


def fallback_options(rows):
    """Plausible row omission/order/NULL mistakes, only used if SQL choices coincide."""
    candidates = []
    if rows:
        candidates += [rows[:-1], rows[1:], list(reversed(rows)), rows + [rows[-1]]]
        first = list(rows[0])
        for j, x in enumerate(first):
            altered = first.copy()
            altered[j] = 0 if x is None else None
            candidates.append([tuple(altered)] + rows[1:])
            if isinstance(x, (int,float)):
                altered = first.copy(); altered[j] = x+1
                candidates.append([tuple(altered)] + rows[1:])
    else:
        candidates = [[(None,)], [(0,)], [(1,)]]
    return candidates


def generate_sql():
    assert len(SQL) == 65, len(SQL)
    for spec in SQL:
        for seed in range(4):
            name, rows, work, t = SCENARIOS[seed]
            fmt = dict(t=t, n=seed+3)
            query = spec['query'].format(**fmt)
            mutation = (spec['mutation'] or '').format(**fmt)
            con = database(seed)
            if mutation:
                con.executescript(mutation)
            actual = con.execute(query).fetchall()
            correct = result(actual)
            choices = [correct]
            distractors = []
            for wrong in spec['wrong']:
                sql_wrong = wrong.format(**fmt)
                rr = con.execute(sql_wrong).fetchall()
                text = result(rr)
                if text not in choices:
                    choices.append(text)
                    distractors.append(sql_wrong)
                if len(choices)==4:
                    break
            for rr in fallback_options(actual):
                if len(choices)==4:
                    break
                text = result(rr)
                if text not in choices:
                    choices.append(text)
                    distractors.append('행 순서·NULL·누락·중복을 바꾼 오답')
            con.close()
            assert len(choices)==4, (spec['key'],seed,choices)
            code = (mutation+'\n' if mutation else '') + query
            fixture_query = query + '\n' + mutation
            qid = add({
                'category': spec['category'], 'learningTopic': spec['topic'],
                'templateId': 'db-sql-'+spec['key'], 'title': spec['title']+' · '+name,
                'prompt': '자체 제작 연습문제 · SQLite 기준. 아래 SQL을 실행한 결과는? 보기의 /는 행 구분이며 괄호 안은 열 순서다. 다른 변경은 없다.',
                'passage': fixture_text(seed, fixture_query), 'code':code,
                'difficulty':spec['difficulty'],
            }, correct, choices,
                spec['reasoning'] + '\n실행 결과: ' + correct + '.',
                ['지문에 제시된 초기 표에서 SQL의 조건과 연산 순서를 적용한다.',
                 spec['reasoning'], '열과 행의 순서를 맞추면 ' + correct + '이다.'],
                'computed-verified')
            AUDIT.append({'id':qid, 'templateId':'db-sql-'+spec['key'], 'seed':seed,
                          'query':query, 'mutation':mutation, 'result':[list(row) for row in actual],
                          'correctOption':correct, 'distractorQueries':distractors})


# Four named scenarios per concept. Within a concept these are alternate applications,
# not question-id padding or copies of publisher questions.
CONCEPTS = []


def concept(key, topic, category, prompt, scenarios, options, correct, explain, difficulty='보통'):
    assert len(scenarios)==4
    CONCEPTS.append(dict(key=key,topic=topic,category=category,prompt=prompt,
                         scenarios=scenarios,options=options,correct=correct,
                         explain=explain,difficulty=difficulty))


concept('candidate-key','후보키와 최소성','키와 제약','주어진 유일성 규칙에서 후보키의 조건을 만족하는 설명은?',
    [('교육생','교육생번호','이메일','교육생번호와 이메일 각각이 유일하며 NULL이 없다.'),
     ('장비','장비번호','시리얼번호','장비번호와 시리얼번호 각각이 유일하며 NULL이 없다.'),
     ('업체','업체번호','등록번호','업체번호와 등록번호 각각이 유일하며 NULL이 없다.'),
     ('계정','계정번호','로그인아이디','계정번호와 로그인아이디 각각이 유일하며 NULL이 없다.')],
    ['{a}와 {b} 각각은 후보키이며 두 열을 합친 집합은 최소성이 없다.', '{a}와 {b}를 반드시 합쳐야만 후보키가 된다.', '{a}만 후보키이고 {b}는 유일해도 후보키가 될 수 없다.', '후보키에는 항상 NULL을 허용해야 한다.'],0,
    '후보키는 모든 행을 유일하게 식별하면서 열을 하나라도 빼면 그 성질을 잃는 최소 슈퍼키다. {a}와 {b} 각각이 유일하므로 각각 후보키이며 두 열을 합친 집합은 불필요한 열을 가진다.')
concept('composite-key','복합키의 범위','키와 제약','업무 규칙에 맞는 기본키는?',
    [('접수','지점코드','접수번호','접수번호는 지점 내부에서만 유일하며 다른 지점에서 재사용된다.'),
     ('좌석','열차번호','좌석번호','좌석번호는 열차 안에서만 유일하며 다른 열차에서 재사용된다.'),
     ('품목','창고번호','선반번호','선반번호는 창고 안에서만 유일하며 다른 창고에서 재사용된다.'),
     ('교육반','과정코드','분반번호','분반번호는 과정 안에서만 유일하며 다른 과정에서 재사용된다.')],
    ['({a}, {b})를 함께 기본키로 사용한다.', '{b}만 기본키로 사용한다.', '{a}만 기본키로 사용한다.', '열의 저장 순서를 바꾸면 키가 필요 없다.'],0,
    '{b}는 전체 표에서 유일하지 않고 {a}도 여러 행에서 반복된다. 두 값을 함께 보면 업무 대상 하나를 식별하므로 복합 기본키가 필요하다. 키 열에는 NULL을 두지 않는다.','기초')
concept('foreign-key','외래키 참조 무결성','키와 제약','부모와 자식의 연결을 DB가 검사하도록 하는 제약은?',
    [('주문','고객','고객번호','주문의 고객번호는 실제 고객 표에 존재해야 한다.'),
     ('배정','직원','직원번호','배정의 직원번호는 실제 직원 표에 존재해야 한다.'),
     ('장애기록','장비','장비번호','장애기록의 장비번호는 실제 장비 표에 존재해야 한다.'),
     ('수강','과정','과정번호','수강의 과정번호는 실제 과정 표에 존재해야 한다.')],
    ['{entity}.{b}가 {a} 표의 유일한 키를 참조하는 FOREIGN KEY를 둔다.', '{entity}의 모든 열에 같은 인덱스 이름을 붙인다.', '자식 행을 항상 부모 행보다 먼저 삭제한다는 주석만 쓴다.', '외래키 열을 문자열로 바꾸면 참조 무결성이 자동 보장된다.'],0,
    '외래키는 자식의 참조 값이 부모의 참조 가능한 유일 키에 존재하는지 검사한다. 필수 관계라면 NOT NULL도 별도로 필요하다. 인덱스 이름이나 주석은 데이터의 유효성을 강제하지 못한다.','기초')
concept('check-domain','CHECK 업무 범위','키와 제약','음수가 허용되지 않는 필수 값을 강제하는 제약 조합은?',
    [('재고','수량','0','수량은 반드시 입력하고 0 이상이어야 한다.'),
     ('계정','잔액','0','이 시나리오에서 잔액은 반드시 입력하고 0 이상이어야 한다.'),
     ('예약','인원','0','인원은 반드시 입력하고 0 이상이어야 한다.'),
     ('작업','소요시간','0','소요시간은 반드시 입력하고 0 이상이어야 한다.')],
    ['{a} NOT NULL과 CHECK({a} >= {b})를 함께 사용한다.', 'CHECK({a} >= {b})만으로 NULL도 반드시 금지된다.', '인덱스를 만들면 음수가 자동 거절된다.', '열 별칭을 positive로 정하면 값이 강제된다.'],0,
    'CHECK는 조건이 거짓인 값을 거부하지만 NULL 때문에 UNKNOWN인 경우는 일반적으로 통과할 수 있다. 따라서 필수 입력은 NOT NULL, 값의 범위는 CHECK로 각각 강제해야 한다.')
concept('delete-cascade','ON DELETE CASCADE','키와 제약','자식이 부모 없이 존재할 수 없는 관계를 자동 정리하는 정책은?',
    [('주문상세','주문','상세행','주문을 물리 삭제하면 그 주문의 상세행도 삭제해야 한다.'),
     ('설문응답','설문','응답행','설문을 물리 삭제하면 해당 설문의 응답행도 삭제해야 한다.'),
     ('임시작업','임시배치','작업행','임시배치를 물리 삭제하면 연결된 작업행도 삭제해야 한다.'),
     ('연습기록','연습세션','기록행','연습세션을 물리 삭제하면 연결된 기록행도 삭제해야 한다.')],
    ['자식 외래키에 ON DELETE CASCADE를 지정한다.', '자식 외래키에 ON DELETE SET NULL을 지정하면 자식도 삭제된다.', '부모를 삭제해도 자식 외래키 검사는 항상 생략된다.', '부모 표에만 UNIQUE를 추가하면 자식 삭제가 자동 실행된다.'],0,
    'CASCADE는 참조되는 부모 행 삭제를 연결된 자식 행 삭제로 전파한다. SET NULL은 자식 행을 남기고 참조 값을 NULL로 바꾸는 정책이므로 요구사항과 다르다.')
concept('first-normal','제1정규형의 원자값','정규화','값 목록을 한 칸에 저장한 설계를 개선하는 방향은?',
    [('고객','고객번호','전화번호','전화번호 열에 여러 번호를 쉼표로 연결해 저장한다.'),
     ('직원','직원번호','자격증','자격증 열에 여러 자격증명을 쉼표로 연결해 저장한다.'),
     ('강좌','강좌번호','교재','교재 열에 여러 교재번호를 쉼표로 연결해 저장한다.'),
     ('프로젝트','프로젝트번호','참여자','참여자 열에 여러 직원번호를 쉼표로 연결해 저장한다.')],
    ['별도 연결 표에 ({a}, {b})를 한 값씩 행으로 저장한다.', '쉼표 대신 세미콜론으로만 바꾼다.', '한 칸에 더 긴 문자열을 허용하면 원자성이 확보된다.', '열 이름을 plural로 바꾸면 정규화가 끝난다.'],0,
    '반복 값 목록은 각각의 항목을 조건으로 검색하거나 제약을 적용하기 어렵다. 한 행에 하나의 연결 값을 저장하면 관계형 연산과 무결성 검사를 적용하기 쉽다. 구분자만 바꾸는 것은 구조 개선이 아니다.','기초')
concept('second-normal','제2정규형과 부분 종속','정규화','복합키 일부에만 종속되는 속성을 분리하는 방법은?',
    [('수강','학생번호','학생이름','기본키=(학생번호,과목번호), 학생번호→학생이름, 전체 키→성적.'),
     ('주문상세','상품번호','상품명','기본키=(주문번호,상품번호), 상품번호→상품명, 전체 키→수량.'),
     ('창고재고','창고번호','창고주소','기본키=(창고번호,상품번호), 창고번호→창고주소, 전체 키→재고.'),
     ('직원배정','직원번호','직원이름','기본키=(직원번호,프로젝트번호), 직원번호→직원이름, 전체 키→배정시간.')],
    ['{a}가 키인 별도 표에 {b}를 두고 원래 표에서는 참조한다.', '{b}를 모든 행에서 계속 복사한다.', '복합키에서 다른 키 열을 지워 중복 행을 그대로 둔다.', '열 순서를 바꾸면 함수 종속이 사라진다.'],0,
    '{b}는 전체 복합키가 아니라 {a}에만 종속되어 부분 종속을 가진다. {a}가 키인 표로 분리하면 같은 이름이나 주소를 반복 저장하는 중복과 갱신 이상을 줄인다.')
concept('third-normal','제3정규형과 이행 종속','정규화','비키 속성 사이 종속을 분리하는 설계는?',
    [('직원','부서번호','부서명','직원번호→부서번호, 부서번호→부서명. 직원번호만 후보키이다.'),
     ('상품','제조사번호','제조사명','상품번호→제조사번호, 제조사번호→제조사명. 상품번호만 후보키이다.'),
     ('지점직원','지점번호','지점주소','직원번호→지점번호, 지점번호→지점주소. 직원번호만 후보키이다.'),
     ('장비','모델번호','모델명','장비번호→모델번호, 모델번호→모델명. 장비번호만 후보키이다.')],
    ['({a}, {b}) 표를 분리하고 원래 표에 {a}를 둔다.', '{b}를 모든 행마다 여러 번 복사한다.', '기본키를 {b}로 바꿔 기존 행을 전부 유지한다.', '모든 값을 문자열 하나로 합친다.'],0,
    '원래 키→{a}→{b}라는 이행 종속이 있다. {a}가 결정자인 별도 표에서 {b}를 관리하고 원래 표는 {a}를 참조하면 결정 사실을 한 번만 저장한다.')
concept('bcnf','BCNF 결정자','정규화','후보키가 아닌 결정자가 있는 관계의 BCNF 판단은?',
    [('수강','교수','과목','R(학생,과목,교수). (학생,과목)→교수, 교수→과목. 후보키는 (학생,과목),(학생,교수). 교수 하나는 여러 학생을 맡는다.'),
     ('배정','담당자','업무','R(고객,업무,담당자). (고객,업무)→담당자, 담당자→업무. 후보키는 (고객,업무),(고객,담당자). 담당자는 여러 고객을 맡는다.'),
     ('교육','강사','강좌','R(수강생,강좌,강사). (수강생,강좌)→강사, 강사→강좌. 후보키는 (수강생,강좌),(수강생,강사). 강사는 여러 수강생을 맡는다.'),
     ('배송','차량','노선','R(화물,노선,차량). (화물,노선)→차량, 차량→노선. 후보키는 (화물,노선),(화물,차량). 차량은 여러 화물을 운송한다.')],
    ['{a}→{b}에서 {a}가 슈퍼키가 아니므로 BCNF를 위반한다.', '후보키가 두 개이면 모든 함수 종속이 자동으로 BCNF를 만족한다.', '열이 세 개이므로 함수 종속을 검사할 필요가 없다.', '모든 속성이 어떤 후보키에 포함되면 BCNF가 자동 보장된다.'],0,
    'BCNF는 모든 비자명 함수 종속 X→Y의 결정자 X가 슈퍼키일 것을 요구한다. {a}만으로 행 전체를 식별하지 못하므로 {a}→{b}가 BCNF 위반이다. 기본키를 어떤 후보키로 선택하는지는 이 판단을 바꾸지 않는다.','심화')
concept('lossless','무손실 분해','정규화','두 관계를 조인해 원래 관계를 정확히 복원할 수 있는 조건은?',
    [('직원분해','직원번호','부서번호','R(직원번호,부서번호,부서명), 부서번호→부서명. R1(직원번호,부서번호),R2(부서번호,부서명)로 분해한다.'),
     ('상품분해','상품번호','제조사번호','R(상품번호,제조사번호,제조사명), 제조사번호→제조사명. R1(상품번호,제조사번호),R2(제조사번호,제조사명)로 분해한다.'),
     ('장비분해','장비번호','모델번호','R(장비번호,모델번호,모델명), 모델번호→모델명. R1(장비번호,모델번호),R2(모델번호,모델명)로 분해한다.'),
     ('책분해','도서번호','출판사번호','R(도서번호,출판사번호,출판사명), 출판사번호→출판사명. R1(도서번호,출판사번호),R2(출판사번호,출판사명)로 분해한다.')],
    ['공통 속성 {b}가 R2의 키이므로 무손실 분해 조건을 만족한다.', '공통 열이 한 개이면 데이터와 종속에 관계없이 항상 손실 분해다.', '두 표의 열 수가 다르므로 무손실 조인이 불가능하다.', '기본키 이름을 같은 문자열로 정하면 모든 분해가 무손실이다.'],0,
    '이진 분해에서 공통 속성이 한쪽 관계의 모든 속성을 결정하면 무손실 조건을 만족한다. {b}가 R2의 나머지 속성을 결정하므로 조인 시 한 원래 연결에 여러 불필요한 조합이 붙지 않는다.','심화')
concept('closure','속성 폐포','키와 함수 종속','주어진 종속만으로 {a}의 폐포를 구하면?',
    [('접수','A','D','R(A,B,C,D), 함수 종속 A→B, B→C, C→D.'),
     ('교육','P','S','R(P,Q,R,S), 함수 종속 P→Q, Q→R, R→S.'),
     ('업무','K','N','R(K,L,M,N), 함수 종속 K→L, L→M, M→N.'),
     ('보증','W','Z','R(W,X,Y,Z), 함수 종속 W→X, X→Y, Y→Z.')],
    ['첫 속성에서 연쇄적으로 모든 속성을 얻으므로 {a}는 후보키다.', '{a} 자체만 얻으며 어떤 다른 속성도 얻을 수 없다.', '마지막 속성 {b} 하나만 얻으며 {a}는 폐포에서 사라진다.', '열 저장 순서가 없으므로 폐포를 계산할 수 없다.'],0,
    '폐포는 시작 집합 {a}를 포함한 상태에서 적용 가능한 함수 종속을 반복한다. 첫 종속의 오른쪽을 얻으면 다음 종속도 적용할 수 있어 마지막 {b}까지 모두 얻는다. 단일 열 {a}가 전 속성을 결정하며 최소성이 있어 후보키다.','심화')
concept('update-anomaly','갱신 이상','정규화','한 사실을 여러 행에 중복 저장할 때 발생하는 문제는?',
    [('직원부서','부서명','직원','같은 부서의 직원 행마다 부서명을 복사하고 이름 변경 때 일부 행만 수정했다.'),
     ('주문상품','상품명','주문','동일 상품명이 여러 주문상세 행에 복사되고 변경 때 일부 행만 수정했다.'),
     ('장비모델','모델명','장비','동일 모델명이 여러 장비 행에 복사되고 변경 때 일부 행만 수정했다.'),
     ('수강교재','교재명','수강','동일 교재명이 여러 수강 행에 복사되고 변경 때 일부 행만 수정했다.')],
    ['같은 {a} 사실이 행마다 달라지는 갱신 이상이다.', '원하는 행을 못 삽입하는 삽입 이상만 해당한다.', 'SQL 문장 길이 때문에 발생한 구문 오류다.', '정규화된 표에는 같은 사실을 더 많이 복사해야 예방된다.'],0,
    '한 사실을 여러 위치에 복사하면 일부만 수정해 같은 {a}에 대해 서로 다른 값이 남는다. 관련 식별자에 종속되는 사실을 별도 표에서 한 번 관리하면 이 갱신 이상을 줄일 수 있다.','기초')
concept('many-many','다대다 관계 연결 표','ER 모델링','요구사항을 표현하는 관계형 설계는?',
    [('수강','학생','과목','학생은 여러 과목을 듣고 과목에는 여러 학생이 있다. 수강마다 성적을 저장한다.'),
     ('배정','직원','프로젝트','직원은 여러 프로젝트에 참여하고 프로젝트에는 여러 직원이 있다. 배정마다 시간을 저장한다.'),
     ('주문상세','주문','상품','주문에 여러 상품이 있고 상품은 여러 주문에 포함된다. 주문상세마다 수량을 저장한다.'),
     ('대여','회원','장비','회원은 여러 장비를 빌리고 장비도 시점에 따라 여러 회원에게 대여된다. 대여마다 시작시각을 저장한다.')],
    ['두 대상의 키를 참조하는 {entity} 연결 표에 관계 자체의 속성을 둔다.', '{a} 표의 한 칸에 모든 {b} 키를 쉼표로 저장한다.', '{b} 표에서 전체 {a}를 단 하나의 고정 문자열로 저장한다.', '둘 중 한 표를 지우면 다대다 요구사항을 모두 보존한다.'],0,
    '다대다 관계는 양쪽 대상과 별도의 연결 표로 표현한다. 성적·시간·수량·시각처럼 연결 하나에 속한 정보는 어느 한 대상의 속성이 아니라 연결 행의 속성이다. 반복 대여는 대여 식별자나 시각을 포함해 식별한다.')
concept('cardinality','관계의 카디널리티','ER 모델링','주어진 업무 규칙에서 부모 한 건과 자식의 관계는?',
    [('주문','고객','주문','주문은 정확히 고객 한 명에게 속하며 고객은 주문을 0개 이상 가질 수 있다.'),
     ('직원','부서','직원','직원은 정확히 부서 하나에 속하며 부서는 직원을 0명 이상 가질 수 있다.'),
     ('장비','모델','장비','장비는 정확히 모델 하나에 속하며 모델은 장비를 0대 이상 가질 수 있다.'),
     ('게시물','작성자','게시물','게시물은 정확히 작성자 한 명에게 속하며 작성자는 게시물을 0개 이상 가질 수 있다.')],
    ['{a} 대 {b}는 1:N이며 자식 쪽 부모 참조를 필수로 한다.', '{a} 대 {b}는 항상 1:1이다.', '{b} 한 건이 동시에 모든 {a}를 참조하는 N:M이다.', '부모가 자식을 0개 가질 수 있으면 자식도 부모 없이 허용해야 한다.'],0,
    '부모 하나가 여러 자식을 가질 수 있고 자식 하나는 부모 하나만 갖는다. 부모의 자식 참여가 선택적이라는 것과 자식의 부모 참조가 필수라는 것은 서로 다른 참여 조건이다.','기초')
concept('surrogate','자연키 변경과 대리키','ER 모델링','변경될 수 있는 업무 번호로 여러 표가 연결될 때 적절한 설계 고려는?',
    [('업체','사업용코드','업체ID','사업용코드는 업무 개편으로 변경될 수 있지만 같은 업체의 이력은 계속 연결해야 한다.'),
     ('직원','사번표시값','직원ID','합병 후 표시 사번이 바뀔 수 있지만 같은 직원의 이력은 계속 연결해야 한다.'),
     ('상품','판매코드','상품ID','판매코드는 개편으로 변경될 수 있지만 같은 상품의 이력은 계속 연결해야 한다.'),
     ('장비','관리라벨','장비ID','관리라벨은 교체될 수 있지만 같은 장비의 이력은 계속 연결해야 한다.')],
    ['안정적인 {b}로 관계를 연결하고 현재 {a}에는 필요한 유일성 제약을 별도로 둔다.', '대리키를 만들면 모든 업무 유일성 제약이 자동으로 사라져도 된다.', '업무 코드가 바뀔 때 관련 이력 행을 모두 삭제한다.', '모든 관계에 표시 이름 문자열만 복사한다.'],0,
    '대리키는 관계의 식별자를 업무 표시값 변경과 분리할 수 있다. 하지만 대리키가 있다고 업무 코드의 중복 허용 여부까지 결정되는 것은 아니므로 필요한 UNIQUE 제약은 별도로 둔다.')
concept('atomicity','원자성','트랜잭션','두 변경이 함께 성공하거나 함께 취소되어야 하는 성질은?',
    [('송금','출금','입금','출금만 성공하고 입금이 실패한 상태를 허용하지 않는다.'),
     ('주문','주문생성','재고차감','주문생성만 성공하고 재고차감이 실패한 상태를 허용하지 않는다.'),
     ('좌석변경','기존예약해제','새예약생성','기존예약해제만 성공하고 새예약생성이 실패한 상태를 허용하지 않는다.'),
     ('보증이관','기존담당해제','새담당지정','기존담당해제만 성공하고 새담당지정이 실패한 상태를 허용하지 않는다.')],
    ['원자성: {a}와 {b}를 한 트랜잭션의 성공·취소 단위로 처리한다.', '지속성: 미커밋 변경을 반드시 다른 사용자에게 즉시 보인다.', '인덱스 선택성: 항상 모든 열에 인덱스를 만든다.', '정렬 안정성: 이름순 정렬만 하면 두 변경이 함께 성공한다.'],0,
    '원자성은 트랜잭션의 일부 결과만 확정되지 않도록 하는 all-or-nothing 성질이다. 두 변경을 한 트랜잭션으로 묶고 실패 시 함께 취소하는 처리가 필요하다.','기초')
concept('durability','지속성','트랜잭션','성공한 COMMIT 이후 장애가 나도 확정 결과를 복구하는 성질은?',
    [('입금','확정잔액','재시작','입금 COMMIT 응답을 받은 뒤 서버가 중단됐다.'),
     ('접수','확정접수번호','재시작','접수 COMMIT 응답을 받은 뒤 DB 프로세스가 중단됐다.'),
     ('계정생성','확정계정','재시작','계정생성 COMMIT 응답을 받은 뒤 서버가 중단됐다.'),
     ('승인','확정승인상태','재시작','승인 COMMIT 응답을 받은 뒤 DB 프로세스가 중단됐다.')],
    ['지속성: 성공적으로 커밋한 {a}는 복구 후에도 유지되어야 한다.', '원자성: 커밋한 변경도 모든 재시작에서 무조건 취소한다.', '독립성: 테이블 이름이 서로 다르면 자동 백업된다.', 'NULL 비교: 빈 값만 복구하면 확정 결과도 복구된다.'],0,
    '지속성은 DB가 성공적으로 커밋한 결과를 이후 장애에도 보존하는 성질이다. 로그와 저장장치에 대한 적절한 기록·복구 설정이 이를 뒷받침하며 미커밋 변경의 지속성을 요구하는 것은 아니다.','기초')
concept('dirty-read','더티 리드','동시성과 격리','아직 커밋하지 않은 변경을 읽는 현상을 무엇이라 하는가?',
    [('잔액조회','잔액','100→150','T1이 잔액을 변경하고 미커밋 상태다. T2가 그 값을 읽은 후 T1은 ROLLBACK한다.'),
     ('재고조회','재고','10→4','T1이 재고를 변경하고 미커밋 상태다. T2가 그 값을 읽은 후 T1은 ROLLBACK한다.'),
     ('점수조회','점수','60→90','T1이 점수를 변경하고 미커밋 상태다. T2가 그 값을 읽은 후 T1은 ROLLBACK한다.'),
     ('등급조회','등급','B→A','T1이 등급을 변경하고 미커밋 상태다. T2가 그 값을 읽은 후 T1은 ROLLBACK한다.')],
    ['더티 리드: T2가 미커밋 {a}를 읽었다.', '팬텀 리드: 반드시 새 행 삽입만 있었던 것이다.', '커버링 인덱스: 모든 변경이 안전하게 확정됐다.', '무손실 분해: 두 관계를 조인한 것이다.'],0,
    'T2가 읽은 값은 T1의 커밋으로 확정되지 않았고 이후 취소된다. 이런 미커밋 데이터 읽기가 더티 리드다. 격리 수준이나 DB 구현에 따라 허용 여부가 달라지므로 이 문제는 관찰된 현상 자체를 묻는다.')
concept('nonrepeatable','반복 불가능 읽기','동시성과 격리','같은 행을 두 번 읽었는데 다른 커밋으로 값이 달라진 현상은?',
    [('잔액','잔액','100→120','T1이 행을 읽고 T2가 그 행의 값을 바꿔 COMMIT했다. T1이 같은 행을 다시 읽어 새 값을 봤다.'),
     ('재고','재고','30→25','T1이 행을 읽고 T2가 그 행의 값을 바꿔 COMMIT했다. T1이 같은 행을 다시 읽어 새 값을 봤다.'),
     ('상태','심사상태','대기→완료','T1이 행을 읽고 T2가 그 행의 값을 바꿔 COMMIT했다. T1이 같은 행을 다시 읽어 새 값을 봤다.'),
     ('담당','담당자','민서→지후','T1이 행을 읽고 T2가 그 행의 값을 바꿔 COMMIT했다. T1이 같은 행을 다시 읽어 새 값을 봤다.')],
    ['반복 불가능 읽기: 같은 행의 {a}가 재조회 때 달라졌다.', '더티 리드: T2의 변경은 커밋되지 않았다고 볼 수밖에 없다.', '팬텀 리드만 해당하며 같은 행 값 변경은 상관없다.', '함수 종속: 후보키 최소성을 검사한 것이다.'],0,
    'T2는 이미 커밋했다. T1의 같은 행 재조회가 다른 값을 읽었으므로 반복 불가능 읽기다. 새 조건 일치 행이 추가되는 팬텀과 관찰 지점이 다르다.')
concept('phantom','팬텀 리드','동시성과 격리','같은 조건으로 재조회한 결과에 새 행이 나타난 현상은?',
    [('고액신청','금액','1000 이상','T1이 조건에 맞는 행들을 읽었다. T2가 조건을 만족하는 새 행을 INSERT하고 COMMIT했다. T1 재조회에 새 행이 추가됐다.'),
     ('대기접수','상태','대기','T1이 조건에 맞는 행들을 읽었다. T2가 조건을 만족하는 새 행을 INSERT하고 COMMIT했다. T1 재조회에 새 행이 추가됐다.'),
     ('활성계정','활성여부','1','T1이 조건에 맞는 행들을 읽었다. T2가 조건을 만족하는 새 행을 INSERT하고 COMMIT했다. T1 재조회에 새 행이 추가됐다.'),
     ('저재고상품','재고','5 미만','T1이 조건에 맞는 행들을 읽었다. T2가 조건을 만족하는 새 행을 INSERT하고 COMMIT했다. T1 재조회에 새 행이 추가됐다.')],
    ['팬텀 리드: 같은 조건의 결과 집합에 새 행이 나타났다.', '더티 리드: 새 행은 미커밋이라고 가정해야 한다.', '원자성 위반: INSERT가 성공하면 항상 원자성이 깨진다.', '정규화 위반: 행 수가 늘면 항상 제2정규형 위반이다.'],0,
    '동일 조건을 다시 실행했을 때 이전에 없던 조건 일치 행이 생겼다. 이 결과 집합 변화가 팬텀 리드다. 격리 수준 이름만으로 구현을 단정하지 않고 제시된 관찰로 판단한다.')
concept('lost-update','갱신 분실','동시성과 격리','서로 읽은 이전 값을 기준으로 덮어쓰는 문제의 해결 방향은?',
    [('재고','재고','수량','T1과 T2가 같은 재고 10을 읽고 각자 1개 차감한 값 9를 써 최종 9가 됐다. 실제 두 번 차감해야 한다.'),
     ('조회수','조회수','횟수','T1과 T2가 같은 조회수 10을 읽고 각자 1 증가한 값 11을 써 최종 11이 됐다. 실제 두 번 증가해야 한다.'),
     ('예약','남은좌석','수량','T1과 T2가 같은 남은좌석 10을 읽고 각자 1 차감한 값 9를 써 최종 9가 됐다. 실제 두 번 차감해야 한다.'),
     ('누적실적','누적실적','횟수','T1과 T2가 같은 누적실적 10을 읽고 각자 1 증가한 값 11을 써 최종 11이 됐다. 실제 두 번 증가해야 한다.')],
    ['원자적 증감 UPDATE 또는 잠금·버전 검증으로 충돌을 제어한다.', '두 트랜잭션 모두 이전 값을 읽어 덮어쓰는 방식을 그대로 둔다.', '값을 문자열로 바꾸면 동시성이 자동 해결된다.', '모든 SELECT에서 ORDER BY를 제거하면 갱신 분실이 사라진다.'],0,
    '각자 이전 값을 읽고 계산한 결과를 그대로 저장하면 한 트랜잭션의 변화가 덮어써질 수 있다. DB 내 원자적 증감, 적절한 잠금 또는 버전 조건을 이용한 충돌 검출과 재시도로 갱신 분실을 제어한다.', '심화')
concept('deadlock','교착 상태의 순환 대기','동시성과 격리','서로 상대가 보유한 잠금을 기다리는 상황을 줄이는 방법은?',
    [('계정','계정 A','계정 B','T1은 A 잠금을 갖고 B를 기다리며 T2는 B 잠금을 갖고 A를 기다린다.'),
     ('재고','상품 A','상품 B','T1은 A 잠금을 갖고 B를 기다리며 T2는 B 잠금을 갖고 A를 기다린다.'),
     ('담당배정','직원 A','직원 B','T1은 A 잠금을 갖고 B를 기다리며 T2는 B 잠금을 갖고 A를 기다린다.'),
     ('좌석','좌석 A','좌석 B','T1은 A 잠금을 갖고 B를 기다리며 T2는 B 잠금을 갖고 A를 기다린다.')],
    ['여러 자원의 잠금 획득 순서를 통일하고 교착 감지 시 적절히 재시도한다.', '각 트랜잭션이 항상 반대 순서로 잠금을 잡도록 한다.', '둘 다 기다리면 반드시 자동으로 모든 변경이 성공한다.', '잠금 대기 상태에서는 실패를 처리할 필요가 없다.'],0,
    '상대가 가진 자원을 서로 기다리는 순환이 교착을 만든다. 공통 자원 순서에 따라 잠금을 획득하면 이런 순환 가능성을 줄이고, 실제 교착 취소가 발생하면 트랜잭션 단위로 안전하게 재시도한다.', '심화')
concept('optimistic','낙관적 버전 검증','동시성과 격리','읽은 뒤 다른 수정이 있었는지 확인하는 UPDATE 방식은?',
    [('신청','상태','version','사용자가 version=3인 신청을 읽고 편집한다. 저장 시 다른 사용자의 변경을 덮어쓰면 안 된다.'),
     ('계정','설정','version','사용자가 version=3인 계정설정을 읽고 편집한다. 저장 시 다른 사용자의 변경을 덮어쓰면 안 된다.'),
     ('상품','가격','version','사용자가 version=3인 상품가격을 읽고 편집한다. 저장 시 다른 사용자의 변경을 덮어쓰면 안 된다.'),
     ('배정','담당자','version','사용자가 version=3인 배정을 읽고 편집한다. 저장 시 다른 사용자의 변경을 덮어쓰면 안 된다.')],
    ['WHERE id=? AND version=3으로 갱신하고 version을 증가시키며 영향 행 수 0이면 충돌 처리한다.', 'WHERE id=?만 사용하고 version을 그대로 둔다.', 'version을 화면에 표시하기만 하면 DB에서 충돌이 자동 검출된다.', '항상 아무 조건 없는 UPDATE를 사용하면 다른 변경을 보존한다.'],0,
    '읽었던 버전과 현재 버전이 같을 때만 갱신하도록 조건을 둔다. 성공 시 버전을 증가시키고 영향 행 수가 0이면 이미 바뀐 데이터 또는 사라진 행으로 취급해 새로 읽거나 재시도한다.', '심화')
concept('composite-index','복합 B-tree의 열 순서','인덱스와 성능','주어진 동등 조건과 범위 조건에 맞는 인덱스 순서는?',
    [('접수검색','지점코드','접수일','주요 쿼리는 지점코드 동등 조건과 접수일 범위 조건을 함께 사용한다.'),
     ('작업검색','담당팀','생성일','주요 쿼리는 담당팀 동등 조건과 생성일 범위 조건을 함께 사용한다.'),
     ('주문검색','고객번호','주문일','주요 쿼리는 고객번호 동등 조건과 주문일 범위 조건을 함께 사용한다.'),
     ('로그검색','시스템코드','발생시각','주요 쿼리는 시스템코드 동등 조건과 발생시각 범위 조건을 함께 사용한다.')],
    ['일반적인 후보는 ({a}, {b}) B-tree이며 실제 사용은 실행 계획으로 확인한다.', '인덱스가 있으면 옵티마이저가 어떤 쿼리에도 반드시 사용한다.', '열 순서는 모든 조건에서 항상 아무 영향이 없다.', '{b}를 함수로 바꾸면 모든 DB가 일반 인덱스를 항상 그대로 사용한다.'],0,
    '선두 열의 동등 조건으로 영역을 좁히고 다음 열의 범위를 탐색하는 복합 B-tree가 일반적인 후보이다. 데이터 분포·쿼리·DB 구현에 따라 선택이 달라질 수 있어 실제 실행 계획과 측정으로 확인한다.')
concept('sargable','조건식과 인덱스 활용','인덱스와 성능','날짜 열의 일반 B-tree 인덱스를 검토할 때 유리한 조건 형태는?',
    [('접수','접수시각','2026-10-03','접수시각의 하루 범위를 조회한다. 열은 시간까지 저장한다.'),
     ('주문','주문시각','2026-10-03','주문시각의 하루 범위를 조회한다. 열은 시간까지 저장한다.'),
     ('로그','발생시각','2026-10-03','발생시각의 하루 범위를 조회한다. 열은 시간까지 저장한다.'),
     ('배치','완료시각','2026-10-03','완료시각의 하루 범위를 조회한다. 열은 시간까지 저장한다.')],
    ['{a} >= 당일 00:00 AND {a} < 다음날 00:00 범위를 검토한다.', '{a}를 문자열로 매번 변환하면 일반 인덱스 사용이 항상 보장된다.', '시간이 있어도 {a} = 당일 00:00만으로 하루 전체가 선택된다.', '범위 조건에서 다음날 00:00을 <=로 포함해야 하루만 정확히 고른다.'],0,
    '열 자체에 하한 포함·다음날 상한 제외 조건을 걸면 시간값을 빠짐없이 하루 범위로 선택할 수 있다. 함수나 문자열 변환을 열에 적용하는 조건과 일반 인덱스 활용 가능성은 다르며 실제 계획 확인이 필요하다.')
concept('covering','커버링 인덱스','인덱스와 성능','조회에 필요한 값을 인덱스 안에서 모두 얻을 수 있는 경우의 의미는?',
    [('고객검색','고객번호','등급','필터와 SELECT에 필요한 고객번호·등급이 같은 인덱스에 모두 있다.'),
     ('주문검색','고객번호','주문번호','필터와 SELECT에 필요한 고객번호·주문번호가 같은 인덱스에 모두 있다.'),
     ('접수검색','지점코드','접수번호','필터와 SELECT에 필요한 지점코드·접수번호가 같은 인덱스에 모두 있다.'),
     ('작업검색','상태','작업번호','필터와 SELECT에 필요한 상태·작업번호가 같은 인덱스에 모두 있다.')],
    ['커버링 인덱스로 추가 본문 행 조회를 줄일 가능성이 있다.', '이 경우 쓰기 유지 비용과 저장 공간이 무조건 0이다.', 'ORDER BY가 없어도 모든 표시 순서가 업무 기준으로 보장된다.', '모든 DB와 상태에서 본문 접근은 절대 한 번도 필요하지 않다.'],0,
    '쿼리에 필요한 열을 인덱스에서 얻을 수 있으면 본문 테이블 접근을 줄일 수 있다. 다만 DB의 가시성 확인 등 구현과 상태에 따라 실제 접근은 달라지며 공간과 쓰기 유지 비용은 계속 고려한다.')
concept('least-privilege','최소 권한','보안과 운영','조회 전용 기능의 DB 권한으로 적절한 것은?',
    [('통계서비스','집계뷰','읽기','서비스는 승인된 집계뷰를 SELECT만 하며 데이터 변경이나 스키마 변경이 필요 없다.'),
     ('보고서서비스','보고서뷰','읽기','서비스는 승인된 보고서뷰를 SELECT만 하며 데이터 변경이나 스키마 변경이 필요 없다.'),
     ('모니터링','모니터링뷰','읽기','서비스는 승인된 모니터링뷰를 SELECT만 하며 데이터 변경이나 스키마 변경이 필요 없다.'),
     ('학습대시보드','학습통계뷰','읽기','서비스는 승인된 학습통계뷰를 SELECT만 하며 데이터 변경이나 스키마 변경이 필요 없다.')],
    ['전용 계정에 필요한 {a}의 SELECT 권한만 부여한다.', '편의를 위해 모든 표의 UPDATE·DELETE와 관리자 권한을 부여한다.', '읽기 기능도 매번 전체 관리자 비밀번호를 사용자에게 전달한다.', '권한을 구분하지 않아도 앱 화면에서 버튼만 숨기면 충분하다.'],0,
    '최소 권한은 기능 수행에 필요한 대상과 연산만 허용하는 원칙이다. 승인된 뷰의 SELECT만 필요한 계정에 광범위한 변경·관리 권한을 주면 불필요한 오작동이나 침해 범위가 커진다.','기초')
concept('parameterized','SQL 매개변수 바인딩','보안과 운영','사용자 입력을 SQL 값으로 안전하게 전달하는 기본 방법은?',
    [('고객조회','이름','사용자입력','이름 검색 입력을 SQL 문자열에 그대로 이어 붙이고 있다.'),
     ('계정조회','아이디','사용자입력','아이디 입력을 SQL 문자열에 그대로 이어 붙이고 있다.'),
     ('상품조회','상품명','사용자입력','상품명 입력을 SQL 문자열에 그대로 이어 붙이고 있다.'),
     ('접수조회','메모','사용자입력','메모 검색 입력을 SQL 문자열에 그대로 이어 붙이고 있다.')],
    ['값 자리에 매개변수를 두고 DB 드라이버의 바인딩 API로 {a} 입력을 전달한다.', '입력 앞뒤에 작은따옴표만 추가하면 모든 공격이 차단된다.', 'SQL 문자열 전체를 화면에서 숨기기만 하면 충분하다.', '입력을 SQL 명령으로 해석하도록 그대로 연결하는 것을 유지한다.'],0,
    '매개변수 바인딩은 입력값을 SQL 문법과 분리해 값으로 전달한다. 단순 문자열 결합이나 따옴표 추가에 의존하지 않는다. 표·열 이름 같은 식별자는 값 매개변수로 대체하지 않고 허용 목록 등으로 별도 제어한다.','기초')
concept('backup-recovery','백업의 복구 검증','보안과 운영','운영 백업이 실제 복구에 쓸 수 있는지 확인하는 가장 직접적인 방법은?',
    [('접수DB','접수 데이터','백업','정기 백업 파일이 존재하지만 복구를 한 번도 시험하지 않았다.'),
     ('학습DB','학습 데이터','백업','정기 백업 파일이 존재하지만 복구를 한 번도 시험하지 않았다.'),
     ('재고DB','재고 데이터','백업','정기 백업 파일이 존재하지만 복구를 한 번도 시험하지 않았다.'),
     ('고객DB','고객 데이터','백업','정기 백업 파일이 존재하지만 복구를 한 번도 시험하지 않았다.')],
    ['격리된 환경에서 실제 복구하고 필요한 데이터와 제약·시간 목표를 검증한다.', '백업 파일 이름에 complete를 붙이는 것으로 복구 가능성을 증명한다.', '백업 파일 크기가 0보다 크면 데이터 정확성을 전부 보장한다.', '복구 시험 없이 백업 성공 로그만 평생 확인한다.'],0,
    '백업 생성 성공과 실제 복구 가능성은 별도 문제다. 운영 데이터에 영향을 주지 않는 격리 환경에서 복원하고 내용·무결성과 소요 시간을 확인해야 복구 절차와 목표를 검증할 수 있다.')
concept('relational-division','관계 나눗셈과 모든 조건','관계 대수','필수 집합의 모든 항목과 연결된 대상을 찾는 관계 연산의 의미는?',
    [('자격직원','직원','필수자격','보유(직원,자격) 관계와 필수자격(자격) 관계가 있다. 필수자격을 모두 보유한 직원을 찾는다.'),
     ('이수학생','학생','필수과목','이수(학생,과목) 관계와 필수과목(과목) 관계가 있다. 필수과목을 모두 이수한 학생을 찾는다.'),
     ('지원제품','제품','필수규격','지원(제품,규격) 관계와 필수규격(규격) 관계가 있다. 필수규격을 모두 지원하는 제품을 찾는다.'),
     ('가능업체','업체','필수지역','배송(업체,지역) 관계와 필수지역(지역) 관계가 있다. 필수지역을 모두 배송할 수 있는 업체를 찾는다.')],
    ['관계 나눗셈은 {b}의 모든 값과 연결된 {a}를 찾는 의미다.', '일부 값 하나와만 연결되면 모든 조건을 충족했다고 본다.', '카티션 곱을 만들면 원래 연결 사실에 관계없이 모든 대상이 적격이다.', '순서대로 정렬하기만 하면 모든 조건 충족 여부가 자동 계산된다.'],0,
    '관계 나눗셈은 연결 관계를 필수 값 집합으로 나누어 각 필수 값과 전부 연결된 대상을 구하는 연산이다. SQL에서는 누락된 필수 값이 존재하지 않는다는 NOT EXISTS 구조 등으로 표현할 수 있다. 하나라도 연결된 EXISTS와 모든 값 연결은 다르다.', '심화')


def korean_format(template, values):
    """Choose natural Korean particles after dynamically inserted subject nouns."""
    for key, value in values.items():
        if not value:
            continue
        last = ord(value[-1])
        final = (last-0xAC00)%28 if 0xAC00<=last<=0xD7A3 else 0
        for written, with_final, without_final in [
                ('는','은','는'), ('가','이','가'), ('를','을','를'),
                ('와','과','와'), ('로','으로','로')]:
            particle = with_final if final else without_final
            if written=='로' and final==8:
                particle='로'
            template = template.replace('{'+key+'}'+written, '{'+key+'}'+particle)
    return template.format(**values)


# Three genuinely different decision problems following the first application of
# each concept. These change conditions, requested judgments and misconceptions.
VARIANTS = {}


def variants(key, *rows):
    assert len(rows)==3
    VARIANTS[key] = rows


variants('candidate-key',
 ('슈퍼키와 최소성', 'R(A,B,C)에서 A가 유일하고 NULL이 없다. A→B,C이다. A와 B를 함께 잡은 집합을 판단한다.',
  '집합 {A,B}에 대한 올바른 설명은?', ['유일성은 있지만 B를 빼도 식별되므로 후보키는 아니다.','유일성이 전혀 없다.','반드시 유일한 후보키다.','B만으로 모든 행을 식별할 수 있다.'],0,
  'A가 이미 모든 행을 식별한다. {A,B}는 슈퍼키지만 불필요한 B를 제거할 수 있어 최소성이 없으므로 후보키가 아니다.'),
 ('대체 후보키', '직원번호와 업무이메일은 각각 유일·필수다. 기본키로 직원번호를 선택했다.',
  '업무이메일의 역할은?', ['기본키로 선택되지 않은 후보키이며 대체키로 볼 수 있다.','기본키가 아니므로 유일성은 반드시 제거해야 한다.','직원번호와 결합하지 않으면 슈퍼키가 아니다.','항상 외래키다.'],0,
  '여러 후보키 중 하나만 기본키로 선택해도 나머지는 후보키의 식별 능력을 유지한다. 이를 대체키라고 부를 수 있으며 외래키 여부는 별도의 참조 관계다.'),
 ('종속으로 후보키 구하기', 'R(A,B,C), 함수 종속 A→B, B→A, A→C가 주어진다. 다른 종속은 없다.',
  '후보키의 전체 목록은?', ['A와 B 각각','A만','C만','(A,B)만'],0,
  'A+={A,B,C}이고 B→A를 거쳐 B+도 전체 속성이 된다. A와 B 각각 단일 열로 최소이고 C에서는 다른 열을 얻지 못한다.'))
variants('composite-key',
 ('복합키 중복 검사', 'Tickets의 기본키는 (branch,no). 기존 행은 (A,1),(A,2),(B,1)이다. 다른 제약은 없고 모든 값은 필수다.',
  '키 위반 없이 삽입 가능한 행은?', ['(B,2)','(A,1)','(A,2)','(B,1)'],0,
  '복합키는 두 값의 조합으로 중복을 검사한다. B라는 지점이나 2라는 번호가 각각 존재해도 (B,2) 조합은 새 값이므로 허용된다.'),
 ('관계 식별자에 시각 추가', 'Rental(member_id,device_id,start_time)에서 같은 회원이 같은 장비를 여러 시점에 다시 대여할 수 있다. 동일 회원·장비·시각의 대여는 한 건이다.',
  '모든 대여 이력을 구분하는 자연 복합키는?', ['(member_id,device_id,start_time)','(member_id,device_id)','device_id만','member_id만'],0,
  '회원과 장비만으로는 반복 대여를 구분하지 못한다. 시작 시각까지 포함하면 지문에서 한 건이라고 정한 조합을 식별할 수 있다.'),
 ('복합키의 필수성', 'Enrollment(student_id,course_id)의 기본키가 두 열의 조합이다. 관계형 기본키는 모든 구성 열을 필수로 한다.',
  '표준적인 기본키 제약에서 허용할 수 없는 행은?', ['(NULL,10)','(1,10)','(1,11)','(2,10)'],0,
  '기본키의 NULL 금지는 조합 전체뿐 아니라 각 구성 열에 적용된다. student_id가 NULL인 행은 다른 행과 중복되지 않아도 기본키 조건을 어긴다.'))
variants('foreign-key',
 ('없는 부모 참조', 'Customer(id)에는 1,2만 있다. Order.customer_id는 Customer.id를 참조하는 필수 외래키다.',
  '고객번호 3으로 주문을 추가하려면 먼저 충족해야 할 조건은?', ['참조 가능한 고객 3이 존재해야 한다.','주문번호만 새 값이면 부모는 없어도 된다.','고객번호를 문자열로 캐스팅하면 부모가 불필요하다.','정렬하면 없는 부모 참조가 허용된다.'],0,
  '필수 외래키는 참조 값이 부모 키에 존재하도록 요구한다. 자식의 자체 기본키가 새 값인지는 별도의 제약이며 참조 대상 부재를 해결하지 못한다.'),
 ('선택적 외래키', 'Task.owner_id는 Staff.id를 참조하지만 NOT NULL은 없다. 담당자 미배정 상태를 NULL로 표현한다. 단일 열 외래키다.',
  'NOT NULL을 추가하지 않은 현재 설계의 의미는?', ['미배정 NULL은 허용되지만 입력한 담당자번호는 존재하는 직원을 참조해야 한다.','존재하지 않는 임의 숫자도 모두 허용된다.','외래키가 있으면 NULL이 자동 금지된다.','직원 표의 모든 id가 Task에도 반드시 있어야 한다.'],0,
  '단일 열 외래키의 NULL은 관계가 없는 상태로 허용할 수 있다. 실제 참조 값을 저장하면 부모 존재 여부를 검사하며 필수 관계는 NOT NULL을 별도 지정한다.'),
 ('참조 대상 유일성', 'Department에 dept_id가 PRIMARY KEY이고 name은 중복 가능한 표시명이다. Employee가 부서 하나를 참조해야 한다.',
  '외래키 참조 대상으로 가장 적절한 열은?', ['dept_id','중복 가능한 name','행의 현재 표시 순번','항상 첫 번째 물리 행'],0,
  '부서의 고유 식별자인 dept_id를 참조하면 대상이 명확하다. 중복 표시명이나 물리 행 순서는 관계의 안정적인 유일 식별자가 아니다.'))
variants('check-domain',
 ('CHECK와 NULL', 'PostgreSQL에서 amount INTEGER CHECK(amount>=0)만 선언했다. NOT NULL은 선언하지 않았다.',
  'amount=NULL을 넣을 때 이 CHECK 자체의 판단은?', ['조건이 UNKNOWN이므로 이 CHECK만으로 NULL을 거부하지 않는다.','UNKNOWN을 거짓으로 보아 항상 거부한다.','NULL을 자동으로 0으로 변경한다.','NULL을 자동으로 1로 변경한다.'],0,
  'CHECK는 거짓인 조건을 거부한다. NULL에 대한 비교는 UNKNOWN이며 PostgreSQL CHECK는 참 또는 NULL을 허용하므로 필수 입력은 NOT NULL이 필요하다.'),
 ('상태별 범위 제약', '할인율은 0부터 100까지이며 값이 반드시 있어야 한다.',
  '요구조건을 정확히 표현한 것은?', ['NOT NULL과 CHECK(rate BETWEEN 0 AND 100)','CHECK(rate>=0 OR rate<=100)만','CHECK(rate<100)만','UNIQUE(rate)만'],0,
  '양끝 포함 구간은 rate>=0 AND rate<=100 또는 BETWEEN이다. OR는 범위 밖 값도 한쪽 조건을 만족해 허용하고 UNIQUE는 범위나 필수 입력을 강제하지 않는다.'),
 ('열 사이의 제약', '예약은 start_time과 end_time을 필수 입력하며 종료가 시작보다 뒤여야 한다.',
  '두 시각의 관계를 강제하는 핵심 CHECK는?', ['CHECK(end_time>start_time)','CHECK(end_time<>NULL)','UNIQUE(start_time)','CHECK(start_time>0)'],0,
  '요구사항은 두 열 사이의 순서 비교이므로 end_time>start_time이다. 두 열의 NULL 금지는 별도 NOT NULL이 맡으며 단일 열 UNIQUE는 시간 순서를 보장하지 않는다.'))
variants('delete-cascade',
 ('부모 삭제 거부', '계약을 참조하는 청구서가 있으면 계약의 물리 삭제를 허용하지 않아야 한다.',
  '외래키 삭제 동작으로 적절한 것은?', ['참조 자식이 있을 때 삭제를 거부하는 RESTRICT 정책','ON DELETE CASCADE로 청구서도 삭제','ON DELETE SET NULL로 청구서 연결 제거','외래키를 삭제해 제한 제거'],0,
  '관련 청구서가 있으면 부모 삭제를 거절해야 하므로 삭제 제한 정책을 사용한다. CASCADE나 SET NULL은 삭제를 허용한 뒤 자식에 다른 조치를 취한다.'),
 ('관계만 해제', '퇴사한 직원의 계정을 삭제해도 과거 작업 기록은 남기되 owner_id는 NULL로 바꾼다. owner_id는 NULL 허용이다.',
  '정책에 맞는 삭제 동작은?', ['ON DELETE SET NULL','ON DELETE CASCADE','작업 기록도 반드시 삭제하는 정책','직원 삭제 때 모든 작업을 INSERT하는 정책'],0,
  'SET NULL은 자식 행을 유지하고 참조 값을 비운다. 자식 외래키가 NOT NULL이면 이 요구와 충돌하므로 NULL 허용이라는 지문 조건이 필요하다.'),
 ('연쇄 삭제 영향', 'Batch→Job→JobLog의 두 외래키가 모두 ON DELETE CASCADE이다. 한 Batch를 삭제하고 그 Batch에만 속한 Job과 그 Job의 Log가 있다.',
  '일반적인 연쇄 동작의 결과는?', ['연결된 Job과 그 Job의 Log도 삭제된다.','Job은 삭제되지만 연결된 Log는 반드시 고아로 남는다.','Batch만 삭제되고 자식은 아무 검사 없이 남는다.','다른 Batch에 속한 모든 Job까지 무조건 삭제된다.'],0,
  '첫 참조에서 Batch 삭제가 Job 삭제를 전파하고, 두 번째 참조에서 Job 삭제가 해당 JobLog 삭제를 전파한다. 연결되지 않은 다른 Batch의 행까지 지우는 것은 아니다.'))
variants('first-normal',
 ('반복 열의 확장 문제', 'Contact(customer_id,phone1,phone2,phone3)로 전화번호를 저장한다. 앞으로 네 개 이상도 허용해야 하고 번호별 유일성 검사도 필요하다.',
  '요구사항에 맞는 구조 개선은?', ['ContactPhone(customer_id,phone)처럼 번호당 한 행을 둔다.','phone4,phone5를 끝없이 추가하는 것만 가능하다.','phone1에 모든 번호를 문자열로 합친다.','고객번호를 전화번호 개수로 바꾼다.'],0,
  '별도 자식 표의 행 수로 여러 번호를 표현하면 수량 증가가 스키마 열 추가를 요구하지 않고 각 번호에 개별 제약과 조회를 적용할 수 있다.'),
 ('목록 문자열 검색', 'Skills(employee_id,skill_list)의 skill_list가 "SQL,Python" 같은 문자열이다. 기술 하나와 정확히 연결된 직원을 찾아야 한다.',
  '목록 문자열 대신 관계형 연결 표를 쓸 때 얻는 이점은?', ['각 기술을 별도 값으로 비교하고 외래키 등 제약을 적용하기 쉽다.','어떤 기술명도 부분 문자열 검색으로만 검사해야 한다.','연결 표의 모든 열이 반드시 NULL이 된다.','기술 개수만 저장하면 기술 이름도 자동 복원된다.'],0,
  '기술별 행을 저장하면 정확한 동등 비교와 참조 검사를 사용할 수 있다. 문자열 부분 검색은 토큰 경계·구분자·표기 변경을 별도 처리해야 한다.'),
 ('연결 값 중복 방지', 'StudentPhone(student_id,phone)에서 같은 학생에게 같은 번호를 두 번 등록하는 것을 금지하되 다른 학생이 같은 가족 전화번호를 쓰는 것은 허용한다.',
  '적절한 유일성 제약은?', ['UNIQUE(student_id,phone)','UNIQUE(phone)만','UNIQUE(student_id)만','제약 대신 모든 번호를 한 칸에 합친다.'],0,
  '금지하려는 중복 단위는 학생과 전화번호의 조합이다. 전화번호만 유일하면 가족 공유를 막고 학생번호만 유일하면 여러 번호 등록을 막는다.'))
variants('second-normal',
 ('부분 종속 판정', 'R(order_id,item_id,item_name,qty)는 원자값을 저장하고 키=(order_id,item_id)이다. item_id→item_name이며 키→qty이다.',
  '부분 함수 종속에 해당하는 것은?', ['item_id→item_name','(order_id,item_id)→qty','키의 모든 값이 NOT NULL인 사실','행 수가 100인 사실'],0,
  '키의 진부분집합 item_id가 비키 속성 item_name을 결정한다. 이것이 부분 종속이며 전체 키가 qty를 결정하는 것은 정상적인 완전 종속 조건이다.'),
 ('단일 후보키의 제2정규형', 'R(id,name,dept)에서 후보키는 단일 열 id뿐이고 모든 값은 원자적이다. dept→name 같은 추가 종속의 제3정규형 여부는 별도다.',
  '제2정규형의 부분 종속 관점에서 올바른 설명은?', ['단일 열 후보키에는 비어 있지 않은 진부분집합이 없어 부분 종속 문제가 없다.','후보키가 단일 열이면 반드시 제2정규형 위반이다.','행이 두 개 이상이면 반드시 부분 종속이다.','열 이름이 id이면 모든 정규형이 자동 보장된다.'],0,
  '제2정규형은 후보키의 진부분집합에 대한 비키 속성의 부분 종속을 배제한다. 단일 후보키의 경우 이런 비어 있지 않은 부분집합은 없지만 제3정규형이나 BCNF까지 자동 만족하는 것은 아니다.'),
 ('잘못된 분해의 키 손실', 'Enrollment의 키는 (student_id,course_id)이고 한 학생은 여러 과목을 수강한다. student_name 분리 후 수강 표의 키를 student_id 하나로 바꾸자는 제안이 있다.',
  '이 제안의 문제는?', ['한 학생의 여러 수강 행을 식별할 수 없어 원래 수강 관계를 보존하지 못한다.','이름을 분리했으니 과목 식별자는 항상 불필요하다.','이름을 문자열로 만들면 기본키가 자동 복구된다.','키 열 개수를 줄이면 무조건 모든 중복이 보존된다.'],0,
  '학생 이름의 부분 종속을 분리하는 것과 수강 관계의 식별자는 별개다. 학생·과목 조합이 수강 한 건을 식별하므로 course_id를 키에서 없애면 여러 수강을 구분하지 못한다.'))
variants('third-normal',
 ('이행 종속 찾기', 'R(employee_id,dept_id,dept_name)에서 employee_id만 후보키이고 employee_id→dept_id,dept_id→dept_name이다.',
  '직원 키에서 dept_name까지의 결정 경로는?', ['employee_id→dept_id→dept_name으로 이행한다.','dept_name이 반드시 employee_id를 결정한다.','dept_id가 자동으로 모든 직원 행의 후보키다.','같은 부서명은 한 직원에게만 허용된다.'],0,
  '직원 식별자로 부서번호를 얻고 부서번호에서 부서명을 얻는 두 단계 결정이 있다. 부서번호가 여러 직원에서 반복될 수 있으므로 직원 표의 슈퍼키라고 볼 수 없다.'),
 ('분리 후 부서명 변경', '직원 표는 (employee_id,dept_id), 부서 표는 (dept_id,dept_name)으로 분리되어 있다. 부서 7의 직원은 20명이다.',
  '부서 7의 이름 변경을 저장하는 기본 대상은?', ['부서 표의 dept_id=7 한 행','직원 표의 20개 행에 이름을 복사해 각각 수정','모든 직원의 employee_id','부서 7 직원의 수만 변경'],0,
  '부서명 사실은 부서 표에서 부서번호당 한 번 관리한다. 직원 행은 참조번호를 보존하므로 이름 변경 때문에 같은 사실을 20번 복사할 필요가 없다.'),
 ('제3정규형 조건', '함수 종속 X→A가 비자명하다. X는 슈퍼키가 아니고 A는 어떤 후보키에도 포함되지 않는 비주요 속성이다.',
  '이 종속에 대한 제3정규형 판단은?', ['제3정규형을 위반한다.','비자명 종속이면 항상 제3정규형을 만족한다.','A가 비주요 속성이라 BCNF도 자동 만족한다.','키를 primary라고 이름 붙이면 종속이 사라진다.'],0,
  '제3정규형은 비자명 종속에서 결정자가 슈퍼키이거나 종속 속성이 주요 속성일 것을 요구한다. 여기서는 두 조건 모두 성립하지 않아 위반한다.',))
variants('bcnf',
 ('BCNF를 만족하는 종속', 'R(A,B,C)의 모든 비자명 종속은 후보키 A 또는 슈퍼키 AB를 결정자로 한다.',
  'BCNF 판단은?', ['모든 비자명 종속의 결정자가 슈퍼키이므로 BCNF를 만족한다.','후보키가 한 개면 반드시 BCNF 위반이다.','A가 후보키여도 결정자로 사용하면 안 된다.','열이 세 개이면 BCNF 검사를 할 수 없다.'],0,
  'BCNF의 조건은 비자명 함수 종속의 모든 결정자가 슈퍼키라는 것이다. 후보키 A는 슈퍼키이고 AB도 A를 포함하므로 슈퍼키다.'),
 ('제3정규형과 BCNF 차이', 'R(S,C,I), SC→I, I→C. 후보키는 SC,SI이며 I 자체는 슈퍼키가 아니다. C는 후보키 SC에 포함되는 주요 속성이다.',
  'I→C 때문에 가능한 정규형 판정은?', ['주요 속성 C 때문에 제3정규형 조건은 가능하지만 BCNF는 위반한다.','제3정규형과 BCNF 조건이 완전히 같으므로 차이가 없다.','I는 후보키에 포함되기만 하면 슈퍼키다.','C가 주요 속성이면 모든 결정자가 슈퍼키로 바뀐다.'],0,
  '제3정규형은 결정자가 슈퍼키가 아니어도 종속 속성이 주요 속성이면 허용한다. BCNF에는 이 예외가 없으므로 I가 슈퍼키가 아닌 종속은 위반이다.'),
 ('분해와 종속 보존의 구분', 'BCNF 분해를 검토한다. 무손실 조인은 확보했지만 일부 원래 함수 종속은 개별 분해 표만 검사해서 강제하기 어렵다.',
  '올바른 설명은?', ['무손실성과 종속 보존은 다른 성질이며 BCNF 분해가 항상 둘 다 보장되지는 않는다.','무손실이면 모든 종속도 반드시 개별 표에서 보존된다.','종속을 보존하지 않으면 항상 원래 행을 복원할 수 없다.','BCNF라는 이름만으로 모든 업무 제약 구현이 끝난다.'],0,
  '무손실은 조인 시 원래 정보를 복원하는 성질이고 종속 보존은 원래 종속을 분해 표의 제약으로 강제할 수 있는 성질이다. BCNF 분해에서 두 목표가 함께 자동 보장되는 것은 아니다.'))
variants('lossless',
 ('공통 열만으로 부족한 분해', 'R(A,B,C)에서 지정된 종속은 없다. R1(A,B),R2(B,C)로 분해한다. 원래 행은 (a1,b,c1),(a2,b,c2)이다.',
  '분해 표를 B로 조인하면 생길 수 있는 문제는?', ['(a1,b,c2),(a2,b,c1) 같은 가짜 조합이 추가된다.','원래 두 행만 항상 반환된다.','B가 공통이면 어떤 종속 없이도 항상 무손실이다.','모든 속성이 자동으로 NULL로 바뀐다.'],0,
  '분해 후 B=b로 두 A와 두 C가 서로 연결되어 네 조합을 만든다. 원래 없던 교차 조합이 생기므로 이 데이터에서 손실 분해이며 공통 열 존재만으로 무손실이 보장되지 않는다.'),
 ('공통 속성의 키 판정', 'R(A,B,C), A→B이고 B→C는 주어지지 않았다. R1(A,B),R2(A,C)로 나눈다.',
  '이진 분해의 무손실 조건을 만족하는 근거는?', ['공통 속성 A가 R1의 모든 속성을 결정한다.','열 이름이 한 글자라 무손실이다.','B와 C가 서로 같은 값이어야만 무손실이다.','두 표의 열 수가 같기만 하면 충분하다.'],0,
  '교집합 A의 폐포에 R1의 속성 A,B가 들어간다. 공통 속성이 한쪽 관계 전체를 결정하는 이진 분해 무손실 조건을 만족한다.'),
 ('무손실과 NULL 보충 구분', '이론적 관계 분해의 무손실 조인을 검토하고 있다. 일부 매칭이 없는 행을 LEFT JOIN으로 보존하면 된다는 제안이 있다.',
  '올바른 판단은?', ['LEFT JOIN의 행 보존은 분해의 자연 조인 무손실성 증명과 별개다.','LEFT JOIN만 쓰면 어떤 관계 분해도 항상 원래 관계와 동일하다.','NULL을 추가하면 모든 함수 종속이 자동 보존된다.','무손실 분해는 결과 열이 한 개일 때만 정의된다.'],0,
  '무손실 분해는 원래 관계를 분해 결과의 조인으로 정확히 복원하는 성질이다. 외부 조인의 NULL 보충은 다른 연산이므로 그것만으로 가짜 조합이나 정보 복원의 문제를 해결했다고 증명하지 못한다.'))
variants('closure',
 ('폐포의 시작 집합', 'R(A,B,C,D), A→B, C→D만 주어진다.',
  'A의 속성 폐포는?', ['{A,B}','{B}만','{A,B,C,D}','{A,D}'],0,
  '시작 집합 A를 포함하고 A→B로 B를 얻는다. C를 얻는 종속이 없으므로 C→D는 적용할 수 없다. 다른 속성을 임의로 추가할 수 없다.'),
 ('복합 결정자 적용', 'R(A,B,C,D), A→B, AC→D만 주어진다.',
  'AC의 폐포는?', ['{A,B,C,D}','{A,C}만','{A,B}만','{B,D}만'],0,
  '시작 집합 A,C에서 A→B로 B를 얻고 AC→D로 D를 얻는다. 처음부터 A와 C가 함께 있으므로 복합 결정자를 적용할 수 있다.'),
 ('열을 빼며 최소키 확인', 'R(A,B,C), A→B, B→C가 주어진다. AB는 모든 속성을 결정한다.',
  'AB의 최소성을 검사한 결과는?', ['B를 빼도 A가 전체를 결정하므로 AB는 후보키가 아니다.','A와 B를 어떤 순서로 쓰든 반드시 후보키다.','AB가 슈퍼키이면 최소성도 자동 성립한다.','C만으로 A를 얻을 수 있어 C가 후보키다.'],0,
  'A에서 B를 얻고 B에서 C를 얻으므로 A만으로 전체를 결정한다. AB는 식별 가능하지만 B가 불필요하므로 최소 후보키가 아니다.'))
variants('update-anomaly',
 ('삭제 이상', 'CourseStudent(course_id,course_name,student_id)에 강좌 정보를 수강생 행에만 저장한다. 마지막 수강생 행을 지우면 강좌 이름도 사라진다.',
  '주된 이상 현상은?', ['삭제 이상','교착 상태','더티 리드','문자열 비교 오류'],0,
  '수강 취소라는 사실을 삭제하면서 독립적으로 보존해야 할 강좌 정보까지 사라진다. 관련 없는 사실이 같은 행에 결합되어 생기는 삭제 이상이다.'),
 ('삽입 이상', 'SupplierOrder(supplier_id,supplier_name,order_id)에서 order_id가 필수다. 새 공급업체가 아직 주문을 받지 않았다.',
  '공급업체만 먼저 저장하지 못하는 문제는?', ['삽입 이상','순위 함수의 동점','팬텀 리드','인덱스의 정렬 오류'],0,
  '공급업체 사실을 저장하려면 별도 사실인 주문도 있어야 하는 구조다. 공급업체와 주문 관계를 분리하면 주문이 없는 공급업체를 독립적으로 추가할 수 있다.'),
 ('중복 사실의 관리 위치', 'BranchEmployee(branch_id,branch_phone,employee_id)에서 같은 지점 전화번호를 직원마다 복사한다. 직원 수가 늘수록 변경 대상도 늘어난다.',
  '중복의 원인을 줄이는 설계는?', ['Branch(branch_id,branch_phone)를 분리해 전화번호를 지점당 한 번 저장한다.','직원마다 전화번호 복사본을 더 만든다.','지점 전화번호를 기본키로 하여 모든 직원을 한 행에 합친다.','직원 표시 순서를 바꾼다.'],0,
  '지점 전화번호는 지점에 대한 사실이다. 지점 식별자를 키로 하는 별도 표에서 한 번 저장하고 직원은 지점을 참조하면 직원 수와 변경 대상 수를 분리할 수 있다.'))
variants('many-many',
 ('관계 속성의 위치', 'Student와 Course를 Enrollment(student_id,course_id)로 연결한다. 성적은 학생 전체가 아니라 특정 수강에 대한 값이다.',
  'grade를 저장할 위치는?', ['Enrollment의 해당 학생·과목 연결 행','Student에 학생당 한 값','Course에 과목당 한 값','학생 이름 문자열의 뒤'],0,
  '성적은 학생과 과목의 조합에 종속된다. 학생은 과목마다 성적이 다르고 과목도 학생마다 성적이 다르므로 연결 행의 속성이다.'),
 ('다대다 연결의 중복 단위', 'ProjectMember에서 같은 직원이 같은 프로젝트에 한 번만 배정된다. 직원은 다른 프로젝트에도 배정될 수 있다.',
  '중복 배정을 방지하는 제약은?', ['UNIQUE(project_id,employee_id)','UNIQUE(employee_id)만','UNIQUE(project_id)만','직원 이름에만 CHECK'],0,
  '금지하려는 단위는 동일 프로젝트·직원 조합이다. 한쪽 열만 유일하게 만들면 정상적인 다대다 관계의 여러 연결을 막는다.'),
 ('연결 삭제와 대상 보존', 'UserRole(user_id,role_id)에서 한 사용자의 특정 역할 부여를 철회한다. 사용자와 역할 자체는 계속 존재해야 한다.',
  '기본적으로 삭제할 대상은?', ['해당 UserRole 연결 행','사용자 본체와 모든 역할','역할 본체와 모든 사용자','DB 전체 스키마'],0,
  '역할 부여의 철회는 두 대상 사이의 한 관계를 제거하는 것이다. 대상 자체를 삭제하면 다른 연결과 이력까지 영향을 줄 수 있어 요구 범위를 벗어난다.'))
variants('cardinality',
 ('일대일 강제', '직원 한 명에게 사물함은 최대 하나이며 사물함 하나도 직원 최대 한 명에게만 배정한다. Assignment에 직원번호와 사물함번호를 저장한다.',
  '양방향 최대 1을 강제하는 제약은?', ['employee_id와 locker_id 각각에 UNIQUE','두 열의 조합에만 UNIQUE','locker_id에 중복을 무제한 허용','행 표시 순서만 지정'],0,
  '복합 UNIQUE는 동일 쌍의 중복만 막는다. 직원이 서로 다른 사물함 두 개에 배정되거나 사물함이 두 직원에게 배정되는 것도 막으려면 각 열의 유일성이 필요하다.'),
 ('선택 참여와 필수 참여', '한 고객은 아직 주문이 없을 수 있으나 주문은 반드시 고객 한 명에게 속한다.',
  '자식 Order.customer_id의 선언으로 적절한 것은?', ['Customer를 참조하는 FOREIGN KEY와 NOT NULL','NULL 허용 외래키만으로 필수 참여 강제','고객 이름의 부분 문자열','주문의 모든 고객번호를 0으로 고정'],0,
  '주문 쪽의 필수 참여는 외래키로 부모 존재를, NOT NULL로 참조 값 입력을 함께 강제한다. 고객이 주문을 0개 가질 수 있다는 사실은 자식의 필수 참조와 모순되지 않는다.'),
 ('카디널리티 변경', '이전에는 한 신청에 담당자가 정확히 한 명이었지만 이제 여러 담당자가 참여하고 직원도 여러 신청을 담당한다.',
  '관계 구조를 바꾸는 적절한 방향은?', ['신청·직원 연결 표를 추가해 여러 배정을 표현한다.','신청의 담당자번호 한 칸에 한 명만 계속 저장한다.','직원 표를 삭제한다.','신청번호에 담당자 이름을 모두 이어 붙인다.'],0,
  '양쪽이 모두 여러 대상을 가질 수 있어 다대다 관계가 된다. 연결 표의 각 행으로 배정 하나를 표현해야 여러 담당자를 개별적으로 제약·조회할 수 있다.'))
variants('surrogate',
 ('대리키와 업무 중복', 'Company에 자동 증가 id 기본키를 두었다. 같은 사업자등록번호의 업체를 중복 등록하면 안 된다.',
  '추가로 필요한 제약은?', ['업무 규칙에 맞는 사업자등록번호의 UNIQUE·필수 제약','id가 있으니 등록번호는 무제한 중복 허용','등록번호를 화면에서 숨기는 것만','테이블 이름에 unique 접미사'],0,
  '대리키 id는 행마다 별도의 식별자를 제공할 뿐 동일 업체 사실의 중복 등록을 자동으로 막지 않는다. 업무상 유일해야 할 식별 값은 별도로 제약을 둔다.'),
 ('외부 식별자와 내부 관계', '회원의 외부 로그인명이 변경될 수 있다. 내부 member_id는 안정적으로 유지되며 결제 이력이 member_id를 참조한다.',
  '로그인명 변경 시 일반적인 이력 연결 결과는?', ['member_id가 유지되면 결제의 참조 키를 바꾸지 않고 연결을 유지할 수 있다.','모든 결제 이력을 반드시 삭제해야 한다.','로그인명 변경이 결제 금액도 자동 변경한다.','참조 키가 유지돼도 모든 외래키가 자동 위반된다.'],0,
  '안정적인 내부 식별자와 표시·로그인 값을 분리했으므로 참조 대상 키는 유지된다. 로그인명 고유성 등 필요한 업무 제약은 계속 별도로 검사한다.'),
 ('자동 증가값의 의미', 'Ticket.id는 DB가 생성하는 대리키이며 중간에 취소·삭제·실패가 있을 수 있다.',
  'id에 대한 안전한 가정은?', ['식별자로 사용할 수 있지만 반드시 빈틈없는 업무 접수 순번이라고 단정하면 안 된다.','값에 빈 번호가 있으면 항상 데이터가 유실됐다는 증거다.','큰 id는 모든 DB에서 커밋 시간이 반드시 더 늦다.','id 값 자체가 금액 합계를 나타낸다.'],0,
  '대리키의 생성 규칙과 트랜잭션·삭제 동작 때문에 번호에 빈틈이 있을 수 있다. 업무상 연속 번호나 확정 시각이 필요하면 그 요구를 별도로 설계해야 한다.'))
variants('atomicity',
 ('커밋 전 실패', '한 트랜잭션에서 주문을 추가하고 재고를 차감한다. 재고 차감에서 오류가 나 전체 트랜잭션을 ROLLBACK한다.',
  '원자성에 맞는 결과는?', ['그 트랜잭션에서 추가한 주문도 취소된다.','주문만 확정하고 재고는 그대로 둔다.','이미 실행한 INSERT는 ROLLBACK과 관계없이 항상 확정된다.','재고만 두 번 차감한다.'],0,
  '같은 트랜잭션의 일부만 확정되지 않아야 한다. 전체 ROLLBACK은 앞서 성공한 주문 추가를 포함해 해당 트랜잭션의 변경을 취소한다.'),
 ('외부 효과의 트랜잭션 범위', 'DB 트랜잭션 안에서 주문을 추가하고 외부 이메일 API로 알림을 보냈다. 그 뒤 DB 트랜잭션을 ROLLBACK했다.',
  'DB의 원자성만으로 보장할 수 없는 것은?', ['이미 외부로 전송한 이메일이 자동 취소되는 것','같은 DB 트랜잭션의 주문 INSERT 취소','미커밋 DB 변경을 확정하지 않는 것','DB 내 변경을 성공·취소 단위로 묶는 것'],0,
  '일반적인 DB 트랜잭션은 외부 이메일 서비스의 이미 수행한 효과까지 되돌리지 않는다. 외부 연동에는 커밋 후 발송·아웃박스·중복 처리 같은 별도 일관성 설계가 필요하다.'),
 ('성공 단위의 경계', 'A 작업을 COMMIT한 후 별도 새 트랜잭션에서 B 작업이 실패해 ROLLBACK했다.',
  '두 트랜잭션의 원자성만 고려한 결과는?', ['B의 취소가 이미 커밋한 A를 자동 취소하지 않는다.','B가 실패하면 과거 모든 COMMIT도 자동 취소된다.','A와 B가 같은 함수에서 호출되면 자동으로 한 트랜잭션이다.','ROLLBACK은 반드시 DB 전체를 초기화한다.'],0,
  '원자성은 정의된 트랜잭션 단위에 적용된다. A는 이전 트랜잭션에서 확정됐으므로 B 트랜잭션의 ROLLBACK 범위에 포함되지 않는다.'))
variants('durability',
 ('커밋과 미커밋 구분', 'T1의 변경은 COMMIT 성공 응답을 받았다. T2는 UPDATE했지만 아직 COMMIT하지 않은 채 DB가 정상적인 장애 복구를 한다.',
  '지속성의 직접적인 대상은?', ['T1의 확정 변경','T2의 미커밋 변경만','모든 실행 중인 SELECT의 화면 순서','클라이언트 임시 입력 폼'],0,
  '지속성은 성공적으로 커밋한 결과를 보존하는 성질이다. 미커밋 변경은 성공한 트랜잭션 결과로 확정되지 않았으며 정상 복구에서는 취소될 수 있다.'),
 ('지속성과 백업', 'DB가 로컬 디스크에 커밋 결과를 안전하게 저장한다. 이후 데이터센터 전체의 저장장치가 복구 불가능하게 손상되는 사고에 대비해야 한다.',
  '지속성 외에 추가로 필요한 운영 대책은?', ['별도 장애 영역의 백업과 실제 복구 계획','기본키 이름을 durable로 변경','ORDER BY를 모든 쿼리에서 제거','한 디스크의 모든 파일에 같은 별칭 지정'],0,
  '일상적 커밋 보존과 저장장치 자체가 소실되는 재해 대비는 별도 운영 범위다. 별도 장애 영역의 복구 가능한 백업과 절차를 준비해야 한다.'),
 ('성공 응답의 해석', '클라이언트가 COMMIT 요청을 보냈지만 연결이 끊겨 성공·실패 응답을 받지 못했다. DB 상태를 아직 확인하지 않았다.',
  '중복 처리 없이 대응하기 위한 안전한 판단은?', ['결과가 미확정이므로 거래 식별자 등으로 확정 상태를 확인하고 재시도를 설계한다.','응답이 없으니 반드시 모든 변경이 취소됐다.','응답이 없으니 반드시 커밋됐다고 단정한다.','확인 없이 같은 입금을 무제한 다시 실행한다.'],0,
  '요청 후 응답 유실은 실제 DB의 커밋 여부와 별개다. 이미 확정됐을 수 있어 업무 식별자·멱등성·상태 조회를 이용해 결과를 확인하고 안전한 재시도를 해야 한다.'))
variants('dirty-read',
 ('이미 커밋된 읽기', 'T1이 잔액을 150으로 UPDATE하고 COMMIT했다. 그 후 T2가 150을 읽었다.',
  '이 관찰을 더티 리드라고 볼 수 있는가?', ['아니다. 읽기 전에 변경이 커밋되어 있다.','변경값을 읽으면 항상 더티 리드다.','잔액이 숫자이면 무조건 더티 리드다.','COMMIT은 읽기와 아무 관련이 없다.'],0,
  '더티 리드는 다른 트랜잭션의 미커밋 변경을 읽는 현상이다. 이 사례는 커밋 이후 확정 데이터를 읽으므로 그 조건에 해당하지 않는다.'),
 ('취소한 값에 의존', 'T1이 상품 가격을 500으로 바꾸고 미커밋 상태다. T2는 500을 읽어 견적을 저장했다. T1은 ROLLBACK해 가격을 300으로 되돌렸다.',
  'T2 견적의 위험 원인은?', ['확정되지 않고 취소된 가격에 의존한 더티 리드','확정된 가격을 두 번 읽은 것만','새 상품 행이 추가된 팬텀','후보키의 최소성'],0,
  'T2는 T1이 커밋하지 않은 가격을 읽고 후속 계산에 사용했다. 그 가격은 취소되어 최종 DB 사실이 아니므로 미확정 값 의존이 생긴다.'),
 ('더티 리드 방지 조건', '미커밋 가격을 읽어 업무 결정을 내리면 안 되는 요구사항이다. 특정 제품 구현을 가정하지 않고 격리 성질을 선택한다.',
  '필요한 격리 성질은?', ['다른 트랜잭션의 미커밋 변경을 읽지 않도록 해야 한다.','어떤 트랜잭션도 자기 자신의 변경을 읽을 수 없어야 한다.','모든 읽기에 NULL만 반환해야 한다.','항상 외래키를 없애야 한다.'],0,
  '요구는 미커밋 타 트랜잭션 데이터의 노출을 막는 것이다. 격리 수준과 DB별 구현을 확인해 이 성질을 제공하는 설정·조회 방식을 선택한다.'))
variants('nonrepeatable',
 ('값 변화와 행 추가 구별', 'T1은 id=7의 상태를 대기로 읽었다. T2가 같은 id=7을 완료로 바꾸고 COMMIT했다. T1은 id=7을 완료로 다시 읽었다.',
  '직접 관찰된 현상은?', ['같은 행 값이 달라진 반복 불가능 읽기','새 id가 추가된 팬텀만','미커밋 값을 읽은 더티 리드','복합키 중복'],0,
  '행의 식별자 id=7은 같고 이미 커밋된 변경으로 열 값만 달라졌다. 미커밋 읽기나 새 조건 일치 행의 출현이 아닌 같은 행 재읽기 차이다.'),
 ('재읽기 값이 같은 경우', 'T1이 id=1 잔액을 읽고 다른 사용자 변경 없이 같은 행을 다시 읽어 같은 값을 얻었다.',
  '이 기록만으로 확인할 수 있는 것은?', ['반복 불가능 읽기는 이 관찰에서 발생하지 않았다.','시스템의 모든 트랜잭션에서 앞으로도 어떤 읽기 이상이 절대 없다는 것','DB가 반드시 SERIALIZABLE이라는 것','백업 복구가 반드시 성공한다는 것'],0,
  '두 번 같은 값을 봤다는 관찰은 이 사례에서 값 변화가 없었다는 뜻이다. 한 사례만으로 전체 격리 수준이나 미래의 모든 동시 실행을 증명하지 못한다.'),
 ('단일 스냅샷의 목적', '보고서 한 트랜잭션에서 같은 행을 여러 번 읽을 때 그 보고서의 일관된 값이 필요하다. 다른 세션의 갱신은 계속 허용한다.',
  '검토할 격리 동작은?', ['보고서가 일관된 스냅샷을 읽도록 하는 DB별 격리 기능','다른 세션의 미커밋 값을 매번 즉시 노출','id를 항상 무작위로 바꿔 재조회','동일 행을 다른 문자열 타입으로 복사'],0,
  '보고서의 관찰 범위를 일관된 스냅샷으로 만들면 중간 커밋으로 같은 행 값이 달라지는 문제를 줄일 수 있다. 정확한 보장과 쓰기 충돌 동작은 사용하는 DB의 격리 구현을 확인해야 한다.'))
variants('phantom',
 ('조건 집합의 삭제', 'T1이 조건에 맞는 id 1,2,3을 읽었다. T2가 그 조건의 id=2를 삭제해 COMMIT했다. T1 재조회는 id 1,3을 읽었다.',
  '범위 재조회 관점에서 확인된 변화는?', ['같은 조건 결과 집합의 구성원이 달라졌다.','WHERE 조건이 자동으로 삭제됐다.','항상 미커밋 삭제를 읽었다.','두 번째 결과에 새 id가 반드시 늘었다.'],0,
  '조건 일치 집합은 삽입뿐 아니라 삭제·조건 충족 여부의 변경으로도 달라질 수 있다. 여기서는 이미 커밋한 삭제로 조건 결과 집합의 구성원이 사라졌다.'),
 ('같은 건수의 다른 구성', '첫 조건 조회 결과 id는 1,2이다. 다른 트랜잭션이 id=2를 삭제하고 조건에 맞는 id=3을 삽입해 COMMIT했다. 두 번째 결과 id는 1,3이다.',
  'COUNT(*) 두 번이 같다는 사실의 한계는?', ['건수만 같아도 결과 집합의 행 구성은 달라질 수 있다.','건수가 같으면 모든 행과 열 값이 반드시 동일하다.','COUNT(*)가 같으면 커밋이 없었다는 증거다.','건수가 같으면 외래키 위반이다.'],0,
  '둘 다 두 행이지만 구성은 {1,2}에서 {1,3}으로 바뀌었다. 집계 건수 동일만으로 범위 읽기의 동일성을 판단할 수 없다.'),
 ('행 잠금과 범위의 구별', '이미 존재하는 고액신청 두 행만 잠갔다. 동시 삽입으로 해당 보고서의 조건 결과 집합이 달라지는 현상도 방지해야 한다는 요구가 생겼다.',
  '검토해야 할 추가 범위는?', ['DB의 범위·술어 보호 또는 적절한 직렬화 보장','기존 행 잠금만으로 모든 새로운 행 삽입이 항상 금지됨','두 행의 표시명을 바꾸는 것','인덱스 이름의 길이'],0,
  '존재 행 보호와 조건을 만족할 새 행의 출현 보호는 다르다. 사용하는 DB의 격리·범위 또는 술어 보호 동작을 검토해 결과 집합 일관성을 설계한다.'))
variants('lost-update',
 ('원자적 증가', 'counter=10이다. 두 트랜잭션이 DB에서 직렬화되는 UPDATE counters SET counter=counter+1을 각각 한 번 성공적으로 실행해 COMMIT했다.',
  '다른 변경이 없을 때 최종 값은?', ['12','11','10','20'],0,
  '각 UPDATE는 저장된 현재 값에 1을 더하는 연산으로 직렬화된다. 첫 번째가 11을 만들고 두 번째가 12를 만들어 이전 값 계산 결과를 덮어쓰는 패턴과 다르다.'),
 ('조건부 잔액 차감', '잔액은 100이고 80을 차감하려 한다. UPDATE accounts SET balance=balance-80 WHERE id=1 AND balance>=80으로 처리하고 영향 행 수를 확인한다.',
  '조건의 목적은?', ['갱신 시점에 잔액 조건을 함께 검사해 부족할 때 변경하지 않게 한다.','모든 트랜잭션에서 부족 잔액도 강제로 음수로 만든다.','읽기 전용 문장이 되어 아무 값도 바뀌지 않는다.','ORDER BY 없이 출금 순서를 화면에 보장한다.'],0,
  '조건과 증감 연산을 같은 UPDATE에 두면 해당 DB의 쓰기 동시성 처리 아래 갱신 시의 조건을 검사한다. 영향 행 수 0이면 잔액 부족·대상 부재 등 실패 사유를 업무적으로 처리한다.'),
 ('읽기 계산 저장의 충돌', 'T1과 T2는 조회수 20을 각각 읽었다. T1은 21을 저장하고 T2도 자신이 계산한 21을 저장했다. 둘 다 성공했다.',
  '최종 21이 두 번 증가 기대값 22와 다른 이유는?', ['두 번째 저장이 첫 번째 증가를 이전 값 기반 결과로 덮어썼다.','SQL COUNT가 항상 1을 빼기 때문이다.','21이 기본키라 한 번 더 증가할 수 없다.','NULL이므로 산술식이 실행되지 않았다.'],0,
  '두 트랜잭션의 계산이 모두 같은 이전 값 20에 기반했다. 증가 자체를 DB 안의 원자적 연산으로 하지 않고 계산 결과 21을 두 번 대입하면 한 증가가 분실된다.'))
variants('deadlock',
 ('단순 대기와 교착 구별', 'T1은 A 잠금을 보유하고 작업 중이다. T2는 A를 기다린다. T1은 T2가 보유한 어떤 자원도 기다리지 않는다.',
  '이 정보만으로 교착이라고 할 수 있는가?', ['아니다. 일방향 잠금 대기이며 순환 대기는 제시되지 않았다.','잠금을 기다리는 세션이 하나라도 있으면 항상 교착이다.','작업 중인 T1이 반드시 취소된다.','외래키가 없으면 잠금 대기가 불가능하다.'],0,
  '교착에는 서로 진행을 막는 순환 대기가 필요하다. T1이 진행해 A를 해제할 수 있는 일방향 대기와 교착은 구분해야 한다.'),
 ('잠금 순서 통일', '두 계정 A,B를 갱신하는 모든 트랜잭션이 항상 작은 계정번호부터 잠근다.',
  '이 규칙이 줄이는 위험은?', ['동일 자원을 반대 순서로 잡으며 생기는 순환 대기','모든 논리적 업무 오류를 완전히 제거','모든 SELECT에서 인덱스 비용을 0으로 만듦','모든 트랜잭션을 미커밋 읽기로 전환'],0,
  '자원에 공통 순서를 두면 A를 가진 채 B를 기다리는 동안 반대 순서의 B 보유·A 대기를 만드는 패턴을 줄인다. 다른 원인의 교착이나 업무 오류까지 모두 없애는 보장은 아니다.'),
 ('교착으로 취소된 거래', 'DB가 교착을 감지해 송금 트랜잭션 하나를 취소했다. 송금은 출금과 입금을 한 트랜잭션에 묶는다.',
  '애플리케이션의 적절한 처리 단위는?', ['실패 결과를 확인하고 전체 송금을 안전하게 재시도하는 정책','입금 부분만 확인 없이 반복 실행','오류를 무시하고 성공 응답','취소된 트랜잭션의 상태를 그대로 성공으로 저장'],0,
  '교착 취소는 거래 전체의 실패로 처리해야 한다. 트랜잭션 경계·재시도 횟수·멱등성을 고려한 전체 송금 재시도로 부분 중복 반영을 피한다.'))
variants('optimistic',
 ('버전 조건의 영향 행 수', '사용자는 version=4를 읽었다. 다른 변경이 먼저 version=5로 커밋했다. 현재 UPDATE ... WHERE id=1 AND version=4의 영향 행 수는 0이다.',
  '이 결과에서 필요한 처리는?', ['충돌로 보고 최신 데이터를 읽어 재검토한다.','변경이 성공했으므로 성공 응답한다.','WHERE의 version을 제거해 무조건 덮어쓴다.','기존 version=4로 되돌려 모두 같은 값으로 만든다.'],0,
  '현재 버전이 읽었던 버전과 달라 조건을 통과하지 못했다. 0행 갱신은 성공 저장이 아니며 사용자의 수정과 새 변경을 어떻게 조정할지 정해야 한다.'),
 ('원자적인 버전 비교와 증가', '읽은 버전과 현재 버전을 확인하는 SELECT와 실제 UPDATE를 별도 단계로 분리하면 사이에 다른 변경이 들어올 수 있다.',
  '낙관적 제어의 핵심은?', ['버전 조건과 값·버전 갱신을 한 조건부 UPDATE에서 원자적으로 수행한다.','버전 SELECT만 하고 UPDATE에서는 조건을 빼도 항상 안전하다.','버전 값을 저장하지 않고 화면에만 표시한다.','동시 요청을 전부 같은 이전 버전으로 강제한다.'],0,
  '검사와 사용 사이의 경합을 막으려면 UPDATE 자체가 읽은 버전 조건을 포함해야 한다. 성공할 때 새 값을 쓰고 버전을 함께 증가시키며 영향 행 수를 확인한다.'),
 ('재시도 시 재계산', '버전 충돌 후 최신 잔액이 달라졌다. 이전 잔액으로 계산한 저장값을 그대로 다시 제출하려 한다.',
  '재시도에서 필요한 단계는?', ['최신 상태를 다시 읽고 업무 조건·계산을 재검토한다.','충돌이 나도 이전 계산값을 무제한 덮어쓴다.','버전 조건을 제거하면 언제나 업무 결과가 보존된다.','최신 상태는 표시만 하고 계산에는 쓰지 않는다.'],0,
  '충돌은 읽었던 전제가 바뀌었다는 뜻이다. 최신 상태에서 유효한 변경인지 다시 판단하고 계산해야 하며, 단순히 버전만 바꿔 이전 결과를 저장하면 다른 변경을 훼손할 수 있다.'))
variants('composite-index',
 ('인덱스의 쓰기 비용', '조회 개선을 위해 테이블에 보조 인덱스 5개를 추가했다. INSERT와 인덱스 열 UPDATE도 자주 발생한다.',
  '함께 고려할 비용은?', ['추가 저장 공간과 쓰기 때 인덱스 유지 비용','인덱스가 늘면 모든 INSERT가 반드시 빨라짐','인덱스의 저장 공간은 항상 0','인덱스가 있으면 DB는 절대 통계를 쓰지 않음'],0,
  '보조 인덱스는 별도 검색 구조를 저장하고 관련 데이터 변경 때 유지해야 한다. 조회 이익과 공간·쓰기 비용을 함께 측정해 불필요한 인덱스를 줄인다.'),
 ('인덱스 선택과 플래너', 'status 열에 인덱스가 있지만 쿼리 조건이 전체 행의 대부분을 선택한다. 실행 계획은 테이블 스캔이다.',
  '이 선택에 대한 적절한 판단은?', ['대량 행 조회에서는 스캔이 더 저렴할 수 있어 실제 비용·시간을 확인한다.','인덱스가 있으니 어떤 스캔도 무조건 DB 오류다.','인덱스는 생성 즉시 모든 쿼리에 강제 적용된다.','status 값이 반복되면 SQL 조회 자체가 불가능하다.'],0,
  '플래너는 데이터 분포와 접근 비용을 비교한다. 대부분의 행을 읽어야 하면 인덱스 탐색 후 본문 접근보다 순차적 스캔이 유리할 수 있다.'),
 ('결과 정렬의 보장', 'created_at 인덱스가 있고 쿼리는 SELECT id FROM tickets만 실행하며 ORDER BY가 없다.',
  '결과 순서에 대한 안전한 설명은?', ['업무상 필요한 순서는 ORDER BY로 명시해야 한다.','인덱스가 있으니 created_at 오름차순이 항상 보장된다.','기본키 값은 항상 삽입 순서와 같다.','표의 마지막 행이 항상 먼저 표시된다.'],0,
  'ORDER BY 없이 결과 행 순서는 보장된 계약이 아니다. 접근 경로나 계획이 바뀔 수 있으므로 필요한 정렬 열과 동점 기준을 명시한다.'))
variants('sargable',
 ('반개구간의 경계', '2026-10-03 하루의 timestamp 값을 조회하려 한다. 다음날 00:00의 행은 10월4일 데이터다.',
  '정확한 상한 조건은?', ["timestamp < '2026-10-04 00:00:00'","timestamp <= '2026-10-04 00:00:00'","timestamp = '2026-10-03 00:00:00'","timestamp > '2026-10-04 00:00:00'"],0,
  '하루 범위를 시작 시각 이상, 다음날 시작 시각 미만으로 잡으면 정밀도가 다른 끝 시각을 임의로 만들지 않고 다음날 행도 제외할 수 있다.'),
 ('실행 계획으로 확인', '조건식에서 인덱스 열을 함수로 감쌌다. 사용하는 DB에는 함수 인덱스나 쿼리 변환 기능이 있을 수도 있다.',
  '인덱스 활용 여부를 확인하는 방법은?', ['해당 DB의 실제 실행 계획과 쿼리 시간을 확인한다.','함수를 썼으니 모든 DB에서 항상 같은 접근이 보장된다고 단정한다.','SQL 문장 글자 수만 센다.','인덱스 이름만 보고 결과를 결정한다.'],0,
  '함수 조건의 인덱스 활용은 DB 기능·인덱스 정의·변환에 따라 다르다. 정확한 계획과 측정값을 확인해야 하며 일반 규칙을 절대적인 제품 동작으로 단정하지 않는다.'),
 ('경계 값과 시간 정밀도', '하루의 마지막 시각을 23:59:59로 잡으려 한다. 열은 소수 초를 저장해 23:59:59.500도 존재한다.',
  '권장되는 범위 표현의 이유는?', ['다음날 시작 미만으로 쓰면 소수 초를 포함한 하루 끝값을 빠짐없이 포함한다.','23:59:59보다 큰 값은 모두 다음날이다.','소수 초가 있으면 하루 범위를 SQL로 표현할 수 없다.','끝값을 항상 23:59:59로 고정해야 정확하다.'],0,
  '하루 안의 23:59:59.500은 23:59:59보다 커서 단순 끝값 비교에 빠질 수 있다. 다음날 00:00 미만이라는 상한은 시간 정밀도와 무관하게 하루 경계를 표현한다.'))
variants('covering',
 ('SELECT 열 증가의 영향', '조회는 customer_id와 grade만 필요해 두 열을 가진 인덱스로 커버 가능했다. 이후 SELECT에 인덱스에 없는 address도 추가했다.',
  '커버 여부에 대한 변화는?', ['그 인덱스만으로 address까지 얻을 수 없어 같은 커버 조건이 더는 성립하지 않는다.','어떤 SELECT 열을 더해도 기존 인덱스가 모든 값을 자동 포함한다.','address가 문자열이면 인덱스에 없어도 저장값이 자동 생성된다.','SELECT 열은 인덱스 활용과 아무 관련이 없다.'],0,
  '커버 여부는 현재 쿼리가 요구하는 열과 인덱스에 저장된 값에 달려 있다. 새로 필요한 address가 없으면 추가 본문 접근 등의 계획을 검토해야 한다.'),
 ('커버링의 비용 균형', 'SELECT에 쓰이는 모든 열을 큰 인덱스로 복사하자는 제안이다. 자주 바뀌는 긴 문자열도 많다.',
  '검토해야 할 trade-off는?', ['본문 접근 감소 가능성과 인덱스 크기·쓰기 비용 증가를 함께 비교한다.','인덱스 열은 많이 넣을수록 모든 비용이 반드시 줄어든다.','문자열 길이는 인덱스 공간에 아무 영향이 없다.','조회에 필요 없는 열도 무조건 모두 포함해야 한다.'],0,
  '커버 범위를 넓히면 일부 조회 접근을 줄일 수 있지만 인덱스 크기와 유지 비용이 늘 수 있다. 실제 워크로드에서 필요한 열과 비용을 측정해야 한다.'),
 ('계획의 확인 범위', '인덱스 정의에 조회 열이 모두 있지만 실행 계획과 실제 테이블 접근을 아직 확인하지 않았다.',
  '안전한 결론은?', ['커버 가능성을 검토할 수 있으며 실제 접근은 DB 계획과 상태로 확인해야 한다.','본문 접근은 모든 DB에서 영원히 절대 발생하지 않는다.','쿼리 플래너가 그 인덱스를 무조건 사용한다.','존재하는 인덱스는 SQL 결과 행을 항상 두 배로 만든다.'],0,
  '열 포함만으로 옵티마이저의 선택이나 가시성 확인 같은 내부 동작을 단정할 수 없다. 커버 가능한 구조와 실제 선택·접근은 구분해 확인한다.'))
variants('least-privilege',
 ('민감 열 제외 뷰', '보고서에는 지점별 건수만 필요하고 주민번호 같은 개인 식별 원문은 필요 없다.',
  '접근 설계로 적절한 것은?', ['필요한 집계만 제공하는 뷰와 그 뷰의 조회 권한을 부여한다.','원문 전체 테이블에 관리자 권한을 준다.','화면에 안 보이면 DB 조회 권한은 구분하지 않는다.','모든 원문 값을 로그에 남겨 보고서를 만든다.'],0,
  '필요한 정보 범위를 좁힌 뷰와 권한을 사용하면 기능 수행에 불필요한 원문 접근을 줄일 수 있다. 화면 노출과 DB 권한은 별도 통제다.'),
 ('역할 분리', '웹 조회 서비스와 스키마 배포 도구가 같은 관리자 계정을 공유하고 있다.',
  '권한 분리 개선은?', ['조회 서비스와 배포 도구에 별도 계정·역할을 두고 필요한 권한만 각각 부여한다.','웹 서비스가 매 요청마다 모든 사용자의 비밀번호를 출력한다.','계정 이름만 두 개로 바꾸고 같은 전권을 계속 공유한다.','비밀번호를 소스에 쓰면 최소 권한이 달성된다.'],0,
  '실행 목적에 따라 필요한 권한이 다르다. 조회 런타임이 스키마 변경·관리 권한을 가질 필요 없이 별도 역할로 범위를 분리할 수 있다.'),
 ('권한 회수 검증', '운영 계정의 DELETE 권한을 회수했다고 변경 기록에 적었다. 실제 권한과 기능 영향은 확인하지 않았다.',
  '변경 확인에 필요한 단계는?', ['유효 권한과 필요한 기능 동작을 검증한다.','기록에 쓰면 실제 권한은 자동 회수된다.','계정에 administrator라는 이름을 더한다.','권한 검증 대신 테이블을 삭제한다.'],0,
  '부여된 역할이나 다른 권한 경로 때문에 유효 권한은 단순 변경 문구와 다를 수 있다. 실제 권한이 의도대로 적용됐는지와 필요한 조회가 계속 동작하는지 확인한다.'))
variants('parameterized',
 ('동적 정렬 식별자', '사용자가 sort 필드로 정렬 열 이름을 선택한다. 값 매개변수는 데이터 값용이며 열 이름 자리를 대신하지 않는다.',
  '안전한 동적 정렬 구성은?', ['허용된 열 이름 목록에서 매핑하고 값 조건은 별도 바인딩한다.','사용자 문자열을 ORDER BY 뒤에 그대로 붙인다.','ORDER BY ?에 문자열을 바인딩하면 항상 그 이름의 열로 정렬된다.','작은따옴표를 추가하면 임의 식별자가 모두 안전하다.'],0,
  '식별자는 값 바인딩과 다른 문법 범주다. 사전에 허용한 열 이름으로 매핑한 SQL 조각만 사용하고 검색값 등 데이터는 매개변수로 전달한다.'),
 ('플레이스홀더의 따옴표', 'SQLite 드라이버에서 위치 매개변수 ?를 사용한다. WHERE name = \'?\'라고 쓰고 값을 바인딩하려 한다.',
  '올바른 수정은?', ['WHERE name = ?로 쓰고 입력값을 바인딩 인수로 전달한다.','따옴표 안의 ?가 그대로 값 플레이스홀더이므로 수정이 필요 없다.','입력값을 SQL 문자열에 직접 붙인다.','매개변수에 SQL 전체를 실행 명령으로 전달한다.'],0,
  '따옴표 안의 물음표는 문자열 리터럴이다. 플레이스홀더는 SQL 문법에서 따옴표 없이 ?로 두고 드라이버에 별도 값 인수를 전달해야 한다.'),
 ('입력 검증과 바인딩', '검색어 길이를 제한하고 허용 문자 검사를 추가했다. 개발자는 이제 SQL 문자열 결합도 안전하다고 주장한다.',
  '적절한 판단은?', ['입력 검증과 별도로 값 매개변수 바인딩을 유지한다.','입력 검증 하나가 모든 SQL 문맥의 안전성을 자동 보장한다.','검증을 통과한 값은 반드시 SQL 명령으로 실행해야 한다.','바인딩하면 업무상 입력 검증은 영원히 필요 없다.'],0,
  '입력 검증은 업무상 형식·범위를 검사하고 바인딩은 값과 SQL 문법을 분리한다. 역할이 달라 둘 중 하나가 다른 모든 요구를 대체한다고 볼 수 없다.'))
variants('backup-recovery',
 ('복구 시간 목표', '운영 목표는 장애 후 30분 이내 서비스 복구다. 백업 복원과 검증을 실제 시험했더니 90분이 걸렸다.',
  '검증 결과의 의미는?', ['데이터 복원이 성공해도 복구 시간 목표를 만족하지 못했다.','파일을 복원했으니 30분 목표도 자동 달성됐다.','90분은 데이터 유실량이므로 시간 목표와 무관하다.','백업 파일 이름을 바꾸면 복구 시간이 30분이 된다.'],0,
  '복원 성공 여부와 목표 시간 내 복구 여부는 따로 검증한다. 90분이 걸렸으므로 30분 목표에 맞게 절차·용량·복구 방식을 개선해야 한다.'),
 ('격리 환경에서 복원 시험', '복구 검증을 위해 운영 DB에 백업을 덮어써 테스트하자는 제안이다. 운영 데이터 변경은 승인되지 않았다.',
  '적절한 시험 환경은?', ['운영과 분리된 환경에 복원해 내용·제약·시간을 확인한다.','운영 원본에 무조건 덮어쓴다.','운영 데이터부터 삭제하고 결과만 확인한다.','파일 확장자를 바꾸기만 한다.'],0,
  '격리 환경의 복구 시험은 운영 데이터를 훼손하지 않고 실제 복원 가능성을 확인한다. 접근 권한과 민감 데이터 보호도 시험 환경의 범위에 맞게 적용한다.'),
 ('복제와 이력 백업', '실시간 복제본이 있다. 운영에서 실수로 행을 삭제하면 그 삭제도 복제본에 즉시 전파된다.',
  '복제만으로 부족한 복구 요구는?', ['실수 삭제 이전 시점으로 돌아갈 수 있는 이력 백업·복구 수단','현재 삭제 상태를 똑같이 유지하는 것','읽기 부하를 여러 서버로 나누는 것','복제 연결의 현재 상태를 확인하는 것'],0,
  '복제는 현재 상태를 따라가므로 잘못된 변경도 전파할 수 있다. 과거 시점 복구에는 적절한 백업·변경 로그 보존 등 별도의 이력 복구 수단이 필요하다.'))
variants('relational-division',
 ('모두 충족과 하나 충족', '필수 기술은 SQL,Python이다. 민서는 SQL만, 지후는 SQL과 Python을 보유한다.',
  '필수 기술을 모두 가진 대상은?', ['지후만','민서만','민서와 지후 모두','아무도 없음'],0,
  '모두 충족은 필수 집합의 각 값과 연결되어야 한다. SQL 하나만 가진 민서는 Python 연결이 없어 제외되고 두 기술을 가진 지후만 통과한다.'),
 ('추가 능력의 허용', '필수 자격은 X,Y이다. 한 직원은 X,Y,Z를 모두 보유한다. 필수 자격 외 추가 자격은 제한하지 않는다.',
  '이 직원의 적격 여부는?', ['필수 X,Y를 모두 보유하므로 적격이다.','추가 Z가 있으므로 무조건 부적격이다.','보유 개수가 정확히 2일 때만 나눗셈을 통과한다.','X와 Y 중 하나만 있어도 동일하게 적격이다.'],0,
  '모든 필수 값과 연결되어야 한다는 요구는 연결이 정확히 필수 집합과 같아야 한다는 요구가 아니다. 추가 자격을 금지하지 않으면 X,Y,Z 보유도 조건을 만족한다.'),
 ('누락이 없음으로 표현', '어떤 직원이 모든 필수 과목을 이수했는지를 SQL로 판단한다. 직원별로 필수 과목 중 이수 기록이 없는 과목을 찾을 수 있다.',
  '모든 필수 과목 이수를 표현하는 논리는?', ['이수하지 않은 필수 과목이 존재하지 않는다.','이수한 과목이 하나라도 존재한다.','전체 이수 행을 무조건 삭제한다.','필수 과목 수와 무관하게 이름순 정렬한다.'],0,
  '모든 값에 대해 조건이 성립한다는 것은 조건을 만족하지 않는 필수 값이 존재하지 않는다는 뜻이다. SQL에서는 이 누락 검사에 NOT EXISTS를 적용하는 구조로 표현할 수 있다.'))


def generate_concepts():
    assert len(CONCEPTS)==30, len(CONCEPTS)
    assert set(VARIANTS)=={c['key'] for c in CONCEPTS}
    for spec in CONCEPTS:
        for seed,(entity,a,b,rules) in enumerate(spec['scenarios']):
            fmt = dict(entity=entity,a=a,b=b)
            if seed:
                title,rules,prompt,choices,ci,exp = VARIANTS[spec['key']][seed-1]
            else:
                title = spec['topic']+' · '+entity
                prompt = korean_format(spec['prompt'],fmt)
                choices = [korean_format(s,fmt) for s in spec['options']]
                ci = spec['correct']
                exp = korean_format(spec['explain'],fmt)
            correct = choices[ci]
            context = '가상의 데이터베이스 사례.' if seed else f'가상의 {entity} 사례.'
            add({'category':spec['category'], 'learningTopic':spec['topic'],
                 'templateId':'db-concept-'+spec['key'], 'title':title,
                 'prompt':'자체 제작 연습문제 · '+prompt,
                 'passage':f'{context}\n{rules}\n명시된 업무 규칙과 함수 종속만 고려한다.',
                 'difficulty':spec['difficulty']}, correct, choices, exp,
                ['지문에서 식별자·종속·변경 순서 또는 권한 요구사항을 확인한다.', exp])


def validate():
    assert len(QUESTIONS)==380 and len(ANSWERS)==380
    assert len({q['id'] for q in QUESTIONS})==380
    templates = collections.Counter(q['templateId'] for q in QUESTIONS)
    assert len(templates)==95 and max(templates.values())==4
    normalized = [json.dumps([q['prompt'],q.get('passage'),q.get('code'),q['options']],ensure_ascii=False) for q in QUESTIONS]
    assert len(set(normalized))==380
    for q in QUESTIONS:
        assert q['track']=='db' and q['kind']=='original' and q['sourceId']=='original'
        assert len(q['options'])==4 and len(set(q['options']))==4
        assert q['learningTopic'] and q['templateId'] and q['passage']
        a = ANSWERS[q['id']]
        assert a['explanation'] and a['detailedSteps'] and 0<=a['correctIndex']<4
    # Independent fresh connections re-run every final stored executable question.
    for entry in AUDIT:
        con = database(entry['seed'])
        if entry['mutation']:
            con.executescript(entry['mutation'])
        rows = con.execute(entry['query']).fetchall()
        con.close()
        expected = result(rows)
        q = next(q for q in QUESTIONS if q['id']==entry['id'])
        assert q['options'].count(expected)==1
        assert q['options'][ANSWERS[q['id']]['correctIndex']]==expected
    return {'newQuestions':380,'sqlExecutionVerified':len(AUDIT),'conceptReviewed':120,
            'questionStructures':len(templates),'maxVariantsPerStructure':max(templates.values()),
            'learningTopics':len({q['learningTopic'] for q in QUESTIONS}),
            'sqliteVersion':sqlite3.sqlite_version, 'duplicateQuestions':0,
            'categories':dict(collections.Counter(q['category'] for q in QUESTIONS)),
            'documentation':DOCS}


def main():
    generate_sql()
    generate_concepts()
    report = validate()
    outputs = {'database-questions.json':QUESTIONS, 'database-answers.json':ANSWERS,
               'database-verification.json':{'summary':report,'sqlChecks':AUDIT}}
    if '--check' in sys.argv:
        for name, value in outputs.items():
            existing = json.loads((DEST/name).read_text(encoding='utf-8-sig'))
            if name=='database-verification.json':
                existing['summary']['sqliteVersion']=value['summary']['sqliteVersion']
            assert existing==value, f'{name} differs from reproducible generator'
    else:
        DEST.mkdir(parents=True,exist_ok=True)
        for name,value in outputs.items():
            (DEST/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()

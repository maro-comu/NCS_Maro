"""Independent runtime and simulation checks for the original IT expansion."""
import ipaddress
import itertools
import json
import os
import re
import shutil
import subprocess
import sys
from collections import Counter
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUESTIONS = json.loads((ROOT / "data/expansion/programming-questions.json").read_text(encoding="utf-8-sig"))
ANSWERS = json.loads((ROOT / "data/expansion/programming-answers.json").read_text(encoding="utf-8-sig"))
NODE = os.environ.get("STUDY_NODE") or shutil.which("node")


def number(pattern, text):
    match = re.search(pattern, text)
    assert match, (pattern, text)
    return int(match.group(1))


def calculation(q):
    """Read the student-visible parameters rather than generation variables."""
    p, t = q["prompt"], q["templateId"]
    if t == "algo-triangle-loop":
        n = number(r"n=(\d+)", p)
        return sum(1 for i in range(1, n + 1) for _ in range(i)), "회"
    if t == "algo-doubling-loop":
        bound = number(r"x<(\d+)", p)
        value, count = 1, 0
        while value < bound:
            count += 1
            value *= 2
        return count, "회"
    if t == "algo-merge-total":
        size = number(r"길이 (\d+) 배열", p)
        block, count = 2, 0
        while block <= size:
            for start in range(0, size, block):
                for _ in range(start, min(start + block, size)):
                    count += 1
            block *= 2
        return count, "회"
    if t == "ds-complete-binary":
        depth = number(r"잎 깊이가 (\d+)", p)
        level = [0]
        count = len(level)
        for _ in range(depth):
            level = [child for node in level for child in (node * 2 + 1, node * 2 + 2)]
            count += len(level)
        return count, "개"
    if t == "algo-bubble-one-pass":
        values = json.loads(re.search(r"\[[\d, ]+\]", p).group(0))
        for i in range(len(values) - 1):
            if values[i] > values[i + 1]:
                values[i], values[i + 1] = values[i + 1], values[i]
        return json.dumps(values, separators=(",", ":")), ""
    if t in ("os-fcfs-wait", "os-sjf-wait"):
        if t == "os-fcfs-wait":
            values = list(map(int, re.search(r"각각 (\d+),(\d+),(\d+)ms", p).groups()))
        else:
            values = sorted(map(int, re.findall(r"P\d=(\d+)ms", p)))
        now, total_wait = 0, 0
        for burst in values:
            total_wait += now
            now += burst
        return total_wait, "ms"
    if t == "os-round-robin-first":
        quantum = number(r"타임퀀텀 (\d+)ms", p)
        queue = ["P1", "P2", "P3"]
        now = 0
        while queue:
            task = queue.pop(0)
            if task == "P3":
                return now, "ms"
            now += quantum
    if t == "os-page-offset":
        page_size = number(r"페이지 크기가 (\d+)바이트", p)
        address = number(r"논리주소 (\d+)", p)
        return divmod(address, page_size)[1], "바이트"
    if t == "os-page-count":
        space = number(r"주소 공간은 (\d+)바이트", p)
        page_size = number(r"페이지 크기는 (\d+)바이트", p)
        covered, pages = 0, 0
        while covered < space:
            covered += page_size
            pages += 1
        return pages, "페이지"
    if t == "os-amdahl":
        denominator = number(r"1/(\d+)은 직렬", p)
        limit = Fraction(1, denominator)
        return Fraction(1, 1) / limit, "배"
    if t == "os-semaphore-count":
        permits = number(r"초깃값 (\d+)", p)
        for _ in range(number(r"acquire (\d+)회", p)):
            permits -= 1
            assert permits >= 0
        for _ in range(number(r"release (\d+)회", p)):
            permits += 1
        return permits, "개"
    if t == "os-disk-fcfs":
        head = number(r"실린더 (\d+)에", p)
        requests = list(map(int, re.search(r"FCFS로 (\d+), (\d+), (\d+) 순서", p).groups()))
        travelled = 0
        for target in requests:
            while head != target:
                head += 1 if target > head else -1
                travelled += 1
        return travelled, "실린더"
    if t == "net-transfer-time":
        megabytes = number(r"크기 (\d+)MB", p)
        megabits_per_sec = number(r"(\d+)Mb/s", p)
        return Fraction(megabytes * 10**6 * 8, megabits_per_sec * 10**6), "초"
    if t in ("net-ipv4-hosts", "net-cidr-block"):
        prefix = number(r"IPv4 /(\d+)", p)
        network = ipaddress.ip_network(f"10.0.0.0/{prefix}")
        if t == "net-ipv4-hosts":
            return len(list(network.hosts())), "개"
        return network.num_addresses, "개"
    if t == "net-stop-wait":
        send = number(r"전송시간은 (\d+)ms", p)
        delay = number(r"전파 지연은 (\d+)ms", p)
        return Fraction(send * 100, send + delay), "%"
    if t == "net-udp-payload":
        total = number(r"전체 IP 패킷이 (\d+)바이트", p)
        ip = number(r"IP 헤더 (\d+)바이트", p)
        udp = number(r"UDP 헤더 (\d+)바이트", p)
        payload = bytearray(total)
        return len(payload[ip + udp :]), "바이트"
    if t == "net-tcp-ack":
        sequence = number(r"순서 번호가 (\d+)", p)
        length = number(r"데이터 길이는 (\d+)바이트", p)
        for _ in range(length):
            sequence += 1
        return sequence, ""
    if t == "ds-hash-linear":
        size = number(r"크기 (\d+)인 해시", p)
        old = list(map(int, re.search(r"(\d+), (\d+)을 이미 삽입", p).groups()))
        new = number(r"(\d+)가 들어갈", p)
        table = [None] * size
        inserted_at = None
        for key in old + [new]:
            slot = key % size
            while table[slot] is not None:
                slot = (slot + 1) % size
            table[slot] = key
            inserted_at = slot
        return inserted_at, ""
    if t == "ds-matrix-storage":
        rows, cols = map(int, re.search(r"(\d+)행 (\d+)열", p).groups())
        item_size = number(r"한 원소 (\d+)바이트", p)
        start = number(r"시작 주소 (\d+)", p)
        row, col = map(int, re.search(r"\[(\d+)\]\[(\d+)\]", p).groups())
        assert 0 <= row < rows and 0 <= col < cols
        cursor = start
        for r in range(rows):
            for c in range(cols):
                if (r, c) == (row, col):
                    return cursor, ""
                cursor += item_size
    if t == "algo-linear-comparisons":
        length = number(r"길이 (\d+)인 배열", p)
        return sum(1 for _ in range(length)), "회"
    if t == "algo-complete-graph":
        vertices = number(r"정점 (\d+)개", p)
        return len(list(itertools.combinations(range(vertices), 2))), "개"
    if t == "ds-stack-depth":
        text = re.search(r"문자열 '([^']+)'", p).group(1)
        stack, high = [], 0
        for char in text:
            if char == "(":
                stack.append(char)
            else:
                assert stack
                stack.pop()
            high = max(high, len(stack))
        assert not stack
        return high, "개"
    raise AssertionError(("unverified calculation template", t))


executed = simulated = 0
assert len(QUESTIONS) == len(ANSWERS) == 380
assert set(ANSWERS) == {q["id"] for q in QUESTIONS}
for q in QUESTIONS:
    answer = ANSWERS[q["id"]]
    expected = q["options"][answer["correctIndex"]]
    assert len(set(q["options"])) == 4
    assert q["kind"] == "original" and q["sourceId"] == "original"
    assert q["learningTopic"] and q["templateId"]
    if "code" in q:
        command = [sys.executable, "-c", q["code"]] if q["language"] == "Python" else [NODE, "-e", q["code"]]
        run = subprocess.run(command, text=True, capture_output=True, timeout=6, check=True)
        actual = run.stdout.strip().replace("\r\n", "\n").replace("\n", " / ")
        assert actual == expected, (q["id"], repr(actual), repr(expected))
        assert answer["verification"] == "computed-verified"
        executed += 1
    elif not q["templateId"].startswith("scenario-"):
        value, unit = calculation(q)
        actual = f"{float(value):g}{unit}" if isinstance(value, Fraction) else f"{value}{unit}"
        assert actual == expected, (q["id"], actual, expected, q["prompt"])
        assert answer["verification"] == "computed-verified"
        simulated += 1
assert executed == simulated == 120
families = Counter(q["templateId"] for q in QUESTIONS)
distribution = [sum(a["correctIndex"] == i for a in ANSWERS.values()) for i in range(4)]
assert max(families.values()) <= 5
assert distribution == [95, 95, 95, 95]
print(json.dumps({"questions": 380, "codeRuntimeChecks": executed, "independentCalculationChecks": simulated, "scenarioReviewItems": 140, "templates": len(families), "maxVariants": max(families.values()), "correctIndexDistribution": distribution}))

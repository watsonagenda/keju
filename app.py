#!/usr/bin/env python3
"""
科举 — Agent 优先的智能备考系统
面向各类应试考试的智能备考系统
v3 — 信心度评价 + 标准化导入 + 数据导出 + 出卷增强
"""
import json, os, random, uuid, sqlite3
from datetime import datetime
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

os.makedirs(TEMPLATES_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

QUESTIONS_FILE = os.path.join(DATA_DIR, 'questions.json')
DB_FILE = os.path.join(DATA_DIR, 'questions.db')
RESULTS_FILE = os.path.join(DATA_DIR, 'results.json')
SYLLABUS_FILE = os.path.join(DATA_DIR, 'syllabus.json')

DEFAULT_QUESTIONS = {"questions": [], "banks": {}, "meta": {"version": 3, "created": datetime.now().isoformat()}}

VALID_TYPES = {"single", "multiple", "reading", "translation", "writing", "dialogue_completion"}

def normalize_confidence(c):
    """Convert confidence to string: 3/high/confident -> 'confident', 2/neutral -> 'neutral', 1/low/guess -> 'guess'"""
    c = str(c).lower()
    if c in ('3', 'high', 'confident'):
        return 'confident'
    elif c in ('2', 'neutral'):
        return 'neutral'
    elif c in ('1', 'low', 'guess'):
        return 'guess'
    return c

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def db_query(sql, params=()):
    conn = get_db()
    try:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def db_execute(sql, params=()):
    conn = get_db()
    try:
        conn.execute(sql, params)
        conn.commit()
    finally:
        conn.close()


def load_json(path, default):
    if not os.path.exists(path):
        save_json(path, default)
        return default
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _map_category_to_qtype(category):
    """将 category（如'词语语法'）映射为 qtype（如'single'）"""
    cat_lower = str(category).lower().replace(' ', '_')
    if cat_lower in ('写作', 'writing'):
        return 'writing'
    elif cat_lower in ('翻译', 'translation'):
        return 'translation'
    elif cat_lower in ('对话补全', 'dialogue_completion'):
        return 'dialogue_completion'
    elif cat_lower in ('阅读', 'reading', '阅读理解'):
        return 'reading'
    elif cat_lower in ('多选', 'multiple'):
        return 'multiple'
    else:
        return 'single'


def load_questions():
    """从SQLite数据库加载题目（主数据源），JSON作为备用"""
    try:
        rows = db_query('SELECT * FROM questions ORDER BY id')
        questions = []
        banks = {}
        for r in rows:
            q = {
                'id': str(r['question_id']),
                'question_id': str(r['question_id']),
                'question': r['question'],
                'options': json.loads(r['options']) if r['options'] else [],
                'correct_answer': r['correct_answer'],
                'knowledge_point': r['knowledge_point'],
                'explanation': r['explanation'],
                'bank': r['bank'],
                'type': r.get('category', '词语语法'),
                'qtype': _map_category_to_qtype(r.get('category', '词语语法')),
                'passage': r.get('passage', ''),
                'reference': '',
                'difficulty': r.get('difficulty', 3),
                'tags': json.loads(r['tags']) if r.get('tags') else [],
                'source': r.get('source', ''),
                'has_attempts': False
            }
            questions.append(q)
            bk = q['bank']
            if bk not in banks:
                banks[bk] = {'name': bk, 'total': 0}
            banks[bk]['total'] = banks[bk].get('total', 0) + 1
        return {'questions': questions, 'banks': banks, 'meta': {'version': 3, 'source': 'sqlite'}}
    except Exception as e:
        print(f"  [WARN] SQLite failed ({e}), falling back to JSON")
        data = load_json(QUESTIONS_FILE, DEFAULT_QUESTIONS)
        for q in data.get('questions', []):
            q.setdefault('id', q.get('question_id', str(uuid.uuid4().hex[:8])))
            q.setdefault('qtype', _map_category_to_qtype(q.get('type', 'single')))
        return data


def save_questions(data):
    """保存题目到 JSON，同时同步回 SQLite"""
    save_json(QUESTIONS_FILE, data)
    try:
        conn = get_db()
        sql = 'INSERT OR REPLACE INTO questions (question_id, question, options, correct_answer, knowledge_point, explanation, bank, category, passage, difficulty, tags, source) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
        for q in data.get('questions', []):
            qid = str(q.get('question_id') or q.get('id', ''))
            options = json.dumps(q.get('options', []))
            tags = json.dumps(q.get('tags', []))
            category = q.get('type', '词语语法')
            qtype = q.get('qtype', 'single')
            if qtype in ('writing', 'translation', 'dialogue_completion'):
                category = {'writing': '写作', 'translation': '翻译', 'dialogue_completion': '对话补全'}.get(qtype, category)
            conn.execute(sql, (qid, q.get('question', ''), options, q.get('correct_answer', ''), q.get('knowledge_point', '未知'), q.get('explanation', ''), q.get('bank', '默认'), category, q.get('passage', ''), q.get('difficulty', 3), tags, q.get('source', '')))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"  [WARN] SQLite sync failed: {e}")


def load_results():
    return load_json(RESULTS_FILE, [])


def save_results(data):
    save_json(RESULTS_FILE, data)


# ── 前端路由 ──

@app.route('/')
def index():
    qdata = load_questions()
    results = load_results()
    return render_template('index.html',
                         total=len(qdata.get("questions", [])),
                         banks=qdata.get("banks", {}),
                         attempts=len(results))


@app.route('/exam/<bank>')
def exam_page(bank):
    qdata = load_questions()
    qs = [q for q in qdata.get("questions", []) if q.get("bank") == bank]
    # Ensure every question has both 'id' and 'qtype'
    for q in qs:
        q.setdefault('id', q.get('question_id', str(uuid.uuid4().hex[:8])))
        q.setdefault('qtype', _map_category_to_qtype(q.get('type', 'single')))
    return render_template('exam.html', bank=bank, questions=qs)


@app.route('/results')
def results_page():
    results = load_results()
    results.sort(key=lambda x: x.get("date", ""), reverse=True)
    return render_template('results.html', results=results[:50])


@app.route('/writing')
def writing_page():
    qdata = load_questions()
    writing_qs = [q for q in qdata.get("questions", []) if q.get("qtype") in ("writing", "translation")]
    return render_template('writing.html', questions=writing_qs)


@app.route('/translation')
def translation_page():
    qdata = load_questions()
    trans_qs = [q for q in qdata.get("questions", []) if q.get("qtype") in ("translation",)]
    for q in trans_qs:
        q.setdefault('id', q.get('question_id', str(uuid.uuid4().hex[:8])))
    return render_template('translation.html', questions=trans_qs)


@app.route('/dialogue')
def dialogue_page():
    qdata = load_questions()
    dial_qs = [q for q in qdata.get("questions", []) if q.get("qtype") in ("dialogue_completion",)]
    for q in dial_qs:
        q.setdefault('id', q.get('question_id', str(uuid.uuid4().hex[:8])))
    return render_template('dialogue.html', questions=dial_qs)


# ── 题库管理 API ──

@app.route('/api/banks')
def list_banks():
    data = load_questions()
    banks = data.get("banks", {})
    questions = data.get("questions", [])
    result = {}
    for bk, info in banks.items():
        qs = [q for q in questions if q.get("bank") == bk]
        result[bk] = {
            "name": info.get("name", bk),
            "description": info.get("description", ""),
            "total": len(qs),
            "by_type": {},
            "by_kp": {}
        }
        for q in qs:
            t = q.get("qtype", q.get("type", "single"))
            kp = q.get("knowledge_point", "未知")
            result[bk]["by_type"][t] = result[bk]["by_type"].get(t, 0) + 1
            result[bk]["by_kp"][kp] = result[bk]["by_kp"].get(kp, 0) + 1
    return jsonify({"success": True, "banks": result})


@app.route('/api/quiz/questions')
def get_questions():
    bank = request.args.get('bank', '')
    qtype = request.args.get('type', '')
    qdata = load_questions()
    qs = qdata.get("questions", [])
    if bank:
        qs = [q for q in qs if q.get('bank') == bank]
    if qtype:
        qs = [q for q in qs if q.get('qtype', q.get('type', '')) == qtype]
    safe = [{k: v for k, v in q.items() if k not in ("answer", "reference")} for q in qs]
    return jsonify({"questions": safe, "total": len(safe)})


@app.route('/api/quiz/check', methods=['POST'])
def check_answer():
    body = request.get_json()
    qid = body.get('question_id')
    user_answer = body.get('answer', '').strip()

    qdata = load_questions()
    question = None
    for q in qdata.get("questions", []):
        qid_str = str(q.get("id") or q.get("question_id", ""))
        if qid_str == str(qid):
            question = q
            break

    if not question:
        return jsonify({"success": False, "error": "题目不存在"}), 404

    correct_answer = question.get('correct_answer', question.get('answer', ''))
    qtype = question.get('type', 'single')
    is_correct = False

    if qtype in ('writing', 'translation'):
        return jsonify({
            "success": True,
            "is_correct": None,
            "reference": question.get('reference', ''),
            "explanation": question.get('explanation', '请对照参考答案自评'),
            "type": qtype,
            "user_answer": user_answer,
            "correct_answer": "主观题，请自行评分",
            "knowledge_point": question.get('knowledge_point', '')
        })

    if qtype == 'dialogue_completion':
        is_correct = user_answer.upper() == str(correct_answer).upper().strip()

    elif qtype in ('single', 'boolean'):
        is_correct = user_answer.upper() == str(correct_answer).upper().strip()
    elif qtype == 'multiple':
        ua = sorted([a.strip().upper() for a in user_answer.replace('，', ',').split(',') if a.strip()])
        ca_raw = correct_answer if isinstance(correct_answer, list) else str(correct_answer).replace('，', ',').split(',')
        ca = sorted([a.strip().upper() for a in ca_raw if a.strip()])
        is_correct = ua == ca
    elif qtype == 'fill':
        acceptable = [str(correct_answer).strip().lower()]
        acceptable += [a.strip().lower() for a in str(correct_answer).split('/')]
        is_correct = user_answer.lower() in acceptable
    elif qtype == 'reading':
        is_correct = user_answer.upper() == str(correct_answer).upper().strip()
    else:
        is_correct = user_answer.upper() == str(correct_answer).upper().strip()

    return jsonify({
        "success": True,
        "is_correct": is_correct,
        "correct_answer": correct_answer,
        "explanation": question.get('explanation', ''),
        "knowledge_point": question.get('knowledge_point', ''),
        "type": qtype,
        "qtype": question.get('qtype', qtype),
        "user_answer": user_answer,
        "reference": question.get('reference', '')
    })


@app.route('/api/quiz/check-translation', methods=['POST'])
def check_translation():
    """翻译题提交/评分 - 返回参考译文、评分维度和逐句对比"""
    body = request.get_json()
    qid = body.get('question_id')
    user_translation = body.get('answer', '').strip()

    qdata = load_questions()
    question = None
    for q in qdata.get("questions", []):
        qid_str = str(q.get("id") or q.get("question_id", ""))
        if qid_str == str(qid):
            question = q
            break

    if not question:
        return jsonify({"success": False, "error": "题目不存在"}), 404

    reference = question.get('reference', question.get('correct_answer', '无参考译文'))
    source_text = question.get('question', '')

    # 基本统计
    user_words = len(user_translation.split())
    ref_words = len(reference.split())
    user_chars = len(user_translation.replace(' ', ''))

    # 关键词匹配（简单分析，不替AI评分）
    ref_keywords = set(reference.lower().split())
    user_keywords = set(user_translation.lower().split())
    keyword_overlap = ref_keywords & user_keywords
    keyword_rate = round(len(keyword_overlap) / max(len(ref_keywords), 1) * 100, 1)

    return jsonify({
        "success": True,
        "is_correct": None,
        "reference": reference,
        "explanation": question.get('explanation', ''),
        "knowledge_point": question.get('knowledge_point', ''),
        "source_text": source_text,
        "user_translation": user_translation,
        "stats": {
            "user_words": user_words,
            "ref_words": ref_words,
            "user_chars": user_chars,
            "keyword_overlap_rate": keyword_rate
        },
        "scoring_dimensions": [
            {"name": "语义准确性", "weight": "40%", "description": "是否准确传达了原文意思"},
            {"name": "语言流畅度", "weight": "30%", "description": "译文是否通顺自然，符合目标语言习惯"},
            {"name": "词汇与语法", "weight": "20%", "description": "关键词汇翻译是否准确，语法是否正确"},
            {"name": "完整性", "weight": "10%", "description": "是否完整翻译了原文所有内容"}
        ]
    })


@app.route('/api/quiz/check-writing', methods=['POST'])
def check_writing():
    """写作题提交/评分 - 返回参考范文、评分标准和统计信息"""
    body = request.get_json()
    qid = body.get('question_id')
    user_essay = body.get('answer', '').strip()

    qdata = load_questions()
    question = None
    for q in qdata.get("questions", []):
        qid_str = str(q.get("id") or q.get("question_id", ""))
        if qid_str == str(qid):
            question = q
            break

    if not question:
        return jsonify({"success": False, "error": "题目不存在"}), 404

    reference = question.get('reference', question.get('correct_answer', '无参考范文'))
    prompt_text = question.get('question', '')

    # 字数统计
    user_words = len(user_essay.split())
    user_sentences = len([s for s in user_essay.replace('!','.').replace('?','.').split('.') if s.strip()])
    user_paragraphs = len([p for p in user_essay.split('\n\n') if p.strip()])

    # 提取题目要求的词数范围
    import re
    word_range_match = re.search(r'(\d+)\s*[-–—]\s*(\d+)\s*(词|word|字)', prompt_text)
    required_min = int(word_range_match.group(1)) if word_range_match else 0
    required_max = int(word_range_match.group(2)) if word_range_match else 0

    word_feedback = ""
    if required_min and required_max:
        if user_words < required_min:
            word_feedback = f"字数不足（当前 {user_words} 词，要求 {required_min}-{required_max} 词）"
        elif user_words > required_max:
            word_feedback = f"字数偏多（当前 {user_words} 词，要求 {required_min}-{required_max} 词）"
        else:
            word_feedback = f"字数符合要求（{user_words} 词，要求 {required_min}-{required_max} 词）"
    else:
        word_feedback = f"共 {user_words} 词"

    return jsonify({
        "success": True,
        "is_correct": None,
        "reference": reference,
        "explanation": question.get('explanation', ''),
        "knowledge_point": question.get('knowledge_point', ''),
        "prompt": prompt_text,
        "user_essay": user_essay,
        "word_feedback": word_feedback,
        "stats": {
            "user_words": user_words,
            "user_sentences": user_sentences,
            "user_paragraphs": user_paragraphs,
            "required_min": required_min,
            "required_max": required_max
        },
        "scoring_dimensions": [
            {"name": "内容完整性", "weight": "30%", "description": "是否覆盖题目要求的所有要点"},
            {"name": "语言准确性", "weight": "25%", "description": "语法、拼写、标点是否正确"},
            {"name": "结构逻辑性", "weight": "20%", "description": "段落结构是否清晰，逻辑是否连贯"},
            {"name": "词汇丰富度", "weight": "15%", "description": "用词是否多样，表达是否地道"},
            {"name": "格式规范性", "weight": "10%", "description": "格式是否规范，字数是否符合要求"}
        ]
    })


@app.route('/api/quiz/save', methods=['POST'])
def save_attempt():
    """保存答题记录（含信心度）"""
    data = request.get_json()
    results = load_results()

    record = {
        "attempt_id": data.get("attempt_id", str(uuid.uuid4().hex[:12])),
        "date": datetime.now().isoformat(),
        "bank": data.get("bank", "default"),
        "total_questions": data.get("total_questions", 0),
        "correct_count": data.get("correct_count", 0),
        "score": data.get("score", 0),
        "duration_seconds": data.get("duration_seconds", 0),
        "answers": data.get("answers", [])
    }

    # 统计信心度
    confidence_stats = {"confident": 0, "neutral": 0, "guess": 0}
    guess_correct = 0
    guess_total = 0
    for a in record["answers"]:
        c = normalize_confidence(a.get("confidence", ""))
        if c in confidence_stats:
            confidence_stats[c] += 1
        if c == "guess":
            guess_total += 1
            if a.get("is_correct"):
                guess_correct += 1
    record["confidence_stats"] = confidence_stats
    record["guess_correct"] = guess_correct
    record["guess_total"] = guess_total

    results.append(record)
    save_results(results)

    # 标记已做过的题目
    qdata = load_questions()
    attempted_ids = set()
    for a in record["answers"]:
        qid = a.get("question_id")
        if qid:
            attempted_ids.add(str(qid))
    modified = False
    for q in qdata.get("questions", []):
        if str(q.get("id")) in attempted_ids and not q.get("has_attempts"):
            q["has_attempts"] = True
            modified = True
    if modified:
        save_questions(qdata)

    return jsonify({"success": True, "attempt_id": record["attempt_id"]})


# ── Agent 专用 API ──

@app.route('/api/agent/import', methods=['POST'])
def agent_import():
    """Agent 批量导入新题 — 支持 FORMAT.md 标准格式验证"""
    body = request.get_json()
    questions_list = body.get("questions", [])
    bank = body.get("bank", "默认题库")
    bank_desc = body.get("bank_description", "")
    auto_id = body.get("auto_id", True)

    data = load_questions()
    existing = data.get("questions", [])
    existing_ids = {str(q.get("id")) for q in existing}
    added = 0
    skipped = 0
    errors = []

    for idx, q in enumerate(questions_list):
        # 验证必填字段
        qtype = q.get("type", "single")
        if qtype not in VALID_TYPES:
            errors.append({"index": idx, "error": f"无效题型 '{qtype}'，有效值: {', '.join(sorted(VALID_TYPES))}"})
            continue
        if not q.get("question"):
            errors.append({"index": idx, "error": "缺少必填字段 question"})
            continue

        qid = q.get("id") or q.get("question_id")
        if auto_id or not qid:
            qid = f"{bank}_{len(existing) + added + 1}" if bank else str(uuid.uuid4().hex[:8])
        if str(qid) in existing_ids:
            skipped += 1
            continue

        q["id"] = str(qid)
        q["question_id"] = str(qid)
        q["bank"] = bank
        q.setdefault("type", "single")
        q.setdefault("options", [])
        q.setdefault("explanation", "")
        q.setdefault("knowledge_point", "未知")
        q.setdefault("tags", [])
        q.setdefault("difficulty", 3)
        if not isinstance(q.get("difficulty"), (int, float)) or not (1 <= q["difficulty"] <= 5):
            q["difficulty"] = 3
        q.setdefault("has_attempts", False)
        q.setdefault("passage", "")
        q.setdefault("reference", "")
        q.setdefault("source", q.get("source", ""))
        q["_created"] = datetime.now().isoformat()
        existing.append(q)
        existing_ids.add(str(qid))
        added += 1

    if bank not in data.get("banks", {}):
        data.setdefault("banks", {})
        data["banks"][bank] = {"name": bank, "description": bank_desc, "_created": datetime.now().isoformat()}

    data["questions"] = existing
    save_questions(data)

    return jsonify({
        "success": True,
        "added": added,
        "skipped": skipped,
        "total": len(existing),
        "errors": errors
    })


@app.route('/api/agent/batch-check', methods=['POST'])
def agent_batch_check():
    body = request.get_json()
    answers = body.get("answers", [])
    data = load_questions()
    q_map = {}
    for q in data.get("questions", []):
        qid = str(q.get("id") or q.get("question_id", ""))
        q_map[qid] = q
    results = []

    for item in answers:
        qid = str(item.get("question_id"))
        ua = item.get("answer", "").strip()
        q = q_map.get(qid)
        if not q:
            results.append({"question_id": qid, "error": "not found"})
            continue
        ca = q.get("correct_answer", "")
        qt = q.get("qtype", q.get("type", "single"))
        if qt in ("single", "boolean", "dialogue_completion"):
            ok = ua.upper() == str(ca).upper().strip()
        elif qt == "multiple":
            ua_s = sorted([x.strip().upper() for x in ua.replace("，", ",").split(",") if x.strip()])
            ca_raw = ca if isinstance(ca, list) else str(ca).replace("，", ",").split(",")
            ca_s = sorted([x.strip().upper() for x in ca_raw if x.strip()])
            ok = ua_s == ca_s
        elif qt == "fill":
            ok = ua.lower() in [x.strip().lower() for x in str(ca).split("/")]
        elif qt in ("translation", "writing"):
            ok = None
        else:
            ok = ua.upper() == str(ca).upper().strip()
        results.append({
            "question_id": qid,
            "is_correct": ok,
            "correct_answer": ca if ok is not None else "主观题",
            "user_answer": ua,
            "knowledge_point": q.get("knowledge_point"),
            "explanation": q.get("explanation", ""),
            "reference": q.get("reference", "") if ok is None else ""
        })

    return jsonify({"success": True, "results": results})


# ── 分析 API ──

@app.route('/api/analysis/wrong')
def wrong_questions():
    results = load_results()
    qdata = load_questions()
    q_map = {};
    for q in qdata.get("questions", []):
        qid = str(q.get("id") or q.get("question_id", "")); q_map[qid] = q

    wrong = {}
    for r in results:
        for a in r.get("answers", []):
            if a.get("is_correct") is False:
                qid = str(a.get("question_id"))
                if qid not in wrong:
                    q = q_map.get(qid, {})
                    wrong[qid] = {
                        "question": a.get("question", ""),
                        "correct_answer": q.get("correct_answer", ""),
                        "user_answer": a.get("user_answer", ""),
                        "explanation": q.get("explanation", ""),
                        "wrong_count": 1
                    }
                else:
                    wrong[qid]["wrong_count"] += 1
    return jsonify({"questions": wrong})


@app.route('/api/analysis/wrong-questions')
def analysis_wrong_questions():
    results = load_results()
    qdata = load_questions()
    q_map = {};
    for q in qdata.get("questions", []):
        qid = str(q.get("id") or q.get("question_id", "")); q_map[qid] = q
    bank = request.args.get("bank")

    wrong_map = {}
    for r in results:
        if bank and r.get("bank") != bank:
            continue
        for a in r.get("answers", []):
            if a.get("is_correct") is False:
                qid = str(a.get("question_id", ""))
                q = q_map.get(qid, {})
                if qid not in wrong_map:
                    wrong_map[qid] = {
                        "question_id": qid,
                        "question": q.get("question", a.get("question", ""))[:150],
                        "type": q.get("type", ""),
                        "knowledge_point": q.get("knowledge_point", ""),
                        "correct_answer": q.get("correct_answer", a.get("correct_answer", "")),
                        "explanation": q.get("explanation", a.get("explanation", "")),
                        "wrong_count": 0,
                        "attempts": []
                    }
                wrong_map[qid]["wrong_count"] += 1
                wrong_map[qid]["attempts"].append({
                    "attempt_id": r.get("attempt_id"),
                    "date": r.get("date"),
                    "user_answer": a.get("user_answer", "")
                })
    return jsonify({"success": True, "total_wrong": len(wrong_map), "questions": list(wrong_map.values())})


@app.route('/api/analysis/knowledge-points')
def analysis_knowledge_points():
    """按知识点统计正确率（含信心度维度）"""
    results = load_results()
    qdata = load_questions()
    q_map = {};
    for q in qdata.get("questions", []):
        qid = str(q.get("id") or q.get("question_id", "")); q_map[qid] = q
    bank = request.args.get("bank")

    stats = {}
    for r in results:
        if bank and r.get("bank") != bank:
            continue
        for a in r.get("answers", []):
            if a.get("is_correct") is None:
                continue
            qid = str(a.get("question_id", ""))
            q = q_map.get(qid, {})
            kp = q.get("knowledge_point", "未知")
            if kp not in stats:
                stats[kp] = {
                    "total": 0, "correct": 0,
                    "confident_total": 0, "confident_correct": 0,
                    "neutral_total": 0, "neutral_correct": 0,
                    "guess_total": 0, "guess_correct": 0,
                    "questions": set()
                }
            stats[kp]["total"] += 1
            stats[kp]["questions"].add(qid)

            is_correct = a.get("is_correct", False)
            if is_correct:
                stats[kp]["correct"] += 1

            confidence = normalize_confidence(a.get("confidence", ""))
            if confidence == "confident":
                stats[kp]["confident_total"] += 1
                if is_correct:
                    stats[kp]["confident_correct"] += 1
            elif confidence == "neutral":
                stats[kp]["neutral_total"] += 1
                if is_correct:
                    stats[kp]["neutral_correct"] += 1
            elif confidence == "guess":
                stats[kp]["guess_total"] += 1
                if is_correct:
                    stats[kp]["guess_correct"] += 1

    result = {}
    weak_points = []
    for kp, s in stats.items():
        surface_rate = round(s["correct"] / s["total"] * 100, 1) if s["total"] else 0
        # 真实掌握率 = (有把握对 + 一般对) / (有把握总 + 一般总)
        true_total = s["confident_total"] + s["neutral_total"]
        true_correct = s["confident_correct"] + s["neutral_correct"]
        true_rate = round(true_correct / true_total * 100, 1) if true_total > 0 else surface_rate

        # 蒙对率
        guess_correct = s["guess_correct"]
        guess_total = s["guess_total"]
        guess_rate = round(guess_correct / guess_total * 100, 1) if guess_total > 0 else 0

        result[kp] = {
            "total": s["total"],
            "correct": s["correct"],
            "surface_correct_rate": surface_rate,       # 表面正确率（含蒙对）
            "true_correct_rate": true_rate,              # 真实掌握率（不含蒙）
            "confident_total": s["confident_total"],
            "confident_correct": s["confident_correct"],
            "neutral_total": s["neutral_total"],
            "neutral_correct": s["neutral_correct"],
            "guess_total": guess_total,
            "guess_correct": guess_correct,
            "guess_correct_rate": guess_rate,            # 蒙对率
            "question_count": len(s["questions"])
        }

        # 薄弱点判断：真实掌握率 < 70% 或 蒙对 > 0
        is_weak = (true_rate < 70 and s["total"] >= 2) or guess_total > 0
        if is_weak:
            weak_points.append({
                "knowledge_point": kp,
                "true_correct_rate": true_rate,
                "surface_correct_rate": surface_rate,
                "total": s["total"],
                "guess_total": guess_total,
                "guess_correct": guess_correct
            })

    # 排序：蒙对数越多越靠前，然后按真实掌握率升序
    weak_points.sort(key=lambda x: (-x["guess_correct"], x["true_correct_rate"]))

    return jsonify({
        "success": True,
        "by_knowledge_point": result,
        "weak_points": weak_points
    })


@app.route('/api/analysis/generate-review-exam', methods=['POST'])
def generate_review_exam():
    """按薄弱知识点自动出卷 — 优先蒙对知识点"""
    body = request.get_json()
    count = body.get("count", 10)
    focus_kps = body.get("knowledge_points", [])
    include_kps = body.get("include_knowledge_points", [])
    exclude_attempted = body.get("exclude_attempted", True)

    qdata = load_questions()
    all_qs = qdata.get("questions", [])

    # 分析薄弱点（含蒙对识别）
    results = load_results()
    q_map = {str(q.get("question_id") or q.get("id")): q for q in all_qs}
    kp_guess = {}  # kp -> guess_correct_count
    kp_true_rate = {}
    kp_total = {}

    for r in results:
        for a in r.get("answers", []):
            if a.get("is_correct") is None:
                continue
            qid = str(a.get("question_id", ""))
            q = q_map.get(qid, {})
            kp = q.get("knowledge_point", "未知")
            if kp not in kp_total:
                kp_total[kp] = {"correct": 0, "total": 0, "guess_correct": 0, "true_correct": 0, "true_total": 0}
            kp_total[kp]["total"] += 1
            if a.get("is_correct"):
                kp_total[kp]["correct"] += 1
            confidence = normalize_confidence(a.get("confidence", ""))
            if confidence == "guess":
                kp_guess[kp] = kp_guess.get(kp, 0) + (1 if a.get("is_correct") else 0)
            if confidence in ("confident", "neutral"):
                kp_total[kp]["true_total"] += 1
                if a.get("is_correct"):
                    kp_total[kp]["true_correct"] += 1

    for kp, s in kp_total.items():
        true_total = s["true_total"]
        kp_true_rate[kp] = round(s["true_correct"] / true_total * 100, 1) if true_total > 0 else 100

    # 构建优先级：蒙对知识点 > 薄弱知识点
    priority_kps = []
    # 优先：有蒙对的知识点
    for kp, gc in sorted(kp_guess.items(), key=lambda x: -x[1]):
        if gc > 0:
            priority_kps.append(kp)
    # 其次：薄弱知识点（真实掌握率 < 70%）
    for kp, rate in sorted(kp_true_rate.items(), key=lambda x: x[1]):
        if rate < 70 and kp not in priority_kps:
            priority_kps.append(kp)

    # 如果指定了 focus_kps 优先使用
    if focus_kps:
        priority_kps = focus_kps
    elif include_kps:
        priority_kps = include_kps

    # 按优先级选题目，每个知识点至少2道
    selected = []
    selected_ids = set()
    kp_count = {}

    q_by_kp = {}
    for q in all_qs:
        kp = q.get("knowledge_point", "未知")
        if kp not in q_by_kp:
            q_by_kp[kp] = []
        q_by_kp[kp].append(q)

    # 第一轮：每个优先级知识点至少2道
    for kp in priority_kps:
        if len(selected) >= count:
            break
        candidates = q_by_kp.get(kp, [])
        if not candidates:
            continue
        random.shuffle(candidates)
        added = 0
        for q in candidates:
            if len(selected) >= count:
                break
            qid = str(q.get("id"))
            if qid in selected_ids:
                continue
            if exclude_attempted and q.get("has_attempts", False):
                continue
            selected.append(q)
            selected_ids.add(qid)
            kp_count[kp] = kp_count.get(kp, 0) + 1
            added += 1
            if added >= 2:
                break

    # 第二轮：不够则从所有候选补充
    if len(selected) < count:
        remaining = [q for q in all_qs if str(q.get("id")) not in selected_ids
                     and (not exclude_attempted or not q.get("has_attempts", False))]
        random.shuffle(remaining)
        for q in remaining:
            if len(selected) >= count:
                break
            selected.append(q)

    safe = [{k: v for k, v in q.items() if k not in ("answer", "reference")} for q in selected]
    return jsonify({
        "success": True,
        "total": len(selected),
        "exam": safe,
        "priority_knowledge_points": priority_kps[:5]
    })


@app.route('/api/analysis/overview')
def overview():
    """学习概览数据（含近期记录）"""
    results = load_results()
    qdata = load_questions()

    total_questions = len(qdata.get("questions", []))
    total_correct = 0
    total_answered = 0

    for r in results:
        total_correct += r.get("correct_count", 0)
        total_answered += r.get("total_questions", 0)

    # 最近 5 条
    recent = []
    sorted_results = sorted(results, key=lambda x: x.get("date", ""), reverse=True)
    for r in sorted_results[:5]:
        recent.append({
            "attempt_id": r.get("attempt_id", ""),
            "bank": r.get("bank", ""),
            "date": r.get("date", ""),
            "correct_count": r.get("correct_count", 0),
            "total_questions": r.get("total_questions", 0),
            "score": r.get("score", 0)
        })

    return jsonify({
        "total_questions": total_questions,
        "total_correct": total_correct,
        "total_answered": total_answered,
        "overall_rate": round(total_correct / total_answered * 100, 1) if total_answered else 0,
        "attempts": len(results),
        "recent": recent
    })


# ── 数据导出 API ──

@app.route('/api/analysis/export-results')
def export_results():
    """导出所有答题记录为 JSON（时间倒序）"""
    results = load_results()
    results.sort(key=lambda x: x.get("date", ""), reverse=True)

    export = {
        "exported_at": datetime.now().isoformat(),
        "total_records": len(results),
        "records": results
    }
    return jsonify({"success": True, "data": export})


@app.route('/api/analysis/export-weakpoints')
def export_weakpoints():
    """导出薄弱知识点分析报告"""
    results = load_results()
    qdata = load_questions()
    q_map = {};
    for q in qdata.get("questions", []):
        qid = str(q.get("id") or q.get("question_id", "")); q_map[qid] = q
    bank = request.args.get("bank")

    stats = {}
    for r in results:
        if bank and r.get("bank") != bank:
            continue
        for a in r.get("answers", []):
            if a.get("is_correct") is None:
                continue
            qid = str(a.get("question_id", ""))
            q = q_map.get(qid, {})
            kp = q.get("knowledge_point", "未知")
            if kp not in stats:
                stats[kp] = {
                    "knowledge_point": kp,
                    "total": 0, "correct": 0,
                    "confident_total": 0, "confident_correct": 0,
                    "neutral_total": 0, "neutral_correct": 0,
                    "guess_total": 0, "guess_correct": 0
                }
            stats[kp]["total"] += 1
            is_correct = a.get("is_correct", False)
            if is_correct:
                stats[kp]["correct"] += 1

            confidence = normalize_confidence(a.get("confidence", ""))
            if confidence == "confident":
                stats[kp]["confident_total"] += 1
                if is_correct:
                    stats[kp]["confident_correct"] += 1
            elif confidence == "neutral":
                stats[kp]["neutral_total"] += 1
                if is_correct:
                    stats[kp]["neutral_correct"] += 1
            elif confidence == "guess":
                stats[kp]["guess_total"] += 1
                if is_correct:
                    stats[kp]["guess_correct"] += 1

    items = []
    for kp, s in stats.items():
        surface_rate = round(s["correct"] / s["total"] * 100, 1) if s["total"] else 0
        true_total = s["confident_total"] + s["neutral_total"]
        true_correct = s["confident_correct"] + s["neutral_correct"]
        true_rate = round(true_correct / true_total * 100, 1) if true_total > 0 else surface_rate
        guess_total = s["guess_total"]
        guess_correct = s["guess_correct"]
        guess_rate = round(guess_correct / guess_total * 100, 1) if guess_total > 0 else 0

        risk = "safe"
        if true_rate < 50 or guess_total > 0:
            risk = "critical"
        elif true_rate < 70:
            risk = "weak"

        items.append({
            "knowledge_point": kp,
            "total": s["total"],
            "correct": s["correct"],
            "surface_correct_rate": surface_rate,
            "true_correct_rate": true_rate,
            "confident_total": s["confident_total"],
            "confident_correct": s["confident_correct"],
            "neutral_total": s["neutral_total"],
            "neutral_correct": s["neutral_correct"],
            "guess_total": guess_total,
            "guess_correct": guess_correct,
            "guess_correct_rate": guess_rate,
            "risk_level": risk,
            "recommendation": "需重点复习" if risk in ("critical", "weak") else "已掌握"
        })

    items.sort(key=lambda x: (x["risk_level"] != "critical", x["true_correct_rate"]))

    summary = {
        "exported_at": datetime.now().isoformat(),
        "total_knowledge_points": len(items),
        "critical_count": sum(1 for i in items if i["risk_level"] == "critical"),
        "weak_count": sum(1 for i in items if i["risk_level"] == "weak"),
        "safe_count": sum(1 for i in items if i["risk_level"] == "safe"),
        "readable_summary": []
    }

    for item in items:
        summary["readable_summary"].append(
            f"[{item['risk_level'].upper()}] {item['knowledge_point']}: "
            f"真实掌握率 {item['true_correct_rate']}% (表面 {item['surface_correct_rate']}%), "
            f"蒙对 {item['guess_correct']}/{item['guess_total']}, "
            f"建议: {item['recommendation']}"
        )

    return jsonify({"success": True, "data": summary, "details": items})


# ── 考纲管理 ──

@app.route('/api/syllabus', methods=['GET', 'POST', 'PUT'])
def syllabus():
    if request.method == 'GET':
        return jsonify({"success": True, "syllabus": load_json(SYLLABUS_FILE, {})})
    body = request.get_json()
    save_json(SYLLABUS_FILE, body)
    return jsonify({"success": True, "message": "考纲已保存"})


# ── 启动 ──
if __name__ == '__main__':
    print("=" * 50)
    print("  科举 v3 — Agent 优先智能备考系统")
    print("  各类应试考试")
    print(f"  题库文件: {QUESTIONS_FILE}")
    print(f"  记录文件: {RESULTS_FILE}")
    print(f"  访问地址: http://localhost:8081")
    print("=" * 50)
    app.run(host='0.0.0.0', port=8081, debug=False)

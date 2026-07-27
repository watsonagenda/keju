#!/usr/bin/env python3
"""迁移科举系统数据 + 注入Agent收集的真题

使用方法：
1. 修改 KEJU_QUESTIONS 和 BACKUP_PATH 为您的实际路径
2. 运行: python3 scripts/migrate_keju.py
"""
import json, os, sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
QUESTIONS_FILE = os.path.join(DATA_DIR, 'questions.json')

# ⚠️ 请根据实际情况修改以下路径
KEJU_QUESTIONS = os.path.join(BASE_DIR, 'questions.json')
# BACKUP_PATH = None  # 可选：指定备份文件路径  # 例如: "/path/to/backup.json"

def load_json(path):
    if not path:
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"  ⚠️  无法加载 {path}: {e}")
        return None

def migrate():
    print("=" * 50)
    print("  数据迁移工具 — 科举")
    print("=" * 50)

    new_data = {"questions": [], "banks": {}, "meta": {"version": 2}}

    # 1. 从科举系统迁移
    print("\n📦 从科举系统迁移题目...")
    keju = load_json(KEJU_QUESTIONS)
    migrated_count = 0
    if keju and "题库" in keju:
        for q in keju["题库"]:
            qid = q.get("id")
            if not qid:
                continue
            new_q = {
                "id": str(qid),
                "type": q.get("type", "single").strip().lower(),
                "bank": "应试考试",
                "question": q.get("question", ""),
                "options": q.get("options", []),
                "answer": q.get("answer", ""),
                "explanation": q.get("explanation", ""),
                "knowledge_point": q.get("knowledge_point", "未知"),
                "tags": q.get("tags", []),
                "difficulty": q.get("difficulty", 3),
                "passage": q.get("passage", ""),
                "reference": q.get("reference", ""),
                "has_attempts": False,
                "_created": "2026-05-28T00:00:00"
            }
            t = new_q["type"]
            if t == "boolean": new_q["type"] = "boolean"
            elif t in ("single", "multiple", "fill", "translation", "writing", "reading"): pass
            elif t == "judge": new_q["type"] = "boolean"
            elif t == "填空": new_q["type"] = "fill"
            elif t == "翻译": new_q["type"] = "translation"
            elif t == "写作": new_q["type"] = "writing"
            elif t == "阅读理解": new_q["type"] = "reading"
            elif t == "多选": new_q["type"] = "multiple"
            else: new_q["type"] = "single"
            new_data["questions"].append(new_q)
            migrated_count += 1
        print(f"  ✅ 迁移 {migrated_count} 题")

    # 2. 从备份文件迁移
    if BACKUP_PATH:
        print("\n📦 从备份文件迁移...")
        backup = load_json(BACKUP_PATH)
        if backup and "题库" in backup:
            existing_ids = {q["id"] for q in new_data["questions"]}
            bk_count = 0
            for q in backup["题库"]:
                qid = str(q.get("id", ""))
                if qid in existing_ids:
                    continue
                new_q = {
                    "id": qid,
                    "type": q.get("type", "single").strip().lower(),
                    "bank": "应试考试",
                    "question": q.get("question", ""),
                    "options": q.get("options", []),
                    "answer": q.get("answer", ""),
                    "explanation": q.get("explanation", ""),
                    "knowledge_point": q.get("knowledge_point", "未知"),
                    "tags": q.get("tags", []),
                    "difficulty": q.get("difficulty", 3),
                    "passage": q.get("passage", ""),
                    "reference": q.get("reference", ""),
                    "has_attempts": False,
                    "_created": "2026-05-28T00:00:00"
                }
                t = new_q["type"]
                if t == "boolean": new_q["type"] = "boolean"
                elif t in ("single", "multiple", "fill", "translation", "writing", "reading"): pass
                elif t == "judge": new_q["type"] = "boolean"
                elif t == "填空": new_q["type"] = "fill"
                elif t == "翻译": new_q["type"] = "translation"
                elif t == "写作": new_q["type"] = "writing"
                elif t == "阅读理解": new_q["type"] = "reading"
                elif t == "多选": new_q["type"] = "multiple"
                else: new_q["type"] = "single"
                new_data["questions"].append(new_q)
                existing_ids.add(qid)
                bk_count += 1
            print(f"  ✅ 从备份补充 {bk_count} 题")

    # 设置 bank 信息
    new_data["banks"]["应试考试"] = {
        "name": "应试考试",
        "description": "应试考试题库（含历年真题）",
        "_created": "2026-05-28T00:00:00"
    }

    # 写入
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(QUESTIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(new_data, f, ensure_ascii=False, indent=2)

    # 统计
    type_count = {}
    for q in new_data["questions"]:
        t = q.get("type", "unknown")
        type_count[t] = type_count.get(t, 0) + 1

    print(f"\n📊 迁移完成！")
    print(f"  总题数: {len(new_data['questions'])}")
    for t, n in sorted(type_count.items()):
        print(f"    {t}: {n} 题")
    print(f"\n  📁 写入: {QUESTIONS_FILE}")

if __name__ == '__main__':
    migrate()

# 科举 — Agent 操作指南

## 系统定位
Agent 自动备考系统。Agent 负责：收集真题 → 入库 → 出卷 → 分析错题 → 针对性训练。

## 数据模型

### 题目 (Question)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 唯一ID，建议 `bank_序号` |
| type | string | single/multiple/boolean/fill/translation/writing/reading/dialogue_completion |
| bank | string | 所属题库名 |
| question | string | 题目正文 |
| passage | string | 阅读文章（reading 题型用） |
| options | list[string] | 选项列表 ["A. xxx","B. xxx",...] |
| answer | string/list | 答案（主观题空） |
| reference | string | 翻译参考/写作范文 |
| explanation | string | 解析 |
| knowledge_point | string | 知识点标签 🔑 分析维度核心 |
| tags | list[string] | 标签 ["2014年5月真题","基础"] |
| difficulty | int | 1-5 |
| has_attempts | bool | 有答题记录后自动置true |

### 答题记录 (Attempt)
保存于 `data/results.json`，每条包含：
- attempt_id, date, bank, score, correct_count, total_questions, duration_seconds
- answers: [{question_id, question, user_answer, correct_answer, is_correct, knowledge_point, explanation}, ...]

## Agent 工作流

### 1️⃣ 收集真题 → 批量导入
```
POST /api/agent/import
{
  "bank": "2024年11月真题",
  "bank_description": "2024年11月考试真题",
  "questions": [
    {
      "id": "202411_001",       // 可选，留空自动生成
      "type": "single",
      "question": "...",
      "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
      "answer": "A",
      "explanation": "解析...",
      "knowledge_point": "时态",
      "tags": ["2024年11月真题", "语法"],
      "difficulty": 2
    }
  ]
}
```

### 2️⃣ 出卷
```
GET /api/questions?bank=2024年11月真题&limit=20
```
返回不含答案的题目列表。

### 3️⃣ 校验答案（Agent 批量阅卷）

**客观题批量校验：**
```
POST /api/agent/batch-check
{
  "answers": [
    {"question_id": "1", "answer": "A"},
    {"question_id": "2", "answer": "B,C"}
  ]
}
```

**翻译题单题校验：**
```
POST /api/quiz/check-translation
{
  "question_id": "trans_001",
  "answer": "中国是一个拥有悠久历史的国家。"
}
```
返回参考译文、关键词覆盖率、评分维度（语义准确性40%/语言流畅度30%/词汇语法20%/完整性10%）。

**写作题单题校验：**
```
POST /api/quiz/check-writing
{
  "question_id": "writing_001",
  "answer": "Reading plays an essential role in our lives..."
}
```
返回参考范文、字数反馈、句子/段落统计、评分维度（内容30%/语言25%/结构20%/词汇15%/格式10%）。

**对话补全题校验：**
```
POST /api/quiz/check
{
  "question_id": "dial_001",
  "answer": "A",
  "qtype": "dialogue_completion"
}
```
走标准客观题校验流程，答案字母比对。

### 4️⃣ 分析薄弱点
```
GET /api/analysis/knowledge-points
```
返回各知识点正确率，`weak_points` 列出正确率 < 70% 的知识点。

### 5️⃣ 获取错题
```
GET /api/analysis/wrong-questions
```
返回所有错题列表，包含每次错误详情。

### 6️⃣ 生成针对性复习卷
```
POST /api/analysis/generate-review-exam
{
  "count": 10,
  "knowledge_points": ["时态", "非谓语动词"],
  "exclude_attempted": false
}
```

### 7️⃣ 整体概览
```
GET /api/analysis/overview
```

### 8️⃣ 考纲管理
```
GET /api/syllabus
PUT /api/syllabus  (body: {考纲内容})
```

## 完整复习循环

```
Agent 收集真题 ──导入──> 科举 ──用户做题──> 保存记录 ──Agent分析──> 识别薄弱点
     ^                                                                      │
     └──────────── 生成针对性练习 ──导入新题 ─────────────────────────┘
```

## 快速启动
```bash
cd 
python app.py
# 访问 http://localhost:8080
```

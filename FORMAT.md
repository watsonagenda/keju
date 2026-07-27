# 科举 标准题目格式规范

## JSON 结构

每道题目为一个 JSON 对象，核心字段如下：

```json
{
  "type": "single",
  "question": "题目文本",
  "options": ["A. 选项A", "B. 选项B", "C. 选项C", "D. 选项D"],
  "answer": "A",
  "explanation": "解析文本",
  "knowledge_point": "所属知识点",
  "difficulty": 3,
  "tags": ["标签1", "标签2"],
  "passage": "",
  "reference": "",
  "source": ""
}
```

## 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `type` | string | 是 | 题型：`single`（单选）/ `multiple`（多选）/ `reading`（阅读理解）/ `translation`（翻译）/ `writing`（写作） |
| `question` | string | 是 | 题目文本。如需换行可用 `\n` |
| `options` | string[] | 是 | 选项列表，格式 `"A. 内容"`。写作/翻译题型可为空数组 |
| `answer` | string | 是 | 正确答案。单选/阅读填字母如 `"A"`；多选用逗号分隔如 `"A,C"` 或数组 `["A","C"]`；写作/翻译题填 `"主观题"` |
| `explanation` | string | 推荐 | 题目解析，帮助学生理解 |
| `knowledge_point` | string | 推荐 | 所属知识点，如 `"时态"`、`"虚拟语气"`，用于薄弱点分析 |
| `difficulty` | number | 否 | 难度等级 1-5，默认 3。1=基础，5=高难 |
| `tags` | string[] | 否 | 标签列表，如 `["真题", "2014年5月"]` |
| `passage` | string | 否 | 阅读理解文章内容（仅 `reading` 类型） |
| `reference` | string | 否 | 参考译文/范文（`translation` / `writing` 类型） |
| `source` | string | 否 | 题目来源说明，如 `"2022年真题"`、`"模拟卷A"` |

## 题型示例

### 单选题 (`single`)

```json
{
  "type": "single",
  "question": "By the time we arrived at the cinema, the movie _____ already.",
  "options": ["A. started", "B. has started", "C. had started", "D. was starting"],
  "answer": "C",
  "explanation": "by the time引导的时间状语从句表示在过去某个时间之前已完成的动作，用过去完成时。",
  "knowledge_point": "时态",
  "difficulty": 3,
  "tags": ["语法", "真题"],
  "source": "2022年真题"
}
```

### 多选题 (`multiple`)

```json
{
  "type": "multiple",
  "question": "Which of the following are correct? (Select all that apply)",
  "options": ["A. I have gone to Beijing.", "B. I have been to Beijing.", "C. He has been to Shanghai.", "D. She has gone home."],
  "answer": "B,C,D",
  "explanation": "have gone to表示去了还没回来，have been to表示去过已回来。A中'I have gone'不合逻辑。",
  "knowledge_point": "现在完成时",
  "difficulty": 3,
  "tags": ["语法"]
}
```

### 阅读理解 (`reading`)

```json
{
  "type": "reading",
  "passage": "In recent years, online learning has become increasingly popular...",
  "question": "What is the main idea of the passage?",
  "options": ["A. Online learning is better than traditional learning.", "B. Online learning has advantages and challenges.", "C. Traditional learning is outdated.", "D. Everyone should learn online."],
  "answer": "B",
  "explanation": "全文讨论了在线学习的优势和挑战，B最全面。",
  "knowledge_point": "阅读理解",
  "difficulty": 2,
  "tags": ["阅读", "教育类"]
}
```

### 翻译题 (`translation`)

```json
{
  "type": "translation",
  "question": "将下列句子翻译成英文：\n中国是一个拥有悠久历史的国家。",
  "options": [],
  "answer": "主观题",
  "explanation": "参考译文见 reference 字段。翻译评分要点：时态正确、核心词汇准确、语序通顺。",
  "knowledge_point": "翻译",
  "difficulty": 3,
  "reference": "China is a country with a long history.",
  "tags": ["翻译", "中国文化"],
  "source": "2021年真题"
}
```

### 写作题 (`writing`)

```json
{
  "type": "writing",
  "question": "请以 'The Importance of Reading' 为题，写一篇 100-120 词的英语短文。",
  "options": [],
  "answer": "主观题",
  "explanation": "评分维度：内容完整性、语言准确性、结构逻辑性、词汇丰富度。",
  "knowledge_point": "写作",
  "difficulty": 4,
  "reference": "Reading plays an essential role in our lives...",
  "tags": ["写作", "议论文"],
  "source": "模拟卷"
}
```

### 对话补全题 (`dialogue_completion`)

```json
{
  "type": "dialogue_completion",
  "passage": "Speaker A: Hi, how are you doing today?\nSpeaker B: I'm great! __BLANK__\nSpeaker A: I'm doing well, thanks for asking.",
  "question": "选择最合适的选项补全对话中的空白。",
  "options": ["A. How about you?", "B. What's your name?", "C. Where are you going?", "D. Nice to meet you."],
  "answer": "A",
  "explanation": "B说'I'm great'后需要回问对方的情况，'How about you?'是最自然的社交对话表达。",
  "knowledge_point": "对话补全",
  "difficulty": 2,
  "tags": ["对话补全", "日常交际"],
  "source": "模拟卷"
}
```

对话补全题中，`passage` 字段包含完整对话文本，空白处用 `__BLANK__` 标记。每个填空作为一道独立题目，选项目 `options` 提供可选项，`answer` 记录正确选项字母。

## 批量导入

### API 端点

```
POST /api/agent/import
```

请求体：

```json
{
  "bank": "题库名称",
  "bank_description": "题库描述",
  "questions": [ ... ]
}
```

导入时系统自动：
- 生成唯一 ID（如未提供）
- 校验必填字段
- 去重（同一 ID 不重复导入）
- 统计导入结果

### 响应

```json
{
  "success": true,
  "added": 10,
  "skipped": 2,
  "total": 12,
  "errors": []
}
```

## 大批量题目组织建议（500+题）

1. **按知识点分文件**：每个知识点一个 JSON 文件，如 `tense.json`、`vocabulary.json`
2. **按题型分文件**：`reading_passages.json`、`translation.json`
3. **ID 命名规范**：`{题库缩写}_{知识点}_{序号}`，如 `ExamBank_tense_001`
4. **分批导入**：每次导入 100-200 题，避免单次请求过大
5. **数据库索引**：questions.json 中 `id` 字段自动去重，相同 ID 不重复导入
6. **分页预留**：数据结构 `{"questions":[], "banks":{}, "meta":{"version":2, "total":500}}` 已支持前端分页（需配合 `/api/quiz/questions?page=1&limit=50` 参数，暂未实现分页逻辑，但结构已兼容）

## 数据导出

### 导出答题记录

```
GET /api/analysis/export-results
```
返回所有答题记录 JSON，按时间倒序排列。

### 导出薄弱点分析

```
GET /api/analysis/export-weakpoints
```
返回薄弱知识点分析报告（含信心度维度），JSON 格式。

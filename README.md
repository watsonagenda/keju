# 科举 — Agent 优先的智能备考系统

一个面向各类应试考试的智能备考系统，支持多种题型练习、AI 辅助批改、学情分析和针对性出题。

## 功能特性

- **多种题型**：单选题、多选题、阅读理解、翻译题、写作题、情景对话
- **智能出题**：AI Agent 可根据薄弱点自动生成针对性练习题
- **自动批改**：客观题自动评分，主观题（翻译/写作）AI 辅助评分
- **学情分析**：按知识点统计正确率，识别薄弱环节
- **错题回顾**：自动收集错题，支持生成复习卷
- **Agent 集成**：多 Agent 协作，支持飞书团队机器人

## 技术栈

- **后端**：Python Flask
- **前端**：HTML + CSS + JavaScript（单页应用）
- **数据库**：SQLite（内置）
- **AI**：OpenClaw Agent 框架集成

## 快速开始

### 安装依赖

```bash
pip install flask openpyxl
```

### 启动服务

```bash
cd /path/to/keju
python app.py
```

服务默认运行在 `http://localhost:8081`

### 访问页面

- 首页：`http://localhost:8081/`
- 考试页面：`http://localhost:8081/exam/{bank_name}`
- 翻译练习：`http://localhost:8081/translation`
- 写作练习：`http://localhost:8081/writing`
- 对话补全：`http://localhost:8081/dialogue`
- 结果查看：`http://localhost:8081/results`

## 目录结构

```
科举/
├── app.py              # Flask 主应用
├── FORMAT.md           # 题目格式规范
├── AGENTS.md           # Agent 操作指南
├── review_rules.yaml   # 审题规则配置
├── openclaw_agents.yaml # Agent 多角色配置
├── templates/          # HTML 模板
│   ├── index.html      # 首页
│   ├── exam.html       # 考试页
│   ├── translation.html # 翻译页
│   ├── writing.html    # 写作页
│   ├── dialogue.html   # 对话页
│   └── results.html    # 结果页
├── static/             # 静态资源（CSS/JS）
├── data/               # 数据文件
│   ├── questions.json  # 题库数据
│   ├── results.json    # 答题记录
│   └── dialogue_questions.json  # 对话题库
└── scripts/            # 辅助脚本
    └── migrate_keju.py # 数据迁移工具
```

## API 接口

### 题库相关

- `GET /api/banks` - 获取所有题库列表
- `GET /api/quiz/questions?bank={name}&limit={n}` - 获取题目（不含答案）
- `POST /api/agent/import` - Agent 导入题目
- `POST /api/agent/batch-check` - Agent 批量批改

### 答题相关

- `POST /api/quiz/check` - 检查答案
- `POST /api/quiz/check-translation` - 批改翻译题
- `POST /api/quiz/check-writing` - 批改写作题
- `POST /api/quiz/save` - 保存答题记录

### 分析相关

- `GET /api/analysis/wrong` - 获取错题列表
- `GET /api/analysis/wrong-questions` - 获取详细错题
- `GET /api/analysis/knowledge-points` - 知识点正确率分析
- `GET /api/analysis/overview` - 学习概览
- `POST /api/analysis/generate-review-exam` - 生成复习卷
- `GET /api/analysis/export-results` - 导出答题记录
- `GET /api/analysis/export-weakpoints` - 导出薄弱点分析

## 数据格式

题目 JSON 格式请参考 [FORMAT.md](FORMAT.md)。

Agent 操作指南请参考 [AGENTS.md](AGENTS.md)。

## 注意事项

1. **不要提交敏感数据**：`data/bot_credentials.json` 包含飞书 Bot 凭据，请勿上传到公开仓库
2. **数据备份**：定期备份 `data/` 目录下的文件
3. **生产部署**：建议使用 Gunicorn 或 uWSGI 替代 Flask 开发服务器

## License

MIT

# 项目介绍
本项目是一个面向PMP（项目管理专业人士）认证考试备考的智能学习辅助系统。它利用知识库中的PDF学习资料，实现每日知识卡片生成、自动出题测验、测验结果解析、学习周报和薄弱知识点分析等功能。系统可运行在本地环境（或局域网），不依赖公有云服务，支持多用户登录和数据隔离。

## 项目效果

> 以下截图展示系统主要功能模块：登陆页、每日知识卡片、学习测验、答题结果解析、学习统计及薄弱知识点分析。

![PMP备考助手-登陆模块](login-page.png)
![PMP备考助手-每日知识卡片](daily-cards-page.png)
![PMP备考助手-学习测验](quiz-page.png)
![PMP备考助手-学习统计](weekly-report-page.png)

## 技术栈

| 技术                | 用途                       |
|---------------------|----------------------------|
| Python 3.9          | 后端开发语言               |
| Streamlit           | Web 前端框架（UI 构建）    |
| SQLite              | 本地数据库（持久化存储）   |
| ChromaDB            | 向量数据库（本地本地知识索引） |
| PyMuPDF (fitz)      | PDF 文本解析               |
| sentence-transformers | 嵌入模型（语义检索用）    |
| kwiki-cli           | 知识库云端 API 调用工具    |
| venv                | Python 虚拟环境 (隔离依赖) |

## 项目结构

```
pmp-system/
├── app.py              # Streamlit 前端界面（5 个页面 + 路由）
├── auth.py             # 用户认证模块（登录、登出、权限控制）
├── db.py               # 数据库管理（Schema、初始化、密码验证）
├── dal.py              # 知识库云端 API 封装 (kwiki-cli)
├── services.py         # 核心业务逻辑（卡片生成、测验引擎、统计分析）
├── local_knowledge.py  # 本地知识库索引（PDF 解析 + 向量检索）
├── requirements.txt    # Python 依赖清单
├── run.bat             # Windows 一键启动脚本
├── .gitignore          # Git 忽略规则
├── local_data/         # 本地知识库数据（PDF 下载 + ChromaDB 索引）
├── venv/               # Python 虚拟环境
└── pmp_study.db        # SQLite 本地数据库文件
```

### 模块职责详解

#### 1. `app.py` — Web 前端
- **页面路由**: 每日卡片 (`render_cards_page`)、学习测验 (render_quiz_page)、学习统计 (render_stats_page)、薄弱点分析 (render_weakpoint_page)
- **用户认证集成**: 页面级权限检查、管理员功能（重置数据库）
- **Streamlit 兼容层**: 针对 Streamlit 1.12.0 的 API 降级处理

#### 2. `auth.py` — 认证模块
- **登录页面**: 用户名/密码表单，首次加载渲染
- **会话管理**: 基于 `st.session_state`
- **角色权限**: 管理员 (admin) vs 普通用户 (user)，仅管理员可见重置功能

#### 3. `db.py` — 数据库层
- **5 张表**: `users`, `cards`, `quizzes`, `quiz_answers`, `wrong_answer_bank`, `study_log`
- **密码哈希**: SHA-256 (带固定 salt)
- **数据迁移**: 旧表自动添加 `user_id` 列

#### 4. `dal.py` — 知识库云端访问层
- **kwiki-cli 子进程封装**: 所有 `kwiki` 子命令通过 `subprocess` 调用
- **自动重试**: 网络瞬断时最多重试 2 次
- **错误检测**: API 返回 `code: 100200` 时自动缩短 prompt 重试

#### 5. `services.py` — 业务核心
- **卡片生成** (`generate_daily_cards`): 调用云端 AI 提取知识点
- **测验引擎** (`generate_quiz`): 错题复习融入 + AI 出新题 → 逐行扫描解析
- **批改评分** (`grade_quiz`): 逐题比对 → 错题入库 + 艾宾浩斯排期
- **统计** (`get_weekly_stats`): 加权正确率 (总对/总题)
- **薄弱点** (`get_all_domain_accuracy`): 领域标准化 + 时效过滤

#### 6. `local_knowledge.py` — 本地知识索引
- **PDF 下载**: 从 WPS 知识库下载到 `local_data/pdfs/`
- **PyMuPDF 解析**: 提取可读文本，清理页码/页眉
- **ChromaDB 索引**: 500 char 重叠块 + all-MiniLM-L6-v2 嵌入
- **语义检索**: `search()` / `search_as_context()`

## 功能说明

### 用户认证
- 系统启动时展示登录页面，需要用户名和密码
- 管理员 (`admin/admin123`) 具有重置数据库的权限
- 普通用户 (`user/user123`) 只能访问学习功能
- 用户数据完全隔离，各自独立的卡片、测验和错题库

### 每日知识卡片
- 从知识库 PDF 中随机提取 N 个核心知识点
- 生成结构化的卡片（标题、知识领域、详细解释）
- 支持删除单张卡片

### 学习测验
- 指定知识领域或全领域出题
- 每道题包含 4 个选项、正确答案和详细解析
- 智能融入错题复习：测验中 40% 的题目来自错题库中到期复习的题目
- 批改结果标注"已攻克"或"再错"

### 学习统计
- 本周学习数据概览（卡片数、测验数、正确率）
- 每日正确率趋势图
- 正确率采用加权计算（总正确题数 / 总答题数）

### 薄弱知识分析
- 所有知识领域的正确率一览表
- 可设定统计时间范围（近 7 天 / 近 30 天 / 全部历史）
- 自动识别薄弱领域并给出 AI 复习建议
- 最少答题数过滤，排除统计噪音

### 错题库（艾宾浩斯记忆曲线）
- 答错的题目自动入库，记录题目、正确答案、解析
- 按记忆曲线排期复习：第 1 次错 1 天后出现，再错 3 天后，再错 7 天，再错 14 天
- 正确答对错题后不再出现

### 数据统计
- 卡片、测验、错题数据与用户数据本地化存储，不受网络限制
- 支持多用户登录，数据独立隔离

## 快速开始

### 环境要求
- Python 3.9+
- Node.js (kwiki-cli 依赖)
- Windows / macOS / Linux

### 安装步骤

```bash
# 1. 克隆仓库
git clone https://github.com/wgloia/pmp-system.git
cd pmp-system

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # macOS/Linux
# 或
venv\Scripts\activate.bat  # Windows

# 3. 安装依赖
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com

# 4. 初始化数据库
python db.py

# 5. 启动应用
streamlit run app.py
```

### 快速启动 (Windows)
双击 `run.bat` 即可自动完成环境安装和启动。

### 默认账号
| 用户名 | 密码 | 角色 |
|--------|------|------|
| admin  | admin123 | 管理员 |
| user   | user123 | 普通用户 |

## 许可证
MIT

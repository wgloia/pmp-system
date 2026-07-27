"""
业务服务层 — 卡片生成 / 测验引擎 / 统计分析 / 薄弱点诊断
"""
import json
import re
from datetime import datetime, timedelta

from db import get_db, PMP_DOMAINS
from dal import ask_knowledge_base


# ───────────────── 每日知识卡片 ─────────────────

def generate_daily_cards(n: int = 3) -> list[dict]:
    """
    生成 N 张每日知识卡片。
    调用 WPS 知识库 AI 问答，从 PDF 资料中提取核心知识点。
    """
    prompt = (
        f"请从PMP备考资料中，随机选择{n}个重要的核心知识点（必须来自不同知识领域），"
        "为每个知识点生成一张知识卡片。\n\n"
        "每张卡片严格按以下格式输出（卡片之间用 --- 分隔）：\n\n"
        "### 知识卡片N：知识点标题\n"
        "- **领域：**知识领域名\n"
        "- **内容：**知识点详细解释（2-3句话）\n\n"
        "---\n\n"
        f"知识领域必须是以下之一：{'、'.join(PMP_DOMAINS)}\n"
        "确保内容基于学习资料中的真实知识点，不要编造。"
    )
    raw = ask_knowledge_base(prompt, deep_think=True)
    return _parse_cards(raw, n)


def _parse_cards(raw: str, expected_n: int) -> list[dict]:
    """从 AI 回复中解析知识卡片（兼容多种输出格式）"""
    # 方法1：尝试 JSON
    json_match = re.search(r"\[.*\]", raw, re.DOTALL)
    if json_match:
        try:
            cards = json.loads(json_match.group())
            return cards[:expected_n]
        except json.JSONDecodeError:
            pass

    # 方法2：按 ### 或 --- 切分卡片块
    cards = []
    blocks = re.split(r"\n(?=###\s)", raw)
    if len(blocks) <= 1:
        blocks = re.split(r"\n---+\n", raw)

    for block in blocks[:expected_n]:
        block = block.strip()
        if not block or len(block) < 15:
            continue

        card = {"topic": "", "title": "", "content": ""}

        # 1) 从标题行提取：### 知识卡片N：领域-标题 / ### 卡片N：标题
        title_line = ""
        m = re.search(r"###\s*(?:知识)?卡片\d*\s*[：:]\s*(.+)", block)
        if m:
            title_line = m.group(1).strip()
            # 尝试拆分 "领域-标题" 或 "领域：标题"
            parts = re.split(r"\s*[-–—：:]\s*", title_line, maxsplit=1)
            if len(parts) == 2:
                card["topic"] = parts[0].strip()
                card["title"] = parts[1].strip()
            else:
                card["title"] = title_line

        # 2) 从正文中提取标签字段（兼容多种写法）
        label_patterns = {
            "topic": [r"\*\*(?:领域|知识点来源|所属领域|知识领域)[：:]\*\*\s*(.+)",
                      r"(?:领域|知识点来源|所属领域)[：:]\s*(.+)"],
            "content": [r"\*\*(?:内容|核心内容|知识点详解|详细解释)[：:]\*\*\s*(.+)",
                        r"(?:核心内容|知识点详解)[：:]\s*(.+)"],
        }

        for field, patterns in label_patterns.items():
            if not card[field]:
                for pat in patterns:
                    m = re.search(pat, block)
                    if m:
                        card[field] = m.group(1).strip()
                        break

        # 3) 兜底：标题已有但内容为空时，用 block 中非标签的正文部分
        if card["title"] and not card["content"]:
            # 去掉 ### 行和所有 **xxx：** 标签行，剩余作为内容
            body = re.sub(r"^###.*\n?", "", block, flags=re.MULTILINE)
            body = re.sub(r"\*\*[^*]+[：:]\*\*.*\n?", "", body)
            body = body.strip()
            if body:
                card["content"] = body[:300]

        # 4) 最终兜底
        if not card["title"] and not card["content"]:
            clean = re.sub(r"^###.*\n?", "", block, flags=re.MULTILINE)
            card["content"] = clean.strip()[:300]
            card["title"] = "待整理"

        if card["content"]:
            # 清理：去掉尾部 --- 分隔符
            card["content"] = re.sub(r"\n---+\s*$", "", card["content"]).strip()
            cards.append(card)

    while len(cards) < expected_n:
        cards.append({"topic": "解析不足", "title": f"第{len(cards)+1}张解析失败", "content": "请重新生成"})

    return cards[:expected_n]


def save_cards_to_db(cards: list[dict], user_id: int) -> int:
    """保存卡片到数据库，返回保存数量"""
    conn = get_db()
    today = datetime.now().strftime("%Y-%m-%d")
    count = 0
    for c in cards:
        conn.execute(
            "INSERT INTO cards (user_id, date, topic, title, content) VALUES (?,?,?,?,?)",
            (user_id, today, c.get("topic", ""), c.get("title", ""), c.get("content", "")),
        )
        count += 1
    conn.commit()
    conn.close()
    return count


def get_today_cards(user_id: int) -> list[dict]:
    """获取今日卡片"""
    conn = get_db()
    today = datetime.now().strftime("%Y-%m-%d")
    rows = conn.execute(
        "SELECT * FROM cards WHERE user_id=? AND date=? ORDER BY id", (user_id, today)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_card(card_id: int, user_id: int) -> bool:
    """删除单张卡片（仅限本人）"""
    conn = get_db()
    conn.execute("DELETE FROM cards WHERE id=? AND user_id=?", (card_id, user_id))
    conn.commit()
    deleted = conn.total_changes > 0
    conn.close()
    return deleted


# ───────────────── 学习内容测验 ─────────────────

def generate_quiz(user_id: int, topic: str = "", question_count: int = 5, review_ratio: float = 0.4) -> dict:
    """
    生成测验题目，自动融入错题复习。

    Args:
        user_id: 当前用户 ID
        topic: 知识领域，为空则综合
        question_count: 总题数
        review_ratio: 错题占比

    Returns:
        {"questions": [...], "quiz_id": int, "review_count": int}
    """
    today = datetime.now().strftime("%Y-%m-%d")

    # ── 1. 从错题库中抽取待复习题目 ──
    review_questions = _get_due_review_questions(user_id, topic, max(int(question_count * review_ratio), 1))
    review_count = len(review_questions)

    # ── 2. AI 生成新题目（补齐剩余数量） ──
    new_count = question_count - review_count
    new_questions = []
    if new_count > 0:
        topic_hint = f'关于"{topic}"' if topic else "覆盖多个知识领域"
        prompt = (
            f"请从PMP备考资料中，{topic_hint}，生成{new_count}道单项选择题。\n\n"
            "每道题严格按以下格式输出（题与题之间用 --- 分隔）：\n\n"
            "**领域：**知识领域名\n"
            "**题目：**题目内容\n"
            "A. 选项A\n"
            "B. 选项B\n"
            "C. 选项C\n"
            "D. 选项D\n"
            "**答案：**A\n"
            "**解析：**详细解析（引用资料原文）\n\n"
            "---\n\n"
            f"知识领域必须是以下之一：{'、'.join(PMP_DOMAINS)}\n"
            "确保每道题有且只有一个正确答案。"
        )
        raw = ask_knowledge_base(prompt, deep_think=False)
        new_questions = _parse_quiz(raw, new_count)

    # ── 2.5 补全 topic：用户指定了领域则直接使用，否则从题目文本推测 ──
    for q in new_questions:
        if topic:
            q["topic"] = topic  # 用户选了指定领域，直接记录
        elif not q.get("topic"):
            q["topic"] = _infer_topic_from_text(q.get("question", ""))

    # ── 3. 合并：错题在前（标记为复习），新题在后 ──
    questions = review_questions + new_questions

    conn = get_db()
    topics = set(q.get("topic", "未分类") for q in questions)
    conn.execute(
        "INSERT INTO quizzes (user_id, date, topic, questions, total, correct, score) VALUES (?,?,?,?,?,0,0)",
        (user_id, today, "/".join(topics), json.dumps(questions, ensure_ascii=False), len(questions)),
    )
    quiz_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    conn.close()

    return {
        "quiz_id": quiz_id,
        "questions": questions,
        "total": len(questions),
        "review_count": review_count,
    }


def _get_due_review_questions(user_id: int, topic: str = "", limit: int = 3) -> list[dict]:
    """从错题库中获取到期待复习的题目"""
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_db()

    if topic:
        rows = conn.execute(
            """SELECT *, MAX(review_count) FROM wrong_answer_bank
               WHERE user_id=? AND next_review <= ? AND topic = ?
               GROUP BY question
               ORDER BY next_review ASC, review_count DESC
               LIMIT ?""",
            (user_id, today, topic, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT *, MAX(review_count) FROM wrong_answer_bank
               WHERE user_id=? AND next_review <= ?
               GROUP BY question
               ORDER BY next_review ASC, review_count DESC
               LIMIT ?""",
            (user_id, today, limit),
        ).fetchall()
    conn.close()

    questions = []
    for r in rows:
        try:
            options = json.loads(r["options_json"])
        except (json.JSONDecodeError, TypeError):
            options = {}
        questions.append({
            "topic": r["topic"] + " (复习)",
            "question": r["question"],
            "options": options,
            "answer": r["correct_answer"],
            "explanation": r["explanation"] or "",
            "from_review": True,  # 标记为错题复习
            "review_count": r["review_count"],
        })

    return questions


def _parse_quiz(raw: str, expected_n: int) -> list[dict]:
    """逐行扫描解析测验题目，稳健处理 AI 各种输出格式"""
    # JSON 尝试
    json_match = re.search(r"\[.*\]", raw, re.DOTALL)
    if json_match:
        try:
            parsed = json.loads(json_match.group())
            if isinstance(parsed, list) and len(parsed) > 0:
                return parsed[:expected_n]
        except json.JSONDecodeError:
            pass

    # ── 逐行扫描：划分每道题的起止位置 ──
    lines = raw.split("\n")
    # 找到所有"题目起点"行号：以数字+英文句号开头，如 "1. xxx" 或 "1．xxx"
    q_starts = []
    for i, line in enumerate(lines):
        if re.match(r"^\s*\d+[\.．]\s", line.strip()):
            q_starts.append(i)

    if not q_starts:
        # 没有编号行，尝试按 ### 标题切分
        for i, line in enumerate(lines):
            if re.match(r"^###\s*(?:单项选择|单选|选择)?(?:题目|问题|题|第\d+题)", line.strip()):
                q_starts.append(i)

    if not q_starts:
        # 再不行，按 --- 切分
        raw_parts = re.split(r"\n---+\n", raw)
        blocks = [p for p in raw_parts if len(p.strip()) >= 20]
        if len(blocks) >= 2:
            # 创建一个伪 raw，给每块加上编号
            numbered_raw = ""
            for j, b in enumerate(blocks):
                numbered_raw += f"{j+1}. {b.strip()}\n\n"
            return _parse_quiz(numbered_raw, expected_n)

    questions = []

    for idx, start_line in enumerate(q_starts[:expected_n]):
        end_line = q_starts[idx + 1] if idx + 1 < len(q_starts) else len(lines)
        block_lines = lines[start_line:end_line]
        block_text = "\n".join(block_lines)

        q = {"topic": "", "question": "", "options": {}, "answer": "", "explanation": ""}

        # ── 提取题目文本 ──
        question_parts = []
        in_question = False
        for line in block_lines:
            ls = line.strip()
            if re.match(r"^\s*\d+[\.．]\s", ls):
                question_parts.append(re.sub(r"^\s*\d+[\.．]\s*", "", ls))
                in_question = True
                continue
            if not in_question:
                continue
            if re.match(r"^[A-D][\.．、\)）]\s", ls):
                break  # 遇到选项，停止
            if re.match(r"^(?:答案|解析|解释|说明)[：:]", ls):
                break  # 遇到答案/解析，停止
            if ls:
                question_parts.append(ls)
        q["question"] = "\n".join(question_parts).strip()

        # ── 提取选项 ──
        for opt_char in "ABCD":
            for line in block_lines:
                m = re.match(rf"^{opt_char}[\.．、\)）]\s*(.+)", line.strip())
                if m:
                    q["options"][opt_char] = m.group(1).strip()
                    break

        # ── 提取答案 ──
        for line in block_lines:
            m = re.search(r"(?:\*\*)?答案(?:\*\*)?[：:]\s*([A-D])", line.strip())
            if m:
                q["answer"] = m.group(1).strip()
                break
        if not q["answer"]:
            for line in block_lines:
                m = re.search(r"正确[答案选项]*[：:]\s*([A-D])", line.strip())
                if m:
                    q["answer"] = m.group(1).strip()
                    break

        # ── 提取解析 ──
        expl_lines = []
        in_expl = False
        for line in block_lines:
            ls = line.strip()
            if re.match(r"^(?:\*\*)?(?:解析|解释|说明)(?:\*\*)?[：:]", ls):
                expl_lines.append(re.sub(r"^(?:\*\*)?(?:解析|解释|说明)(?:\*\*)?[：:]\s*", "", ls))
                in_expl = True
                continue
            if in_expl:
                if re.match(r"^\s*\d+[\.．]\s|^---", ls):
                    break
                if ls:
                    expl_lines.append(ls)
        q["explanation"] = (" ".join(expl_lines)).strip()[:500]

        # ── 兜底 ──
        if not q["question"]:
            q["question"] = block_text[:200]
        if not q["answer"]:
            q["answer"] = "?"

        questions.append(q)

    while len(questions) < expected_n:
        questions.append({
            "topic": "解析不足", "question": "题目解析失败，请重新生成",
            "options": {"A": "", "B": "", "C": "", "D": ""},
            "answer": "?", "explanation": ""
        })

    return questions[:expected_n]

    while len(questions) < expected_n:
        questions.append({
            "topic": "解析不足", "question": "题目解析失败，请重新生成",
            "options": {"A": "", "B": "", "C": "", "D": ""},
            "answer": "?", "explanation": ""
        })

    return questions[:expected_n]


def grade_quiz(user_id: int, quiz_id: int, user_answers: dict[int, str]) -> dict:
    """
    批改测验，存入答题记录。

    Args:
        user_id: 当前用户 ID
        quiz_id: 测验 ID
        user_answers: {题号(0-based): "A"}

    Returns:
        {"score": 80.0, "correct": 4, "total": 5, "details": [...]}
    """
    conn = get_db()
    quiz = conn.execute("SELECT * FROM quizzes WHERE id=?", (quiz_id,)).fetchone()
    if not quiz:
        conn.close()
        return {"error": "测验不存在"}

    questions = json.loads(quiz["questions"])
    details = []
    correct_count = 0

    for i, q in enumerate(questions):
        user_ans = user_answers.get(i, "").upper()
        is_correct = user_ans == q["answer"].upper()
        if is_correct:
            correct_count += 1

        result = conn.execute(
            """INSERT INTO quiz_answers
               (user_id, quiz_id, topic, question, user_answer, correct_answer, is_correct, explanation)
               VALUES (?,?,?,?,?,?,?,?)""",
            (user_id, quiz_id, q.get("topic", ""), q["question"],
             user_ans, q["answer"], int(is_correct), q.get("explanation", "")),
        )
        answer_id = result.lastrowid

        # 答错的题加入错题库（基于艾宾浩斯记忆曲线排期）
        if not is_correct:
            today = datetime.now().strftime("%Y-%m-%d")
            # 查找该题是否已有错题记录，获取review_count
            existing = conn.execute(
                "SELECT review_count FROM wrong_answer_bank WHERE question=? ORDER BY review_count DESC LIMIT 1",
                (q["question"],),
            ).fetchone()
            review_count = (existing["review_count"] + 1) if existing else 0
            # 记忆曲线间隔：0次→1天, 1次→3天, 2次→7天, 3+次→14天
            intervals = [1, 3, 7, 14]
            days = intervals[min(review_count, len(intervals) - 1)]
            next_review = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
            conn.execute(
                """INSERT INTO wrong_answer_bank
                   (user_id, quiz_answer_id, topic, question, options_json, correct_answer, explanation,
                    review_count, next_review, last_reviewed)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (user_id, answer_id, q.get("topic", ""), q["question"],
                 json.dumps(q.get("options", {}), ensure_ascii=False),
                 q["answer"], q.get("explanation", ""),
                 review_count, next_review, today),
            )

            conn.execute(
                "INSERT INTO study_log (user_id, date, activity, duration_min, detail) VALUES (?,?,?,?,?)",
                (user_id, today, "错题记录", 0, f"领域:{q.get('topic','')} 题目:{q['question'][:50]}"),
            )

        details.append({
            "index": i,
            "topic": q.get("topic", ""),
            "question": q["question"],
            "options": q.get("options", {}),
            "user_answer": user_ans,
            "correct_answer": q["answer"],
            "is_correct": is_correct,
            "explanation": q.get("explanation", ""),
            "from_review": q.get("from_review", False),
        })

    total = len(questions)
    score = round(correct_count / total * 100, 1) if total > 0 else 0

    conn.execute(
        "UPDATE quizzes SET correct=?, score=? WHERE id=?",
        (correct_count, score, quiz_id),
    )
    conn.commit()
    conn.close()

    return {"quiz_id": quiz_id, "score": score, "correct": correct_count, "total": total, "details": details}


# ───────────────── 每周学习统计 ─────────────────

def get_weekly_stats(user_id: int) -> dict:
    """获取本周学习统计数据（加权正确率 = 总正确题数 / 总答题数）"""
    conn = get_db()
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    week_start = monday.strftime("%Y-%m-%d")
    today_str = today.strftime("%Y-%m-%d")

    cards = conn.execute(
        "SELECT COUNT(*) as n FROM cards WHERE user_id=? AND date BETWEEN ? AND ?",
        (user_id, week_start, today_str),
    ).fetchone()["n"]

    quiz_stats = conn.execute(
        "SELECT COUNT(*) as n,"
        " COALESCE(SUM(correct), 0) as total_correct,"
        " COALESCE(SUM(total), 0) as total_questions"
        " FROM quizzes WHERE user_id=? AND date BETWEEN ? AND ?",
        (user_id, week_start, today_str),
    ).fetchone()

    total_correct = quiz_stats["total_correct"]
    total_questions = quiz_stats["total_questions"]
    weighted_score = round(total_correct / total_questions * 100, 1) if total_questions > 0 else 0

    trend_rows = conn.execute(
        "SELECT date, SUM(correct) as day_correct, SUM(total) as day_total, COUNT(*) as quiz_count"
        " FROM quizzes WHERE user_id=? AND date BETWEEN ? AND ?"
        " GROUP BY date ORDER BY date",
        (user_id, week_start, today_str),
    ).fetchall()

    conn.close()

    daily_trend = []
    for r in trend_rows:
        ratio = round(r["day_correct"] / r["day_total"] * 100, 1) if r["day_total"] > 0 else 0
        daily_trend.append({
            "date": r["date"],
            "avg_score": ratio,
            "quiz_count": r["quiz_count"],
        })

    return {
        "week_start": week_start,
        "week_end": today_str,
        "cards_generated": cards,
        "quiz_count": quiz_stats["n"],
        "avg_score": weighted_score,
        "daily_trend": daily_trend,
    }


def _infer_topic_from_text(text: str) -> str:
    """从题目文本推测知识领域（用于 topic 为空时的补救）"""
    if not text:
        return "未分类"
    keyword_map = {
        "整合": "整合管理", "章程": "整合管理", "整体": "整合管理",
        "范围": "范围管理", "WBS": "范围管理", "需求": "范围管理", "变更": "整合管理",
        "进度": "时间管理", "工期": "时间管理", "时间": "时间管理",
        "成本": "成本管理", "预算": "成本管理", "费用": "成本管理",
        "质量": "质量管理", "缺陷": "质量管理",
        "团队": "人力资源管理", "成员": "人力资源管理", "T型": "人力资源管理",
        "资源": "人力资源管理", "人员": "人力资源管理", "冲突": "人力资源管理",
        "沟通": "沟通管理", "报告": "沟通管理", "会议": "沟通管理",
        "干系": "干系人管理", "利益": "干系人管理",
        "风险": "风险管理", "不确定": "风险管理", "应对": "风险管理",
        "采购": "采购管理", "合同": "采购管理", "供应商": "采购管理", "外包": "采购管理",
        "法规": "干系人管理", "合规": "干系人管理", "法律": "干系人管理",
        "安全": "风险管理", "数据": "整合管理",
    }
    for kw, domain in keyword_map.items():
        if kw in text:
            return domain
    return "综合"


# ───────────────── 薄弱知识点分析 ─────────────────

def _normalize_topic(raw_topic: str) -> str:
    """将 AI 返回的非标准领域名映射到 PMP 十大领域"""
    if not raw_topic or raw_topic in ("未分类", "涵盖多个知识领域", "多个领域"):
        return "综合"
    # 关键词 → 标准领域名
    keyword_map = {
        "整合": "整合管理", "整体": "整合管理",
        "范围": "范围管理", "需求": "范围管理",
        "时间": "时间管理", "进度": "时间管理", "工期": "时间管理",
        "成本": "成本管理", "费用": "成本管理", "预算": "成本管理",
        "质量": "质量管理", "测试": "质量管理",
        "人力": "人力资源管理", "人员": "人力资源管理", "资源": "人力资源管理",
        "团队": "人力资源管理", "T型": "人力资源管理",
        "沟通": "沟通管理", "干系": "干系人管理", "利益": "干系人管理",
        "风险": "风险管理", "不确定": "风险管理",
        "采购": "采购管理", "合同": "采购管理", "供应商": "采购管理",
        "业务环境": "干系人管理", "合规": "干系人管理", "法规": "干系人管理",
    }
    for kw, domain in keyword_map.items():
        if kw in raw_topic:
            return domain
    return raw_topic


def get_all_domain_accuracy(user_id: int, days: int = 0) -> dict:
    """
    获取所有知识领域的正确率统计。

    Args:
        user_id: 当前用户 ID
        days: 统计最近 N 天的数据，0 表示全部历史

    Returns:
        {"domains": [...], "summary": {...}}
    """
    conn = get_db()
    if days > 0:
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        rows = conn.execute(
            "SELECT topic, COUNT(*) as total, SUM(is_correct) as correct"
            " FROM quiz_answers WHERE user_id=? AND created_at >= ?"
            " GROUP BY topic ORDER BY total DESC",
            (user_id, cutoff),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT topic, COUNT(*) as total, SUM(is_correct) as correct"
            " FROM quiz_answers WHERE user_id=?"
            " GROUP BY topic ORDER BY total DESC",
            (user_id,),
        ).fetchall()
    conn.close()

    # 按标准化领域合并统计
    domain_stats = {}
    for r in rows:
        norm = _normalize_topic(r["topic"])
        if norm not in domain_stats:
            domain_stats[norm] = {"total": 0, "correct": 0}
        domain_stats[norm]["total"] += r["total"]
        domain_stats[norm]["correct"] += r["correct"]

    # 构建返回列表
    domains = []
    total_questions = 0
    total_correct = 0
    for domain, stats in sorted(domain_stats.items(), key=lambda x: -x[1]["total"]):
        acc = round(stats["correct"] / stats["total"] * 100, 1) if stats["total"] > 0 else 0
        domains.append({
            "topic": domain,
            "total_questions": stats["total"],
            "correct": stats["correct"],
            "wrong": stats["total"] - stats["correct"],
            "accuracy": acc / 100,
            "accuracy_pct": f"{acc}%",
            "is_weak": acc < 60,
        })
        total_questions += stats["total"]
        total_correct += stats["correct"]

    overall_acc = round(total_correct / total_questions * 100, 1) if total_questions > 0 else 0

    return {
        "domains": domains,
        "summary": {
            "total_questions": total_questions,
            "total_correct": total_correct,
            "overall_accuracy": overall_acc,
            "overall_accuracy_pct": f"{overall_acc}%",
            "days": days if days > 0 else "全部",
        },
    }


def analyze_weak_points(user_id: int, threshold: float = 0.6, days: int = 0) -> list[dict]:
    """
    分析薄弱知识点。

    Args:
        user_id: 当前用户 ID
        threshold: 正确率阈值，低于此值视为薄弱
        days: 统计最近 N 天，0 表示全部

    Returns:
        薄弱知识点列表，按错误率从高到低排列
    """
    all_data = get_all_domain_accuracy(user_id, days=days)
    weak = [d for d in all_data["domains"] if d["accuracy"] < threshold and d["total_questions"] >= 3]
    # 按正确率从低到高排，但只列出题量 >= 3 的领域（排除统计噪音）
    return sorted(weak, key=lambda x: x["accuracy"])


def get_review_suggestions(weak_points: list[dict]) -> str:
    """基于薄弱点，通过 AI 问答获取针对性复习建议"""
    if not weak_points:
        return "目前没有明显的薄弱领域，继续保持！"

    topics_str = "、".join(
        f"{wp['topic']}(正确率{wp['accuracy_pct']})" for wp in weak_points[:5]
    )
    prompt = (
        f"我在PMP备考中，以下知识领域的测验正确率较低：{topics_str}。\n"
        "请针对这些薄弱领域，给出：\n"
        "1. 每个领域的核心概念复习要点\n"
        "2. 容易混淆的知识点对比\n"
        "3. 建议的学习顺序和备考技巧\n"
        "回答简洁有条理，每个领域不超过3个要点。"
    )
    return ask_knowledge_base(prompt, deep_think=True)

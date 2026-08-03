"""
PMP 备考辅助系统 — Web 前端 (Streamlit) · Moebius 极繁主义主题
启动: streamlit run app.py
"""
import json
import streamlit as st
import pandas as pd
from datetime import datetime

from db import init_db, get_db, PMP_DOMAINS, reset_db
from services import (
    generate_daily_cards, save_cards_to_db, get_today_cards, delete_card,
    generate_quiz, grade_quiz,
    get_weekly_stats,
    get_all_domain_accuracy,
    analyze_weak_points, get_review_suggestions,
    add_note, get_notes, delete_note, update_note,
)
from auth import require_login, get_current_user, is_admin, logout
from moebius_theme import MOEBIUS_CSS

st.set_page_config(
    page_title="PMP 备考助手 · 知识圣殿",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 注入 Moebius 极繁主义主题
st.markdown(MOEBIUS_CSS, unsafe_allow_html=True)

# 补充隐藏 Streamlit 默认 UI
st.markdown("""
<style>
    footer {visibility: hidden;}
    .stDeployButton {display: none;}
    [data-testid="stDecoration"] {display: none;}
</style>
""", unsafe_allow_html=True)

# ── 登录检查（未登录时渲染登录页，阻止后续代码） ──
init_db()
user = require_login()
user_id = user["id"]


# ═══════════════════════════ 页面实现 ═══════════════════════════

def render_cards_page():
    st.header("每日知识卡片")
    st.caption("从 PMP 备考资料中提炼核心知识点，每日为你呈现智慧结晶")

    col1, col2, col3 = st.columns([1, 1.5, 4])
    with col1:
        n = st.selectbox("卡片数量", [3, 5, 10], index=0)
    with col2:
        st.write("")
        st.write("")
        gen_btn = st.button("✦ 生成今日卡片")

    if gen_btn:
        with st.spinner("知识精灵正在为萃取智慧精华..."):
            cards = generate_daily_cards(n, user_id)
            saved = save_cards_to_db(cards, user_id)
            st.success(f"已为你准备 {saved} 张知识卡片")
            st.experimental_rerun()

    cards = get_today_cards(user_id)
    if not cards:
        st.info("今天还没有生成卡片，点击上方按钮开启今日知识之旅")
        return

    st.markdown("---")
    for i, c in enumerate(cards, 1):
        card_id = c["id"]
        # Moebius 装饰卡片 HTML
        card_html = f"""
        <div class="moebius-card">
            <div class="card-number">◈ 知识碎片 第 {i} 号 ◈</div>
            <span class="card-domain">{c['topic']}</span>
            <div class="card-title">{c['title']}</div>
            <div class="card-divider">· · · ✦ · · ·</div>
            <div class="card-content">{c['content']}</div>
        </div>
        """
        col_card, col_btn = st.columns([25, 1])
        with col_card:
            st.markdown(card_html, unsafe_allow_html=True)
        with col_btn:
            if st.button("✧", key=f"del_card_{card_id}", help="删除此卡片"):
                delete_card(card_id, user_id)
                st.experimental_rerun()


def render_quiz_page():
    st.header("试炼之殿")
    st.caption("AI 出题 · 即时批改 · 错题归库 · 记忆循环")

    # 测验配置
    col1, col2, col3 = st.columns(3)
    with col1:
        topic = st.selectbox("知识领域（留空 = 综合全部领域）", [""] + PMP_DOMAINS)
    with col2:
        q_count = st.selectbox("题目数量", [5, 10, 15], index=0)
    with col3:
        st.write("")
        st.write("")

    gen_btn = st.button("🎲 生成测验")

    # Session state
    if "quiz" not in st.session_state:
        st.session_state.quiz = None
    if "graded" not in st.session_state:
        st.session_state.graded = None

    if gen_btn:
        with st.spinner("AI 正在根据学习资料出题..."):
            st.session_state.quiz = generate_quiz(user_id, topic, q_count)
            st.session_state.graded = None
            st.experimental_rerun()

    quiz = st.session_state.quiz
    if not quiz:
        st.info("📝 点击上方按钮生成一份测验")
        return

    st.markdown("---")
    review_n = quiz.get("review_count", 0)
    new_n = quiz["total"] - review_n
    title = f"测验 #{quiz['quiz_id']}（共 {quiz['total']} 题"
    if review_n > 0:
        title += f"，含 {review_n} 道错题复习"
    title += "）"
    st.subheader(title)

    # 答题表单
    answers = {}
    with st.form("quiz_form"):
        for i, q in enumerate(quiz["questions"]):
            is_review = q.get("from_review", False)
            badge = " 🔄复习" if is_review else ""
            st.markdown(f"**{i + 1}. [{q.get('topic', '未分类')}]{badge} {q['question']}**")
            options = q.get("options", {})
            label_map = {}
            for k, v in options.items():
                label_map[f"{k}: {v}"] = k
            choice = st.radio(
                f"第 {i+1} 题",
                list(label_map.keys()),
                index=0,
                key=f"quiz_q_{quiz['quiz_id']}_{i}",
            )
            if choice:
                answers[i] = label_map[choice]
            st.caption("---")

        submitted = st.form_submit_button("📤 提交答案")

    if submitted and answers:
        with st.spinner("正在批改..."):
            st.session_state.graded = grade_quiz(user_id, quiz["quiz_id"], answers)
            st.experimental_rerun()

    # 结果展示
    graded = st.session_state.graded
    if graded:
        st.markdown("---")
        st.subheader("📊 测验结果")
        score = graded["score"]
        color = "green" if score >= 80 else "orange" if score >= 60 else "red"
        st.markdown(
            f"### 得分：:{color}[{score}%]  "
            f"（{graded['correct']} / {graded['total']} 正确）"
        )

        st.markdown("---")
        for d in graded.get("details", []):
            is_rev = d.get("from_review", False)
            icon = "✅" if d["is_correct"] else "❌"
            rev_tag = " 🔄已攻克" if (is_rev and d["is_correct"]) else (" 🔄再错" if (is_rev and not d["is_correct"]) else "")
            with st.expander(
                f"{icon} 第 {d['index']+1} 题 [{d['topic']}]{rev_tag} {d['question'][:40]}...",
                expanded=not d["is_correct"],
            ):
                st.markdown(f"**题目：** {d['question']}")
                for k, v in d.get("options", {}).items():
                    mark = ""
                    if k == d["correct_answer"]:
                        mark = " ✅（正确答案）"
                    elif k == d["user_answer"] and not d["is_correct"]:
                        mark = " ❌（你的答案）"
                    st.markdown(f"- {k}：{v}{mark}")

                st.markdown("---")
                st.markdown(f"**📖 解析：** {d['explanation']}")


def render_stats_page():
    st.header("修习录")

    stats = get_weekly_stats(user_id)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("本周生成卡片", stats["cards_generated"], "张")
    with col2:
        st.metric("本周完成测验", stats["quiz_count"], "次")
    with col3:
        st.metric("平均正确率", f"{stats['avg_score']}%")

    st.markdown("---")

    if stats["daily_trend"]:
        st.subheader("每日正确率趋势")
        df = pd.DataFrame(stats["daily_trend"])
        df_chart = df.rename(columns={"date": "日期", "avg_score": "平均正确率", "quiz_count": "测验次数"})
        st.bar_chart(df_chart.set_index("日期")["平均正确率"], use_container_width=True)

        st.subheader("每日测验次数")
        st.bar_chart(df_chart.set_index("日期")["测验次数"], use_container_width=True)


def render_weakpoint_page():
    st.header("明镜台")

    col1, col2, col3 = st.columns(3)
    with col1:
        time_range = st.selectbox(
            "统计时间范围",
            ["全部历史", "最近 7 天", "最近 30 天"],
            index=0,
        )
    with col2:
        threshold = st.slider(
            "薄弱阈值（正确率低于此值）",
            0.0, 1.0, 0.6, 0.05,
        )
    with col3:
        min_questions = st.number_input("最少答题数（过滤噪音）", 1, 20, 3)

    # 时间范围 → days 参数
    days_map = {"全部历史": 0, "最近 7 天": 7, "最近 30 天": 30}
    days = days_map[time_range]

    all_data = get_all_domain_accuracy(user_id, days=days)

    if not all_data["domains"]:
        st.info("还没有答题记录，先去做几套测验吧！")
        return

    # ── 总体概览 ──
    summary = all_data["summary"]
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("总答题数", summary["total_questions"])
    with col2:
        st.metric("总正确题数", summary["total_correct"])
    with col3:
        st.metric("加权正确率", summary["overall_accuracy_pct"])

    st.markdown("---")

    # ── 全领域正确率表 ──
    st.subheader("各领域正确率一览")
    df_all = pd.DataFrame(all_data["domains"])
    if not df_all.empty:
        df_show = df_all[["topic", "total_questions", "correct", "wrong", "accuracy_pct"]]
        df_show.columns = ["知识领域", "答题数", "正确", "错误", "正确率"]
        # 给薄弱行加颜色标记
        def color_row(row):
            is_weak = row["正确率"] == "0.0%" or float(row["正确率"].rstrip("%")) < 60
            return ["background-color: #fff3cd" if is_weak else "" for _ in row]
        styled = df_show.style.apply(color_row, axis=1)
        st.dataframe(styled)

    st.markdown("---")

    # ── 薄弱领域分析 ──
    weak = [d for d in all_data["domains"] if d["accuracy"] < threshold and d["total_questions"] >= min_questions]
    weak = sorted(weak, key=lambda x: x["accuracy"])

    if not weak:
        st.success("🎉 没有符合标准的薄弱领域！继续保持。")
    else:
        st.subheader(f"⚠️ 薄弱领域（正确率 < {int(threshold*100)}%，至少 {min_questions} 题）")
        df_weak = pd.DataFrame(weak)
        df_weak_display = df_weak[["topic", "total_questions", "correct", "wrong", "accuracy_pct"]]
        df_weak_display.columns = ["知识领域", "答题数", "正确", "错误", "正确率"]
        st.dataframe(df_weak_display)

        st.markdown("---")
        st.subheader("🤖 AI 针对性复习建议")

        if st.button("生成复习建议"):
            with st.spinner("AI 正在分析薄弱点并生成建议..."):
                suggestion = get_review_suggestions(weak)
                st.markdown(suggestion)


def render_notes_page():
    st.header("知识手札")
    st.caption("记录学习中的关键知识点，构建个人知识体系")

    # 搜索与筛选
    col1, col2 = st.columns([3, 1])
    with col1:
        search = st.text_input("搜索笔记", placeholder="输入关键词搜索标题或内容...")
    with col2:
        filter_topic = st.selectbox("筛选领域", ["全部"] + PMP_DOMAINS, index=0)

    # 新建笔记
    with st.expander("✦ 记录新知识", expanded=False):
        col_a, col_b = st.columns(2)
        with col_a:
            new_topic = st.selectbox("所属领域", PMP_DOMAINS, key="note_topic")
        with col_b:
            new_title = st.text_input("知识点标题", key="note_title", placeholder="简洁概括")
        new_content = st.text_area("详细内容", key="note_content", height=120,
                                   placeholder="记录关键概念、公式、记忆要点...")
        if st.button("保存笔记"):
            if new_title.strip() and new_content.strip():
                add_note(user_id, new_topic, new_title.strip(), new_content.strip())
                st.success("知识已保存 ✦")
                st.experimental_rerun()
            else:
                st.warning("标题和内容不能为空")

    st.markdown("---")

    # 查询逻辑
    topic_filter = "" if filter_topic == "全部" else filter_topic
    notes = get_notes(user_id, topic=topic_filter, search=search.strip())

    if not notes:
        st.info("暂无笔记，点击上方「记录新知识」开始书写")
        return

    st.caption(f"共 {len(notes)} 条笔记")

    for note in notes:
        # Moebius 卡片风格
        note_html = f"""
        <div class="moebius-card">
            <div class="card-number">◈ {note['date']} ◈</div>
            <span class="card-domain">{note['topic']}</span>
            <div class="card-title">{note['title']}</div>
            <div class="card-divider">· · · ✦ · · ·</div>
            <div class="card-content">{note['content']}</div>
        </div>
        """
        col_note, col_del = st.columns([25, 1])
        with col_note:
            st.markdown(note_html, unsafe_allow_html=True)
        with col_del:
            if st.button("✧", key=f"del_note_{note['id']}", help="删除此笔记"):
                delete_note(note["id"], user_id)
                st.experimental_rerun()


# ── 侧边栏 ──
with st.sidebar:
    st.title("知识圣殿")
    st.caption("PMP 备考辅助系统")

    role_text = "圣殿守护者" if user['role'] == 'admin' else "求道者"
    st.markdown(f"✦ **{user['username']}** · {role_text}")

    page = st.radio(
        "✦ 知识圣殿 ✦",
        ["◈ 每日知识卡片", "◆ 试炼之殿", "◈ 修习录", "◆ 明镜台", "✦ 知识手札"],
    )

    st.markdown("---")

    if st.button("离开圣殿"):
        logout()

    if is_admin():
        st.markdown("---")
        st.caption("◆ 圣殿守护者权限")
        if st.button("重置知识宝库"):
            reset_db()
            st.success("知识宝库已清空，等待重新积累智慧")
            st.experimental_rerun()


# ── 页面路由 ──
if "知识卡片" in page:
    render_cards_page()
elif "试炼" in page:
    render_quiz_page()
elif "修习" in page:
    render_stats_page()
elif "明镜" in page:
    render_weakpoint_page()
elif "手札" in page:
    render_notes_page()

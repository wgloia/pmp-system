"""
PMP 备考辅助系统 — Web 前端 (Streamlit)
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
)
from auth import require_login, get_current_user, is_admin, logout

st.set_page_config(
    page_title="PMP 备考助手",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 隐藏 Streamlit 默认英文 UI
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
    st.header("🃏 每日知识卡片")
    st.caption("基于 WPS 知识库 AI，从 PMP 备考资料中提取核心知识点，生成每日复习卡片")

    col1, col2, col3 = st.columns([1, 1.5, 4])
    with col1:
        n = st.selectbox("卡片数量", [3, 5, 10], index=0)
    with col2:
        st.markdown("&nbsp;")  # 占位补偿 selectbox 的 label 高度
        gen_btn = st.button("✨ 生成今日卡片")

    if gen_btn:
        with st.spinner("正在调用知识库 AI 生成卡片..."):
            cards = generate_daily_cards(n)
            saved = save_cards_to_db(cards, user_id)
            st.success(f"已生成并保存 {saved} 张卡片")
            st.experimental_rerun()

    # 展示今日卡片
    cards = get_today_cards(user_id)
    if not cards:
        st.info("🃏 今天还没有生成卡片，点击上方按钮生成")
        return

    st.markdown("---")
    for i, c in enumerate(cards, 1):
        card_id = c["id"]
        col_card, col_btn = st.columns([20, 1])
        with col_card:
            with st.expander(f"卡片 {i} — {c['topic']}：{c['title']}", expanded=(i == 1)):
                st.markdown(f"**知识点：** {c['title']}")
                st.markdown(f"**所属领域：** {c['topic']}")
                st.markdown(f"**详解：** {c['content']}")
        with col_btn:
            st.write("")  # 垂直对齐
            if st.button("🗑️", key=f"del_card_{card_id}", help="删除此卡片"):
                delete_card(card_id, user_id)
                st.experimental_rerun()


def render_quiz_page():
    st.header("📝 学习测验")
    st.caption("基于 WPS 知识库 AI，根据学习内容自动出题，提交后即时反馈正确答案与解析")

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
    st.header("📊 每周学习统计")

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
    st.header("🔍 薄弱知识点分析")

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


# ── 侧边栏 ──
with st.sidebar:
    st.title("📋 PMP 备考助手")
    st.caption("基于 WPS 知识库 AI 能力")

    # 用户信息
    st.markdown(f"👤 **{user['username']}** ({'管理员' if user['role'] == 'admin' else '普通用户'})")

    page = st.radio(
        "导航菜单",
        ["🃏 每日知识卡片", "📝 学习测验", "📊 学习统计", "🔍 薄弱点分析"],
    )

    st.markdown("---")

    if st.button("🚪 退出登录"):
        logout()

    # 管理员专属：重置数据库
    if is_admin():
        st.markdown("---")
        st.caption("🔒 管理员操作")
        if st.button("🗑 重置数据库（清空所有数据）"):
            reset_db()
            st.success("数据库已重置，所有数据已清空")
            st.experimental_rerun()


# ── 页面路由 ──
if page == "🃏 每日知识卡片":
    render_cards_page()
elif page == "📝 学习测验":
    render_quiz_page()
elif page == "📊 学习统计":
    render_stats_page()
elif page == "🔍 薄弱点分析":
    render_weakpoint_page()

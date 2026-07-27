"""
认证模块 — 登录/登出/会话管理
"""
import streamlit as st
from db import verify_login, init_db


def require_login() -> dict:
    """
    确保当前会话已登录，返回用户信息。
    未登录时渲染登录界面并阻止后续代码执行。
    """
    # 已登录则直接返回
    if "user" in st.session_state and st.session_state.user:
        return st.session_state.user

    # 渲染登录界面
    render_login_page()
    st.stop()  # 阻止后续页面渲染
    return {}  # unreachable, satisfies type checker


def render_login_page():
    """渲染登录界面"""
    # 隐藏 Streamlit 默认 UI
    st.markdown("""
    <style>
        footer {visibility: hidden;}
        .stDeployButton {display: none;}
        [data-testid="stSidebar"] {display: none;}
        [data-testid="stToolbar"] {display: none;}
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.title("📋 PMP 备考助手")
        st.caption("登录后开始学习")

        username = st.text_input("用户名", placeholder="请输入用户名")
        password = st.text_input("密码", type="password", placeholder="请输入密码")

        if st.button("登录"):
            init_db()
            user = verify_login(username, password)
            if user:
                st.session_state.user = user
                st.session_state.logged_in = True
                st.success(f"欢迎回来，{user['username']}！")
                st.experimental_rerun()
            else:
                st.error("用户名或密码错误")

        st.markdown("---")
        st.caption("默认账号：admin / admin123（管理员）")
        st.caption("默认账号：user / user123（普通用户）")


def get_current_user() -> dict:
    """获取当前登录用户"""
    return st.session_state.get("user", {})


def is_admin() -> bool:
    """当前用户是否为管理员"""
    user = get_current_user()
    return user.get("role") == "admin"


def logout():
    """登出"""
    st.session_state.user = None
    st.session_state.logged_in = False
    st.experimental_rerun()

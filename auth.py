"""
认证模块 — 登录/登出/会话管理 · Moebius 极繁主义主题
"""
import streamlit as st
from db import verify_login, init_db
from moebius_theme import MOEBIUS_CSS


def require_login() -> dict:
    """确保当前会话已登录，未登录时渲染登录界面"""
    if "user" in st.session_state and st.session_state.user:
        return st.session_state.user

    render_login_page()
    st.stop()
    return {}


def render_login_page():
    """渲染 Moebius 风格登录界面"""
    st.markdown(MOEBIUS_CSS, unsafe_allow_html=True)
    st.markdown("""
    <style>
        footer {visibility: hidden;}
        .stDeployButton {display: none;}
        [data-testid="stSidebar"] {display: none;}
        [data-testid="stToolbar"] {display: none;}
        /* 登录页特殊：居中卡片 */
        .stApp {
            display: flex; align-items: center; justify-content: center;
        }
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.title("知识圣殿")
        st.caption("PMP 备考辅助系统")

        username = st.text_input("道号", placeholder="请输入用户名")
        password = st.text_input("密钥", type="password", placeholder="请输入密码")

        if st.button("✦ 进入圣殿"):
            init_db()
            user = verify_login(username, password)
            if user:
                st.session_state.user = user
                st.session_state.logged_in = True
                role = "圣殿守护者" if user['role'] == 'admin' else "求道者"
                st.success(f"欢迎归来，{role} {user['username']}")
                st.experimental_rerun()
            else:
                st.error("道号或密钥不正确，请重新输入")

        st.markdown("---")
        st.caption("圣殿守护者：admin / admin123")
        st.caption("求道者：user / user123")


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

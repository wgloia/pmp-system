"""
PMP 备考助手 — Python 启动器
双击 run.bat 或直接 python launcher.py
"""
import subprocess
import sys
import os
from pathlib import Path

PROJECT_DIR = Path(__file__).parent
LOG_FILE = PROJECT_DIR / "startup.log"


def log(msg: str):
    """写日志"""
    line = f"[{msg}]"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def main():
    log(f"启动 {PROJECT_DIR}")

    # 检查 Python 版本
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}"
    log(f"Python {py_ver}")

    # 检查并激活 venv
    if sys.platform == "win32":
        venv_python = PROJECT_DIR / "venv" / "Scripts" / "python.exe"
    else:
        venv_python = PROJECT_DIR / "venv" / "bin" / "python"

    if not venv_python.exists():
        log("创建虚拟环境...")
        subprocess.run([sys.executable, "-m", "venv", str(PROJECT_DIR / "venv")], check=True)

    # 安装依赖
    result = subprocess.run(
        [str(venv_python), "-c", "import streamlit"],
        capture_output=True,
    )
    if result.returncode != 0:
        log("安装依赖...")
        subprocess.run([
            str(venv_python), "-m", "pip", "install",
            "streamlit", "pandas", "PyMuPDF", "chromadb", "protobuf>=3.20,<4",
            "-i", "https://mirrors.aliyun.com/pypi/simple/",
            "--trusted-host", "mirrors.aliyun.com",
        ], check=True)

    # 初始化数据库
    log("初始化数据库...")
    subprocess.run([str(venv_python), str(PROJECT_DIR / "db.py")], check=True)

    # 启动 Streamlit
    log("启动 Streamlit http://localhost:8501")
    env = os.environ.copy()
    env["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

    streamlit_exe = venv_python.parent / "streamlit.exe"
    subprocess.run([
        str(streamlit_exe), "run", str(PROJECT_DIR / "app.py"),
        "--server.headless", "true", "--server.port", "8501",
    ], env=env)

    log("Streamlit 已退出")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"错误: {e}")
    input("按任意键退出...")

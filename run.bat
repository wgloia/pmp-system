@echo off
chcp 65001 >nul
cd /d "%~dp0"

REM 激活虚拟环境
call venv\Scripts\activate.bat

REM 安装依赖
pip install streamlit pandas PyMuPDF chromadb "protobuf>=3.20,<4" ^
    -i https://mirrors.aliyun.com/pypi/simple/ ^
    --trusted-host mirrors.aliyun.com

REM 初始化数据库
python db.py

REM 启动 Streamlit（protobuf 兼容模式）
set PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
streamlit run app.py

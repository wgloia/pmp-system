@echo off
chcp 65001 >nul
cd /d "%~dp0"
title PMP 备考助手 · 知识圣殿

REM 激活虚拟环境
call venv\Scripts\activate.bat || (
    echo [错误] 虚拟环境不存在，请先运行 python -m venv venv
    pause
    exit /b 1
)

REM 检查核心依赖是否已安装（避免每次重装）
python -c "import streamlit" 2>nul
if %errorlevel% neq 0 (
    echo [安装] 正在安装依赖...
    pip install streamlit pandas PyMuPDF chromadb "protobuf>=3.20,<4" ^
        -i https://mirrors.aliyun.com/pypi/simple/ ^
        --trusted-host mirrors.aliyun.com
    if %errorlevel% neq 0 (
        echo [错误] 依赖安装失败，请检查网络连接
        pause
        exit /b 1
    )
)

REM 初始化数据库
python db.py
if %errorlevel% neq 0 (
    echo [错误] 数据库初始化失败
    pause
    exit /b 1
)

REM 启动 Streamlit
echo.
echo [启动] PMP 备考助手 · 知识圣殿
echo [地址] http://localhost:8501
echo.
set PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
streamlit run app.py --server.headless true --server.port 8501

REM 如果 Streamlit 异常退出，暂停查看错误
if %errorlevel% neq 0 pause

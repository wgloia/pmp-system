@echo off
title PMP 备考助手 · 知识圣殿
cd /d "%~dp0"

REM 将输出写入日志文件，同时显示在控制台
set LOGFILE=%~dp0startup.log
echo ============================================ > %LOGFILE%
echo PMP 备考助手 启动日志 %date% %time% >> %LOGFILE%
echo ============================================ >> %LOGFILE%

REM 检查 Python
python --version >> %LOGFILE% 2>&1
if %errorlevel% neq 0 (
    echo [错误] 找不到 Python，请确认已安装 Python 3.9+ >> %LOGFILE%
    echo [错误] 找不到 Python，请确认已安装 Python 3.9+
    pause
    exit /b 1
)

REM 检查虚拟环境
if not exist "venv\Scripts\activate.bat" (
    echo [错误] 虚拟环境不存在，正在创建... >> %LOGFILE%
    echo [错误] 虚拟环境不存在，正在创建...
    python -m venv venv >> %LOGFILE% 2>&1
    if %errorlevel% neq 0 (
        echo [错误] 创建虚拟环境失败 >> %LOGFILE%
        pause
        exit /b 1
    )
)

REM 激活虚拟环境
call venv\Scripts\activate.bat >> %LOGFILE% 2>&1
echo [信息] 虚拟环境已激活 >> %LOGFILE%

REM 安装依赖（已安装则跳过）
python -c "import streamlit" >> %LOGFILE% 2>&1
if %errorlevel% neq 0 (
    echo [安装] 正在安装依赖，请稍候... >> %LOGFILE%
    echo [安装] 正在安装依赖，请稍候...
    pip install streamlit pandas PyMuPDF chromadb "protobuf>=3.20,<4" ^
        -i https://mirrors.aliyun.com/pypi/simple/ ^
        --trusted-host mirrors.aliyun.com >> %LOGFILE% 2>&1
    if %errorlevel% neq 0 (
        echo [错误] 依赖安装失败，查看 startup.log 了解详情 >> %LOGFILE%
        echo [错误] 依赖安装失败
        pause
        exit /b 1
    )
    echo [信息] 依赖安装完成 >> %LOGFILE%
)

REM 初始化数据库
python db.py >> %LOGFILE% 2>&1
if %errorlevel% neq 0 (
    echo [错误] 数据库初始化失败，查看 startup.log >> %LOGFILE%
    echo [错误] 数据库初始化失败
    pause
    exit /b 1
)
echo [信息] 数据库就绪 >> %LOGFILE%

REM 启动 Streamlit
echo [启动] PMP 备考助手 · 知识圣殿 >> %LOGFILE%
echo [启动] 访问地址: http://localhost:8501 >> %LOGFILE%
echo.
echo ============================================
echo   PMP 备考助手 · 知识圣殿
echo   访问地址: http://localhost:8501
echo   日志文件: startup.log
echo ============================================
echo.

set PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
streamlit run app.py --server.headless true --server.port 8501 2>> %LOGFILE%

REM Streamlit 退出后暂停
echo.
echo Streamlit 已停止，查看 startup.log 了解详情
pause

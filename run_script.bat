@echo off
REM ============================================================
REM  tender-writer 脚本调用入口
REM  用途:通过本地 venv 里的 python 执行 scripts\ 下的脚本
REM        所有 AI 工具(Claude Code / Qwen Code / Trae / Cline 等)
REM        在五阶段主干 + 并列阶段工作流中应统一通过本脚本调用 Python 脚本,
REM        而不是直接 python xxx.py(否则会因为缺包而报错)
REM  使用方法:run_script.bat <脚本名> <参数1> <参数2> ...
REM  示例:    run_script.bat parse_tender.py "D:\xxx\招标文件.pdf"
REM ============================================================
chcp 65001 >nul
setlocal

REM 切换到本脚本所在目录(确保相对路径正确)
cd /d "%~dp0"

REM ----------- 检查 .venv 是否存在 -----------
if not exist ".venv\Scripts\python.exe" (
    echo.
    echo [错误] 未找到本地虚拟环境 .venv
    echo 请先双击 install.bat 完成环境准备,然后再运行本脚本。
    echo.
    exit /b 1
)

REM ----------- 检查参数 -----------
if "%~1"=="" (
    echo.
    echo [错误] 未指定要运行的脚本名。
    echo 用法:run_script.bat ^<脚本名^> ^<参数1^> ^<参数2^> ...
    echo 示例:run_script.bat parse_tender.py "D:\xxx\招标文件.pdf"
    echo.
    echo 可用脚本:
    echo   parse_tender.py           招标文件解析^(阶段 1^)
    echo   build_scoring_matrix.py   评分矩阵构建^(阶段 2^)
    echo   generate_outline.py       提纲生成^(阶段 3^)
    echo   append_chapter.py         markdown 章节追加到 docx^(阶段 4^)
    echo   compliance_check.py       合规终审^(阶段 5^)
    echo   ingest_assets.py          已知分类素材摄入
    echo   triage_unsorted.py        未知分类材料 triage
    echo   add_company.py            新增公司并初始化目录
    echo   docx_builder.py           docx 构建工具模块^(被其他脚本调用^)
    echo.
    exit /b 1
)

REM ----------- 检查脚本是否存在 -----------
set "SCRIPT_NAME=%~1"
if not exist "scripts\%SCRIPT_NAME%" (
    echo.
    echo [错误] 找不到脚本 scripts\%SCRIPT_NAME%
    echo 请确认脚本名拼写是否正确。
    echo.
    exit /b 1
)

REM ----------- 执行脚本(透传所有后续参数) -----------
shift
set "ARGS="
:collect_args
if "%~1"=="" goto run
set "ARGS=%ARGS% "%~1""
shift
goto collect_args

:run
".venv\Scripts\python.exe" "scripts\%SCRIPT_NAME%" %ARGS%
exit /b %errorlevel%

@echo off
REM ============================================================
REM  tender-writer skill 一键环境准备脚本
REM  用途:在 tender-writer 文件夹内创建隔离的 Python 虚拟环境
REM        并安装所有依赖,完全不污染系统 Python 环境
REM  使用方法:双击本文件即可
REM  作者:tender-writer skill
REM ============================================================
chcp 65001 >nul
setlocal enabledelayedexpansion

REM 切换到本脚本所在目录(确保相对路径正确)
cd /d "%~dp0"

echo.
echo ============================================================
echo   tender-writer skill 环境准备
echo ============================================================
echo.

REM ----------- 第一步:检查 Python 是否已安装 -----------
echo [1/4] 正在检查 Python 是否已安装...

set "PYTHON_CMD="
python --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_CMD=python"
    goto python_found
)

py --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_CMD=py"
    goto python_found
)

echo.
echo [错误] 未检测到 Python!
echo.
echo 请先到 https://www.python.org/downloads/ 下载并安装 Python 3.10 或更高版本。
echo 安装时请务必勾选 "Add Python to PATH" 选项,否则安装完后仍然无法使用。
echo 安装完成后,重新双击本脚本即可继续。
echo.
pause
exit /b 1

:python_found
for /f "tokens=*" %%i in ('!PYTHON_CMD! --version 2^>^&1') do set "PYTHON_VERSION=%%i"
echo     检测到 !PYTHON_VERSION!
echo.

REM ----------- 第二步:创建虚拟环境 -----------
echo [2/4] 正在创建隔离虚拟环境 .venv\ ...

if exist ".venv\Scripts\python.exe" (
    echo     .venv 已存在,跳过创建步骤。
    echo     若需重新初始化,请手动删除 tender-writer\.venv 文件夹后再运行本脚本。
) else (
    !PYTHON_CMD! -m venv .venv
    if !errorlevel! neq 0 (
        echo.
        echo [错误] 创建虚拟环境失败!
        echo 可能原因:Python 安装不完整,缺少 venv 模块。
        echo 请尝试重新安装 Python,或运行 "!PYTHON_CMD! -m ensurepip" 修复。
        echo.
        pause
        exit /b 1
    )
    echo     .venv 创建完成。
)
echo.

REM ----------- 第三步:升级 pip -----------
echo [3/4] 正在升级 pip 到最新版本...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if %errorlevel% neq 0 (
    echo.
    echo [警告] pip 升级失败,继续尝试安装依赖。
    echo 如果后续依赖安装也失败,请检查网络连接。
    echo.
)
echo.

REM ----------- 第四步:安装依赖 -----------
echo [4/4] 正在安装 requirements.txt 中的依赖包...
echo     ^(首次安装可能需要几分钟,请耐心等待^)
echo.
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo ========================================
    echo [安装失败] 可能原因及解决办法:
    echo   1. 网络问题 - 国内用户可用清华镜像:
    echo      .venv\Scripts\python.exe -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
    echo   2. 缺少 C++ 构建工具 - 装 Visual Studio Build Tools
    echo   3. requirements.txt 包名有误 - 联系维护人
    echo ========================================
    pause
    exit /b 1
) else (
    echo.
    echo ========================================
    echo [安装成功] 环境已准备就绪!
    echo ========================================
    echo.
    echo 下一步^(根据你使用的 AI 工具选其一^):
    echo.
    echo   [方式一] Claude Code^(推荐^):
    echo     1. 把整个 tender-writer 文件夹复制到工作目录的 .claude\skills\ 下
    echo     2. 在工作目录下启动 Claude Code: claude
    echo     3. 上传招标文件,或者直接说 "帮我编制这个标书的技术方案"
    echo.
    echo   [方式二] 其他能操作本地文件的 AI^(Qwen Code / Trae / Cline 等^):
    echo     在工作目录下启动你的 AI 工具,手动让它读取
    echo     tender-writer\SKILL.md 并按其中的五阶段主干 + 并列阶段工作流推进
    echo.
    echo   [方式三] 纯对话 AI^(Kimi / 豆包 / 文心一言 等^):
    echo     注意:本 skill 依赖本地脚本执行,纯对话 AI 不能完整运行。
    echo     可参考 SKILL.md 文本作为提示词素材,但无法执行五阶段主干 + 并列阶段脚本。
    echo.
    echo 详细使用说明请阅读 README.md
    echo.
    pause
    exit /b 0
)

@echo off
chcp 65001 >nul
echo ========================================
echo   安装校园网自动登录脚本所需依赖
echo ========================================
echo.
pip install requests
echo.
if %errorlevel% equ 0 (
    echo [成功] 依赖安装完成！
) else (
    echo [失败] 安装出错，请检查是否安装了 Python
)
echo.
pause

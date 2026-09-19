@echo off
REM cart.bat —— 菜单 + 整数运算(批处理不支持浮点,金额以"元"为单位取整)
setlocal enabledelayedexpansion
chcp 65001 >nul

set "TOTAL=0"
set "COUNT=0"

:menu
cls
echo ==============================
echo           简易购物车
echo ==============================
echo    1. 机械键盘   399 元
echo    2. 鼠标垫      30 元
echo    3. 查看小票
echo    4. 清空购物车
echo    0. 退出
echo ==============================
set /p "CHOICE=请输入选项: "

if "%CHOICE%"=="1" (
    set /a TOTAL+=399
    set /a COUNT+=1
    echo.
    echo 已加入:机械键盘
    timeout /t 1 >nul
    goto menu
)
if "%CHOICE%"=="2" (
    set /a TOTAL+=30
    set /a COUNT+=1
    echo.
    echo 已加入:鼠标垫
    timeout /t 1 >nul
    goto menu
)
if "%CHOICE%"=="3" goto show
if "%CHOICE%"=="4" goto clear
if "%CHOICE%"=="0" goto end

echo.
echo 无效选项,请重新输入。
timeout /t 1 >nul
goto menu

:show
cls
echo ==============================
echo             小票
echo ==============================
if "%COUNT%"=="0" (
    echo 购物车是空的
) else (
    echo 商品件数:%COUNT% 件
    echo 合计金额:%TOTAL% 元
)
echo ==============================
pause
goto menu

:clear
set "TOTAL=0"
set "COUNT=0"
echo.
echo 购物车已清空。
timeout /t 1 >nul
goto menu

:end
echo.
echo 感谢使用,再见!
endlocal
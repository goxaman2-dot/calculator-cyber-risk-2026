@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo === Сохраняю изменения в GitHub ===
git add -A
git commit -m "Обновление калькулятора"
if errorlevel 1 (
    echo Нечего коммитить — изменений не найдено.
) else (
    git push
)
echo.
echo Готово. Можно закрыть окно.
pause

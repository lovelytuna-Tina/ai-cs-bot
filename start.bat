@echo off
chcp 65001 >nul
cd /d F:\020-Trae\ai-cs-bot
echo ============================================
echo   AI 智能客服助手 启动中...
echo ============================================
echo.
echo 启动成功后，请用浏览器访问：
echo   http://127.0.0.1:8000
echo.
echo 停止服务：按 Ctrl + C，或直接关闭本窗口
echo ============================================
echo.
"C:\Users\Administrator\AppData\Local\Programs\Python\Python314\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
pause

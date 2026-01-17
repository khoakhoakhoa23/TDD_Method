@echo off
REM Medium Load Test - Scale up from working baseline
REM This script runs a medium load test to find the optimal concurrency level

echo Starting medium load test (building on successful light test)...

REM Change to backend directory
cd /d %~dp0

REM Set medium load test settings - gradually increasing from light test
set LOAD_TEST_MODE=true
set DEBUG=false
set LOAD_TOTAL_USERS=50
set LOAD_CONCURRENCY=10
set LOAD_TIMEOUT=15
set LOAD_REQUEST_CONCURRENCY=100
set LOAD_WRITE_CONCURRENCY=20
set LOAD_AUTH_CONCURRENCY=10

REM Start Django dev server in background
echo Starting Django development server...
start /B python manage.py runserver 127.0.0.1:8000 --noreload

REM Wait for server to start
timeout /t 3 /nobreak > nul

REM Run medium load test
echo Running medium load test (50 users, 10 concurrency)...
python load_test_e2e.py

REM Cleanup
echo Stopping server...
taskkill /f /im python.exe > nul 2>&1

echo Medium load test completed.
pause

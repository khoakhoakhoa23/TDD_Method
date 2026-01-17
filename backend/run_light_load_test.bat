@echo off
REM Light Load Test - Just to verify optimizations work
REM This script runs a minimal load test to check if server can handle basic load

echo Starting light load test to verify optimizations...

REM Change to backend directory
cd /d %~dp0

REM Set minimal load test settings
set LOAD_TEST_MODE=true
set DEBUG=false
set LOAD_TOTAL_USERS=10
set LOAD_CONCURRENCY=3
set LOAD_TIMEOUT=20
set LOAD_REQUEST_CONCURRENCY=50
set LOAD_WRITE_CONCURRENCY=10
set LOAD_AUTH_CONCURRENCY=5

REM Start Django dev server in background
echo Starting Django development server...
start /B python manage.py runserver 127.0.0.1:8000 --noreload

REM Wait for server to start
timeout /t 3 /nobreak > nul

REM Run light load test
echo Running light load test...
python load_test_e2e.py

REM Cleanup
echo Stopping server...
taskkill /f /im python.exe > nul 2>&1

echo Light load test completed.
pause

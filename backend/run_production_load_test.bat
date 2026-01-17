@echo off
REM Production Load Test Runner with Gunicorn
REM This script runs a production server and optimized load test

echo Starting production load test with Gunicorn...

REM Set load test environment variables
set LOAD_TEST_MODE=true
set DEBUG=false
set LOAD_TOTAL_USERS=100
set LOAD_CONCURRENCY=20
set LOAD_TIMEOUT=15
set LOAD_REQUEST_CONCURRENCY=200
set LOAD_WRITE_CONCURRENCY=40
set LOAD_AUTH_CONCURRENCY=20

REM Start Gunicorn server in background
echo Starting Gunicorn server...
start /B gunicorn --config gunicorn.conf.py backend.wsgi:application

REM Wait for server to start
timeout /t 5 /nobreak > nul

REM Run the optimized load test
echo Running load test...
python load_test_e2e.py

REM Cleanup
echo Stopping server...
taskkill /f /im gunicorn.exe > nul 2>&1

echo Load test completed.
pause

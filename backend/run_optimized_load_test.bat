@echo off
REM Optimized Load Test Runner
REM This script runs the load test with optimized settings for high concurrency

echo Starting optimized load test...

REM Set load test environment variables
set LOAD_TEST_MODE=true
set DEBUG=false
set LOAD_TOTAL_USERS=200
set LOAD_CONCURRENCY=50
set LOAD_TIMEOUT=10
set LOAD_REQUEST_CONCURRENCY=300
set LOAD_WRITE_CONCURRENCY=50
set LOAD_AUTH_CONCURRENCY=25

REM Database optimization
set DB_CONN_MAX_AGE=300
set DB_CONN_HEALTH_CHECKS=true

REM Run the optimized load test
python load_test_e2e.py

echo Load test completed.
pause

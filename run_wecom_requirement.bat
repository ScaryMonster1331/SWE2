@echo off
set /p APPROVAL_ID=Approval ID: 
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_wecom_requirement.ps1" -ApprovalId "%APPROVAL_ID%"
set EXIT_CODE=%ERRORLEVEL%
pause
exit /b %EXIT_CODE%

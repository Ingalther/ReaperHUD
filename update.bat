@echo off
rem The Reaper HUD - one-click update.
rem Pulls the latest version from GitHub, rebuilds the HUD from TF2's current files and installs it into TF2's
rem custom folder. The project folder itself is the HUD: dropped into tf\custom (e.g. as "ReaperHUD-main") it
rem is built in place; anywhere else the HUD is copied into tf\custom\reaper-hud.
rem To use a different git branch instead, only change the line below.
if not defined BRANCH set "BRANCH=main"

cd /d "%~dp0"
title The Reaper HUD - update
color 0B
if not exist ".git" if not exist "tools\build.py" goto wrongplace

echo.
echo  TF2 must be closed. Press any key to continue.
pause >nul
rem Git, Python 3, Pillow and numpy are checked before anything changes;
rem a missing one is named and can be installed.
call :tools
if errorlevel 1 exit /b 1
echo.
echo  [1/3] Pulling the latest changes from GitHub...
if exist ".git" goto pull
echo  This folder has no git data yet, linking it to GitHub...
git init -q
git remote add origin https://github.com/Ingalther/ReaperHUD.git
git fetch origin %BRANCH% || goto nofetch
git checkout -f -B %BRANCH% origin/%BRANCH% && goto pull || goto nofiles

:pull
rem Local differences in the HUD parts (resource, scripts, materials, info.vdf) are reset first so they
rem cannot block the pull; nothing is lost, step 2 rebuilds them.
git checkout -- resource scripts materials info.vdf 2>nul
git clean -fdq -- resource scripts materials cfg 2>nul
git fetch origin %BRANCH% || goto nofetch
rem Git now swaps this file under the running window. The rest of the line below still runs, and from there on
rem the window finds its way by label in the new file: the labels pull, build, nofetch and nofiles (and the
rem ones they use) must stay in every later version.
git reset -q --hard origin/%BRANCH% && goto build || goto nofiles

:build
call :tools
if errorlevel 1 exit /b 1
echo.
echo  [2/3] Building the HUD and installing it into TF2...
%PY% tools\build.py --install
if errorlevel 1 goto nobuild
rem The install check (tools\doctor.py) looks for what makes the HUD look wrong in game (TF2 left running,
rem another HUD or a mod in tf\custom that replaces its files), offers to move such mods out and writes
rem rk_report.txt next to this file. It never stops an update that went through.
echo.
echo  [3/3] Checking the install...
%PY% tools\doctor.py
echo.
echo  Done! You can start TF2.
pause
exit /b 0

:tools
rem Checks for Git, Python 3 (found as PY), Pillow and numpy. Missing ones are offered for install (Git and
rem Python through winget, Windows' own installer; Pillow and numpy through pip), or else named with where
rem to get them. Returns 1 while one is still missing.
set "RK_TRIED="
:tools_check
call :findtools
if not defined RK_NOGIT if defined PY if not defined RK_NOPKG exit /b 0
echo.
echo  update.bat needs a few free tools to download and build the HUD, and this PC is missing:
if defined RK_NOGIT echo   - Git
if not defined PY echo   - Python 3
if defined RK_NOPKG echo   - Pillow and numpy, two add-ons for Python
if defined RK_TRIED goto tools_manual
set "RK_WINGET="
if defined RK_NOGIT set "RK_WINGET=1"
if not defined PY set "RK_WINGET=1"
if defined RK_WINGET winget --version >nul 2>&1 || goto tools_manual
echo.
echo  update.bat can download and install them for you now, free and from their official sources.
echo  Windows may ask for permission.
choice /c YN /n /m " Install them now? [Y/N] "
if errorlevel 2 goto tools_manual
set "RK_TRIED=1"
if defined RK_NOGIT winget install --id Git.Git -e --source winget --accept-package-agreements --accept-source-agreements
if not defined PY winget install --id Python.Python.3.13 -e --source winget --accept-package-agreements --accept-source-agreements
rem What winget installed is on the PATH of new windows only: take the PATH over from the registry.
for /f "usebackq delims=" %%P in (`%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe -NoProfile -Command "[Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User')"`) do set "PATH=%%P"
call :findtools
if defined PY if defined RK_NOPKG %PY% -m pip install --disable-pip-version-check pillow numpy
goto tools_check

:tools_manual
color 0C
set "RK_PIP=%PY%"
if not defined PY set "RK_PIP=py"
echo.
if defined RK_TRIED echo  Not everything could be installed. If something was installed just now, close this window and
if defined RK_TRIED echo  run update.bat again. Otherwise get it by hand:
if defined RK_NOGIT echo   - Git: get it from https://git-scm.com/download/win and install it with the default options.
if not defined PY echo   - Python 3: get it from https://www.python.org/downloads/ and install it with the default options.
if defined RK_NOPKG echo   - Pillow and numpy: open a Command Prompt and run   %RK_PIP% -m pip install pillow numpy
echo  Then run update.bat again.
echo.
echo  Without these tools you can update by hand: download the newest ZIP from
echo  https://github.com/Ingalther/ReaperHUD/releases/latest and put its folder into tf\custom
echo  in place of this one.
pause
exit /b 1

:findtools
rem Sets PY to the Python 3 command, and RK_NOGIT / RK_NOPKG when Git / Pillow and numpy are missing.
set "PY="
set "RK_NOGIT="
set "RK_NOPKG="
git --version >nul 2>&1 || if exist "%ProgramFiles%\Git\cmd\git.exe" set "PATH=%PATH%;%ProgramFiles%\Git\cmd"
git --version >nul 2>&1 || set "RK_NOGIT=1"
python -c "import sys; sys.exit(sys.version_info[0] != 3)" >nul 2>&1 && set "PY=python"
if not defined PY py -3 -c "import sys" >nul 2>&1 && set "PY=py -3"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" set PY="%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
if not defined PY if exist "%ProgramFiles%\Python313\python.exe" set PY="%ProgramFiles%\Python313\python.exe"
if defined PY %PY% -c "import PIL, numpy" >nul 2>&1 || set "RK_NOPKG=1"
if not defined PY set "RK_NOPKG=1"
exit /b 0

:wrongplace
color 0C
echo.
echo  This update.bat is not inside The Reaper HUD's project folder.
echo  Run the update.bat that sits next to the "tools" folder, not a copy of it.
echo  Folder used now: %CD%
pause
exit /b 1

:nofetch
color 0C
echo.
echo  Git could not download the new version from GitHub; the lines above say why.
echo  Most often the internet connection is down, or a firewall or antivirus blocks Git. Fix that, then run
echo  update.bat again.
goto report

:nofiles
color 0C
echo.
echo  Git could not put the new version in place; the lines above say why. Most often a program still has
echo  files of this folder open (TF2, an editor, an antivirus scan): close it, then run update.bat again.
goto report

:nobuild
color 0C
echo.
echo  The new version is downloaded, but building the HUD failed; the lines above say why.
goto report

:report
echo  If it keeps failing, send a screenshot of this window when you report the problem.
pause
exit /b 1

: << 'CMDBLOCK'
@echo off
REM Cross-platform polyglot wrapper for Trigpoint's hook scripts.
REM On Windows: cmd.exe runs the batch portion below, which finds a Python
REM interpreter and calls it. On Unix: the shell reads this as a script,
REM because ":" is a no-op and the heredoc swallows the batch half.
REM
REM The technique is borrowed from obra/superpowers, which uses it to find
REM bash. Trigpoint's hooks are Python, so this looks for Python instead:
REM Windows has no "python3" command, it has "py -3" or "python".
REM
REM When no interpreter is found this exits 0 without a message. A missing
REM Python must leave the agent's session working exactly as before, just
REM without the ledger state and without the re-run. A hook that fails loudly
REM on a machine that never asked for it is worse than one that stays quiet.
REM
REM Usage: run-hook.cmd <script-name.py> [args...]

if "%~1"=="" (
    echo run-hook.cmd: missing script name >&2
    exit /b 1
)

set "HOOK_DIR=%~dp0"

REM The Windows launcher is the most reliable way to reach Python 3.
where py >nul 2>nul
if %ERRORLEVEL% equ 0 (
    py -3 "%HOOK_DIR%%~1" %2 %3 %4 %5 %6 %7 %8 %9
    exit /b %ERRORLEVEL%
)

where python3 >nul 2>nul
if %ERRORLEVEL% equ 0 (
    python3 "%HOOK_DIR%%~1" %2 %3 %4 %5 %6 %7 %8 %9
    exit /b %ERRORLEVEL%
)

where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    python "%HOOK_DIR%%~1" %2 %3 %4 %5 %6 %7 %8 %9
    exit /b %ERRORLEVEL%
)

REM No interpreter: stay silent. The plugin simply does nothing here.
exit /b 0
CMDBLOCK

# Unix half.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPT_NAME="$1"
shift

for interpreter in python3 python; do
    if command -v "$interpreter" >/dev/null 2>&1; then
        exec "$interpreter" "${SCRIPT_DIR}/${SCRIPT_NAME}" "$@"
    fi
done

# Same rule as the Windows half: no interpreter is a quiet no-op, not an error.
exit 0

@echo off
REM Launcher for running OpenLP from the repository using a local venv in the project root.
REM Usage: double-click this file or create a shortcut to it.
set ScriptDir=%~dp0
"%ScriptDir%\.venv\Scripts\python.exe" "%ScriptDir%run_openlp.py" -p %*

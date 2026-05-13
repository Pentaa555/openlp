Option Explicit
Dim shell, repo, cmd
Set shell = CreateObject("WScript.Shell")
repo = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
cmd = """" & repo & "\.venv\Scripts\pythonw.exe"" """ & repo & "\run_openlp.py"" -p"
shell.CurrentDirectory = repo
shell.Run cmd, 0, False

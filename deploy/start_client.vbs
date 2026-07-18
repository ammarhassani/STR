' Launch the STR CLIENT app with no console window (#23). The app's own window
' still appears; only the black CMD window is suppressed. Put a shortcut to THIS
' file on the desktop / Startup folder for a clean launch.
Option Explicit
Dim oShell, oFSO, strRoot, strCmd
Set oShell = CreateObject("WScript.Shell")
Set oFSO = CreateObject("Scripting.FileSystemObject")

strRoot = oFSO.GetParentFolderName(oFSO.GetParentFolderName(WScript.ScriptFullName))

' Self-update (#19) first, then launch the client — both logged, both hidden.
strCmd = "cmd /c cd /d """ & strRoot & """ & " & _
         "if not exist logs mkdir logs & " & _
         "python updater.py >> logs\client.log 2>&1 & " & _
         "pythonw flet_app\main.py >> logs\client.log 2>&1"

oShell.Run strCmd, 0, False

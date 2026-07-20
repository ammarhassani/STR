' DEPRECATED -- do not deploy this to client PCs.
'
' Client PCs now run the packaged FIU_System.exe, which needs no Python, no
' source tree and no launcher script. Use the control panel's "Build client
' folder" button instead (see docs/SETUP.md section C).
'
' Kept only for running a client from source on a developer machine.
'
' Why it is retired: this script's WScript -> cmd -> python chain with a hidden
' window is indistinguishable from a malware dropper to endpoint security, and
' it was flagged by the bank's EDR on 2026-07-20. The exe removes the pattern
' entirely rather than asking for a detection exclusion, which would have been
' the wrong fix.
'
' Launch the STR CLIENT app with no console window (#23). The app's own window
' still appears; only the black CMD window is suppressed.
Option Explicit
Dim oShell, oFSO, strRoot, strCmd
Set oShell = CreateObject("WScript.Shell")
Set oFSO = CreateObject("Scripting.FileSystemObject")

strRoot = oFSO.GetParentFolderName(oFSO.GetParentFolderName(WScript.ScriptFullName))

' Self-update (#19) first, then launch the client — both logged, both hidden.
' `md logs 2>nul` deliberately replaces `if not exist logs mkdir logs`: in a
' one-line cmd chain the IF swallows everything after it into its body, so once
' logs\ existed the condition was false and NOTHING else ran -- the launcher
' worked exactly once per PC and then silently started nothing ever again.
strCmd = "cmd /c cd /d """ & strRoot & """ & " & _
         "md logs 2>nul & " & _
         "python updater.py >> logs\client.log 2>&1 & " & _
         "pythonw flet_app\main.py >> logs\client.log 2>&1"

oShell.Run strCmd, 0, False

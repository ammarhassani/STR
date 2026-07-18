' Launch the STR HOST completely hidden — no CMD window kept open (#23).
' Put a shortcut to THIS file (not the .bat) in the Startup folder
' (Win+R -> shell:startup) so the host runs invisibly on login.
'
' Uses pythonw (no console) and redirects all output to logs\host.log so the
' host is fully headless yet still leaves a log you can read if something breaks.
Option Explicit
Dim oShell, oFSO, strRoot, strCmd
Set oShell = CreateObject("WScript.Shell")
Set oFSO = CreateObject("Scripting.FileSystemObject")

' STR root = the parent of this script's folder (deploy\ -> STR root)
strRoot = oFSO.GetParentFolderName(oFSO.GetParentFolderName(WScript.ScriptFullName))

' Self-update (#19) first, then launch the host — both logged, both hidden.
' `md logs 2>nul` deliberately replaces `if not exist logs mkdir logs`: in a
' one-line cmd chain the IF swallows everything after it into its body, so once
' logs\ existed the condition was false and NOTHING else ran -- the launcher
' worked exactly once per PC and then silently started nothing ever again.
strCmd = "cmd /c cd /d """ & strRoot & """ & " & _
         "md logs 2>nul & " & _
         "python updater.py >> logs\host.log 2>&1 & " & _
         "pythonw flet_app\main.py --host >> logs\host.log 2>&1"

' 0 = hidden window, False = fire-and-forget (don't wait for the host to exit)
oShell.Run strCmd, 0, False

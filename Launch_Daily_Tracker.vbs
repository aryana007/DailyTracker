' ========================================================
' Daily Routine & Food Log - Silent VBS Launcher
' Launches with zero terminal/console window
' ========================================================
Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

strDir = fso.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = strDir

pythonwPath = WshShell.ExpandEnvironmentStrings("%LOCALAPPDATA%\Python\pythoncore-3.14-64\pythonw.exe")

If fso.FileExists(pythonwPath) Then
    WshShell.Run """" & pythonwPath & """ """ & strDir & "\daily_tracker.py""", 0, False
Else
    WshShell.Run "pythonw """ & strDir & "\daily_tracker.py""", 0, False
End If

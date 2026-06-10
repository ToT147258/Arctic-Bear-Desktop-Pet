Option Explicit

Dim fso, shell, appDir, launcher, cmd
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")

appDir = fso.GetParentFolderName(WScript.ScriptFullName)
launcher = appDir & "\launch_polar_bear.bat"
cmd = shell.ExpandEnvironmentStrings("%ComSpec%")
shell.CurrentDirectory = appDir
shell.Run """" & cmd & """ /d /c """ & launcher & """", 0, False

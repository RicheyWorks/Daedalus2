# never -unattended on the GUI editor
& "C:\UE\UnrealEditor.exe" $Project -d3d11 -gpucrashdebugging
& "C:\UE\UnrealEditor-Cmd.exe" $Project -run=pythonscript -unattended
& $editor $Project -run=pythonscript -script=x.py -unattended -nopause
& "C:\UE\UnrealEditor.exe" $Project -game -unattended


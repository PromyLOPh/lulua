copy %~dp0\system32\kbdarlulua.dll /B c:\windows\system32\
copy %~dp0\syswow64\kbdarlulua.dll /B c:\windows\syswow64\
reg import %~dp0\lulua.reg
pause


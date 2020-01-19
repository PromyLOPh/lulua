REM taken from https://levicki.net/articles/2006/09/29/HOWTO_Build_keyboard_layouts_for_Windows_x64.php

SET OUTNAME=kbdarlulua
SET MSKLC="C:\Program Files (x86)\Microsoft Keyboard Layout Creator 1.4"

mkdir System32

%MSKLC%\bin\i386\rc.exe -r -i%MSKLC%\inc -DSTD_CALL -DCONDITION_HANDLING=1 -DNT_UP=1 -DNT_INST=0 -DWIN32=100 -D_NT1X_=100 -DWINNT=1 -D_WIN32_WINNT=0x0502 /DWINVER=0x0502 -D_WIN32_IE=0x0600 -DWIN32_LEAN_AND_MEAN=1 -DDEVL=1 -DFPO=1 -DNDEBUG -l 409 -Fokeyboard.res keyboard.rc || exit /b

REM build 64 bit
%MSKLC%\bin\i386\amd64\cl.exe -nologo -I%MSKLC%\inc -DNOGDICAPMASKS -DNOWINMESSAGES -DNOWINSTYLES -DNOSYSMETRICS -DNOMENUS -DNOICONS -DNOSYSCOMMANDS -DNORASTEROPS -DNOSHOWWINDOW -DOEMRESOURCE -DNOATOM -DNOCLIPBOARD -DNOCOLOR -DNOCTLMGR -DNODRAWTEXT -DNOGDI -DNOKERNEL -DNONLS -DNOMB -DNOMEMMGR -DNOMETAFILE -DNOMINMAX -DNOMSG -DNOOPENFILE -DNOSCROLL -DNOSERVICE -DNOSOUND -DNOTEXTMETRIC -DNOWINOFFSETS -DNOWH -DNOCOMM -DNOKANJI -DNOHELP -DNOPROFILER -DNODEFERWINDOWPOS -DNOMCX -DWIN32_LEAN_AND_MEAN -DRoster -DSTD_CALL -D_WIN32_WINNT=0x0502 /c /Zp8 /Gy /W3 /WX /Gz /Gm- /EHs-c- /GR- /GF -Z7 /Zl /Oxs -Fokeyboard64.obj keyboard.c || exit /b

REM XXX: why use the 32 bit linker here? the one in amd64\ does not work
%MSKLC%\bin\i386\link.exe -nologo -base:0x5FFE0000 -merge:.edata=.data -merge:.rdata=.data -merge:.text=.data -merge:.bss=.data -section:.data,re -MERGE:_PAGE=PAGE -MERGE:_TEXT=.text -MACHINE:AMD64 -SECTION:INIT,d -OPT:REF -OPT:ICF -IGNORE:4039,4078 -noentry -dll -subsystem:native,5.2 -merge:.rdata=.text -PDBPATH:NONE -STACK:0x40000,0x1000 /opt:nowin98 -debugtype:cv,fixup -debug -osversion:5.2 -version:5.2 /release -def:keyboard.def -out:system32\%OUTNAME%.dll keyboard.res keyboard64.obj || exit /b

REM and now 32 bit
mkdir SysWOW64

%MSKLC%\bin\i386\cl.exe -nologo -I%MSKLC%\inc -DBUILD_WOW6432 -DNOGDICAPMASKS -DNOWINMESSAGES -DNOWINSTYLES -DNOSYSMETRICS -DNOMENUS -DNOICONS -DNOSYSCOMMANDS -DNORASTEROPS -DNOSHOWWINDOW -DOEMRESOURCE -DNOATOM -DNOCLIPBOARD -DNOCOLOR -DNOCTLMGR -DNODRAWTEXT -DNOGDI -DNOKERNEL -DNONLS -DNOMB -DNOMEMMGR -DNOMETAFILE -DNOMINMAX -DNOMSG -DNOOPENFILE -DNOSCROLL -DNOSERVICE -DNOSOUND -DNOTEXTMETRIC -DNOWINOFFSETS -DNOWH -DNOCOMM -DNOKANJI -DNOHELP -DNOPROFILER -DNODEFERWINDOWPOS -DNOMCX -DWIN32_LEAN_AND_MEAN -DRoster -DSTD_CALL -D_WIN32_WINNT=0x0502 /c /Zp8 /Gy /W3 /WX /Gz /Gm- /EHs-c- /GR- /GF -Z7 /Zl /Oxs -Fokeyboard32.obj keyboard.c || exit /b

%MSKLC%\bin\i386\link.exe -nologo -base:0x5FFF0000 -merge:.edata=.data -merge:.rdata=.data -merge:.text=.data -merge:.bss=.data -section:.data,re -MERGE:_PAGE=PAGE -MERGE:_TEXT=.text -MACHINE:IX86 -SECTION:INIT,d -OPT:REF -OPT:ICF -IGNORE:4039,4078 -noentry -dll -subsystem:native,5.2 -merge:.rdata=.text -PDBPATH:NONE -STACK:0x40000,0x1000 /opt:nowin98 -debugtype:cv,fixup -debug -osversion:5.2 -version:5.2 /release -def:keyboard.def -out:SysWOW64\%OUTNAME%.dll keyboard.res keyboard32.obj || exit /b


!include LogicLib.nsh
!include x64.nsh

!define APP_NAME "Scanner"
OutFile "Scanner_Setup.exe"

Function .onInit
  ${If} ${RunningX64}
    StrCpy $INSTDIR "$PROGRAMFILES64\${APP_NAME}"
    SetRegView 64
  ${Else}
    StrCpy $INSTDIR "$PROGRAMFILES32\${APP_NAME}"
    SetRegView 32
  ${EndIf}
FunctionEnd

Section "Install"
  SetOutPath $INSTDIR
  ${If} ${RunningX64}
    File "dist\scanner_x64.exe"
    Rename "$INSTDIR\scanner_x64.exe" "$INSTDIR\scanner.exe"
  ${Else}
    File "dist\scanner_x86.exe"
    Rename "$INSTDIR\scanner_x86.exe" "$INSTDIR\scanner.exe"
  ${EndIf}
  
  File /r "sounds"
  CreateDirectory "$INSTDIR\logs"
  File "config.json"
  
  CreateShortCut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\scanner.exe"
  WriteUninstaller "$INSTDIR\uninstall.exe"
SectionEnd
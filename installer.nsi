!include LogicLib.nsh
!include x64.nsh

!define APP_NAME "TrillED Attendance Scanner"
!define APP_ICON "dist\icon.ico"
Icon "${APP_ICON}"
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

  # Registry
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
              "DisplayName" "${APP_NAME}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
              "UninstallString" "$INSTDIR\uninstall.exe"
SectionEnd


Section "Uninstall"
  Delete "$INSTDIR\scanner.exe"
  Delete "$INSTDIR\config.json"
  Delete "$DESKTOP\${APP_NAME}.lnk"
  Delete "$INSTDIR\uninstall.exe"
  RMDir /r "$INSTDIR\sounds"
  RMDir /r "$INSTDIR\logs"
  RMDir "$INSTDIR"
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}"
SectionEnd
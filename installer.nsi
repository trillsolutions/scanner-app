!include LogicLib.nsh
!include x64.nsh
!include MUI2.nsh

!define APP_NAME "TrillED Attendance Scanner"
!define PUBLISHER "Trillsolution"
!define VERSION "1.0.0"
!define WEBSITE_URL "https://trillsolution.com"
!define SUPPORT_EMAIL "support@trillsolution.com"
!define MUI_FINISHPAGE_AUTOCLOSE

# Icon for installer
!define APP_ICON "icon.ico"
Icon "${APP_ICON}"

Name "${APP_NAME}"
OutFile "TrillED_Attendance_Scanner_Setup.exe"
Unicode true
RequestExecutionLevel admin

# Default installation directory
Function .onInit
   ${If} ${RunningX64}
       StrCpy $INSTDIR "$PROGRAMFILES64\${APP_NAME}"
       SetRegView 64
   ${Else}
       StrCpy $INSTDIR "$PROGRAMFILES32\${APP_NAME}"
       SetRegView 32
   ${EndIf}
   
   # Check for admin rights
   UserInfo::GetAccountType
   Pop $0
   ${If} $0 != "admin"
       MessageBox MB_OK|MB_ICONEXCLAMATION "Administrator rights required to install ${APP_NAME}"
       Quit
   ${EndIf}
FunctionEnd

Section "Install"
   SetOutPath $INSTDIR
   
   # Install appropriate version based on architecture
   ${If} ${RunningX64}
       File "dist\scanner_x64.exe"
       Rename "$INSTDIR\scanner_x64.exe" "$INSTDIR\scanner.exe"
   ${Else}
       File "dist\scanner_x86.exe"
       Rename "$INSTDIR\scanner_x86.exe" "$INSTDIR\scanner.exe"
   ${EndIf}
   
   # Install additional files
   File /r "sounds"
   File "config.json"
   CreateDirectory "$INSTDIR\logs"
   
   # Create shortcuts
   CreateDirectory "$SMPROGRAMS\${APP_NAME}"
   CreateShortCut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" "$INSTDIR\scanner.exe"
   CreateShortCut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\scanner.exe"
   
   # Registry information for add/remove programs
   WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
                    "DisplayName" "${APP_NAME}"
   WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
                    "UninstallString" "$INSTDIR\uninstall.exe"
   WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
                    "DisplayIcon" "$INSTDIR\scanner.exe"
   WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
                    "Publisher" "${PUBLISHER}"
   WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
                    "URLInfoAbout" "${WEBSITE_URL}"
   WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
                    "HelpLink" "mailto:${SUPPORT_EMAIL}"
   WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
                    "DisplayVersion" "${VERSION}"
   WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
                      "NoModify" 1
   WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
                      "NoRepair" 1
   
   # Create uninstaller
   WriteUninstaller "$INSTDIR\uninstall.exe"
SectionEnd

Section "Uninstall"
   # Remove application files
   Delete "$INSTDIR\scanner.exe"
   Delete "$INSTDIR\config.json"
   RMDir /r "$INSTDIR\sounds"
   RMDir /r "$INSTDIR\logs"
   
   # Remove shortcuts
   Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"
   Delete "$DESKTOP\${APP_NAME}.lnk"
   RMDir "$SMPROGRAMS\${APP_NAME}"
   
   # Remove uninstaller
   Delete "$INSTDIR\uninstall.exe"
   RMDir "$INSTDIR"
   
   # Remove registry entries
   DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}"
SectionEnd
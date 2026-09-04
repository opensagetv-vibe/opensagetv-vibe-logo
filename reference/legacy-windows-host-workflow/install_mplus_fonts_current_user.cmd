@echo off
setlocal
cd /d "%~dp0"

if not exist "M_PLUS_Rounded_1c" (
  echo ERROR: Folder not found: "%~dp0M_PLUS_Rounded_1c"
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference='Stop';" ^
  "$src = Join-Path $PWD 'M_PLUS_Rounded_1c';" ^
  "$dst = Join-Path $env:LOCALAPPDATA 'Microsoft\Windows\Fonts';" ^
  "New-Item -ItemType Directory -Force -Path $dst | Out-Null;" ^
  "$shell = New-Object -ComObject Shell.Application;" ^
  "$fonts = Get-ChildItem -Path $src -File -Include *.ttf,*.otf;" ^
  "if(-not $fonts){ throw 'No font files found in M_PLUS_Rounded_1c'; }" ^
  "foreach($font in $fonts){" ^
  "  $target = Join-Path $dst $font.Name;" ^
  "  Copy-Item -Force $font.FullName $target;" ^
  "  $fontName = [System.IO.Path]::GetFileNameWithoutExtension($font.Name) + ' (TrueType)';" ^
  "  New-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows NT\CurrentVersion\Fonts' -Name $fontName -Value $font.Name -PropertyType String -Force | Out-Null;" ^
  "}" ^
  "Add-Type -Namespace Win32 -Name NativeMethods -MemberDefinition '[System.Runtime.InteropServices.DllImport(\"user32.dll\",SetLastError=true,CharSet=System.Runtime.InteropServices.CharSet.Auto)] public static extern IntPtr SendMessageTimeout(IntPtr hWnd, int Msg, IntPtr wParam, string lParam, int fuFlags, int uTimeout, out IntPtr lpdwResult);';" ^
  "$result = [IntPtr]::Zero;" ^
  "[void][Win32.NativeMethods]::SendMessageTimeout([IntPtr]0xffff,0x001D,[IntPtr]::Zero,'',2,1000,[ref]$result);" ^
  "Write-Host 'Installed fonts for current user.'"

if errorlevel 1 (
  echo Font installation failed.
  exit /b 1
)

echo Fonts installed for current user.
exit /b 0

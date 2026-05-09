@echo off
echo Installing Quantifile v1.0...
echo.

REM Create Program Files directory
if not exist "%ProgramFiles%\Quantifile" mkdir "%ProgramFiles%\Quantifile"

REM Copy files
copy "Quantifile.exe" "%ProgramFiles%\Quantifile\"
copy "README.md" "%ProgramFiles%\Quantifile\"
copy "LICENSE" "%ProgramFiles%\Quantifile\"

REM Create desktop shortcut
echo Creating desktop shortcut...
powershell "$ws = New-Object -ComObject WScript.Shell; $sc = $ws.CreateShortcut('%UserProfile%\Desktop\Quantifile.lnk'); $sc.TargetPath = '%ProgramFiles%\Quantifile\Quantifile.exe'; $sc.WorkingDirectory = '%ProgramFiles%\Quantifile'; $sc.IconLocation = '%ProgramFiles%\Quantifile\Quantifile.exe'; $sc.Save()"

echo.
echo Installation complete!
echo Quantifile has been installed to: %ProgramFiles%\Quantifile
echo A desktop shortcut has been created.
echo.
pause
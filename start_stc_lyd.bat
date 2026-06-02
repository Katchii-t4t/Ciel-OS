@echo off
:: Ciel Lyd-agent — transkriberer lydopptak til Obsidian-notat
:: Krev: pip install openai-whisper   +   ffmpeg (winget install Gyan.FFmpeg)

:: Legg til ffmpeg i PATH for denne sesjonen
set PATH=%PATH%;C:\Users\Karthik\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin

:: Fix for PyTorch/OpenMP-konflikt på Windows
set KMP_DUPLICATE_LIB_OK=TRUE

start "Ciel-lyd" /min python "C:\Users\Karthik\.claude\stc_lyd.py"

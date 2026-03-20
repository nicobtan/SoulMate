@echo off
setlocal

:: --- 設定エリア ---
:: SoulMateの実行ファイルのパスを指定してちょうだい
:: (run.batを直接呼び出すように修正します)
set "APP_PATH=C:\work\Soulmate\run.bat"
:: ウィンドウのタイトルの一部を指定してちょうだい（SoulMateなど）
set "WINDOW_TITLE=SoulMate"
:: 仮想ディスプレイの開始X座標（1920x1080が4枚なら 1920*4 = 7680）
set "X_COORD=2000"

:: --- 処理開始 ---
echo SoulMateを起動しますわ...
start "" "%APP_PATH%"

:: アプリが完全に立ち上がるまで少し待ちます（秒数は調整してちょうだい）
timeout /t 5 /nobreak > nul

echo 仮想ディスプレイへ移動させますわね...
powershell -command ^
    "$window = Get-Process | Where-Object { $_.MainWindowTitle -like '*%WINDOW_TITLE%*' } | Select-Object -First 1;" ^
    "if ($window) {" ^
    "    $signature = '[DllImport(\"user32.dll\")] public static extern bool MoveWindow(IntPtr hWnd, int X, int Y, int nWidth, int nHeight, bool bRepaint)';" ^
    "    $type = Add-Type -MemberDefinition $signature -Name \"Win32\" -Namespace \"Utils\" -PassThru;" ^
    "    $type::MoveWindow($window.MainWindowHandle, %X_COORD%, 0, 1920, 1200, $true);" ^
    "    echo '移動完了ですわ！';" ^
    "} else {" ^
    "    echo 'ウィンドウが見つかりませんでしたわ...';" ^
    "}"

pause

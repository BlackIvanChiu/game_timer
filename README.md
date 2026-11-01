# 遊戲計時器（給 ADHD 小朋友的視覺計時器）

在玩遊戲之前，讓小朋友自己選好要玩多久，再由爸爸媽媽輸入密碼後開始計時。

- 螢幕左上角會出現一個圓形計時器，彩色扇形的面積就是剩下的時間，顏色會從綠色慢慢變成黃色，最後變成紅色
- 計時器的背景是透明的，滑鼠點擊會直接穿透，不會擋到遊戲操作
- 剩下 5 分鐘時，計時器會振動、發出「叮咚」聲，並顯示「快收尾囉！」；剩 1 分鐘時會再輕輕提醒一次
- 時間一到，每個螢幕都會被擋板蓋住，必須輸入爸爸媽媽的密碼才能解除
- 解鎖後會回到設定畫面，爸爸媽媽可以再加一點時間，或直接按「離開程式」

## 安裝與執行

需要 Python 3.10 以上。

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
python main.py
```

第一次執行時，會先請爸爸媽媽設定家長密碼（至少 4 個字）。之後想改密碼，可以按設定畫面右下角的「更改密碼」。

### 快速測試

```bash
python main.py --minutes-as-seconds
```

加上這個參數後，每一「分鐘」都會當成 1 秒來計算。例如選 15 分鐘，實際上 15 秒就會跑完，第 10 秒時（剩 5 秒）會出現提醒，方便快速確認提醒和擋板是否正常。

## 打包成單一執行檔

```bash
pip install pyinstaller

# Windows：產生單一的 dist\GameTimer.exe
pyinstaller --onefile --windowed --name GameTimer main.py

# macOS：產生 dist/GameTimer.app（.app 本身就是一個資料夾，所以不要加 --onefile）
pyinstaller --windowed --name GameTimer main.py
```

PyInstaller 不能跨平台打包，所以要產生 Windows 版，就必須在 Windows 上執行上面的指令。

### 用 GitHub Actions 自動打包 Windows 版

如果手邊沒有 Windows 電腦，可以交給 GitHub 處理（設定在 `.github/workflows/build-windows.yml`）：

- 每次推送到 `main`，GitHub 都會自動打包。打包好的 `GameTimer.exe` 可以到 repo 的 **Actions** 頁面，點進最新一次執行，在下方的 **Artifacts** 下載（需要登入 GitHub）。
- 推送一個 `v` 開頭的 tag（例如 `git tag v1.0.0 && git push origin v1.0.0`），`GameTimer.exe` 就會自動發佈到 repo 的 **Releases** 頁面，誰都可以下載。

在 macOS 上，如果出現 `You have not agreed to the Xcode license agreements` 的錯誤，請先在終端機執行 `sudo xcodebuild -license` 並同意授權條款，然後再重新打包。

## 設定檔存放位置

密碼不會以明文儲存，而是加上 salt 後用 PBKDF2-SHA256 雜湊。設定檔放在：

- Windows：`%LOCALAPPDATA%\GameTimer\config.json`
- macOS：`~/Library/Preferences/GameTimer/config.json`
- Linux：`~/.config/GameTimer/config.json`

如果忘記密碼，把這個檔案刪掉，下次開啟程式時就會重新請你設定密碼。

## 使用上的注意事項

- **遊戲請改用「無邊框視窗」或「視窗化全螢幕」模式。** 有些遊戲在「獨佔全螢幕」模式下會蓋過所有置頂視窗，這時就看不到計時器和擋板。大部分遊戲都可以在顯示設定中切換。
- **macOS：** 如果遊戲使用 macOS 原生的全螢幕（會切換到另一個桌面空間），計時器可能不會顯示在那個空間上。建議讓遊戲以視窗模式或無邊框模式執行。
- **Linux：** 透明背景和置頂功能需要視窗管理器支援合成（compositing）；大部分桌面環境（GNOME、KDE）預設都已經開啟。
- **防護程度：** 這個版本的防護比較簡單，擋板會擋住 Esc、Alt+F4 和關閉視窗，並且每秒自動回到最上層，但不會攔截 Win 鍵、Alt+Tab，也沒辦法防止從工作管理員強制結束程式。比較適合搭配親子之間的約定一起使用。

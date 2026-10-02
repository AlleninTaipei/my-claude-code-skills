# my-claude-code-skills

個人的 Claude Code 自訂 Skills 與 Slash Commands 集合. 用於擴充 Claude Code 在教學內容產生, 簡報製作, 影片製作與文件撰寫上的能力.

## 目錄結構

```
.
├── CLAUDE.md
├── commands
│   ├── learndoc.md
│   └── md2course.md
└── skills
    ├── codebase-to-course
    ├── frontend-slides
    ├── knowledge-youtube-to-markdown
    ├── programmatic-video
    └── video-to-editable-slides
```

## Skills

### codebase-to-course

將任意程式碼庫轉換為一份精美的互動式單頁 HTML 課程, 教導非技術背景的使用者理解程式碼的運作方式.

- 目標讀者是 "vibe coder": 依靠自然語言指揮 AI 撰寫程式的使用者, 沒有傳統 CS 背景.
- 輸出為一個資料夾, 包含預先建置的 styles.css, main.js, 各模組 HTML 檔案, 以及組裝完成的 index.html.
- 課程結構分為 4 到 6 個模組, 從使用者已知的產品行為出發, 逐步深入到底層程式碼.
- 每個模組至少包含一組程式碼與白話說明的對照, 一個互動視覺化元件, 以及貼近生活的比喻.

觸發方式: 在對話中提到 "把這個專案做成課程", "turn this into a course", 或提供 GitHub 連結要求轉換為互動課程.

### frontend-slides

從零開始或透過轉換 PowerPoint 檔案, 產生視覺效果豐富且零外部依賴的 HTML 簡報.

- 單一 HTML 檔案, CSS 與 JS 全部內嵌, 不需要 npm 或建置工具.
- 採用固定 1920x1080 的簡報舞台, 整體縮放以符合各種螢幕, 內容不隨裝置重新排版.
- 透過產生三種風格預覽讓使用者用眼睛挑選風格, 而非用抽象文字描述喜好.
- 支援匯出為 PDF 或部署到 Vercel 取得可分享的網址.

觸發方式: 使用者要求製作簡報, 將 PPT/PPTX 轉為網頁版, 或需要一份用於演講或提案的投影片.

### knowledge-youtube-to-markdown

將知識型的 YouTube 影片或整個頻道的影片批次轉換為有明確來源依據, 易於閱讀的 Markdown 學習筆記.

- 支援單一影片與頻道/播放清單兩種模式, 批次處理時會先建立清單並套用使用者指定的篩選條件.
- 內容來源優先順序為: 創作者提供的字幕, 原始語言的自動字幕, 使用者提供的逐字稿, 或本地轉錄的音訊/影片.
- 產出內容為改寫過的學習筆記而非逐字稿, 並明確區分原始來源內容與編輯者補充的說明.
- 批次處理會建立 README.md 作為索引, 並以 batch-status.json 記錄可續跑的處理狀態.

觸發方式: 要求將 YouTube 影片或頻道轉換為 Markdown 筆記, 涉及字幕, 逐字稿, 教學摘要或影片索引等需求.

### programmatic-video

完全以程式產生含配樂的宣傳片, 產品廣告, 預告片或片頭, 不需要 ffmpeg 執行檔.

- 以 NumPy, OpenCV, PIL 逐格繪製畫面, 程序化合成配樂與音效, 再以 PyAV 輸出 MP4.
- 提供共用模組 videokit.py, 涵蓋緩動, 雜訊, 文字, 剪影邊緣光, 後製調色, 音訊混音與平行編碼.
- 需要寫實人物時, 可搭配 PixelForge 等影像/影片生成 MCP 產生片段後再剪接調色.
- 附四個完整案例原始碼 (手機廣告, 主機板廣告, 影集預告, 寫實人物預告), 以及驗證成品串流, 長度與音量的腳本.

觸發方式: 要求以程式製作或渲染影片, 廣告, 宣傳片, 預告片或片頭.

### video-to-editable-slides

將簡報型態的影片還原重建為結構化的投影片, 預設輸出可編輯的 Markdown 與自成一體的 HTML 簡報, 依需求另外產生 PowerPoint 與 PDF.

- 從影片中擷取中繼資料, 字幕, 章節, 具代表性的畫面截圖, 轉場與視覺風格, 以及口白內容.
- 會合併漸進式動畫的多個畫面狀態, 判斷哪些元素應重建為可編輯物件, 哪些應保留為畫面截圖.
- 提供忠實重現, 專業重製, 僅大綱三種重建模式, 預設採用專業重製.
- 所有格式由同一份投影片規格 JSON 產生. Markdown 與 HTML 只用 Python 標準函式庫; pptx 使用 python-pptx, PDF 使用 ReportLab, 皆不依賴 Microsoft PowerPoint.

觸發方式: 提供 YouTube 連結或本地影片檔案, 要求還原為投影片.

## Commands

### /learndoc

檢視目前所在資料夾, 為專案撰寫一份詳細的繁體中文 LEARN.md 文件. 內容涵蓋技術架構, 程式碼庫結構, 技術選型的原因, 以及可從中學習的經驗, 例如遇到的錯誤與修復方式, 未來可能的陷阱等.

### /md2course

將一份 Markdown 筆記或文件檔案轉換為自成一體的互動式學習用 HTML 頁面, 視覺風格採用深色主題, 每個章節依內容類型自動搭配對應的互動元件, 例如步驟導覽, 對照面板, 參數卡片等.

## 使用方式

1. 將本儲存庫的 skills 與 commands 目錄內容複製或連結至 Claude Code 的設定路徑下 (例如 `~/.claude/skills` 與 `~/.claude/commands`).
2. Skill 的使用需由使用者以 slash command 明確發起, Claude Code 不會自動判斷並觸發.
3. 使用 `/learndoc` 或 `/md2course` 時, 依照各自檔案中的說明操作即可.

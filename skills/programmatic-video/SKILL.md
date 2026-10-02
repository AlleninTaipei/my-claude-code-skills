---
name: programmatic-video
description: Create promo videos, product commercials, trailers, title sequences or cinematic shorts entirely by code (NumPy/OpenCV/PIL frames, procedurally synthesized music and sound, PyAV MP4 export, no ffmpeg binary needed), optionally with realistic people via an image/video generation MCP such as PixelForge. Use this whenever the user asks to make, render, or programmatically generate a video, ad, 宣傳片, 廣告, 預告片, 片頭, launch film or "AI native workflow" video experiment, even if they only paste a prompt like "create a 30 seconds video programmatically" or name a product or show to promote.
---

# Programmatic Video

用程式產生有配樂的宣傳片. 已用四個案例驗證過: 5 秒手機廣告, 30 秒主機板廣告, 30 秒影集預告 (剪影人物), 30 秒寫實人物諜報預告 (AI 混合).

## 檔案

- `scripts/videokit.py`: 共用模組. 包含緩動, 無縫雜訊, 文字, 暗底, 剪影邊緣光, 後製 (bloom/ACES/遮幅), 音訊 `Mixer`, PyAV 平行編碼.
- `scripts/contact_sheet.py`: 把 PNG 或影片指定影格拼成縮圖總表.
- `scripts/verify_video.py`: 驗證成品的串流, 長度, 影格數, 每段音量.
- `references/pure-code.md`: 畫面技法. 寫畫面程式前先讀.
- `references/ai-hybrid.md`: 寫實人物的 AI 生成流程. 需要寫實人物時讀.
- `references/audio.md`: 配樂與音效. 寫音訊前讀.
- `examples/`: 四個完整案例的原始碼, 需要具體寫法時參考.
  - `iphone17/`: 單檔. 2D SDF 手機, 假 3D 旋轉.
  - `taichi/`: 透視相機, 平面貼圖, 凸起物件, 資料脈衝, HUD.
  - `got/`: 骨架剪影人物, 龍, 鐵王座, 火, 雪, 遮幅, 史詩配樂.
  - `jb/`: AI 混合的 30 秒諜報預告. 5 段生成鏡頭, 加上程式做的打字機字卡, 監視器介面與行人追蹤, 訊號地圖, 甩鏡, 快剪標語, 片尾字卡, 驚悚配樂. 只依賴 `scripts/videokit.py`.

在專案程式裡引用工具模組時, Windows 要用正斜線路徑, Git Bash 的 `/c/Users/...` 格式 Python 不認得:

```python
import sys; sys.path.insert(0, r"C:/Users/<user>/.claude/skills/programmatic-video/scripts")
from videokit import *
```

## 流程

### 1. 確認環境與路線

先檢查有哪些工具: `python -c "import numpy, cv2, PIL, av"`, 再看有沒有 blender, ffmpeg, 以及影像生成 MCP. 不要假設. PyAV 本身內建編碼器, 有它就能輸出含音訊的 MP4.

使用者的 prompt 若寫了「可以自由下載工具」, 但使用者在對話中另外說過不要安裝, 以使用者的明確決定為準, 並在交付時說明差異. 安裝大型軟體 (Blender 等) 之前先問.

依主體選擇路線:

| 主體 | 路線 |
|---|---|
| 產品, 標誌, 文字, 抽象科技感 | 純程式, 見 `references/pure-code.md` |
| 人物, 動物 (可接受剪影或風格化) | 純程式剪影 |
| 寫實人臉, 寫實場景 | AI 混合, 見 `references/ai-hybrid.md` |

處理真實品牌, 影集或人物時:
- 不要畫官方標誌, 品牌名稱用一般字型.
- 不要生成真實演員或名人的臉, 改用原創角色.
- 配樂不仿寫知名主題曲.
- 交付時說明這是概念片.

使用者的 prompt 如果有明顯的筆誤或和對話不一致 (例如 iPhone 17 和 18), 照原文做, 但在回覆中指出.

### 2. 分鏡表

先寫出分鏡表, 再寫程式. 分鏡表包含時間, 畫面, 字卡, 音效重點, 並配合配樂節奏:

- 選一個 BPM, 讓每段剛好是整數小節.
- 每段 4 到 5 秒. 依序是開場, 3 到 4 個賣點或場景, 主視覺, 標題.
- 重擊點 (剪接, 劍擊, 螢幕點亮) 定成常數, 畫面和音訊共用同一份.
- AI 混合路線: 生成鏡頭之間穿插程式鏡頭 (介面, 地圖, 字卡). 程式鏡頭不會漂移, 也不用排隊, 可以補足生成片段的可用秒數.

### 3. 專案結構

在使用者的工作目錄下開一個資料夾. 30 秒等級的片子建議拆成:

- `render.py`: 分鏡函式 `shot_xxx(t)`, 回傳線性 HDR 影像. 加上 `render(f)` 處理轉場與後製, 以及 `encode` / `check` 兩種模式.
- `audio.py`: `build_audio(dur)`, 以及共用的時間常數.
- 其他素材模組, 例如 `board.py`, `figures.py`.
- AI 混合路線用 `assemble.py` 取代 `render.py`, 結構相同, 見 `examples/jb/`.

`render.py 60 150 300` 這種「只輸出指定影格的 PNG」模式一定要有. 這是後面自我檢查的基礎.

### 4. 自我檢查迴圈 (最重要)

成品好不好, 主要差在有沒有回頭看. 每一輪:

1. 每個分鏡至少輸出一格, 加上轉場邊界的影格.
2. 用 `contact_sheet.py` 拼成總表, 用 Read 工具實際看圖.
3. 逐項檢查:
   - 字卡在背景上讀得清楚嗎?
   - 物件方向對嗎 (文字有沒有顛倒或鏡像)?
   - 有沒有接縫, 色塊, 全白格?
   - 主體比例自然嗎?
   - 字卡和主體重疊了嗎?
4. 修正後只重出有問題的影格確認.

通常需要 2 到 3 輪. 修掉的問題要記下來, 交付時列出.

### 5. 全片輸出與驗證

- 全片渲染放背景執行 (`run_in_background`), log 寫進檔案. 等待時先跑 `loudness_report` 檢查音訊.
- 完成後跑 `verify_video.py`, 再用 `contact_sheet.py` 從成品影片抽格看一次.

### 6. 交付

回覆中包含:

- 檔案路徑與規格: 解析度, fps, 長度, 編碼, 大小.
- 分鏡表: 時間, 畫面, 字卡.
- 做法摘要: 用了哪些工具, 沒有安裝什麼, 沒有用哪些外部素材.
- 自我檢查修掉的問題.
- 已知限制, 寫清楚:
  - 只看過畫面, 沒有實際聽過聲音.
  - 規格數字或平台名稱是依記憶寫的, 請使用者確認.
  - 這是概念片, 不是官方作品.
- 重新輸出的指令.

## 常見問題

| 現象 | 原因與處理 |
|---|---|
| 字卡看不清楚 | 先用 `scrim` 墊暗底. 還是有亮圖案透出來, 就把字卡移到暗區 |
| 文字顛倒或鏡像 | 3D 座標系統手性錯誤. 高度存成 `-z`, 相機 up 向量要對 |
| 雲, 火捲動時有直線接縫 | 改用 `videokit.fbm` 的無縫版本 |
| 火或光變成白色光柱 | HDR 值太高, 被 ACES 壓白. 降低數值, 顏色偏紅橘 |
| 雪或粒子像灑在物體上的髒點 | 粒子要畫在主體之前的背景層 |
| 人物像火柴人 | 四肢加粗 (腿約身高 0.09), 加肩甲和衣擺 |
| 標題超出畫面而報錯 | 字距動畫的起始值太大. 先計算寬度, 再加裁切保護 |
| 遠景閃爍 | 透視貼圖縮小時要選 mip 層級 |
| 轉場中間灰霧 | 交叉淡化時不要再疊加白光 |
| 整格全白太久 | 閃光峰值控制在 1 到 2 格 |
| OpenCV 線條有鋸齒 | `LINE_AA` 只對 uint8 有效. 先畫在 uint8 遮罩, 再合成到 float 影像 |
| AI 片段後段變成另一張臉 | 身分漂移. 只用前 3 到 3.5 秒. 主角朝鏡頭跑近時, 第 40 格左右就會漂移, 見 `references/ai-hybrid.md` |
| 生成的車子出現真實品牌標誌 | 用編輯模型去除反而會畫出更清楚的標誌. 改在靜態底圖上用 `cv2.inpaint` 抹掉, 再做圖轉影片 |
| 監視器底圖變成魚眼圓框, 還多一台攝影機 | 提示詞寫 "fills the entire rectangular frame, flat rectilinear perspective", negative 加 fisheye, circular frame |
| 追蹤框被遮幅擋住 | 以底部為基準放大素材, 追蹤從目標清楚的那一格往前後兩個方向做, 目標進入遮幅時隱藏追蹤框 |
| Windows 多行程卡住或報錯 | 呼叫 `encode` 的程式碼要放在 `if __name__ == "__main__":` 之下 |

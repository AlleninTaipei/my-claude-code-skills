# AI 混合路線: 寫實人物與場景

畫面交給生成模型, 剪接, 調色, 字卡, 配樂交給程式. 範例: `examples/jb/` (30 秒, 舊路線 Wan 2.2 做的, 組裝程式仍可參考).

## 影片生成模型: 限定 MiniMax H3

使用者的決定 (2026-10-05): 影片生成一律用 H3, 不再用 Wan 2.2, LTX-2.3, SkyReels. light (4 分鐘 MV) 和 phantom (3 分鐘品牌片) 都是用 Wan 2.2 5B 做的, 成品不理想. 主要問題是 5 秒無聲片段, 身分與動作在後段漂移, 每個鏡頭要各自換臉, 47 段片段很難剪成一致的作品.

| 用途 | 範本 | 說明 |
|---|---|---|
| 正式片段 (全部) | 多模態參考 `9b2ad098...` | ref2va, 20 步. 192 格 1344x768 實測約 9 分鐘 |
| 只用來測參考接法 | 多模態參考・快速 `70132056...` | ref2va + 8 步 Turbo, 768x448 5 秒約 1 分鐘. 不要當正式片段: 實測 (phantom_h3) 常出現兩個畫面半透明疊在一起的溶接疊影, 手部糊成一團, 192 格約 3 分 50 秒 |
| 必須從指定的第一格開始 | 讓圖片動起來 (示範) `50062350...` | H3 i2v. 示範範本, 穩定性未驗證. 提示詞格式不同, 見下方 |
| 沒有任何參考的空景 | 文字生成影片 (示範) `8568165c...` | H3 t2v. 示範範本, 約 25 分鐘, 少用 |

以下 H3 規則整理自範本的 prompting guide, 尚未在本 skill 的案例中實測. 第一個用 H3 的案例做完後, 要把實測結果補回這份文件.

## 何時使用

- 需要寫實人臉或寫實場景. 純程式只能做剪影或風格化.
- 環境中有 PixelForge MCP (`mcp__pixelforge__*`) 且有 H3 範本. 沒有 H3 時, 先告訴使用者, 問要不要改用其他模型或改成剪影, 風格化路線, 不要自行換回 Wan.

## 倫理界線

- 只生成虛構人物. 不要生成可辨識的真實人物, 例如演員或名人, 即使使用者要求重現某部作品的角色也一樣. 改用原創角色, 用髮型, 髮色, 鬍子, 飾品 (耳環, 鼻環, 眼鏡), 服裝細節區分角色.
- 不要用疤痕, 傷口, 油漬, 痣等臉部痕跡當特徵. phantom 的定裝照寫了「眉毛上一道細疤」「鼻樑小傷」「臉頰油漬」, 生成模型把它們畫成明顯的紅色刀痕; 換臉時又逐項要求保留, 疤越畫越大, 結果一支品牌片的主角全帶著新傷. 劇情真的需要傷痕時, 才在那個鏡頭的提示詞裡寫.
- 使用者指定電影或影集 IP 時 (例如 Jason Bourne), 先問片名與角色要直接使用還是改成「風格原創」. 成品要放進對外簡報時, 建議選風格原創.
- 不要用官方標誌. 品牌名稱用一般字型呈現, 合作夥伴的 end card 用中性灰色, 不用對方的品牌色. 交付時說明這是概念片.
- 對外發布時, 建議使用者標示內容由 AI 生成.

## 流程

開始前先 `list_templates`, 對要用的範本 `get_template` 讀 prompting guide. 範本內容會更新, 以 guide 為準.

### 1. 角色定裝照

- 高品質文生圖 (`da4e7bfe...` Qwen-Image 20B, 約 30 秒), 1024x1280 直式, 腰部以上.
- 一段散文: 年齡, 臉型, 眼睛, 髮型, 髮色, 鬍子, 飾品, 服裝材質, 姿勢, 寫明 "clear, unblemished skin", 結尾 `Ultra HD, 4K, cinematic composition.` negative 加 `scar, cut, wound, blood, mark on face`.
- 背景要用接近黑色的暗底 ("plain near-black background, soft frontal key light"), 不要用中性灰底. H3 會把參考圖的背景當成環境: phantom_h3 第 5 段用灰底定裝照, 整段的暗車庫變成淺灰攝影棚; 換成暗底後恢復正常. 已經是灰底的定裝照, 用洪水填充 (固定容差, 從四邊起算) 把灰底換成暗底, 只清掉貼著背景的低彩度小塊, 白色衣服的陰影不要動 (見 phantom_h3/darkbg.py).
- 下載後放大看臉. 有疤或痕跡時:
  - 先試高品質單圖編輯 (`c6d7a8f5...`, negative 有效). 實測 4 張只修好 1 張, 另外 2 張的疤只變淡.
  - 修不掉就用 `cv2.inpaint`: 在疤的周圍框一個小範圍, 以 LAB 色彩空間找出比周圍更紅或更暗的像素當遮罩, 膨脹後 inpaint, 遮罩邊緣柔化. 放大前後對照確認.
- 這張是身分依據, 檢查後就不要再換. 參考圖上的任何痕跡和背景都會被 H3 複製到每個鏡頭. ref2va 直接把它當 `<Picture N>` 參考, 不需要先做換臉關鍵影格.

### 2. 環境與道具參考 (選用)

- 需要固定場景或產品外觀時, 文生圖做一張 16:9 環境圖 (1664x928) 或道具圖, 當另一張 `<Picture N>`.
- 生成場景常自帶真實品牌字樣 (車尾標誌, 油箱字, 顯示卡字). 下載後放大檢查, 像真實品牌的用 `cv2.inpaint` 抹掉再上傳; 無意義的小亂碼抹掉反而留下糊塊, 可以保留.
- 螢幕, 看板上要出現品牌字時, 參考圖畫成全黑空白螢幕, 字在組裝時用程式貼 (見下方「品牌字樣」).

### 3. 分鏡改以「段落」為單位

H3 ref2va 一次生成 5 到 14 秒, 裡面可以有多個 CUT, 同一次生成內的身分會保持一致. 所以分鏡表不再是「每 3 秒一段獨立片段」, 而是:

- 一個生成 = 一個段落 (例如一位角色的一場戲), 8 秒 (192 格, 唯一剛好對齊網格的長度) 或 14 秒, 2 到 4 個 CUT.
- 30 秒的片子約 3 到 4 次生成, 3 分鐘的片子約 15 到 22 次. 先估總時間 (見時間表), 太長就增加程式鏡頭 (字卡, 介面, 產品 macro) 的比例.
- 每次生成只放這個段落真正需要的參考. 每個角色參考要在大部分 CUT 中出現: 只出現在不到約 20% CUT 的角色參考, 會把他的臉套到主角身上 (guide 的實測). 配角用不到那麼多畫面時, 那個參考槽改放道具或環境.
- 群體鏡頭 (3 人以上) 尚未驗證. 先用快速版小尺寸試, 不行就改成全身遠景讓臉維持小尺寸.

### 4. 上傳參考

- `get_upload_url(template_id, param_id="5_references")`, 用 `curl -F "file=@x.png" "<url>"` 上傳, 回傳的 `filename` 就是 key. 一張 ticket 可以上傳同一個參數的多個檔案, 15 分鐘失效.
- 生成過的圖用 `use_output_as_input(job_id, filename, template_id, param_id="5_references")` 轉過去.
- 預算: 圖片 9, 影片 3, 音訊 3, 共 12 個; 每段影片或音訊 2 到 15 秒, 影片合計 15 秒, 獨立音訊合計 15 秒.
- `5_references` 是一個有順序的列表, 放在 `extras`. 標籤依序編號: 圖片 `<Picture 1..>`, 影片 `<Video 1..>`, 音訊 `<Audio 1..>`. 影片設 `include_audio: true` 時, 它的音軌先佔一個 `<Audio N>`. 不要自己推算, 讀 `generate_media` 回傳的 `references.tags`.
- 參考影片只傳動作, 運鏡, 節奏, 不太傳風格; 會被截到輸出的長度; 不要先加黑邊 (黑邊會被複製).

### 5. 提示詞 (ref2va)

```
<風格與光線一句>. Use <Picture 1> as the character reference for the woman chef
and <Picture 2> as the kitchen environment reference; her face, short black bob,
silver hoop earrings and white chef jacket stay consistent in every cut.

CUT 1: Medium close-up as the chef in <Picture 1> tastes sauce from a silver
spoon held at chin height, the camera pushes in with small amplitude at slow
speed. A soft clink of the spoon against the pot and the hiss of the stove.

CUT 2: ...
```

- 第一句就給每個標籤一個工作. 沒被點名的參考會自己變成一個鏡頭.
- 每個 CUT 一行: 鏡頭大小, 主體, 一個連續動作, 運鏡 (類型, 幅度 small/large, 速度 slow/fast).
- 聲音寫在造成它的那個句子裡, 不要另起一段. 音樂寫成動態 ("a rising synth chord swells and holds").
- 比例錨點 (相對人體部位) 要在每個 CUT 內重寫, 只寫在開頭會被 CUT 行覆蓋.
- 全部用肯定句. 沒有 negative 欄位, 點名不要的東西反而會生出來. 把參考圖已有的臉, 顏色, 材質重述一次, 並說它保持一致.
- 狀態詞 ("lit", "working") 畫不出來, 要寫看得見的訊號 ("fans spin with motion-blurred blades", "screen light falling across the glass").
- H3 會只做手勢而漏掉物件: 物件要獨立寫成看得見的主體, 動作只給一個, 用肯定句寫結束狀態.
- 對白: `<d>[English] It fits in one hand.</d> spoken in the voice of <Audio 2>.` 一個 CUT 只會唸一個 `<d>`. 中文接近逐字, 英文日文逐字.
- CUT 數不保證 (6 個 CUT 在 9.4 秒內只回來 5 個), 組裝時要自己偵測實際的切點.

H3 i2v / t2v 示範範本用廠商的三段格式, 不是 CUT 格式:

```
For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.

integrated_multimodal_description: [Shot 1] Live-action, cinematic, ... The camera trucks right with small amplitude at slow speed as ...

overall_soundscape: ...

non_diegetic_music: ... (沒有配樂就寫 N/A)
```

(t2v 省略第一行.)

### 6. 送件, 時間與佇列

- 先用快速版, 768x448, 5 秒試一次新的參考組合, 確認標籤對應與 warnings, 再用 20 步版出正式尺寸.
- 正式尺寸用原生畫布 1344x768. 1920x1088 是訓練面積的兩倍, 很慢.
- 長度用 `extras={"15_seconds": n}`, 影格數往上對齊: 5 秒 = 124 格 (5.17 秒), 8 秒 = 192 格, 14 秒 = 345 格.
- 一次只排一個 H3 工作. 同時送兩個沒有加速, 第三個會失敗. 送出後等它完成再送下一個 (背景輪詢 `get_job`, 或 `wait_for_job` 移到背景).
- 時間 (20 步高品質, 1344x768): 124 格約 4 分 52 秒, 192 格實測約 9 分鐘, 226 格約 13 分, 345 格約 38 分. 3 分鐘的片子約 20 段, 約 3 小時.
- 圖片工作 (定裝, 環境圖) 全部完成後再開始送影片. 影片和圖片共用 GPU, 後送的影片會插隊.
- `generate_media` 每分鐘最多 30 個. 工作可能在伺服器端失敗 (`Something went wrong`), 用 `get_job` 取得實際輸出檔名, 不要用連號猜.

### 7. 檢查生成片段

- 用場景變化偵測找出片段內實際的 CUT 切點 (相鄰格的灰階差異突增), 把每個 CUT 當成一個可用的鏡頭.
- 每個 CUT 抽頭, 中, 尾三格拼成檢查條, 看身分, 道具, 動作是否照提示詞, 有沒有參考圖亂入成獨立鏡頭.
- 聽不到聲音, 但要量每段的音量: 不同生成之間音量可能差到約 25 dB.

### 8. 組裝

- 解碼成 `cache/<name>.npy` (uint8, 縮放到輸出尺寸), worker 用 `np.load(mmap_mode="r")` 共用. 1344x768 不是 16:9, 縮到 1280 寬後是 1280x731, 上下各裁 5 到 6 列.
- 剪接表用 (片段, 素材起點, 時間軸起點, 速度), 每段到下一段起點為止.
- H3 片段自帶音訊 (環境音, 對白, 甚至配樂). 每段要決定: 保留對白與環境音 (做響度正規化, 壓在配樂下), 或整段靜音只用配樂與程式音效. 同一支片要一致, 不要有的段落有環境音, 有的沒有.
- 生成鏡頭之間穿插程式鏡頭 (字卡, 介面, 地圖, 產品特寫), 不會漂移, 不用排隊, 品牌文字最精準. 做法見 `pure-code.md` 第 5.5 節.
- 統一調色, 遮幅, 暗角, 顆粒. 剪接點加短閃光或黑場, 對齊配樂重擊.
- 輸出 24fps, 和 H3 一致.

## 配樂

- 程式合成: 見 `audio.md`.
- PixelForge MiniMax Music 3 (`12031e6a...`):
  - 可以生成有人聲的完整歌曲, 上限 180 秒.
  - 歌詞每個段落標籤 (`[verse]` 等) 獨立一行, 同一行的字會被丟掉.
  - 純音樂的長度主要由段落標籤數量決定: 7 個約 85 秒, 11 個約 150 秒.
  - 生成的純音樂整首起伏常常很平, 段落感要靠程式音效補.
  - 歌詞超過一首能容納的長度時, 拆段生成: 同 seed, 同一段 Vocal Details, 接點選在本來就安靜的地方.
  - PyAV 解碼 FLAC 得到 `(1, 2N)` 交錯陣列, 要 reshape 成 `(2, N)`.
- 歌詞對時: faster-whisper medium, `word_timestamps=True`. 文字用原稿, 只取時間.
- 對拍: onset envelope 自相關估 BPM 與相位, 剪接點吸附到拍點. 用 0.1 到 0.5 秒窗的 RMS 找「先靜後爆」的落差, 對齊最重要的畫面.

## 品牌字樣與畫面中的字

- 讓 AI 在螢幕上寫品牌字既不準又有風險. 參考圖或提示詞寫 "a colossal screen that is completely black and empty", 組裝時用程式貼字.
- 鏡頭在動時, 每格用 `connectedComponentsWithStats` 找畫面中上方最大的暗區當螢幕外框, 字的大小和位置跟著外框走.

## 附錄: 舊路線 (Wan 2.2 i2v, 已停用) 的紀錄

保留下來是為了知道要檢查什麼, 不要再用這條路線.

- 5 秒無聲片段, 後段常身分漂移, 動作反轉 (拉起鐵門又拉下), 服裝長出校徽, 闖入多餘的人, 人物衝向鏡頭. 通常只能用前 2 到 3 秒.
- 每個鏡頭都要先做換臉關鍵影格 (多參考圖編輯 `9cce9e46...`), 四人同框兩次換臉失敗.
- light: 47 段片段, phantom: 45 段片段, 全流程各約 3.5 小時, 大部分在排隊, 成品不理想.

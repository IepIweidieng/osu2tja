# osu2tja

[English](README.md)|**简体中文**

.osu ⟷ .tja 转换器，支持 Python 3。

`.osu` (osu! Beatmap) 是 osu! 游戏所使用的仅包含单一难度的谱面格式。`.osz` (osu! Beatmap Archive) 是 osu! 中单一歌曲所使用的包含多份 `.osu` 文件与资源的标准压缩格式。

`.tja` 或 TJA (缩写意义不明，可能是“Taiko (Tatsu)jin Another”) 是受多种模拟器支持的太鼓谱面格式，例如太鼓次郎、太鼓大次郎、Malody、TJAPlayer3、OpenTaiko、Project OutFox。

包含两支主要工具：osz2tja、tja2osz。

## ⚠️ 注意事项 ⚠️

若谱面不由您创作，转换后的谱面亦不为您所有，仅能作个人使用。

若您欲公开发布不由您所创作的转换后谱面，请事先取得谱面原作者的同意。我们不支持剽窃他人的创作，且会强烈谴责这类行为。

## 執行环境要求

- Python 3.10+
- ffmpeg (选用，由 osz2tja 使用)

### ffmpeg

若 ffmpeg 已安装或在 `osz2tja.py` 的所在目录下，osz2tja 会自动将音频文件转换为 `.ogg` 格式。

在此下载 ffmpeg：<https://www.ffmpeg.org/download.html>

下载后，解压井复制 `bin/ffmpeg.exe` 到 `osz2tja.py` 的所在目录即可。

## osz2tja

本工具由 @SamLangTen 建立

### 用法

```bash
python osz2tja.py [input_folder] [output_folder]
```

示例：

```bash
python osz2tja.py
```

或

```bash
python osz2tja.py a_folder b_folder
```

- `[input_folder]` 为 `.osz` 文件所在的位置。若省略，默认为 `Songs`。
- `[output_folder]` 为转换后的 `.tja` 文件和音频文件的输出位置。若省略，默认为 `Output`。

osz2tja 会在 `[output_folder]` 中为每个生成的 `.tja` 文件创建一个文件夹。

### 功能

- **批量转换** `.osz` 谱面文件为 `.tja` 谱面文件。（@MoshirMoshir）
- 自动映射 osu! 难度（每个 `.tja` 最多 5 个）为 TJA 的 **Edit**（里魔王）、**Oni**（魔王）、**Hard**（困难）、**Normal**（普通）和 **Easy**（简单）难度。（@MoshirMoshir；改进至 5 个），（改进）会考虑 osu! 难度名。
- **超过 5 个难度**的 Beatmap 会拆为多份 `.tja`（例如 `title - 1`、`title - 2`）。（@MoshirMoshir；改进至必要时才加后缀）
- **有多个音乐文件**（不可上架，但可見于部分社区喜爱（Loved）谱面）的 Beatmaps 或**有多个游戏模式**也会拆为多份 `.tja`。（新功能）
- **自动复制**谱面所使用的音频文件（@SamLangTen；**自动 OGG 转换** —— @k2angel）、（新功能）以及背景图片、与其它文件。

## tja2osz

本工具由 @MoshirMoshir 建立

### 用法

```bash
python tja2osz.py [input_folder] [output_folder]
```

示例：

```bash
python tja2osz.py
```

或

```bash
python tja2osz.py a_folder b_folder
```

- `[input_folder]` 为 `.tja` 文件所在的位置（可在任意内部目录中）。若省略，默认为 `Songs`。
- `[output_folder]` 为转换后的 `.osu` 文件和音频文件的输出位置。若省略，默认为 `Output`。

tja2osz 会在 `[output_folder]` 中为每个已处理的 `.tja` 文件创建一个文件夹，其中包含转换后的 `.osu` 文件和音频文件。并且 tja2osz 会在 `[output_folder]` 中为转换后的 `.osu` 文件创建 `.osz` 文件。

### 功能

- **批量转换** `.tja` 谱面文件为 `.osz` 谱面文件。（新功能）
- 自动拆分各个难度、玩家侧、谱面分歧主路線为各自的 `.osu` 难度文件。（已修正）
- **自动复制**谱面所使用的音乐音频、背景图片、与其它文件。（新功能）

## 转换细节

### osu2tja

本工具由 @delguoqing 建立

- 输入（`.osu`）（使用 osz2tja 时由 `.osz` 提取）：
  - [x] osu file format v3\~14, v128（有测试过的；其他版本会警告而继续处理）（改进）
  - [x] 编码：无 BOM 的 UTF-8
- TJA 标头
  - [x] taiko 模式
  - [x] std、（改进）mania、catch 模式转谱
  - [x] 小数时间偏移，見于 osu file format v128（用于 osu!lazer）（新功能）
  - [x] 警告并忽略分析失败的行（改进）
- 输出（`.tja`）
  - [x] 编码：Shift-JIS（若可）或（新功能）帶 BOM 的 UTF-8。
  - [x] 浮点数精度：Python 內置 `float` (IEEE 754 binary64) 精度，（改进）输出不限位数的最简小数。
- TJA 标头
  - 元数据标头
    - [x] osu2tja 水印（移至 TJA 文件首行）
    - [x] `TitleUnicode:`/`Title:` + （新功能）非太鼓 `Mode:` → `TITLE:`
    - [x] `Source:` **和/或** `ArtistUnicode:`/`Artist:` → `SUBTITLE:`（@k2angel），（改进）使用 `Artist / From " Source "` 格式
    - [x] `Artist:` 或 `ArtistUnicode:` → `ARTIST:`（Malody 用）（新功能）
    - [x] `AudioFilename:` → `WAVE:`，（@SamLangTen）自动文件复制，（@k2angel）OGG 转换
    - [x] `PreviewTime:` → `DEMOSTART:`，（新功能）经 osu! 校准误差修正
    - [x] `Creator:` → `MAKER:`（@MoshirMoshir）&（新功能）`AUTHOR:`（Malody 用）
    - [x] 时间点：音效音量（取最大）→ `SEVOL:` ÷ `SONGVOL:`（新功能）
  - 美术标头
    - [x] 首个左右置中背景事件：文件名 → `PREIMAGE:` & `COVER:`（Malody 用）（新功能）
    - [ ] ~~首个左右置中背景事件：文件名 → `BGIMAGE:`~~（计划外）
    - [x] 首个左右置中视频事件：文件名 → `BGMOVIE:`（新功能）
    - [x] 首个左右置中视频事件：起始时间 → `MOVIEOFFSET:`，经 osu! 校准误差修正（新功能）
    - [ ] 故事板事件 → TJAPlayer3-Extended 的 OBJ 命令（计划外）
  - 音频同步标头
    - [x] 初始 BPM → `BPM:`（纯显示用），​（新功能）​各难度可異，​（新功能）输出不限位数的最简小数
    - [x] 首拍时间 → `OFFSET:`（改进），（新功能）​​各难度可異，（新功能）-15 毫秒音乐误差修正（format v4 与更早版本再额外 +24 毫秒）
      - `OFFSET:` 取音乐开始为止最后一拍的开始时间，仿 osu!（稳定版）。delguoqing 版是取最早的音符或时间点。
      - 由於历史原因，osu! 上架谱面与完全校准相比有約 +15 毫秒的音乐误差。使用 format v4 与更早版本的上架谱面有额外的 -24 毫秒音乐误差（共 -9 毫秒）。
  - 难度标头
    - [x] `Version:` → `COURSE:` & TJA 注释（新功能）
    - [ ] `Version:` → `NOTESDESIGNER<n>:`（客串制谱者的难度）（TODO）
    - [ ] `Creator:` → `NOTESDESIGNER<n>:`（其他）（TODO）
    - [x] 难度按 `OverallDifficulty:` 排序 → `COURSE:`（@SamLangTen；自动化 —— @MoshirMoshir；改进为含 `COURSE:Edit`）
    - [x] `OverallDifficulty:` → `LEVEL:`（@SamLangTen）
      - TODO：使用实际的 osu! 难度星数。
    - [x] 转盘：时长 → `BALLOON:`（以官方公式改进以计入 `OverallDifficulty:`（可能仍会差 1、2 打））
- TJA 命令
  - [x] 非继承时间点：BPM → `#BPMCHANGE`，（改进）取绝对值
  - [x] 非继承时间点：小节拍数 → `#MEASURE`，（改进）取绝对值，（新修正）防止歌曲不以 4/4 拍号开始时谱面不同步
  - [x] 不完整小节 → （改进）量化 `#MEASURE` + 未量化 `#MEASURE` + `#DELAY`（崩溃修正 —— @delguoqing；改进至小数毫秒精度，适用于 TJAPlayer3 系列与 OpenTaiko），（新修正）防止未量化部分包含未来小节的命令与音符
    - （新修正）防止输出的小节或最后音符使用错误的时间点而造成谱面不同步甚至无穷回圈
  - [x] 不完整小节或（改进）osu! 计时舍入造成的计时误差 → 以 `#DELAY` 修正
  - [x] `SliderMultiplier:` → 整个谱面的基本 `#SCROLL` 倍率（新功能）
  - [x] 继承时间点：滑条速度变化 & （改进）非继承时间点：BPM 正负号 → `#SCROLL`（没限制范围），（改进）允许负数
  - [x] 时间点：Kiai 时间 → `#GOGOSTART` & `#GOGOEND`
  - [x] 时间点：隐藏首个小节线 → `#BARLINEOFF` & `#BARLINEON`（新功能）
  - [x] 最后音符或时间点位置 + 最大 1 秒留白 → `#END`（改进）
- TJA 音符定义
  - 乐理计时
    - [x] 相对小节头尾的时间偏移 → 节拍等分数
    - [x] 小节中音符间命令插入（改进、新功能）
    - [x] 2 毫秒精度（新功能）
      - 音符与时间点会根据目前 BPM 量化成 2 毫秒以内的 192 分音符（1/48 拍）的 2 的乘幂次分割。
    - [x] 模拟 osu! 与 TJAPlayer3 的计时舍入误差（新功能）
      - TODO：再模拟太鼓次郎 1 的计时舍入误差以改进谱面兼容性
  - 音符符号
    - [x] （std 模式）短滑条转为圆圈（以官方算法改进）
    - [x] （mania 模式）长键转为圆圈（新功能）
      - TODO：长键转为长条连打，并处理重叠音符。
    - [x] （mania 模式，> 1 轨）依轨道位置而不依音效决定咚／咔（新功能）
      - 轨道配置（D = 咚、K = 咔）：KD(D)、KDDK、KKDD(DD)K、KKDDDDKK、KKKDDDD(DD)KK、KKKDDDDDDKKK、KKKKDDDDDD(DD)KKK、……
    - [x] 空白 → `0`（空白）
    - [x] 圆圈，一般或咚轨道，非 finish 音效 → `1`（小咚）
    - [x] 圆圈，whistle/clap 或咔轨道，非 finish 音效 → `2`（小咔）
    - [x] 圆圈，一般或咚轨道，finish 音效 → `3`（大咚）
    - [x] 圆圈，whistle/clap 或咔轨道，finish 音效 → `4`（大咔）
    - [x] 滑条，非 finish 音效 → `5` + `8`（小条连打）
    - [x] 滑条，finish 音效 → `6` + `8`（大条连打）
    - [x] 转盘，非 finish 音效 → `7` + `8`（一般气球连打）
    - [x] 转盘，finish 音效 → `9` + `8` (特殊气球连打)（新功能）

### tja2osu

本工具由 @delguoqing 建立

- 输出（`.osu`）（使用 tja2osz 时打包为歌曲资料夹与 `.osz`）：
  - [x] osu file format v14（改进）
  - [x] 编码：无 BOM 的 UTF-8
  - [x] 浮点数精度：Python 內置 `float` (IEEE 754 binary64) 精度，（改进）输出不限位数的最简小数。
- 输入（`.tja`）
  - [x] 编码：UTF-8、GBK、Shift-JIS、& Big5 猜一（改进）
  - [x] 警告并忽略分析失败的行（改进）
  - [x] 会忽略 TJA `//` 注释，（改进）曲名、副标题、谱面作者的 TJA 标头除外
  - [x] 避免误分析 TJA 标头或命令（例如将 `//#NMSCROLL` 当作 `#N`，`#LYRIC #END` 当作 `#END` 与 `#E`）（修正）
- TJA 标头
  - 元数据标头
    - [x] osu2tja 水印（新功能）
    - [x] `TITLE:` & `SUBTITLE:` → `Title:`，（新功能）支持带或不带 BOM 的 UTF-8，（新功能）`SUBTITLE:` 匹配特定模式时接在 `TITLE:` 后
    - [x] `SUBTITLE:` & `GENRE:` → `Artist:` & `Source:`，（新功能）基于多个常见模式与关键字，（改进）未知 `Artist:` 时改用 `ARTIST:` 标头，未知 `Source:` 预设为空
    - [x] `ARTIST:` → `Artist:`（新功能），（改进）预设为 `Unknown Artist`
    - [x] `MAKER:`/`AUTHOR:`/`//created by ` → `Creator:`（新功能）（默认为 `unknown`）
    - [x] ? → `Tags:`（默认为 `tja`（改进））
    - [x] `GENRE:` → `Tags:`（新功能）
    - [ ] `NOTESDESIGNER<n>:` → `Tags:`（为客串制谱者时）（TODO）
    - [x] `WAVE:` → `AudioFilename:`，（新功能）自动文件复制
    - [x] ? → `AudioLeadIn:`（默认为 `0`）（改进）
    - [x] `DEMOSTART:` → `PreviewTime:`（已修正），（新功能）经 osu! 校准误差修正
    - [x] ? → `CountDown:`（默认为 `0`（false））
    - [x] ? → `SampleSet:`（默认为 `Normal`）
    - [x] `StackLeniency:0.7`（无效果）
    - [x] ? → `Mode:`（默认为 `1`（太鼓））
    - [x] ? → `LetterboxInBreaks:`（默认为 `0`（false））（改进）
    - [x] `SEVOL:` ÷ `SONGVOL:` → 时间点：音效音量（新功能）
  - 美术标头
    - [x] `BGIMAGE:`/`PREIMAGE:`/`COVER:` → 背景事件：文件名，自动文件复制（新功能）
    - [x] `BGMOVIE:` → 视频事件：文件名，自动文件复制（新功能）
    - [x] `MOVIEOFFSET:` → 视频事件：开始时间，经 osu! 校准误差修正（新功能）
    - [ ] TJAPlayer3-Extended 的 OBJ 命令 → 故事板事件（计划外）
  - 音频同步标头
    - [x] `BPM:` → 初始非继承时间点：BPM，（新功能）默认为 120 以符合太鼓次郎行为
    - [x] `OFFSET:` → 初始非继承时间点：时间，（新功能）+15 毫秒音乐误差修正
      - 由於历史原因，osu! 上架谱面与完全校准相比有約 +15 毫秒的音乐误差。
  - 难度标头
    - [x] `STYLE:` → `Version:`（新功能）
    - [x] `COURSE:` → `Version:`（默认为 `Oni`）（改进）
      - 在首个有效 `COURSE:` 前的标头，各难度共用；之后的标头，各难度独立（改进）
    - [ ] `NOTESDESIGNER<n>:` → `Version:<notesdesigner>'s <course>`，`<notesdesigner>` 不为 `<maker>`/`<author>` 时（TODO）
    - [x] `COURSE:` + `LEVEL:` → `HPDrainRate:`（新功能）
      - 默认 `Easy` 为 `8`，`Normal` 为 `7`，`Hard` 与 8+ 星的其他难度为 `6`，其他为 `5`，基于音符数不多时的上架谱面准则下限（改进）
    - [x] `CircleSize:5`（无效果）
    - [x] `ApproachRate:5`（无效果）
    - [x] `COURSE:` → `OverallDifficulty:`（新功能）
      - `Easy`、`Normal` 为 `2.3`：良±42.5ms、可±100.5ms、不可±115.5ms，近似太鼓简单、普通的良判定幅
      - `Hard` 为 `5`：良±34.5ms、可±79.5ms、不可±94.5ms，上架谱面准则上限
      - 其他难度为 `8`：良±25.5ms、可±61.5ms、不可±79.5ms，近似太鼓困难、魔王的良判定幅
    - [x] ？ → `SliderMultiplier:`（默认为 `1.4`（osu!taiko 预设音符间距））
      - `1.4` 是 osu! 上架谱面的标准，基于部分 AC15 之前的游戏。
      - `1.44` 会更接近 AC15~。
    - [ ]（取众数）节拍等分数 → `SliderTickRate:`（TODO）（默认为 `4`（16 分音符））
    - [x] `HEADSCROLL:` → 初始继承时间点：滑条速度变化（新功能）
- TJA 命令
  - [ ] `#START` → 非继承时间点：高小节拍数 + 隐藏首个小节线 +（可选）不完整小节（TODO）
  - [x] `#START P<n>` → 玩家侧 TJA 中的 `#START`（新功能）
  - [x] `#END`/文件结尾 → 非继承时间点：高小节拍数 + 隐藏首个小节线（新功能）
  - [x] `#BRANCHSTART` → 分歧拆分段落开始
    - TODO：检测并回避不可能的分歧路线
  - [x] `#N`/`#E`/`#M` → 拆分为分歧 TJA
    - FIXME：省略部分分歧分支会造成缺少小节的间题。
  - [x] `#BRANCHEND` → 分歧共通部分开始（新修正）
  - [x] `#BPMCHANGE`，正 → 非继承时间点：BPM
    - 每拍毫秒数的绝对值限制在 6×10^-298 到 6×10^298 之间以避免 osu! 崩溃。
  - [x] `#BPMCHANGE`，负，正的 (小节长 ÷ BPM) → 非继承时间点：BPM 取绝对值（新功能）
  - [x] `#MEASURE`，正整数拍数 → 非继承时间点：小节拍数（改进），（新功能）小数參数
  - [x] `#MEASURE`，正非整数拍数 → 非继承时间点：小节拍数 + 不完整小节（改进），（新功能）小数參数
  - [x] 小节途中的 `#MEASURE` 会视为在小节头处理，同太鼓次郎（改进）。
  - [x] 负的 (小节长 ÷ BPM) 或大的负 `#DELAY` → 非完全递增时间序的谱面事件，依时间重新排序（新功能）
    - FIXME：被覆盖的小节的小节线会被忽略不转换
  - [x] `#DELAY` → 移动谱面定义游标的时间
    - FIXME：`#DELAY` 之后的小节线会显示错误，错到下个生成的非继承时间点。
  - [x] `#SCROLL`，正的 (scroll × BPM) → 继承时间点：滑条速度变化
    - FIXME：用 BPM 变化绕过 osu! 滑条速度变化会锁在 0.01x 到 10x 之间的限制。
  - [x] 非正/复数的（scroll × BPM）→ 继承时间点：滑条速度变化取绝对值（新功能）
  - [ ] `#SUDDEN`，有正停止时长 → 继承时间点：经调整的滑条速度变化（TODO）
  - [x] `#GOGOSTART` & `#GOGOEND` → 时间点：Kiai 时间
  - [x] `#BARLINEOFF` & `#BARLINEON` → 时间点：隐藏首个小节线（新功能）
  - [ ] `#BARLINE` → 将小节拆分为（可能）不完整的小节（TODO）
  - [ ] `#BARLINESCROLL` → 继承时间点：在每个小节线和小节线后首音符加上滑条速度变化；原本的小节头有音符时，拆分出隐藏首个小节线的 1 毫秒小节（TODO）
- TJA 音符定义
  - 乐理计时
    - [x] 无音符符号的小节 (`,`) → 完整小节（新修正）
    - [x] 小节中间的 `#BPMCHANGE`
    - [x] (小节长 ÷ 节拍等分数 ÷ 各等分 BPM) 总和 → 相对小节头的时间偏移 (修正了带 `#SCROLL` 的非整数拍小节的错误)
    - [x] 毫秒精度（新功能）
      - `tja2osu.py` 提供 `--beat-align` 选项，可量化谱面物件至指定的拍子等分上（新改进）。
      - FIXME：非预期的额外小节线可能会紧接（约 1 毫秒程度）在（可能隐藏的）小节线（对应非继承时间点（红线））之前出现。
  - 音符符号
    - [x] `0`（空白）→ 空白
    - [x] `1`（小咚）→ 圆圈，默认音效
    - [x] `2` (小咔) → 圆圈，clap 音效
    - [x] `F` (ad-lib) → 空白
    - [x] `C`（炸弹/地雷）→ 空白
    - [x] `3`（大咚）→ 圆圈，finish 音效
    - [x] `A`（牵手大咚）→（大咚）圆圈，finish 音效（新功能）
    - [x] `4`（大咔）→ 圆圈，clap finish 音效
    - [x] `B`（牵手大咔）→（大咔）圆圈，clap finish 音效（新功能）
    - [x] `G`（咔咚）→（大咔）圆圈，whistle + clap finish 音效（新功能）
    - [x] `5`（小条连打头）→ 滑条，默认音效
    - [x] `I`（小/咔？条连打头）→（小条连打）滑条，clap 音效（新功能）
    - [x] `6`（大条连打头）→ 滑条，finish 音效
    - [x] `H`（大/咚？条连打头）→（大条连打）滑条，clap finish 音效（新功能）
    - [x] `7`（一般气球连打头）→ 转盘，默认音效
    - [x] `9`（特殊气球连打头）→ 转盘，finish 音效（改进）
    - [x] `D`（计时弹气球连打头）→（一般气球）转盘，clap 音效（新功能）
    - [x] 连打类音符头，未结尾的连打类音符后 → 空白
    - [x] `8`（显式连打尾），未结尾的连打类音符后 → 前一个滑条/转盘尾
    - [x] 击打类音符，未结尾的连打类音符后 → 前一个滑条/转盘強制结尾（改进）
    - [x] `#END`（命令）/文件结尾，未结尾的连打类音符后 → 前一个滑条/转盘強制结尾（新功能）
    - [x] `8`，单独出現 → 空白（新功能）
    - [x] 连打类音符，非正时长 → 空白（新功能）

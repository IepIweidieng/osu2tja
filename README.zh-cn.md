# osu2tja

[English](README.md)|**简体中文**

.osu ⟷ .tja 转换器，支持 Python 3。

`.osu` (osu! Beatmap) 是 osu! 游戏所使用的仅包含单一难度的谱面格式。`.osz` (osu! Beatmap Archive) 是 osu! 中单一歌曲所使用的包含多份 `.osu` 文件与资源的标准压缩格式。

`.tja` 或 TJA (缩写意义不明，可能是“Taiko (Tatsu)jin Another”) 是受多种模拟器支持的太鼓谱面格式，例如太鼓次郎、太鼓大次郎、Malody、TJAPlayer3、OpenTaiko、Project OutFox。

包含两支主要工具：osz2tja、tja2osz。

## 執行环境要求

- Python 3.x
- ffmpeg (选用，由 osz2tja 使用)

### ffmpeg

若 ffmpeg 已安装或在 `osz2tja.py` 的所在目录下，osz2tja 会自动将音频文件转换为 `.ogg` 格式。

在此下载 ffmpeg：<https://www.ffmpeg.org/download.html>

下载后，解压井复制 `bin/ffmpeg.exe` 到 `osz2tja.py` 的所在目录即可。

## osz2tja

### 用法

```bash
python osz2tja.py [input_folder] [output_folder]
```

示例：

```bash
python osz2tja.py a_folder b_folder
```

- `[input_folder]` 为 `.osz` 文件所在的位置。若省略，默认为 `Songs`。
- `[output_folder]` 为转换后的 `.tja` 文件和音频文件的输出位置。若省略，默认为 `Output`。

osz2tja 会在 `[output_folder]` 中为每个生成的 `.tja` 文件创建一个文件夹。

### 功能

- **批量转换** `.osz` 谱面文件为 `.tja` 谱面文件。（@MoshirMoshir）
- 自动映射 osu! 难度（每个 `.tja` 最多 5 个）为 TJA 的 **Edit**（里魔王）、**Oni**（魔王）、**Hard**（困难）、**Normal**（普通）和 **Easy**（简单）难度。（@MoshirMoshir；改进至 5 个）
- **超过 5 个难度**的 Beatmap 会拆为多份 `.tja`（例如 `title - 1`、`title - 2`）。（@MoshirMoshir；改进至必要时才加后缀）
- **有多个音乐文件**的 Beatmaps（不可上架，但可見于部分社区喜爱（Loved）谱面）也会拆为多份 `.tja`。（新功能）
- **自动复制**谱面所使用的音频文件（@SamLangTen；**自动 OGG 转换** —— @k2angel）、背景图片、与其它文件。（新功能）

### 转换细节

- [x] 输入：osu file format v4\~14（有测试过的；其他版本会警告而继续处理）（改进）
- 输入：
  - osu file format v4\~14（有测试过的；其他版本会警告而继续处理）（改进）
  - taiko 模式
  - std、mania（改进）、catch 模式转谱
  - 小数时间偏移（見于用 osu!lazer 创建或用第三方工具转换的谱面）（新功能）
- TJA 标头
  - 元数据标头
    - [x] osu2tja 水印（移至 TJA 文件首行）
    - [x] `TitleUnicode:`/`Title:` → `TITLE:`
    - [x] `Source:` **和/或** `ArtistUnicode:`/`Artist:` → `SUBTITLE:`（@k2angel）
    - [x] `AudioFilename:` → `WAVE:`，自动文件复制（@SamLangTen），OGG 转换（@k2angel）
    - [x] `PreviewTime:` → `DEMOSTART:`
    - [x] `Creator:` → `MAKER:`（@MoshirMoshir）
    - [x] `Creator:` → `AUTHOR:`（Malody 用）（新功能）
    - [ ] 时间点：音效音量（取最大）→ `SEVOL:` ÷ `SONGVOL:`（TODO）
  - 美术标头
    - [x] 首个置中背景事件：文件名 → `PREIMAGE:`（新功能）
    - [ ] ~~首个置中背景事件：文件名 → `BGIMAGE:`~~（计划外）
    - [x] 首个置中视频事件：文件名 → `BGMOVIE:`（新功能）
    - [x] 首个置中视频事件：起始时间 → `MOVIEOFFSET:`（新功能）
    - [ ] 故事板事件 → TJAPlayer3-Extended 的 OBJ 命令（计划外）
  - 音频同步标头
    - [x] 初始 BPM → `BPM:`（纯显示用，取 2 位小数），​​各难度可異（新功能）
    - [x] 首拍时间 → `OFFSET:`（改进），​​各难度可異（新功能），-15 毫秒音乐误差修正（format v4 与更早版本再额外 +24 毫秒）（新功能）
      - `OFFSET:` 取音乐开始为止最后一拍的开始时间，仿 osu!。delguoqing 版是取最早的音符或时间点。
      - 由於历史原因，osu! 上架谱面与完全校准相比有約 +15 毫秒的音乐误差。使用 format v4 与更早版本的上架谱面有额外的 -24 毫秒音乐误差（共 -9 毫秒）。
  - 难度标头
    - [x] `Version:` & `Mode:` → TJA 注释（纯参考用）（新功能）
    - [ ] `Version:` → `NOTEDESIGNER<n>:`（客串制谱者的难度）（TODO）
    - [ ] `Creator:` → `NOTEDESIGNER<n>:`（其他）（TODO）
    - [x] 难度按 `OverallDifficulty:` 排序 → `COURSE:`（@SamLangTen；自动化 —— @MoshirMoshir；改进为含 `COURSE:Edit`）
    - [x] `OverallDifficulty:` → `LEVEL:`（@SamLangTen）
      - TODO：使用实际的 osu! 难度星数。
    - [x] 转盘：时长 → `BALLOON:`（以官方公式改进以计入 `OverallDifficulty:`（可能仍会差 1、2 打））
- TJA 命令
  - [x] 非继承时间点：BPM → `#BPMCHANGE`
  - [x] 非继承时间点：小节拍数 → `#MEASURE`
  - [x] 不完整小节 → `#MEASURE` + 可能的 `#DELAY`（崩溃修正 —— @delguoqing；改进至毫秒精度）
  - [x] `SliderMultiplier:` → 整个谱面的基本 `#SCROLL` 倍率（新功能）
  - [x] 继承时间点：滑条速度变化 → `#SCROLL`（没限制范围）
  - [x] 时间点：Kiai 时间 → `#GOGOSTART` & `#GOGOEND`
  - [ ] 时间点：隐藏首个小节线 → `#BARLINEOFF` & `#BARLINEON`（TODO）
- TJA 音符定义
  - 乐理计时
    - [x] 相对小节头尾的时间偏移 → 节拍等分数
    - [x] 小节中音符间命令插入（改进、新功能）
    - [ ] 毫秒精度（TODO）
      - 目前全都会先量化成 96 分音符（1/24 拍）。
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
    - [x] 转盘，**任意**音效 → `7` + `8`（一般气球连打）
    - [ ] 转盘，finish 音效 → `9` + `8` (特殊气球连打)（TODO）

## tja2osz

### 用法

```bash
python tja2osz.py [input_folder] [output_folder]
```

示例：

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

### 转换细节

- [x] 输出：osu file format v14（改进）
- [x] 会忽略 TJA `//` 注释
  - FIXME：拆分 TJA 时 `//` 注释不会禁用命令。
- TJA 标头
  - 元数据标头
    - [x] osu2tja 水印（新功能）
    - [x] `TITLE:` → `Title:`，支持带或不带 BOM 的 UTF-8（新功能）
    - [ ] `SUBTITLE:` → `Artist:`（TODO）（目前默认为 `unknown`）
    - [x] `MAKER:`/`AUTHOR:`/`//created by ` → `Creator:`（新功能）（默认为 `unknown`）
    - [x] `SUBTITLE:` → `Source:`（已修正），支持带或不带 BOM 的 UTF-8（新功能）
    - [x] ? → `Tags:` (默认为 `taiko jiro tja`)
    - [ ] `GENRE:` → `Tags:`（TODO）
    - [ ] `NOTESDESIGNER<n>:` → `Tags:`（为客串制谱者时）（TODO）
    - [x] `WAVE:` → `AudioFilename:`，自动文件复制（新功能）
    - [x] ? → `AudioLeadIn:`（默认为 `0`）（改进）
    - [x] `DEMOSTART:` → `PreviewTime:`（已修正）
    - [x] ? → `CountDown:`（默认为 `0`（false））
    - [x] ? → `SampleSet:`（默认为 `Normal`）
    - [x] `StackLeniency:0.7`（无效果）
    - [x] ? → `Mode:`（默认为 `1`（太鼓））
    - [x] ? → `LetterboxInBreaks:`（默认为 `0`（false））（改进）
    - [x] `SEVOL:` ÷ `SONGVOL:` → 时间点：音效音量（新功能）
  - 美术标头
    - [x] `BGIMAGE:`/`PREIMAGE:` → 背景事件：文件名，自动文件复制（新功能）
    - [x] `BGMOVIE:` → 视频事件：文件名，自动文件复制（新功能）
    - [x] `MOVIEOFFSET:` → 视频事件：开始时间（新功能）
    - [ ] TJAPlayer3-Extended 的 OBJ 命令 → 故事板事件（计划外）
  - 音频同步标头
    - [x] `BPM:` → 初始非继承时间点：BPM
    - [x] `OFFSET:` → 初始非继承时间点：时间，+15 毫秒音乐误差修正（新功能）
      - 由於历史原因，osu! 上架谱面与完全校准相比有約 +15 毫秒的音乐误差。
  - 难度标头
    - [x] `STYLE:` → `Version:`（新功能）
    - [x] `COURSE:` → `Version:`（默认为 `Oni`）（改进）
    - [ ] `NOTESDESIGNER<n>:` → `Version:<notesdesigner>'s <course>`，`<notesdesigner>` 不为 `<maker>`/`<author>` 时（TODO）
    - [ ] `COURSE:` + `LEVEL:` → `HPDrainRate:`（TODO）（默认为 `7`（大致为太鼓魔王 10 星入魂难度）（改进）））
    - [x] `CircleSize:5`（无效果）
    - [x] `ApproachRate:5`（无效果）
    - [ ] `COURSE:` + `LEVEL:` → `OverallDifficulty:`（TODO）（默认为 `8.333`（太鼓困难、魔王的良判定幅）（改进）
    - [x] ？ → `SliderMultiplier:`（默认为 `1.44`（AC15~ 音符间距））
    - [ ]（取众数）节拍等分数 → `SliderTickRate:`（TODO）（默认为 `4`（16 分音符））
    - [ ] `HEADSCROLL:` → 初始继承时间点：滑条速度变化（TODO）
- TJA 命令
  - [ ] `#START` → 非继承时间点：高小节拍数 + 隐藏首个小节线 +（可选）不完整小节（TODO）
  - [x] `#START P<n>` → 玩家侧 TJA 中的 `#START`（新功能）
  - [x] `#END`/文件结尾 → 非继承时间点：高小节拍数 + 隐藏首个小节线（新功能）
  - [x] `#BRANCHSTART` → 分歧拆分段落开始
    - TODO：检测并回避不可能的分歧路线
  - [x] `#N`/`#E`/`#M` → 拆分为分歧 TJA
    - FIXME：省略部分分歧分支会造成缺少小节的间题。
  - [ ] `#BRANCHEND` → 分歧共通部分开始
    - FIXME：`#BRANCHEND` 有被识别但被忽略。
  - [x] `#BPMCHANGE`，正 → 非继承时间点：BPM
  - [ ] `#BPMCHANGE`，负，正的 (小节长 ÷ BPM) → 非继承时间点：BPM 取绝对值（TODO）
  - [x] `#MEASURE`，正整数拍数 → 非继承时间点：小节拍数（改进），小数參数（新功能）
  - [x] `#MEASURE`，正非整数拍数 → 非继承时间点：小节拍数 + 不完整小节（改进），小数參数（新功能）
  - [ ] 负的 (小节长 ÷ BPM) → 非完全递增时间序的谱面事件，依时间重新排序（TODO）
  - [x] `#DELAY` → 移动谱面定义游标的时间
    - FIXME：`#DELAY` 之后的小节线会显示错误，错到下个生成的非继承时间点。
    - FIXME：使用大的负 `#DELAY` 时，生成的事件可能不会是正确递增时间序。
  - [x] `#SCROLL`，正的 (scroll × BPM) → 继承时间点：滑条速度变化
    - FIXME：用 BPM 变化绕过 osu! 滑条速度变化会锁在 0.01x 到 10x 之间的限制。
  - [ ] 非正/复数的（scroll × BPM）→ 继承时间点：滑条速度变化取绝对值（TODO）
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
    - [ ] 毫秒精度（TODO）
      - 目前全都会先量化成 96 分音符（1/24 拍）。
  - 音符符号
    - [x] `0`（空白）→ 空白
    - [x] `1`（小咚）→ 圆圈，默认音效
    - [x] `2` (小咔) → 圆圈，clap 音效
    - [ ] `F` (ad-lib) → = 小咚/咔？（TODO）
    - [ ] `C`（炸弹/地雷）→ = 小咚/咔？空白？（TODO）
    - [x] `3`（大咚）→ 圆圈，finish 音效
    - [ ] `A`（牵手大咚）→ 圆圈，finish 音效（TODO）
    - [x] `4`（大咔）→ 圆圈，clap finish 音效
    - [ ] `B`（牵手大咔）→ 圆圈，clap finish 音效（TODO）
    - [ ] `G`（咔咚）→ = 大咚/咔？（TODO）
    - [x] `5`（小条连打头）→ 滑条，默认音效
    - [ ] `I`（小/咔？条连打头）→ = 小条连打头？（TODO）
    - [x] `6`（大条连打头）→ 滑条，finish 音效
    - [ ] `H`（大/咚？条连打头）→ = 大条连打头？（TODO）
      - FIXME：长条连打內的 `#BPMCHANGE` 与 `#SCROLL` 会造成滑条长度计算错误，使时长不正确。
    - [x] `7`（一般气球连打头）→ 转盘，默认音效
    - [x] `9`（特殊气球连打头）→ 转盘，默认音效
      - TODO：用 finish 音效表示差异
    - [ ] `D`（计时弹气球连打头）→ = 一般气球连打？（TODO）
    - [ ] 连打类音符头，未结尾的连打类音符后 → 空白（TODO）
    - [x] `8`（显式连打尾），未结尾的连打类音符后 → 前一个滑条/转盘尾
    - [ ] 击打类音符，未结尾的连打类音符后 → 前一个滑条/转盘強制结尾（TODO）
    - [ ] `#END`（命令），未结尾的连打类音符后 → 前一个滑条/转盘強制结尾（TODO）
    - [ ] `8`，单独出現 → 空白（TODO）
    - [ ] 连打类音符，非正时长 → 空白（TODO）

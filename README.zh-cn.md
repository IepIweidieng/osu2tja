# osu2tja

[English](README.md)|**简体中文**

.osu ⟷ .tja 转换器，支持 Python 3。

`.osu` (osu! Beatmap) 是 osu! 游戏所使用的仅包含单一难度的谱面格式。`.osz` (osu! Beatmap Archive) 是 osu! 中单一歌曲所使用的包含多份 `.osu` 文件与资源的标准压缩格式。

`.tja` 或 TJA (缩写意义不明，可能是“Taiko (Tatsu)jin Another”) 是受多种模拟器支持的太鼓谱面格式，例如太鼓次郎、太鼓大次郎、Malody、TJAPlayer3、Project OutFox。

包含两支主要工具：osz2tja、tja2osu。

## osz2tja

只需简单地输入以下命令：
```
python osz2tja.py <源.osz文件名> <输出路径>
```

osz2tja会读取.osz内的所有.osu子谱面，并输出：
```
====== Difficulty Selection ======
Index  Difficulty  Version
(0):   8           xxxx(Insane)
(1):   6           ddddd(Hard)
(2):   4           ddsadf(Normal)
(3):   2           xxxxx(Easy)
Oni:
Hard:
Normal:
Easy:
```

根据提示匹配OSU的难度版本和太鼓达人的难度。

例如，如果要将“xxxx(Insane)”版本与太鼓的魔王难度匹配，则在“Oni:”提示后输入“0”。
如果您想禁用难度，请输入“-1”。

匹配后osz2tja会生成.tja文件，并将音频文件解压到输出路径下以title命名的文件夹中。

### ffmpeg

若 ffmpeg 已安装或在 `osz2tja.py` 的所在目录下，osz2tja 会自动将音频文件转换为 `.ogg` 格式。

在此下载 ffmpeg：<https://www.ffmpeg.org/download.html>

下载后，解压井复制 `bin/ffmpeg.exe` 到 `osz2tja.py` 的所在目录即可。

## tja2osu

只需简单地输入以下命令：
```
python tja2osu/tja2osu_file_dvide.py <source .tja filename>
```

tja2osu 会自动分割可游玩的难度与谱面分歧为个別的 `.tja` 文件到 `tmp/` 目录下，
并生成对应的 `.osu` 文件到 `out/` 目录下。

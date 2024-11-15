# osu2tja

[English](README.md)|**简体中文**

.osu ⟷ .tja 转换器，支持 Python 3。

`.osu` (osu! Beatmap) 是 osu! 游戏所使用的仅包含单一难度的谱面格式。`.osz` (osu! Beatmap Archive) 是 osu! 中单一歌曲所使用的包含多份 `.osu` 文件与资源的标准压缩格式。

`.tja` 或 TJA (缩写意义不明，可能是“Taiko (Tatsu)jin Another”) 是受多种模拟器支持的太鼓谱面格式，例如太鼓次郎、太鼓大次郎、Malody、TJAPlayer3、Project OutFox。

包含两支主要工具：osz2tja、tja2osz。

## 執行环境要求

- Python 3.x

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

- **批量转换** `.osz` 谱面文件为 `.tja` 谱面文件。
- 自动映射 osu! 难度（每个 `.tja` 最多 5 个）为 TJA 的 **Edit**（里魔王）、**Oni**（魔王）、**Hard**（困难）、**Normal**（普通）和 **Easy**（简单）难度。
- 支持**超过 5 个难度**的 Beatmap，会拆为多份 `.tja`（例如 `title - 1`、`title - 2`）。
- **自动调整难度等级**：拆分的 `.tja` 之间的难度星级会加以调整，使高难度的等级较高。
  > **不**一定会符合太鼓难度等级基准，因为 osu! 的难度等级范围比太鼓来得大。
- **自定义文件夹支持**：可指定输入和输出文件夹。
- **其他元数据**：生成的 `.tja` 文件包含谱面作者信息。

### ffmpeg

若 ffmpeg 已安装或在 `osz2tja.py` 的所在目录下，osz2tja 会自动将音频文件转换为 `.ogg` 格式。

在此下载 ffmpeg：<https://www.ffmpeg.org/download.html>

下载后，解压井复制 `bin/ffmpeg.exe` 到 `osz2tja.py` 的所在目录即可。

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

- **批量转换** `.tja` 谱面文件为 `.osz` 谱面文件。
- **自定义文件夹支持**：可指定输入和输出文件夹。

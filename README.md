# osu2tja

**English**|[简体中文](README.zh-cn.md)

An .osu ⟷ .tja converter, for Python 3.

`.osu` (osu! Beatmap) is the single-difficulty chart format for the game osu!. `.osz` (osu! Beatmap Archive) is the standard zipped form containing multiple `.osu` files and resources for a song entry in osu!.

`.tja` or TJA (unknown acronym, likely "Taiko (Tatsu)jin Another") is a Taiko chart format supported by many simulators, such as TaikoJiro, Taiko-san Daijiro, Malody, TJAPlayer3, and Project OutFox.

It contains 2 major tools: osz2tja & tja2osz.

## Requirements

- Python 3.x

## osz2tja

### Usage

```bash
python osz2tja.py [input_folder] [output_folder]
```

Example:

```bash
python osz2tja.py a_folder b_folder
```

- `[input_folder]` is where your `.osz` files are located. Defaults to `Songs` if omitted.
- `[output_folder]` is where the converted `.tja` files and audio files will be saved. Defaults to `Output` if omitted.

osz2tja will create a folder in `[output_folder]` for each generated `.tja` file.

### Features

- **Batch conversion** of `.osz` files to `.tja` files.
- Automatically maps osu! difficulties (up to 5 per `.tja` file) to TJA **Edit** (Taiko: Inner/Ura Oni or Extra Extreme), **Oni** (Taiko: Extreme), **Hard**, **Normal**, and **Easy** difficulties.
- Supports Beatmaps with **more than 5 difficulties** by splitting them into multiple `.tja` files (e.g., `title - 1`, `title - 2`).
- **Adjusted star scaling**: Difficulty stars are adjusted between splitted `.tja` files to keep higher stars for higher difficulties.
  > Note that these star assignments **ARE NOT** equlivent to the typical Taiko star ratings since osu! has a much broader difficulty range than Taiko.
- **Custom folder support**: You can specify custom input and output folders.
- **Additional metadata**: Each generated `.tja` file includes the creator information.

### ffmpeg

If ffmpeg is installed or placed under the same directory as `osz2tja.py`, osz2tja will automatically convert the audio file into `.ogg` format.

Get ffmpeg here: <https://www.ffmpeg.org/download.html>

After downloading, unzip it and copy `bin/ffmpeg.exe` into the same directory as `osz2tja.py`, and the conversion should now work.

## tja2osz

### Usage

```bash
python tja2osz.py [input_folder] [output_folder]
```

Example:

```bash
python tja2osz.py a_folder b_folder
```

- `[input_folder]` is where your `.tja` files are located (can be in any inner directories). Defaults to `Songs` if omitted.
- `[output_folder]` is where the converted `.osu` files and audio files will be saved. Defaults to `Output` if omitted.

tja2osz will create a folder in `[output_folder]` for each processed `.tja` file. This folder will contain converted `.osu` files and audio file. tja2osz will also create an `.osz` file in `[output_folder]` for these `.osu` files.

### Features

- **Batch conversion** of `.tja` files to `.osz` files.
- **Custom folder support**: You can specify custom input and output folders.

# osu2tja

**English**|[简体中文](README.zh-cn.md)

An .osu ⟷ .tja converter, for Python 3.

`.osu` (osu! Beatmap) is the single-difficulty chart format for the game osu!. `.osz` (osu! Beatmap Archive) is the standard zipped form containing multiple `.osu` files and resources for a song entry in osu!.

`.tja` or TJA (unknown acronym, likely "Taiko (Tatsu)jin Another") is a Taiko chart format supported by many simulators, such as TaikoJiro, Taiko-san Daijiro, Malody, TJAPlayer3, and Project OutFox.

It contains 2 major tools: osz2tja & tja2osu.

## osz2tja

Just simply input the following command:
```
python osz2tja.py <source .osz filename> <output path>
```

osz2tja will read version files in .osz and exhibit all versions with their overall difficulties, like:
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

Please follow the prompts to match the difficulty versions of OSU and difficulies of Taiko no Tatsujin.

For example, input "0" after the "Oni:" prompt if you want to match "xxxx(Insane)" version to Oni difficulty.
Please input "-1" if you want to disable a difficulty.

After matching, osz2tja will generate .tja file and extract audio file to the output path, with a new-created folder named after title.

### ffmpeg

If ffmpeg is installed or placed under the same directory as `osz2tja.py`, osz2tja will automatically convert the audio file into `.ogg` format.

Get ffmpeg here: <https://www.ffmpeg.org/download.html>

After downloading, unzip it and copy `bin/ffmpeg.exe` into the same directory as `osz2tja.py`, and the conversion should now work.

## tja2osu

Just simply input the following command:
```
python tja2osu/tja2osu_file_dvide.py <source .tja filename>
```

tja2osu will automatically separate all playable difficulties and branches into separate `.tja` files under the `tmp/` directory,
and then generate the corresponding `.osu` files in the `out/` directory.

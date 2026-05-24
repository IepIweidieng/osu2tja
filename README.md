# osu2tja

**English**|[简体中文](README.zh-cn.md)

An .osu ⟷ .tja converter, for Python 3.

`.osu` (osu! Beatmap) is the single-difficulty chart format for the game osu!. `.osz` (osu! Beatmap Archive) is the standard zipped form containing multiple `.osu` files and resources for a song entry in osu!.

`.tja` or TJA (unknown acronym, likely "Taiko (Tatsu)jin Another") is a Taiko chart format supported by many simulators, such as TaikoJiro, Taiko-san Daijiro, Malody, TJAPlayer3, OpenTaiko, and Project OutFox.

It contains 2 major tools: osz2tja & tja2osz.

## ⚠️ IMPORTANT NOTE ⚠️

For charts which aren't authored by you, the converted charts aren't yours either and are for personal use only.

If you want to distribute any converted charts not authored by you, please ask the chart author(s) for permission first. We don't support content stealing and do strictly condemn it.

## Requirements

- Python 3.10+
- ffmpeg (optional, for osz2tja)

### ffmpeg

If ffmpeg is installed or placed under the same directory as `osz2tja.py`, osz2tja will automatically convert the audio file into `.ogg` format.

Get ffmpeg here: <https://www.ffmpeg.org/download.html>

After downloading, unzip it and copy `bin/ffmpeg.exe` into the same directory as `osz2tja.py`, and the conversion should now work.

## osz2tja

Tool created by @SamLangTen

### Usage

```bash
python osz2tja.py [input_path] [output_path]
```

Example:

```bash
python osz2tja.py
```

or

```bash
python osz2tja.py a_folder b_folder
```

or

```bash
python osz2tja.py song.osz song.tja
```

- `[input_path]` is the `.osz` file or `.osu` directory to convert, or where your `.osz` files or `.osu` directories are located (can be in any inner directories). If omited, defaults to `Songs` in the same directory as `osz2tja.py`.
- `[output_path]` is the `.tja` file to save, or where the converted `.tja` files will be saved. If omitted, defaults to `Output` in the same directory as `osz2tja.py`.
  - If `[output_path]` is the `.tja` file to save, osz2tja will try to generate all `.tja` file with the given path, with suffix added if necessary.
  - Otherwise, osz2tja will create a folder in `[output_path]` for each generated `.tja` file.
  - Resource files are saved into the same directory as each generated `.tja` file.

### Features

- **Batch or individual conversion** of `.osz` files or (@IepIweidieng) `.osu` directories to `.tja` files. (@MoshirMoshir, individual conversion by @IepIweidieng)
- Automatically maps osu! difficulties (up to 5 per `.tja` file) to TJA **Edit** (Taiko: Inner/Ura Oni or Extra Extreme), **Oni** (Taiko: Extreme), **Hard**, **Normal**, and **Easy** difficulties. (@MoshirMoshir; improved to 5 by @IepIweidieng), (improved by @IepIweidieng) considering osu! difficulty names.
- Beatmaps with **more than 5 difficulties** are split into multiple `.tja` files (e.g., `title - 1`, `title - 2`). (@MoshirMoshir; improved to suffix only when necessary by @IepIweidieng)
- Beatmaps with **multiple song audio files** (unrankable but seen in loved beatmaps) or **multiple game modes** are also split into multiple `.tja` files. (@IepIweidieng)
- **Automatically copy** song audio files (@SamLangTen; **automatic OGG conversion** — @k2angel), (@IepIweidieng) as well as background image and other files used by the chart.

## tja2osz

Tool created by @MoshirMoshir

### Usage

```bash
python tja2osz.py [input_path] [output_path]
```

Example:

```bash
python tja2osz.py
```

or

```bash
python tja2osz.py a_folder b_folder
```

or

```bash
python tja2osz.py song.tja song.osz
```

- `[input_path]` is the `.tja` file to convert, or where your `.tja` files are located (can be in any inner directories). If omitted, defaults to `Songs` in the same directory as `tja2osz.py`.
- `[output_path]` is the `.osz` file to save, or where the converted `.osu` files and resource files will be saved. If omitted, defaults to `Output` in the same directory as `tja2osz.py`.
  - If `[output_path]` is the `.osz` file to save, tja2osz will create a single folder named after the `.osz` file as the folder for all processed `.tja` files.
  - Otherwise, tja2osz will create a folder in `[output_path]` for each processed `.tja` file individually.
  - The folder for each processed `.tja` files will contain the converted `.osu` files and resource files. tja2osz will also create an `.osz` file from this folder.

### Features

- **Batch or individual conversion** of `.tja` files to `.osz` files. (@IepIweidieng)
- Automatically split each TJA difficulty, player-side, and each main branch route as a separate `.osu` difficulty file. (bug fix by @IepIweidieng)
- **Automatically copy** song audio, background image, and other files used by the chart (@IepIweidieng)

## Conversion Details

### osu2tja

Tool created by @delguoqing

- Input (`.osu` files) (extracted from `.osz` by osz2tja):
  - [x] osu file format v3&ndash;14, v128 (those tested; warns and continues to process for other versions) (improved by @IepIweidieng)
  - [x] Encoding: UTF-8 (without BOM)
  - [x] taiko mode
  - [x] std, (improved by @IepIweidieng) mania, & catch mode conversion
  - [x] time offsets in decimal, appears in osu file format v128 (for osu!lazer) (@IepIweidieng)
  - [x] warn and ignore lines with parsing errors (improved by @IepIweidieng)
- Output (`.tja`)
  - [x] Encoding: Shift-JIS (if possible) or (@IepIweidieng) UTF-8 (with BOM).
  - [x] Floating number precision: Python builtin `float` (IEEE 754 binary64) precision, (improved by @IepIweidieng) output simpliest decimal without digit count limits.
- TJA Headers
  - Metadata Headers
    - [x] osu2tja watermark (moved to the first line of the TJA file)
    - [x] `TitleUnicode:`/`Title:` + (@IepIweidieng) non-Taiko `Mode:` → `TITLE:`
    - [x] `Source:` **AND/OR** `ArtistUnicode:`/`Artist:` → `SUBTITLE:` (@k2angel), (improved by @IepIweidieng) in `Artist / From " Source "` format
    - [x] `Artist:` or `ArtistUnicode:` → `ARTIST:` (for Malody) (@IepIweidieng)
    - [x] `AudioFilename:` → `WAVE:`, (@SamLangTen) with automatic file copy, (@k2angel) with OGG conversion
    - [x] `PreviewTime:` → `DEMOSTART:`, (@IepIweidieng) with osu! music offset correction
    - [x] `Creator:` → `MAKER:` (@MoshirMoshir) & (@IepIweidieng) `AUTHOR:` (for Malody)
    - [x] timing point: hitsound volume (max) → `SEVOL:` ÷ `SONGVOL:` (@IepIweidieng)
  - Decoration Headers
    - [x] First horizontally centered background event: filename → `PREIMAGE:` & `COVER:` (for Malody) (@IepIweidieng)
    - [ ] ~~First horizontally centered background event: filename → `BGIMAGE:`~~ (not planned)
    - [x] First horizontally centered video event: filename → `BGMOVIE:` (@IepIweidieng)
    - [x] First horizontally centered video event: start time → `MOVIEOFFSET:`, with osu! music offset correction (@IepIweidieng)
    - [ ] Storyboard event → TJAPlayer3-Extended OBJ commands (not planned)
  - Sync Headers
    - [x] initial BPM → `BPM:` (for display only), (@IepIweidieng) for each difficulty, (@IepIweidieng) output simpliest decimal without digit count limits.
    - [x] initial beat time position → `OFFSET:` (improved by @IepIweidieng), (@IepIweidieng) for each difficulty, (@IepIweidieng) with -15ms music offset correction (extra +24ms for format v4 and earlier)
      - The `OFFSET:` is set to the beginning time position of the last beat non-after the audio to mimic osu! behavior. It was the earliest of the first note or the timing point in delguoqing's version.
      - Ranked osu! beatmaps have roughly +15ms music offset than perfect sync due to the historical reasons. Ranked format v4 and earlier beatmaps have additional -24ms music offset (-9ms in total).
  - Difficulty Headers
    - [x] `Version:` → `COURSE:` & TJA comment (@IepIweidieng)
    - [ ] `Version:` → `NOTESDESIGNER<n>:` (for difficulties by guest chart creators) (TODO)
    - [ ] `Creator:` → `NOTESDESIGNER<n>:` (otherwise) (TODO)
    - [x] Difficulties sorted by `OverallDifficulty:` → `COURSE:` (@SamLangTen; automated — @MoshirMoshir; improved to include `COURSE:Edit` by @IepIweidieng)
    - [x] `OverallDifficulty:` → `LEVEL:` (@SamLangTen)
      - TODO: Use the actual osu! star rating.
    - [x] Spinner: Time length → `BALLOON:` (improved using the official formula to account for `OverallDifficulty:` (might still off by 1 or 2 hits) by @IepIweidieng)
- TJA Commands
  - [x] Uninherited timing point: BPM → `#BPMCHANGE`, (improved by @IepIweidieng) use absolute value
  - [x] Uninherited timing point: Beats per bar → `#MEASURE`, (improved by @IepIweidieng) use absolute value, (bug fix by @IepIweidieng) prevent chart from desyncing when song does not start with 4/4 time signature
  - [x] Incomplete bar → (improved by @IepIweidieng) quantized `#MEASURE` + unquantized `#MEASURE` (crash fixed — @delguoqing; improved to ms with decimal place accuracy for TJAPlayer3 series and OpenTaiko by @IepIweidieng), (bug fix by @IepIweidieng) prevent the unquanized part from including commands and notes from future measures
    - (bug fix by @IepIweidieng) prevent the output measure or last notes from using wrong timing point and causing chart desyncs or even infinite loops
  - [x] Timing error due to incomplete bar or (improved by @IepIweidieng) osu! timing rounding → fixed with `#DELAY`
  - [x] `SliderMultiplier:` → Base `#SCROLL` multiplier for whole chart (@IepIweidieng)
  - [x] Inherited timing point: Slider velocity change & (improved by @IepIweidieng) Uninherited timing point: sign of BPM → `#SCROLL` (uncapped range), (improved by @IepIweidieng) allow negative values
  - [x] Timing point: Kiai time → `#GOGOSTART` & `#GOGOEND`
  - [x] Timing point: Omit first bar line → `#BARLINEOFF` & `#BARLINEON` (@IepIweidieng)
  - [x] Latest note or timing point position + maximum 1 second padding → `#END` (improved by @IepIweidieng)
- TJA Note Definition
  - Timing
    - [x] relative time offset to bar start and end → beat division
    - [x] Mid-bar inter-note command insertion (improved by @IepIweidieng)
    - [x] 2ms timing accuracy (@IepIweidieng)
      - Note and timing points are quantized to 2's power divisions of 1/192nds (1/48 beats) within 2ms according to the current BPM.
    - [x] osu! and TJAPlayer3 timing rounding error simulation (@IepIweidieng)
      - TODO: Also simulate TaikoJiro 1 timing rounding error for better chart compatibility
  - Note Symbols
    - [x] (std mode) short slider to circles (improved using the official algorithm by @IepIweidieng)
    - [x] (mania mode) hold to circles (@IepIweidieng)
      - TODO: Hold to bar drumroll with note overlapping priority handling.
    - [x] (mania mode, > 1 keys) convert Don/Katsu by column position instead of hitsound (@IepIweidieng)
      - Layout: KD(D), KDDK, KKDD(DD)K, KKDDDDKK, KKKDDDD(DD)KK, KKKDDDDDDKKK, KKKKDDDDDD(DD)KKK, ...
    - [x] Empty → `0` (blank)
    - [x] Circle, normal or Don column, non-finish hitsound → `1` (regular Don)
    - [x] Circle, whistle/clap or Katsu column, non-finish hitsound → `2` (regular Katsu)
    - [x] Circle, normal or Don column, finish hitsound → `3` (big Don)
    - [x] Circle, whistle/clap or Katsu column, finish hitsound → `4` (big Katsu)
    - [x] Slider, non-finish hitsound → `5` + `8` (regular bar drumroll)
    - [x] Slider, finish hitsound → `6` + `8` (big bar drumroll)
    - [x] Spinner, non-finish hitsound → `7` + `8` (regular balloon roll)
    - [x] Spinner, finish hitsound → `9` + `8` (special balloon roll) (@IepIweidieng)
    - [x] Overlapping same-column notes → Padding `0` to place the end of overlapped note (if need), then using a negative `#DELAY` to return to the start of the overlapping note and place the start. If across timing points, use additional `#DELAY`s for fixing timing. (@IepIweidieng)
    - [x] Simultaneous different-column notes → Single combined note (@IepIweidieng)
      - Two Dons `1`/`3` + `1`/`3` → `3` (big Don)
      - Two Katsus `2`/`4` + `2`/`4` → `4` (big Katsu)
      - One Don one Katsu, or either KaDon `1`/`3`/`G` + `2`/`4`/`G` → `G` (KaDon)
      - Two bar drumrolls `5`/`6` + `5`/`6` → `6` (big bar drumroll)
      - Two balloon rolls `7`/`9` + `7`/`9` → `9` (special balloon roll)

### tja2osu

Tool created by @delguoqing

- Output (`.osu` files) (packed to song folder and `.osz` by tja2osz):
  - [x] osu file format v14 (improved by @IepIweidieng)
  - [x] Encoding: UTF-8 (without BOM)
  - [x] Floating number precision: Python builtin `float` (IEEE 754 binary64) precision, (improved by @IepIweidieng) output simpliest decimal without digit count limits.
- Input (`.tja`)
  - [x] encoding: Guessed among UTF-8, GBK, Shift-JIS, & Big5 (improved by @IepIweidieng)
  - [x] warn and ignore lines with parsing errors (improved by @IepIweidieng)
  - [x] TJA `//` comment ignoring, (improved by @IepIweidieng) except for the TJA headers for song title, subtitle, and chart author.
  - [x] prevent misinterpreting TJA header or command (such as `//#NMSCROLL` as `#N`, `#LYRIC #END` as `#END` and `#E`) (bug fix by @IepIweidieng)
- TJA Headers
  - Metadata Headers
    - [x] osu2tja watermark (@IepIweidieng)
    - [x] `TITLE:` & `SUBTITLE:` → `Title:`, (@IepIweidieng) UTF-8 with(out) BOM support, (@IepIweidieng) `SUBTITLE:` appends to `TITLE:` if matches certain patterns
    - [x] `SUBTITLE:` & `GENRE:` → `Artist:` & `Source:`, (@IepIweidieng) based on many common patterns and keywords, (improved by @IepIweidieng) where unknown `Artist:` fall backs to `ARTIST:` header and unknown `Source:` defaults to empty
    - [x] `ARTIST:` → `Artist:` (@IepIweidieng), (improved by @IepIweidieng) defaults to `Unknown Artist`
    - [x] `MAKER:`/`AUTHOR:`/`//created by ` → `Creator:` (@IepIweidieng) (defaults to `unknown`)
    - [x] ? → `Tags:` (defaults to `tja` (improved by @IepIweidieng))
    - [x] `GENRE:` → `Tags:` (@IepIweidieng)
    - [ ] `NOTESDESIGNER<n>:` → `Tags:` (for guest chart creators) (TODO)
    - [x] `WAVE:` → `AudioFilename:`, (@IepIweidieng) with automatic file copy
    - [x] ? → `AudioLeadIn:` (defaults to `0`) (improved by @IepIweidieng)
    - [x] `DEMOSTART:` → `PreviewTime:` (bug fix by @IepIweidieng), (@IepIweidieng) with osu! offset correction
    - [x] ? → `CountDown:` (defaults to `0` (false))
    - [x] ? → `SampleSet:` (defaults to `Normal`)
    - [x] `StackLeniency:0.7` (no effects)
    - [x] ? → `Mode:` (defaults to `1` (Taiko))
    - [x] ? → `LetterboxInBreaks:` (defaults to `0` (false)) (improved by @IepIweidieng)
    - [x] `SEVOL:` ÷ `SONGVOL:` → Timing point: hitsound volume (@IepIweidieng)
  - Decoration Headers
    - [x] `BGIMAGE:`/`PREIMAGE:`/`COVER:` → Background event: filename, with automatic file copy (@IepIweidieng)
    - [x] `BGMOVIE:` → Video event: filename, with automatic file copy (@IepIweidieng)
    - [x] `MOVIEOFFSET:` → Video event: start time, with osu! offset correction (@IepIweidieng)
    - [ ] TJAPlayer3-Extended OBJ commands → Storyboard event (not planned)
  - Sync Headers
    - [x] `BPM:` → initial uninherited timing point: BPM, (@IepIweidieng) defaults to 120 for matching TaikoJiro behavior
    - [x] `OFFSET:` → initial uninherited timing point: time, (@IepIweidieng) with +15ms music offset correction
      - Ranked osu! beatmaps have roughly +15ms music offset than perfect sync due to the historical reasons.
  - Difficulty Headers
    - [x] `STYLE:` → `Version:` (@IepIweidieng)
    - [x] `COURSE:` → `Version:` (defaults to `Oni`) (improved by @IepIweidieng)
      - Headers before the first value `COURSE:` are shared by all difficulties, and headers after it are independent in each difficulty (improved by @IepIweidieng)
    - [ ] `NOTESDESIGNER<n>:` → `Version:<notesdesigner>'s <course>` when `<notesdesigner>` isn't `<maker>`/`<author>` (TODO)
    - [x] `COURSE:` + `LEVEL:` → `HPDrainRate:` (@IepIweidieng)
      - Defaults to `8` for `Easy`, `7` for `Normal`, `6` for `Hard` or 8+ star other difficulties, and `5` for other difficulties, based on the lower-limit of ranking guideline if note count is not high (improved by @IepIweidieng)
    - [x] `CircleSize:5` (no effects)
    - [x] `ApproachRate:5` (no effects)
    - [x] `COURSE:` → `OverallDifficulty:` (@IepIweidieng)
      - `2.3` for `Easy` and `Normal`: GREAT/GOOD ±42.5ms, OK ±100.5ms, BAD ±115.5ms, approximately Taiko Easy & Normal GREAT/GOOD window
      - `5` for `Hard`: GREAT/GOOD ±34.5ms, OK ±79.5ms, BAD ±94.5ms, upper-limit of ranking guideline
      - `8` for other difficulties: GREAT/GOOD ±25.5ms, OK ±61.5ms, BAD ±79.5ms, approximately Taiko Hard & Oni GREAT/GOOD window)
    - [x] ? → `SliderMultiplier:` (defaults to `1.4` (osu!taiko default note spacing))
      - `1.4` is the standard of Ranked osu! beatmaps and is based on some games before AC15.
      - `1.44` would be more accurate for AC15&ndash;.
    - [ ] (Mostly-used) beat division → `SliderTickRate:` (TODO) (defaults to `4` (1/16th))
    - [x] `HEADSCROLL:` → initial inherited timing point: Slider velocity change (@IepIweidieng)
- TJA Commands
  - [ ] `#START` → Uninherited timing point: Large beats per bar + omit first bar line + (optional) incomplete bar (TODO)
  - [x] `#START P<n>` → `#START` in player-side TJA (@IepIweidieng)
  - [x] `#END`/end-of-file → Uninherited timing point: Large beats per bar + omit first bar line (@IepIweidieng)
  - [x] `#BRANCHSTART` → Begin branch-split section
    - TODO: detect and avoid impossible branch routes
  - [x] `#N`/`#E`/`#M` → Split into branch TJA
    - FIXME: Omitting some branches causes missing bars.
  - [x] `#BRANCHEND` → Begin branch-common section (bug fix by @IepIweidieng)
  - [x] `#BPMCHANGE`, positive → Uninherited timing point: BPM
    - The absolute value of milliseconds per beat is capped between 6×10^-298 to 6×10^298 to prevent osu! from crash.
  - [x] `#BPMCHANGE`, negative, with positive (bar length ÷ BPM) → Uninherited timing point: absolute-valued BPM (@IepIweidieng)
  - [x] `#MEASURE`, positive integer beats → Uninherited timing point: Beats per bar (improved by @IepIweidieng), (@IepIweidieng) float values
  - [x] `#MEASURE`, positive fraction beats → Uninherited timing point: Beats per bar + incomplete bar (improved by @IepIweidieng), (@IepIweidieng) float values
  - [x] Mid-measure `#MEASURE`s are handled as if they were at the head of the measure as in TaikoJiro (improved by @IepIweidieng)
  - [x] Negative (bar length ÷ BPM) or large negative `#DELAY` → Notechart events are not in completely increasing time order, re-sorted by time (@IepIweidieng)
    - Each bar line of overlapped measures is converted as a visible bar line on the topmost measure. (improved by @IepIweidieng)
  - [x] `#DELAY` → move time of definition cursor
    - The time of visible bar lines after `#DELAY` is also moved. (improved by @IepIweidieng)
  - [x] `#SCROLL`, with positive (scroll × BPM) → Inherited timing point: Slider velocity change
    - FIXME: Use BPM changes to work around the slider velocity change being capped between 0.01x to 10x in osu!.
  - [x] Non-positive/complex-valued (scroll × BPM) → Inherited timing point: Absolute-valued slider velocity change (@IepIweidieng)
  - [ ] `#SUDDEN`, with positive stop duration → Inherited timing point: Scaled slider velocity change (TODO)
  - [x] `#GOGOSTART` & `#GOGOEND` → Timing point: Kiai time
  - [x] `#BARLINEOFF` & `#BARLINEON` → Timing point: Omit first bar line (@IepIweidieng)
  - [x] Visible bar lines (including `#BARLINE`) → Uninherited timing point: not omitting first bar line + incomplete bar, or the bar is complete and no conversion is needed (@IepIweidieng)
  - [x] Invisible bar lines (hidden, or unintended due to `#DELAY` or osu! timing rounding) → Uninherited timing: omit first bar line + (possibly incomplete) bar (@IepIweidieng)
  - [ ] `#BARLINESCROLL` → Inherited timing points: Slider velocity change for every bar line and every first note after bar line; split out a 1ms bar with omitted first bar line for notes on the original bar start (TODO)
- TJA Note Definition
  - Timing
    - [x] Measure with no note symbols (`,`) → Full measure (bug fix by @IepIweidieng)
    - [x] Mid-bar `#BPMCHANGE`s
    - [x] Sum of (bar length ÷ beat division ÷ BPM at each division) → relative time offset to bar start (bug fixed for fractional-beat bars with `#SCROLL`)
    - [x] ms-level timing accuracy (improved by @IepIweidieng)
      - `tja2osu.py` offers the `--beat-align` option for quantized hit objects to specified division of beat (improved by @IepIweidieng).
    - [x] osu! and TJAPlayer3 timing rounding error simulation (@IepIweidieng)
  - Note Symbols
    - [x] `0` (blank) → Empty
    - [x] `1` (regular Don) → Circle, default hitsound
    - [x] `2` (regular Katsu) → Circle, clap hitsound
    - [x] `F` (ad-lib) → empty
    - [x] `C` (bomb/mine) → empty
    - [x] `3` (big Don) → Circle, finish hitsound
    - [x] `A` (handed big Don) → (big Don) Circle, finish hitsound (@IepIweidieng)
    - [x] `4` (big Katsu) → Circle, clap finish hitsound
    - [x] `B` (handed big Katsu) → (big Katsu) Circle, clap finish hitsound (@IepIweidieng)
    - [x] `G` (Kadon) → (big Katsu) Circle, whistle + clap finish hitsound (@IepIweidieng)
    - [x] `5` (head of regular bar drumroll) → Slider, default hitsound
    - [x] `I` (head of regular/Katsu? bar drumroll) → (regular bar drumroll) Slider, clap hitsound (@IepIweidieng)
    - [x] `6` (head of big bar drumroll) → Slider, finish hitsound
    - [x] `H` (head of big/Don? bar drumroll) → (big bar drumroll) Slider, clap finish hitsound (@IepIweidieng)
    - [x] `7` (head of regular balloon roll) → Spinner, default hitsound
    - [x] `9` (head of special balloon roll) → Spinner, finish hitsound (improved by @IepIweidieng)
    - [x] `D` (head of fuze balloon roll) → (regular balloon) Spinner, clap hitsound (@IepIweidieng)
    - [x] Head of any roll-type note, after unended roll-type notes → Empty
    - [x] `8` (explicit end of rolls), after unended roll-type notes → End of last slider/spinner
    - [x] Any hit-type note, after unended roll-type notes → Forced end of last slider/spinner (improved by @IepIweidieng)
    - [x] `#END` (command)/end-of-file, after unended roll-type notes → Forced end of last slider/spinner (@IepIweidieng)
    - [x] `8`, straying → Empty (@IepIweidieng)
    - [x] Any roll-type note, non-positive time duration → Empty (@IepIweidieng)

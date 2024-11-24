# osu2tja

**English**|[简体中文](README.zh-cn.md)

An .osu ⟷ .tja converter, for Python 3.

`.osu` (osu! Beatmap) is the single-difficulty chart format for the game osu!. `.osz` (osu! Beatmap Archive) is the standard zipped form containing multiple `.osu` files and resources for a song entry in osu!.

`.tja` or TJA (unknown acronym, likely "Taiko (Tatsu)jin Another") is a Taiko chart format supported by many simulators, such as TaikoJiro, Taiko-san Daijiro, Malody, TJAPlayer3, OpenTaiko, and Project OutFox.

It contains 2 major tools: osz2tja & tja2osz.

## Requirements

- Python 3.x
- ffmpeg (optional, for osz2tja)

### ffmpeg

If ffmpeg is installed or placed under the same directory as `osz2tja.py`, osz2tja will automatically convert the audio file into `.ogg` format.

Get ffmpeg here: <https://www.ffmpeg.org/download.html>

After downloading, unzip it and copy `bin/ffmpeg.exe` into the same directory as `osz2tja.py`, and the conversion should now work.

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

- **Batch conversion** of `.osz` files to `.tja` files. (@MoshirMoshir)
- Automatically maps osu! difficulties (up to 5 per `.tja` file) to TJA **Edit** (Taiko: Inner/Ura Oni or Extra Extreme), **Oni** (Taiko: Extreme), **Hard**, **Normal**, and **Easy** difficulties. (@MoshirMoshir; improved to 5)
- Beatmaps with **more than 5 difficulties** are split into multiple `.tja` files (e.g., `title - 1`, `title - 2`). (@MoshirMoshir; improved to suffix only when necessary)
- **Automatically copy and convert** the audio file. (@SamLangTen; OGG conversion — @k2angel)

### Conversion Details

- [x] Input: osu file format v4&ndash;14 (those tested; warns and continues to process for other versions) (improved)
- [x] TJA `//` comment ignoring
- TJA Headers
  - Metadata Headers
    - [x] osu2tja watermark (moved to the first line of the TJA file)
    - [x] `TitleUnicode:`/`Title:` → `TITLE:`
    - [x] `Source:` **AND/OR** `ArtistUnicode:`/`Artist:` → `SUBTITLE:` (@k2angel)
    - [x] `AudioFilename:` → `WAVE:`, with automatic file copy (@SamLangTen), with OGG conversion (@k2angel)
    - [x] `PreviewTime:` → `DEMOSTART:`
    - [x] `Creator:` → `MAKER:` (@MoshirMoshir)
    - [ ] `Creator:` → `AUTHOR:` (for Malody) (TODO)
    - [ ] timing point: hitsound volume (max) → `SEVOL:` ÷ `SONGVOL:` (TODO)
  - Decoration Headers
    - [ ] Background event: filename → `PREIMAGE:` (TODO)
    - [ ] Background event: filename → `BGIMAGE:` (TODO)
    - [ ] Video event: filename → `BGMOVIE:` (TODO)
    - [ ] Video event: start time → `MOVIEOFFSET:` (TODO)
    - [ ] Storyboard event → TJAPlayer3-Extended OBJ commands (not planned)
  - Sync Headers
    - [x] initial BPM → `BPM:` (for display only, rounded to 2 decimal digits), for each difficulty (new)
    - [x] initial beat time position → `OFFSET:` (improved), for each difficulty (new), with -15ms music offset correction (extra +24ms for format v4 and earlier) (new)
      - The `OFFSET:` is set to the beginning time position of the last beat non-after the audio to mimic osu! behavior. It was the earliest of the first note or the timing point in delguoqing's version.
      - Ranked osu! beatmaps have roughly +15ms music offset than perfect sync due to the historical reasons. Ranked format v4 and earlier beatmaps have additional -24ms music offset (-9ms in total).
  - Difficulty Headers
    - [x] `Version:` & `Mode:` → TJA comment (for reference only) (new)
    - [ ] `Version:` → `NOTEDESIGNER<n>:` (for difficulties by guest chart creators) (TODO)
    - [ ] `Creator:` → `NOTEDESIGNER<n>:` (otherwise) (TODO)
    - [x] Difficulties sorted by `OverallDifficulty:` → `COURSE:` (@SamLangTen; automated — @MoshirMoshir; improved to include `COURSE:Edit`)
    - [x] `OverallDifficulty:` → `LEVEL:` (@SamLangTen)
      - TODO: Use the actual osu! star rating.
    - [x] Spinner: Time length → `BALLOON:` (improved using the official formula to account for `OverallDifficulty:` (might still off by 1 or 2 hits))
- TJA Commands
  - [x] Uninherited timing point: BPM → `#BPMCHANGE`
  - [x] Uninherited timing point: Beats per bar → `#MEASURE`
  - [x] Incomplete bar → `#MEASURE` + optional `#DELAY` (crash fixed — @delguoqing; improved to ms-level accuracy)
  - [x] Inherited timing point: Slider velocity change → `#SCROLL` (uncapped range)
  - [x] Timing point: Kiai time → `#GOGOSTART` & `#GOGOEND`
  - [ ] Timing point: Omit first bar line → `#BARLINEOFF` & `#BARLINEON` (TODO)
- TJA Note Definition
  - Timing
    - [x] relative time offset to bar start and end → beat division
    - [x] Mid-bar inter-note command insertion (improved, new)
    - [ ] ms-level timing accuracy (TODO)
      - Currently everything is pre-quantized to 1/96ths (1/24 beats).
  - Note Symbols
    - [x] (std mode) short slider to circles (improved using the official algorithm)
    - [x] Empty → `0` (blank)
    - [x] Circle, normal non-finish hitsound → `1` (regular Don)
    - [x] Circle, whistle/clap non-finish hitsound → `2` (regular Katsu)
    - [x] Circle, normal finish hitsound → `3` (big Don)
    - [x] Circle, whistle/clap finish hitsound → `4` (big Katsu)
    - [x] Slider, non-finish hitsound → `5` + `8` (regular bar drumroll)
    - [x] Slider, finish hitsound → `6` + `8` (big bar drumroll)
      - FIXME: Mid-slider BPM changes and slider velocity changes cause incorrect bar drumroll time duration.
    - [x] Spinner, **ANY** hitsound → `7` + `8` (regular balloon roll)
    - [ ] Spinner, finish hitsound → `9` + `8` (special balloon roll) (TODO)

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

- **Batch conversion** of `.tja` files to `.osz` files. (new)
- Automatically split each TJA difficulty and each main branch route as a separate `.osu` difficulty file.
- **Automatically copy** the audio file (new)

### Conversion Details

- [x] Output: osu file format v14 (improved)
- [x] TJA `//` comment ignoring
  - FIXME: `//` comments do not disable commands when splitting TJAs.
- TJA Headers
  - Metadata Headers
    - [x] osu2tja watermark (new)
    - [x] `TITLE:` → `Title:`, UTF-8 with(out) BOM support (new)
    - [ ] `SUBTITLE:` → `Artist:` (TODO) (Currently defaults to `unknown`)
    - [ ] `MAKER:`/`AUTHOR:` → `Creator:` (TODO) (Currently defaults to `unknown`)
    - [x] `SUBTITLE:` → `Source:` (bug fixed), UTF-8 with(out) BOM support (new)
    - [x] ? → `Tags:` (defaults to `taiko jiro tja`)
    - [ ] `GENRE:` → `Tags:` (TODO)
    - [ ] `NOTESDESIGNER<n>:` → `Tags:` (for guest chart creators) (TODO)
    - [x] `WAVE:` → `AudioFilename:`, with automatic file copy (new)
    - [x] ? → `AudioLeadIn:` (defaults to `0`) (improved)
    - [x] `DEMOSTART:` → `PreviewTime:` (bug fixed)
    - [x] ? → `CountDown:` (defaults to `0` (false))
    - [x] ? → `SampleSet:` (defaults to `Normal`)
    - [x] `StackLeniency:0.7` (no effects)
    - [x] ? → `Mode:` (defaults to `1` (Taiko))
    - [x] ? → `LetterboxInBreaks:` (defaults to `0` (false)) (improved)
    - [x] `SEVOL:` ÷ `SONGVOL:` → Timing point: hitsound volume (new)
  - Decoration Headers
    - [ ] `PREIMAGE:` → Background event: filename (TODO)
    - [ ] `BGIMAGE:` → Background event: filename (TODO)
    - [ ] `BGMOVIE:` → Video event: filename (TODO)
    - [ ] `MOVIEOFFSET:` → Video event: start time (TODO)
    - [ ] TJAPlayer3-Extended OBJ commands → Storyboard event (not planned)
  - Sync Headers
    - [x] `BPM:` → initial uninherited timing point: BPM
    - [x] `OFFSET:` → initial uninherited timing point: time, with +15ms music offset correction (new)
      - Ranked osu! beatmaps have roughly +15ms music offset than perfect sync due to the historical reasons.
  - Difficulty Headers
    - [ ] `STYLE:` → `Version:` (TODO)
    - [x] `COURSE:` → `Version:`
    - [ ] `NOTESDESIGNER<n>:` → `Version:<notesdesigner>'s <course>` when `<notesdesigner>` isn't `<maker>`/`<author>` (TODO)
    - [ ] `COURSE:` + `LEVEL:` → `HPDrainRate:` (TODO) (defaults to `7` (roughly Taiko Oni 10 full gauge) (improved))
    - [x] `CircleSize:5` (no effects)
    - [x] `ApproachRate:5` (no effects)
    - [ ] `COURSE:` + `LEVEL:` → `OverallDifficulty:` (TODO) (defaults to `8.333` (Taiko Hard & Oni GREAT/GOOD window) (improved))
    - [x] ? → `SliderMultiplier:` (defaults to `1.47` (AC15&ndash; note spacing))
    - [ ] (Mostly-used) beat division → `SliderTickRate:` (TODO) (defaults to `4` (1/16th))
    - [ ] `HEADSCROLL:` → initial inherited timing point: Slider velocity change (TODO)
- TJA Commands
  - [ ] `#START` → Uninherited timing point: Large beats per bar + omit first bar line + (optional) incomplete bar (TODO)
  - [ ] `#START P<n>` → Split into player-side TJA (TODO)
    - FIXME: When a multiple&ndash;player-side chart set has been defined for any difficulty, wrong difficulties will be notated for split difficulties.
  - [x] `#END` → Uninherited timing point: Large beats per bar + omit first bar line (new)
  - [x] `#BRANCHSTART` → Begin branch-split section
    - TODO: detect and avoid impossible branch routes
  - [x] `#N`/`#E`/`#M` → Split into branch TJA
    - FIXME: Omitting some branches causes missing bars.
  - [ ] `#BRANCHEND` → Begin branch-common section
    - FIXME: `#BRANCHEND` is recognized but ignored.
  - [x] `#BPMCHANGE`, positive → Uninherited timing point: BPM
  - [ ] `#BPMCHANGE`, negative, with positive (bar length ÷ BPM) → Uninherited timing point: absolute-valued BPM (TODO)
  - [x] `#MEASURE`, positive integer beats → Uninherited timing point: Beats per bar (improved), float values (new)
  - [x] `#MEASURE`, positive fraction beats → Uninherited timing point: Beats per bar + incomplete bar (improved), float values (new)
  - [ ] Negative (bar length ÷ BPM) → Notechart events are not in completely increasing time order, re-sorted by time (TODO)
  - [x] `#DELAY` → move time of definition cursor
    - FIXME: The bar line after `#DELAY` will be wrongly displayed until the next uninherited timing point generated.
    - FIXME: The generated events might not be in the correct increasing time order if large negative `#DELAY`s are used.
  - [x] `#SCROLL`, with positive (scroll × BPM) → Inherited timing point: Slider velocity change
    - FIXME: Use BPM changes to work around the slider velocity change being capped between 0.01x to 10x in osu!.
  - [ ] Non-positive/complex-valued (scroll × BPM) → Inherited timing point: Absolute-valued slider velocity change (TODO)
  - [ ] `#SUDDEN`, with positive stop duration → Inherited timing point: Scaled slider velocity change (TODO)
  - [x] `#GOGOSTART` & `#GOGOEND` → Timing point: Kiai time
  - [x] `#BARLINEOFF` & `#BARLINEON` → Timing point: Omit first bar line (new)
  - [ ] `#BARLINE` → Split bars into (possibly) incomplete bars (TODO)
  - [ ] `#BARLINESCROLL` → Inherited timing points: Slider velocity change for every bar line and every first note after bar line; split out a 1ms bar with omitted first bar line for notes on the original bar start (TODO)
- TJA Note Definition
  - Timing
    - [x] Measure with no note symbols (`,`) → Full measure (new bug fix)
    - [x] Mid-bar `#BPMCHANGE`s
    - [x] Sum of (bar length ÷ beat division ÷ BPM at each division) → relative time offset to bar start (bug fixed for fractional-beat bars with `#SCROLL`)
    - [ ] ms-level timing accuracy (TODO)
      - Currently everything is pre-quantized to 1/96ths (1/24 beats).
  - Note Symbols
    - [x] `0` (blank) → Empty
    - [x] `1` (regular Don) → Circle, default hitsound
    - [x] `2` (regular Katsu) → Circle, clap hitsound
    - [ ] `F` (ad-lib) → = regular Don/Katsu? (TODO)
    - [ ] `C` (bomb/mine) → = regular Don/Katsu? empty? (TODO)
    - [x] `3` (big Don) → Circle, finish hitsound
    - [ ] `A` (handed big Don) → Circle, finish hitsound (TODO)
    - [x] `4` (big Katsu) → Circle, clap finish hitsound
    - [ ] `B` (handed big Katsu) → Circle, clap finish hitsound (TODO)
    - [ ] `G` (Kadon) → = big Don/Katsu? (TODO)
    - [x] `5` (head of regular bar drumroll) → Slider, default hitsound
    - [ ] `I` (head of regular/Katsu? bar drumroll) → = head of regular bar drumroll? (TODO)
    - [x] `6` (head of big bar drumroll) → Slider, finish hitsound
    - [ ] `H` (head of big/Don? bar drumroll) → = head of big bar drumroll? (TODO)
      - FIXME: Mid&ndash;bar-drumroll `#BPMCHANGE`s and `#SCROLL`s cause wrong slider length calculation and cause wrong time duration.
    - [x] `7` (head of regular balloon roll) → Spinner, default hitsound
    - [x] `9` (head of special balloon roll) → Spinner, default hitsound
      - TODO: use finish hitsound to mark difference
    - [ ] `D` (head of fuze balloon roll) → = regular balloon roll? (TODO)
    - [ ] Head of any roll-type note, after unended roll-type notes → Empty (TODO)
    - [x] `8` (explicit end of rolls), after unended roll-type notes → End of last slider/spinner
    - [ ] Any hit-type note, after unended roll-type notes → Forced end of last slider/spinner (TODO)
    - [ ] `#END` (command), after unended roll-type notes → Forced end of last slider/spinner (TODO)
    - [ ] `8`, straying → Empty (TODO)
    - [ ] Any roll-type note, non-positive time duration → Empty (TODO)

# sys.path hack
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from common.tja import TjaCmd, convert_str, get_course_by_number, parse_tja_command, parse_tja_header
from common.utils import print_with_pended
from common.osu import EHideFirst, OsuTimingPoint, get_idx_tm_at, get_last_red_tm, get_last_tm, get_red_tm_at, get_tm_at

import argparse
import codecs
from dataclasses import dataclass
import math
import re
import sys
import traceback
from typing import Dict, List, Optional, TextIO, Tuple, TypeVar, Union, cast

chart_resources: Dict[str, str] # {'filename': 'type', ...}

TimingPoints: List[OsuTimingPoint]
bar_data: List[Union[str, TjaCmd]]
lasting_note: Optional["OsuHitObject"]

def init_globals() -> None:
    global ENCODING, TITLE, SUBTITLE, ARTIST, GENRE, BPM, WAVE, OFFSET, DEMOSTART, HEADSCROLL
    global MAKER, CREATOR, SONGVOL, SEVOL, COURSE, LEVEL
    global PREIMAGE, BGIMAGE, BGMOVIE, MOVIEOFFSET
    # jiro data
    ENCODING = None
    TITLE = "NO TITLE"
    SUBTITLE = ""
    ARTIST = ""
    GENRE = []
    BPM = 120.0
    WAVE = None
    OFFSET = 0.0
    DEMOSTART = 0.0
    HEADSCROLL = 1.0
    MAKER = None
    CREATOR = None
    SONGVOL = 100.0
    SEVOL = 100.0
    COURSE = "Oni"
    LEVEL = 0
    PREIMAGE = None
    BGIMAGE = None
    BGMOVIE = None
    MOVIEOFFSET = 0.0

    global AudioFilename, Title, Source, Tags, Artist, Creator, Version
    global AudioLeadIn, CountDown, SampleSet, StackLeniency, Mode, LetterboxInBreaks, PreviewTime
    global TimingPoints, HitObjects
    global HPDrainRate, CircleSize, OverallDifficulty, ApproachRate, SliderMultiplier, SliderTickRate, CircleX, CircleY
    # osu data
    AudioFilename = ""
    Title = ""
    Source = ""
    Tags = ["tja"]
    Artist = "Unknown Artist"
    Creator = "unknown"
    Version = "Oni"
    AudioLeadIn = 0
    CountDown = 0
    SampleSet = "Normal"
    StackLeniency = 0.7
    Mode = 1
    LetterboxInBreaks = 0
    PreviewTime = -1
    TimingPoints = []
    HitObjects = []
    HPDrainRate = 7
    CircleSize = 5
    OverallDifficulty = 8
    ApproachRate = 5
    SliderMultiplier = 1.4
    SliderTickRate = 4
    CircleX = 256
    CircleY = 192

    global chart_resources
    chart_resources = {}

    global has_started, curr_time, bar_data, lasting_note, unknowns
    has_started = False
    curr_time = 0.0
    bar_data = []
    lasting_note = None
    unknowns = set()

def init_debug_globals() -> None:
    global debug_mode, last_debug, print_each_note
    debug_mode = False
    last_debug = None
    print_each_note = False #(int(curr_time) == 112814)

init_debug_globals()

# const_data
BRANCHSTART = "BRANCHSTART"
END = "END"
START = "START"
BPMCHANGE = "BPMCHANGE"
MEASURE = "MEASURE"
GOGOSTART = "GOGOSTART"
GOGOEND = "GOGOEND"
BARLINEOFF = "BARLINEOFF"
BARLINEON = "BARLINEON"
DELAY = "DELAY"
SCROLL = "SCROLL"


def check_unsupported(filename):
    return
    assert isinstance(filename, str)
    assert filename.endswith(".tja"), "filename should ends with .tja"
    try: fobj = open(filename, "rb")
    except IOError: assert False, "can't open tja file."
    if fobj.peek(len(codecs.BOM_UTF8)).startswith(codecs.BOM_UTF8):
        fobj.seek(len(codecs.BOM_UTF8)) # ignore UTF-8 BOM
    END_cnt = 0
    for line in fobj:
        cmd = parse_tja_command(line)
        assert cmd.name != BRANCHSTART.decode(), "don't support branch"
        END_cnt += (cmd.name != END.decode())
        assert END_cnt < 1 or cmd.name != START.decode(), "don't support multiple fumen."

Str = TypeVar('Str', str, bytes)

def rm_jiro_comment(str_: Str) -> Str:
    return str_.partition(cast(Str, b'//' if type(str_) == bytes else '//'))[0]


def parse_tja_complex(str_) -> complex:
    str_ = str_.lower().rstrip()
    if str_.endswith('i'):
        str_ = str_.removesuffix('i') + 'j'
    return complex(str_)


def parse_tja_genre(genres: str) -> List[str]:
    res: List[str] = []
    for genre in genres.split(","):
        genre = genre.lower()
        if genre in {"ポップス", "j-pop", "pop", "rock", "流行音乐", "华语流行音乐", "流行音樂", "華語流行音樂"}:
            genre = "pop"
        elif genre in {"キッズ", "どうよう", "童謡・民謡", "children", "children/folk", "children-folk"}:
            genre = "children-folk"
        elif genre in {"アニメ", "anime", "anime/tv", "卡通动画音乐", "卡通動畫音樂", "애니메이션"}:
            genre = "anime"
        elif genre.startswith("ボーカロイド") or genre.startswith("vocaloid"):
            genre = "vocaloid"
        elif genre in {"ゲームミュージック", "game music", "游戏音乐", "遊戲音樂", "게임"}:
            genre = "game"
        elif genre in {"バラエティ", "バラエティー", "ゲーム＆バラエティ", "variety", "综合音乐", "綜合音樂", "버라이어티"}:
            genre = "variety"
        elif genre in {"クラシック", "クラッシック", "classical", "classic", "古典音乐", "古典音樂", "클래식"}:
            genre = "classical"
        elif genre in {"ナムコオリジナル", "namco original", "namco原创音乐", "namco原創音樂", "남코 오리지널"}:
            genre = "namco"
        if genre:
            res.append(genre)
    return res

def get_meta_data(filename):
    global ENCODING, TITLE, SUBTITLE, ARTIST, GENRE, WAVE, OFFSET, DEMOSTART, HEADSCROLL, MAKER, CREATOR, SONGVOL, SEVOL, COURSE, LEVEL, BPM
    global PREIMAGE, BGIMAGE, BGMOVIE, MOVIEOFFSET
    assert isinstance(filename, str)
    assert filename.endswith(".tja"), "filename should ends with .tja"
    try: fobj = open(filename, "rb")
    except IOError: assert False, "can't open tja file."
    if fobj.peek(len(codecs.BOM_UTF8)).startswith(codecs.BOM_UTF8):
        ENCODING = "utf-8-sig"
        fobj.seek(len(codecs.BOM_UTF8)) # ignore UTF-8 BOM
    for lineno, line in enumerate(fobj):
        try:
            line = line.rstrip(b"\r\n")
            v = parse_tja_header(line)
            if v is None: # try metadata in comments
                creator = line.partition(b"//created by ")[2].strip()
                if creator: CREATOR = convert_str(creator, ENCODING)
                continue
            varg_raw = v.arg
            v.arg = rm_jiro_comment(v.arg).rstrip()
            if v.name == b"TITLE": TITLE = convert_str(varg_raw, ENCODING)
            elif v.name == b"SUBTITLE": SUBTITLE = convert_str(varg_raw, ENCODING)
            elif v.name == b"ARTIST": ARTIST = convert_str(varg_raw, ENCODING)
            elif v.name == b"GENRE": GENRE = parse_tja_genre(convert_str(varg_raw, ENCODING))
            elif v.name == b"BPM": BPM = float(v.arg)
            elif v.name == b"WAVE": WAVE = convert_str(v.arg, ENCODING)
            elif v.name == b"OFFSET": OFFSET = float(v.arg)
            elif v.name == b"DEMOSTART": DEMOSTART = float(v.arg)
            elif v.name == b"HEADSCROLL": HEADSCROLL = parse_tja_complex(v.arg)
            elif v.name in (b"MAKER", b"AUTHOR"): MAKER = convert_str(varg_raw, ENCODING)
            elif v.name == b"SONGVOL": SONGVOL = float(v.arg)
            elif v.name == b"SEVOL": SEVOL = float(v.arg)
            elif v.name == b"COURSE": COURSE = get_course_by_number(convert_str(v.arg, ENCODING))
            elif v.name == b"LEVEL": LEVEL = float(v.arg)
            elif v.name in (b"PREIMAGE", b"COVER"): PREIMAGE = convert_str(v.arg, ENCODING)
            elif v.name == b"BGIMAGE": BGIMAGE = convert_str(v.arg, ENCODING)
            elif v.name == b"BGMOVIE": BGMOVIE = convert_str(v.arg, ENCODING)
            elif v.name == b"MOVIEOFFSET": MOVIEOFFSET = float(v.arg)
            elif (v.name+b':') not in unknowns:
                line_printable = convert_str(line.removesuffix(b'\n'), ENCODING)
                print_with_pended(f"Warning: Unknown or unsupported header {line_printable}", file=sys.stderr)
                unknowns.add(v.name+b':')
        except Exception:
            print_with_pended(traceback.format_exc(), file=sys.stderr)
            print_with_pended(f"Error parsing header in `{filename}` at line {lineno}: `{line}`. Continued.", file=sys.stderr)

MS_OSU_MUSIC_OFFSET = 15
"""Ranked osu! beatmaps have late music / early chart sync. osu!'s new audio engine applies a global 15ms chart delay.
<https://github.com/ppy/osu/issues/24625>
"""

def add_default_timing_point():
    global curr_time

    tm = OsuTimingPoint(
        offset = -(OFFSET * 1000.0 + MS_OSU_MUSIC_OFFSET),
        scroll = 1.0,
        beats = 4.0,
        ggt = False,
        hidefirst = EHideFirst.SHOWN,
        bpm = BPM,
    )
    tm.redtm = tm

    TimingPoints.append(tm)

    curr_time = tm.offset

CIRCLE = 1
SLIDER = 2
SPINNER = 12
SLIDER_END = -SLIDER
SPINNER_END = -SPINNER
FORCED_END = -CIRCLE

EMPTY = 0
CLAP = 8
FINISH = 4
WHISTLE = 2 

def get_osu_type(snd):
    assert snd != '0'
    # non-rolls: end unended roll first if exists, then emit the note
    if snd in ('1', '2', '3', '4', 'A', 'B', 'G'): return CIRCLE if lasting_note is None else FORCED_END
    # converted to empty
    if snd in ('F', 'C'): return None if lasting_note is None else FORCED_END
    # roll heads: ignore repeated roll heads (especially for special balloon bonus border)
    if snd in ('5', '6', 'I', 'H'): return SLIDER if lasting_note is None else None
    if snd in ('7', '9', 'D'): return SPINNER if lasting_note is None else None
    # roll end and unrecognized note symbols
    if snd == '8':
        if lasting_note is not None and lasting_note.type == SLIDER:
            return SLIDER_END
        elif lasting_note is not None and lasting_note.type == SPINNER:
            return SPINNER_END
        print_with_pended(f"Warning: Straying TJA note symbol 8 (roll-type end)", file=sys.stderr)
        return None
    if snd not in unknowns:
        print_with_pended(f"Warning: Unknown TJA note symbol {repr(snd)}", file=sys.stderr)
        unknowns.add(snd)
    if lasting_note is not None:
        print_with_pended(f"Note: With unended roll-type note {lasting_note}", file=sys.stderr)
    return None

def get_osu_sound(snd):
    assert snd != '0'
    if snd == '1': return EMPTY
    elif snd == '2': return CLAP
    elif snd in ('3', 'A'): return FINISH
    elif snd in ('4', 'B'): return FINISH+CLAP
    elif snd == 'G': return FINISH+WHISTLE+CLAP
    elif snd == '5': return EMPTY
    elif snd == 'I': return CLAP
    elif snd == '6': return FINISH
    elif snd == 'H': return FINISH+CLAP
    elif snd == '7': return EMPTY
    elif snd == '8': return EMPTY
    elif snd == '9': return FINISH
    elif snd == 'D': return CLAP
    else: return EMPTY # empty or unknown and warned


def get_all(filename):
    global has_started, curr_time, lasting_note
    try: fobj = open(filename, "rb")
    except IOError: assert False, "can't open tja file."
    if fobj.peek(len(codecs.BOM_UTF8)).startswith(codecs.BOM_UTF8):
        fobj.seek(len(codecs.BOM_UTF8)) # ignore UTF-8 BOM

    has_started = False
    add_default_timing_point()
    for lineno, line in enumerate(fobj):
        try:
            line = line.decode("latin-1").strip()
            line = rm_jiro_comment(line).rstrip()
            hdr = parse_tja_header(line)
            if hdr is not None:
                # no need to handle
                continue
            cmd = parse_tja_command(line)
            if cmd is not None:
                if not has_started and cmd.name == START:
                    has_started = True
                    if HEADSCROLL != 1.0:
                        real_do_cmd((SCROLL, HEADSCROLL))
                    continue
                if cmd.name == END:
                    break
                handle_cmd(line, cmd)
                continue
            handle_note(line)
        except Exception:
            print_with_pended(traceback.format_exc(), file=sys.stderr)
            print_with_pended(f"Error parsing note chart in `{filename}` at line {lineno}: `{line}`. Continued.", file=sys.stderr)
    else:
        print_with_pended(f"Warning: Missing #END at end of chart.", file=sys.stderr)
    if len(bar_data) != 0:
        print_with_pended(f"Warning: Missing comma (,) at end of chart.", file=sys.stderr)
        handle_note(",")
    if lasting_note is not None:
        print_with_pended(f"Warning: Unended roll-type note {lasting_note} ended by end of chart at {curr_time}.", file=sys.stderr)
        add_a_note('8', curr_time)

    # prevent bar lines at and after #END (probably missing and implicit)
    tm = get_last_red_tm(TimingPoints)
    real_do_cmd((MEASURE, math.ceil(min(max(tm.beats, tm.bpm, 1), (1 << 31) - 1)))) # insert a >= 1 minute measure
    real_do_cmd((BARLINEOFF,)) # hide its bar line

# get fixed offset base by the nearest base timing points
# step 1: find the nearest past red timing point r
# step 2: calculate the fixed beat count from t to point r
# step 3: get fixed offset from fixed beat count and bpm
# step 4: find the nearest any-color timing points, past point p and future point f
# step 5: adjust fixed offset so that it is at or after point p and before point f

BEAT_RES = 0 # aligning disabled

def get_real_offset(int_offset):
    if debug_mode:
        print_with_pended("INTOffset", int_offset, file=sys.stderr)
    if BEAT_RES <= 0:
        aligned_offset = int_offset
    else:
        tm = get_red_tm_at(TimingPoints, int_offset)
        int_tm_offset = int(tm.offset)
        tpb = 60000 / tm.bpm
        int_delta = int_offset - tm.offset # more accurate
        sign = (int_delta > 0 and 1 or -1)

        t_unit_cnt = round(abs(int_delta) * tm.bpm * BEAT_RES / 60000)

        beat_cnt = t_unit_cnt / BEAT_RES
        aligned_offset = int_tm_offset + beat_cnt * 60000 * sign / tm.bpm

        if debug_mode:
            print_with_pended(tm, file=sys.stderr)
            print(t_unit_cnt, file=sys.stderr)
            print("DELTA = ", int_delta, file=sys.stderr)
            print("GET BEAT CNT", int_delta/tpb, t_unit_cnt/BEAT_RES, file=sys.stderr)
            print(int_offset, "-->", int_tm_offset + beat_cnt * 60000 / tm.bpm, file=sys.stderr)
            print(int(int_tm_offset + beat_cnt * 60000 / tm.bpm), file=sys.stderr)

            print("CMP", int(int_tm_offset+beat_cnt * 60000 * sign / tm.bpm), int(2663+60000/tm.bpm*beat_cnt), file=sys.stderr)

    ret = aligned_offset
    idx_tm_p = get_idx_tm_at(TimingPoints, int_offset)
    tm_p_offset = TimingPoints[idx_tm_p].offset
    int_tm_p_offset = int(tm_p_offset)
    if ret < tm_p_offset:
        ret = int_tm_p_offset
    if idx_tm_p + 1 < len(TimingPoints):
        tm_f_offset = TimingPoints[idx_tm_p + 1].offset
        int_tm_f_offset = int(tm_f_offset)
        if ret > int_tm_f_offset - 1:
            ret = int_tm_f_offset - 1
        if int_tm_f_offset <= int_tm_p_offset:
            print_with_pended(f"Warning: time {aligned_offset} is between timing points at {tm_p_offset} and {tm_f_offset}, with identical integer offset")

    return ret
   
def handle_cmd(line: str, cmd: TjaCmd) -> None:
    if cmd.name == BPMCHANGE:
        cmd = TjaCmd(cmd.name, float(cmd.args[0]))
    elif cmd.name == MEASURE:
        arg1, arg2 = cmd.args[0].split('/')
        cmd = TjaCmd(cmd.name, 4.0*float(arg1.strip()) / float(arg2.strip()))
    elif cmd.name == SCROLL:
        cmd = TjaCmd(cmd.name, parse_tja_complex(cmd.args[0]))
    elif cmd.name == DELAY:
        cmd = TjaCmd(cmd.name, float(cmd.args[0]))
    else: # default handling
        cmd = TjaCmd(cmd.name, cmd.args[0])

    if bar_data == [] or cmd.name == MEASURE:
        real_do_cmd(cmd)
    else:
        bar_data.append(cmd)

def real_do_cmd(cmd: Union[Tuple, TjaCmd]):
    global curr_time

    if not isinstance(cmd, TjaCmd):
        cmd = TjaCmd(*cmd)
    assert isinstance(cmd, TjaCmd)

    if debug_mode:
        print_with_pended("handle cmd", cmd, file=sys.stderr)
    
    # handle delay, no timing point change
    if cmd.name == DELAY:
        curr_time += cmd.args[0] * 1000
        return
    
    # handel timing point change command    
    if cmd.name == BPMCHANGE:
        get_or_create_curr_red_tm().bpm = cmd.args[0]
    elif cmd.name == MEASURE: # processed before notes
        if len(bar_data) != 0:
            print_with_pended("Warning: Changing measure within a bar is handled as changing at the start of bar.", file=sys.stderr)
            get_last_red_tm(TimingPoints).beats = cmd.args[0]
        else:
            get_or_create_curr_red_tm().beats = cmd.args[0]
    elif cmd.name == SCROLL:
        get_or_create_curr_tm().scroll = abs(cmd.args[0])
    elif cmd.name == GOGOSTART:
        get_or_create_curr_tm().ggt = True
    elif cmd.name == GOGOEND:
        get_or_create_curr_tm().ggt = False
    elif cmd.name == BARLINEOFF:
        get_or_create_curr_tm().hidefirst = EHideFirst.HIDDEN
    elif cmd.name == BARLINEON:
        get_or_create_curr_tm().hidefirst = EHideFirst.SHOWN
    elif ('#'+cmd.name) not in unknowns:
        print_with_pended(f"Warning: Unknown or unsupported command {cmd}.", file=sys.stderr)
        unknowns.add('#'+cmd.name)

@dataclass
class OsuHitObject:
    type: int
    sound: int
    offset: float

def add_a_note(snd, offset):
    global lasting_note
    (osu_type, osu_sound) = (get_osu_type(snd), get_osu_sound(snd))
    if osu_type == FORCED_END: # end unended roll, then emit the note
        add_a_note('8', offset)
        add_a_note(snd, offset)
        return
    if osu_type is None:
        return
    obj = OsuHitObject(osu_type, osu_sound, offset)
    HitObjects.append(obj)
    if osu_type in (SLIDER, SPINNER):
        lasting_note = obj
    if osu_type in (SLIDER_END, SPINNER_END):
        lasting_note = None
    if debug_mode:
        print_with_pended(HitObjects[-1], file=sys.stderr)

def create_new_tm(has_red: bool = False):
    global curr_time

    last_tm = get_last_tm(TimingPoints)
    last_red_tm = get_last_red_tm(TimingPoints)
    
    tm = OsuTimingPoint(
        offset = curr_time,
        redtm = last_red_tm, # can upgrade to red + green later if not having red
        scroll = last_tm and last_tm.scroll or 1.0,
        beats = last_tm.beats,
        ggt = last_tm.ggt,
        hidefirst = last_tm.hidefirst,
        bpm = last_red_tm.bpm,
    )
    if has_red:
        tm.redtm = tm
    if debug_mode:
        print_with_pended("CREATE NEW TM", tm, file=sys.stderr)
    
    TimingPoints.append(tm)
    if has_red:
        curr_time = tm.offset

    return tm

def get_or_create_curr_tm(need_red: bool = False):
    global curr_time
    tm = get_last_tm(TimingPoints)
    if int(curr_time) != int(tm.offset):
        tm = create_new_tm(need_red)
    elif need_red and not tm.is_redline(): # needs to upgrade to red + green
        tm.redtm = tm
    return tm

def get_or_create_curr_red_tm():
    return get_or_create_curr_tm(True)

def get_t_unit(tm: OsuTimingPoint, tot_note):
    if debug_mode:
        print_with_pended(tm.bpm, tot_note, file=sys.stderr)
    return tm.beats * 60000.0 / (tm.bpm * tot_note)

def handle_a_bar():
    global bar_data, curr_time
    
    #debug
    global last_debug
    if last_debug is None:
        last_debug = TimingPoints[0].offset
    #debug

    tot_note = 0
    for data in bar_data:
        if isinstance(data, str):
            tot_note += 1

    if debug_mode:
        print_with_pended("TOT_NOTE", tot_note, file=sys.stderr)
        pure_data = [x for x in bar_data if isinstance(x, str) and x[0].isdigit()]
        p1= "%6d %2.1f %2d %s" % (int(curr_time), \
                get_last_red_tm(TimingPoints).beats, len(pure_data), \
                "".join(pure_data))

        p2= "%s %s" % (repr(get_last_red_tm(TimingPoints).bpm), \
                repr(get_t_unit(get_last_red_tm(TimingPoints), max(1, tot_note)) * max(1, tot_note)))
        print_with_pended(p1, file=sys.stderr)

    #debug
    last_debug = curr_time
    bak_curr_time = curr_time
    note_cnt = -1
    #debug
    
    if not tot_note: # empty or command-only measure
        curr_time += get_t_unit(get_last_red_tm(TimingPoints), 1)
    else:
        for data in bar_data:
            if isinstance(data, str): #note
                note_cnt += 1
                if data != "0":
                    add_a_note(data, curr_time)
                    if print_each_note:
                        print_with_pended(note_cnt, data, curr_time,
                            bak_curr_time + note_cnt * get_t_unit(get_last_red_tm(TimingPoints), tot_note),
                            get_t_unit(get_last_red_tm(TimingPoints), tot_note),
                            file=sys.stderr)
                curr_time += get_t_unit(get_last_red_tm(TimingPoints), tot_note)           
            else: #cmd
                real_do_cmd(data)
    bar_data = [] 
    
    if print_each_note:
        print_with_pended("after bar, curr_time= %f", curr_time, file=sys.stderr)
    # handle bar line visibility
    tmr = get_last_red_tm(TimingPoints)
    tm = get_last_tm(TimingPoints)
    if tm.hidefirst.is_hidden(): # still hidden
        real_do_cmd((MEASURE, tmr.beats)) # insert bar line
        real_do_cmd((BARLINEOFF,)) # hide bar line
    elif tmr.hidefirst.is_hidden(): # no longer hidden
        real_do_cmd((MEASURE, tmr.beats)) # insert bar line
        real_do_cmd((BARLINEON,)) # unhide bar line
    # convert x.x measure to incomplete measure
    if abs(round(tmr.beats) - tmr.beats) > 0.001:
        bak = tmr.beats
        tmr.beats = math.ceil(round(bak, 3)) # a big enough measure for osu
        real_do_cmd((MEASURE, bak)) # remeasure, for tja

def handle_note(line):
    global bar_data
    for ch in line:
        if ch.isalnum() and ch.isascii():
            bar_data.append(ch)
        elif ch == ",":
            handle_a_bar()
        elif not ch.isspace():
            print_with_pended(f"Warning: Invalid TJA note symbol {repr(ch)} ignored", file=sys.stderr)

def write_fmt_ver_str(fout: TextIO) -> None:
    print("osu file format v14", file=fout)
    print("", file=fout)

def write_General(fout: TextIO) -> None:
    global AudioFilename, PreviewTime
    if WAVE:
        AudioFilename = WAVE
        chart_resources[WAVE] = 'song audio'
    else:
        AudioFilename = ""
    PreviewTime = DEMOSTART * 1000 - MS_OSU_MUSIC_OFFSET

    print("[General]", file=fout)
    print("AudioFilename: %s" % (AudioFilename,), file=fout)
    print("AudioLeadIn: %d" % (round(AudioLeadIn)), file=fout)
    print("PreviewTime: %d" % (round(PreviewTime)), file=fout)
    print("CountDown: %d" % (CountDown,), file=fout)
    print("SampleSet: %s" % (SampleSet,), file=fout)
    print("StackLeniency: %s" % (repr(StackLeniency),), file=fout)
    print("Mode: %d" % (Mode,), file=fout)
    print("LetterboxInBreaks: %d" % (LetterboxInBreaks,), file=fout)
    print("", file=fout)

# no use, but required by osu
def write_Editor(fout: TextIO) -> None:
    print("[Editor]", file=fout)
    print("DistanceSpacing: 0.8", file=fout)
    print("BeatDivisor: 4", file=fout)
    print("GridSize: 4", file=fout)
    print("", file=fout)

pat_work_info = re.compile(r'^\w*?(?:ドラマ|[\w ]*?Drama|剧|劇|アニメ|[\w ]*? Anime|动画|動畫|映画|[\w ]*? Movie|电影|電影|CMソング)')
pat_song_type = re.compile(r'(?:(?:オープニング・?|OP|エンディング・?|ED)?(?:テーマ|主題)[歌曲]?|(?:Opening |Ending )?Theme( Song)?|(?:主[题題]|片[头頭尾])[歌曲]?|デモソング|Demo Song|メドレー|Medley|組曲) *$')

def parse_tja_subtitle(title: str, subtitle: str, genres: List[str]) -> Tuple[str, str, str]: # Title, Artist, Source
    artist = ""
    # original genre as Source, where the work title extracted from subtitle is assumed to be fictional
    source = ""
    if "namco" in genres:
        source = "Taiko no Tatsujin"
    elif "opentaiko" in genres:
        source = "OpenTaiko"

    # subtitle is second line of title
    if subtitle.startswith("++"): # or not subtitle.startswith("--"): # some charters omits --
        subtitle = subtitle.removeprefix('++')
        return title + " " + subtitle, artist or Artist, source or Source

    # try extracting info
    subtitle = subtitle.removeprefix("--")

    # work info as secondary title
    match = re.match(r'^[～~].*?(?:[「『]| " ?)(.*?)(?:[」』]| ?" ).*?[～~]', subtitle)
    if match is not None:
        if not source:
            source = match.group(1)
        subtitle = subtitle.removeprefix(match.group(0)).lstrip().removeprefix('/').lstrip()

    # secondary title
    match = (re.match(r'^[～~—].+?[～~—]', subtitle) # secondary title or version
        or re.match(r'''^[^ 「」『』："/]+?[「『"'] ?.+? ?[」』"']''', subtitle)) # movement (classical music)
    if match is not None:
        title += " " + match.group(0)
        subtitle = subtitle.removeprefix(match.group(0)).lstrip().removeprefix('/').lstrip()

    # cover/remix info
    match = re.match(rf'^[^ 「」『』："/]*? cover ver.', subtitle)
    if match is not None:
        title += f" ({match.group(1)} Cover)"
        subtitle = subtitle.removeprefix(match.group(0)).lstrip().removeprefix('/').lstrip()

    # original song info ((original) artists, original title, original artists)
    match = (re.match(rf'^原曲：([^ 「」『』："/]*?)()()', subtitle) # or `From " <original artists> "` (ambiguous)
         or re.match(rf'^([^ 「」『』："/]*?) (?:原曲|From)(?:[「『]| " ?)(.*?) ?/ ?(.*?)(?:[」』]| ?")', subtitle))
    if match is not None:
        artist = match.group(1)
        subtitle = subtitle.removeprefix(match.group(0)).lstrip().removeprefix('/').lstrip()

    # Touhou arrangements
    match = re.match(r'^(?:東方Projectアレンジ|Touhou Project Arrange|東方Project Arrange)', subtitle)
    if match is not None:
        if not source:
            source = "Touhou Project"
        subtitle = subtitle.removeprefix(match.group(0)).lstrip().removeprefix('/').lstrip()

    # "From" source: (artist, source)
    match = (re.match(r'^(?:([^ 「」『』："/]*?)(?: | ?/ ?))?[「『](.*?)[」』][^「」『』："/]*?', subtitle) # ambiguous if no space after artist
         or re.match(r'^(?:([^ 「」『』："/]*?)(?: | ?/ ?))?(?:From|來自)(?:[^「」『』："/]*?)?(?:[「『]| " ?)(.*?)(?:[」』]| ?")', subtitle)
         or re.match(r'^([^「」『』："/]*?)(?:[「『]| " ?)(.*?)(?:[」』]| ?" )[^「」『』："/]*?', subtitle)) # artist or work type before "From"
    if match is not None:
        artist, source = match.group(1) or artist, source or match.group(2)
        subtitle = subtitle.removeprefix(match.group(0)).lstrip().removeprefix('/').lstrip()

    # quoted or spaced work title + song type
    match = re.match(r'^[「『 ](.*?)[」』 ]\w+', subtitle)
    if match is not None:
        if not source:
            source = match.group(1)
        subtitle = subtitle.removeprefix(match.group(0)).lstrip().removeprefix('/').lstrip()

    # ambiguous with single slash, assumed `artist / source`
    # or `<album or series> / <artists or band>` or `<artists> / <project or publisher>` or `<singers> / <other artists or project>`
    match = (re.match(r'^(.*?) / (.*)', subtitle)
        or re.match(r'^(.*?) ?/ ?(.*)', subtitle)) # some charters omit spaces
    if match is not None:
        artist, source = match.group(1), source or match.group(2)
        subtitle = ""

    # ambiguous, assumed artist
    # or `<work name> <song type>`
    if not artist:
        artist = subtitle

    # keyword detection for source
    if pat_work_info.match(artist):
        artist, source = "", artist
    elif pat_song_type.match(artist):
        artist, source = "", artist
    match = pat_song_type.search(source)
    if match is not None:
        source = source.removesuffix(match.group(0)).rstrip()

    return title, artist or Artist, source or Source

def write_Metadata(fout: TextIO) -> None:
    global Title, Artist, Source, Creator, AudioFilename, PreviewTime, Version
    Title, Artist, Source = parse_tja_subtitle(TITLE, SUBTITLE, GENRE)
    if not Artist:
        Artist = ARTIST # fallback, as ARTIST: for Malody is romanized
    Creator = MAKER or CREATOR or Creator
    Version = COURSE
    Tags.extend((genre for genre in GENRE if genre not in ("namco", "opentaiko")))
    for i, tag in enumerate(Tags):
        Tags[i] = tag.strip().replace(' ', '_')
    print("[Metadata]", file=fout)
    print("Title:%s" % (Title,), file=fout)
    print("Artist:%s" % (Artist,), file=fout)
    print("Creator:%s" % (Creator,), file=fout)
    print("Version:%s" % (Version,), file=fout)
    print("Source:%s" % (Source,), file=fout)
    print("Tags:%s" % (" ".join(Tags),), file=fout)
    print("", file=fout)

def write_Difficulty(fout: TextIO) -> None:
    global HPDrainRate, OverallDifficulty, SliderTickRate
    course = COURSE.lower()
    # lower-limit of ranking guideline if note count is not high
    HPDrainRate = (8 if course.startswith('easy')
        else 7 if course.startswith('normal')
        else 6 if course.startswith('hard')
        else (5 if LEVEL < 8 else 6)) # for higher BAD penalty
    OverallDifficulty = (2.3 if course.startswith('easy') or course.startswith('normal') # 42.5ms for GREAT/GOOD
        else 5 if course.startswith('hard') # upper-limit of ranking guideline
        else 8) # 25.5ms for GREAT/GOOD

    print("[Difficulty]", file=fout)
    print("HPDrainRate:%s" % (repr(HPDrainRate),), file=fout)
    print("CircleSize:%s" % (repr(CircleSize),), file=fout)
    print("OverallDifficulty:%s" % (repr(OverallDifficulty),), file=fout)
    print("ApproachRate:%s" % (repr(ApproachRate),), file=fout)
    print("SliderMultiplier:%s" % (repr(SliderMultiplier),), file=fout)
    print("SliderTickRate:%s" % (repr(SliderTickRate),), file=fout)
    print("", file=fout)

def write_Events(fout: TextIO) -> None:
    print("[Events]", file=fout)
    print("//Background and Video events", file=fout)

    # FIXME: What if the filename contains double quotes (")?
    bg = BGIMAGE or PREIMAGE
    if bg:
        print(f'0,0,"{bg}",0,0', file=fout)
        chart_resources[bg] = 'background image'
    if BGMOVIE:
        offset = int(round(MOVIEOFFSET * 1000)) - MS_OSU_MUSIC_OFFSET
        print(f'Video,{offset},"{BGMOVIE}",0,0', file=fout)
        chart_resources[BGMOVIE] = 'background video'

    print("//Break Periods", file=fout)
    print("//Storyboard Layer 0 (Background)", file=fout)
    print("//Storyboard Layer 1 (Fail)", file=fout)
    print("//Storyboard Layer 2 (Pass)", file=fout)
    print("//Storyboard Layer 3 (Foreground)", file=fout)
    print("//Storyboard Layer 4 (Overlay)", file=fout)
    print("//Storyboard Sound Samples", file=fout)
    print("", file=fout)

def write_TimingPoints(fout: TextIO) -> None:
    print("[TimingPoints]", file=fout)
    volume = int(round(min(100, 100 * abs(SEVOL) / max(1, abs(SONGVOL)))))
    res: List[Tuple[int, str]] = []
    for tm in TimingPoints:
        if tm.beats / tm.bpm < 0:
            continue # ignore negative sections (assumed to be overlapped by later positive sections)
        time = int(tm.offset)
        while len(res) > 0 and res[-1][0] > time:
            res.pop() # override overlapped positive sections
        meter = max(1, int(round(tm.beats)))
        fx = tm.ggt + 8 * tm.hidefirst.is_hidden()
        if tm.is_redline():
            beat_dur = min(max(abs(60000.0 / tm.bpm), 6E-298), 6E+298)
            res.append((time, f"{time},{beat_dur},{meter},1,0,{volume},1,{fx}"))
        if not tm.is_redline() or tm.scroll != 1.0:
            beat_dur = -100 / tm.scroll
            res.append((time, f"{time},{beat_dur},{meter},1,0,{volume},0,{fx}"))
        tm.offset = int(tm.offset)

    # res is sorted
    for _, line in res:
        print(line, file=fout)
    print("", file=fout)

def write_HitObjects(fout: TextIO) -> None:
    print("[HitObjects]", file=fout)
    lasting_note = None
    res: List[Tuple[int, str]] = []
    for ho in HitObjects:
        beg_offset = get_real_offset(ho.offset)
        if int(beg_offset) != int(ho.offset):
            if debug_mode:
                print_with_pended("OFFSET FIXED", int(beg_offset), int(ho[2]), file=sys.stderr)
        if ho.type == CIRCLE:
            assert lasting_note is None, "this is abnormal"
            res.append((beg_offset, "%d,%d,%d,%d,%d" % (CircleX, CircleY, beg_offset, ho.type, ho.sound)))
        elif ho.type == SLIDER:
            assert lasting_note is None, "this is abnormal"
            lasting_note = ho
        elif ho.type == SPINNER:
            assert lasting_note is None, "this is abnormal"
            lasting_note = ho
        elif ho.type == SLIDER_END:
            assert lasting_note is not None and \
                    lasting_note.type == SLIDER
            ln = lasting_note
            if ho.offset > ln.offset: # skip non-positive duration rolls
                tmr = get_red_tm_at(TimingPoints, int(ln.offset))
                tmg = get_tm_at(TimingPoints, int(ln.offset)) # green if red + green, otherwise red
                curve_len = 100 * (ho.offset - ln.offset) * tmr.bpm  * SliderMultiplier * tmg.scroll / 60000
                res.append((beg_offset, "%d,%d,%d,%d,%d,L|%d:%d,%d,%f" % (CircleX, CircleY, \
                        int(get_real_offset(ln.offset)), ln.type, ln.sound, \
                        int(CircleX+curve_len), CircleY, 1, curve_len)))
            lasting_note = None
        elif ho.type == SPINNER_END:
            assert lasting_note is not None and \
                    lasting_note.type == SPINNER, "this is abnormal"
            ln = lasting_note
            if ho.offset > ln.offset: # skip non-positive length rolls
                res.append((beg_offset, "%d,%d,%d,%d,%d,%d" % (CircleX, CircleY, int(get_real_offset(ln.offset)), \
                        ln.type, ln.sound, int(get_real_offset(ho.offset)))))
            lasting_note = None

    res.sort(key=lambda x: x[0])
    for _, line in res:
        print(line, file=fout)
    print("", file=fout)

def tja2osu(filename: str, fout: TextIO) -> Dict[str, str]:
    init_globals()
    assert isinstance(filename, str)
    assert filename.endswith(".tja"), "filename should ends with .tja"
    check_unsupported(filename)

    # real work
    get_meta_data(filename)
    write_fmt_ver_str(fout)
    write_General(fout)
    write_Editor(fout)
    write_Metadata(fout)
    write_Difficulty(fout)
    write_Events(fout)

    get_all(filename)
    write_TimingPoints(fout)
    write_HitObjects(fout)

    init_debug_globals()
    return chart_resources


def main():
    global BEAT_RES, debug_mode, print_each_note
    parser = argparse.ArgumentParser(
        description='Convert a single-notechart branch-less .tja file to .osu format and print the result.',
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("filename",
        help="source .tja file. Allows only 1 notechart definition (`#START` to `#END`) and no branch commands.")
    parser.add_argument("options", nargs="*", choices=["debug", []], metavar="{debug}",
        help="extra options (deprecated usage). Can also be specified as --<option> ")
    parser.add_argument("-b", "--beat-align", nargs="?", const=48, type=int, default=BEAT_RES,
        help="align hit objects to specified division of a beat (48 if omitted). Default: No aligning (0).")
    parser.add_argument("-d", "--debug", action="store_true",
        help="display general debug info")
    parser.add_argument("-v", "--verbose", action="store_true",
        help="display debug info for each note")
    args = parser.parse_args()
    BEAT_RES = args.beat_align
    debug_mode = args.debug or ("debug" in args.options)
    print_each_note = args.verbose
    tja2osu(args.filename, sys.stdout)

if __name__ == "__main__":
    try:
        main()
    finally:
        input("Conversion done. Press any key to exit...")

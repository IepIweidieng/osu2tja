# sys.path hack
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from common.tja import ENoteTja, TjaCmd, convert_str, get_course_by_number, parse_tja_command, parse_tja_header
from common.utils import print_with_pended
from common.osu import T_MINUTE, EHitTypeOsu, EHitSoundOsu, ETimingFxOsu, EHideFirst, OsuTimingPoint, almost_bigger, almost_equals, ceil_if_almost_int, get_idx_tm_at, get_last_red_tm, get_last_tm, get_osu_meter, get_red_tm_at, get_tm_at

import argparse
import codecs
from dataclasses import dataclass, field
import math
import re
import sys
import traceback
from typing import Dict, List, Optional, TextIO, Tuple, TypeVar, Union, cast


@dataclass
class Global:
    # jiro data
    ENCODING: Optional[str] = None
    TITLE: str = "NO TITLE"
    SUBTITLE: str = ""
    ARTIST: str = ""
    GENRE: List[str] = field(default_factory=list)
    BPM: float = 120.0
    WAVE: Optional[str] = None
    OFFSET: float = 0.0
    DEMOSTART: float = 0.0
    HEADSCROLL: Union[complex, float] = 1.0
    MAKER: Optional[str] = None
    CREATOR: Optional[str] = None
    SONGVOL: float = 100.0
    SEVOL: float = 100.0
    COURSE: str = "Oni"
    LEVEL: float = 0
    PREIMAGE: Optional[str] = None
    BGIMAGE: Optional[str] = None
    BGMOVIE: Optional[str] = None
    MOVIEOFFSET: float = 0.0

    # osu data
    AudioFilename: str = ""
    Title: str = ""
    Source: str = ""
    Tags: List[str] = field(default_factory=lambda: ["tja", "tja2osu"])
    Artist: str = "Unknown Artist"
    Creator: str = "unknown"
    Version: str = "Oni"
    AudioLeadIn: int = 0
    CountDown: int = 0
    SampleSet: str = "Normal"
    StackLeniency: float = 0.7
    Mode: int = 1
    LetterboxInBreaks: int = 0
    PreviewTime: float = -1
    TimingPoints: List[OsuTimingPoint] = field(default_factory=list)
    HitObjects: List["OsuHitObject"] = field(default_factory=list)
    HPDrainRate: int = 7
    CircleSize: int = 5
    OverallDifficulty: float = 8
    ApproachRate: int = 5
    SliderMultiplier: float = 1.4
    SliderTickRate: int = 4
    CircleX: int = 256
    CircleY: int = 192

    chart_resources: Dict[str, str] = field(default_factory=dict) # {'filename': 'type', ...}

    has_started: bool = False
    curr_time: float = 0.0
    bar_data: List[Union[str, TjaCmd]] = field(default_factory=list)
    lasting_note: Optional["OsuHitObject"] = None
    unknowns: set = field(default_factory=set)

@dataclass
class DebugGlobal():
    debug_mode: bool = False
    print_each_note: bool = False
    last_debug: Optional[float] = None

D = DebugGlobal()


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
BARLINE = "BARLINE"
DELAY = "DELAY"
SCROLL = "SCROLL"


def check_unsupported(filename):
    return
    assert isinstance(filename, str)
    assert filename.lower().endswith(".tja"), "filename should ends with .tja"
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

def get_meta_data(G: Global, filename) -> None:
    assert isinstance(filename, str)
    assert filename.lower().endswith(".tja"), "filename should ends with .tja"
    try: fobj = open(filename, "rb")
    except IOError: assert False, "can't open tja file."
    if fobj.peek(len(codecs.BOM_UTF8)).startswith(codecs.BOM_UTF8):
        G.ENCODING = "utf-8-sig"
        fobj.seek(len(codecs.BOM_UTF8)) # ignore UTF-8 BOM
    for lineno, line in enumerate(fobj):
        try:
            line = line.rstrip(b"\r\n")
            v = parse_tja_header(line)
            if v is None: # try metadata in comments
                creator = line.partition(b"//created by ")[2].strip()
                if creator: G.CREATOR = convert_str(creator, G.ENCODING)
                continue
            varg_raw = v.arg
            v.arg = rm_jiro_comment(v.arg).rstrip()
            if v.name == b"TITLE": G.TITLE = convert_str(varg_raw, G.ENCODING)
            elif v.name == b"SUBTITLE": G.SUBTITLE = convert_str(varg_raw, G.ENCODING)
            elif v.name == b"ARTIST": G.ARTIST = convert_str(varg_raw, G.ENCODING)
            elif v.name == b"GENRE": G.GENRE = parse_tja_genre(convert_str(varg_raw, G.ENCODING))
            elif v.name == b"BPM": G.BPM = float(v.arg)
            elif v.name == b"WAVE": G.WAVE = convert_str(v.arg, G.ENCODING)
            elif v.name == b"OFFSET": G.OFFSET = float(v.arg)
            elif v.name == b"DEMOSTART": G.DEMOSTART = float(v.arg)
            elif v.name == b"HEADSCROLL": G.HEADSCROLL = parse_tja_complex(v.arg)
            elif v.name in (b"MAKER", b"AUTHOR"): G.MAKER = convert_str(varg_raw, G.ENCODING)
            elif v.name == b"SONGVOL": G.SONGVOL = float(v.arg)
            elif v.name == b"SEVOL": G.SEVOL = float(v.arg)
            elif v.name == b"COURSE": G.COURSE = get_course_by_number(convert_str(v.arg, G.ENCODING))
            elif v.name == b"LEVEL": G.LEVEL = float(v.arg)
            elif v.name in (b"PREIMAGE", b"COVER"): G.PREIMAGE = convert_str(v.arg, G.ENCODING)
            elif v.name == b"BGIMAGE": G.BGIMAGE = convert_str(v.arg, G.ENCODING)
            elif v.name == b"BGMOVIE": G.BGMOVIE = convert_str(v.arg, G.ENCODING)
            elif v.name == b"MOVIEOFFSET": G.MOVIEOFFSET = float(v.arg)
            elif (v.name+b':') not in G.unknowns:
                line_printable = convert_str(line.removesuffix(b'\n'), G.ENCODING)
                print_with_pended(f"// Warning: Unknown or unsupported header {line_printable}", file=sys.stderr)
                G.unknowns.add(v.name+b':')
        except Exception:
            for line in traceback.format_exc().splitlines():
                print_with_pended(f"// {line}", file=sys.stderr)
            print_with_pended(f"// Error parsing header in `{filename}` at line {lineno}: `{line}`. Continued.", file=sys.stderr)

MS_OSU_MUSIC_OFFSET = 15
"""Ranked osu! beatmaps have late music / early chart sync. osu!'s new audio engine applies a global 15ms chart delay.
<https://github.com/ppy/osu/issues/24625>
"""

def add_default_timing_point(G: Global):
    tm = OsuTimingPoint(
        offset = -(G.OFFSET * 1000.0 + MS_OSU_MUSIC_OFFSET),
        scroll = 1.0,
        beats = 4.0,
        ggt = False,
        hidefirst = EHideFirst.SHOWN,
        bpm = G.BPM,
        mspb = abs(T_MINUTE / G.BPM),
    )
    tm.redtm = tm

    G.TimingPoints.append(tm)

    G.curr_time = tm.offset


def get_osu_type(G: Global, snd: Union[ENoteTja, str]) -> Optional[EHitTypeOsu]:
    if not isinstance(snd, ENoteTja):
        snd = ENoteTja(snd)
    snd = cast(ENoteTja, snd)
    assert snd != ENoteTja.NONE

    # non-rolls: end unended roll first if exists, then emit the note
    if snd.is_hit_type():
        return EHitTypeOsu.CIRCLE if G.lasting_note is None else EHitTypeOsu.FORCED_END
    # converted to empty
    if snd in (ENoteTja.ADLIB, ENoteTja.BOMB):
        return None if G.lasting_note is None else EHitTypeOsu.FORCED_END
    # roll heads: ignore repeated roll heads (especially for special balloon bonus border)
    if snd.is_renda_type():
        return EHitTypeOsu.SLIDER if G.lasting_note is None else None
    if snd.is_balloon_type():
        return EHitTypeOsu.SPINNER if G.lasting_note is None else None
    # roll end and unrecognized note symbols
    if snd == ENoteTja.END:
        if G.lasting_note is not None and G.lasting_note.type == EHitTypeOsu.SLIDER:
            return EHitTypeOsu.SLIDER_END
        elif G.lasting_note is not None and G.lasting_note.type == EHitTypeOsu.SPINNER:
            return EHitTypeOsu.SPINNER_END
        print_with_pended(f"// Warning: Straying TJA note symbol 8 (roll-type end)", file=sys.stderr)
        return None
    if snd not in G.unknowns:
        print_with_pended(f"// Warning: Unknown TJA note symbol {repr(snd)}", file=sys.stderr)
        G.unknowns.add(snd)
    if G.lasting_note is not None:
        print_with_pended(f"// Note: With unended roll-type note {G.lasting_note}", file=sys.stderr)
    return None

def get_osu_sound(G: Global, snd: Union[ENoteTja, str]) -> EHitSoundOsu:
    if not isinstance(snd, ENoteTja):
        snd = ENoteTja(snd)
    snd = cast(ENoteTja, snd)
    assert snd != ENoteTja.NONE

    if snd == ENoteTja.DON: return EHitSoundOsu.EMPTY
    elif snd == ENoteTja.KATSU: return EHitSoundOsu.CLAP
    elif snd in (ENoteTja.DON_DAI, ENoteTja.DON_HAND): return EHitSoundOsu.FINISH
    elif snd in (ENoteTja.KATSU_DAI, ENoteTja.KATSU_HAND): return EHitSoundOsu.FINISH | EHitSoundOsu.CLAP
    elif snd == ENoteTja.KADON: return EHitSoundOsu.FINISH | EHitSoundOsu.WHISTLE | EHitSoundOsu.CLAP
    elif snd == ENoteTja.RENDA: return EHitSoundOsu.EMPTY
    elif snd == ENoteTja.RENDA_PA: return EHitSoundOsu.CLAP
    elif snd == ENoteTja.RENDA_DAI: return EHitSoundOsu.FINISH
    elif snd == ENoteTja.RENDA_CLAP: return EHitSoundOsu.FINISH | EHitSoundOsu.CLAP
    elif snd == ENoteTja.BALLOON: return EHitSoundOsu.EMPTY
    elif snd == ENoteTja.END: return EHitSoundOsu.EMPTY
    elif snd == ENoteTja.IMO: return EHitSoundOsu.FINISH
    elif snd == ENoteTja.FUZE: return EHitSoundOsu.CLAP
    else: return EHitSoundOsu.EMPTY # empty or unknown and warned


def get_all(G: Global, filename):
    try: fobj = open(filename, "rb")
    except IOError: assert False, "can't open tja file."
    if fobj.peek(len(codecs.BOM_UTF8)).startswith(codecs.BOM_UTF8):
        fobj.seek(len(codecs.BOM_UTF8)) # ignore UTF-8 BOM

    G.has_started = False
    add_default_timing_point(G)
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
                if not G.has_started and cmd.name == START:
                    G.has_started = True
                    if G.HEADSCROLL != 1.0:
                        real_do_cmd(G, (SCROLL, G.HEADSCROLL))
                    continue
                if cmd.name == END:
                    break
                handle_cmd(G, line, cmd)
                continue
            handle_note(G, line)
        except Exception:
            for line in traceback.format_exc().splitlines():
                print_with_pended(f"// {line}", file=sys.stderr)
            print_with_pended(f"// Error parsing note chart in `{filename}` at line {lineno}: `{line}`. Continued.", file=sys.stderr)
    else:
        print_with_pended(f"// Warning: Missing #END at end of chart.", file=sys.stderr)
    if len(G.bar_data) != 0:
        print_with_pended(f"// Warning: Missing comma (,) at end of chart.", file=sys.stderr)
        handle_note(G, ",")
    if G.lasting_note is not None:
        print_with_pended(f"// Warning: Unended roll-type note {G.lasting_note} ended by end of chart at {G.curr_time}.", file=sys.stderr)
        add_a_note(G, '8', G.curr_time)

    # prevent bar lines at and after #END (probably missing and implicit)
    tm = get_last_red_tm(G.TimingPoints)
    real_do_cmd(G, (MEASURE, math.ceil(min(max(tm.beats, tm.bpm, 1), (1 << 31) - 1)))) # insert a >= 1 minute measure
    real_do_cmd(G, (BARLINEOFF,)) # hide its bar line

# get quantized offset by the nearest base timing point
# step 1: find the base timing point around base offset b at or before t
# step 2: calculate the quantized unit count from t to the base timing point
# step 3: get quantized offset from quantized unit count and bpm
# step 4: find the nearest any-color timing points, past point p and future point f
# step 5: adjust quantized offset so that it is at or after point p and before point f

BEAT_RES = 0 # aligning disabled

def get_real_offset(G: Global, dirty_offset: Union[int, float], base_offset: Optional[float] = None, raw: bool = False) -> float:
    if D.debug_mode:
        print_with_pended("// Dirty Offset", dirty_offset, file=sys.stderr)
    if BEAT_RES <= 0:
        aligned_offset = dirty_offset
    else:
        if base_offset is None:
            base_offset = dirty_offset
        tm = get_red_tm_at(G.TimingPoints, base_offset, raw)
        delta = dirty_offset - tm.offset # more accurate
        t_unit = tm.mspb / BEAT_RES
        t_unit_cnt = round(delta / t_unit)
        aligned_offset = tm.offset + t_unit_cnt * t_unit

        if D.debug_mode:
            print_with_pended(f"// {tm}", file=sys.stderr)
            print("// DELTA = ", delta, file=sys.stderr)
            print("// GET UNIT CNT", t_unit, t_unit_cnt, file=sys.stderr)
            print("//", dirty_offset, "-->", tm.offset + t_unit_cnt * t_unit, file=sys.stderr)

    ret = aligned_offset
    if raw:
        idx_tm_p = get_idx_tm_at(G.TimingPoints, dirty_offset, raw)
        tm_p_offset = G.TimingPoints[idx_tm_p].offset
        int_tm_p_offset = int(tm_p_offset)
        if ret < tm_p_offset:
            ret = int_tm_p_offset
        if idx_tm_p + 1 < len(G.TimingPoints):
            tm_f_offset = G.TimingPoints[idx_tm_p + 1].offset
            int_tm_f_offset = int(tm_f_offset)
            if ret >= int_tm_f_offset:
                ret = max(int_tm_p_offset, int_tm_f_offset - 1)
            if int_tm_f_offset <= int_tm_p_offset:
                print_with_pended(f"// Warning: time {aligned_offset} is between timing points at {tm_p_offset} and {tm_f_offset}, with overlapping integer offset {int_tm_p_offset} and {int_tm_f_offset}", file=sys.stderr)

    return ret
   
def handle_cmd(G: Global, line: str, cmd: TjaCmd) -> None:
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

    if G.bar_data == [] or cmd.name == MEASURE:
        real_do_cmd(G, cmd)
    else:
        G.bar_data.append(cmd)

def real_do_cmd(G: Global, cmd: Union[Tuple, TjaCmd]):
    if not isinstance(cmd, TjaCmd):
        cmd = TjaCmd(*cmd)
    cmd = cast(TjaCmd, cmd)

    if D.debug_mode:
        print_with_pended("// handle cmd", cmd, file=sys.stderr)
    
    # handle delay, no timing point change
    if cmd.name == DELAY:
        G.curr_time += cmd.args[0] * 1000
        return
    
    # handle timing point change command
    if cmd.name == BPMCHANGE:
        tm = get_or_create_curr_red_tm(G)
        tm.bpm = cmd.args[0]
        tm.mspb = abs(T_MINUTE / tm.bpm)
    elif cmd.name == MEASURE: # processed before notes
        if len(G.bar_data) != 0:
            print_with_pended("// Warning: Changing measure within a bar is handled as changing at the start of bar.", file=sys.stderr)
            get_last_red_tm(G.TimingPoints).beats = cmd.args[0]
        else:
            get_or_create_curr_red_tm(G).beats = cmd.args[0]
    elif cmd.name == SCROLL:
        get_or_create_curr_tm(G).scroll = abs(cmd.args[0])
    elif cmd.name == GOGOSTART:
        get_or_create_curr_tm(G).ggt = True
    elif cmd.name == GOGOEND:
        get_or_create_curr_tm(G).ggt = False
    elif cmd.name == BARLINEOFF:
        tm = get_or_create_curr_tm(G)
        tm.hidefirst = tm.hidefirst.barline_off()
    elif cmd.name == BARLINEON:
        tm = get_or_create_curr_tm(G)
        tm.hidefirst = tm.hidefirst.barline_on()
    elif cmd.name == BARLINE:
        tm = get_or_create_curr_tm(G)
        tm.hidefirst = tm.hidefirst.add_barline()
    elif ('#'+cmd.name) not in G.unknowns:
        print_with_pended(f"// Warning: Unknown or unsupported command {cmd}.", file=sys.stderr)
        G.unknowns.add('#'+cmd.name)

@dataclass
class OsuHitObject:
    type: EHitTypeOsu
    sound: EHitSoundOsu
    offset: float

def add_a_note(G: Global, snd, offset):
    (osu_type, osu_sound) = (get_osu_type(G, snd), get_osu_sound(G, snd))
    if osu_type == EHitTypeOsu.FORCED_END: # end unended roll, then emit the note
        add_a_note(G, '8', offset)
        add_a_note(G, snd, offset)
        return
    if osu_type is None:
        return
    obj = OsuHitObject(osu_type, osu_sound, offset)
    G.HitObjects.append(obj)
    if osu_type in (EHitTypeOsu.SLIDER, EHitTypeOsu.SPINNER):
        G.lasting_note = obj
    if osu_type in (EHitTypeOsu.SLIDER_END, EHitTypeOsu.SPINNER_END):
        G.lasting_note = None
    if D.debug_mode:
        print_with_pended(f"// {G.HitObjects[-1]}", file=sys.stderr)

def create_new_tm(G: Global, has_red: bool = False, last_tm: Optional[OsuTimingPoint] = None, last_red_tm: Optional[OsuTimingPoint] = None):
    if last_tm is None:
        last_tm = get_last_tm(G.TimingPoints)
    if last_red_tm is None:
        last_red_tm = get_last_red_tm(G.TimingPoints)

    tm = OsuTimingPoint(
        offset = G.curr_time,
        offset_raw = G.curr_time,
        redtm = last_red_tm, # can upgrade to red + green later if not having red
        scroll = last_tm.scroll if last_tm is not None else 1.0,
        beats = last_tm.beats,
        ggt = last_tm.ggt,
        hidefirst = last_tm.hidefirst.remove_barline(),
        bpm = last_red_tm.bpm,
        mspb = last_red_tm.mspb,
    )
    if has_red:
        tm.redtm = tm
    if D.debug_mode:
        print_with_pended("// CREATE NEW TM", tm, file=sys.stderr)
    
    G.TimingPoints.append(tm)
    return tm

def get_or_create_curr_tm(G: Global, need_red: bool = False):
    tm = get_last_tm(G.TimingPoints)
    if G.curr_time != tm.offset:
        tm = create_new_tm(G, need_red)
    elif need_red and not tm.is_redline(): # needs to upgrade to red + green
        tm.redtm = tm
    return tm

def get_or_create_curr_red_tm(G: Global):
    return get_or_create_curr_tm(G, True)

def get_t_unit(tm: OsuTimingPoint, tot_note):
    if D.debug_mode:
        print_with_pended("//", tm.bpm, tot_note, file=sys.stderr)
    return tm.beats * T_MINUTE / (tm.bpm * tot_note)

def handle_a_bar(G: Global):
    #debug
    if D.last_debug is None:
        D.last_debug = G.TimingPoints[0].offset
    #debug

    tot_note = 0
    for data in G.bar_data:
        if isinstance(data, str):
            tot_note += 1

    if D.debug_mode:
        print_with_pended("// TOT_NOTE", tot_note, file=sys.stderr)
        pure_data = [x for x in G.bar_data if isinstance(x, str) and x[0].isdigit()]
        p1= "%6d %2.1f %2d %s" % (int(G.curr_time), \
                get_last_red_tm(G.TimingPoints).beats, len(pure_data), \
                "".join(pure_data))

        p2= "%s %s" % (repr(get_last_red_tm(G.TimingPoints).bpm), \
                repr(get_t_unit(get_last_red_tm(G.TimingPoints), max(1, tot_note)) * max(1, tot_note)))
        print_with_pended(f"// {p1}", file=sys.stderr)

    #debug
    D.last_debug = G.curr_time
    bak_curr_time = G.curr_time
    note_cnt = -1
    #debug

    if not get_last_tm(G.TimingPoints).hidefirst.remove_barline().is_hidden():
        real_do_cmd(G, (BARLINE,))
    if not tot_note: # empty or command-only measure
        G.curr_time += get_t_unit(get_last_red_tm(G.TimingPoints), 1)
    else:
        for data in G.bar_data:
            if isinstance(data, str): #note
                note_cnt += 1
                if data != "0":
                    add_a_note(G, data, G.curr_time)
                    if D.print_each_note:
                        print_with_pended("//", note_cnt, data, G.curr_time,
                            bak_curr_time + note_cnt * get_t_unit(get_last_red_tm(G.TimingPoints), tot_note),
                            get_t_unit(get_last_red_tm(G.TimingPoints), tot_note),
                            file=sys.stderr)
                G.curr_time += get_t_unit(get_last_red_tm(G.TimingPoints), tot_note)           
            else: #cmd
                real_do_cmd(G, data)
    G.bar_data = [] 
    
    if D.print_each_note:
        print_with_pended(f"// after bar, curr_time= {G.curr_time}", file=sys.stderr)

def handle_note(G: Global, line: str):
    for ch in line:
        if ch.isalnum() and ch.isascii():
            G.bar_data.append(ch)
        elif ch == ",":
            handle_a_bar(G)
        elif not ch.isspace():
            print_with_pended(f"// Warning: Invalid TJA note symbol {repr(ch)} ignored", file=sys.stderr)

def write_fmt_ver_str(G: Global, fout: TextIO) -> None:
    print("osu file format v14", file=fout)
    print("", file=fout)

def write_General(G: Global, fout: TextIO) -> None:
    if G.WAVE:
        G.AudioFilename = G.WAVE
        G.chart_resources[G.WAVE] = 'song audio'
    else:
        G.AudioFilename = ""
    G.PreviewTime = G.DEMOSTART * 1000 - MS_OSU_MUSIC_OFFSET

    print("[General]", file=fout)
    print("AudioFilename: %s" % (G.AudioFilename,), file=fout)
    print("AudioLeadIn: %d" % (round(G.AudioLeadIn)), file=fout)
    print("PreviewTime: %d" % (round(G.PreviewTime)), file=fout)
    print("CountDown: %d" % (G.CountDown,), file=fout)
    print("SampleSet: %s" % (G.SampleSet,), file=fout)
    print("StackLeniency: %s" % (repr(G.StackLeniency),), file=fout)
    print("Mode: %d" % (G.Mode,), file=fout)
    print("LetterboxInBreaks: %d" % (G.LetterboxInBreaks,), file=fout)
    print("", file=fout)

# no use, but required by osu
def write_Editor(G: Global, fout: TextIO) -> None:
    print("[Editor]", file=fout)
    print("DistanceSpacing: 0.8", file=fout)
    print("BeatDivisor: 4", file=fout)
    print("GridSize: 4", file=fout)
    print("", file=fout)

pat_work_info = re.compile(r'^\w*?(?:ドラマ|[\w ]*?Drama|剧|劇|アニメ|[\w ]*? Anime|动画|動畫|映画|[\w ]*? Movie|电影|電影|CMソング)')
pat_song_type = re.compile(r'(?:(?:オープニング・?|OP|エンディング・?|ED)?(?:テーマ|主題)[歌曲]?|(?:Opening |Ending )?Theme( Song)?|(?:主[题題]|片[头頭尾])[歌曲]?|デモソング|Demo Song|メドレー|Medley|組曲) *$')

def parse_tja_subtitle(G: Global, title: str, subtitle: str, genres: List[str]) -> Tuple[str, str, str]: # Title, Artist, Source
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
        return title + " " + subtitle, artist or G.Artist, source or G.Source

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

    return title, artist or G.Artist, source or G.Source

def write_Metadata(G: Global, fout: TextIO) -> None:
    G.Title, G.Artist, G.Source = parse_tja_subtitle(G, G.TITLE, G.SUBTITLE, G.GENRE)
    if not G.Artist:
        G.Artist = G.ARTIST # fallback, as ARTIST: for Malody is romanized
    G.Creator = G.MAKER or G.CREATOR or G.Creator
    G.Version = G.COURSE
    G.Tags.extend((genre for genre in G.GENRE if genre not in ("namco", "opentaiko")))
    for i, tag in enumerate(G.Tags):
        G.Tags[i] = tag.strip().replace(' ', '_')
    print("[Metadata]", file=fout)
    print("Title:%s" % (G.Title,), file=fout)
    print("Artist:%s" % (G.Artist,), file=fout)
    print("Creator:%s" % (G.Creator,), file=fout)
    print("Version:%s" % (G.Version,), file=fout)
    print("Source:%s" % (G.Source,), file=fout)
    print("Tags:%s" % (" ".join(G.Tags),), file=fout)
    print("", file=fout)

def write_Difficulty(G: Global, fout: TextIO) -> None:
    course = G.COURSE.lower()
    # lower-limit of ranking guideline if note count is not high
    G.HPDrainRate = (8 if course.startswith('easy')
        else 7 if course.startswith('normal')
        else 6 if course.startswith('hard')
        else (5 if G.LEVEL < 8 else 6)) # for higher BAD penalty
    G.OverallDifficulty = (2.3 if course.startswith('easy') or course.startswith('normal') # 42.5ms for GREAT/GOOD
        else 5 if course.startswith('hard') # upper-limit of ranking guideline
        else 8) # 25.5ms for GREAT/GOOD

    print("[Difficulty]", file=fout)
    print("HPDrainRate:%s" % (repr(G.HPDrainRate),), file=fout)
    print("CircleSize:%s" % (repr(G.CircleSize),), file=fout)
    print("OverallDifficulty:%s" % (repr(G.OverallDifficulty),), file=fout)
    print("ApproachRate:%s" % (repr(G.ApproachRate),), file=fout)
    print("SliderMultiplier:%s" % (repr(G.SliderMultiplier),), file=fout)
    print("SliderTickRate:%s" % (repr(G.SliderTickRate),), file=fout)
    print("", file=fout)

def write_Events(G: Global, fout: TextIO) -> None:
    print("[Events]", file=fout)
    print("//Background and Video events", file=fout)

    # FIXME: What if the filename contains double quotes (")?
    bg = G.BGIMAGE or G.PREIMAGE
    if bg:
        print(f'0,0,"{bg}",0,0', file=fout)
        G.chart_resources[bg] = 'background image'
    if G.BGMOVIE:
        offset = int(round(G.MOVIEOFFSET * 1000)) - MS_OSU_MUSIC_OFFSET
        print(f'Video,{offset},"{G.BGMOVIE}",0,0', file=fout)
        G.chart_resources[G.BGMOVIE] = 'background video'

    print("//Break Periods", file=fout)
    print("//Storyboard Layer 0 (Background)", file=fout)
    print("//Storyboard Layer 1 (Fail)", file=fout)
    print("//Storyboard Layer 2 (Pass)", file=fout)
    print("//Storyboard Layer 3 (Foreground)", file=fout)
    print("//Storyboard Layer 4 (Overlay)", file=fout)
    print("//Storyboard Sound Samples", file=fout)
    print("", file=fout)


def write_TimingPoints(G: Global, fout: TextIO) -> None:
    # flatten timing points
    tms: List[OsuTimingPoint] = []
    for tm in G.TimingPoints:
        # ignore (assumely overlapped) negative sections
        negative = tm.beats / tm.bpm < 0
        if tm.hidefirst.is_barline():
            if negative:
                tm.redtm = None # reset pointer later
            tms.append(tm)
        elif not negative:
            # ignore overlapped positive sections
            for j in range(len(tms), 0, -1):
                tmj = tms[j - 1]
                if tmj.offset < tm.offset:
                    break
                if tmj.hidefirst.is_barline():
                    tm.redtm = None # reset pointer later
                else:
                    tms.pop(j)
            tms.append(tm)
    tms.sort(key=lambda tm: tm.offset)

    print("[TimingPoints]", file=fout)
    volume = int(round(min(100, 100 * abs(G.SEVOL) / max(1, abs(G.SONGVOL)))))
    tm_idx = 0
    tmg = tmr = tms[0]
    G.TimingPoints = [tmr] # rebuild

    # use the last timing points if simultaneous
    queued_ms: Optional[float] = None
    queued_red: Optional[str] = None
    queued_green: Optional[str] = None

    def write_queue(ms: Optional[float] = None, force: bool = False) -> None:
        nonlocal queued_ms, queued_red, queued_green
        if ms != queued_ms or force:
            queued_ms = ms
            if queued_red is not None:
                print(queued_red, file=fout)
            queued_red = None
            if queued_green is not None:
                print(queued_green, file=fout)
            queued_green = None

    def emit_tm(tm: OsuTimingPoint) -> float:
        nonlocal tmr, tmg, queued_red, queued_green

        if tm.redtm is None: # reset for bar lines in negative or overlapped sections
            hidefirst = tm_next.hidefirst
            tm_next.merge_with(tmg, tmr)
            tm_next.hidefirst = hidefirst
        if tm.is_redline():
            tmr = tm

        # write
        write_queue(int(tm.offset))
        meter = get_osu_meter(tmr.beats) # convert x.x measure to incomplete measure
        fx = ((ETimingFxOsu.GGT if tm.ggt else ETimingFxOsu.NONE)
            | (ETimingFxOsu.HIDEFIRST if not tm.hidefirst.is_barline() else ETimingFxOsu.NONE))
        if tm.is_redline():
            beat_dur = min(max(tmr.mspb, 6E-298), 6E+298)
            queued_red = f"{int(tm.offset)},{beat_dur},{meter},1,0,{volume},1,{fx.value}"
        if not tm.is_redline() or tm.scroll != 1.0:
            beat_dur = -100 / tm.scroll
            queued_green = f"{int(tm.offset)},{beat_dur},{meter},1,0,{volume},0,{fx.value}"
        # update
        tm.redtm = tmr
        tmg = tm
        tm.offset = int(tm.offset)
        G.TimingPoints.append(tm)
        return tm.offset

    # simulate osu rounding error
    bar_offset_end = bar_offset_begin = tmr.offset
    bar_offset_end += get_osu_meter(tmr.beats) * tmr.mspb

    while tm_idx < len(tms):
        tm_next = tms[tm_idx]

        # skip effects
        aligned_end = ceil_if_almost_int(bar_offset_end)
        if not tm_next.is_redline() and not tm_next.hidefirst.is_barline() and tm_next.offset < aligned_end:
            tm_next.offset = max(tm_next.offset, bar_offset_begin)
            emit_tm(tm_next)
            tm_idx += 1
            continue

        if (tm_next.is_redline()
            and (not almost_bigger(tm_next.offset, bar_offset_end) or int(tm_next.offset) <= int(bar_offset_end))
            ): # red timing point reached
            aligned_end = emit_tm(tm_next)
            tm_idx += 1
        elif (tm_next.hidefirst.is_barline()
            and (almost_equals(tm_next.offset, aligned_end) or int(tm_next.offset) == int(aligned_end))
            ): # bar line reached expectedly
            emit_tm(tm_next)
            tm_idx += 1
        elif (tm_next.hidefirst.is_barline()
            and (not almost_bigger(tm_next.offset, aligned_end) and int(tm_next.offset) < int(aligned_end))
            ): # bar line reached early
            # promote to red
            hidefirst = tm_next.hidefirst
            tm_next.merge_with(tmg if tm_next.redtm is None else None, tmr=tmr)
            tm_next.hidefirst = hidefirst.add_barline()
            tm_next.redtm = tm_next
            aligned_end = emit_tm(tm_next)
            tm_idx += 1
        else: # no bar lines or hidden
            tm_next = create_new_tm(G, True, tmg, tmr)
            tm_next.offset = tm_next.offset_raw = aligned_end
            tm_next.hidefirst = tm_next.hidefirst.remove_barline()
            aligned_end = emit_tm(tm_next)

        # next measure
        # simulate osu rounding error
        bar_offset_end = bar_offset_begin = aligned_end
        bar_offset_end += get_osu_meter(tmr.beats) * tmr.mspb

    write_queue(force=True)
    print("", file=fout)

def write_HitObjects(G: Global, fout: TextIO) -> None:
    print("[HitObjects]", file=fout)
    lasting_note = None
    res: List[Tuple[float, str]] = []
    for ho in G.HitObjects:
        beg_offset = get_real_offset(G, ho.offset)
        if int(beg_offset) != int(ho.offset):
            if D.debug_mode:
                print_with_pended("// OFFSET FIXED", int(beg_offset), int(ho.offset), file=sys.stderr)
        if ho.type == EHitTypeOsu.CIRCLE:
            assert lasting_note is None, "this is abnormal"
            res.append((beg_offset, "%d,%d,%d,%d,%d" % (G.CircleX, G.CircleY, beg_offset, ho.type.value, ho.sound.value)))
        elif ho.type == EHitTypeOsu.SLIDER:
            assert lasting_note is None, "this is abnormal"
            lasting_note = ho
        elif ho.type == EHitTypeOsu.SPINNER:
            assert lasting_note is None, "this is abnormal"
            lasting_note = ho
        elif ho.type == EHitTypeOsu.SLIDER_END:
            assert lasting_note is not None and \
                    lasting_note.type == EHitTypeOsu.SLIDER
            ln = lasting_note
            if ho.offset > ln.offset: # skip non-positive duration rolls
                tmr = get_red_tm_at(G.TimingPoints, int(ln.offset))
                tmg = get_tm_at(G.TimingPoints, int(ln.offset)) # green if red + green, otherwise red
                curve_len = 100 * (ho.offset - ln.offset) * tmr.bpm  * G.SliderMultiplier * tmg.scroll / T_MINUTE
                res.append((beg_offset, "%d,%d,%d,%d,%d,L|%d:%d,%d,%f" % (G.CircleX, G.CircleY, \
                        int(get_real_offset(G, ln.offset)), ln.type.value, ln.sound.value, \
                        int(G.CircleX + curve_len), G.CircleY, 1, curve_len)))
            lasting_note = None
        elif ho.type == EHitTypeOsu.SPINNER_END:
            assert lasting_note is not None and \
                    lasting_note.type == EHitTypeOsu.SPINNER, "this is abnormal"
            ln = lasting_note
            if ho.offset > ln.offset: # skip non-positive length rolls
                res.append((beg_offset, "%d,%d,%d,%d,%d,%d" % (G.CircleX, G.CircleY, int(get_real_offset(G, ln.offset)), \
                        (ln.type | EHitTypeOsu.NC).value, ln.sound.value, int(get_real_offset(G, ho.offset)))))
            lasting_note = None

    res.sort(key=lambda x: x[0])
    for _, line in res:
        print(line, file=fout)
    print("", file=fout)

def tja2osu(filename: str, fout: TextIO, debugGlobal: Optional[DebugGlobal] = None) -> Dict[str, str]:
    if debugGlobal is None:
        debugGlobal = DebugGlobal()
    global D
    D = debugGlobal
    G = Global()
    assert isinstance(filename, str)
    assert filename.lower().endswith(".tja"), "filename should ends with .tja"
    check_unsupported(filename)

    # real work
    get_meta_data(G, filename)
    write_fmt_ver_str(G, fout)
    write_General(G, fout)
    write_Editor(G, fout)
    write_Metadata(G, fout)
    write_Difficulty(G, fout)
    write_Events(G, fout)

    get_all(G, filename)
    write_TimingPoints(G, fout)
    write_HitObjects(G, fout)

    return G.chart_resources


def main():
    global BEAT_RES
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
    debugGlobal = DebugGlobal(debug_mode=args.debug or ("debug" in args.options), print_each_note=args.verbose)
    tja2osu(args.filename, sys.stdout, debugGlobal=debugGlobal)

if __name__ == "__main__":
    try:
        main()
    finally:
        input("// Done. Press the Enter key to exit...")

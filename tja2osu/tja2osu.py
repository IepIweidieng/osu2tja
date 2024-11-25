# $Id$

# sys.path hack
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from common.utils import print_with_pended

import argparse
from bisect import bisect_right
import codecs
import math
import sys
import copy
from typing import List, Optional, OrderedDict, TextIO, Tuple

chart_resources: List[Tuple[str, str]] # [('type', 'filename'), ...]

def reset_global_variables() -> None:
    global ENCODING, TITLE, SUBTITLE, BPM, WAVE, OFFSET, DEMOSTART
    global MAKER, AUTHOR, CREATOR, SONGVOL, SEVOL, COURSE
    # jiro data
    ENCODING = None
    TITLE = "NO TITLE"
    SUBTITLE = "NO SUBTITLE"
    BPM = 0.0
    WAVE = None
    OFFSET = 0.0
    DEMOSTART = 0.0
    MAKER = None
    AUTHOR = None
    CREATOR = None
    SONGVOL = 100.0
    SEVOL = 100.0
    COURSE = "Oni"

    global AudioFilename, Title, Source, Tags, Artist, Artist, Creator, Version
    global AudioLeadIn, CountDown, SampleSet, StackLeniency, Mode, LetterboxInBreaks, PreviewTime
    global TimingPoints, TimingPointsRed, HitObjects
    global HPDrainRate, CircleSize, OverallDifficulty, ApproachRate, SliderMultiplier, SliderTickRate, CircleX, CircleY
    # osu data
    AudioFilename = ""
    Title = ""
    Source = ""
    Tags = "taiko jiro tja"
    Artist = "unknown"
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
    TimingPointsRed = []
    HitObjects = []
    HPDrainRate = 7
    CircleSize = 5
    OverallDifficulty = 8.333
    ApproachRate = 5
    SliderMultiplier = 1.44
    SliderTickRate = 4
    CircleX = 256
    CircleY = 192

    global chart_resources
    chart_resources = []

    global has_started, curr_time, bar_data, lasting_note
    has_started = False
    curr_time = 0.0
    bar_data = []
    lasting_note = None

    global debug_mode, last_debug
    debug_mode = False
    last_debug = None

# const_data
BRANCH = "BRANCH"
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

ENCODINGS_KNOWN = ["utf-8-sig", "gbk", "shift-jis", "big5"]

# guess str
def try_decode(bytes_: bytes, enc_guessed: Optional[str] = None) -> Tuple[Optional[str], str]:
    ret = OrderedDict()
    for enc in ([enc_guessed] if enc_guessed else []) + ENCODINGS_KNOWN:
        try:
            ret[enc] = bytes_.decode(enc)
        except UnicodeError:
            pass
    
    enc_guessed, decoded = None, bytes_.decode("latin-1")
    for enc, dec in ret.items():
        if enc_guessed is None or len(dec) < len(decoded):
            enc_guessed, decoded = enc, dec
    return enc_guessed, decoded

def convert_str(bytes_: bytes, enc_guessed: Optional[str] = None) -> str:
    _, decoded = try_decode(bytes_, enc_guessed)
    return decoded

def check_unsupported(filename):
    return
    assert isinstance(filename, str)
    rtassert(filename.endswith(".tja"), "filename should ends with .tja")
    try: fobj = open(filename, "rb")
    except IOError: rtassert(False, "can't open tja file.")
    if fobj.peek(len(codecs.BOM_UTF8)).startswith(codecs.BOM_UTF8):
        fobj.seek(len(codecs.BOM_UTF8)) # ignore UTF-8 BOM
    END_cnt = 0
    for line in fobj:
        rtassert(("#"+BRANCH).decode() not in line, "don't support branch")
        END_cnt += (("#"+END).decode() in line)
        rtassert(END_cnt <= 1, "don't support multiple fumen.")

def rm_jiro_comment(str_: str) -> str:
    assert isinstance(str_, str)
    return str_.partition('//')[0]

def get_meta_data(filename):
    global ENCODING, TITLE, SUBTITLE, WAVE, OFFSET, DEMOSTART, MAKER, AUTHOR, CREATOR, SONGVOL, SEVOL, COURSE, BPM
    assert isinstance(filename, str)
    rtassert(filename.endswith(".tja"), "filename should ends with .tja")
    try: fobj = open(filename, "rb")
    except IOError: rtassert(False, "can't open tja file.")
    if fobj.peek(len(codecs.BOM_UTF8)).startswith(codecs.BOM_UTF8):
        ENCODING = "utf-8-sig"
        fobj.seek(len(codecs.BOM_UTF8)) # ignore UTF-8 BOM
    for line in fobj:
        line = line.strip()
        vname, _, vval = line.partition(b":")
        vname = vname.strip()
        vval = vval.strip()
        if vname == b"TITLE": TITLE = convert_str(vval, ENCODING)
        elif vname == b"SUBTITLE": SUBTITLE = convert_str(vval, ENCODING)
        elif vname == b"BPM": BPM = float(vval)
        elif vname == b"WAVE": WAVE = convert_str(vval, ENCODING)
        elif vname == b"OFFSET": OFFSET = float(vval)
        elif vname == b"DEMOSTART": DEMOSTART = float(vval)
        elif vname == b"MAKER": MAKER = convert_str(vval, ENCODING)
        elif vname == b"AUTHOR": AUTHOR = convert_str(vval, ENCODING)
        elif vname == b"SONGVOL": SONGVOL = float(vval)
        elif vname == b"SEVOL": SEVOL = float(vval)
        elif vname == b"COURSE": COURSE = convert_str(vval, ENCODING)
        else: # try metadata in comments
            creator = line.partition(b"//created by ")[2].strip()
            if creator: CREATOR = convert_str(creator, ENCODING)

MS_OSU_MUSIC_OFFSET = 15
"""Ranked osu! beatmaps have late music / early chart sync. osu!'s new audio engine applies a global 15ms chart delay.
<https://github.com/ppy/osu/issues/24625>
"""

def add_default_timing_point():
    global curr_time

    tm = {}
    tm["offset"] = -(OFFSET * 1000.0 + MS_OSU_MUSIC_OFFSET)
    tm["redline"] = True
    tm["scroll"] = 1.0
    tm["measure"] = 4.0
    tm["GGT"] = False
    tm["hidefirst"] = False
    tm["bpm"] = BPM

    TimingPoints.append(tm)
    TimingPointsRed.append(tm)

    curr_time = tm["offset"]

CIRCLE = 1
SLIDER = 2
SPINNER = 12 
SLIDER_END = -2
SPINNER_END = -12 

EMPTY = 0
CLAP = 8
FINISH = 4
WHISTLE = 2 

def get_osu_type(snd):
    snd = int(snd)
    assert snd != 0
    if snd in (1, 2, 3, 4): return CIRCLE
    if snd in (5, 6): return SLIDER
    if snd in (7, 9): return SPINNER
    if snd == 8:
        if lasting_note == SLIDER:
            return SLIDER_END
        elif lasting_note == SPINNER:
            return SPINNER_END
    assert False, repr(snd) + repr(lasting_note)

def get_osu_sound(snd):
    snd = int(snd)
    assert snd != 0
    if snd == 1: return EMPTY
    elif snd == 2: return CLAP
    elif snd == 3: return FINISH
    elif snd == 4: return FINISH+CLAP
    elif snd == 5: return EMPTY
    elif snd == 6: return FINISH
    elif snd == 7: return EMPTY
    elif snd == 8: return EMPTY
    elif snd == 9: return EMPTY
    else: assert False


def get_all(filename):
    global has_started, curr_time
    try: fobj = open(filename, "rb")
    except IOError: rtassert(False, "can't open tja file.")
    if fobj.peek(len(codecs.BOM_UTF8)).startswith(codecs.BOM_UTF8):
        fobj.seek(len(codecs.BOM_UTF8)) # ignore UTF-8 BOM

    has_started = False
    add_default_timing_point()
    for line in fobj:
        line = line.decode("latin-1").strip()
        line = rm_jiro_comment(line)
        if not has_started and ("#"+START) in line:
            has_started = True
            continue
        if not has_started: continue
        if ("#"+END) in line:
            break
        if ("#" in line): handle_cmd(line)
        else: handle_note(line)
    # prevent bar lines at and after #END (probably missing and implicit)
    tm = get_last_red_tm()
    real_do_cmd((MEASURE, max(tm["measure"], math.ceil(tm["bpm"])))) # insert a >= 1 minute measure
    real_do_cmd((BARLINEOFF,)) # hide its bar line

def get_real_offset(int_offset):
#    print_with_pended("INTOffset", int_offset, file=sys.stderr)
    tm = get_red_tm_at(int_offset)
    tpb = 60000 / tm["bpm"]
    int_delta = abs(int_offset - tm["offset"])
    sign = (int_offset - tm["offset"] > 0 and 1 or -1)

    t_unit_cnt = round(int_delta * tm["bpm"] * 24 / 60000)

    beat_cnt = t_unit_cnt / 24
    ret = tm["offset"] + beat_cnt * 60000 * sign / tm["bpm"]
    
    if int(ret) in ():
        print_with_pended(tm, file=sys.stderr)
        print(t_unit_cnt, file=sys.stderr)
        print("DELAT = ", int_delta, file=sys.stderr)
        print("GET BEAT CNT", int_delta/tpb, t_unit_cnt/24, file=sys.stderr)
        print(int_offset, "-->", tm["offset"] + beat_cnt * 60000 / tm["bpm"], file=sys.stderr)
        print(int(tm["offset"] + beat_cnt * 60000 / tm["bpm"]), file=sys.stderr)

        print("CMP", int(tm["offset"]+beat_cnt * 60000 * sign / tm["bpm"]), int(2663+60000/tm["bpm"]*beat_cnt), file=sys.stderr)
        
    return ret     
   
def handle_cmd(line: str) -> None:
    cmd = None
    if ("#"+BPMCHANGE) in line:
        bpm = float(line.partition('#'+BPMCHANGE)[2][1:].strip())
        cmd = (BPMCHANGE, bpm)
    elif ("#"+MEASURE) in line:
        arg_str = line.partition('#'+MEASURE)[2][1:].strip()
        arg1, arg2 = arg_str.split('/')
        cmd = (MEASURE, 4.0*float(arg1.strip()) / float(arg2.strip()))
    elif ("#"+SCROLL) in line:
        arg_str = line.partition('#'+SCROLL)[2][1:].strip()
        cmd = (SCROLL, float(arg_str))        
    elif ("#"+GOGOSTART) in line:
        cmd = (GOGOSTART,)
    elif ("#"+GOGOEND) in line:
        cmd = (GOGOEND,)
    elif ("#"+BARLINEOFF) in line:
        cmd = (BARLINEOFF,)
    elif ("#"+BARLINEON) in line:
        cmd = (BARLINEON,)
    elif ("#"+DELAY) in line:
        arg_str = line.partition('#'+DELAY)[2][1:].strip()
        cmd = (DELAY, float(arg_str))
    else:
        return

    if bar_data == []:
        real_do_cmd(cmd)
    else:
        bar_data.append(cmd)

def real_do_cmd(cmd):
    global curr_time

#    print_with_pended("handle cmd", cmd, file=sys.stderr)
    
    # handle delay, no timing point change
    if cmd[0] == DELAY:
        curr_time += cmd[1] * 1000
        return
    
    # handel timing point change command    
    if cmd[0] == BPMCHANGE:
        get_or_create_curr_red_tm()["bpm"] = cmd[1]
    elif cmd[0] == MEASURE:
        assert len(bar_data) == 0, "can't change measure within a bar"
        get_or_create_curr_red_tm()["measure"] = cmd[1]
    elif cmd[0] == SCROLL:
        get_or_create_curr_tm()["scroll"] = cmd[1]
    elif cmd[0] == GOGOSTART:
        get_or_create_curr_tm()["GGT"] = True
    elif cmd[0] == GOGOEND:
        get_or_create_curr_tm()["GGT"] = False
    elif cmd[0] == BARLINEOFF:
        get_or_create_curr_tm()["hidefirst"] = True
    elif cmd[0] == BARLINEON:
        get_or_create_curr_tm()["hidefirst"] = False
    else:
        assert False, "unknown or unsupported command"

def add_a_note(snd, offset):
    global lasting_note
    snd = int(snd)
    HitObjects.append((get_osu_type(snd), get_osu_sound(snd), offset))
    if get_osu_type(snd) in (SLIDER, SPINNER):
        lasting_note = get_osu_type(snd)
    if get_osu_type(snd) in (SLIDER_END, SPINNER_END):
        lasting_note = None
#    print_with_pended(HitObjects[-1], file=sys.stderr)

def get_last_tm():
    return TimingPoints[-1]

def get_last_red_tm():
    return TimingPointsRed[-1]
        
def get_tm_at(t):
    assert len(TimingPoints) > 0, "Need at least one timing point"
    return TimingPoints[max(0, bisect_right(TimingPoints, t, key=lambda tm: tm["offset"]) - 1)]

def get_red_tm_at(t):
    assert len(TimingPointsRed) > 0, "Need at least one uninherited timing point"
    return TimingPointsRed[max(0, bisect_right(TimingPointsRed, int(t), key=lambda tm: tm["offset"]) - 1)]
   
def create_new_tm(has_red: bool = False):
    global curr_time

    last_tm = get_last_tm()
    last_red_tm = get_last_red_tm()
    
    tm = {}
    tm["offset"] = int(curr_time)
#    print_with_pended("GREATE NEW TM", tm["offset"], file=sys.stderr)
    tm["redline"] = has_red # can upgrade to red + green later if not having red
    tm["scroll"] = last_tm and last_tm["scroll"] or 1.0
    tm["measure"] = last_tm["measure"]
    tm["GGT"] = last_tm["GGT"]
    tm["hidefirst"] = last_tm["hidefirst"]
    tm["bpm"] = last_red_tm["bpm"]
    
    TimingPoints.append(tm)
    if has_red:
        TimingPointsRed.append(tm)
        curr_time = int(tm["offset"])

    return tm

def get_or_create_curr_tm(need_red: bool = False):
    global curr_time
    tm = get_last_tm()
    if int(curr_time) != tm["offset"]:
        tm = create_new_tm(need_red)
    elif need_red and not tm["redline"]: # needs to upgrade to red + green
        tm["redline"] = True
        TimingPointsRed.append(tm)
        curr_time = int(tm["offset"])
    return tm

def get_or_create_curr_red_tm():
    return get_or_create_curr_tm(True)

def get_t_unit(tm, tot_note):
    #print_with_pended(tm["bpm"], tot_note, file=sys.stderr)
    return tm["measure"] * 60000.0 / (tm["bpm"] * tot_note)

def handle_a_bar():
    global bar_data, curr_time
    
    #debug
    global last_debug
    if last_debug is None:
        last_debug = TimingPoints[0]["offset"]
    #debug

    tot_note = 0
    for data in bar_data:
        if isinstance(data, str):
            tot_note += 1
    #print_with_pended("TOT_NOTE", tot_note, file=sys.stderr)
    
    if False and debug_mode:
        pure_data = filter(lambda x:x[0].isdigit(), bar_data)
        p1= "%6d %2.1f %2d %s" % (int(curr_time), \
                get_last_red_tm()["measure"], len(pure_data), \
                "".join(pure_data))

        p2= "%.4f %.2f" % (get_last_red_tm()["bpm"], \
                get_t_unit(get_last_red_tm(), tot_note) * tot_note)
        print_with_pended(p1, file=sys.stderr)

    #debug
    last_debug = curr_time
    print_each_note = False #(int(curr_time) == 112814)
    bak_curr_time = curr_time
    note_cnt = -1
    #debug
    
    if not tot_note: # empty or command-only measure
        curr_time += get_t_unit(get_last_red_tm(), 1)
    else:
        for data in bar_data:
            if isinstance(data, str): #note
                note_cnt += 1
                if data == "0" or \
                    (lasting_note != None and data != '8'):
                    curr_time += get_t_unit(get_last_red_tm(), tot_note)
                    continue
                add_a_note(data, curr_time)
                if print_each_note:
                    print_with_pended(note_cnt, data, curr_time, bak_curr_time + note_cnt * get_t_unit(get_last_red_tm(), tot_note), get_t_unit(get_last_red_tm(), tot_note), file=sys.stderr)
                curr_time += get_t_unit(get_last_red_tm(), tot_note)           
            else: #cmd
                real_do_cmd(data)
    bar_data = [] 
    
    if print_each_note:
        print_with_pended("after bar, curr_time= %f", curr_time, file=sys.stderr)
    # handle bar line visibility
    tmr = get_last_red_tm()
    tm = get_last_tm()
    if tm["hidefirst"]: # still hidden
        real_do_cmd((MEASURE, tmr["measure"])) # insert bar line
        real_do_cmd((BARLINEOFF,)) # hide bar line
    elif tmr["hidefirst"]: # no longer hidden
        real_do_cmd((MEASURE, tmr["measure"])) # insert bar line
        real_do_cmd((BARLINEON,)) # unhide bar line
    # convert x.x measure to incomplete measure
    if abs(round(tmr["measure"]) - tmr["measure"]) > 0.001:
        bak = tmr["measure"]
        tmr["measure"] = math.ceil(round(bak, 3)) # a big enough measure for osu
        real_do_cmd((MEASURE, bak)) # remeasure, for tja

def handle_note(line):
    global bar_data
    for ch in line:
        if ch.isdigit():
            bar_data.append(ch)
        elif ch == ",":
            handle_a_bar()

def write_fmt_ver_str(fout: TextIO) -> None:
    print("osu file format v14", file=fout)
    print("", file=fout)

def write_General(fout: TextIO) -> None:
    global Title, Source, AudioFilename, PreviewTime
    Title = TITLE
    Source = SUBTITLE
    if WAVE:
        AudioFilename = WAVE
        chart_resources.append(('song audio', WAVE))
    else:
        AudioFilename = ""
    PreviewTime = DEMOSTART * 1000

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

def write_Metadata(fout: TextIO) -> None:
    global Title, Source, Creator, AudioFilename, PreviewTime, Version
    Title = TITLE
    Source = SUBTITLE    
    Creator = MAKER or AUTHOR or CREATOR or Creator
    Version = COURSE
    print("[Metadata]", file=fout)
    print("Title:%s" % (Title,), file=fout)
    print("Artist:%s" % (Artist,), file=fout)
    print("Creator:%s" % (Creator,), file=fout)
    print("Version:%s" % (Version,), file=fout)
    print("Source:%s" % (Source,), file=fout)
    print("Tags:%s" % (Tags,), file=fout)
    print("", file=fout)

def write_Difficulty(fout: TextIO) -> None:
    print("[Difficulty]", file=fout)
    print("HPDrainRate:%s" % (repr(HPDrainRate),), file=fout)
    print("CircleSize:%s" % (repr(CircleSize),), file=fout)
    print("OverallDifficulty:%s" % (repr(OverallDifficulty),), file=fout)
    print("ApproachRate:%s" % (repr(ApproachRate),), file=fout)
    print("SliderMultiplier:%s" % (repr(SliderMultiplier),), file=fout)
    print("SliderTickRate:%s" % (repr(SliderTickRate),), file=fout)
    print("", file=fout)

def write_TimingPoints(fout: TextIO) -> None:
    print("[TimingPoints]", file=fout)
    volume = int(round(min(100, 100 * abs(SEVOL) / max(1, abs(SONGVOL)))))
    for tm in TimingPoints:
        time = int(tm["offset"])
        meter = max(1, int(round(tm["measure"])))
        fx = tm["GGT"] + 8 * tm["hidefirst"]
        if tm["redline"]:
            beat_dur = 60000.0 / tm["bpm"]
            print(f"{time},{beat_dur},{meter},1,0,{volume},1,{fx}", file=fout)
        if not tm["redline"] or tm["scroll"] != 1.0:
            beat_dur = -100 / tm["scroll"]
            print(f"{time},{beat_dur},{meter},1,0,{volume},0,{fx}", file=fout)
        tm["offset"] = int(tm["offset"])
    print("", file=fout)

def write_HitObjects(fout: TextIO) -> None:
    print("[HitObjects]", file=fout)
    lasting_note = None
    for ho in HitObjects:
        beg_offset = get_real_offset(ho[2])
        if int(beg_offset) != int(ho[2]):
#            print_with_pended("OFFSET FIXED", int(beg_offset), int(ho[2]), file=sys.stderr)
            pass
        if ho[0] == CIRCLE:
            rtassert(lasting_note is None, "this is abnormal")
            print("%d,%d,%d,%d,%d" % (CircleX, CircleY, beg_offset, ho[0], ho[1]),
                file=fout)
        elif ho[0] == SLIDER:
            rtassert(lasting_note is None, "this is abnormal")
            lasting_note = ho
        elif ho[0] == SPINNER:
            rtassert(lasting_note is None, "this is abnormal")
            lasting_note = ho
        elif ho[0] == SLIDER_END:
            rtassert(lasting_note is not None and \
                    lasting_note[0] == SLIDER)
            ln = lasting_note
            tmr = get_red_tm_at(int(ln[2]))
            tmg = get_tm_at(int(ln[2])) # green if red + green, otherwise red
            curve_len = 100 * (ho[2] - ln[2]) * tmr["bpm"]  * SliderMultiplier * tmg["scroll"] / 60000
            print("%d,%d,%d,%d,%d,L|%d:%d,%d,%f" % (CircleX, CircleY, \
                    int(get_real_offset(ln[2])), ln[0], ln[1], \
                    int(CircleX+curve_len), CircleY, 1, curve_len),
                file=fout)
            lasting_note = None
        elif ho[0] == SPINNER_END:
            rtassert(lasting_note is not None and \
                    lasting_note[0] == SPINNER, "this is abnormal")
            ln = lasting_note
            print("%d,%d,%d,%d,%d,%d" % (CircleX, CircleY, int(get_real_offset(ln[2])), \
                    ln[0], ln[1], int(get_real_offset(ho[2]))),
                file=fout)
            lasting_note = None
    print("", file=fout)

def tja2osu(filename: str, fout: TextIO) -> List[Tuple[str, str]]:
    reset_global_variables()
    assert isinstance(filename, str)
    rtassert(filename.endswith(".tja"), "filename should ends with .tja")
    check_unsupported(filename)

    # real work
    get_meta_data(filename)
    write_fmt_ver_str(fout)
    write_General(fout)
    write_Editor(fout)
    write_Metadata(fout)
    write_Difficulty(fout)
    get_all(filename)
    if not debug_mode:
        write_TimingPoints(fout)
        write_HitObjects(fout)
    return chart_resources


def rtassert(b, str=""):
    if not b:
        print_with_pended(str, file=sys.stderr)
        exit()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Convert a single-notechart branch-less .tja file to .osu format and print the result.',
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("filename",
        help="source .tja file. Allows only 1 notechart definition (`#START` to `#END`) and no branch commands.")
    parser.add_argument("options", nargs="*", choices=["debug", []], metavar="{debug}",
        help="extra options (deprecated usage). Can also be specified as --<option> ")
    parser.add_argument("-d", "--debug", action="store_true",
        help="display extra info")
    args = parser.parse_args()
    debug_mode = args.debug or ("debug" in args.options)
    tja2osu(args.filename, sys.stdout)

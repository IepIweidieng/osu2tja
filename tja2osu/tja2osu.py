# $Id$
import codecs
import math
import sys
import copy
from typing import Optional, OrderedDict, Tuple

# jiro data
ENCODING = None
TITLE = "NO TITLE"
SUBTITLE = "NO SUBTITLE"
BPM = 0.0
WAVE = "NO WAVE FILE"
OFFSET = 0.0
DEMOSTART = 0.0
SONGVOL = 100.0
SEVOL = 100.0
COURSE = "Oni"

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
HitObjects = []
HPDrainRate = 7
CircleSize = 5
OverallDifficulty = 8.333
ApproachRate = 5
SliderMultiplier = 1.47
SliderTickRate = 4
CircleX = 256
CircleY = 192

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
    global ENCODING, TITLE, SUBTITLE, WAVE, OFFSET, DEMOSTART, SONGVOL, SEVOL, COURSE, BPM
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
        elif vname == b"SONGVOL": SONGVOL = float(vval)
        elif vname == b"SEVOL": SEVOL = float(vval)
        elif vname == b"COURSE": COURSE = convert_str(vval, ENCODING)

def add_default_timing_point():
    global TimingPoints
    tm = {}
    tm["offset"] = -OFFSET * 1000.0
    tm["redline"] = True
    tm["scroll"] = 1.0
    tm["measure"] = 4.0
    tm["GGT"] = False
    tm["hidefirst"] = False
    tm["bpm"] = BPM

    TimingPoints.append(tm)

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


has_started = False 
curr_time = 0.0
bar_data = []
lasting_note = None

def get_all(filename):
    global has_started, curr_time
    try: fobj = open(filename, "rb")
    except IOError: rtassert(False, "can't open tja file.")
    if fobj.peek(len(codecs.BOM_UTF8)).startswith(codecs.BOM_UTF8):
        fobj.seek(len(codecs.BOM_UTF8)) # ignore UTF-8 BOM

    has_started = False
    curr_time = -OFFSET * 1000
    add_default_timing_point()
    for line in fobj:
        line = line.decode("latin-1").strip()
        line = rm_jiro_comment(line)
        if not has_started and ("#"+START) in line:
            has_started = True
            continue
        if not has_started: continue
        if ("#"+END) in line:
            # prevent bar lines at and after #END
            tm = get_last_red_tm()
            real_do_cmd((MEASURE, max(tm["measure"], math.ceil(tm["bpm"])))) # insert a >= 1 minute measure
            real_do_cmd((BARLINEOFF,)) # hide its bar line
            break
        if ("#" in line): handle_cmd(line)
        else: handle_note(line)

def get_real_offset(int_offset):
#    print("INTOffset", int_offset, file=sys.stderr)
    tm = get_red_tm_at(int_offset)
    tpb = 60000 / tm["bpm"]
    int_delta = abs(int_offset - tm["offset"])
    sign = (int_offset - tm["offset"] > 0 and 1 or -1)

    t_unit_cnt = round(int_delta * tm["bpm"] * 24 / 60000)

    beat_cnt = t_unit_cnt / 24
    ret = tm["offset"] + beat_cnt * 60000 * sign / tm["bpm"]
    
    if int(ret) in ():
        print(tm, file=sys.stderr)
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

#    print("handle cmd", cmd, file=sys.stderr)
    
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
#    print(HitObjects[-1], file=sys.stderr)

def get_last_tm():
    return TimingPoints[-1]

def get_last_red_tm():
    for i in range(len(TimingPoints)-1, -1, -1):
        if TimingPoints[i]["redline"]:
            return TimingPoints[i]
    assert False
        
def get_tm_at(t):
    assert len(TimingPoints) > 0, "Need at least one timing point"
    if int(t) < TimingPoints[0]["offset"]:
        return TimingPoints[0]
    ret_tm = TimingPoints[0]
    for tm in TimingPoints:
        if tm["offset"] > t:
            break
        ret_tm = tm
    return ret_tm

def get_red_tm_at(t):
    assert len(TimingPoints) > 0
    assert TimingPoints[0]["redline"]
    if int(t) < TimingPoints[0]["offset"]:
        return TimingPoints[0]
    ret_tm = TimingPoints[0]
    for tm in TimingPoints:
        if tm["offset"] > int(t):
            break
        if tm["redline"]:
            ret_tm = tm
    return ret_tm
   
def create_new_tm():
    last_tm = get_last_tm()
    last_red_tm = get_last_red_tm()
    
    tm = {}
    tm["offset"] = int(curr_time)
#    print("GREATE NEW TM", tm["offset"], file=sys.stderr)
    tm["redline"] = False # can upgrade to red + green later
    tm["scroll"] = last_tm and last_tm["scroll"] or 1.0
    tm["measure"] = last_tm["measure"]
    tm["GGT"] = last_tm["GGT"]
    tm["hidefirst"] = last_tm["hidefirst"]
    tm["bpm"] = last_red_tm["bpm"]
    
    return tm

def get_or_create_curr_tm():
    tm = get_last_tm()
    if int(curr_time) != tm["offset"]:
        tm = create_new_tm()
        TimingPoints.append(tm)
    return tm

def get_or_create_curr_red_tm():
    global curr_time
    tm = get_or_create_curr_tm()
    curr_time = int(tm["offset"])
    tm["redline"] = True
    return tm

def get_t_unit(tm, tot_note):
    #print(tm["bpm"], tot_note, file=sys.stderr)
    return tm["measure"] * 60000.0 / (tm["bpm"] * tot_note)

debug_mode = False
last_debug = None
def handle_a_bar():
    global bar_data, curr_time
    
    #debug
    global last_debug
    if last_debug is None:
        last_debug = -OFFSET * 1000
    #debug

    tot_note = 0
    for data in bar_data:
        if isinstance(data, str):
            tot_note += 1
    #print("TOT_NOTE", tot_note, file=sys.stderr)
    
    if False and debug_mode:
        pure_data = filter(lambda x:x[0].isdigit(), bar_data)
        p1= "%6d %2.1f %2d %s" % (int(curr_time), \
                get_last_red_tm()["measure"], len(pure_data), \
                "".join(pure_data))

        p2= "%.4f %.2f" % (get_last_red_tm()["bpm"], \
                get_t_unit(get_last_red_tm(), tot_note) * tot_note)
        print(p1, file=sys.stderr)

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
                    print(note_cnt, data, curr_time, bak_curr_time + note_cnt * get_t_unit(get_last_red_tm(), tot_note), get_t_unit(get_last_red_tm(), tot_note), file=sys.stderr)
                curr_time += get_t_unit(get_last_red_tm(), tot_note)           
            else: #cmd
                real_do_cmd(data)
    bar_data = [] 
    
    if print_each_note:
        print("after bar, curr_time= %f", curr_time, file=sys.stderr)
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
        tmr["measure"] = max(1, math.ceil(round(bak, 3))) # a big enough measure for osu
        real_do_cmd((MEASURE, bak)) # remeasure, for tja

def handle_note(line):
    global bar_data
    for ch in line:
        if ch.isdigit():
            bar_data.append(ch)
        elif ch == ",":
            handle_a_bar()

def write_fmt_ver_str():
    print("osu file format v14")
    print("")

def write_General():
    global Title, Source, AudioFilename, PreviewTime
    Title = TITLE
    Source = SUBTITLE
    AudioFilename = WAVE
    PreviewTime = DEMOSTART * 1000

    print("[General]")
    print("AudioFilename: %s" % (AudioFilename,))
    print("AudioLeadIn: %d" % (round(AudioLeadIn)),)
    print("PreviewTime: %d" % (round(PreviewTime)),)
    print("CountDown: %d" % (CountDown,))
    print("SampleSet: %s" % (SampleSet,))
    print("StackLeniency: %s" % (repr(StackLeniency),))
    print("Mode: %d" % (Mode,))
    print("LetterboxInBreaks: %d" % (LetterboxInBreaks,))
    print("")

# no use, but required by osu
def write_Editor():
    print("[Editor]")
    print("DistanceSpacing: 0.8")
    print("BeatDivisor: 4")
    print("GridSize: 4")
    print("")

def write_Metadata():
    global Title, Source, AudioFilename, PreviewTime, Version
    Title = TITLE
    Source = SUBTITLE    
    Version = COURSE
    print("[Metadata]")
    print("Title:%s" % (Title,))
    print("Artist:%s" % (Artist,))
    print("Creator:%s" % (Creator,))
    print("Version:%s" % (Version,))
    print("Source:%s" % (Source,))
    print("Tags:%s" % (Tags,))
    print("")

def write_Difficulty():
    print("[Difficulty]")
    print("HPDrainRate:%s" % (repr(HPDrainRate),))
    print("CircleSize:%s" % (repr(CircleSize),))
    print("OverallDifficulty:%s" % (repr(OverallDifficulty),))
    print("ApproachRate:%s" % (repr(ApproachRate),))
    print("SliderMultiplier:%s" % (repr(SliderMultiplier),))
    print("SliderTickRate:%s" % (repr(SliderTickRate),))
    print("")

def write_TimingPoints():
    print("[TimingPoints]")
    volume = int(round(min(100, 100 * abs(SEVOL) / max(1, abs(SONGVOL)))))
    for tm in TimingPoints:
        time = int(tm["offset"])
        meter = int(round(tm["measure"]))
        fx = tm["GGT"] + 8 * tm["hidefirst"]
        if tm["redline"]:
            beat_dur = 60000.0 / tm["bpm"]
            print(f"{time},{beat_dur},{meter},1,0,{volume},1,{fx}")
        if not tm["redline"] or tm["scroll"] != 1.0:
            beat_dur = -100 / tm["scroll"]
            print(f"{time},{beat_dur},{meter},1,0,{volume},0,{fx}")
        tm["offset"] = int(tm["offset"])
    print("")

def write_HitObjects():
    print("[HitObjects]")
    lasting_note = None
    for ho in HitObjects:
        beg_offset = get_real_offset(ho[2])
        if int(beg_offset) != int(ho[2]):
#            print("OFFSET FIXED", int(beg_offset), int(ho[2]), file=sys.stderr)
            pass
        if ho[0] == CIRCLE:
            rtassert(lasting_note is None, "this is abnormal")
            print("%d,%d,%d,%d,%d" % (CircleX, CircleY, beg_offset, ho[0],
                    ho[1]))
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
                    int(CircleX+curve_len), CircleY, 1, curve_len))
            lasting_note = None
        elif ho[0] == SPINNER_END:
            rtassert(lasting_note is not None and \
                    lasting_note[0] == SPINNER, "this is abnormal")
            ln = lasting_note
            print("%d,%d,%d,%d,%d,%d" % (CircleX, CircleY, int(get_real_offset(ln[2])), \
                    ln[0], ln[1], int(get_real_offset(ho[2]))))
            lasting_note = None
    print("")

def tja2osu(filename):
    assert isinstance(filename, str)
    rtassert(filename.endswith(".tja"), "filename should ends with .tja")
    check_unsupported(filename)

    # real work
    get_meta_data(filename)
    write_fmt_ver_str()
    write_General()
    write_Editor()
    write_Metadata()
    write_Difficulty()
    get_all(filename)
    if not debug_mode:
        write_TimingPoints()
        write_HitObjects()


def rtassert(b, str=""):
    if not b:
        print(str, file=sys.stderr)
        exit()

def get_help_str():
    return "HELP STRING"

if __name__ == "__main__":
    rtassert(len(sys.argv) >= 2, "need a filename\n" +get_help_str())
    debug_mode = (len(sys.argv) >= 3 and ("debug" in sys.argv))
    tja2osu(sys.argv[1])

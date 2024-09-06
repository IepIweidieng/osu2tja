# -*- coding: utf-8 -*-
from functools import reduce
import sys
import optparse
import copy
import codecs
import os
import math

OSU_VER_STR_PREFIX = "osu file format v"

OSU_VER_MIN = 8
OSU_VER_MAX = 14
OSU_VER_SUPPORT = range(OSU_VER_MIN, OSU_VER_MAX + 1)

WATER_MARK = "//Auto generated by osu2tja"
T_MINUTE = 60000

# osu note type consts
OSU_NOTE_NC = 4
OSU_NOTE_CIRCLE = 1
OSU_NOTE_SLIDER = 2
OSU_NOTE_SPINNER = 8

# osu hitsound consts
HITSND_NORMAL = 0
HITSND_CLAP = 8
HITSND_WHISTLE = 2
HITSND_FINISH = 4

# tja onp consts
ONP_NONE = '0'
ONP_DON = '1'
ONP_KATSU = '2'
ONP_DON_DAI = '3'
ONP_KATSU_DAI = '4'
ONP_RENDA = '5'
ONP_RENDA_DAI = '6'
ONP_BALLOON = '7'
ONP_END = '8'
ONP_IMO = '9'

# tja command format string
FMT_SCROLLCHANGE = '#SCROLL %f'
FMT_BPMCHANGE = '#BPMCHANGE %f'
FMT_GOGOSTART = '#GOGOSTART'
FMT_GOGOEND = '#GOGOEND'
FMT_MEASURECHANGE = '#MEASURE %d/%d'
FMT_DELAY = '#DELAY %f'

# ----------------------
# utilities
# ----------------------


def make_cmd(cmd, *args):
    return cmd % args


def gcd(a, b):
    if a % b != 0:
        return gcd(b, a % b)
    return b


def gcd_of_list(l):
    return reduce(gcd, l)

# convert time for print


def format_time(t):
    return t//T_MINUTE*100000+t % T_MINUTE


def get_base_timing_point(timing_points, t):
    assert len(timing_points) > 0, "Need at least one timing point"
    # A note can appear even the first timing point
    if int(t) < timing_points[0]["offset"]:
        return copy.copy(timingpoints[0])

    base = timing_points[0]
    for timing_point in timing_points:
        if timing_point["offset"] > t:
            break
        base = timing_point
    return copy.copy(base)


def get_base_red_timing_point(timing_points, t):
    red_timing_points = [d for d in timing_points if d["redline"] == True]
    return get_base_timing_point(red_timing_points, t)

# ----------------------
# parse single line
# ----------------------


def get_section_name(str):
    if str is None:
        return ""
    if str.startswith('[') and str.endswith(']'):
        return str[1:-1]
    return ""


def get_var(str):
    if str is None:
        return "", ""
    try:
        idx = str.index(':')
        var_name = str[:idx].strip()
        var_value = str[idx+1:].strip()
    except:
        return "", ""
    return var_name, var_value


def get_timing_point(str, prev_timing_point=None):
    if str is None:
        return {}

    # in case new items are added to osu format
    ps = str.split(',')
    if len(ps) < 8:
        return {}

    offset, rawbpmv, beats, _, _, _, _, is_ggt = ps[:8]
    is_ggt = (is_ggt != '0')

    # fill a timing point dict
    ret = {}
    try:
        ret["offset"] = int(offset)  # time
        if float(rawbpmv) > 0:	   # BPM change or SCROLL speed change
            bpm = ret["bpm"] = 60 * 1000.0 / float(rawbpmv)
            ret["scroll"] = 1.0
            ret["redline"] = True
        elif float(rawbpmv) < 0:
            ret["bpm"] = prev_timing_point.get("bpm", None)
            ret["scroll"] = -100.0 / float(rawbpmv)
            ret["redline"] = False
            ret["offset"] = get_real_offset(ret["offset"])
        else:
            assert False
        ret["beats"] = int(beats)  # measure change
        ret["GGT"] = is_ggt

    except:
        print("Osu file Error, at [TimingPoints] section, please check", file=sys.stderr)
        return {}

    return ret


# global variables
timingpoints = []
balloons = []
slider_velocity = None
tail_fix = False
taiko_mode = False
osu_format_ver = 0
commands_within = []

# debug args
show_head_info = False
ignore_format_ver = False
combo_cnt = 0
guess_measure = False


def reset_global_variables():
    global timingpoints, balloons, slider_velocity, tail_fix, taiko_mode, osu_format_ver, commands_within
    global show_head_info, ignore_format_ver, combo_cnt, guess_measure
    timingpoints = []
    balloons = []
    slider_velocity = None
    tail_fix = False
    taiko_mode = False
    osu_format_ver = 0
    commands_within = []

    # debug args
    show_head_info = False
    ignore_format_ver = False
    combo_cnt = 0
    guess_measure = False


# get fixed beat count
def get_real_beat_cnt(tm, beat_cnt):
    return round(beat_cnt * 24, 2) / 24

# get fixed offset base by the nearest base timing point
# step 1: find the base timing point around t
# step 2: calculate the fixed beat count from t to the base timing point
# step 3: get fixed offset from fixed beat count and bpm


def get_real_offset(int_offset):
    int_offset = int(int_offset)

    tm = get_base_red_timing_point(timingpoints, int_offset)
    tpb = 1.0 * T_MINUTE / tm["bpm"]
    int_delta = abs(int_offset - tm["offset"])
    sign = (int_offset - tm["offset"] > 0 and 1 or -1)

    t_unit_cnt = round(int_delta * tm["bpm"] * 24 / T_MINUTE)

    beat_cnt = t_unit_cnt / 24

    ret = tm["offset"] + beat_cnt * T_MINUTE * sign / tm["bpm"]

    return ret


def get_slider_time(l, tm):
    global slider_velocity
    tpb = 60.0 * 1000 / tm["bpm"]
    sv = slider_velocity
    scroll = tm["scroll"]
    return 1.0 * l * tpb / (100 * sv * scroll)


def get_slider_beat_cnt(l, tm):
    global slider_velocity
    tpb = 60.0 * 1000 / tm["bpm"]
    sv = slider_velocity
    scroll = tm["scroll"]
    return get_real_beat_cnt(tm, 1.0 * l / (100 * sv * scroll))


def get_slider_sound(str):
    ret = []
    ps = str.split(',')
    reverse_cnt = int(ps[6])
    if len(ps) == 8:
        return [int(ps[4])] * (reverse_cnt + 1)
    else:
        return [int(x) for x in ps[8].split('|')]


def get_donkatsu_by_sound(sound):
    if sound == HITSND_NORMAL:
        return ONP_DON
    elif sound in (HITSND_CLAP, HITSND_WHISTLE, HITSND_CLAP | HITSND_WHISTLE):
        return ONP_KATSU
    elif sound == HITSND_FINISH:
        return ONP_DON_DAI
    elif sound in (HITSND_FINISH | HITSND_CLAP,
                   HITSND_FINISH | HITSND_WHISTLE,
                   HITSND_FINISH | HITSND_CLAP | HITSND_WHISTLE):
        return ONP_KATSU_DAI
    else:
        assert False, "don't know what note"


slider_combo_cnt_240 = 0
slider_combo_cnt_less = 0


def get_note(str):
    global timing_point
    global taiko_mode
    ret = []

    if str is None:
        return ret
    ps = str.split(',')
    if len(ps) < 5:
        return ret

    type = int(ps[3])
    sound = int(ps[4])
    offset = get_real_offset(int(ps[2]))

    type &= (~OSU_NOTE_NC)  # remove new combo flag

    if type == OSU_NOTE_CIRCLE:  # circle
        ret.append((get_donkatsu_by_sound(sound), offset))
    elif type == OSU_NOTE_SLIDER:  # slider, reverse??

        global slider_combo_cnt_240, slider_combo_cnt_less
        if int(float(ps[7])) * int(ps[6]) >= 480:
            slider_combo_cnt_240 += int(ps[6]) + 1
        else:
            slider_combo_cnt_less += int(ps[6]) + 1

        curve_len = float(ps[7])
        reverse_cnt = int(ps[6])
        total_len = curve_len * reverse_cnt
        tm = get_base_timing_point(timingpoints, offset)
        tpb = 1.0 * T_MINUTE / tm["bpm"]

        beat_cnt = get_slider_beat_cnt(curve_len, tm)

        t_noreverse = get_slider_time(curve_len, tm)

        assert reverse_cnt + 1 == len(get_slider_sound(str))
        if (taiko_mode and beat_cnt < 1.0) or \
                (not taiko_mode and beat_cnt * reverse_cnt < 2.0):
            for i, snd in enumerate((get_slider_sound(str))):
                point_offset = offset + get_slider_time(curve_len * i, tm)
                point_offset = get_real_offset(int(point_offset))
                ret.append((get_donkatsu_by_sound(snd), point_offset))
        else:
            if sound == 0:
                ret.append((ONP_RENDA, offset))
            else:
                ret.append((ONP_RENDA_DAI, offset))
            ret.append((ONP_END, offset + t_noreverse * reverse_cnt))

    elif type == OSU_NOTE_SPINNER:  # spinner
        ret.append((ONP_BALLOON, offset))
        ret.append((ONP_END, get_real_offset(int(ps[5]))))
        # how many hit will break a ballon
        # TODO: according to length of the spinner
        global balloons
        balloons.append(int((ret[-1][1]-ret[-2][1])/122))

    return ret


# BEAT - MEASURE TABLE
measure_table = (
    (0.25, "1/16"),
    (1, "1/4"),
    (1.25, "5/16"),
    (1.5, "3/8"),
    (2, "2/4"),
    (2.25, "9/16"),
    (2.5, "5/8"),
    (3, "3/4"),
    (3.75, "15/16"),
    (4, "4/4"),
    (4.5, "9/8"),
    (5, "5/4"),
    (6, "6/4"),
    (7, "7/4"),
    (8, "8/4"),
    (9, "9/4"),
)

# handle an incomplete bar
# if the bar is empty(contains no notes), use #DELAY command
# if the bar is not empty, use #MEASURE to write a bar, and # DELAY to consume
# 	the remaining time.


def write_incomplete_bar(tm, bar_data, begin, end, tja_contents):

    if len(bar_data) == 0 and int(begin) == int(end):
        return

    if len(bar_data) == 0:  # use DELAY to skip an empty bar
        tja_contents.append(make_cmd(FMT_DELAY, (end-begin) / 1000.0))
        return

    tpb = T_MINUTE / tm["bpm"]
    my_beat_cnt = 1.0 * (end - begin) * tm["bpm"] / T_MINUTE

    # this is accurate, +1/24 to avoid the last note to be divided to the next
    # bar
    min_beat_cnt = get_real_beat_cnt(
        tm, 1.0 * tm["bpm"] * (bar_data[-1][1]-begin) / T_MINUTE) + 1.0/24

    global guess_measure
    # force guess measure
    if not guess_measure:
        for beat_cnt, str in measure_table:
            if beat_cnt >= min_beat_cnt and \
                    int(begin + 1.0 * beat_cnt * T_MINUTE / tm["bpm"]) <= end:

                tja_contents.append("#MEASURE"+str)
                write_bar_data(tm, bar_data, begin, begin +
                               beat_cnt * tpb, tja_contents)
                delay_time = end - \
                    int(begin + 1.0 * beat_cnt * T_MINUTE / tm["bpm"])
                assert delay_time >= 0, "DELAY FAULT %f" % delay_time

                # jiro will ignore delays short than 0.001s
                # TODO: add up total epsilon!? and fix it later?
                if delay_time >= 1:
                    tja_contents.append(make_cmd(FMT_DELAY, delay_time/1000.0))
                return

    # Missing all, guess a measure here!
    denominator = 48*48
    numerator = int(round(denominator * min_beat_cnt))
    _gcd = gcd(denominator, numerator)
    denominator /= _gcd
    numerator /= _gcd

    if denominator in (1, 2):
        fix_mul = 4 / denominator
        denominator *= fix_mul
        numerator *= fix_mul

    tja_contents.append("//[Warning] This may be erronous!!")
    tja_contents.append(make_cmd(FMT_MEASURECHANGE, numerator, denominator))
    write_bar_data(tm, bar_data, begin, begin +
                   min_beat_cnt * tpb, tja_contents)
    delay_time = end - int(begin + 1.0 * min_beat_cnt * T_MINUTE / tm["bpm"])
    if delay_time >= 1:
        tja_contents.append(make_cmd(FMT_DELAY, delay_time / 1000.0))
    return


def write_bar_data(tm, bar_data, begin, end, tja_contents):
    global show_head_info
    global combo_cnt, tail_fix
    global commands_within

    t_unit = 60.0 * 1000 / tm["bpm"] / 24
    offset_list = [int(begin)] + [datum[1] for datum in bar_data] + [int(end)]
    # print offset_list
    delta_list = []
    for offset1, offset2 in zip(offset_list[:-1], offset_list[1:]):
        delta = (offset2-offset1)/t_unit
        t_unit_cnt = int(round(delta))
        delta_list.append(t_unit_cnt)

    if abs(delta_list[-1]) < 1:
        tail_fix = True
        write_bar_data(tm, bar_data[:-1], begin, end, tja_contents)
        return

    ret_str = ""

    # TODO: fix this!
    if len(bar_data) == 0:
        offset = begin
        # Insert commands!
        while commands_within and int(offset) >= int(commands_within[0][0]):

            ret_str += "\n"
            ret_str += make_cmd(*commands_within[0][1:])
            ret_str += "\n"

            commands_within = commands_within[1:]

    delta_gcd = gcd_of_list(delta_list)
    ret_str += "0"*int(delta_list[0]/delta_gcd)
    empty_t_unit = ["0"*int(x/delta_gcd-1) for x in delta_list[1:]]

    for empty_t_unit_cnt, (note, offset) in zip(empty_t_unit, bar_data):
        # Insert commands!
        while commands_within and int(offset) >= int(commands_within[0][0]):

            ret_str += "\n"
            ret_str += make_cmd(*commands_within[0][1:])
            ret_str += "\n"

            commands_within = commands_within[1:]
        ret_str += note + empty_t_unit_cnt

    head = "%4d %6d %.2f %2d " % (combo_cnt,
                                  format_time(int(begin)), delta_gcd/24.0, len(ret_str))

    if show_head_info:  # show debug info?
        ret_str = head + ret_str

    tja_contents.append(ret_str + ',')

    for note, offset in bar_data:
        if note in (ONP_DON, ONP_KATSU, ONP_DON_DAI, ONP_KATSU_DAI):
            combo_cnt += 1


def osu2tja(fp, course, level, audio_name):
    global slider_velocity, timingpoints
    global balloons, tail_fix, ignore_format_ver
    global osu_format_ver
    global commands_within
    global taiko_mode

    tja_heads = list()
    tja_contents = list()
    # check filename
    # if not filename.lower().endswith(".osu"):
    #    print("Input file should be Osu file!(*.osu): \n\t[[ %s ]]" % filename, file=sys.stderr)
    #    return False

    # try to open file
    # try:
    #    fp = codecs.open(filename, "r", "utf8")
    # except IOError:
    #    print("Can't open file `%s`" % filename, file=sys.stderr)
    #    return False

    # data structures to hold information
    audio = ""
    title = ""
    subtitle = ""
    creator = ""
    artist = ""
    version = ""
    preview = 0
    hitobjects = []

    # state vars
    osu_ver_str = ""
    curr_sec = ""
    # read data
    lines = fp.readlines()
    for line in lines:
        line = line.strip()
        if line == "":
            continue

        # check osu file format version
        if osu_ver_str == "":
            osu_ver_str = line
            osu_format_ver_pos = line.index(
                OSU_VER_STR_PREFIX) + len(OSU_VER_STR_PREFIX)
            osu_format_ver = int(osu_ver_str[osu_format_ver_pos:])
            if not ignore_format_ver:
                if osu_format_ver not in OSU_VER_SUPPORT:
                    print("Only support osu file format v%s at the moment. You may try option -i to force convert if you will." %
                          ("/".join([str(i) for i in OSU_VER_SUPPORT])), file=sys.stderr)
                    return False

        # new section? Update section name.
        new_sec = get_section_name(line)
        if new_sec:
            curr_sec = new_sec
            continue

        # varible? Parse variable
        vname, vval = get_var(line)

        # read in useful infomation in following sections
        if curr_sec == "General":
            if vname == "AudioFilename":
                root, ext = os.path.splitext(vval)
                if ext != ".ogg":
                    vval = root+".ogg"
                audio = vval
            elif vname == "PreviewTime":
                preview = int(vval)
            elif vname == "Mode":
                taiko_mode = (int(vval) == 1)

        elif curr_sec == "Metadata":
            if vname in ("Title", "TitleUnicode"):
                title = vval or title
            elif vname == "Creator":
                creator = vval
            elif vname == "Version":
                version = vval
            elif vname == "Source":
                subtitle = vval
            elif vname in ("Artist", "ArtistUnicode"):
                artist = vval or artist
        elif curr_sec == "Difficulty":
            if vname == "SliderMultiplier":
                slider_velocity = float(vval)
            elif vname == "OverallDifficulty":
                difficulty = math.floor(float(vval))
        elif curr_sec == "TimingPoints":
            prev_timing_point = timingpoints and timingpoints[-1] or None
            data = get_timing_point(line, prev_timing_point)
            if data:
                timingpoints.append(data)
        elif curr_sec == "HitObjects":
            data = get_note(line)
            if data:
                hitobjects.extend(data)

    assert len(hitobjects) > 0

    # check if there is note before first timing point
    if int(hitobjects[0][1]) < timingpoints[0]["offset"]:
        new_tm_first = dict(timingpoints[0])
        new_tm_first["offset"] = int(hitobjects[0][1])
        timingpoints = [new_tm_first] + timingpoints

    # collect all #SCROLL #GOGOSTART #GOGOEND commands
    # these commands will not be broken by #BPMCHANGE or # MEASURE
    cur_scroll = 1.0
    cur_ggt = False
    for tm in timingpoints:
        if tm["scroll"] != cur_scroll:
            commands_within.append(
                (tm["offset"], FMT_SCROLLCHANGE, tm["scroll"]))
        if tm["GGT"] != cur_ggt:
            commands_within.append((tm["offset"],
                                    tm["GGT"] and FMT_GOGOSTART or FMT_GOGOEND))
        cur_scroll = tm["scroll"]
        cur_ggt = tm["GGT"]

    BPM = timingpoints[0]["bpm"]
    OFFSET = timingpoints[0]["offset"] / 1000.0
    PREVIEW = preview

    scroll = timingpoints[0]["scroll"]
    tm_idx = 0  # current timing point index
    obj_idx = 0  # current hit object index
    chap_idx = 0  # current chapter index
    measure = timingpoints[0]["beats"]  # current measure
    curr_bpm = BPM  # current bpm
    jiro_data = []  # jiro fumen data

    bar_data = []  # current bar data
    last_tm = 0  # last hit object offset

    bar_offset_begin = timingpoints[0]["offset"]
    bar_max_length = 1.0 * measure * T_MINUTE / curr_bpm  # current bar length

    bar_cnt = 1
    tja_heads.append("TITLE:%s" % title)
    if subtitle != "" and artist != "":
        subtitle = f"{artist} ｢{subtitle}｣より"
    tja_heads.append("SUBTITLE:--%s" % (subtitle or artist))
    tja_heads.append("WAVE:%s" % audio_name)
    tja_heads.append("BPM:%.2f" % timingpoints[0]["bpm"])
    tja_heads.append("OFFSET:-%.3f" % (timingpoints[0]["offset"] / 1000.0))
    tja_heads.append("DEMOSTART:%.3f" % (preview / 1000.0))

    tja_contents.append("")
    if version in "Inner Oni":
        course = "Edit"
    else:
        course = "Oni"
    tja_contents.append(f"COURSE:{course}") # TODO: GUESS DIFFICULTY
    if difficulty != "":
        level = difficulty+4
    else:
        level = 9
    tja_contents.append(f"LEVEL:{level}")  # TODO: GUESS LEVEL

    # don't write score init and score diff
    # taiko jiro will calculate score automatically
    tja_contents.append("BALLOON:%s" % ','.join(map(repr, balloons)))

    tja_contents.append("")
    tja_contents.append("#START")

    def is_new_measure(timing_point):
        bpm = timing_point["bpm"]
        _measure = timing_point["beats"]
        return bpm != curr_bpm or measure != _measure or timing_point["redline"]

    # check if all notes align ok
    for ho1, ho2 in zip(hitobjects[:-1], hitobjects[1:]):
        if ho2[1] <= ho1[1]:
            tja_contents.append(ho1)

    while obj_idx < len(hitobjects):
        # get next object to process
        next_obj = hitobjects[obj_idx]
        next_obj_offset = int(next_obj[1])
        next_obj_type = next_obj[0]

        # get next measure offset to compare
        if tm_idx < len(timingpoints):
            next_measure_offset = timingpoints[tm_idx]["offset"]
        else:
            next_measure_offset = bar_offset_begin + bar_max_length + 1

        # skip volumn change and kiai
        if tm_idx < len(timingpoints) and \
                not is_new_measure(timingpoints[tm_idx]):
            tm_idx += 1
            continue

        tpb = T_MINUTE / curr_bpm
        # check if this object falls into this measure
        end = min(bar_offset_begin + bar_max_length, next_measure_offset)

        if next_obj_offset + tpb / 24 >= int(end):
            # write_a_measure()
            if int(end) == int(bar_offset_begin + bar_max_length):
                tm = get_base_timing_point(timingpoints, bar_offset_begin)
                write_bar_data(tm, bar_data, bar_offset_begin,
                               end, tja_contents)
                bar_data = []
                bar_cnt += 1
                bar_offset_begin = get_real_offset(end)
                bar_max_length = measure * time_per_beat
            elif int(end) == next_measure_offset:  # collect an incomplete bar?
                write_incomplete_bar(get_base_timing_point(timingpoints, bar_offset_begin),
                                     bar_data, bar_offset_begin, end, tja_contents)
                bar_data = []
                measure = timingpoints[tm_idx]["beats"]
                if timingpoints[tm_idx]["redline"]:
                    curr_bpm = timingpoints[tm_idx]["bpm"]
                    bar_offset_begin = next_measure_offset
                    tja_contents.append(make_cmd(FMT_BPMCHANGE, curr_bpm))
                else:
                    bar_offset_begin = end
                time_per_beat = (60 * 1000) / curr_bpm
                bar_max_length = measure * time_per_beat

                if tail_fix:
                    tail_fix = False
                    obj_idx -= 1
                    new_obj = (hitobjects[obj_idx][0], bar_offset_begin)
                    hitobjects[obj_idx] = new_obj

                # add new commands
                tja_contents.append(make_cmd(FMT_MEASURECHANGE, measure, 4))

                tm_idx += 1
            else:
                assert False, "BAR END POS ERROR"

        else:
            if next_obj[1] < bar_offset_begin:
                bar_data.append((next_obj[0], bar_offset_begin))
            else:
                bar_data.append(next_obj)
            obj_idx += 1

    # flush buffer
    if len(bar_data) > 0:
        write_bar_data(get_base_timing_point(timingpoints, bar_offset_begin),
                       bar_data, bar_offset_begin, end, tja_contents)

    tja_contents.append("#END")
    tja_contents.append(WATER_MARK)
    tja_contents.append(f"//created by {creator}")
    return tja_heads, tja_contents


if __name__ == "__main__":
    parser = optparse.OptionParser()
    parser.add_option("-i", "--ignore_version", action="store_const",
                      const=True, dest="ignore_version", default=False)
    parser.add_option("-d", "--debug", action="store_const",
                      const=True, dest="debug", default=False)
    parser.add_option("-g", "--guess", action="store_const",
                      const=True, dest="guess_measure", default=False)
    (options, args) = parser.parse_args()

    show_head_info = options.debug
    ignore_format_ver = options.ignore_version
    guess_measure = options.guess_measure
    osu2tja(args[0])

    if show_head_info:
        print(slider_combo_cnt_240, file=sys.stderr)
        print(slider_combo_cnt_less, file=sys.stderr)

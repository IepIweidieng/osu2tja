# -*- coding: utf-8 -*-

# sys.path hack
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from common.utils import print_with_pended

from array import array
from bisect import bisect_left, bisect_right
from functools import reduce
import itertools
import sys
import argparse
import copy
import codecs
from fractions import Fraction
import os
import math
from typing import IO, List, Optional, Tuple, Union

OSU_VER_STR_PREFIX = "osu file format v"

OSU_VER_MIN = 4
OSU_VER_MAX = 14
OSU_VER_SUPPORT = range(OSU_VER_MIN, OSU_VER_MAX + 1)

WATER_MARK = "//Auto generated by osu2tja"
T_MINUTE = 60000

# osu game mode consts
GAMEMODE_STD = 0
GAMEMODE_TAIKO = 1
GAMEMODE_CATCH = 2
GAMEMODE_MANIA = 3

GAMEMODE_TO_STR = {
    GAMEMODE_STD: "osu!std",
    GAMEMODE_TAIKO: "osu!taiko",
    GAMEMODE_CATCH: "osu!catch",
    GAMEMODE_MANIA: "osu!mania",
}

# osu note type consts
OSU_NOTE_CIRCLE = 1 << 0
OSU_NOTE_SLIDER = 1 << 1
OSU_NOTE_NC = 1 << 2
OSU_NOTE_SPINNER = 1 << 3
OSU_NOTE_HOLD = 1 << 7

# osu hitsound consts
HITSND_NORMAL = 1 << 0
HITSND_WHISTLE = 1 << 1
HITSND_FINISH = 1 << 2
HITSND_CLAP = 1 << 3

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


def gcd_of_list(l):
    return reduce(math.gcd, l)

# convert time for print


def format_time(t):
    return t//T_MINUTE*100000+t % T_MINUTE


def get_base_timing_point(timing_points, t):
    assert len(timing_points) > 0, "Need at least one timing point"
    # A note can appear even the first timing point
    if int(math.floor(t)) < timing_points[0]["offset"]:
        return copy.copy(timingpoints[0])

    idx_tm = bisect_right(timing_points, t, key=lambda tm: tm["offset"]) - 1
    return copy.copy(timing_points[idx_tm])


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


def get_var(str: str) -> Tuple[str, str]:
    if str is None:
        return "", ""
    var_name, _, var_value = str.partition(':')
    return var_name.strip(), var_value.strip()


def get_timing_point(str, prev_timing_point=None):
    if str is None:
        return {}

    # in case new items are added to osu format
    ps = str.split(',')
    if len(ps) < 7:
        return {}

    offset, rawbpmv, beats = ps[:3]
    is_ggt = (len(ps) > 7 and ps[7] != '0')

    # fill a timing point dict
    ret = {}
    try:
        ret["offset"] = float(offset)  # time
        ret["GGT"] = is_ggt
        if float(rawbpmv) > 0: # BPM change
            mspb = ret["mspb"] = float(rawbpmv)
            bpm = ret["bpm"] = 60 * 1000.0 / mspb
            ret["beats"] = int(beats) # measure change
            ret["scroll"] = 1.0
            ret["redline"] = True
        elif float(rawbpmv) < 0: # SCROLL speed change
            assert prev_timing_point is not None
            if (prev_timing_point["offset"] == ret["offset"]
                and prev_timing_point["redline"]
                and prev_timing_point["GGT"] == is_ggt
                ):
                ret = prev_timing_point # merge uninherited (red) + inherited (green) timing points
            else:
                ret["mspb"] = prev_timing_point.get("mspb", None)
                ret["bpm"] = prev_timing_point.get("bpm", None)
                ret["beats"] = prev_timing_point.get("beats", None) # ignored for inherited timing points
                ret["redline"] = False
                ret["offset"] = get_real_offset(ret["offset"])
            ret["scroll"] = -100.0 / float(rawbpmv)
        else:
            assert False

    except:
        print_with_pended("Osu file Error, at [TimingPoints] section, please check", file=sys.stderr)
        return {}

    return ret


def reset_global_variables() -> None:
    global timingpoints, balloons, slider_multiplier, slider_tick_rate, column_count, tail_fix, gamemode_idx, osu_format_ver, commands_within
    global show_head_info, combo_cnt, guess_measure
    # global variables
    timingpoints = []
    balloons = []
    slider_multiplier = None
    slider_tick_rate = None
    column_count = 1
    tail_fix = False
    gamemode_idx = GAMEMODE_STD
    osu_format_ver = 0
    commands_within = []

    # debug args
    show_head_info = False
    combo_cnt = 0
    guess_measure = False


# get fixed beat count
def get_real_beat_cnt(tm, beat_cnt):
    return round(beat_cnt * 24, 2) / 24

# get fixed offset base by the nearest base timing point
# step 1: find the base timing point around t
# step 2: calculate the fixed beat count from t to the base timing point
# step 3: get fixed offset from fixed beat count and bpm


def get_real_offset(int_offset: Union[int, float]) -> float:
    int_offset = int(math.floor(int_offset))

    tm = get_base_red_timing_point(timingpoints, int_offset)
    tpb = 1.0 * T_MINUTE / tm["bpm"]
    int_delta = abs(int_offset - tm["offset"])
    sign = (int_offset - tm["offset"] > 0 and 1 or -1)

    t_unit_cnt = round(int_delta * tm["bpm"] * 24 / T_MINUTE)

    beat_cnt = t_unit_cnt / 24

    ret = tm["offset"] + beat_cnt * T_MINUTE * sign / tm["bpm"]

    return ret


def get_slider_sound(str):
    ret = []
    ps = str.split(',')
    reverse_cnt = int(ps[6])
    if len(ps) == 8:
        return [int(ps[4])] * (reverse_cnt + 1)
    else:
        return [int(x) for x in ps[8].split('|')]


def get_hitnote_type(sound: int, column: int):
    is_dai = bool(sound & HITSND_FINISH)
    if column_count <= 1: # Purely keysounded
        is_katsu = bool(sound & (HITSND_CLAP | HITSND_WHISTLE))
    else: # Donkey Konga (KD) / Taiko (KDDK) layout
        n_cols_ka_l = int(math.ceil(column_count / 4))
        n_cols_ka_r = int(column_count / 4)
        is_katsu = (column < n_cols_ka_l or column_count - 1 - column < n_cols_ka_r)
    return ((ONP_KATSU_DAI if is_katsu else ONP_DON_DAI) if is_dai
        else ONP_KATSU if is_katsu else ONP_DON)


# https://github.com/ppy/osu/blob/master/osu.Game.Rulesets.Taiko/Beatmaps/TaikoBeatmapConverter.cs

VELOCITY_MULTIPLIER = 1.4
"""
<summary>
A speed multiplier applied globally to osu!taiko.
</summary>
<remarks>
osu! is generally slower than taiko, so a factor was historically added to increase speed for converts.
This must be used everywhere slider length or beat length is used in taiko.

Of note, this has never been exposed to the end user, and is considered a hidden internal multiplier.
</remarks>
"""

swell_hit_multiplier = 1.65
"""
<summary>
Because swells are easier in taiko than spinners are in osu!,
legacy taiko multiplies a factor when converting the number of required hits.
</summary>
"""

osu_base_scoring_distance: float = 100
"""<summary>
Base osu! slider scoring distance.
</summary>
"""


def get_precision_adjusted_beat_length(sliderVelocity: float, timingControlPoint) -> float:
    """
    <summary>
    Introduces floating-point errors to post-multiplied beat length for legacy rulesets that depend on it.
    You should definitely not use this unless you know exactly what you're doing.
    </summary>
    """
    sliderVelocityAsBeatLength: float = -100 / sliderVelocity

    # Note: In stable, the division occurs on floats, but with compiler optimisations turned on actually seems to occur on doubles via some .NET black magic (possibly inlining?).
    bpmMultiplier: float = (
        min(max(array('f', [-sliderVelocityAsBeatLength])[0], 10), 10000) / 100.0
        if sliderVelocityAsBeatLength < 0
        else 1)

    return timingControlPoint["mspb"] * bpmMultiplier


def should_convert_slider_to_hits(tm, curve_len: float, reverse_cnt: int) -> Tuple[bool, int, float]:
    isForCurrentRuleset = (gamemode_idx == GAMEMODE_TAIKO)

    # DO NOT CHANGE OR REFACTOR ANYTHING IN HERE WITHOUT TESTING AGAINST _ALL_ BEATMAPS.
    # Some of these calculations look redundant, but they are not - extremely small floating point errors are introduced to maintain 1:1 compatibility with stable.
    # Rounding cannot be used as an alternative since the error deltas have been observed to be between 1e-2 and 1e-6.

    # The true distance, accounting for any repeats. This ends up being the drum roll distance later
    spans: int = reverse_cnt or 1
    distance: float = curve_len

    # Do not combine the following two lines!
    distance *= VELOCITY_MULTIPLIER
    distance *= spans

    timingPoint = tm

    beatLength: float

    if timingPoint["scroll"] != 1.0:
        beatLength = get_precision_adjusted_beat_length(timingPoint["scroll"], timingPoint)
    else:
        beatLength = timingPoint["mspb"]

    assert slider_multiplier is not None and slider_tick_rate is not None
    sliderScoringPointDistance: float = osu_base_scoring_distance * (slider_multiplier * VELOCITY_MULTIPLIER) / slider_tick_rate

    # The velocity and duration of the taiko hit object - calculated as the velocity of a drum roll.
    taikoVelocity: float = sliderScoringPointDistance * slider_tick_rate
    taikoDuration = int(distance / taikoVelocity * beatLength)

    if isForCurrentRuleset:
        tickSpacing = 0
        return (False, taikoDuration, tickSpacing)

    osuVelocity: float = taikoVelocity * (1000.0 / beatLength)

    # osu-stable always uses the speed-adjusted beatlength to determine the osu! velocity, but only uses it for conversion if beatmap version < 8
    if osu_format_ver >= 8:
        beatLength = timingPoint["mspb"]

    # If the drum roll is to be split into hit circles, assume the ticks are 1/8 spaced within the duration of one beat
    tickSpacing = min(beatLength / slider_tick_rate, float(taikoDuration) / spans)

    return (tickSpacing > 0
            and distance / osuVelocity * 1000 < 2 * beatLength,
            taikoDuration, tickSpacing)


def get_note(str_: str, od: float) -> List[Tuple[str, float, int]]:
    global timing_point
    global gamemode_idx
    ret: List[Tuple[str, float, int]] = []

    if str_ is None:
        return ret
    ps = str_.split(',')
    if len(ps) < 5:
        return ret

    column = (min(max(math.floor(float(ps[0]) * column_count / 512), 0), column_count - 1)
        if gamemode_idx == GAMEMODE_MANIA
        else 0)
    type = int(ps[3])
    sound = int(ps[4])
    offset = get_real_offset(float(ps[2]))

    if type & OSU_NOTE_CIRCLE:  # circle
        ret.append((get_hitnote_type(sound, column), offset, column))
    elif type & OSU_NOTE_SLIDER:  # slider, reverse??
        tm = get_base_timing_point(timingpoints, offset)
        curve_len = float(ps[7])
        reverse_cnt = int(ps[6])
        (should_convert, taiko_duration, tick_spacing) = should_convert_slider_to_hits(tm, curve_len, reverse_cnt)

        assert reverse_cnt + 1 == len(get_slider_sound(str_))
        if should_convert:
            slider_sounds = get_slider_sound(str_)
            i = 0
            j = offset
            while j <= offset + taiko_duration + tick_spacing / 8:
                point_offset = get_real_offset(j)
                ret.append((get_hitnote_type(slider_sounds[i], column), point_offset, column))

                j += tick_spacing
                i = (i + 1) % len(slider_sounds)

                if math.isclose(tick_spacing, 0, rel_tol=0, abs_tol=1e-7):
                    break
        else:
            if sound & HITSND_FINISH:
                ret.append((ONP_RENDA_DAI, offset, column))
            else:
                ret.append((ONP_RENDA, offset, column))
            ret.append((ONP_END, offset + taiko_duration, column))

    elif type & OSU_NOTE_HOLD:  # hold, converted to circle because overlapping notes are not supported
        tmr = get_base_red_timing_point(timingpoints, offset)
        offset_end = int(ps[5].split(':', 1)[0])
        taiko_duration = offset_end - offset
        tick_spacing = min(tmr["mspb"] / slider_tick_rate, float(taiko_duration))
        j = offset
        while j <= offset + taiko_duration + tick_spacing / 8:
            point_offset = get_real_offset(j)
            ret.append((get_hitnote_type(sound, column), point_offset, column))

            j += tick_spacing

            if math.isclose(tick_spacing, 0, rel_tol=0, abs_tol=1e-7):
                break

    elif type & OSU_NOTE_SPINNER:  # spinner
        ret.append((ONP_BALLOON, offset, column))
        ret.append((ONP_END, get_real_offset(int(ps[5])), column))
        # how many hit will break a ballon
        global balloons
        hit_multiplier = (5 - 2 * (5 - od) / 5 if od < 5
            else 5 + 2.5 * (od - 5) / 5 if od > 5
            else 5) * swell_hit_multiplier
        hits = int(max(1, (ret[-1][1] - ret[-2][1]) / 1000 * hit_multiplier))
        balloons.append(hits)

    return ret


# BEAT - MEASURE TABLE: (beat_cnt, numerator, denominator)
measure_table = (
    (0.25, 1, 16),
    (1, 1, 4),
    (1.25, 5, 16),
    (1.5, 3, 8),
    (2, 2, 4),
    (2.25, 9, 16),
    (2.5, 5, 8),
    (3, 3, 4),
    (3.75, 15, 16),
    (4, 4, 4),
    (4.5, 9, 8),
    (5, 5, 4),
    (6, 6, 4),
    (7, 7, 4),
    (8, 8, 4),
    (9, 9, 4),
)

def get_tsign(tsign_raw: Fraction) -> Tuple[int, int]:
    denominator = tsign_raw.denominator
    numerator = tsign_raw.numerator

    if denominator in (1, 2):
        fix_mul = 4 // denominator
        denominator *= fix_mul
        numerator *= fix_mul

    return (numerator, denominator)

# handle an incomplete bar
# use #MEASURE to write a bar, and use #DELAY to fix the remaining time error.


def write_incomplete_bar(tm, bar_data, begin, end, tja_contents):
    if int(math.floor(begin)) == int(math.floor(end)) and len(bar_data) == 0 and len(commands_within) == 0:
        return

    mspb = T_MINUTE / tm["bpm"]
    my_beat_cnt = 1.0 * (end - begin) * tm["bpm"] / T_MINUTE

    # this is accurate
    time_bar_data_last = bar_data[-1][1] if len(bar_data) > 0 else begin
    min_beat_cnt = 1.0 * tm["bpm"] * (time_bar_data_last - begin) / T_MINUTE

    # force guess measure?
    global guess_measure
    for beat_cnt, numerator, denominator in (measure_table if not guess_measure else []):
        if beat_cnt > min_beat_cnt and \
                abs(beat_cnt - my_beat_cnt) < 1 / 384 and \
                abs(int(math.floor(begin + 1.0 * beat_cnt * mspb)) - int(math.floor(end))) <= 25:
            break
    else:
        # Missing all, guess a measure here!
        fraction = Fraction(my_beat_cnt / 4).limit_denominator(48 * 48)
        (numerator, denominator) = get_tsign(fraction)

        # avoid the last note to be divided into the next bar
        if min_beat_cnt > 0 and numerator <= min_beat_cnt * denominator:
            numerator = int(min_beat_cnt * denominator) + 1
            # re-simplify the fraction
            (numerator, denominator) = get_tsign(Fraction(numerator, denominator))
        # TaikoJiro does not support 0/x measures. Use a <= 1ms measure instead.
        # Note: numerator and denominator can both have decimal places
        elif numerator == 0:
            (numerator, denominator) = (1, 4 * max(1, mspb))

        beat_cnt = 4 * numerator / denominator

    tja_contents.append(make_cmd(FMT_MEASURECHANGE, numerator, denominator))
    write_bar_data(tm, bar_data, begin, begin + beat_cnt * mspb, tja_contents)
    delay_time = int(math.floor(end)) - int(math.floor(begin + beat_cnt * mspb))
    # Note: #DELAY value can be in any sign

    # jiro will ignore delays shorter than 0.001s
    if abs(delay_time) >= 1:
        tja_contents.append(make_cmd(FMT_DELAY, delay_time / 1000.0))


def get_dt_unit_cnt(t_unit: float, offset0: Union[float, int], offset1: Union[float, int]) -> int:
    delta = (offset1 - offset0) / t_unit
    return int(round(delta))


def write_bar_data(tm, bar_data, begin, end, tja_contents):
    global show_head_info
    global combo_cnt, tail_fix
    global commands_within

    if int(math.floor(begin)) == int(math.floor(end)) and len(bar_data) == 0 and len(commands_within) == 0:
        return

    # ms per 1/96th note; quantize to 1/96th
    t_unit = 60.0 * 1000 / tm["bpm"] / 24

    # ignore past-end notes
    if len(bar_data) > 0 and get_dt_unit_cnt(t_unit, bar_data[-1][1], int(math.floor(end))) <= 0:
        tail_fix = True
        write_bar_data(tm, bar_data[:-1], begin, end, tja_contents)
        return

    # ignore past-end commands
    idx_cmd_limit = bisect_left(commands_within, int(math.floor(end)), key=lambda cmd: cmd[0])

    # build offset data
    offset_list = sorted(set(itertools.chain(
        [int(math.floor(begin))],
        (cmd[0] for _, cmd in zip(range(idx_cmd_limit), commands_within)), # in-range commands
        (datum[1] for datum in bar_data),
        [int(math.floor(end))],
    )))

    # calculate beat division (no known efficient general solution exists (integer factor problem); do heuristics here)
    delta_list = [get_dt_unit_cnt(t_unit, offset_list[i], offset_list[i + 1])
        for i in range(len(offset_list) - 1)]
    delta_list_non_zero = [d for d in delta_list if d != 0] # ignore sub-quantization intervals
    delta_gcd = gcd_of_list(delta_list_non_zero) if len(delta_list_non_zero) != 0 else 1

    # build notechart definition bar string
    bar_strs: List[str] = []
    idx_cmd = 0
    idx_bar_data = 0
    # floating number offset should match exactly here since they are in the list as-is
    # use <= in case bad things happen
    for offset, delta_n_symbols in zip(offset_list, delta_list): # in range(len(offset_list) - 1)
        # Insert commands
        while idx_cmd < len(commands_within) and commands_within[idx_cmd][0] <= offset:
            bar_strs.append("\n")
            bar_strs.append(make_cmd(*commands_within[idx_cmd][1:]))
            bar_strs.append("\n")
            idx_cmd += 1

        if delta_n_symbols > 0:
            # Insert a note (simultaneous notes are not supported)
            note = ONP_NONE
            while idx_bar_data < len(bar_data) and bar_data[idx_bar_data][1] <= offset:
                note = bar_data[idx_bar_data][0]
                idx_bar_data += 1
            if note in (ONP_DON, ONP_KATSU, ONP_DON_DAI, ONP_KATSU_DAI):
                combo_cnt += 1
            bar_strs.append(note)

            # Insert blanks (if needed)
            bar_strs.append("0" * int(delta_n_symbols / delta_gcd - 1))

    # remove processed notechart objects
    commands_within = commands_within[idx_cmd:]
    # bar_data = bar_data[idx_bar_data:] # useless

    # bar-terminating symbol (1-symbol beat length if comes solely, otherwise zero length)
    bar_strs.append(',')
    bar_str = ''.join(bar_strs)

    head = "%4d %6d %.2f %2d " % (combo_cnt,
                                  format_time(int(math.floor(begin))), delta_gcd/24.0, len(bar_str))

    if show_head_info:  # show debug info?
        print_with_pended(head + bar_str, file=sys.stderr)

    tja_contents.append(bar_str)


def osu2tja_level(star_osu: float) -> float:
    # 0 to 13 distribution, only a preliminary approximant
    # osu! 0 -> Taiko 1 (OpenTaiko 0)
    # osu! 6 -> Taiko 10 (OpenTaiko 10+)
    # osu! 10 -> OpenTaiko 12+
    min_ = 0.5
    range_ = 12.9374
    exp_base_ = 9.21907
    offset_ = 1.08941
    power_ = 0.514826
    factor_ = range_ / (math.pi / 2)
    return min_ + factor_ * math.atan(math.pow(exp_base_, math.pow(star_osu, power_) - offset_) / factor_)

MS_OSU_MUSIC_OFFSET = 15
"""Ranked osu! beatmaps have late music / early chart sync. osu!'s new audio engine applies a global 15ms chart delay.
<https://github.com/ppy/osu/issues/24625>
"""

MS_OSU_PRE_V5_MUSIC_OFFSET = -24
"""Ranked osu! beatmaps before format v5 had additional early music / late chart sync.
<https://github.com/ppy/osu/discussions/26133>
"""

def osu2tja(fp: IO[str], course: Union[str, int], level: Union[int, float], audio_name: Optional[str]) -> Tuple[
        List[str], List[str], List[str], List[str]
    ]:
    reset_global_variables()
    global slider_multiplier, slider_tick_rate, column_count, timingpoints
    global balloons, tail_fix
    global osu_format_ver
    global commands_within
    global gamemode_idx

    tja_heads_meta: List[str] = []
    tja_heads_sync: List[str] = []
    tja_heads_diff: List[str] = []
    tja_contents: List[str] = []

    # data structures to hold information
    audio = ""
    title = ""
    subtitle = ""
    creator = ""
    artist = ""
    version = ""
    preview = 0
    hitobjects: List[Tuple[str, float, int]] = []

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
            osu_format_ver = int(line.partition(OSU_VER_STR_PREFIX)[2])
            if osu_format_ver not in OSU_VER_SUPPORT:
                str_vers_support = "/".join((str(i) for i in OSU_VER_SUPPORT))
                print_with_pended(f"Warning: found osu file format v{osu_format_ver}, but only v{str_vers_support} are supported at this moment. The conversion will be performed but might fail.",
                      file=sys.stderr)

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
                if ext.lower() not in [".ogg", ".mp3"]:
                    vval = root+".ogg"
                audio = vval
            elif vname == "PreviewTime":
                preview = int(vval)
            elif vname == "Mode":
                gamemode_idx = int(vval)

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
            if vname == "CircleSize":
                if gamemode_idx == GAMEMODE_MANIA:
                    column_count = int(vval)
            elif vname == "SliderMultiplier":
                slider_multiplier = float(vval)
            elif vname == "SliderTickRate":
                slider_tick_rate = float(vval)
            elif vname == "OverallDifficulty":
                overall_difficulty = math.floor(float(vval)) # accuracy, not the actual star rating
        elif curr_sec == "TimingPoints":
            prev_timing_point = timingpoints and timingpoints[-1] or None
            data = get_timing_point(line, prev_timing_point)
            if data:
                timingpoints.append(data)
        elif curr_sec == "HitObjects":
            data = get_note(line, overall_difficulty)
            idx_last = 0
            for obj in data:
                # fix out-of-order objects for converted osu!mania holds
                idx_last = bisect_right(hitobjects, obj[1], lo=idx_last, key=lambda x: x[1])
                hitobjects.insert(idx_last, obj)

    assert len(hitobjects) > 0

    # The music starts at 0ms and the bar line starts too.
    # add an initial timing point at whole beats non-after the music
    if timingpoints[0]["offset"] > 0:
        tm_first = timingpoints[0]
        init_beats = int(math.ceil(tm_first["offset"] / tm_first["mspb"]))
        (init_whole_bars, init_frac_bar_beats) = divmod(init_beats, tm_first["beats"])
        new_tms = []

        # timing point for the first beat, if not a whole bar
        if init_frac_bar_beats != 0:
            new_tm_first_frac = dict(tm_first)
            new_tm_first_frac["offset"] = get_real_offset(
                tm_first["offset"] - init_beats * tm_first["mspb"])
            new_tm_first_frac["beats"] = init_frac_bar_beats
            new_tms.append(new_tm_first_frac)

        # timing point for the first whole bar, if any
        if init_whole_bars != 0:
            new_tm_first_whole = dict(tm_first)
            new_tm_first_whole["offset"] = get_real_offset(
                tm_first["offset"] - init_whole_bars * tm_first["beats"] * tm_first["mspb"])
            new_tm_first_whole["beats"] = tm_first["beats"]
            new_tms.append(new_tm_first_whole)

        if len(new_tms) != 0:
            timingpoints = new_tms + timingpoints

    # collect all #SCROLL #GOGOSTART #GOGOEND commands
    # these commands will not be broken by #BPMCHANGE or # MEASURE
    assert slider_multiplier is not None
    sv_err_max = 0.00025
    # Ranked osu!taiko beatmaps uses SV 1.40. tja2osu uses SV 1.44. Allows up-to SV 1.47.
    base_scroll = (1.0 if 1.40 - sv_err_max <= slider_multiplier <= 1.47 + sv_err_max
        else slider_multiplier / 1.40)
    cur_scroll = 1.0
    cur_ggt = False
    for tm in timingpoints:
        scroll = tm["scroll"] * base_scroll
        if scroll != cur_scroll:
            commands_within.append(
                (tm["offset"], FMT_SCROLLCHANGE, scroll))
        if tm["GGT"] != cur_ggt:
            commands_within.append((tm["offset"],
                                    tm["GGT"] and FMT_GOGOSTART or FMT_GOGOEND))
        cur_scroll = scroll
        cur_ggt = tm["GGT"]

    BPM = timingpoints[0]["bpm"]
    ms_osu_total_offset = MS_OSU_MUSIC_OFFSET
    if osu_format_ver < 5:
        ms_osu_total_offset += MS_OSU_PRE_V5_MUSIC_OFFSET
    OFFSET = (-timingpoints[0]["offset"] - ms_osu_total_offset) / 1000.0
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
    tja_heads_meta.append(WATER_MARK)
    tja_heads_meta.append("TITLE:%s" % title)
    if subtitle != "" and artist != "":
        subtitle = f"{artist} ｢{subtitle}｣より"
    tja_heads_meta.append("SUBTITLE:--%s" % (subtitle or artist))
    tja_heads_meta.append("WAVE:%s" % (audio_name or audio))
    tja_heads_meta.append("MAKER:%s" % creator) # for TJAP2fPC-based sims
    tja_heads_meta.append("AUTHOR:%s" % creator) # for Malody

    tja_heads_meta.append("DEMOSTART:%.3f" % (preview / 1000.0))

    tja_heads_sync.append("BPM:%.2f" % timingpoints[0]["bpm"])
    tja_heads_sync.append("OFFSET:%.3f" % OFFSET)

    str_info_diff_orig = f"// osu! difficulty: {version}"
    if gamemode_idx != GAMEMODE_TAIKO:
        str_mode = GAMEMODE_TO_STR.get(gamemode_idx, f"game mode {gamemode_idx}")
        str_info_diff_orig += f" ({str_mode} convert)"
    tja_heads_diff.append(str_info_diff_orig)
    tja_heads_diff.append(f"COURSE:{course}") # TODO: GUESS DIFFICULTY
    if level is None:
        level = osu2tja_level(overall_difficulty)
    tja_heads_diff.append(f"LEVEL:{level}")  # TODO: GUESS LEVEL

    # don't write score init and score diff
    # taiko jiro will calculate score automatically
    tja_heads_diff.append("BALLOON:%s" % ','.join(map(repr, balloons)))

    tja_contents.append("#START")

    def is_new_measure(timing_point):
        bpm = timing_point["bpm"]
        _measure = timing_point["beats"]
        return bpm != curr_bpm or measure != _measure or timing_point["redline"]

    # check if all notes align ok
    for i, (ho1, ho2) in enumerate(zip(hitobjects[:-1], hitobjects[1:])):
        # allows simultaneous notes in different columns
        if ho1[1] > ho2[1] or (ho1[1] == ho2[1] and ho1[2] == ho2[2]):
            print_with_pended(f"Warning: Hit object {i}: {ho1} occurs non-before hit object {i + 1}: {ho2}.", file=sys.stderr)

    while obj_idx < len(hitobjects):
        # get next object to process
        next_obj = hitobjects[obj_idx]
        next_obj_offset = int(math.floor(next_obj[1]))
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

        if next_obj_offset >= int(math.floor(end)):
            # write_a_measure()
            if int(math.floor(end)) == int(math.floor(bar_offset_begin + bar_max_length)):
                tm = get_base_timing_point(timingpoints, bar_offset_begin)
                write_bar_data(tm, bar_data, bar_offset_begin,
                               end, tja_contents)
                bar_data = []
                bar_cnt += 1
                bar_offset_begin = get_real_offset(end)
                bar_max_length = measure * time_per_beat
            elif int(math.floor(end)) == int(math.floor(next_measure_offset)):  # collect an incomplete bar?
                if tm_idx > 0: # not the start of the initial bar
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
                    new_obj = (hitobjects[obj_idx][0], bar_offset_begin, hitobjects[obj_idx][2])
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
    return tja_heads_meta, tja_heads_sync, tja_heads_diff, tja_contents


def main():
    parser = argparse.ArgumentParser(
        description='Convert an .osu file to .tja format and print the result.',
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("filename", help="source .osu file")
    parser.add_argument("-d", "--debug", action="store_true",
        help="display extra info")
    parser.add_argument("-g", "--guess-measure", "--guess", action="store_true",
        help="force skipping predefined integer ratio look-up for bar length")
    args = parser.parse_args()

    global show_head_info, guess_measure
    show_head_info = args.debug
    guess_measure = args.guess_measure

    # check filename
    if not args.filename.lower().endswith(".osu"):
        print("Input file should be Osu file!(*.osu): \n\t[[ %s ]]" % args.filename, file=sys.stderr)
        return

    # try to open file
    try:
        fp = codecs.open(args.filename, "r", "utf8")
        head_meta, head_sync, head_diff, diff_content = osu2tja(fp, 3, 9, None) # defaulted course and level
        head_sync_main = head_sync
    except IOError:
        print("Can't open file `%s`" % args.filename, file=sys.stderr)
        return

    # print results
    print("\n".join(head_meta))
    print("\n".join(head_sync_main))
    print()
    print("\n".join(head_diff))
    print("\n".join(head_sync))
    print("\n")
    print("\n".join(diff_content))


if __name__ == "__main__":
    main()

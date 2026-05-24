from array import array
from bisect import bisect_right
from dataclasses import dataclass
from enum import Enum
import math
from typing import Callable, Dict, List, Optional, Sequence, TypeVar, Union, cast

OSU_VER_STR_PREFIX = "osu file format v"

OSU_VER_MIN = 3
OSU_VER_MAX = 14
OSU_VER_LAZER = 128
def osu_ver_supported(v):
    return OSU_VER_MIN <= v <= OSU_VER_MAX or v == OSU_VER_LAZER


T_MINUTE = 60000


class EHideFirst(Enum):
    BARLINE_IN_SHOWN = -2 # TJA real bar line or #BARLINE when #BARLINEON
    UNHIDDEN = BARLINE_IN_HIDDEN = -1 # osu! after hidefirst / TJA #BARLINE when #BARLINEOFF
    SHOWN = 0 # osu! not hidefirst / TJA #BARLINEON
    TO_UNHIDE = 1 # osu! hidefirst
    HIDDEN = 2 # osu! before hidefirst / TJA #BARLINEOFF

    def is_hidden(self) -> bool:
        return self in {EHideFirst.TO_UNHIDE, EHideFirst.HIDDEN}

    def is_barline(self) -> bool:
        return self in {EHideFirst.BARLINE_IN_HIDDEN, EHideFirst.BARLINE_IN_SHOWN}

    def add_barline(self) -> "EHideFirst":
        return (EHideFirst.BARLINE_IN_SHOWN if self == EHideFirst.SHOWN
            else EHideFirst.BARLINE_IN_HIDDEN if self == EHideFirst.HIDDEN
            else self)

    def remove_barline(self) -> "EHideFirst":
        return (EHideFirst.SHOWN if self == EHideFirst.BARLINE_IN_SHOWN
            else EHideFirst.HIDDEN if self == EHideFirst.BARLINE_IN_HIDDEN
            else self)

    def barline_on(self) -> "EHideFirst":
        return (EHideFirst.BARLINE_IN_SHOWN if self == EHideFirst.BARLINE_IN_HIDDEN
            else EHideFirst.SHOWN if self == EHideFirst.HIDDEN
            else self)

    def barline_off(self) -> "EHideFirst":
        return (EHideFirst.BARLINE_IN_HIDDEN if self == EHideFirst.BARLINE_IN_SHOWN
            else EHideFirst.HIDDEN if self == EHideFirst.SHOWN
            else self)


@dataclass
class OsuTimingPoint:
    offset: float
    sevol: float = 100
    ggt: bool = False
    hidefirst: EHideFirst = EHideFirst.SHOWN
    # redline or inherited properties
    mspb: float = T_MINUTE / 120
    bpm: float = 120
    beats: float = 4
    beat_res: int = 192 // 4 # 1/192nd
    # greenline properties
    scroll: float = 1.0
    offset_raw: float = 0
    # redline pointer
    redtm: Optional["OsuTimingPoint"] = None

    def is_redline(self) -> bool:
        return self.redtm == self

    def unhide_first(self) -> bool:
        if self.hidefirst == EHideFirst.TO_UNHIDE:
            self.hidefirst = EHideFirst.UNHIDDEN
            return True
        return False

    def merge_with(self, tmg: Optional["OsuTimingPoint"] = None, tmr: Optional["OsuTimingPoint"] = None) -> None:
        if tmg is not None:
            self.sevol = tmg.sevol
            self.ggt = tmg.ggt
            self.hidefirst = tmg.hidefirst
        # redline or inherited properties
        if tmr is not None:
            self.mspb = tmr.mspb
            self.bpm = tmr.bpm
            self.beats = tmr.beats
            self.beat_res = tmr.beat_res
        # greenline properties
        if tmg is not None:
            self.scroll = tmg.scroll


def get_osu_meter(beats: float) -> int:
    return math.ceil(min(max(beats, 1), (1 << 31) - 1))


def get_last_tm(timing_points: List[OsuTimingPoint]):
    return timing_points[-1]


def get_last_red_tm(timing_points: List[OsuTimingPoint]):
    tmr = get_last_tm(timing_points).redtm
    assert tmr is not None, "Need at least one uninherited timing point"
    return tmr


def get_idx_tm_at(timing_points: List[OsuTimingPoint], t, raw=False):
    assert len(timing_points) > 0, "Need at least one timing point"
    # A note can appear even the first timing point
    key: Callable[[OsuTimingPoint], float] = (lambda tm: tm.offset_raw) if raw else (lambda tm: tm.offset)
    idx_tm = max(0, bisect_right(timing_points, t, key=key) - 1)
    return idx_tm


def get_tm_at(timing_points: List[OsuTimingPoint], t, raw=False):
    return timing_points[get_idx_tm_at(timing_points, t, raw)]  # no copy for correctly updating hidefirst


def get_red_tm_at(timing_points: List[OsuTimingPoint], t, raw=False):
    tmr = get_tm_at(timing_points, t, raw).redtm
    assert tmr is not None, "Need at least one uninherited timing point"
    return tmr

def f32(val: float):
    return array('f', [val])[0]

# https://github.com/ppy/osu-framework/blob/master/osu.Framework/Utils/Precision.cs
EPSILON_F32 = f32(1e-3)
EPSILON_F64 = 1e-7

def definitely_bigger(v1, v2, error = EPSILON_F64):
    return v1 - error > v2

def almost_bigger(v1, v2, error = EPSILON_F64):
    return v1 > v2 - error

def almost_equals(v1, v2, error = EPSILON_F64):
    return abs(v1 - v2) <= error

# bar end aligned to integer or uninherited timing point
# https://github.com/ppy/osu/issues/28317

def ceil_if_almost_int(ms: float) -> float:
    ims = math.copysign(math.ceil(abs(ms)), ms)
    return ims if almost_equals(ms, ims) else ms

diffrank_to_name: Dict[float, Sequence[str]] = {
    -1: ("beginner", "shokyuu"),
    0: ("easy", "kantan", "cup", "ez", "past", "whisper"),
    0.5: ("basic", "bsc"),
    1: ("normal", "futsuu", "salad", "nm", "medium", "novice", "nov", "present", "acoustic"),
    1.5: ("advanced", "adv"),
    2: ("hard", "muzukashii", "muzu", "platter", "difficult", "hd", "future", "ultra"),
    2.5: ("hyper"),
    3: ("insane", "oni", "rain", "extreme", "another", "mx", "shd", "exhaust", "exh", "eternal", "acoustic"),
    3.5: ("expert"),
    4: ("extra", "edit", "ura", "inner", "overdose", "edit", "black", "challenge",
        "sc", "ex", "beyond", "inf", "grv", "mxm", "ult", "ultra", "master", "chaos", "special", "phantasm"),
    4.25: ("master"),
    4.5: ("extreme", "hell", "deluge", "leggendaria", "hvn", "vvd", "xcd", "re:master", "ultima", "world's", "lunatic", "glitch", "crash"),
}

T = TypeVar('T', bound=Optional[float])

def get_diffrank_by_name(name: Optional[str], default: T = 3, allow_num: bool = True) -> T:
    if name is not None:
        if allow_num:
            try:
                return cast(T, float(name))
            except ValueError:
                pass
        words = set(name.lower().split())
        for rank, keywords in diffrank_to_name.items():
            if any(((kw in words) for kw in keywords)):
                return cast(T, rank)
    return default 

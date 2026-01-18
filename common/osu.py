from bisect import bisect_right
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Dict, List, Optional, Sequence

OSU_VER_STR_PREFIX = "osu file format v"

OSU_VER_MIN = 3
OSU_VER_MAX = 14
OSU_VER_LAZER = 128
def osu_ver_supported(v):
    return OSU_VER_MIN <= v <= OSU_VER_MAX or v == OSU_VER_LAZER


T_MINUTE = 60000


class EHideFirst(Enum):
    UNHIDDEN = -1
    SHOWN = 0
    TO_UNHIDE = 1
    HIDDEN = 2

    def is_hidden(self) -> bool:
        return self in {EHideFirst.TO_UNHIDE, EHideFirst.HIDDEN}


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
        return self.redtm is None or self.redtm == self


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


def get_diffrank_by_name(name: Optional[str]) -> float:
    if name is not None:
        try:
            return float(name)
        except ValueError:
            words = set(name.lower().split())
            for rank, keywords in diffrank_to_name.items():
                if any(((kw in words) for kw in keywords)):
                    return rank
    return 3

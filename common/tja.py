from dataclasses import dataclass
from enum import Enum
import re
from typing import Generic, Optional, OrderedDict, Sequence, Tuple, TypeVar, Union, cast

Str = TypeVar('Str', str, bytes)


class EHitTypeTja(Enum):
    HIT = '1'
    RENDA = '5'
    BALLOON = '7'

class EHitSoundTja(Enum):
    DON = '1'
    KATSU = '2'
    KADON = 'G'
    CLAP = '4'

class ENoteTja(Enum):
    NONE = '0'

    DON = '1'
    KATSU = '2'
    DON_DAI = '3'
    KATSU_DAI = '4'
    DON_HAND = 'A'
    KATSU_HAND = 'B'
    KADON = 'G'

    BOMB = 'C'
    ADLIB = 'F'

    RENDA = '5'
    RENDA_DAI = '6'
    RENDA_CLAP = 'H'
    RENDA_PA = 'I'

    BALLOON = '7'
    IMO = '9'
    FUZE = 'D'

    END = '8'

    __hit_type = (DON, KATSU, DON_DAI, DON_HAND, KATSU_DAI, KATSU_HAND, KADON)
    __renda_type = (RENDA, RENDA_DAI, RENDA_CLAP, RENDA_PA)
    __balloon_type = (BALLOON, IMO, FUZE)

    @staticmethod
    def get_hit_types(): return ENoteTja.__hit_type
    @staticmethod
    def get_renda_types(): return ENoteTja.__renda_type
    @staticmethod
    def get_balloon_types(): return ENoteTja.__balloon_type

    def is_hit_type(self) -> bool:
        return self.value in ENoteTja.__hit_type

    def is_renda_type(self) -> bool:
        return self.value in ENoteTja.__renda_type

    def is_balloon_type(self) -> bool:
        return self.value in ENoteTja.__balloon_type


# guess str
ENCODINGS_KNOWN = ["utf-8-sig", "gbk", "shift-jis", "big5"]


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


def get_course_by_number(num: Union[float, Str]) -> str:
    if (isinstance(num, str) or isinstance(num, bytes)) and not num.isdigit():
        return convert_str(num) if type(num) == bytes else cast(str, num)
    num = int(num)
    if num <= 0:
        return "Easy"
    elif num == 1:
        return "Normal"
    elif num == 2:
        return "Hard"
    elif num == 3:
        return "Oni"
    elif num == 4:
        return "Edit"
    else:
        return "Edit%d" % (num - 4)


str_pat_tja_header = r'^[ \t]*([^ \t:]*)[ \t]*:(.*)$'
pat_tja_header = re.compile(str_pat_tja_header)
bpat_tja_header = re.compile(str_pat_tja_header.encode())


@dataclass
class TjaHdr(Generic[Str]):
    name: Str
    arg: Str


def parse_tja_header(line: Str) -> Optional[TjaHdr]:
    match = cast(re.Pattern[Str], bpat_tja_header if type(line) == bytes else pat_tja_header).match(line)
    if match is None:
        return None
    return TjaHdr(*match.groups())


str_pat_tja_command = r'^[ \t]*#([^ \t]*[A-Z_]+)[ \t]?(.*)$'
pat_tja_command = re.compile(str_pat_tja_command)
bpat_tja_command = re.compile(str_pat_tja_command.encode())


@dataclass
class TjaCmd(Generic[Str]):
    name: Str
    args: Sequence

    def __init__(self, name, *args):
        object.__setattr__(self, 'name', name)
        object.__setattr__(self, 'args', args)


def parse_tja_command(line: Str) -> Optional[TjaCmd]:
    match = cast(re.Pattern[Str], bpat_tja_command if type(line) == bytes else pat_tja_command).match(line)
    if match is None:
        return None
    return TjaCmd(*match.groups())

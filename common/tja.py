from dataclasses import dataclass
import re
from typing import Generic, Optional, Sequence, TypeVar, Union, cast

Str = TypeVar('Str', str, bytes)


def get_course_by_number(num: Union[float, Str]) -> str:
    if isinstance(num, str) and not num.isdigit():
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

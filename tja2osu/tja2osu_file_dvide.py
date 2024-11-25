# sys.path hack
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from . import tja2osu
except ImportError:
    import tja2osu.tja2osu
from common.utils import print_with_pended, print_pend, print_unpend

import argparse
import codecs
from importlib import reload
from pyexpat.errors import codes
import shutil
import sys
import os
import textwrap
import traceback
from typing import Dict, List, Optional, Tuple

WATER_MARK = b"//Auto generated by osu2tja"

# song data
WAVE = b""

def get_course_by_number(str_: bytes) -> str:
    if not str_.isdigit():
        return tja2osu.convert_str(str_)
    num = int(str_)
    if num <= 0: return "Easy"
    elif num == 1: return "Normal"
    elif num == 2: return "Hard"
    elif num == 3: return "Oni"
    elif num == 4: return "Edit"
    else: return "Edit%d" % (num-4)

def get_style(str_: bytes) -> Optional[int]:
    if str_.isdigit():
        return int(str_)
    if str_.lower() == b"single":
        return 1
    if str_.lower() in {b"double", b"couple"}:
        return 2
    return None

def parse_tja_header(line: bytes) -> Tuple[Optional[bytes], bytes]:
    global WAVE
    vname, delim, vval = line.partition(b":")
    vname = vname.strip()
    vval = vval.strip()
    if vname == b"WAVE":
        WAVE = vval
    if delim == b":" and vname.isalnum(): # probably a header
        return vname, vval
    return None, b""

def divide_diff(path_tja: str, dir_out: str) -> List[str]:
    assert isinstance(path_tja, str)
    fname_base, ext = os.path.splitext(os.path.basename(path_tja))
    assert ext == ".tja"

    fnames_by_course: Dict[Tuple[str, int, int], List[str]] = {}
    course = "Oni"
    style = 1
    player_side = 0
    common_data: List[bytes] = []
    diff_data: List[bytes] = []
    started = False
    fobj = open(path_tja, "rb")
    bom = b""

    def write_chartdef():
        fnames = fnames_by_course.setdefault((course, style, player_side), [])
        course_suffixes: List[str] = []
        if style > 1 or player_side > 0:
            course_suffixes.append(f"({style}P_P{player_side + 1})")
        if len(fnames) > 0:
            course_suffixes.append(f"(No{len(fnames)})")
        fname = f"{fname_base} {course}{''.join(course_suffixes)}.tja"
        fnames.append(fname)

        fout = open(os.path.join(dir_out, fname), "wb")

        fout.write(bom + WATER_MARK + b"\n")
        for str_ in common_data:
            fout.write(str_)
            fout.write(b"\n")
        fout.write(b"\nCOURSE:%s\n\n" % (course.encode('latin1'),))

        for str_ in diff_data:
            fout.write(str_)
            fout.write(b"\n")
        fout.close()

        diff_data.clear()

    if fobj.peek(len(codecs.BOM_UTF8)).startswith(codecs.BOM_UTF8):
        bom = fobj.read(len(codecs.BOM_UTF8)) # extract UTF-8 BOM
    for line in fobj:
        line = line.rstrip(b"\r\n")
        line_no_comment, comment_delim, comment = line.partition(b"//")
        if not started and b"#START" in line_no_comment:
            started = True
            _, line, side_str = line_no_comment.partition(b"#START")
            if comment_delim:
                line += b" " + comment_delim + comment # rebuild line
            side_str = side_str.strip()
            if side_str.startswith(b"P") and side_str[1:].isdigit():
                player_side = int(side_str[1:]) - 1
            else:
                player_side = 0
        if started:
            diff_data.append(line)
        else:
            vname, vval = parse_tja_header(line_no_comment)
            if vname == b"COURSE":
                assert vval is not None
                course = get_course_by_number(vval)
            elif vname == b"STYLE":
                style = get_style(vval) or style
            else:
                common_data.append(line)
        if started and b"#END" in line_no_comment:
            write_chartdef()
            started = False
    fobj.close()

    if started: # missing #END; implicit #END at end-of-file
        write_chartdef()

    return [fname for fnames in fnames_by_course.values() for fname in fnames]

def divide_branch(path_tja: str, dir_out: str) -> List[str]:
    assert isinstance(path_tja, str)
    fname, ext = os.path.splitext(os.path.basename(path_tja))
    assert ext == ".tja"

    try:
        fobj = open(path_tja, "rb")
    except IOError:
        assert False, "can't open tja file."

    bom = b""
    if fobj.peek(len(codecs.BOM_UTF8)).startswith(codecs.BOM_UTF8):
        bom = fobj.read(len(codecs.BOM_UTF8)) # extract UTF-8 BOM
    branch_data: List[List[bytes]] = [[], [], []]
    which = None

    has_branch = False
    for line in fobj:
        line = line.strip()
        line_no_comment, _, _ = line.partition(b"//")
        if b"#BRANCHSTART" in line_no_comment:
            has_branch = True
            continue
        if b"#BRANCHEND" in line_no_comment \
            or b"#SECTION" in line_no_comment:
            continue
        if b"#E" in line_no_comment:
            which = "E"
        elif b"#N" in line_no_comment:
            which = "N"
        elif (b"#M" in line_no_comment) and (b"#MEASURE" not in line_no_comment):
            which = "M"
        elif b"#BRANCHEND" in line_no_comment:
            which = None
        else:
            vname, _, vval = line_no_comment.partition(b":")
            vname = vname.strip()
            vval = vval.strip()
            if vname == b"COURSE":
                vval_str = vval
                branch_data[0].append(b"COURSE:" + vval_str + b"(Kurouto)")
                branch_data[1].append(b"COURSE:" + vval_str + b"(Futsuu)")
                branch_data[2].append(b"COURSE:" + vval_str + b"(Tatsujin)")
                continue

            line_str = line
            if which == None:
                branch_data[0].append(line_str)
                branch_data[1].append(line_str)
                branch_data[2].append(line_str)
            elif which == "E":
                branch_data[0].append(line_str)
            elif which == "N":
                branch_data[1].append(line_str)
            elif which == "M":
                branch_data[2].append(line_str)
            else:
                assert False
    fobj.close()
    if not has_branch:
        return []

    file_list = [f"{fname}(Kurouto).tja", f"{fname}(Futsuu).tja", f"{fname}(Tatsujin).tja"]
    i = 0
    for f in file_list:
        fout = open(os.path.join(dir_out, f), "wb")
        fout.write(bom + WATER_MARK + b"\n")
        for str_ in branch_data[i]:
            fout.write(str_)
            fout.write(b"\n")
        fout.close()
        i += 1

    return file_list


def tja2osus(fpath_tja: str, target_path: str="out") -> None:
    dirname_dest, ext = os.path.splitext(os.path.basename(fpath_tja))
    dir_tmp = os.path.join("tmp", dirname_dest)
    os.makedirs(dir_tmp, exist_ok=True)
    all_file_list = []
    print(f"Splitting `{fpath_tja}` ...", end="", flush=True)
    print_pend()
    try:
        file_list = divide_diff(fpath_tja, dir_tmp)
    except Exception:
        print_with_pended(traceback.format_exc(), file=sys.stderr)
        print(f"Error splitting `{fpath_tja}` into difficulties. Continued.", file=sys.stderr)
        file_list: List[str] = []
    for diff_file in file_list:
        fpath_tja_diff = os.path.join(dir_tmp, diff_file)
        try:
            branch_file_list = divide_branch(fpath_tja_diff, dir_tmp)
        except Exception:
            print_with_pended(traceback.format_exc(), file=sys.stderr)
            print(f"Error splitting difficulty TJA `{fpath_tja_diff}` into branches. Continued.", file=sys.stderr)
            continue
        if len(branch_file_list) > 0:
            all_file_list.extend(branch_file_list)
        else:
            all_file_list.append(diff_file)
    print_unpend()
    print(f"\rSplitting `{fpath_tja}` into `{'`, `'.join(all_file_list)}` done!")

    resources: Dict[str, str] = {}

    dir_out = os.path.join(target_path, dirname_dest)
    os.makedirs(dir_out, exist_ok=True)
    for fname_tja_i in all_file_list:
        fpath_tja_i = os.path.join(dir_tmp, fname_tja_i)
        fname, ext = os.path.splitext(fname_tja_i)
        tja_name_i, diff = fname.rsplit(None, 1)
        fname_osu_i = f"{tja_name_i}[{diff}].osu"
        fpath_osu_i = os.path.join(dir_out, fname_osu_i)
        fout = open(fpath_osu_i, "w")
        print(f"Converting `{fpath_tja_i}` to `{fname_osu_i}` ...", end="", flush=True)
        print_pend()
        try:
            rescs = tja2osu.tja2osu(fpath_tja_i, fout)
            resources.update(rescs)
        except Exception:
            print_with_pended(traceback.format_exc(), file=sys.stderr)
            print(f"Error processing {diff} difficulty of `{fpath_tja_i}`. Continued.", file=sys.stderr)
        fout.close()
        print_unpend()
        print(f"\rConverting `{fpath_tja_i}` to `{fname_osu_i}` done!")

    for rfname, rtype in resources.items():
        rfpath_src = os.path.join(os.path.dirname(fpath_tja), rfname)
        rfpath_desk = os.path.join(dir_out, rfname)
        try:
            shutil.copyfile(rfpath_src, rfpath_desk)
        except FileNotFoundError:
            print(f"Warning: Referenced {rtype} file `{rfpath_src}` not found. Not copied.", file=sys.stderr)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=textwrap.dedent('''\
        Convert a general .tja file to multiple .osu files and copy the audio to "out/<song_folder>/".
        Intermediate single-notechart branch-less .tja files are written to "tmp/<song_folder>/"
        '''),
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("filename",
        help="source .tja file. Allows multiple notechart definitions and branch commands.")
    args = parser.parse_args()
    tja2osus(args.filename)

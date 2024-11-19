import codecs
from importlib import reload
from pyexpat.errors import codes
import shutil
import sys
import os
from typing import List

try:
    from . import tja2osu
except ImportError:
    import tja2osu

WATER_MARK = b"//Auto generated by osu2tja"

# song data
TITLE = b"NO TITLE"
SUBTITLE = b"NO SUBTITLE"
BPM = b"0.0" # use string copying
WAVE = b""
OFFSET = b"0.0" # use string copying
DEMOSTART = b"0.0" # use string copying
SONGVOL = b"100.0" # use string copying
SEVOL = b"100.0" # use string copying

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

def get_comm_data(filename: str) -> List[str]:
    assert isinstance(filename, str)
    assert filename.endswith(".tja")
    global TITLE, SUBTITLE, BPM, WAVE, OFFSET, DEMOSTART, SONGVOL, SEVOL
    try: fobj = open(filename, "rb")
    except IOError: tja2osu.rtassert(False, "can't open tja file.")
    if fobj.peek(len(codecs.BOM_UTF8)).startswith(codecs.BOM_UTF8):
        fobj.seek(len(codecs.BOM_UTF8)) # ignore UTF-8 BOM
    course_list: List[str] = []
    for line in fobj:
        line = line.strip()
        vname, _, vval = line.partition(b":")
        vname = vname.strip()
        vval = vval.strip()
        if vname == b"TITLE": TITLE = vval
        elif vname == b"SUBTITLE": SUBTITLE = vval
        elif vname == b"BPM": BPM = vval
        elif vname == b"WAVE": WAVE = vval
        elif vname == b"OFFSET": OFFSET = vval
        elif vname == b"DEMOSTART": DEMOSTART = vval
        elif vname == b"SONGVOL": SONGVOL = vval
        elif vname == b"SEVOL": SEVOL = vval
        elif vname == b"COURSE":
            vval_dec = get_course_by_number(vval)
            course_list.append(vval_dec)
    fobj.close()
    return course_list

def divide_diff(path_tja: str, dir_out: str) -> List[str]:
    assert isinstance(path_tja, str)
    fname, ext = os.path.splitext(os.path.basename(path_tja))
    assert ext == ".tja"

    course_list = get_comm_data(path_tja)
    file_list = [f"{fname} {x}.tja" for x in course_list]

    diff_data: List[bytes] = []
    started = False
    i = 0
    fobj = open(path_tja, "rb")
    bom = b""
    if fobj.peek(len(codecs.BOM_UTF8)).startswith(codecs.BOM_UTF8):
        bom = fobj.read(len(codecs.BOM_UTF8)) # extract UTF-8 BOM
    for line in fobj:
        line = line.strip()
        if b"#END" in line:
            diff_data.append(line)

            if i >= len(file_list):
                course_list.append(f"No{i}")
                file_list.append(f"{fname} No{i}.tja")

            fout = open(os.path.join(dir_out, file_list[i]), "wb")

            fout.write(bom + WATER_MARK + b"\n")
            fout.write(b"TITLE:%b\n" % (TITLE,))
            fout.write(b"SUBTITLE:%b\n" % (SUBTITLE,))
            fout.write(b"BPM:%b\n" % (BPM,))
            fout.write(b"WAVE:%b\n" % (WAVE,))
            fout.write(b"OFFSET:%b\n" % (OFFSET,))
            fout.write(b"DEMOSTART:%b\n" % (DEMOSTART,))
            fout.write(b"SONGVOL:%b\n" % (SONGVOL,))
            fout.write(b"SEVOL:%b\n" % (SEVOL,))
            fout.write(b"\n")
            fout.write(b"COURSE:%s\n" % (course_list[i].encode('latin1'),))

            for str_ in diff_data:
                fout.write(str_)
                fout.write(b"\n")
            fout.close()
            diff_data = []
            started = False
            i += 1
            continue

        if not started and b"#START" in line:
            started = True
        if started:
            diff_data.append(line)
    fobj.close()

    assert i == len(course_list), course_list

    return file_list

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
        if b"#BRANCHSTART" in line:
            has_branch = True
            continue
        if b"#BRANCHEND" in line \
            or b"#SECTION" in line:
            continue
        if b"#E" in line:
            which = "E"
        elif b"#N" in line:
            which = "N"
        elif (b"#M" in line) and (b"#MEASURE" not in line):
            which = "M"
        elif b"#BRANCHEND" in line:
            which = None
        else:
            _line = line.strip()
            vname, _, vval = _line.partition(b":")
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


def tja2osus(tja_path: str, target_path: str="out") -> None:
    dirname_dest, ext = os.path.splitext(os.path.basename(tja_path))
    dir_tmp = os.path.join("tmp", dirname_dest)
    os.makedirs(dir_tmp, exist_ok=True)
    all_file_list = []
    file_list = divide_diff(tja_path, dir_tmp)
    for diff_file in file_list:
        branch_file_list = divide_branch(os.path.join(dir_tmp, diff_file), dir_tmp)
        if len(branch_file_list) > 0:
            all_file_list.extend(branch_file_list)
        else:
            all_file_list.append(diff_file)

    dir_out = os.path.join(target_path, dirname_dest)
    os.makedirs(dir_out, exist_ok=True)
    old_stdout = sys.stdout
    for fname_tja in all_file_list:
        fname, ext = os.path.splitext(fname_tja)
        piece = fname.rsplit(None, 1)
        fname = piece[0] + "[" + piece[1] + "]"
        fout = open(os.path.join(dir_out, f"{fname}.osu"), "w")
        sys.stdout = fout
        module = reload(tja2osu)
        tja2osu.tja2osu(os.path.join(dir_tmp, fname_tja))
        fout.close()
        
        sys.stdout = old_stdout
        print("Generate:%s.osu" % fname, file=sys.stderr)

    try:
        wave_dec = tja2osu.convert_str(WAVE)
        path_wave_src = os.path.join(os.path.dirname(tja_path), wave_dec)
        path_wave_dest = os.path.join(dir_out, wave_dec)
        shutil.copyfile(path_wave_src, path_wave_dest)
    except FileNotFoundError:
        print(f"Audio file {path_wave_src} not found. Not copied.", file=sys.stderr)

if __name__ == "__main__":
    assert len(sys.argv) > 1
    tja2osus(sys.argv[1])

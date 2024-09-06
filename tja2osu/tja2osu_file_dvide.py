from importlib import reload
import sys
import os
import tja2osu

WATER_MARK = "//Auto generated by osu2tja"

# song data
TITLE = "NO TITLE"
SUBTITLE = "NO SUBTITLE"
BPM = 0.0
WAVE = ""
OFFSET = 0.0
DEMOSTART = 0.0

def get_course_by_number(str_):
    if not str_.isdigit():
        return str_
    num = int(str_)
    if num <= 0: return "Easy"
    elif num == 1: return "Normal"
    elif num == 2: return "Hard"
    elif num == 3: return "Oni"
    else: return "Oni%d" % (num-3)

def get_comm_data(filename):
    assert isinstance(filename, str)
    assert filename.endswith(".tja")
    global TITLE, SUBTITLE, BPM, WAVE, OFFSET
    try: fobj = open(filename, "rb")
    except IOError: tja2osu.rtassert(False, "can't open tja file.")
    if fobj.peek(3) == "".encode("utf-8-sig"):
        fobj.seek(3) # ignore UTF-8 BOM
    course_list = []
    for line in fobj:
        line = line.strip()
        try: i = line.index(b":")
        except ValueError: continue
        vname = line[:i].strip()
        vval = line[i+1:].strip()
        if vname == b"TITLE": TITLE = tja2osu.convert_str(vval)
        elif vname == b"SUBTITLE": SUBTITILE = tja2osu.convert_str(vval)
        elif vname == b"BPM": BPM = vval.decode("latin-1")
        elif vname == b"WAVE": WAVE = tja2osu.convert_str(vval)
        elif vname == b"OFFSET": OFFSET = vval.decode("latin-1")
        elif vname == b"DEMOSTART": DEMOSTART = vval.decode("latin-1")
        elif vname == b"COURSE":
            vval = get_course_by_number(vval.decode("latin-1"))
            course_list.append(vval)
    fobj.close()
    return course_list

def divide_diff(filename):
    assert isinstance(filename, str)
    assert filename.endswith(".tja")

    course_list = get_comm_data(filename)
    file_list = [filename[:-4]+" "+x+".tja" for x in course_list]

    diff_data = []
    started = False
    i = 0
    fobj = open(filename, "rb")
    if fobj.peek(3) == "".encode("utf-8-sig"):
        fobj.seek(3) # ignore UTF-8 BOM
    for line in fobj:
        line = line.strip()
        if b"#END" in line:
            diff_data.append(line.decode("latin1"))

            if i >= len(file_list):
                course_list.append("No%d" % i)
                file_list.append(filename[:-4]+ (" No%d" % i) + ".tja")

            # convert to UTF-8-BOM TJA for easier encoding handling
            # only compatible with newer simulators such as TJAPlayer3 and taiko-web
            fout = open(os.path.join("tmp", file_list[i]), "w", encoding="utf-8-sig")

            print(WATER_MARK, file=fout)
            print("TITLE:", TITLE, file=fout)
            print("SUBTITLE:", SUBTITLE, file=fout)
            print("BPM:", BPM, file=fout)
            print("WAVE:", WAVE, file=fout)
            print("OFFSET:", OFFSET, file=fout)
            print("DEMOSTART:", DEMOSTART, file=fout)
            print("", file=fout)
            print("COURSE:", course_list[i] , file=fout)

            for str_ in diff_data: print(str_, file=fout)
            fout.close()
            diff_data = []
            started = False
            i += 1
            continue

        if not started and b"#START" in line:
            started = True
        if started:
            diff_data.append(line.decode("latin1"))
    fobj.close()

    assert i == len(course_list), course_list

    return file_list

def divide_branch(filename):
    assert isinstance(filename, str)
    assert filename.endswith(".tja")
    try: fobj = open(os.path.join("tmp", filename), "rb")
    except IOError: assert False, "can't open tja file."
    if fobj.peek(3) == "".encode("utf-8-sig"):
        fobj.seek(3) # ignore UTF-8 BOM
    branch_data = [[], [], []]
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
            try: i = _line.index(b":")
            except ValueError: continue
            vname = _line[:i].strip()
            vval = _line[i+1:].strip()
            if vname == b"COURSE":
                vval_str = vval.decode("latin1")
                branch_data[0].append("COURSE:" + vval_str + "(Kurouto)")
                branch_data[1].append("COURSE:" + vval_str + "(Futsuu)")
                branch_data[2].append("COURSE:" + vval_str + "(Tatsujin)")
                continue

            line_str = line.decode("latin1")
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

    file_list = [filename[:-4]+"(Kurouto).tja", filename[:-4]+"(Futsuu).tja",
            filename[:-4]+"(Tatsujin).tja"]
    i = 0
    for f in file_list:
        # convert to UTF-8-BOM TJA for easier encoding handling
        # only compatible with newer simulators such as TJAPlayer3 and taiko-web
        fout = open(os.path.join("tmp", f), "w", encoding="utf-8-sig")
        print(WATER_MARK, file=fout)
        for str_ in branch_data[i]:
            print(str_, file=fout)
        fout.close()
        i += 1

    return file_list


def divide_tja(filename):
    try:
        os.mkdir("tmp")
    except FileExistsError:
        pass
    all_file_list = []
    file_list = divide_diff(filename)
    for diff_file in file_list:
        branch_file_list = divide_branch(diff_file)
        if len(branch_file_list) > 0:
            all_file_list.extend(branch_file_list)
        else:
            all_file_list.append(diff_file)
            
    try:
        os.mkdir("out")
    except FileExistsError:
        pass
    old_stdout = sys.stdout
    for all_ready_file in all_file_list:
        name = all_ready_file[:-4]
        piece = name.rsplit(None, 1)
        name = piece[0] + "[" + piece[1] + "]"
        fout = open(os.path.join("out", "%s.osu" % (name,)) ,"w")
        sys.stdout = fout
        module = reload(tja2osu)
        tja2osu.tja2osu(os.path.join("tmp", all_ready_file))
        fout.close()
        
        sys.stdout = old_stdout
        print("Generate:%s.osu" % name, file=sys.stderr)

if __name__ == "__main__":
    assert len(sys.argv) > 1
    divide_tja(sys.argv[1])
    

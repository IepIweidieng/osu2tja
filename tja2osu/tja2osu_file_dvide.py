from importlib import reload
import sys
import os
import tja2osu

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
    try: fobj = open(filename)
    except IOError: tja2osu.rtassert(False, "can't open tja file.")
    course_list = []
    for line in fobj:
        line = line.strip()
        try: i = line.index(":")
        except ValueError: continue
        vname = line[:i].strip()
        vval = line[i+1:].strip()
        if vname == "TITLE": TITLE = vval
        elif vname == "SUBTITLE": SUBTITILE = vval
        elif vname == "BPM": BPM = vval
        elif vname == "WAVE": WAVE = vval
        elif vname == "OFFSET": OFFSET = vval
        elif vname == "DEMOSTART": DEMOSTART = vval
        elif vname == "COURSE":
            vval = get_course_by_number(vval)
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
    for line in open(filename):
        line = line.strip()
        if "#END" in line:
            diff_data.append(line)

            if i >= len(file_list):
                course_list.append("No%d" % i)
                file_list.append(filename[:-4]+ (" No%d" % i) + ".tja")
                
            fout = open(os.path.join("tmp", file_list[i]), "w")

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

        if not started and "#START" in line:
            started = True
        if started:
            diff_data.append(line)

    assert i == len(course_list), course_list

    return file_list

def divide_branch(filename):
    assert isinstance(filename, str)
    assert filename.endswith(".tja")
    try: fobj = open(os.path.join("tmp", filename))
    except IOError: assert False, "can't open tja file."
    branch_data = [[], [], []]
    which = None

    has_branch = False
    for line in fobj:
        line = line.strip()
        if "#BRANCHSTART" in line:
            has_branch = True
            continue
        if "#BRANCHEND" in line \
            or "#SECTION" in line:
            continue
        if "#E" in line:
            which = "E"
        elif "#N" in line:
            which = "N"
        elif ("#M" in line) and ("#MEASURE" not in line):
            which = "M"
        elif "#BRANCHEND" in line:
            which = None
        else:
            _line = line.strip()
            try: i = _line.index(":")
            except ValueError: pass
            vname = _line[:i].strip()
            vval = _line[i+1:].strip()
            if vname == "COURSE":
                branch_data[0].append("COURSE:"+vval+"(Kurouto)")
                branch_data[1].append("COURSE:"+vval+"(Futsuu)")
                branch_data[2].append("COURSE:"+vval+"(Tatsujin)")
                continue

            if which == None:
                branch_data[0].append(line)
                branch_data[1].append(line)
                branch_data[2].append(line)
            elif which == "E":
                branch_data[0].append(line)
            elif which == "N":
                branch_data[1].append(line)                
            elif which == "M":
                branch_data[2].append(line)                
            else:
                assert False
    fobj.close()
    if not has_branch:
        return []

    file_list = [filename[:-4]+"(Kurouto).tja", filename[:-4]+"(Futsuu).tja",
            filename[:-4]+"(Tatsujin).tja"]
    i = 0
    for f in file_list:
        fout = open(os.path.join("tmp", f), "w")
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
        print("Generate:%s.osu" % name)

if __name__ == "__main__":
    assert len(sys.argv) > 1
    divide_tja(sys.argv[1])
    

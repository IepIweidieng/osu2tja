#from niceui import ui
from osu2tja.osu2tja import osu2tja, get_var
from contextlib import redirect_stdout
from shutil import copyfile
import subprocess
import os
import pathlib
import glob
import zipfile
import codecs

if __name__ == "__main__":
    print("osu2tja")
    print("forked by @fragment_mlk")
    while True:
        try:
            path = input("> ").replace('"', "")
            if path == "exit":
                exit()
            else:
                path = pathlib.Path(path)
        except Exception:
            print("error.")
            continue
        # check filename
        if not path.suffix in ".osu":
            print("Input file should be Osu file!(*.osu): \n\t[[ %s ]]" % path)
            continue
        # try to open file
        try:
            fp = codecs.open(path, "r", "utf8")
        except Exception:
            print("Can't open file `%s`" % path)

        title = ""
        audio = ""
        for line in fp:
            line = line.strip()
            if line == "":
                continue
            vname, vval = get_var(line)
            if vname in "AudioFilename":
                audio = vval or audio
            if vname in ("Title", "TitleUnicode"):
                title = vval or title
            elif vname not in ("Title", "TitleUnicode") and title != "":
                break
            else:
                continue

        song_dir = os.path.join("../songs", title)
        audio_file = os.path.join(path.parent, audio)
        tja_file = os.path.join(song_dir, title+".tja")
        if not os.path.exists(song_dir):
            os.makedirs(song_dir)
        print(f"convert {path} -> {tja_file} ...")
        with open(tja_file, "w") as f:
            with redirect_stdout(f):
                osu2tja(path)
            print("convert finished.")
        root, ext = os.path.splitext(audio)
        song_file = os.path.join(song_dir, root+".ogg")
        if ext != ".ogg":
            print(f"convert {audio_file} -> {song_file} ...")
            with redirect_stdout(open(os.devnull, 'w')):
                proc = subprocess.run(f'ffmpeg -i "{audio_file}" "{song_file}"', stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("convert finished.")
        else:
            print(f"copy {audio_file} -> {song_file} ...")
            copyfile(audio_file, song_file)
            print("copy finished.")


from osu2tja.osu2tja import osu2tja, reset_global_variables
from zipfile import ZipFile, is_zipfile
from typing import Dict, List
from os import path
import os
import optparse
from io import TextIOWrapper
import subprocess


def extract_osu_file_info(file) -> Dict[str, object]:
    result: Dict[str, object] = dict()
    for line in file:
        if line == "[Difficulty]":
            break

        if line.startswith("Version:"):
            result["version"] = line.split(":")[1].strip()
        elif line.startswith("OverallDifficulty:"):
            result["difficulty"] = float(line.split(":")[1])
        elif line.startswith("Title:") and "title" not in result:
            result["title"] = line.split(":")[1].strip()
        elif line.startswith("TitleUnicode:"):
            result["title"] = line.split(":")[1].strip()
        elif line.startswith("AudioFilename:"):
            result["audio"] = line.split(":")[1].strip()

        if len(result.keys()) == 4:
            break
    return result


def convert_to_ogg(audio_root: str, audio_name: str) -> str:
    fname, ext = os.path.splitext(audio_name)
    audio_name_ogg = f"{fname}.ogg"
    audio_path = os.path.join(audio_root, audio_name)
    audio_path_ogg = os.path.join(audio_root, audio_name_ogg)

    if ext != ".ogg":
        print(f"Converting {audio_path} -> {audio_path_ogg} ...")
        proc = subprocess.run(["ffmpeg", "-i", audio_path, audio_path_ogg], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if proc.returncode == 0:
            os.remove(audio_path) # no longer needed
            print("Convert Audio Done!")
            return audio_name_ogg

        print("Convert audio failed. Please verify whether ffmpeg has been properly installed. Continued.")
    return audio_name


def convert(source_path: str, target_path: str) -> None:
    if not is_zipfile(source_path):
        print(f"{source_path} is not a zip file")
        return

    osu_zip: ZipFile = ZipFile(source_path, "r")
    osu_files = [filename for filename in osu_zip.namelist()
                 if filename.endswith(".osu")]
    osu_infos = list()
    for filename in osu_files:
        fp = TextIOWrapper(osu_zip.open(filename, "r"), encoding="utf-8")
        osu_info = extract_osu_file_info(fp)
        fp.close()
        osu_info["filename"] = filename
        osu_infos.append(osu_info)
    original_audio_name = osu_infos[0]["audio"]
    title = osu_infos[0]["title"]
    new_audio_name = title + \
        path.splitext(original_audio_name)[-1]

    # interactive mode, show all difficulties to user
    print("====== Difficulties Selection ======")
    print("Index\tDifficulty\tVersion")
    osu_infos.sort(key=lambda x: x["difficulty"], reverse=True)
    for i, osu_info in enumerate(osu_infos):
        print(f"({i}):\t{osu_info['difficulty']}\t{osu_info['version']}")

    print()
    print("Please select difficulties(-1 if not available):")
    diff_names = ["Easy", "Normal", "Hard", "Oni", "Edit"]
    diff_indexes = [-1, -1, -1, -1, -1]
    for diff in range(4, -1, -1):
        diff_indexes[diff] = int(input(f"{diff_names[diff]}:"))

    # extract audio first
    storage_path = path.join(target_path, title)
    os.makedirs(storage_path)
    osu_zip.extract(original_audio_name, storage_path)
    audio_path_orig = path.join(storage_path, original_audio_name)
    audio_path_new = path.join(storage_path, new_audio_name)
    if audio_path_new != audio_path_orig:
        print(f"Renaming {audio_path_orig} -> {audio_path_new} ...")
        os.rename(audio_path_orig, audio_path_new)
    print("Extract Audio Done!")
    new_audio_name = convert_to_ogg(storage_path, new_audio_name)

    head = []
    diff_contents: List[List[str]] = [[], [], [], [], []]
    for diff in range(4, -1, -1):
        if diff_indexes[diff] != -1:
            reset_global_variables()
            diff_index = diff_indexes[diff]
            with TextIOWrapper(
                    osu_zip.open(osu_infos[diff_index]["filename"]),
                    encoding="utf-8") as diff_fp:
                level = int(osu_infos[diff_index]["difficulty"])
                head, diff_contents[diff] = osu2tja(diff_fp, diff_names[diff], level, new_audio_name)

    # saving tja
    with open(path.join(storage_path, title+".tja"), "w+") as f:
        f.write("\n".join(head))
        for diff in range(4, -1, -1):
            if diff_indexes[diff] != -1:
                f.write("\n")
                f.write("\n".join(diff_contents[diff]))
    print("Tja converted!")
    osu_zip.close()


if __name__ == "__main__":
    parser = optparse.OptionParser()
    (options, args) = parser.parse_args()
    convert(args[0], args[1])

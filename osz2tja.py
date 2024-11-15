from osu2tja.osu2tja import OSU_VER_STR_PREFIX, osu2tja, osu2tja_level, reset_global_variables
from tja2osu.tja2osu_file_dvide import divide_tja  # Use divide_tja for tja2osz conversion
from zipfile import ZipFile, is_zipfile
from typing import Dict, List
from os import path
import os
import sys
from io import TextIOWrapper
import subprocess

def extract_osu_file_info(file) -> Dict[str, object]:
    result: Dict[str, object] = dict()
    for line in file:
        if line == "[Difficulty]":
            break

        if line.startswith(OSU_VER_STR_PREFIX) and "format_ver" not in result:
            result["format_ver"] = int(line.split("v")[1].strip())
        elif line.startswith("Version:"):
            result["version"] = line.split(":")[1].strip()
        elif line.startswith("OverallDifficulty:"): # accuracy, not the real star rating
            result["difficulty"] = float(line.split(":")[1])
        elif line.startswith("Title:"):
            result["title_ascii"] = line.split(":")[1].strip()
            if "title" not in result:
                result["title"] = result["title_ascii"]
        elif line.startswith("TitleUnicode:"):
            result["title"] = line.split(":")[1].strip()
        elif line.startswith("AudioFilename:"):
            result["audio"] = line.split(":")[1].strip()

        if all((key in result) for key in ["format_ver", "version", "difficulty", "title", "audio"]):
            break
    return result


def convert_to_ogg(audio_root: str, audio_name: str) -> str:
    fname, ext = os.path.splitext(audio_name)
    audio_name_ogg = f"{fname}.ogg"
    audio_path = os.path.join(audio_root, audio_name)
    audio_path_ogg = os.path.join(audio_root, audio_name_ogg)

    if ext.lower() != ".ogg":
        print(f"Converting {audio_path} -> {audio_path_ogg} ...")
        for ffmpeg in ["ffmpeg", "./ffmpeg", "./ffmpeg.exe"]:
            try:
                proc = subprocess.run([ffmpeg, "-i", audio_path, audio_path_ogg, "-hide_banner", "-loglevel", "error"])
                if proc.returncode == 0:
                    os.remove(audio_path) # no longer needed
                    print("Convert Audio Done!")
                    return audio_name_ogg
                print(proc.stderr)
                print("Convert audio failed. Continued.")
                break
            except FileNotFoundError:
                continue
        else:
            print("Cannot found ffmpeg. Will not convert to `.ogg`.")

    return audio_name

bad_chars_for_path = {'\\', '/', ':', '*', '?', '"', '<', '>', '|', '.', '{', '}'}


def convert_osz2tja(source_path: str, target_path: str) -> None:
    warnings = []  # List to store warnings
    try:
        if not is_zipfile(source_path):
            raise ValueError(f"{source_path} is not a valid zip file")

        osu_zip: ZipFile = ZipFile(source_path, "r")
        osu_files = [filename for filename in osu_zip.namelist() if filename.endswith(".osu")]
        if not osu_files:
            raise ValueError(f"No .osu files found in {source_path}")

        osu_infos = list()
        for filename in osu_files:
            fp = TextIOWrapper(osu_zip.open(filename, "r"), encoding="utf-8")
            osu_info = extract_osu_file_info(fp)
            fp.close()
            osu_info["filename"] = filename
            osu_infos.append(osu_info)

        osu_infos.sort(key=lambda x: x["difficulty"])  # Sort from easiest to hardest

        n_diffs_max_per_tja = 5
        will_split_tja = (len(osu_infos) > n_diffs_max_per_tja)

        for folder_num, start_idx in enumerate(range(0, len(osu_infos), n_diffs_max_per_tja)):
            # Get the subset of difficulties for this folder
            selected_infos = osu_infos[start_idx:start_idx + n_diffs_max_per_tja]

            # Determine folder name
            title = selected_infos[0]["title"]  # Use the title of the first map for naming
            title_for_path = ''.join((
                ch if ch not in bad_chars_for_path else '_'
                for ch in selected_infos[0]["title_ascii"]))
            folder_name = f"{title_for_path} - {folder_num + 1}" if will_split_tja else title_for_path

            # Extract audio first
            info = selected_infos[0]
            storage_path = path.join(target_path, folder_name)
            os.makedirs(storage_path, exist_ok=True)
            osu_zip.extract(info["audio"], storage_path)
            info["audio"] = convert_to_ogg(storage_path, info["audio"])

            # Adjust difficulties for this folder
            difficulties = ["Edit", "Oni", "Hard", "Normal", "Easy"]
            if len(selected_infos) <= 4:
                difficulties = difficulties[1:1+len(selected_infos)]

            head_meta: List[str] = []
            head_sync_main: List[str] = []
            head_syncs: Dict[str, List[str]] = {diff: [] for diff in difficulties}
            head_diffs: Dict[str, List[str]] = {diff: [] for diff in difficulties}
            diff_contents: Dict[str, List[str]] = {diff: [] for diff in difficulties}

            # process in descending difficulties
            # Note: `selected_infos` is in ascending OverallDifficulty
            for diff, info in zip(difficulties, reversed(selected_infos)):
                try:
                    reset_global_variables()
                    with TextIOWrapper(osu_zip.open(info["filename"]), encoding="utf-8") as diff_fp:
                        level = int(info["difficulty"] + folder_num)  # Progressive scaling of stars
                        head_meta, head_syncs[diff], head_diffs[diff], diff_contents[diff] = (
                            osu2tja(diff_fp, diff, level, info["audio"])
                        )
                        if len(head_sync_main) == 0:
                            head_sync_main = head_syncs[diff]
                            print(f"main sync headers: {head_sync_main}")
                        elif head_syncs[diff] != head_sync_main:
                            print(f"Warning: Generated a different sync header for {diff}: {head_syncs[diff]}")
                except Exception as e:
                    warning_message = f"Error processing difficulty {diff}: {e}"
                    print(warning_message)
                    warnings.append(warning_message)  # Track warnings for non-fatal errors

            # Save .tja file
            with open(path.join(storage_path, f"{folder_name}.tja"), "w+") as f:
                f.write("\n".join(head_meta))
                f.write("\n")
                f.write("\n".join(head_sync_main))
                f.write("\n")
                for diff in difficulties:
                    if diff_contents[diff]:
                        f.write("\n")
                        f.write("\n".join(head_diffs[diff]))
                        f.write("\n")
                        f.write("\n".join(head_syncs[diff]))
                        f.write("\n\n")
                        f.write("\n".join(diff_contents[diff]))
                        f.write("\n")

            print(f"Converted {folder_name} to TJA")

        osu_zip.close()

        # If there are warnings, notify the user in the console
        if warnings:
            print("\nWarning: Some maps may have possible errors due to the following issues:")
            for warning in warnings:
                print(f"- {warning}")

    except Exception as e:
        raise RuntimeError(f"Error converting {source_path}: {e}")

def batch_convert_osz2tja(input_folder: str, output_folder: str):
    skipped_files = []
    for filename in os.listdir(input_folder):
        if filename.endswith(".osz"):
            source_path = path.join(input_folder, filename)
            try:
                convert_osz2tja(source_path, output_folder)
            except Exception as e:
                print(f"Skipping {filename} due to error: {e}")
                skipped_files.append(filename)

    if skipped_files:
        print("\nSkipped files:")
        for file in skipped_files:
            print(f"- {file}")

def batch_convert_tja2osz(input_folder: str, output_folder: str):
    for filename in os.listdir(input_folder):
        if filename.endswith(".tja"):
            try:
                divide_tja(path.join(input_folder, filename))
                print(f"Converted {filename} to OSZ")
            except Exception as e:
                print(f"Error converting {filename}: {e}")

if __name__ == "__main__":
    print("Select conversion mode:")
    print("1. osz2tja (default)")
    print("2. tja2osz (not implemented)")
    choice = input("Enter 1 or 2: ")

    # Set default input and output folders
    input_folder = "Songs"
    output_folder = "Output"

    # Check for command-line arguments
    if len(sys.argv) > 1:
        input_folder = sys.argv[1]  # Override input folder if provided
    if len(sys.argv) > 2:
        output_folder = sys.argv[2]  # Override output folder if provided

    print(f"Input folder: {input_folder}")
    print(f"Output folder: {output_folder}")

    if choice == "2":
        batch_convert_tja2osz(input_folder, output_folder)
    else:
        batch_convert_osz2tja(input_folder, output_folder)

    input("\nPress enter to exit...")
    sys.exit(0)

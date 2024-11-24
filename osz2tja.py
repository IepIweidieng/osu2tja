import argparse
import shutil
import textwrap
import traceback
from common.utils import print_with_pended, print_pend, print_unpend
from osu2tja.osu2tja import OSU_VER_STR_PREFIX, osu2tja, osu2tja_level, reset_global_variables
from tja2osu.tja2osu_file_dvide import tja2osus
from zipfile import ZipFile, is_zipfile
from typing import Dict, List, Literal
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
            result["format_ver"] = int(line.partition(OSU_VER_STR_PREFIX)[2].strip())
            continue

        key, _, val = line.partition(":")
        if key == "Version":
            result["version"] = val.strip()
        elif key == "OverallDifficulty": # accuracy, not the real star rating
            result["difficulty"] = float(val)
        elif key == "Title":
            result["title_ascii"] = val.strip()
            if "title" not in result:
                result["title"] = result["title_ascii"]
        elif key == "TitleUnicode":
            result["title"] = val.strip()
        elif key == "AudioFilename":
            result["audio"] = val.strip()

        if all((key in result) for key in ["format_ver", "version", "difficulty", "title", "audio"]):
            break
    return result


def convert_to_ogg(audio_root: str, audio_name: str) -> str:
    fname, ext = os.path.splitext(audio_name)
    audio_name_ogg = f"{fname}.ogg"
    audio_path = os.path.join(audio_root, audio_name)
    audio_path_ogg = os.path.join(audio_root, audio_name_ogg)

    if ext.lower() != ".ogg":
        if os.path.exists(audio_path_ogg):
            return audio_name_ogg
        print(f"Converting `{audio_path}` -> `{audio_path_ogg}` ...", end="", flush=True)
        print_pend()
        for ffmpeg in ["ffmpeg", "./ffmpeg", "./ffmpeg.exe"]:
            try:
                proc = subprocess.run([ffmpeg, "-i", audio_path, audio_path_ogg, "-hide_banner", "-loglevel", "error"])
                if proc.returncode == 0:
                    os.remove(audio_path) # no longer needed
                    print_unpend()
                    print(f"\rConverting `{audio_path}` -> `{audio_path_ogg}` done!")
                    return audio_name_ogg
                print_with_pended(proc.stderr, file=sys.stderr)
                print("Convert audio failed. Continued.", file=sys.stderr)
                break
            except FileNotFoundError:
                continue
        else:
            print_with_pended("Cannot found ffmpeg. Will not convert to `.ogg`.", file=sys.stderr)

    return audio_name

bad_chars_for_path = {'\\', '/', ':', '*', '?', '"', '<', '>', '|', '.', '{', '}'}


def convert_osz2tja(osus_fpath: str, target_path: str) -> None:
    if not is_zipfile(osus_fpath):
        raise ValueError(f"{osus_fpath} is not a valid zip file")
    osus_fname = os.path.basename(osus_fpath)

    osu_zip: ZipFile = ZipFile(osus_fpath, "r")
    osu_files = [filename for filename in osu_zip.namelist() if filename.endswith(".osu")]
    if not osu_files:
        raise ValueError(f"No .osu files found in {osus_fpath}")

    osu_infos_by_song: Dict[str, List] = {}
    for filename in osu_files:
        fp = TextIOWrapper(osu_zip.open(filename, "r"), encoding="utf-8")
        osu_info = extract_osu_file_info(fp)
        fp.close()
        osu_info["filename"] = filename
        assert type(osu_info["audio"]) == str
        osu_infos_by_song.setdefault(osu_info["audio"], []).append(osu_info)

    osu_info_first = next(iter(osu_infos_by_song.values()))[0]
    title = osu_info_first["title"] # Use the title of the first map for naming
    title_for_path = ''.join((
        ch if ch not in bad_chars_for_path else '_'
        for ch in osu_info_first["title_ascii"]))

    n_diffs_max_per_tja = 5
    will_split_tja = (
        len(osu_infos_by_song.keys()) > 1
        or any((len(infos) > n_diffs_max_per_tja for infos in osu_infos_by_song.values()))
    )

    n_tjas = 0
    for song_audio, osu_infos in osu_infos_by_song.items():
        osu_infos.sort(key=lambda x: x["difficulty"])
        for start_idx in range(0, len(osu_infos), n_diffs_max_per_tja):
            # Get the subset of difficulties for this folder
            selected_infos = osu_infos[start_idx:start_idx + n_diffs_max_per_tja]

            # 1 directory per .tja file for maximum compatibility
            n_tjas += 1
            folder_name = f"{title_for_path} - {n_tjas}" if will_split_tja else title_for_path

            # Extract audio first
            storage_path = path.join(target_path, folder_name)
            os.makedirs(storage_path, exist_ok=True)
            try:
                osu_zip.extract(song_audio, storage_path)
                song_audio_tja = convert_to_ogg(storage_path, song_audio)
            except KeyError:
                print(f"Warning: song audio `{song_audio}` not found. Neither copied nor converted.", file=sys.stderr)
                song_audio_tja = song_audio

            tja_fname = f"{folder_name}.tja"
            tja_fpath = path.join(storage_path, tja_fname)
            print(f"Converting `{osus_fname}` to `{tja_fname}` ...", end="", flush=True)
            print_pend()

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
            head_sync_main_printed = False
            for diff, info in zip(difficulties, reversed(selected_infos)):
                try:
                    reset_global_variables()
                    with TextIOWrapper(osu_zip.open(info["filename"]), encoding="utf-8") as diff_fp:
                        level = int(info["difficulty"])
                        head_meta, head_syncs[diff], head_diffs[diff], diff_contents[diff] = (
                            osu2tja(diff_fp, diff, level, song_audio_tja)
                        )
                        if len(head_sync_main) == 0:
                            head_sync_main = head_syncs[diff]
                        elif head_syncs[diff] != head_sync_main:
                            if not head_sync_main_printed:
                                print_with_pended(f"Warning: Main sync headers: {head_sync_main}", file=sys.stderr)
                                head_sync_main_printed = True
                            print(f"Warning: Generated a different sync header for {diff}: {head_syncs[diff]}", file=sys.stderr)
                except Exception:
                    print_with_pended(traceback.format_exc(), file=sys.stderr)
                    print(f"Error processing {diff} [{info['version']}] difficulty of `{folder_name}`. Continued.", file=sys.stderr)

            # Save .tja file
            with open(tja_fpath, "w+") as f:
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

            print_unpend()
            print(f"\rConverting `{osus_fname}` to `{tja_fname}` done!")

    osu_zip.close()

def batch_convert_osz2tja(input_folder: str, output_folder: str):
    skipped_files = []
    for filename in os.listdir(input_folder):
        if filename.endswith(".osz"):
            source_path = path.join(input_folder, filename)
            try:
                convert_osz2tja(source_path, output_folder)
                print(f"Converted `{filename}` to TJAs.")
            except Exception:
                traceback.print_exc()
                print(f"Error converting `{source_path}`. Continued.", file=sys.stderr)
                skipped_files.append(source_path)

    if skipped_files:
        print("\nSkipped files:")
        for file in skipped_files:
            print(f"- {file}")

def batch_convert_tja2osz(input_folder: str, output_folder: str):
    skipped_files = []
    for dirpath, dirnames, names in os.walk(input_folder):
        for filename in names:
            path_tja = os.path.join(dirpath, filename)
            fname, ext = os.path.splitext(filename)
            if ext != ".tja":
                continue
            try:
                tja2osus(path_tja, output_folder)
                dir_out = os.path.join(output_folder, fname)
                print(f"Converted `{path_tja}` to `{fname}/*.osu`s.")
                shutil.make_archive(dir_out, 'zip', dir_out)
                os.rename(f"{dir_out}.zip", f"{dir_out}.osz")
                print(f"Converted `{dir_out}/` to `{fname}.osz`.")
            except Exception:
                traceback.print_exc()
                print(f"Error converting `{path_tja}`. Continued.", file=sys.stderr)
                skipped_files.append(path_tja)

    if skipped_files:
        print("\nSkipped files:")
        for file in skipped_files:
            print(f"- {file}")

def osz2tja2osz_main(mode: Literal['osz2tja', 'tja2osz']) -> None:
    ext_in = '.tja' if mode == 'tja2osz' else '.osz'
    ext_out = '.osu' if mode == 'tja2osz' else '.tja'
    parser = argparse.ArgumentParser(
        description=textwrap.dedent(f'''\
        Convert {ext_in} files to {ext_out} files and copy the audio to "<output_folder>/<song_folder>/".
        {'.osz files are also created in "<output_folder>/".' if mode == 'tja2osz' else ''}
        '''),
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('input_folder', nargs='?', default='Songs',
        help=f'where your {ext_in} files are located (default: Songs)')
    parser.add_argument('output_folder', nargs='?', default='Output',
        help=f'where the converted {ext_out} files will be saved (default: Output)')
    args = parser.parse_args()

    print(f"Input folder: {args.input_folder}")
    print(f"Output folder: {args.output_folder}")

    if mode == "tja2osz":
        batch_convert_tja2osz(args.input_folder, args.output_folder)
    else:
        batch_convert_osz2tja(args.input_folder, args.output_folder)

if __name__ == "__main__":
    osz2tja2osz_main('osz2tja')

from common.osu import OSU_VER_STR_PREFIX, get_diffrank_by_name
from common.tja import get_course_by_number
from common.utils import print_with_pended, print_pend, print_unpend
from osu2tja.osu2tja import osu2tja
from tja2osu.tja2osu_file_dvide import tja2osus

import argparse
import shutil
import textwrap
import traceback
from zipfile import ZipFile, is_zipfile
from typing import Dict, List, Literal, Tuple
from os import path
import os
import sys
from io import TextIOWrapper
import subprocess

def extract_osu_file_info(file) -> Dict[str, object]:
    result: Dict[str, object] = dict()
    for lineno, line in enumerate(file):
        try:
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
            elif key == "Mode":
                result["mode"] = int(val)

            if all((key in result) for key in ["format_ver", "version", "difficulty", "title", "audio", "mode"]):
                break
        except Exception:
            print_with_pended(traceback.format_exc(), file=sys.stderr)
            print_with_pended(f"Error parsing header in `{file.name}` at line {lineno}: `{line}`. Continued.", file=sys.stderr)

    return result


def get_ogg_path(audio_root: str, audio_name: str) -> Tuple[str, str, str]:
    fname, ext = os.path.splitext(audio_name)
    audio_name_ogg = f"{fname}.ogg"
    audio_path_ogg = os.path.join(audio_root, audio_name_ogg)
    return ext, audio_name_ogg, audio_path_ogg


def convert_to_ogg(audio_root: str, audio_name: str) -> str:
    ext, audio_name_ogg, audio_path_ogg = get_ogg_path(audio_root, audio_name)
    audio_path = os.path.join(audio_root, audio_name)
    if ext.lower() != ".ogg":
        if os.path.exists(audio_path_ogg):
            os.remove(audio_path) # no longer needed
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


n_diffs_max_per_tja = 5

def get_rank_type_error(diffranks: List[float], difftypes: List[int]) -> float:
    return sum((diffrank - difftype) ** 2 for diffrank, difftype in zip(diffranks, difftypes))

def get_best_difftypes(diffranks: List[float]) -> List[int]:
    # try add difficulty gaps and find the best fit
    # final best
    difftypes = [n_diffs_max_per_tja - 1 - i for i in range(len(diffranks))]
    error = get_rank_type_error(diffranks, difftypes)
    for _ in range(n_diffs_max_per_tja - len(diffranks)):
        # best for current gap count
        difftypes_i = difftypes[:]
        error_i = error
        has_gap_i = False
        for idx_gap in range(len(diffranks)):
            # value for current gap
            difftypes_j = [v - 1 if i >= idx_gap else v for i, v in enumerate(difftypes)]
            error_j = get_rank_type_error(diffranks, difftypes_j)
            if error_j <= error_i:
                difftypes_i = difftypes_j
                error_i = error_j
                has_gap_i = True
        if not has_gap_i:
            break
        else:
            difftypes = difftypes_i
            error = error_i

    return difftypes


def convert_osz2tja(osus_fpath: str, target_path: str) -> None:
    if not is_zipfile(osus_fpath):
        raise ValueError(f"{osus_fpath} is not a valid zip file")
    osus_fname = os.path.basename(osus_fpath)

    osu_zip: ZipFile = ZipFile(osus_fpath, "r")
    osu_files = [filename for filename in osu_zip.namelist() if filename.endswith(".osu")]
    if not osu_files:
        raise ValueError(f"No .osu files found in {osus_fpath}")

    osu_infos_by_song: Dict[Tuple[str, int], List] = {}
    for filename in osu_files:
        fp = TextIOWrapper(osu_zip.open(filename, "r"), encoding="utf-8")
        osu_info = extract_osu_file_info(fp)
        fp.close()
        osu_info["filename"] = filename
        osu_info["audio"] = osu_info["audio"] or ""
        osu_info["mode"] = osu_info["mode"] or 0
        assert type(osu_info["audio"]) == str and type(osu_info["mode"]) == int
        osu_infos_by_song.setdefault((osu_info["audio"], osu_info["mode"]), []).append(osu_info)

    osu_info_first = next(iter(osu_infos_by_song.values()))[0]
    title = osu_info_first["title"] # Use the title of the first map for naming
    title_for_path = ''.join((
        ch if ch not in bad_chars_for_path else '_'
        for ch in osu_info_first["title_ascii"]))

    will_split_tja = (
        len(osu_infos_by_song) > 1
        or any((len(infos) > n_diffs_max_per_tja for infos in osu_infos_by_song.values()))
    )

    n_tjas = 0
    for (song_audio, game_mode), osu_infos in osu_infos_by_song.items():
        for osu_info in osu_infos:
            osu_info["diffrank"] = get_diffrank_by_name(osu_info["version"])
        osu_infos.sort(key=lambda x: (x["diffrank"], x["difficulty"]))
        for start_idx in range(0, len(osu_infos), n_diffs_max_per_tja):
            # Get the subset of difficulties for this folder
            selected_infos = osu_infos[start_idx:start_idx + n_diffs_max_per_tja]

            # 1 directory per .tja file for maximum compatibility
            n_tjas += 1
            folder_name = f"{title_for_path} - {n_tjas}" if will_split_tja else title_for_path

            # Extract audio first
            storage_path = path.join(target_path, folder_name)
            os.makedirs(storage_path, exist_ok=True)
            ext, audio_name_ogg, audio_path_ogg = get_ogg_path(storage_path, song_audio)
            if os.path.exists(audio_path_ogg):
                song_audio_tja = audio_name_ogg
            else:
                try:
                    osu_zip.extract(song_audio, storage_path)
                    song_audio_tja = convert_to_ogg(storage_path, song_audio)
                except KeyError:
                    print(f"Warning: song audio `{song_audio}` not found. Neither copied nor converted.", file=sys.stderr)
                    song_audio_tja = song_audio

            # Collect other chart resources
            resources: Dict[str, str] = {}

            tja_fname = f"{folder_name}.tja"
            tja_fpath = path.join(storage_path, tja_fname)
            print(f"Converting `{osus_fname}` to `{tja_fname}` ...", end="", flush=True)
            print_pend()

            # Assign difficulty types for this folder
            difftypes = get_best_difftypes([info["diffrank"] for info in selected_infos])
            difficulties = [get_course_by_number(v) for v in difftypes]

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
                    with TextIOWrapper(osu_zip.open(info["filename"]), encoding="utf-8") as diff_fp:
                        level = int(info["difficulty"])
                        head_meta, head_syncs[diff], head_diffs[diff], diff_contents[diff], rescs = (
                            osu2tja(diff_fp, diff, level, song_audio_tja)
                        )
                        resources.update(rescs)
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
            for enc in ["shift-jis", "utf-8-sig"]:
                try:
                    with open(tja_fpath, "w+", encoding=enc) as f:
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
                    break
                except UnicodeEncodeError:
                    assert enc != "utf-8-sig", "Found invalid UTF-8 characters during conversion."

            print_unpend()
            print(f"\rConverting `{osus_fname}` to `{tja_fname}` done!")

            # Extract other resources
            for rfname, rtype in resources.items():
                try:
                    osu_zip.extract(rfname, storage_path)
                except KeyError:
                    print_with_pended(f"Warning: Referenced {rtype} file `{rfname}` not found. Not copied.", file=sys.stderr)

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

def batch_convert_tja2osz(input_folder: str, output_folder: str, tmp_folder: str):
    skipped_files = []
    for dirpath, dirnames, names in os.walk(input_folder):
        for filename in names:
            path_tja = os.path.join(dirpath, filename)
            fname, ext = os.path.splitext(filename)
            if ext != ".tja":
                continue
            try:
                tja2osus(path_tja, output_folder, tmp_folder)
                dir_out = os.path.join(output_folder, fname)
                print(f"Converted `{path_tja}` to `{fname}/*.osu`s.")
                shutil.make_archive(dir_out, 'zip', dir_out)
                os.replace(f"{dir_out}.zip", f"{dir_out}.osz")
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

    script_name = path.basename(__file__)
    root_dir = path.dirname(path.abspath(__file__))
    parser = argparse.ArgumentParser(
        description=textwrap.dedent(f'''\
        Convert {ext_in} files to {ext_out} files and copy the audio to "<output_folder>/<song_folder>/".
        {'.osz files are also created in "<output_folder>/".' if mode == 'tja2osz' else ''}
        '''),
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('input_folder', nargs='?', default=path.join(root_dir, 'Songs'),
        help=f'where your {ext_in} files are located (default: Songs) (Songs is in the same directory as {script_name})')
    parser.add_argument('output_folder', nargs='?', default=path.join(root_dir, 'Output'),
        help=f'where the converted {ext_out} files will be saved (default: Output) (Output is in the same directory as {script_name})')
    args = parser.parse_args()

    print(f"Input folder: {path.abspath(args.input_folder)}")
    print(f"Output folder: {path.abspath(args.output_folder)}")

    if mode == "tja2osz":
        batch_convert_tja2osz(args.input_folder, args.output_folder, path.join(root_dir, 'tmp'))
    else:
        batch_convert_osz2tja(args.input_folder, args.output_folder)

if __name__ == "__main__":
    try:
        osz2tja2osz_main('osz2tja')
    finally:
        input("Done. Press the Enter key to exit...")

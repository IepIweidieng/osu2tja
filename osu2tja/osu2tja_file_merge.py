# sys.path hack
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from osu2tja.osu2tja import osu2tja, init_debug_globals, WATER_MARK
except ImportError:
    from osu2tja import osu2tja, init_debug_globals, WATER_MARK
assert callable(osu2tja)

from common.osu import OSU_VER_STR_PREFIX, get_diffrank_by_name
from common.tja import get_course_by_number
from common.utils import print_with_pended, print_pend, print_unpend

import argparse
import traceback
from typing import Any, Callable, Dict, List, Optional, TextIO, Tuple, Union
from os import path
import os
import sys
from shutil import copy2
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


FnameDiffrankLevel = Tuple[str, Optional[float], Optional[Union[int, float]]]

# return number of .tja file generated
def osus2tja(fname_diffrank_levels: List[FnameDiffrankLevel], osus_name: Optional[str] = None, target_path: Optional[str] = None,
    extract_file: Callable[[str, str], Any] = copy2, open_file: Callable[[str], TextIO] = open,
    ) -> int:
    osu_infos_by_song: Dict[Tuple[str, int], List] = {}
    for filename, diffrank, level in fname_diffrank_levels:
        with open_file(filename) as fp:
            osu_info = extract_osu_file_info(fp)
        osu_info["filename"] = filename
        osu_info["audio"] = osu_info["audio"] or ""
        osu_info["mode"] = osu_info["mode"] or 0
        osu_info["difficulty_tja"] = level # internal field
        osu_info["diffrank"] = diffrank
        assert type(osu_info["audio"]) == str and type(osu_info["mode"]) == int
        mode_group = osu_info["mode"] if target_path is not None else 0 # allow mixing game mode if using the osu2tja script
        osu_infos_by_song.setdefault((osu_info["audio"], mode_group), []).append(osu_info)

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
    for (song_audio, game_mode_group), osu_infos in osu_infos_by_song.items():
        mixed_mode = False
        first_mode = None
        for osu_info in osu_infos:
            if osu_info["diffrank"] is None:
                osu_info["diffrank"] = get_diffrank_by_name(osu_info["version"])
            if first_mode is None:
                first_mode = osu_info["mode"]
            elif osu_info["mode"] != first_mode:
                mixed_mode = True
        osu_infos.sort(key=lambda x: (x["diffrank"], x["difficulty_tja"], x["difficulty"]))
        for start_idx in range(0, len(osu_infos), n_diffs_max_per_tja):
            # Get the subset of difficulties for this folder
            selected_infos = osu_infos[start_idx:start_idx + n_diffs_max_per_tja]

            # 1 directory per .tja file for maximum compatibility
            n_tjas += 1
            folder_name = f"{title_for_path} - {n_tjas}" if will_split_tja else title_for_path

            # Extract audio first
            if target_path is None:
                song_audio_tja = storage_path = None
            else:
                storage_path = path.join(target_path, folder_name)
                os.makedirs(storage_path, exist_ok=True)
                ext, audio_name_ogg, audio_path_ogg = get_ogg_path(storage_path, song_audio)
                if os.path.exists(audio_path_ogg):
                    song_audio_tja = audio_name_ogg
                else:
                    try:
                        extract_file(song_audio, storage_path)
                        song_audio_tja = convert_to_ogg(storage_path, song_audio)
                    except (KeyError, FileNotFoundError):
                        print(f"// Warning: song audio `{song_audio}` not found. Neither copied nor converted.", file=sys.stderr)
                        song_audio_tja = song_audio

            # Collect other chart resources
            resources: Dict[str, str] = {}

            if storage_path is None:
                tja_fname = tja_fpath = None
            else:
                tja_fname = f"{folder_name}.tja"
                tja_fpath = path.join(storage_path, tja_fname)
                if osus_name is not None:
                    print(f"// Converting `{osus_name}` to `{tja_fname}` ...", end="", flush=True)
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
                    with open_file(info["filename"]) as diff_fp:
                        level = info["difficulty_tja"] if info["difficulty_tja"] is not None else info["difficulty"]
                        head_meta, head_syncs[diff], head_diffs[diff], diff_contents[diff], rescs = (
                            osu2tja(diff_fp, diff, level, song_audio_tja, mixed_mode)
                        )
                        resources.update(rescs)
                        if len(head_sync_main) == 0:
                            head_sync_main = head_syncs[diff]
                        elif head_syncs[diff] != head_sync_main:
                            if not head_sync_main_printed:
                                print_with_pended(f"// Warning: Main sync headers: {head_sync_main}", file=sys.stderr)
                                head_sync_main_printed = True
                            print(f"// Warning: Generated a different sync header for {diff}: {head_syncs[diff]}", file=sys.stderr)
                except Exception:
                    for line in traceback.format_exc().splitlines():
                        print_with_pended(f"// {line}", file=sys.stderr)
                    print(f"// Error processing {diff} [{info['version']}] difficulty of `{folder_name}`. Continued.", file=sys.stderr)

            # Save .tja file
            def write_file(f: TextIO) -> None:
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

            for enc in ["shift-jis", "utf-8-sig"]:
                try:
                    if tja_fpath is not None:
                        with open(tja_fpath, "w+", encoding=enc) as f:
                            write_file(f)
                    else:
                        write_file(sys.stdout)
                    break
                except UnicodeEncodeError:
                    assert enc != "utf-8-sig", "Found invalid UTF-8 characters during conversion."

            if osus_name is not None and tja_fname is not None:
                print_unpend()
                print(f"\r// Converting `{osus_name}` to `{tja_fname}` done!")

            # Extract other resources
            if storage_path is not None:
                for rfname, rtype in resources.items():
                    try:
                        extract_file(rfname, storage_path)
                    except (KeyError, FileNotFoundError):
                        print_with_pended(f"// Warning: Referenced {rtype} file `{rfname}` not found. Not copied.", file=sys.stderr)

    return n_tjas


def main():
    parser = argparse.ArgumentParser(
        description='Convert .osu file(s) to .tja format and print the result.',
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("file_course_levels", metavar="filename [course] [level]", nargs='+',
        help="source .osu file, with optionally given difficulty name and optionally given star level")
    parser.add_argument("-d", "--debug", action="store_true",
        help="display extra info of converted measures")
    parser.add_argument("-t", "--trace", action="store_true",
        help="log measure conversion info into generated tja")
    parser.add_argument("-i", "--inspect", metavar="ms", type=float, nargs='+', default=[],
        help="display extra info of osu objects placed at specified millisecond offsets")
    parser.add_argument("-g", "--guess-measure", "--guess", action="store_true",
        help="deprecated option intended for forcing skipping predefined integer ratio look-up (now removed) for bar length. Has no effects.")
    args = parser.parse_args()

    init_debug_globals(args.debug, args.trace, args.inspect)

    # check filenames
    fname_diffrank_levels: List[FnameDiffrankLevel] = []
    for arg in args.file_course_levels:
        assert isinstance(arg, str)

        # file
        if os.path.isfile(arg) and arg.lower().endswith(".osu"):
            fname_diffrank_levels.append((arg, None, None))
            continue

        # diffrank
        diffrank = get_diffrank_by_name(arg, default=None, allow_num=False)
        if diffrank is not None:
            if fname_diffrank_levels and fname_diffrank_levels[-1][1] is None:
                fname_diffrank_levels[-1] = (fname_diffrank_levels[-1][0], diffrank, fname_diffrank_levels[-1][2])
            else:
                print("// Course (re-)specified without a corresponding .osu file: `%s`" % arg, file=sys.stderr)
            continue

        # level
        try:
            level = int(arg) if arg.isdigit() else float(arg)
            if fname_diffrank_levels and fname_diffrank_levels[-1][2] is None:
                fname_diffrank_levels[-1] = (fname_diffrank_levels[-1][0], fname_diffrank_levels[-1][1], level)
            else:
                print("// Level (re-)specified without a corresponding .osu file: `%s`" % arg, file=sys.stderr)
            continue
        except ValueError:
            pass

        print("// Invalid filename, course, or level: `%s`. Ignored." % arg, file=sys.stderr)

    if not fname_diffrank_levels:
        print("// No valid .osu files specified.", file=sys.stderr)
        return

    n_tjas = osus2tja(fname_diffrank_levels)
    if n_tjas > 1:
        print(f"// Warning: Concatenated {n_tjas} .tja files. Look for `{WATER_MARK}` for each .tja header.", file=sys.stderr)


if __name__ == "__main__":
    try:
        main()
    finally:
        input("// Done. Press the Enter key to exit...")

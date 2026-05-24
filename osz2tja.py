from osu2tja.osu2tja_file_merge import osus2tja, FnameDiffrankLevel
from tja2osu.tja2osu_file_dvide import tja2osus

import argparse
import shutil
import textwrap
import traceback
from zipfile import ZipFile, is_zipfile
from typing import List, Literal
from os import path
import os
import sys
from io import TextIOWrapper

def convert_osz2tja(osus_fpath: str, target_path: str) -> None:
    if not is_zipfile(osus_fpath):
        raise ValueError(f"{osus_fpath} is not a valid zip file")

    with ZipFile(osus_fpath, "r") as osu_zip:
        osus_fname = os.path.basename(osus_fpath)
        osu_files: List[FnameDiffrankLevel] = [(filename, None, None)
            for filename in osu_zip.namelist() if filename.lower().endswith(".osu")]
        if not osu_files:
            raise ValueError(f"No .osu files found in {osus_fpath}")
        osus2tja(osu_files, osus_name=osus_fname, target_path=target_path,
            extract_file=osu_zip.extract,
            open_file=lambda fname: TextIOWrapper(osu_zip.open(fname, "r"), encoding="utf-8"))

def convert_osudir2tja(osudir_fpath: str, target_path: str) -> bool:
    osudir_fname = os.path.basename(osudir_fpath)
    osu_files: List[FnameDiffrankLevel] = [(filename, None, None)
        for filename in os.listdir(osudir_fpath) if filename.lower().endswith(".osu")]
    if not osu_files:
        return False
    osus2tja(osu_files, osus_name=osudir_fname, root_path=osudir_fpath, target_path=target_path)
    return True

def batch_convert_osz2tja(input_path: str, output_path: str):
    skipped_files = []
    processed_files = set()

    def convert_file(dirpath: str, filename: str):
        path_osudir = path.join(dirpath, filename)
        if path_osudir in processed_files:
            return
        processed_files.add(path_osudir)
        fname, ext = os.path.splitext(path_osudir)
        try:
            if os.path.isdir(path_osudir):
                if convert_osudir2tja(path_osudir, output_path):
                    print(f"Converted `{filename}/` to TJAs.")
            elif ext.lower() == ".osz":
                convert_osz2tja(path_osudir, output_path)
                print(f"Converted `{filename}` to TJAs.")
        except Exception:
            traceback.print_exc()
            print(f"Error converting `{path_osudir}`. Continued.", file=sys.stderr)
            skipped_files.append(path_osudir)

    convert_file(os.path.dirname(input_path), os.path.basename(input_path))
    for dirpath, dirnames, names in os.walk(input_path):
        for dirname in dirnames:
            convert_file(dirpath, dirname)
        for filename in names:
            convert_file(dirpath, filename)

    if skipped_files:
        print("\nSkipped files:")
        for file in skipped_files:
            print(f"- {file}")

def convert_tja2osz(tja_fpath: str, output_path: str, tmp_folder: str, fname: str):
    if os.path.isfile(output_path) or not os.path.exists(output_path):
        output_path_noext, output_ext = os.path.splitext(output_path)
        if output_ext.lower() == ".osz":
            output_path, fname = os.path.dirname(output_path_noext), os.path.basename(output_path_noext)

    tja2osus(tja_fpath, output_path, tmp_folder, fname=fname)
    dir_out = os.path.join(output_path, fname)
    print(f"Converted `{tja_fpath}` to `{fname}/*.osu`s.")
    shutil.make_archive(dir_out, 'zip', dir_out)
    os.replace(f"{dir_out}.zip", f"{dir_out}.osz")
    print(f"Converted `{dir_out}/` to `{fname}.osz`.")

def batch_convert_tja2osz(input_path: str, output_path: str, tmp_folder: str):
    skipped_files = []

    def convert_file(dirpath: str, filename: str):
        path_tja = os.path.join(dirpath, filename)
        fname, ext = os.path.splitext(filename)
        try:
            if ext.lower() == ".tja":
                convert_tja2osz(path_tja, output_path, tmp_folder, fname)
        except Exception:
            traceback.print_exc()
            print(f"Error converting `{path_tja}`. Continued.", file=sys.stderr)
            skipped_files.append(path_tja)

    if os.path.isfile(input_path):
        convert_file(os.path.dirname(input_path), os.path.basename(input_path))
    else:
        for dirpath, dirnames, names in os.walk(input_path):
            for filename in names:
                convert_file(dirpath, filename)

    if skipped_files:
        print("\nSkipped files:")
        for file in skipped_files:
            print(f"- {file}")

def osz2tja2osz_main(mode: Literal['osz2tja', 'tja2osz']) -> None:
    if mode == 'tja2osz':
        ext_in = lambda s='': f'.tja file{s}'
        ext_out = lambda s='': f'.osz file{s}'
    else:
        ext_in = lambda s='': f'.osz file{s} or .osu director{"ies" if s else "y"}'
        ext_out = lambda s='': f'.tja file{s}'

    script_name = path.basename(__file__)
    root_dir = path.dirname(path.abspath(__file__))
    parser = argparse.ArgumentParser(
        description=textwrap.dedent(f'''\
        Convert {ext_in('s')} to {ext_out('s')} and copy the audio to "<output_folder>/<song_folder>/".
        {'.osz files are also created in "<output_folder>/".' if mode == 'tja2osz' else ''}
        '''),
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('input_path', nargs='?', default=path.join(root_dir, 'Songs'),
        help=f'The {ext_in()} to convert, or the directory where your {ext_in("s")} are located (default: Songs) (Songs is in the same directory as {script_name})')
    parser.add_argument('output_path', nargs='?', default=path.join(root_dir, 'Output'),
        help=f'The converted {ext_out()} to save, or the directory where the converted {ext_out("s")} will be saved (default: Output) (Output is in the same directory as {script_name})')
    args = parser.parse_args()

    print(f"Input folder: {path.abspath(args.input_path)}")
    print(f"Output folder: {path.abspath(args.output_path)}")

    if mode == "tja2osz":
        batch_convert_tja2osz(args.input_path, args.output_path, path.join(root_dir, 'tmp'))
    else:
        batch_convert_osz2tja(args.input_path, args.output_path)

if __name__ == "__main__":
    try:
        osz2tja2osz_main('osz2tja')
    finally:
        input("Done. Press the Enter key to exit...")

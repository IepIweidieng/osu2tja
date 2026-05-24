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

def batch_convert_osz2tja(input_folder: str, output_folder: str):
    skipped_files = []
    for filename in os.listdir(input_folder):
        if filename.lower().endswith(".osz"):
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

def convert_tja2osz(tja_fpath: str, output_folder: str, tmp_folder: str, fname: str) -> str:
    tja2osus(tja_fpath, output_folder, tmp_folder)
    dir_out = os.path.join(output_folder, fname)
    print(f"Converted `{tja_fpath}` to `{fname}/*.osu`s.")
    shutil.make_archive(dir_out, 'zip', dir_out)
    os.replace(f"{dir_out}.zip", f"{dir_out}.osz")
    return dir_out

def batch_convert_tja2osz(input_folder: str, output_folder: str, tmp_folder: str):
    skipped_files = []
    for dirpath, dirnames, names in os.walk(input_folder):
        for filename in names:
            path_tja = os.path.join(dirpath, filename)
            fname, ext = os.path.splitext(filename)
            if ext.lower() != ".tja":
                continue
            try:
                dir_out = convert_tja2osz(path_tja, output_folder, tmp_folder, fname)
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

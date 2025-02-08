#!/usr/bin/env python3
"""
concatenate_files.py

This script recursively searches a repository for files matching a given
extension (default: .py) and concatenates their contents into a single
output file. Each file is preceded by a header showing its relative path.

Usage:
    python concatenate_files.py [-r ROOT_DIR] [-e EXTENSION] [-o OUTPUT_FILE]

Examples:
    # Concatenate all Python files under the current directory:
    python concatenate_files.py

    # Concatenate all files with .py extension under /path/to/repo:
    python concatenate_files.py -r /path/to/repo

    # Use a custom output file name:
    python concatenate_files.py -o merged_output.txt
"""

import os
import argparse
import sys

def main():
    parser = argparse.ArgumentParser(
        description="Recursively concatenate files of a specified extension."
    )
    parser.add_argument(
        "-r", "--root",
        default=".",
        help="Root directory to scan (default: current directory)"
    )
    parser.add_argument(
        "-e", "--extension",
        default=".py",
        help="File extension to include (default: .py)"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output file name (default: <scriptBaseName>.txt in the script's directory)"
    )
    args = parser.parse_args()

    root_dir = os.path.abspath(args.root)
    extension = args.extension

    # Determine the full path of this script.
    script_path = os.path.abspath(__file__)
    script_dir = os.path.dirname(script_path)
    script_base_name = os.path.splitext(os.path.basename(script_path))[0]

    # Determine the output file.
    if args.output:
        output_file = os.path.abspath(args.output)
    else:
        output_file = os.path.join(script_dir, f"{script_base_name}.txt")

    files_to_concatenate = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Skip hidden directories, __pycache__, and the transcription_bot folder
        dirnames[:] = [d for d in dirnames if not (d.startswith('.') or d == '__pycache__' or d == 'transcription_bot')]
        for filename in filenames:
            if filename.endswith(extension):
                full_path = os.path.join(dirpath, filename)
                # Skip the output file if it's inside the repository.
                if os.path.abspath(full_path) == output_file:
                    continue
                # Skip this script itself.
                if os.path.abspath(full_path) == script_path:
                    continue
                files_to_concatenate.append(full_path)

    # Sort files by their relative paths for a consistent order.
    files_to_concatenate.sort(key=lambda f: os.path.relpath(f, root_dir))

    merged_content = ""

    for file_path in files_to_concatenate:
        rel_path = os.path.relpath(file_path, root_dir)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                file_data = f.read()
        except Exception as e:
            print(f"Error reading file {file_path}: {e}", file=sys.stderr)
            continue

        # Append a header (using Python comment style) and then the file's contents.
        merged_content += (
            f"\n# ************************************************************\n"
            f"#  {rel_path}\n"
            f"# ************************************************************\n\n"
        )
        merged_content += file_data + "\n"

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(merged_content)
    except Exception as e:
        print(f"Error writing to output file {output_file}: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Files concatenated into \"{output_file}\".")

if __name__ == "__main__":
    main()

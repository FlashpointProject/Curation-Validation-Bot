import os.path
import subprocess
import tempfile
import zipfile

import py7zr
from logger import getLogger

l = getLogger("repack")


def repack(filename: str):
    filename = os.path.abspath(filename)
    errors: list = []
    temp_folder = tempfile.mkdtemp()

    # unpack file

    # repack with bluezip
    l.debug(f"bluezipping '{filename}'...")

    # Spawn a process with arguments
    process_args = ["python", "./bluezip.py", os.path.abspath(filename), "-o", temp_folder]
    process = subprocess.Popen(process_args, cwd='bluezip', stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Wait for the process to exit and get the output
    stdout, stderr = process.communicate()

    # Get the exit code of the process
    exit_code = process.returncode

    if exit_code != 0:
        l.error(f"bluezip failed for '{filename}'")
        errors.append("Error during bluezip")
        return errors, ""

    # Get the list of files inside the folder
    files = os.listdir(temp_folder)

    # Filter out any subdirectories and get the first file
    first_file = next(file for file in files if os.path.isfile(os.path.join(temp_folder, file)))
    first_file = os.path.join(temp_folder, first_file)
    l.debug(first_file)

    return errors, first_file



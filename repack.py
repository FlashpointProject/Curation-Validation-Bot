import os.path
import subprocess
import tempfile
import zipfile
import random
import string
import asyncio

import py7zr
from logger import getLogger

l = getLogger("repack")


async def repack(filename: str):
    filename = os.path.abspath(filename)
    errors: list = []
    repack_folder = os.environ["REPACK_DIR"]
    temp_folder = os.path.join(repack_folder, ''.join(random.choices(string.ascii_letters + string.digits, k=10)))
    if not os.path.exists(temp_folder):
        # If not, create the directory and its parents recursively
        os.makedirs(temp_folder, 0o777)

    # unpack file

    # repack with bluezip
    l.debug(f"bluezipping '{filename}'...")

    # Spawn a process with arguments
    process_args = ["./bluezip.py", os.path.abspath(filename), "-o", temp_folder]
    print(process_args)
    process = await asyncio.subprocess.create_subprocess_exec("python", *process_args, cwd='bluezip', stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)

    # Wait for the process to exit and get the output
    stdout, stderr = await process.communicate()

    # Get the exit code of the process
    exit_code = process.returncode

    if exit_code != 0:
        l.error(f"bluezip failed for '{filename}'")
        errors.append("Error during bluezip")
        return errors, ""

    for r, d, f in os.walk(temp_folder):
        os.chmod(r, 0o777)
    os.chmod(temp_folder, 0o777)

# Get the list of files inside the folder
    files = os.listdir(temp_folder)

    # Filter out any subdirectories and get the first file
    first_file = next(file for file in files if os.path.isfile(os.path.join(temp_folder, file)))
    first_file = os.path.join(temp_folder, first_file)
    l.debug(first_file)

    return errors, first_file



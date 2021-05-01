from typing import Optional

import py7zr

from logger import getLogger
import tempfile
import zipfile

l = getLogger("main")

max_uncompressed_size = 1000 * 1000 * 1000


# noinspection PyUnboundLocalVariable
def get_all_curations_in_zip(filename: str) -> tuple[Optional[list[str]], Optional[list[str]]]:
    errors: list = []

    # process archive
    filenames: list = []

    if filename.endswith(".7z"):
        try:
            l.debug(f"reading archive '{filename}'...")
            archive = py7zr.SevenZipFile(filename, mode='r')

            uncompressed_size = archive.archiveinfo().uncompressed
            if uncompressed_size > max_uncompressed_size:
                errors.append(
                    f"The archive is too large to be validated (`{uncompressed_size // 1000000}MB/{max_uncompressed_size // 1000000}MB`).")
                archive.close()
                return errors, None

            filenames = archive.getnames()
            base_path = tempfile.mkdtemp(prefix="curation_validator_") + "/"
        except Exception as e:
            l.error(f"there was an error while reading file '{filename}': {e}")
            errors.append("There seems to a problem with your 7z file.")
            return errors, None
    elif filename.endswith(".zip"):
        try:
            l.debug(f"reading archive '{filename}'...")
            archive = zipfile.ZipFile(filename, mode='r')

            uncompressed_size = sum([zinfo.file_size for zinfo in archive.filelist])
            if uncompressed_size > max_uncompressed_size:
                errors.append(
                    f"The archive is too large to be validated (`{uncompressed_size // 1000000}MB/{max_uncompressed_size // 1000000}MB`).")
                archive.close()
                return errors, None

            filenames = archive.namelist()
            base_path = tempfile.mkdtemp(prefix="curation_validator_") + "/"
        except Exception as e:
            l.error(f"there was an error while reading file '{filename}': {e}")
            errors.append("There seems to a problem with your zip file.")
            return errors, None
    archive_types = ['.7z', '.zip']
    archive_names = []
    for archive_type in archive_types:
        for file in filenames:
            if archive_type in file:
                archive_names.append(base_path + '/' + file)
    if len(archive_names) > 2:
        result = archive_names
        archive.extractall(path=base_path)
    else:
        result = [filename]
    archive.close()
    return None, result

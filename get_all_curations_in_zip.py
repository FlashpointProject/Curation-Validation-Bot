import os
import re
import tempfile
import zipfile
from typing import Optional

import py7zr

from curation_validator import archive_cleanup
from logger import getLogger

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
            base_archive = py7zr.SevenZipFile(filename, mode='r')

            uncompressed_size = base_archive.archiveinfo().uncompressed
            if uncompressed_size > max_uncompressed_size:
                errors.append(
                    f"The archive is too large to be validated (`{uncompressed_size // 1000000}MB/{max_uncompressed_size // 1000000}MB`).")
                base_archive.close()
                return errors, None

            filenames = base_archive.getnames()
            base_path = tempfile.mkdtemp(prefix="curation_validator_") + "/"
        except Exception as e:
            l.error(f"there was an error while reading file '{filename}': {e}")
            errors.append("There seems to a problem with your 7z file.")
            return errors, [filename]
    elif filename.endswith(".zip"):
        try:
            l.debug(f"reading archive '{filename}'...")
            base_archive = zipfile.ZipFile(filename, mode='r')

            uncompressed_size = sum([zinfo.file_size for zinfo in base_archive.filelist])
            if uncompressed_size > max_uncompressed_size:
                errors.append(
                    f"The archive is too large to be validated (`{uncompressed_size // 1000000}MB/{max_uncompressed_size // 1000000}MB`).")
                base_archive.close()
                return errors, None

            filenames = base_archive.namelist()
            base_path = tempfile.mkdtemp(prefix="curation_validator_") + "/"
        except Exception as e:
            l.error(f"there was an error while reading file '{filename}': {e}")
            return errors, [filename]

    meta_regex = re.compile(r"meta\.(yaml|yml|txt)$")

    has_meta = [match for match in filenames if meta_regex.search(match) is not None]
    if not has_meta:
        archive_types = ['.7z', '.zip']
        archive_names = []
        for archive_type in archive_types:
            for file in filenames:
                if file.endswith(archive_type):
                    archive_names.append(base_path + '/' + file)

        base_archive.extractall(path=base_path)
        base_archive.close()
        # Get only the archives which have a meta file in them
        try:
            hi = []
            for name in archive_names:
                for file in get_archive_filenames(name):
                    if meta_regex.match(file):
                        hi.append(name)
            archive_names = [archive_name for archive_name in archive_names if [name for name in get_archive_filenames(archive_name) if meta_regex.search(name)]]
        except ArchiveTooLargeException:
            errors.append("The archive is too large to be validated")
            archive_cleanup(filename, base_path)
            return errors, [filename]
        except Exception as e:
            errors.append(f"There was an error while reading files {archive_names}:{e}")
            archive_cleanup(filename, base_path)
            return errors, [filename]
        if not archive_names:
            archive_cleanup(filename, base_path)
            return errors, [filename]
        os.remove(base_path)
        return errors, archive_names


def get_archive_filenames(path: str) -> list[str]:
    if path.endswith(".7z"):
        l.debug(f"reading archive '{path}'...")
        archive = py7zr.SevenZipFile(path, mode='r')
        uncompressed_size = archive.archiveinfo().uncompressed
        if uncompressed_size > max_uncompressed_size:
            raise ArchiveTooLargeException
        filenames = archive.getnames()
    elif path.endswith(".zip"):
        l.debug(f"reading archive '{path}'...")
        archive = zipfile.ZipFile(path, mode='r')
        uncompressed_size = sum([zinfo.file_size for zinfo in archive.filelist])
        if uncompressed_size > max_uncompressed_size:
            raise ArchiveTooLargeException
        filenames = archive.namelist()
    else:
        raise NotArchiveType
    return filenames


class ArchiveTooLargeException(Exception):
    pass


class NotArchiveType(Exception):
    pass

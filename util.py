import zipfile

import py7zr

from logger import getLogger

l = getLogger("main")
max_uncompressed_size = 1000 * 1000 * 1000


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

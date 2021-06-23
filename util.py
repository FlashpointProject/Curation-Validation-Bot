import datetime
import re
import zipfile

import py7zr
from discord.ext import commands

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


time_regex = re.compile(r"(\d{1,5}(?:[.,]?\d{1,5})?)([smhdw])")
time_dict = {"h": 3600, "s": 1, "m": 60, "d": 86400, "w": 604800}


class TimeDeltaConverter(commands.Converter):
    async def convert(self, ctx, argument):
        matches = time_regex.findall(argument.lower())
        seconds = 0
        for v, k in matches:
            try:
                seconds += time_dict[k] * float(v)
            except KeyError:
                raise commands.BadArgument("{} is an invalid time-key! h/m/s/d/w are valid!".format(k))
            except ValueError:
                raise commands.BadArgument("{} is not a number!".format(v))
        if seconds <= 0:
            raise commands.BadArgument("Time must be greater than 0.")
        return datetime.timedelta(seconds=seconds)


class ArchiveTooLargeException(Exception):
    pass


class NotArchiveType(Exception):
    pass

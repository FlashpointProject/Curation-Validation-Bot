import shutil
import json
import re
from typing import Optional

import yaml
import py7zr
from logger import getLogger
import os
import tempfile
import zipfile
import requests

l = getLogger("main")


def validate_curation(filename: str) -> tuple[list, list, Optional[bool]]:
    errors: list = []
    warnings: list = []

    # process archive
    filenames: list = []

    max_uncompressed_size = 1000 * 1000 * 1000

    if filename.endswith(".7z"):
        try:
            l.debug(f"reading archive '{filename}'...")
            archive = py7zr.SevenZipFile(filename, mode='r')

            uncompressed_size = archive.archiveinfo().uncompressed
            if uncompressed_size > max_uncompressed_size:
                warnings.append(
                    f"The archive is too large to validate (`{uncompressed_size // 1000000}MB/{max_uncompressed_size // 1000000}MB`).")
                archive.close()
                return errors, warnings, None

            filenames = archive.getnames()
            base_path = tempfile.mkdtemp(prefix="curation_validator") + "/"
            archive.extractall(path=base_path)
            archive.close()
        except Exception as e:
            l.error(f"there was an error while reading file '{filename}': {e}")
            errors.append("There was an error while reading your submission.")
            return errors, warnings, None
    elif filename.endswith(".zip"):
        try:
            l.debug(f"reading archive '{filename}'...")
            archive = zipfile.ZipFile(filename, mode='r')

            uncompressed_size = sum([zinfo.file_size for zinfo in archive.filelist])
            if uncompressed_size > max_uncompressed_size:
                warnings.append(
                    f"The archive is too large to validate (`{uncompressed_size // 1000000}MB/{max_uncompressed_size // 1000000}MB`).")
                archive.close()
                return errors, warnings, None

            filenames = archive.namelist()
            base_path = tempfile.mkdtemp(prefix="curation_validator") + "/"
            archive.extractall(path=base_path)
            archive.close()
        except Exception as e:
            l.error(f"there was an error while reading file '{filename}': {e}")
            errors.append("There was an error while reading your submission.")
            return errors, warnings, None
    else:
        l.warn(f"file type of file '{filename}' not supported")

    l.debug(filenames)

    l.debug(f"validating archive data for '{filename}'...")
    # check files
    uuid_folder_regex = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}/?$")
    # meta_outside_root_folder_regex = re.compile(r"^meta\.(yaml|yml|txt)$")
    content_folder_regex = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}/content/?$")
    meta_regex = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}/meta\.(yaml|yml|txt)$")
    logo_regex = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}/logo\.(png)$")
    ss_regex = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}/ss\.(png)$")
    uuid_folder = [match for match in filenames if uuid_folder_regex.match(match) is not None]
    # meta_outside_root_folder = [match for match in filenames if meta_outside_root_folder_regex.match(match) is not None]
    content_folder = [match for match in filenames if content_folder_regex.match(match) is not None]
    meta = [match for match in filenames if meta_regex.match(match) is not None]
    logo = [match for match in filenames if logo_regex.match(match) is not None]
    ss = [match for match in filenames if ss_regex.match(match) is not None]

    if len(uuid_folder) == 0:
        errors.append("Root directory is either missing or its name is incorrect. It should be in UUIDv4 format.")
        return errors, warnings, None

    # if len(meta_outside_root_folder) != 0:
    #     errors.append("Found meta file outside root directory. Did you forgot to enclose the files into one directory?")
    #     return errors, warnings

    if len(logo) == 0:
        errors.append("Logo file is either missing or its filename is incorrect.")
    if len(ss) == 0:
        errors.append("Screenshot file is either missing or its filename is incorrect.")

    # check content
    if len(content_folder) == 0:
        errors.append("Content folder not found.")
    else:
        filecount_in_content = sum([len(files) for r, d, files in os.walk(base_path + content_folder[0])])
        if filecount_in_content == 0:
            errors.append("No files found in content folder.")

    # process meta
    is_extreme = False
    props: dict = {}
    if not meta:
        errors.append("Meta file is either missing or its filename is incorrect. Are you using Flashpoint Core for curating?")
    else:
        meta_filename = meta[0]
        with open(base_path + meta_filename) as meta_file:
            if meta_filename.endswith(".yml") or meta_filename.endswith(".yaml"):
                try:
                    props: dict = yaml.safe_load(meta_file)
                except yaml.YAMLError:  # If this is being called, it's a meta .txt
                    errors.append("Unable to load meta YAML file")
            elif meta_filename.endswith(".txt"):
                break_index: int = 0
                while break_index != -1:
                    props, break_index = parse_lines_until_multiline(meta_file.readlines(), props,
                                                                     break_index)
                    props, break_index = parse_multiline(meta_file.readlines(), props, break_index)
            else:
                errors.append("Meta file is either missing or its filename is incorrect. Are you using Flashpoint Core for curating?")

        title: tuple[str, bool] = ("Title", bool(props["Title"]))
        # developer: tuple[str, bool] = ("Developer", bool(props["Developer"]))

        release_date: tuple[str, bool] = ("Release Date", bool(props["Release Date"]))
        if release_date[1]:
            date_string = props["Release Date"].strip()
            if len(date_string) > 0:
                date_regex = re.compile(r"^\d{4}(-\d{2}){0,2}$")
                if not date_regex.match(date_string):
                    errors.append(f"Release date {date_string} is incorrect. Release dates should always be in `YYYY-MM-DD` format.")

        language_properties: tuple[str, bool] = ("Languages", bool(props["Languages"]))
        if language_properties[1]:
            with open("language-codes.json") as f:
                list_of_language_codes: list[dict] = json.load(f)
                language_str: str = props["Languages"]
                languages = language_str.split(";")
                languages = [x.strip() for x in languages]
                language_codes = []
                for x in list_of_language_codes:
                    language_codes.append(x["alpha2"])
                for language in languages:
                    if language not in language_codes:
                        if language == "sp":
                            errors.append("The correct ISO 639-1 language code for Spanish is `es`, not `sp`.")
                        elif language == "ge":
                            errors.append("The correct ISO 639-1 language code for German is `de`, not `ge`.")
                        elif language == "jp":
                            errors.append("The correct ISO 639-1 language code for Japanese is `ja`, not `jp`.")
                        elif language == "kr":
                            errors.append("The correct ISO 639-1 language code for Korean is `ko`, not `kr`.")
                        elif language == "ch":
                            errors.append("The correct ISO 639-1 language code for Chinese is `zh`, not `ch`.")
                        elif language == "iw":
                            errors.append("The correct ISO 639-1 language code for Hebrew is `he`, not `iw`.")
                        elif language == "cz":
                            errors.append("The correct ISO 639-1 language code for Czech is `cs`, not `cz`.")
                        elif language == "pe":
                            errors.append("The correct ISO 639-1 language code for Farsi is `fa`, not `pe`.")
                        else:
                            errors.append(f"Code `{language}` is not a valid ISO 639-1 language code.")

        # tag: tuple[str, bool] = ("Tags", bool(props["Tags"]))
        source: tuple[str, bool] = ("Source", bool(props["Source"]))
        status: tuple[str, bool] = ("Status", bool(props["Status"]))
        launch_command: tuple[str, bool] = ("Launch Command", bool(props["Launch Command"]))
        application_path: tuple[str, bool] = ("Application Path", bool(props["Application Path"]))

        # TODO check description?
        # description: tuple[str, bool] = ("Description", bool(props["Original Description"]))
        # if description[1] is False and (
        #         bool(props["Curation Notes"]) or bool(props["Game Notes"])):
        #     reply += "Make sure you didn't put your description in the notes section.\n"

        if "https" in props["Launch Command"]:
            errors.append("Found `https` in launch command. All launch commands must use `http` instead of `https`.")

        simple_mandatory_props: list[tuple[str, bool]] = [title, language_properties, source, launch_command, status, application_path]
        if not all([x[1] for x in simple_mandatory_props]):
            for prop in simple_mandatory_props:
                if prop[1] is False:
                    errors.append(f"The `{prop[0]}` property in the meta file is mandatory.")

        # TODO check optional props?
        # optional_props: list[tuple[str, bool]] = [developer, release_date, tag, description]
        # if not all(optional_props[1]): for x in optional_props: if x[1] is False: reply += x[0] +
        # "is missing, but not necessary. Add it if you can find it, but it's okay if you can't.\n"

        tags: list[str] = props["Tags"].split(";")
        tags: list[str] = [x.strip() for x in tags]
        tags: list[str] = [x for x in tags if len(x) > 0]

        master_tag_list = get_tag_list()

        if len(tags) == 0:
            errors.append("Missing tags. At least one tag must be specified.")
        else:
            for tag in tags:
                if tag not in master_tag_list:
                    warnings.append(f"Tag `{tag}` is not a known tag.")

        extreme: tuple[str, bool] = ("Extreme", bool(props["Extreme"]))
        is_extreme = False
        if extreme[1] and props["Extreme"]:
            is_extreme = True

    l.debug(f"cleaning up after archive'{filename}'...")
    shutil.rmtree(base_path, True)

    return errors, warnings, is_extreme


def get_tag_list() -> list[str]:
    l.debug(f"getting tags...")
    resp = requests.get(url="https://bluebot.unstable.life/tags")
    return resp.json()["tags"]


def parse_lines_until_multiline(lines: list[str], d: dict, starting_number: int):
    break_number: int = -1
    for idx, line in enumerate(lines[starting_number:]):
        if '|' not in line:
            split: list[str] = line.split(":")
            split: list[str] = [x.strip(' ') for x in split]
            d.update({split[0]: split[1]})
        else:
            break_number = idx
            break
    return d, break_number


def parse_multiline(lines: list[str], d: dict, starting_number: int):
    break_number = -1
    key: str = ""
    val: str = ""
    for idx, line in enumerate(lines[starting_number:]):
        if idx is starting_number:
            split = line.split(':')
            split = [x.strip(' ') for x in split]
            key = split[0]
        else:
            if line.startswith('\t'):
                line = line.strip(" \t")
                val += line
            else:
                break_number = idx
                break
    d.update({key: val})
    return d, break_number

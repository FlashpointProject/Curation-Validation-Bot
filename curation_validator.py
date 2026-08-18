import base64
import io
import random
import shutil
import json
import re
from enum import Enum, auto
import string
from typing import Optional, TypedDict
from datetime import datetime, timedelta
from pydantic import BaseModel
from fastapi import UploadFile

import py7zr
from cachetools import TTLCache, cached
from ruamel.yaml import YAML, YAMLError

from logger import getLogger
import os
import tempfile
import zipfile
import requests
from bs4 import BeautifulSoup

l = getLogger("main")


class CurationType(Enum):
    FLASH_GAME = auto()
    OTHER_GAME = auto()
    ANIMATION = auto()

class EditCurationMeta(BaseModel):
    Title: str | None = None
    AlternateTitles: str | None = None
    Version: str | None = None
    Developer: str | None = None
    Publisher: str | None = None
    ReleaseDate: str | None = None
    Series: str | None = None
    Source: str | None = None
    Status: str | None = None
    Tags: str | None = None
    Languages: str | None = None
    OriginalDescription: str | None = None
    GameNotes: str | None = None  

max_uncompressed_size = 50 * 1000 * 1000 * 1000
max_archive_members = 10_000_000
max_image_size = 16 * 1024 * 1024
max_validation_images = 16
max_metadata_size = 16 * 1024 * 1024


class ValidationMemberTooLarge(Exception):
    pass


def _member_size(member) -> int:
    if isinstance(member, zipfile.ZipInfo):
        return member.file_size
    return member.uncompressed


def _member_is_directory(member) -> bool:
    if isinstance(member, zipfile.ZipInfo):
        return member.is_dir()
    return member.is_directory


def _zip_member_count(filename: str) -> int:
    # ZipFile eagerly builds a ZipInfo for every member. Read just the EOCD
    # first so an archive over the member cap is rejected before that allocation.
    with open(filename, "rb") as archive_file:
        end_record = zipfile._EndRecData(archive_file)
    if end_record is None:
        raise zipfile.BadZipFile("File is not a zip file")
    return end_record[zipfile._ECD_ENTRIES_TOTAL]


def _read_validation_members(archive, members: dict[str, tuple[object, int]]) -> dict[str, bytes]:
    for member, size_limit in members.values():
        if _member_size(member) > size_limit:
            raise ValidationMemberTooLarge

    if isinstance(archive, zipfile.ZipFile):
        result = {}
        for name, (member, size_limit) in members.items():
            with archive.open(member, mode="r") as source:
                result[name] = source.read(size_limit + 1)
    else:
        archive.reset()
        largest_limit = max(size_limit for _, size_limit in members.values())
        factory = py7zr.io.BytesIOFactory(largest_limit + 1)
        archive.extract(targets=list(members), factory=factory)
        result = {
            name: factory.get(name).read(size_limit + 1)
            for name, (_, size_limit) in members.items()
        }

    if any(len(result[name]) > size_limit for name, (_, size_limit) in members.items()):
        raise ValidationMemberTooLarge
    return result


def _check_content_members(archive_members, content_folder: str, errors: list) -> None:
    content_prefix = content_folder.rstrip("/") + "/"
    localflash_path = content_prefix + "localflash"
    localflash_prefix = localflash_path + "/"
    found_content_file = False
    found_localflash = False
    children: dict[str, bool] = {}
    for member in archive_members:
        if not member.filename.startswith(content_prefix):
            continue
        if not _member_is_directory(member):
            found_content_file = True
        if member.filename != localflash_path and not member.filename.startswith(localflash_prefix):
            continue

        found_localflash = True
        if member.filename == localflash_path:
            if not _member_is_directory(member):
                children["localflash"] = True
            continue

        relative_name = member.filename[len(localflash_prefix):].rstrip("/")
        if not relative_name:
            continue
        child_name, separator, _ = relative_name.partition("/")
        is_direct_file = not separator and not _member_is_directory(member)
        children[child_name] = children.get(child_name, False) or is_direct_file

    if not found_content_file:
        errors.append("No files found in content folder.")
    if not found_localflash:
        return

    if len(children) > 1 or any(children.values()):
        errors.append("Content must be in additional folder in localflash rather than in localflash directly.")
        return

    if len(children) == 1:
        with open("data/common_localflash_names.json") as f:
            bad_localflash_names = json.load(f)["names"]
        if next(iter(children)) in bad_localflash_names:
            errors.append("Extremely common localflash containing folder name, please change.")


def update_meta(filename: str, new_meta: EditCurationMeta | None, new_logo: UploadFile | None, new_ss: UploadFile | None):
    repack_folder = os.environ["REPACK_DIR"]
    errors: list = []
    warnings: list = []

    meta_content = None
    meta_filename = None

    if filename.endswith(".7z"):
        try:
            l.debug(f"reading archive '{filename}'...")
            archive = py7zr.SevenZipFile(filename, mode='r')

            uncompressed_size = archive.archiveinfo().uncompressed
            if uncompressed_size > max_uncompressed_size:
                warnings.append(
                    f"The archive is too large to be validated (`{uncompressed_size // 1000000}MB/{max_uncompressed_size // 1000000}MB`).")
                archive.close()
                return errors, warnings, filename

            filenames = archive.getnames()
            base_path = tempfile.mkdtemp(prefix="curation_validator_") + "/"
            archive.extractall(path=base_path)
            archive.close()
        except Exception as e:
            l.error(f"there was an error while reading file '{filename}': {e}")
            errors.append("There seems to a problem with your 7z file.")
            return errors, warnings, filename
    elif filename.endswith(".zip"):
        try:
            l.debug(f"reading archive '{filename}'...")
            archive = zipfile.ZipFile(filename, mode='r')

            uncompressed_size = sum([zinfo.file_size for zinfo in archive.filelist])
            if uncompressed_size > max_uncompressed_size:
                warnings.append(
                    f"The archive is too large to be validated (`{uncompressed_size // 1000000}MB/{max_uncompressed_size // 1000000}MB`).")
                archive.close()
                return errors, warnings, filename

            filenames = archive.namelist()
            base_path = tempfile.mkdtemp(prefix="curation_validator_") + "/"
            archive.extractall(path=base_path)
            archive.close()
        except Exception as e:
            l.error(f"there was an error while reading file '{filename}': {e}")
            errors.append("There seems to a problem with your zip file.")
            return errors, warnings, filename
    elif filename.endswith(".rar"):
        errors.append("Curations must be either .zip or .7z, not .rar.")
        return errors, warnings, filename
    else:
        l.warn(f"file type of file '{filename}' not supported")
        errors.append(f"file type of file '{filename}' not supported")
        return errors, warnings, filename
    
    # check files
    l.debug(f"validating archive data for '{filename}'...")
    uuid_folder_regex = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}/?$")
    uuid_folder = [match for match in filenames if uuid_folder_regex.match(match) is not None]

    meta = []
    logo = []
    logo_case = []
    ss = []
    ss_case = []

    if len(uuid_folder) == 0:  # legacy or broken curation
        meta_regex = re.compile(r"^[^/]+/meta\.(yaml|yml|txt)$")
        logo_regex = re.compile(r"^[^/]+/logo\.(png)$")
        logo_regex_case = re.compile(r"(?i)^[^/]+/logo\.(png)$")
        ss_regex = re.compile(r"^[^/]+/ss\.(png)$")
        ss_regex_case = re.compile(r"(?i)^[^/]+/ss\.(png)$")
        
        meta = [match for match in filenames if meta_regex.match(match) is not None]
        logo = [match for match in filenames if logo_regex.match(match) is not None]
        logo_case = [match for match in filenames if logo_regex_case.match(match) is not None]
        ss = [match for match in filenames if ss_regex.match(match) is not None]
        ss_case = [match for match in filenames if ss_regex_case.match(match) is not None]
    else:  # core curation
        meta_regex = re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}/meta\.(yaml|yml|txt)$")
        logo_regex = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}/logo\.png$")
        logo_regex_case = re.compile(
            r"(?i)^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}/logo\.(png)$")
        ss_regex = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}/ss\.png$")
        ss_regex_case = re.compile(
            r"(?i)^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}/ss\.(png)$")
        
        meta = [match for match in filenames if meta_regex.match(match) is not None]
        logo = [match for match in filenames if logo_regex.match(match) is not None]
        logo_case = [match for match in filenames if logo_regex_case.match(match) is not None]
        ss = [match for match in filenames if ss_regex.match(match) is not None]
        ss_case = [match for match in filenames if ss_regex_case.match(match) is not None]

    if len(meta) == 0:
        errors.append("Did not find a meta file to edit")
        archive_cleanup(filename, base_path)
        return errors, warnings, filename

    meta_filename = meta[0]
    props = {}
    l.debug(f"Reading metadata file in: '{base_path + meta_filename}'")
    with open(base_path + meta_filename, mode='r', encoding='utf8') as meta_file:
        if meta_filename.endswith(".yml") or meta_filename.endswith(".yaml"):
            try:
                yaml = YAML(typ="safe")
                props: dict = yaml.load(meta_file)
                if props is None:
                    errors.append("The meta file seems to be empty.")
                    archive_cleanup(filename, base_path)
                    return errors, warnings, filename
            except YAMLError:
                errors.append(f"Unable to load meta YAML file")
                archive_cleanup(filename, base_path)
                return errors, warnings, filename
            except ValueError as e:
                l.debug(f"ValueError reading meta file: {e}")
                errors.append("Invalid release date. Ensure entered date is valid.")
                archive_cleanup(filename, base_path)
                return errors, warnings, filename
        elif meta_filename.endswith(".txt"):
            break_index: int = 0
            while break_index != -1:
                props, break_index = parse_lines_until_multiline(meta_file.readlines(), props,
                                                                    break_index)
                props, break_index = parse_multiline(meta_file.readlines(), props, break_index)
                if props.get("Genre") is not None:
                    props["Tags"] = props["Genre"]
        else:
            errors.append(
                "Meta file is either missing or its filename is incorrect. Are you using Flashpoint Core for curating?")
            archive_cleanup(filename, base_path)
            return errors, warnings, filename

    # translate legacy fields
    if props.get("Platform") is not None:
        props["Platforms"] = props["Platform"]

    # add primary platform if missing
    if "Platforms" in props and "Primary Platform" not in props:
        props["Primary Platform"] = props["Platforms"].split(';')[0].strip()

    if new_meta is not None:
        if new_meta.Title is not None:
            props["Title"] = new_meta.Title

        if new_meta.AlternateTitles is not None:
            props["Alternate Titles"] = new_meta.AlternateTitles

        if new_meta.Version is not None:
            props["Version"] = new_meta.Version

        if new_meta.Developer is not None:
            props["Developer"] = new_meta.Developer

        if new_meta.Publisher is not None:
            props["Publisher"] = new_meta.Publisher

        if new_meta.ReleaseDate is not None:
            props["Release Date"] = new_meta.ReleaseDate

        if new_meta.Series is not None:
            props["Series"] = new_meta.Series

        if new_meta.Source is not None:
            props["Source"] = new_meta.Source

        if new_meta.Status is not None:
            props["Status"] = new_meta.Status

        if new_meta.Tags is not None:
            props["Tags"] = new_meta.Tags

        if new_meta.Languages is not None:
            props["Languages"] = new_meta.Languages

        if new_meta.OriginalDescription is not None:
            props["Original Description"] = new_meta.OriginalDescription

        if new_meta.GameNotes is not None:
            props["Game Notes"] = new_meta.GameNotes

    if len(logo) > 0 and new_logo is not None:
        if new_logo.size > 26214400:
            errors.append("New logo larger than 25mb, rejected")
            return errors, warnings, filename
        with open(base_path + logo[0], "wb") as logo_file:
            logo_file.write(new_logo.file.read())

    if len(ss) > 0 and new_ss is not None:
        if new_ss.size > 26214400:
            errors.append("New screenshot larger than 25mb, rejected")
            return errors, warnings, filename
        with open(base_path + ss[0], "wb") as ss_file:
            ss_file.write(new_ss.file.read())

    if meta_filename.endswith('.txt'):
        # Delete the original .txt file and save back as .yaml instead
        os.remove(base_path + meta_filename)
        meta_filename = meta_filename.replace('.txt', '.yaml')    

    with open(base_path + meta_filename, mode='w', encoding='utf8') as meta_file:
        yaml.dump(props, meta_file)
        
    try:
        if filename.endswith(".zip"):
            filename = filename.replace(".zip", ".7z")
        
        filename = os.path.basename(filename)
        temp_folder = os.path.join(repack_folder, ''.join(random.choices(string.ascii_letters + string.digits, k=10)))
        if not os.path.exists(temp_folder):
            # If not, create the directory and its parents recursively
            os.makedirs(temp_folder, 0o777)
        
        filename = os.path.join(temp_folder, filename)

        # Create new 7z archive with all files including modified meta
        with py7zr.SevenZipFile(filename, mode='w') as new_archive:
            for root, dirs, files in os.walk(base_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, base_path)
                    new_archive.write(file_path, arcname)
                        
        l.debug(f"Successfully rebuilt archive '{filename}' with updated metadata")
        
    except Exception as e:
        l.error(f"Error rebuilding archive '{filename}': {e}")
        errors.append(f"Failed to rebuild archive: {str(e)}")
        archive_cleanup(filename, base_path)
        return errors, warnings, filename
    

    # Return the meta content and filename for further processing
    return errors, warnings, filename

def validate_curation(filename: str) -> tuple[list,
                                              list,
                                              Optional[bool],
                                              Optional[CurationType],
                                              Optional[dict],
                                              Optional[list[dict]]]:
    errors: list = []
    warnings: list = []

    # Only inventory the archive here. Validation reads the small metadata and
    # image members later; content is never extracted to the container rootfs.
    archive = None
    archive_members = []
    if filename.endswith(".7z"):
        try:
            l.debug(f"reading archive '{filename}'...")
            archive = py7zr.SevenZipFile(filename, mode='r')
            archive_members = archive.list()
            uncompressed_size = sum(_member_size(member) for member in archive_members)
            if len(archive_members) > max_archive_members:
                errors.append(
                    f"The archive contains too many members (`{len(archive_members)}/{max_archive_members}`).")
                archive.close()
                return errors, warnings, None, None, None, None
            if uncompressed_size > max_uncompressed_size:
                warnings.append(
                    f"The archive is too large to be validated (`{uncompressed_size // 1000000}MB/{max_uncompressed_size // 1000000}MB`).")
                archive.close()
                return errors, warnings, None, None, None, None
        except Exception as e:
            if archive is not None:
                archive.close()
            l.error(f"there was an error while reading file '{filename}': {e}")
            errors.append("There seems to a problem with your 7z file.")
            return errors, warnings, None, None, None, None
    elif filename.endswith(".zip"):
        try:
            l.debug(f"reading archive '{filename}'...")
            member_count = _zip_member_count(filename)
            if member_count > max_archive_members:
                errors.append(
                    f"The archive contains too many members (`{member_count}/{max_archive_members}`).")
                return errors, warnings, None, None, None, None
            archive = zipfile.ZipFile(filename, mode='r')
            archive_members = archive.infolist()
            uncompressed_size = sum(_member_size(member) for member in archive_members)
            if len(archive_members) > max_archive_members:
                errors.append(
                    f"The archive contains too many members (`{len(archive_members)}/{max_archive_members}`).")
                archive.close()
                return errors, warnings, None, None, None, None
            if uncompressed_size > max_uncompressed_size:
                warnings.append(
                    f"The archive is too large to be validated (`{uncompressed_size // 1000000}MB/{max_uncompressed_size // 1000000}MB`).")
                archive.close()
                return errors, warnings, None, None, None, None
        except Exception as e:
            if archive is not None:
                archive.close()
            l.error(f"there was an error while reading file '{filename}': {e}")
            errors.append("There seems to a problem with your zip file.")
            return errors, warnings, None, None, None, None
    elif filename.endswith(".rar"):
        errors.append("Curations must be either .zip or .7z, not .rar.")
        return errors, warnings, None, None, None, None
    else:
        l.warn(f"file type of file '{filename}' not supported")
        errors.append(f"file type of file '{filename}' not supported")
        return errors, warnings, None, None, None, None

    # check files
    l.debug(f"validating archive data for '{filename}'...")
    uuid_folder_regex = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}/?$")
    has_uuid_folder = any(
        uuid_folder_regex.match(member.filename) is not None
        for member in archive_members
    )

    logo = []
    ss = []

    if not has_uuid_folder:  # legacy or broken curation
        meta_regex = re.compile(r"^[^/]+/meta\.(yaml|yml|txt)$")
        logo_regex = re.compile(r"^[^/]+/logo\.(png)$")
        logo_regex_case = re.compile(r"(?i)^[^/]+/logo\.(png)$")
        ss_regex = re.compile(r"^[^/]+/ss\.(png)$")
        ss_regex_case = re.compile(r"(?i)^[^/]+/ss\.(png)$")

        content_folder = None
        for member in archive_members:
            f = member.filename
            index = f.find("/content")
            if index != -1:
                # Always save the shortest content path to avoid content folders inside weirdly named folders first
                new_path = f[:index + len("/content")]
                if content_folder is not None and len(content_folder) > len(new_path):
                    content_folder = new_path
                elif content_folder is None:
                    content_folder = new_path

        meta = [member.filename for member in archive_members if meta_regex.match(member.filename) is not None]
        logo = [member.filename for member in archive_members if logo_regex.match(member.filename) is not None]
        logo_case = [member.filename for member in archive_members if logo_regex_case.match(member.filename) is not None]
        ss = [member.filename for member in archive_members if ss_regex.match(member.filename) is not None]
        ss_case = [member.filename for member in archive_members if ss_regex_case.match(member.filename) is not None]
    else:  # core curation
        meta_regex = re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}/meta\.(yaml|yml|txt)$")
        logo_regex = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}/logo\.png$")
        logo_regex_case = re.compile(
            r"(?i)^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}/logo\.(png)$")
        ss_regex = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}/ss\.png$")
        ss_regex_case = re.compile(
            r"(?i)^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}/ss\.(png)$")
        
        content_folder = None
        for member in archive_members:
            f = member.filename
            index = f.find("/content")
            if index != -1:
                # Always save the shortest content path to avoid content folders inside weirdly named folders first
                new_path = f[:index + len("/content")]
                if content_folder is not None and len(content_folder) > len(new_path):
                    content_folder = new_path
                elif content_folder is None:
                    content_folder = new_path

        meta = [member.filename for member in archive_members if meta_regex.match(member.filename) is not None]
        logo = [member.filename for member in archive_members if logo_regex.match(member.filename) is not None]
        logo_case = [member.filename for member in archive_members if logo_regex_case.match(member.filename) is not None]
        ss = [member.filename for member in archive_members if ss_regex.match(member.filename) is not None]
        ss_case = [member.filename for member in archive_members if ss_regex_case.match(member.filename) is not None]

    if len(logo) == 0 and len(ss) == 0 and content_folder is None and len(meta) == 0:
        errors.append("Logo, screenshot, content folder and meta not found. Is your curation structured properly?")
        archive.close()
        return errors, warnings, None, None, None, None

    if set(logo) != set(logo_case):
        errors.append("Logo file extension must be lowercase.")
    else:
        if len(logo) == 0:
            errors.append("Logo file is either missing or its filename is incorrect.")

    if set(ss) != set(ss_case):
        errors.append("Screenshot file extension must be lowercase.")
    else:
        if len(ss) == 0:
            errors.append("Screenshot file is either missing or its filename is incorrect.")

    # Duplicate archive entries with the same screenshot path used to produce
    # duplicate base64 payloads. Only the final archive entry for a path is read.
    ss = list(dict.fromkeys(ss))
    image_candidates = ([('logo', logo[0])] if len(logo) == 1 else []) + [
        ('screenshot', screenshot) for screenshot in ss
    ]
    if len(image_candidates) > max_validation_images:
        errors.append(
            f"The archive contains too many validation images "
            f"(`{len(image_candidates)}/{max_validation_images}`).")
        image_candidates = image_candidates[:max_validation_images]

    selected_names = set(meta[:1] + [name for _, name in image_candidates])
    selected_members = {
        member.filename: member
        for member in archive_members
        if member.filename in selected_names
    }
    meta_content = None
    images = []
    image_requests = []
    for image_type, image_name in image_candidates:
        image_size = _member_size(selected_members[image_name])
        if image_size > max_image_size:
            errors.append(
                f"Image `{image_name}` exceeds the {max_image_size // (1024 * 1024)}MB validation limit.")
        else:
            image_requests.append((image_type, image_name))

    try:
        read_requests = {
            image_name: (selected_members[image_name], max_image_size)
            for _, image_name in image_requests
        }
        if meta:
            if _member_size(selected_members[meta[0]]) > max_metadata_size:
                errors.append(
                    f"Metadata file `{meta[0]}` exceeds the {max_metadata_size // (1024 * 1024)}MB validation limit.")
            else:
                read_requests[meta[0]] = (selected_members[meta[0]], max_metadata_size)

        member_data = _read_validation_members(archive, read_requests) if read_requests else {}
        if meta and meta[0] in member_data:
            meta_content = member_data[meta[0]]
        for image_type, image_name in image_requests:
            images.append({"type": image_type, "data": encode_image(member_data[image_name])})
    except ValidationMemberTooLarge:
        errors.append("An archive member exceeded its validation limit while being read.")
    except Exception as e:
        archive.close()
        archive_type = "7z" if filename.endswith(".7z") else "zip"
        l.error(f"there was an error while reading members from '{filename}': {e}")
        errors.append(f"There seems to a problem with your {archive_type} file.")
        return errors, warnings, None, None, None, None
    archive.close()

    # check content
    if content_folder is None:
        errors.append("Content folder not found.")
    else:
        _check_content_members(archive_members, content_folder, errors)
    # process meta
    is_extreme = False
    curation_type = None
    props: dict = {}
    if len(meta) == 0:
        errors.append(
            "Meta file is either missing or its filename is incorrect. Are you using Flashpoint Core for curating?")
    elif meta_content is None:
        pass
    else:
        meta_filename = meta[0]
        l.debug(f"Reading metadata file in archive: '{meta_filename}'")
        with io.StringIO(meta_content.decode("utf8")) as meta_file:
            if meta_filename.endswith(".yml") or meta_filename.endswith(".yaml"):
                try:
                    yaml = YAML(typ="safe")
                    props: dict = yaml.load(meta_file)
                    if props is None:
                        errors.append("The meta file seems to be empty.")
                        return errors, warnings, None, None, None, None
                except YAMLError:
                    errors.append(f"Unable to load meta YAML file")
                    return errors, warnings, None, None, None, None
                except ValueError as e:
                    l.debug(f"ValueError reading meta file: {e}")
                    errors.append("Invalid release date. Ensure entered date is valid.")
                    return errors, warnings, None, None, None, None
            elif meta_filename.endswith(".txt"):
                break_index: int = 0
                while break_index != -1:
                    props, break_index = parse_lines_until_multiline(meta_file.readlines(), props,
                                                                     break_index)
                    props, break_index = parse_multiline(meta_file.readlines(), props, break_index)
                    if props.get("Genre") is not None:
                        props["Tags"] = props["Genre"]
            else:
                errors.append(
                    "Meta file is either missing or its filename is incorrect. Are you using Flashpoint Core for curating?")
                return errors, warnings, None, None, None, None

        # translate legacy fields
        if props.get("Platform") is not None:
            props["Platforms"] = props["Platform"]

        # add primary platform if missing
        if "Platforms" in props and "Primary Platform" not in props:
            props["Primary Platform"] = props["Platforms"].split(';')[0].strip()

        title: tuple[str, bool] = ("Title", bool(props.get("Title")))
        # developer: tuple[str, bool] = ("Developer", bool(props["Developer"]))
        release_date: tuple[str, bool] = ("Release Date", bool(props.get("Release Date")))
        if release_date[1]:
            date_string = str(props.get("Release Date")).strip()
            if len(date_string) > 0:
                date_regex = re.compile(r"^\d{4}(-\d{2}){0,2}$")
                if not date_regex.match(date_string):
                    errors.append(
                        f"Release date {date_string} is incorrect. Release dates should always be in `YYYY-MM-DD` format.")

                # check age of release
                year = None
                month = None
                day = None

                if date_string.count("-") == 0:
                    year = int(date_string)
                elif date_string.count("-") == 1:
                    date_split = date_string.split("-")
                    year = int(date_split[0])
                    month = int(date_split[1])
                elif date_string.count("-") == 2:
                    date_split = date_string.split("-")
                    year = int(date_split[0])
                    month = int(date_split[1])
                    day = int(date_split[2])

                if not is_date_more_than_three_years_ago(datetime.now(), year, month, day):
                    warnings.append(f"Release date {date_string} is less than 3 years ago. Curation should be frozen.")

        language_properties: tuple[str, bool] = "Languages", bool(props.get("Languages"))
        if language_properties[1]:
            with open("data/language-codes.json") as f:
                list_of_language_codes: list[dict] = json.load(f)
            with open("data/lang_replacements.json") as f:
                replacements: dict = json.load(f)
            language_str: str = props.get("Languages", "")
            language_codes = language_str.split(";")
            language_codes = [x.strip() for x in language_codes]
            valid_language_codes = []
            for x in list_of_language_codes:
                valid_language_codes.append(x["alpha2"])
            for language_code in language_codes:
                replacement_code = replacements.get(language_code)
                if language_code not in valid_language_codes:
                    if language_code == "":
                        pass
                    elif ',' in language_code:
                        errors.append("Languages should be separated with semicolons, not commas.")
                    elif language_code in [x["English"] for x in list_of_language_codes]:
                        for x in list_of_language_codes:
                            if language_code in x["English"]:
                                errors.append(
                                    f"Languages must be in ISO 639-1 format, so please use `{x['alpha2']}` instead of `{language_code}`")
                    elif replacement_code is not None:
                        language_name = ""
                        for x in list_of_language_codes:
                            if replacement_code == x["alpha2"]:
                                language_name = x["English"]
                        errors.append(
                            f"The correct ISO 639-1 language code for {language_name} is `{replacement_code}`, not `{language_code}`.")
                    else:
                        errors.append(f"Code `{language_code}` is not a valid ISO 639-1 language code.")

        # tag: tuple[str, bool] = ("Tags", bool(props["Tags"]))
        source: tuple[str, bool] = ("Source", bool(props.get("Source")))
        status: tuple[str, bool] = ("Status", bool(props.get("Status")))
        launch_command: tuple[str, bool] = ("Launch Command", bool(props.get("Launch Command")))
        application_path: tuple[str, bool] = ("Application Path", bool(props.get("Application Path")))

        # TODO check description?
        # description: tuple[str, bool] = ("Description", bool(props["Original Description"]))
        # if description[1] is False and (
        #         bool(props["Curation Notes"]) or bool(props["Game Notes"])):
        #     reply += "Make sure you didn't put your description in the notes section.\n"

        simple_mandatory_props: list[tuple[str, bool]] = [title, language_properties, source, launch_command, status,
                                                          application_path]
        if not all([x[1] for x in simple_mandatory_props]):
            for prop in simple_mandatory_props:
                if prop[1] is False:
                    errors.append(f"The `{prop[0]}` property in the meta file is mandatory.")

        if launch_command[1] and "https" in props["Launch Command"]:
            errors.append("Found `https` in launch command. All launch commands must use `http` instead of `https`.")

        if launch_command[1] and props["Launch Command"] in get_launch_commands_bluebot():
            errors.append(
                "Identical launch command already present in the master database. Is your curation a duplicate?")

        # TODO check optional props?
        # optional_props: list[tuple[str, bool]] = [developer, release_date, tag, description]
        # if not all(optional_props[1]): for x in optional_props: if x[1] is False: reply += x[0] +
        # "is missing, but not necessary. Add it if you can find it, but it's okay if you can't.\n"

        tags: list[str] = props.get("Tags", "").split(";") if props.get("Tags", "") is not None else ""
        tags: list[str] = [x.strip() for x in tags]
        tags: list[str] = [x for x in tags if len(x) > 0]

        master_tag_list = get_tag_list()

        if not tags:
            errors.append("Missing tags. At least one tag must be specified.")
        else:
            for tag in tags:
                if tag not in master_tag_list:
                    warnings.append(f"Tag `{tag}` is not a known tag, please verify (did you write it correctly?).")

        extreme: tuple[str, bool] = ("Extreme", bool(props.get("Extreme")))
        blacklisted_tags = get_blacklisted_tag_list_file()
        extreme_tags = get_extreme_tag_list_file()
        is_blacklisted = False
        is_extreme = False
        if extreme[1] and (props["Extreme"] == "Yes" or props["Extreme"] is True):
            is_extreme = True
        if tags:
            has_extreme_tags = bool([tag for tag in tags if tag in extreme_tags])
            has_blacklisted_tags = bool([tag for tag in tags if tag in blacklisted_tags])
            has_legacy_extreme = "LEGACY-Extreme" in tags
            if has_blacklisted_tags or has_extreme_tags or has_legacy_extreme:
                is_extreme = True
            if is_extreme and not has_extreme_tags:
                errors.append("Curation is extreme but lacks extreme tags.")
            if has_blacklisted_tags:
                errors.append("Contains blacklisted tags")

        if props.get("Library") is not None and "theatre" in props.get("Library"):
            curation_type = CurationType.ANIMATION
        else:
            platforms: Optional[str] = props.get("Platforms")
            if platforms is None or "Flash" in platforms:
                curation_type = CurationType.FLASH_GAME
            else:
                curation_type = CurationType.OTHER_GAME

    # map add apps to more 'Extras', 'Message' props and an 'Add Apps' array
    addApps = props.get("Additional Applications")
    addAppsArr = []
    if addApps is not None:
        keys = list(addApps)
        for key in keys:
            if key == "Extras":
                props["Extras"] = addApps["Extras"]
            elif key == "Message":
                props["Message"] = addApps["Message"]
            else:
                addAppsArr.append({
                    "Heading": key,
                    "Application Path": addApps[key]["Application Path"],
                    "Launch Command": addApps[key]["Launch Command"]
                })
    props["Additional Applications"] = addAppsArr
    print(props["Additional Applications"])

    validRuffleValues = ["standalone"]
    ruffleSupport = props.get("Ruffle Support")
    if ruffleSupport is not None:
        if ruffleSupport not in ["standalone"] and ruffleSupport.strip() != "":
            errors.append(f"Ruffle Support must be '' or a value in '" + str(validRuffleValues) + "'")

    return errors, warnings, is_extreme, curation_type, props, images


def encode_image(image_data: bytes):
    if len(image_data) > max_image_size:
        raise ValidationMemberTooLarge
    return base64.b64encode(image_data)


def archive_cleanup(filename, base_path):
    l.debug(f"cleaning up extracted files in {base_path} after the archive '{filename}'...")
    shutil.rmtree(base_path, True)


@cached(cache=TTLCache(maxsize=1, ttl=600))
def get_launch_commands_bluebot() -> list[str]:
    l.debug(f"getting launch commands from bluebot...")
    resp = requests.get(url="https://bluebot.unstable.life/launch-commands")
    return resp.json()["launch_commands"]


@cached(cache=TTLCache(maxsize=1, ttl=600))
def get_tag_list_bluebot() -> list[str]:
    l.debug(f"getting tags from bluebot...")
    resp = requests.get(url="https://bluebot.unstable.life/tags")
    return resp.json()["tags"]


@cached(cache=TTLCache(maxsize=1, ttl=3600))
def get_tag_list_file() -> list[dict[str, str]]:
    l.debug(f"getting tags from file...")
    with open("data/category_tags.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        return data["tags"]

@cached(cache=TTLCache(maxsize=1, ttl=3600))
def get_blacklisted_tag_list_file() -> list[str]:
    l.debug(f"getting blacklisted tags from file...")
    with open("data/blacklisted_tags.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        return data["tags"]

@cached(cache=TTLCache(maxsize=1, ttl=3600))
def get_extreme_tag_list_file() -> list[str]:
    l.debug(f"getting extreme tags from file...")
    with open("data/extreme_tags.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        return data["tags"]


@cached(cache=TTLCache(maxsize=1, ttl=60))
def get_tag_list_wiki() -> list[dict[str, str]]:
    l.debug(f"getting tags from wiki...")
    tags = []
    resp = requests.get(url="https://flashpointarchive.org/datahub/Tags")
    soup = BeautifulSoup(resp.text, "html.parser")
    tables = soup.find_all("table")
    for table in tables:
        rows = table.find_all("tr")
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 2:
                tag = {}
                col = cols[0]
                links = row.find_all('a')
                if len(links) > 0:
                    tag["name"] = links[0].contents[0].strip()
                else:
                    tag["name"] = col.contents[0].strip()

                try:
                    desc = cols[1]
                    tag["description"] = desc.contents[0].strip()
                    tags.append(tag)
                except:
                    pass
    return tags


def get_tag_list() -> list[str]:
    bluebot_tags = get_tag_list_bluebot()
    wiki_tags = [tag["name"] for tag in get_tag_list_wiki()]
    file_tags = [tag["name"] for tag in get_tag_list_file()]
    return list(set(file_tags + bluebot_tags + wiki_tags))


def parse_lines_until_multiline(lines: list[str], d: dict, starting_number: int):
    break_number: int = -1
    for idx, line in enumerate(lines[starting_number:]):
        if '|' not in line and line.strip():
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


def is_date_more_than_three_years_ago(now, year, month=None, day=None):
    if day is None:
        if month is None:
            # Only the year is known, assume it's the last day of the year
            month = 12
            day = 31
        else:
            # The year and month are known, assume it's the last day of the month
            if month in {1, 3, 5, 7, 8, 10, 12}:
                day = 31
            elif month in {4, 6, 9, 11}:
                day = 30
            else:
                if (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0):
                    day = 29
                else:
                    day = 28

    date = datetime(year, month, day)
    three_years_ago = now - timedelta(days=3*365)
    return date < three_years_ago

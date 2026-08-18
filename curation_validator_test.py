import os
import asyncio
import tempfile
import warnings
import zipfile
import py7zr
import pytest
import unittest
from unittest.mock import patch
from repack import repack
from datetime import datetime

from curation_validator import (
    CurationType,
    ValidationMemberTooLarge,
    encode_image,
    is_date_more_than_three_years_ago,
    max_archive_members,
    max_image_size,
    max_validation_images,
    validate_curation,
)

pytest_plugins = ('pytest_asyncio',)

os.environ["REPACK_DIR"] = os.path.dirname(os.path.realpath(__file__)) + '/repack/'


def mock_get_tag_list() -> list[str]:
    return ["A", "B", "E"]


def mock_get_launch_commands_bluebot() -> list[str]:
    return ["http://www.bluemaxima.org/a.html", "http://www.bluemaxima.org/b.html", "http://localflash/lab/c.html"]


class TestCurationValidator(unittest.TestCase):

    def setUp(self):
        self.tag_patcher = patch('curation_validator.get_tag_list')
        self.tag_list = self.tag_patcher.start()
        self.tag_list.side_effect = mock_get_tag_list
        self.launch_command_patcher = patch('curation_validator.get_launch_commands_bluebot')
        self.launch_command_list = self.launch_command_patcher.start()
        self.launch_command_list.side_effect = mock_get_launch_commands_bluebot

    def tearDown(self):
        self.tag_patcher.stop()
        self.launch_command_patcher.stop()

    def test_valid_yaml_meta(self):
        for extension in ["7z", "zip"]:
            errors, warnings, is_extreme, _, _, _ = validate_curation(f"test_curations/test_curation_valid.{extension}")
            self.assertCountEqual(errors, [])
            self.assertCountEqual(warnings, [])
            self.assertFalse(is_extreme)

    def test_invalid_yaml_meta_extreme(self):
        for extension in ["7z", "zip"]:
            errors, warnings, is_extreme, _, _, _ = validate_curation(
                f"test_curations/test_curation_invalid_extreme.{extension}")
            self.assertCountEqual(errors, ["Curation is extreme but lacks extreme tags."])
            self.assertCountEqual(warnings, [])
            self.assertTrue(is_extreme)

    def test_valid_yaml_meta_extreme(self):
        for extension in ["7z", "zip"]:
            errors, warnings, is_extreme, _, _, _ = validate_curation(
                f"test_curations/test_curation_valid_extreme.{extension}")
            self.assertCountEqual(errors, [])
            self.assertCountEqual(warnings, [])
            self.assertTrue(is_extreme)

    def test_valid_legacy(self):
        for extension in ["7z", "zip"]:
            errors, warnings, is_extreme, _, _, _ = validate_curation(
                f"test_curations/test_curation_valid_legacy.{extension}")
            self.assertCountEqual(errors, [])
            self.assertCountEqual(warnings, [])
            self.assertFalse(is_extreme)

    def test_valid_legacy_genre(self):
        for extension in ["7z", "zip"]:
            errors, warnings, is_extreme, _, _, _ = validate_curation(
                f"test_curations/test_curation_valid_legacy_genre.{extension}")
            self.assertCountEqual(errors, [])
            self.assertCountEqual(warnings, [])
            self.assertFalse(is_extreme)

    def test_curation_invalid_archive(self):
        for extension in ["7z", "zip"]:
            errors, warnings, is_extreme, _, _, _ = validate_curation(
                f"test_curations/test_curation_invalid_archive.{extension}")
            self.assertCountEqual(errors, [f"There seems to a problem with your {extension} file."])
            self.assertCountEqual(warnings, [])

    def test_curation_empty_meta(self):
        for extension in ["7z", "zip"]:
            errors, warnings, is_extreme, _, _, _ = validate_curation(
                f"test_curations/test_curation_empty_meta.{extension}")
            self.assertCountEqual(errors, ["The meta file seems to be empty."])
            self.assertCountEqual(warnings, [])

    def test_curation_duplicate_launch_command(self):
        for extension in ["7z", "zip"]:
            errors, warnings, is_extreme, _, _, _ = validate_curation(
                f"test_curations/test_curation_duplicate_launch_command.{extension}")
            self.assertCountEqual(errors, [
                "Identical launch command already present in the master database. Is your curation a duplicate?"])
            self.assertCountEqual(warnings, [])

    def test_curation_capital_extension_logo(self):
        for extension in ["7z", "zip"]:
            errors, warnings, is_extreme, _, _, _ = validate_curation(
                f"test_curations/test_curation_capital_extension_logo.{extension}")
            self.assertCountEqual(errors, ["Logo file extension must be lowercase."])
            self.assertCountEqual(warnings, [])

    def test_curation_capital_extension_screenshot(self):
        for extension in ["7z", "zip"]:
            errors, warnings, is_extreme, _, _, _ = validate_curation(
                f"test_curations/test_curation_capital_extension_screenshot.{extension}")
            self.assertCountEqual(errors, ["Screenshot file extension must be lowercase."])
            self.assertCountEqual(warnings, [])

    # def test_curation_too_large(self):
    #     for extension in ["7z", "zip"]:
    #         errors, warnings, _, _, _, _ = validate_curation(f"test_curations/test_curation_2GB.{extension}")
    #         self.assertCountEqual(errors, [])
    #         self.assertCountEqual(warnings, ["The archive is too large to be validated (`2000MB/1000MB`)."])

    def test_validation_does_not_extract_archive(self):
        with patch.object(zipfile.ZipFile, "extractall", side_effect=AssertionError("unexpected extraction")), \
                patch("py7zr.SevenZipFile.extractall", side_effect=AssertionError("unexpected extraction")), \
                patch("curation_validator.tempfile.mkdtemp", side_effect=AssertionError("unexpected scratch tree")):
            for extension in ["7z", "zip"]:
                errors, warnings, _, _, _, _ = validate_curation(
                    f"test_curations/test_curation_valid.{extension}")
                self.assertCountEqual(errors, [])
                self.assertCountEqual(warnings, [])

    def test_archive_member_limit(self):
        self.assertEqual(max_archive_members, 10_000_000)
        with patch("curation_validator.max_archive_members", 1), \
                patch("curation_validator.zipfile.ZipFile", side_effect=AssertionError("archive was indexed")):
            errors, warnings, _, _, _, _ = validate_curation("test_curations/test_curation_valid.zip")
        self.assertEqual(errors, ["The archive contains too many members (`14/1`)."])
        self.assertEqual(warnings, [])

        with patch("curation_validator.max_archive_members", 1):
            errors, warnings, _, _, _, _ = validate_curation("test_curations/test_curation_valid.7z")
        self.assertEqual(errors, ["The archive contains too many members (`14/1`)."])
        self.assertEqual(warnings, [])

    def test_large_zip_content_is_not_extracted(self):
        with patch("curation_validator.tempfile.mkdtemp", side_effect=AssertionError("unexpected scratch tree")):
            errors, warnings, _, _, _, images = validate_curation("test_curations/test_curation_2GB.zip")
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])
        self.assertEqual(len(images), 2)

    def test_oversized_image_is_not_encoded(self):
        self.assertEqual(max_image_size, 16 * 1024 * 1024)
        with tempfile.TemporaryDirectory() as temp_dir:
            archive_path = os.path.join(temp_dir, "oversized-logo.zip")
            with zipfile.ZipFile("test_curations/test_curation_valid.zip", "r") as source, \
                    zipfile.ZipFile(archive_path, "w") as destination:
                for member in source.infolist():
                    data = source.read(member)
                    if member.filename.endswith("/logo.png"):
                        data = b"\0" * (max_image_size + 1)
                    destination.writestr(member, data)

            errors, warnings, _, _, _, images = validate_curation(archive_path)

        self.assertEqual(errors, [
            "Image `e647a839-c4d8-4c51-8f04-4cf142f1718c/logo.png` exceeds the 16MB validation limit."
        ])
        self.assertEqual(warnings, [])
        self.assertEqual([image["type"] for image in images], ["screenshot"])

    def test_encode_image_enforces_limit(self):
        with self.assertRaises(ValidationMemberTooLarge):
            encode_image(b"\0" * (max_image_size + 1))

    def test_validation_image_count_is_bounded(self):
        self.assertEqual(max_validation_images, 16)
        with patch("curation_validator.max_validation_images", 1):
            errors, warnings, _, _, _, images = validate_curation(
                "test_curations/test_curation_valid.zip")
        self.assertEqual(errors, ["The archive contains too many validation images (`2/1`)."])
        self.assertEqual(warnings, [])
        self.assertEqual([image["type"] for image in images], ["logo"])

    def test_duplicate_screenshot_paths_are_encoded_once(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            archive_path = os.path.join(temp_dir, "duplicate-screenshot.zip")
            with zipfile.ZipFile("test_curations/test_curation_valid.zip", "r") as source, \
                    zipfile.ZipFile(archive_path, "w") as destination:
                screenshot = next(
                    member for member in source.infolist()
                    if member.filename.endswith("/ss.png")
                )
                screenshot_data = source.read(screenshot)
                for member in source.infolist():
                    destination.writestr(member, source.read(member))
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", UserWarning)
                    for _ in range(3):
                        destination.writestr(screenshot.filename, screenshot_data)

            errors, validation_warnings, _, _, _, images = validate_curation(archive_path)

        self.assertEqual(errors, [])
        self.assertEqual(validation_warnings, [])
        self.assertEqual([image["type"] for image in images], ["logo", "screenshot"])

    def test_7z_reads_selected_members_in_one_pass(self):
        extract_calls = []
        original_extract = py7zr.SevenZipFile.extract

        def tracking_extract(archive, *args, **kwargs):
            extract_calls.append(kwargs.get("targets"))
            return original_extract(archive, *args, **kwargs)

        with patch.object(py7zr.SevenZipFile, "extract", new=tracking_extract):
            errors, validation_warnings, _, _, _, _ = validate_curation(
                "test_curations/test_curation_valid.7z")

        self.assertEqual(errors, [])
        self.assertEqual(validation_warnings, [])
        self.assertEqual(len(extract_calls), 1)
        self.assertEqual(len(extract_calls[0]), 3)

    def test_curation_null_languages(self):
        for extension in ["7z", "zip"]:
            errors, warnings, _, _, _, _ = validate_curation(f"test_curations/test_curation_nul_languages.{extension}")
            self.assertCountEqual(errors, ["The `Languages` property in the meta file is mandatory."])
            self.assertCountEqual(warnings, [])

    def test_empty_content(self):
        for extension in ["7z", "zip"]:
            errors, warnings, _, _, _, _ = validate_curation(f"test_curations/test_curation_empty_content.{extension}")
            self.assertCountEqual(errors, ["No files found in content folder."])
            self.assertCountEqual(warnings, [])

    def test_missing_content(self):
        for extension in ["7z", "zip"]:
            errors, warnings, _, _, _, _ = validate_curation(
                f"test_curations/test_curation_missing_content.{extension}")
            self.assertCountEqual(errors, ["Content folder not found."])
            self.assertCountEqual(warnings, [])

    def test_missing_logo(self):
        for extension in ["7z", "zip"]:
            errors, warnings, _, _, _, _ = validate_curation(f"test_curations/test_curation_missing_logo.{extension}")
            self.assertCountEqual(errors, ["Logo file is either missing or its filename is incorrect."])
            self.assertCountEqual(warnings, [])

    def test_missing_meta(self):
        for extension in ["7z", "zip"]:
            errors, warnings, _, _, _, _ = validate_curation(f"test_curations/test_curation_missing_meta.{extension}")
            self.assertCountEqual(errors,
                                  [
                                      "Meta file is either missing or its filename is incorrect. Are you using Flashpoint Core for curating?"])
            self.assertCountEqual(warnings, [])

    def test_missing_root_folder(self):
        for extension in ["7z", "zip"]:
            errors, warnings, _, _, _, _ = validate_curation(
                f"test_curations/test_curation_missing_root_folder.{extension}")
            self.assertCountEqual(errors, [
                "Logo, screenshot, content folder and meta not found. Is your curation structured properly?"])
            self.assertCountEqual(warnings, [])

    def test_missing_ss(self):
        for extension in ["7z", "zip"]:
            errors, warnings, _, _, _, _ = validate_curation(f"test_curations/test_curation_missing_ss.{extension}")
            self.assertCountEqual(errors, ["Screenshot file is either missing or its filename is incorrect."])
            self.assertCountEqual(warnings, [])

    def test_unknown_tag_warning(self):
        for extension in ["7z", "zip"]:
            errors, warnings, _, _, _, _ = validate_curation(f"test_curations/test_curation_unknown_tag.{extension}")
            self.assertCountEqual(errors, [])
            self.assertCountEqual(warnings,
                                  ["Tag `Unknown Tag` is not a known tag, please verify (did you write it correctly?).",
                                   "Tag `Another Unknown Tag` is not a known tag, please verify (did you write it correctly?)."])

    def test_missing_tags(self):
        for extension in ["7z", "zip"]:
            errors, warnings, _, _, _, _ = validate_curation(f"test_curations/test_curation_missing_tags.{extension}")
            self.assertCountEqual(errors, ["Missing tags. At least one tag must be specified."])
            self.assertCountEqual(warnings, [])

    def test_missing_title(self):
        for extension in ["7z", "zip"]:
            errors, warnings, _, _, _, _ = validate_curation(f"test_curations/test_curation_missing_title.{extension}")
            self.assertCountEqual(errors, ["The `Title` property in the meta file is mandatory."])
            self.assertCountEqual(warnings, [])

    def test_missing_application_path_warning(self):
        for extension in ["7z", "zip"]:
            errors, warnings, _, _, _, _ = validate_curation(
                f"test_curations/test_curation_missing_application_path.{extension}")
            self.assertCountEqual(errors, ["The `Application Path` property in the meta file is mandatory."])
            self.assertCountEqual(warnings, [])

    def test_missing_launch_command(self):
        for extension in ["7z", "zip"]:
            errors, warnings, _, _, _, _ = validate_curation(
                f"test_curations/test_curation_missing_launch_command.{extension}")
            self.assertCountEqual(errors, ["The `Launch Command` property in the meta file is mandatory."])
            self.assertCountEqual(warnings, [])

    def test_missing_languages(self):
        for extension in ["7z", "zip"]:
            errors, warnings, _, _, _, _ = validate_curation(
                f"test_curations/test_curation_missing_languages.{extension}")
            self.assertCountEqual(errors, ["The `Languages` property in the meta file is mandatory."])
            self.assertCountEqual(warnings, [])

    def test_comma_in_languages(self):
        for extension in ["7z", "zip"]:
            errors, warnings, _, _, _, _ = validate_curation(
                f"test_curations/test_curation_comma_in_languages.{extension}")
            self.assertCountEqual(errors, ["Languages should be separated with semicolons, not commas."])
            self.assertCountEqual(warnings, [])

    def test_common_bad_language(self):
        for extension in ["7z", "zip"]:
            errors, warnings, _, _, _, _ = validate_curation(
                f"test_curations/test_curation_common_bad_language.{extension}")
            self.assertCountEqual(errors, ["The correct ISO 639-1 language code for Japanese is `ja`, not `jp`."])
            self.assertCountEqual(warnings, [])

    def test_language_name(self):
        for extension in ["7z", "zip"]:
            errors, warnings, _, _, _, _ = validate_curation(f"test_curations/test_curation_language_name.{extension}")
            self.assertCountEqual(errors,
                                  ["Languages must be in ISO 639-1 format, so please use `ja` instead of `Japanese`"])
            self.assertCountEqual(warnings, [])

    def test_missing_source(self):
        for extension in ["7z", "zip"]:
            errors, warnings, _, _, _, _ = validate_curation(f"test_curations/test_curation_missing_source.{extension}")
            self.assertCountEqual(errors, ["The `Source` property in the meta file is mandatory."])
            self.assertCountEqual(warnings, [])

    def test_missing_status(self):
        for extension in ["7z", "zip"]:
            errors, warnings, _, _, _, _ = validate_curation(f"test_curations/test_curation_missing_status.{extension}")
            self.assertCountEqual(errors, ["The `Status` property in the meta file is mandatory."])
            self.assertCountEqual(warnings, [])

    def test_Norway(self):
        for extension in ["7z", "zip"]:
            errors, warnings, _, _, _, _ = validate_curation(f"test_curations/test_curation_Norwegian.{extension}")
            self.assertCountEqual(errors, [])
            self.assertCountEqual(warnings, [])

    def test_rar(self):
        errors, warnings, _, _, _, _ = validate_curation("test_curations/test_curation_rar.rar")
        self.assertCountEqual(errors, ["Curations must be either .zip or .7z, not .rar."])
        self.assertCountEqual(warnings, [])

    def test_trailing_language_semicolon(self):
        for extension in ["7z", "zip"]:
            errors, warnings, _, _, _, _ = validate_curation(
                f"test_curations/test_curation_languages_semicolon.{extension}")
            self.assertCountEqual(errors, [])
            self.assertCountEqual(warnings, [])

    def test_valid_date(self):
        for extension in ["7z", "zip"]:
            errors, warnings, _, _, _, _ = validate_curation(f"test_curations/test_curation_invalid_date.{extension}")
            self.assertCountEqual(errors, ["Invalid release date. Ensure entered date is valid."])
            self.assertCountEqual(warnings, [])

    def test_localflash_too_many_files(self):
        for extension in ["7z", "zip"]:
            errors, warnings, _, _, _, _ = validate_curation(
                f"test_curations/test_curation_localflash_too_many_files.{extension}")
            self.assertCountEqual(errors, [
                "Content must be in additional folder in localflash rather than in localflash directly."])
            self.assertCountEqual(warnings, [])

    def test_localflash_no_folder(self):
        for extension in ["7z", "zip"]:
            errors, warnings, _, _, _, _ = validate_curation(
                f"test_curations/test_curation_localflash_no_folder.{extension}")
            self.assertCountEqual(errors, [
                "Content must be in additional folder in localflash rather than in localflash directly."])
            self.assertCountEqual(warnings, [])

    def test_localflash_bad_name(self):
        for extension in ["7z", "zip"]:
            errors, warnings, _, _, _, _ = validate_curation(
                f"test_curations/test_curation_localflash_bad_name.{extension}")
            self.assertCountEqual(errors, ["Extremely common localflash containing folder name, please change."])
            self.assertCountEqual(warnings, [])

    def test_no_library(self):
        for extension in ["7z", "zip"]:
            errors, warnings, _, curation_type, _, _ = validate_curation(
                f"test_curations/test_curation_none_library.{extension}")
            self.assertCountEqual(errors, [])
            self.assertCountEqual(warnings, [])
            self.assertEqual(curation_type, CurationType.FLASH_GAME)

    def test_convert_platform_field(self):
        for extension in ["7z", "zip"]:
            errors, warnings, _, _, meta, _ = validate_curation(f"test_curations/test_curation_valid.{extension}")
            self.assertCountEqual(errors, [])
            self.assertCountEqual(warnings, [])
            self.assertEqual(meta["Platforms"], "Flash")

    def test_addapps(self):
        for extension in ["7z", "zip"]:
            errors, warnings, _, _, meta, _ = validate_curation(
                f"test_curations/test_curation_valid_addapps.{extension}")
            self.assertCountEqual(errors, [])
            self.assertEqual(meta["Extras"], "test")
            self.assertEqual(meta["Message"], "test")
            self.assertEqual(len(meta["Additional Applications"]), 1)
            self.assertEqual(meta["Additional Applications"][0]["Heading"], "Test")
            self.assertEqual(meta["Additional Applications"][0]["Application Path"], "test")
            self.assertEqual(meta["Additional Applications"][0]["Launch Command"], "test")

    def test_primary_platform(self):
        for extension in ["7z", "zip"]:
            # From empty
            errors, warnings, _, _, meta, _ = validate_curation(f"test_curations/test_curation_valid.{extension}")
            self.assertCountEqual(errors, [])
            self.assertEqual(meta["Primary Platform"], "Flash")
            # From stated
            errors, warnings, _, _, meta, _ = validate_curation(
                f"test_curations/test_curation_primary_platform.{extension}")
            self.assertCountEqual(errors, [])
            self.assertEqual(meta["Primary Platform"], "HTML5")

    def test_ruffle_support(self):
        for extension in ["7z", "zip"]:
            errors, warnings, _, _, meta, _ = validate_curation(
                f"test_curations/test_curation_invalid_ruffle.{extension}")
            self.assertNotEqual(len(errors), 0)


@pytest.mark.asyncio
async def test_bluezip():
    for extension in ["7z", "zip"]:
        errors, output = await repack(f"test_curations/test_curation_valid.{extension}")
        assert len(errors) == 0
        assert os.path.exists(output)


def test_is_date_more_than_three_years_ago():
    cases = [
        {"now": datetime(2003, 1, 1), "year": 2000, "month": 1, "day": 1, "return": True},
        {"now": datetime(2003, 1, 1), "year": 2000, "month": 1, "day": 2, "return": False},
        {"now": datetime(2003, 1, 1), "year": 2002, "month": 2, "day": 20, "return": False},
        {"now": datetime(2003, 1, 1), "year": 2002, "month": None, "day": None, "return": False},
        {"now": datetime(2003, 1, 1), "year": 2002, "month": 1, "day": None, "return": False},
    ]

    for case in cases:
        assert case["return"] == is_date_more_than_three_years_ago(case["now"], case["year"], case["month"], case["day"]), case


if __name__ == '__main__':
    unittest.main()

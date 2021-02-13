import unittest
from typing import List
from unittest.mock import patch

from curation_validator import validate_curation


def mock_get_tag_list() -> List[str]:
    return ["A", "B"]


class TestCurationValidator(unittest.TestCase):

    def setUp(self):
        self.patcher = patch('curation_validator.get_tag_list')
        self.tag_list = self.patcher.start()
        self.tag_list.side_effect = mock_get_tag_list

    def tearDown(self):
        self.patcher.stop()

    def test_curation_too_large(self):
        for extension in ["7z", "zip"]:
            errors, warnings = validate_curation(f"test_curations/test_curation_2GB.{extension}")
            self.assertCountEqual(errors, [])
            self.assertCountEqual(warnings, ["The archive is too large to validate (`2000MB/1000MB`)."])

    def test_empty_content(self):
        for extension in ["7z", "zip"]:
            errors, warnings = validate_curation(f"test_curations/test_curation_empty_content.{extension}")
            self.assertCountEqual(errors, ["No files found in content folder."])
            self.assertCountEqual(warnings, [])

    def test_missing_content(self):
        for extension in ["7z", "zip"]:
            errors, warnings = validate_curation(f"test_curations/test_curation_missing_content.{extension}")
            self.assertCountEqual(errors, ["Content folder not found."])
            self.assertCountEqual(warnings, [])

    def test_missing_logo(self):
        for extension in ["7z", "zip"]:
            errors, warnings = validate_curation(f"test_curations/test_curation_missing_logo.{extension}")
            self.assertCountEqual(errors, ["Logo file is either missing or its filename is incorrect."])
            self.assertCountEqual(warnings, [])

    def test_missing_meta(self):
        for extension in ["7z", "zip"]:
            errors, warnings = validate_curation(f"test_curations/test_curation_missing_meta.{extension}")
            self.assertCountEqual(errors,
                                  ["Meta file is either missing or its filename is incorrect. Are you using Flashpoint Core for curating?"])
            self.assertCountEqual(warnings, [])

    def test_missing_root_folder(self):
        for extension in ["7z", "zip"]:
            errors, warnings = validate_curation(f"test_curations/test_curation_missing_root_folder.{extension}")
            self.assertCountEqual(errors, ["Root directory is either missing or its name is incorrect. It should be in UUIDv4 format."])
            self.assertCountEqual(warnings, [])

    def test_missing_ss(self):
        for extension in ["7z", "zip"]:
            errors, warnings = validate_curation(f"test_curations/test_curation_missing_ss.{extension}")
            self.assertCountEqual(errors, ["Screenshot file is either missing or its filename is incorrect."])
            self.assertCountEqual(warnings, [])

    def test_unknown_tag(self):
        for extension in ["7z", "zip"]:
            errors, warnings = validate_curation(f"test_curations/test_curation_unknown_tag.{extension}")
            self.assertCountEqual(errors, [])
            self.assertCountEqual(warnings, ["Tag `Unknown Tag` is not a known tag.", "Tag `Another Unknown Tag` is not a known tag."])

    def test_valid(self):
        for extension in ["7z", "zip"]:
            errors, warnings = validate_curation(f"test_curations/test_curation_valid.{extension}")
            self.assertCountEqual(errors, [])
            self.assertCountEqual(warnings, [])


if __name__ == '__main__':
    unittest.main()

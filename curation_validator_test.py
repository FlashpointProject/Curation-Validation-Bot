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

    def test_empty_content(self):
        errors, warnings = validate_curation("test_curations/test_curation_empty_content.7z")

        self.assertCountEqual(errors, ["No files found in content folder."])
        self.assertCountEqual(warnings, [])

    def test_missing_content(self):
        errors, warnings = validate_curation("test_curations/test_curation_missing_content.7z")

        self.assertCountEqual(errors, ["Content folder not found."])
        self.assertCountEqual(warnings, [])

    def test_missing_logo(self):
        errors, warnings = validate_curation("test_curations/test_curation_missing_logo.7z")

        self.assertCountEqual(errors, ["Logo file is either missing or its filename is incorrect."])
        self.assertCountEqual(warnings, [])

    def test_missing_meta(self):
        errors, warnings = validate_curation("test_curations/test_curation_missing_meta.7z")

        self.assertCountEqual(errors, ["Meta file is either missing or its filename is incorrect. Are you using Flashpoint Core for curating?"])
        self.assertCountEqual(warnings, [])

    def test_missing_root_folder(self):
        errors, warnings = validate_curation("test_curations/test_curation_missing_root_folder.7z")

        self.assertCountEqual(errors, ["Root directory is either missing or its name is incorrect. It should be in UUIDv4 format."])
        self.assertCountEqual(warnings, [])

    def test_missing_ss(self):
        errors, warnings = validate_curation("test_curations/test_curation_missing_ss.7z")

        self.assertCountEqual(errors, ["Screenshot file is either missing or its filename is incorrect."])
        self.assertCountEqual(warnings, [])

    def test_unknown_tag(self):
        errors, warnings = validate_curation("test_curations/test_curation_unknown_tag.7z")

        self.assertCountEqual(errors, [])
        self.assertCountEqual(warnings, ["Tag `Unknown Tag` is not a known tag.", "Tag `Another Unknown Tag` is not a known tag."])

    def test_valid(self):
        errors, warnings = validate_curation("test_curations/test_curation_valid.7z")

        self.assertCountEqual(errors, [])
        self.assertCountEqual(warnings, [])


if __name__ == '__main__':
    unittest.main()

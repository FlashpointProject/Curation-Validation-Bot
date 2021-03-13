import unittest
from unittest.mock import patch

from curation_validator import validate_curation


def mock_get_tag_list() -> list[str]:
    return ["A", "B"]


def mock_get_launch_commands_bluebot() -> list[str]:
    return ["http://www.bluemaxima.org/a.html", "http://www.bluemaxima.org/b.html"]


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
            errors, warnings, is_extreme = validate_curation(f"test_curations/test_curation_valid.{extension}", True, False)
            self.assertCountEqual(errors, [])
            self.assertCountEqual(warnings, [])
            self.assertFalse(is_extreme)

    def test_valid_yaml_meta_extreme(self):
        for extension in ["7z", "zip"]:
            errors, warnings, is_extreme = validate_curation(f"test_curations/test_curation_valid_extreme.{extension}", True, False)
            self.assertCountEqual(errors, [])
            self.assertCountEqual(warnings, [])
            self.assertTrue(is_extreme)

    def test_valid_legacy(self):
        for extension in ["7z", "zip"]:
            errors, warnings, is_extreme = validate_curation(f"test_curations/test_curation_valid_legacy.{extension}", True, False)
            self.assertCountEqual(errors, [])
            self.assertCountEqual(warnings, [])
            self.assertFalse(is_extreme)

    def test_valid_legacy_genre(self):
        for extension in ["7z", "zip"]:
            errors, warnings, is_extreme = validate_curation(
                f"test_curations/test_curation_valid_legacy_genre.{extension}", True, False)
            self.assertCountEqual(errors, [])
            self.assertCountEqual(warnings, [])
            self.assertFalse(is_extreme)

    def test_curation_invalid_channel_flash(self):
        errors, warnings, is_extreme = validate_curation(f"test_curations/test_curation_other.7z", True, False)
        self.assertCountEqual(errors, [f'If this is a not a flash game, go to #other-game-curations. Otherwise change the Platform to "Flash".'])
        self.assertCountEqual(warnings, [])
        errors, warnings, is_extreme = validate_curation(f"test_curations/test_curation_animation.7z", True, False)
        self.assertCountEqual(errors, [f'If this is an animation and not a game, go to #animation-curations. Otherwise change the Library to "Games".'])
        self.assertCountEqual(warnings, [])

    def test_curation_valid_channel_animation(self):
        errors, warnings, is_extreme = validate_curation(f"test_curations/test_curation_animation.7z", False, False)
        self.assertCountEqual(errors, [])
        self.assertCountEqual(warnings, [])

    def test_curation_invalid_channel_animation(self):
        errors, warnings, is_extreme = validate_curation(f"test_curations/test_curation_other.7z", False, False)
        self.assertCountEqual(errors, [f'If this is a game and not an animation, go to #flash-game-curations or #other-game-curations. Otherwise change the Library to "Animations".'])
        self.assertCountEqual(warnings, [])
        errors, warnings, is_extreme = validate_curation(f"test_curations/test_curation_valid.7z", False, False)
        self.assertCountEqual(errors, [f'If this is a game and not an animation, go to #flash-game-curations or #other-game-curations. Otherwise change the Library to "Animations".'])
        self.assertCountEqual(warnings, [])

    def test_curation_valid_channel_other(self):
        errors, warnings, is_extreme = validate_curation(f"test_curations/test_curation_other.7z", False, True)
        self.assertCountEqual(errors, [])
        self.assertCountEqual(warnings, [])

    def test_curation_invalid_channel_other(self):
        errors, warnings, is_extreme = validate_curation(f"test_curations/test_curation_animation.7z", False, True)
        self.assertCountEqual(errors, [f'If this is an animation and not a game, go to #animation-curations. Otherwise change the Library to "Games".'])
        self.assertCountEqual(warnings, [])
        errors, warnings, is_extreme = validate_curation(f"test_curations/test_curation_valid.7z", False, True)
        self.assertCountEqual(errors, [f'If this is a flash game, go to #flash-game-curations. Otherwise change the Platform to the appropriate one.'])
        self.assertCountEqual(warnings, [])

    def test_curation_empty_meta(self):
        for extension in ["7z", "zip"]:
            errors, warnings, is_extreme = validate_curation(f"test_curations/test_curation_empty_meta.{extension}", False, False)
            self.assertCountEqual(errors, ["The meta file seems to be empty."])
            self.assertCountEqual(warnings, [])

    def test_curation_duplicate_launch_command(self):
        for extension in ["7z", "zip"]:
            errors, warnings, is_extreme = validate_curation(
                f"test_curations/test_curation_duplicate_launch_command.{extension}", True, False)
            self.assertCountEqual(errors, [
                "Identical launch command already present in the master database. Is your curation a duplicate?"])
            self.assertCountEqual(warnings, [])

    def test_curation_capital_extension_logo(self):
        for extension in ["7z", "zip"]:
            errors, warnings, is_extreme = validate_curation(
                f"test_curations/test_curation_capital_extension_logo.{extension}", True, False)
            self.assertCountEqual(errors, ["Logo file extension must be lowercase."])
            self.assertCountEqual(warnings, [])

    def test_curation_capital_extension_screenshot(self):
        for extension in ["7z", "zip"]:
            errors, warnings, is_extreme = validate_curation(
                f"test_curations/test_curation_capital_extension_screenshot.{extension}", True, False)
            self.assertCountEqual(errors, ["Screenshot file extension must be lowercase."])
            self.assertCountEqual(warnings, [])

    def test_curation_too_large(self):
        for extension in ["7z", "zip"]:
            errors, warnings, _ = validate_curation(f"test_curations/test_curation_2GB.{extension}", True, False)
            self.assertCountEqual(errors, [])
            self.assertCountEqual(warnings, ["The archive is too large to be validated (`2000MB/1000MB`)."])

    def test_empty_content(self):
        for extension in ["7z", "zip"]:
            errors, warnings, _ = validate_curation(f"test_curations/test_curation_empty_content.{extension}", True, False)
            self.assertCountEqual(errors, ["No files found in content folder."])
            self.assertCountEqual(warnings, [])

    def test_missing_content(self):
        for extension in ["7z", "zip"]:
            errors, warnings, _ = validate_curation(f"test_curations/test_curation_missing_content.{extension}", True, False)
            self.assertCountEqual(errors, ["Content folder not found."])
            self.assertCountEqual(warnings, [])

    def test_missing_logo(self):
        for extension in ["7z", "zip"]:
            errors, warnings, _ = validate_curation(f"test_curations/test_curation_missing_logo.{extension}", True, False)
            self.assertCountEqual(errors, ["Logo file is either missing or its filename is incorrect."])
            self.assertCountEqual(warnings, [])

    def test_missing_meta(self):
        for extension in ["7z", "zip"]:
            errors, warnings, _ = validate_curation(f"test_curations/test_curation_missing_meta.{extension}", True, False)
            self.assertCountEqual(errors,
                                  [
                                      "Meta file is either missing or its filename is incorrect. Are you using Flashpoint Core for curating?"])
            self.assertCountEqual(warnings, [])

    def test_missing_root_folder(self):
        for extension in ["7z", "zip"]:
            errors, warnings, _ = validate_curation(f"test_curations/test_curation_missing_root_folder.{extension}", True, False)
            self.assertCountEqual(errors, [
                "Logo, screenshot, content folder and meta not found. Is your curation structured properly?"])
            self.assertCountEqual(warnings, [])

    def test_missing_ss(self):
        for extension in ["7z", "zip"]:
            errors, warnings, _ = validate_curation(f"test_curations/test_curation_missing_ss.{extension}", True, False)
            self.assertCountEqual(errors, ["Screenshot file is either missing or its filename is incorrect."])
            self.assertCountEqual(warnings, [])

    def test_unknown_tag_warning(self):
        for extension in ["7z", "zip"]:
            errors, warnings, _ = validate_curation(f"test_curations/test_curation_unknown_tag.{extension}", True, False)
            self.assertCountEqual(errors, [])
            self.assertCountEqual(warnings,
                                  ["Tag `Unknown Tag` is not a known tag, please verify (did you write it correctly?).",
                                   "Tag `Another Unknown Tag` is not a known tag, please verify (did you write it correctly?)."])

    def test_missing_tags(self):
        for extension in ["7z", "zip"]:
            errors, warnings, _ = validate_curation(f"test_curations/test_curation_missing_tags.{extension}", True, False)
            self.assertCountEqual(errors, ["Missing tags. At least one tag must be specified."])
            self.assertCountEqual(warnings, [])

    def test_missing_title(self):
        for extension in ["7z", "zip"]:
            errors, warnings, _ = validate_curation(f"test_curations/test_curation_missing_title.{extension}", True, False)
            self.assertCountEqual(errors, ["The `Title` property in the meta file is mandatory."])
            self.assertCountEqual(warnings, [])

    def test_missing_application_path_warning(self):
        for extension in ["7z", "zip"]:
            errors, warnings, _ = validate_curation(
                f"test_curations/test_curation_missing_application_path.{extension}", True, False)
            self.assertCountEqual(errors, ["The `Application Path` property in the meta file is mandatory."])
            self.assertCountEqual(warnings, [])

    def test_missing_launch_command(self):
        for extension in ["7z", "zip"]:
            errors, warnings, _ = validate_curation(f"test_curations/test_curation_missing_launch_command.{extension}", True, False)
            self.assertCountEqual(errors, ["The `Launch Command` property in the meta file is mandatory."])
            self.assertCountEqual(warnings, [])

    def test_missing_languages(self):
        for extension in ["7z", "zip"]:
            errors, warnings, _ = validate_curation(f"test_curations/test_curation_missing_languages.{extension}", True, False)
            self.assertCountEqual(errors, ["The `Languages` property in the meta file is mandatory."])
            self.assertCountEqual(warnings, [])

    def test_comma_in_languages(self):
        for extension in ["7z", "zip"]:
            errors, warnings, _ = validate_curation(f"test_curations/test_curation_comma_in_languages.{extension}", True, False)
            self.assertCountEqual(errors, ["Languages should be separated with semicolons, not commas."])
            self.assertCountEqual(warnings, [])

    def test_missing_source(self):
        for extension in ["7z", "zip"]:
            errors, warnings, _ = validate_curation(f"test_curations/test_curation_missing_source.{extension}", True, False)
            self.assertCountEqual(errors, ["The `Source` property in the meta file is mandatory."])
            self.assertCountEqual(warnings, [])

    def test_missing_status(self):
        for extension in ["7z", "zip"]:
            errors, warnings, _ = validate_curation(f"test_curations/test_curation_missing_status.{extension}", True, False)
            self.assertCountEqual(errors, ["The `Status` property in the meta file is mandatory."])
            self.assertCountEqual(warnings, [])

    def test_Norway(self):
        for extension in ["7z", "zip"]:
            errors, warnings, _ = validate_curation(f"test_curations/test_curation_Norwegian.{extension}", True, False)
            self.assertCountEqual(errors, [])
            self.assertCountEqual(warnings, [])

    def test_rar(self):
        errors, warnings, _ = validate_curation("test_curations/test_curation_rar.rar", True, False)
        self.assertCountEqual(errors, ["Curations must be either .zip or .7z, not .rar."])
        self.assertCountEqual(warnings, [])

    def test_trailing_language_semicolon(self):
        for extension in ["7z", "zip"]:
            errors, warnings, _ = validate_curation(f"test_curations/test_curation_languages_semicolon.{extension}", True, False)
            self.assertCountEqual(errors, [])
            self.assertCountEqual(warnings, [])


if __name__ == '__main__':
    unittest.main()

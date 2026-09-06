#!/usr/bin/env python3
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import logo_pipeline  # noqa: E402


class LogoPipelineTest(unittest.TestCase):
    def test_android_asset_contract_is_complete(self):
        self.assertEqual(29, len(logo_pipeline.EXPECTED))
        self.assertEqual(27, len(logo_pipeline.EXPECTED_PNGS))
        self.assertEqual(2, len(logo_pipeline.EXPECTED_XMLS))
        self.assertEqual(
            "RGB",
            logo_pipeline.EXPECTED_MODES[
                "android-tv/src/main/res/drawable/banner_v2.png"
            ],
        )
        self.assertIn(
            "android-tv/src/main/res/drawable/banner_v2.png",
            logo_pipeline.EXPECTED,
        )
        self.assertIn(
            "android-tv/store-assets/amazon-fire-tv-app-icon-1280x720.png",
            logo_pipeline.EXPECTED,
        )
        self.assertIn(
            "android-tv/store-assets/amazon-fire-tv-background-1920x1080.png",
            logo_pipeline.EXPECTED,
        )
        self.assertIn(
            "android-tv/store-assets/amazon-tablet-small-icon-114x114.png",
            logo_pipeline.EXPECTED,
        )
        self.assertEqual(2, len(logo_pipeline.REQUIRED_TRANSPARENCY))
        self.assertEqual(5, len(logo_pipeline.REQUIRED_VISIBLE_FOREGROUNDS))
        self.assertIn(
            "android-shared/src/main/res/mipmap-xhdpi/ic_launcher_v2_foreground.png",
            logo_pipeline.REQUIRED_VISIBLE_FOREGROUNDS,
        )
        self.assertNotIn(
            "android-tv/src/main/res/mipmap-xhdpi/banner_v2.png",
            logo_pipeline.EXPECTED,
        )
        self.assertNotIn(
            "android-tv/src/main/res/mipmap-xhdpi/ic_launcher_v2.png",
            logo_pipeline.EXPECTED,
        )

    def test_source_material_is_self_contained(self):
        self.assertTrue((ROOT / "SageTV_VIBE_512_V3.svg").is_file())
        self.assertTrue((ROOT / "sagetv_logo.ini").is_file())
        self.assertTrue((ROOT / "M_PLUS_Rounded_1c/MPLUSRounded1c-ExtraBold.ttf").is_file())

    def test_adaptive_icon_configuration_has_visible_foreground(self):
        config = (ROOT / "sagetv_logo.ini").read_text(encoding="utf-8")
        self.assertIn("artwork_layer = foreground", config)
        self.assertIn("background_color = #05004A", config)
        self.assertIn("[launcher]\n", config)
        self.assertIn("scale = 0.80", config)
        self.assertIn("scale = 0.60", config)

    def test_manifest_refresh_is_bounded_to_logo_owned_paths(self):
        source = Path(logo_pipeline.ROOT / "scripts/logo_pipeline.py").read_text()
        self.assertIn('values.pop("branding/SageTV-Vibe.png", None)', source)
        self.assertIn('"config/logo-assets.sha256"', source)
        self.assertNotIn("project_manifest.py", source)


if __name__ == "__main__":
    unittest.main()

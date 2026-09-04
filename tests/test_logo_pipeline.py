#!/usr/bin/env python3
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import logo_pipeline  # noqa: E402


class LogoPipelineTest(unittest.TestCase):
    def test_android_asset_contract_is_complete(self):
        self.assertEqual(25, len(logo_pipeline.EXPECTED))
        self.assertEqual(23, len(logo_pipeline.EXPECTED_PNGS))
        self.assertEqual(2, len(logo_pipeline.EXPECTED_XMLS))

    def test_source_material_is_self_contained(self):
        self.assertTrue((ROOT / "SageTV_VIBE_512_V3.svg").is_file())
        self.assertTrue((ROOT / "sagetv_logo.ini").is_file())
        self.assertTrue((ROOT / "M_PLUS_Rounded_1c/MPLUSRounded1c-ExtraBold.ttf").is_file())

    def test_manifest_refresh_is_bounded_to_logo_owned_paths(self):
        source = Path(logo_pipeline.ROOT / "scripts/logo_pipeline.py").read_text()
        self.assertIn('values.pop("branding/SageTV-Vibe.png", None)', source)
        self.assertIn('"config/logo-assets.sha256"', source)
        self.assertNotIn("project_manifest.py", source)


if __name__ == "__main__":
    unittest.main()

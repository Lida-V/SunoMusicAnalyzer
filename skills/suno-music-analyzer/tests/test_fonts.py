"""Portability checks for font discovery and explicit-font failure modes."""
import importlib.util
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / 'scripts' / 'suno_report_themes.py'
spec = importlib.util.spec_from_file_location('suno_report_themes_test', MODULE_PATH)
fonts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fonts)


class FontDiscoveryTests(unittest.TestCase):
    def test_candidates_cover_windows_macos_and_linux(self):
        for platform, fragment in [('win32', 'BIZ-UDGothicR.ttc'),
                                   ('darwin', 'ヒラギノ角ゴシック'),
                                   ('linux', 'ipaexg.ttf')]:
            with self.subTest(platform=platform), patch.object(fonts.sys, 'platform', platform), \
                 patch.object(fonts.shutil, 'which', return_value=None):
                self.assertTrue(any(fragment in str(p) for p, _ in fonts._font_candidates()))

    def test_missing_font_reports_actionable_error(self):
        with patch.object(fonts, '_font_candidates', return_value=[]):
            with self.assertRaisesRegex(ValueError, '--font'):
                fonts.register_fonts()

    def test_override_must_exist(self):
        with self.assertRaisesRegex(ValueError, 'Font file not found'):
            fonts.register_fonts(ROOT / 'missing-font.ttf')

    def test_ttc_index_requires_font(self):
        result = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'suno-one-page-report.py'),
                                 'unused.json', '--output', 'unused.pdf', '--font-index', '1'],
                                capture_output=True, text=True, encoding='utf-8')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('--font-index requires --font', result.stderr)

    def test_windows_builtin_and_explicit_ttc_override_if_available(self):
        candidate = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts' / 'BIZ-UDGothicR.ttc'
        if not candidate.is_file():
            self.skipTest('BIZ-UDGothic not installed')
        fonts.register_fonts(candidate, 1)
        self.assertIn('Gothic', fonts.pdfmetrics.getRegisteredFontNames())


if __name__ == '__main__':
    unittest.main()

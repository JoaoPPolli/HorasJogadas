"""Links de download do site e proteção dos arquivos usados como saída."""
import tempfile
import unittest
from pathlib import Path
from scripts.build_site import build


class SiteTests(unittest.TestCase):
    def test_generated_site_has_direct_downloads_and_no_template_tokens(self):
        with tempfile.TemporaryDirectory() as temporary:
            output=build(Path(temporary)/'site')
            html=(output/'index.html').read_text(encoding='utf-8')
            self.assertNotIn('__RELEASE__',html)
            for name in ('HorasJogadas-Windows-Setup.exe','HorasJogadas-Windows-Portable.zip','HorasJogadas-Linux-x86_64.tar.gz','SHA256SUMS.txt'):
                self.assertIn('https://github.com/JoaoPPolli/HorasJogadas/releases/latest/download/'+name,html)
            self.assertTrue((output/'assets'/'library.png').exists())
            history=(output/'changelog'/'index.html').read_text(encoding='utf-8')
            import re
            root=Path(__file__).resolve().parent.parent
            versions=re.findall(r'^## (\d+\.\d+\.\d+)',(root/'CHANGELOG.md').read_text(encoding='utf-8'),re.M)
            self.assertEqual(re.findall(r'data-version="([^"]+)"',history),versions)
            self.assertNotIn('__',history)
            self.assertIn('changelog/',html)
            self.assertIn('/releases/tag/v3.0.1',history)
            self.assertNotIn('/releases/tag/v2.5.0',history)
            build(output)

    def test_existing_user_directory_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary); (root/'keep.txt').write_text('keep')
            with self.assertRaises(ValueError): build(root)
            self.assertEqual((root/'keep.txt').read_text(),'keep')

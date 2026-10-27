"""Links de download do site e proteção dos arquivos usados como saída."""
import tempfile
import unittest
from pathlib import Path
from scripts.build_site import build


class SiteTests(unittest.TestCase):
    def test_generated_site_has_direct_downloads_and_no_template_tokens(self):
        with tempfile.TemporaryDirectory() as temporary:
            output=build(Path(temporary)/'site')
            html=(output/'index.html').read_text()
            self.assertNotIn('__RELEASE__',html)
            for name in ('HorasJogadas-Windows-Setup.exe','HorasJogadas-Windows-Portable.zip','HorasJogadas-Linux-x86_64.tar.gz','SHA256SUMS.txt'):
                self.assertIn('https://github.com/JoaoPPolli/HorasJogadas/releases/latest/download/'+name,html)
            self.assertTrue((output/'assets'/'library.png').exists())
            build(output)

    def test_existing_user_directory_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary); (root/'keep.txt').write_text('keep')
            with self.assertRaises(ValueError): build(root)
            self.assertEqual((root/'keep.txt').read_text(),'keep')

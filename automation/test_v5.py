"""Regression checks for upper-only placement, revised sources and cache invalidation."""
import unittest
from pathlib import Path
from PIL import Image, ImageDraw
from generate import Assets, choose_badge, REVISION_ARCHIVES
from catalog import source_fingerprint

ROOT=Path(__file__).resolve().parents[1]

class V5Tests(unittest.TestCase):
    def test_upper_left_and_frame_clearance(self):
        cx,cy,occupied=choose_badge(Image.new('RGB',(1024,1024),'white'),200,220)
        self.assertEqual(cx,158)
        self.assertGreaterEqual(cx-80-38,40)
        self.assertGreaterEqual(cy-80,212)
        self.assertLessEqual(cy,380)
        self.assertEqual(occupied,0)

    def test_right_when_left_is_occupied(self):
        im=Image.new('RGB',(1024,1024),'white')
        ImageDraw.Draw(im).rectangle((48,210,350,500),fill='black')
        self.assertEqual(choose_badge(im,200,220)[0],866)

    def test_no_bottom_fallback(self):
        im=Image.new('RGB',(1024,1024),'white')
        ImageDraw.Draw(im).rectangle((40,212,984,600),fill='black')
        with self.assertRaisesRegex(ValueError,'badge_review'):
            choose_badge(im,200,220)
        with self.assertRaisesRegex(ValueError,'badge_review'):
            choose_badge(im,200,220,manual=[866,860])

    def test_revised_priority_and_combined_zip_separation(self):
        assets=Assets(ROOT)
        for code,archive in REVISION_ARCHIVES.items():
            item=assets.match(code+'-1','option')
            self.assertEqual(item['archive'],archive)
            self.assertTrue(item['filename'].startswith(code+'-'))
        assets.items=[i for i in assets.items if i['archive']!=REVISION_ARCHIVES['BB0001']]
        with self.assertRaises(FileNotFoundError):assets.match('BB0001-1','option')

    def test_new_source_invalidates_cache(self):
        self.assertNotEqual(source_fingerprint({'code':'SN0004'},['old'],'v5'),
                            source_fingerprint({'code':'SN0004'},['new'],'v5'))

if __name__=='__main__':unittest.main()

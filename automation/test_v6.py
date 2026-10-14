"""V6 regression checks for label protection, overlap review and real resume."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from PIL import Image,ImageDraw
from badge_rules import circle_intersects_box, important_regions
from generate import choose_badge
from catalog import digest, render_catalog, update_archive
from zipfile import ZipFile
ROOT=Path(__file__).resolve().parents[1]

class V6Tests(unittest.TestCase):
    def test_foreground_overlap_alone_is_not_a_failure(self):
        im=Image.new('RGB',(1024,1024),'white')
        ImageDraw.Draw(im).rectangle((40,212,984,600),fill='gray')
        cx,cy,overlap=choose_badge(im,200,220,critical_boxes=[[400,650,600,750]])
        self.assertLess(cx,512)
        self.assertGreater(overlap,.02)
        self.assertGreaterEqual(cx-80-38,40)
        self.assertGreaterEqual(cy-80,212)

    def test_label_protection_selects_right(self):
        center=choose_badge(Image.new('RGB',(1024,1024),'white'),200,220,
                            critical_boxes=[[78,212,430,550]])[:2]
        self.assertGreater(center[0],512)
        self.assertFalse(circle_intersects_box(center,[78,212,430,550]))

    def test_important_regions_never_fall_back_to_bottom(self):
        with self.assertRaisesRegex(ValueError,'badge_review'):
            choose_badge(Image.new('RGB',(1024,1024),'white'),200,220,
                         critical_boxes=[[40,212,984,600]])
        with self.assertRaisesRegex(ValueError,'badge_review'):
            choose_badge(Image.new('RGB',(1024,1024),'white'),200,220,manual=[866,860])

    def test_circle_rectangle_check_does_not_reject_empty_corner(self):
        self.assertFalse(circle_intersects_box((160,300),[225,365,240,380],padding=0))
        self.assertTrue(circle_intersects_box((160,300),[160,300,180,320]))

    def test_annotations_are_bound_to_source_and_geometry(self):
        im=Image.new('RGB',(1024,1024),'white')
        group={'important_region_annotation':{'source_sha256':'old','product_box':[100,200,900,970],
                                               'critical_regions':[]}}
        with self.assertRaisesRegex(ValueError,'annotation does not match'):
            important_regions(im,[100,200,900,970],group,'new')
        with self.assertRaisesRegex(ValueError,'annotation does not match'):
            important_regions(im,[120,200,920,970],group,'old')

    def test_zip_resume_preserves_current_archive_and_detects_changed_image(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);out=root/'out';code='TEST';folder=out/code;folder.mkdir(parents=True)
            image=folder/'thumbnail.png';Image.new('RGB',(20,20),'white').save(image)
            archive=root/'TEST.zip';status={'code':code,'status':'complete'}
            self.assertFalse(update_archive(archive,code,out,[image],status))
            before=(digest(archive),archive.stat().st_mtime_ns)
            self.assertTrue(update_archive(archive,code,out,[image],status))
            self.assertEqual(before,(digest(archive),archive.stat().st_mtime_ns))
            photo=Image.open(image);photo.putpixel((5,5),(255,0,0));photo.save(image)
            self.assertFalse(update_archive(archive,code,out,[image],status))
            with ZipFile(archive) as saved:
                self.assertIsNone(saved.testzip())
                self.assertEqual(saved.read('TEST/thumbnail.png'),image.read_bytes())

    def test_pending_visual_review_approval_and_resume(self):
        # Actual pipeline, isolated outputs/config; all real sources are read-only links.
        code='AB0001'
        with tempfile.TemporaryDirectory() as temporary:
            task=Path(temporary);source=task/'source';source.mkdir();out=task/'output';out.mkdir()
            for p in ROOT.iterdir():
                if p.is_file() and p.suffix in ('.xlsx','.zip','.png'):
                    (source/p.name).symlink_to(p)
            config=source/'automation';config.mkdir()
            for name in ['catalog-overrides.json','catalog-important-regions.json']:
                shutil.copy2(ROOT/'automation'/name,config/name)
            (source/'previews/v5-before').mkdir(parents=True)
            (source/'previews/v5-before'/f'{code}.png').symlink_to(ROOT/'previews/v5-before'/f'{code}.png')
            shutil.copy2(ROOT/'output/v5-original-layouts.json',out/'v5-original-layouts.json')
            pending,_=render_catalog(source,out,only=[code])
            thumbnail=pending['products'][code]['thumbnail']
            self.assertEqual(thumbnail['status'],'review_required')
            self.assertIn('awaits visual verification',thumbnail['error'])
            self.assertFalse((out/code/'thumbnail.png').exists())
            candidate=thumbnail['candidate']
            self.assertTrue((source/candidate['path']).exists())
            review={'decision':'approved','sha256':candidate['sha256'],
                    'source_sha256':candidate['layout']['source']['sha256'],'policy_version':6,
                    'note':'Test fixture: protected-label overlap and geometry checked.'}
            (config/'catalog-v6-reviews.json').write_text(json.dumps({code:review}))
            approved,_=render_catalog(source,out,only=[code])
            self.assertEqual(approved['products'][code]['status'],'complete')
            before={p.relative_to(out):(digest(p),p.stat().st_mtime_ns) for p in (out/code).rglob('*.png')}
            resumed,_=render_catalog(source,out,only=[code])
            after={p.relative_to(out):(digest(p),p.stat().st_mtime_ns) for p in (out/code).rglob('*.png')}
            self.assertEqual(before,after)
            self.assertTrue(resumed['products'][code]['thumbnail']['reused'])

if __name__=='__main__':unittest.main()

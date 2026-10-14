"""Filename contract, continuation rows, and byte-preserving resumable migration."""
import json,tempfile,unittest
from pathlib import Path
from openpyxl import Workbook
from PIL import Image
from catalog import digest,render_catalog
from generate import thumbnail_filename,groups_from_excel
from rename_thumbnails import migrate

class FilenameTests(unittest.TestCase):
    def test_names(self):
        for ref,expected in [('AB0001-2','AB0001-2.png'),('Name.JPG','Name.png'),('한글 이름.PNG','한글 이름.png')]:
            self.assertEqual(thumbnail_filename({'thumbnail_refs':[ref]}),expected)
        for refs in [[],['A','B'],['../A'],['a\\b']]:
            with self.assertRaises(ValueError):thumbnail_filename({'thumbnail_refs':refs})

    def test_migration_and_continuation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);out=root/'output';(out/'AB0001/options').mkdir(parents=True);(root/'automation').mkdir()
            wb=Workbook();ws=wb.active
            ws.append(['품명','브랜드','브랜드 파일명','상품명','썸네일 파일','옵션명','옵션 파일'])
            ws.append(['AB0001','Brand','Brand','Title','AB0001-2','First','AB0001-1'])
            ws.append([None,None,None,None,None,'Second','AB0001-2'])
            wb.save(root/'화장품 썸네일_수정.xlsx')
            groups,errors=groups_from_excel(root/'화장품 썸네일_수정.xlsx')
            self.assertFalse(errors);self.assertEqual(len(groups),1);self.assertEqual(len(groups['AB0001']['options']),2)
            old=out/'AB0001/thumbnail.png';Image.new('RGB',(1024,1024),'white').save(old)
            sha=digest(old);mtime=old.stat().st_mtime_ns
            (out/'AB0001/options/AB0001-1.png').write_bytes(b'unchanged option bytes')
            state={'products':{'AB0001':{'status':'complete','thumbnail':{'status':'success','path':'AB0001/thumbnail.png','sha256':sha}}}}
            (out/'catalog-state.json').write_text(json.dumps(state));(root/'automation/catalog-protected.json').write_text(json.dumps({'output/AB0001/thumbnail.png':sha}))
            migrate(root);migrate(root)
            new=out/'AB0001/AB0001-2.png'
            self.assertEqual(digest(new),sha);self.assertEqual(new.stat().st_mtime_ns,mtime);self.assertFalse(old.exists())
            self.assertEqual(json.loads((out/'catalog-state.json').read_text())['products']['AB0001']['status'],'complete')

    def test_v6_approved_resume(self):
        import shutil
        root=Path(__file__).resolve().parents[1];code='AB0001'
        current=json.loads((root/'output/catalog-state.json').read_text())['products'][code]
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp);shutil.copytree(root/'output'/code,out/code)
            shutil.copy2(root/'output/catalog-source-index.json',out/'catalog-source-index.json')
            (out/'catalog-state.json').write_text(json.dumps({'schema':1,'products':{code:current}}))
            before={str(p.relative_to(out)):(digest(p),p.stat().st_mtime_ns) for p in out.rglob('*.png')}
            state,_=render_catalog(root,out,only=[code])
            self.assertTrue(state['products'][code]['thumbnail']['reused'])
            self.assertEqual(before,{str(p.relative_to(out)):(digest(p),p.stat().st_mtime_ns) for p in out.rglob('*.png')})

if __name__=='__main__':unittest.main()

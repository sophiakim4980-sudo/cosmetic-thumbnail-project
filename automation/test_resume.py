"""Exercise real resume logic in an isolated output folder without rewriting PNGs."""
import json
import shutil
import tempfile
from pathlib import Path

from catalog import digest, render_catalog
from generate import split_title

root=Path(__file__).resolve().parents[1]
assert split_title('Product (4 Colors (3-in-1)) (Second)') == ('Product',['4 Colors 3-in-1','Second'])
code='NF0001'
current=json.loads((root/'output/catalog-state.json').read_text())['products'][code]
with tempfile.TemporaryDirectory() as temp:
    out=Path(temp)
    shutil.copytree(root/'output'/code,out/code)
    shutil.copy2(root/'output/analysis.json',out/'analysis.json')
    (out/'catalog-state.json').write_text(json.dumps({'schema':1,'products':{code:current}}))
    before={p.relative_to(out):(digest(p),p.stat().st_mtime_ns) for p in (out/code).rglob('*.png')}
    state,_=render_catalog(root,out,only=[code])
    after={p.relative_to(out):(digest(p),p.stat().st_mtime_ns) for p in (out/code).rglob('*.png')}
    assert before==after, 'Valid completed PNGs were unnecessarily rewritten'
    assert state['products'][code]['thumbnail']['reused'] is True
    assert all(o['reused'] is True for o in state['products'][code]['options'].values())
print('PASS: nested parentheses and real product resume reused all PNGs with identical hashes and modification times')

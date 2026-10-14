"""Validate sample matching, geometry, output archives, and unchanged option pixels."""
import json
import argparse
import tempfile
from pathlib import Path
from zipfile import ZipFile

from openpyxl import Workbook
from PIL import Image, ImageChops

from generate import Assets, SAMPLES, groups_from_excel, split_title, make_thumbnail, thumbnail_filename

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path, default=ROOT/'output')
OUT = parser.parse_args().output.resolve()
PREVIEWS = ROOT/'previews' if OUT == (ROOT/'output').resolve() else OUT
report = json.loads((OUT/'analysis.json').read_text(encoding='utf-8'))
assets = Assets(ROOT)

assert split_title('Example (A) Product (B)') == ('Example Product', ['A', 'B'])
assert split_title('Juice Moisturizing Sunscreen') == ('Juice Moisturizing Sunscreen', [])
with tempfile.TemporaryDirectory() as tmp:
    wb = Workbook()
    ws = wb.active
    ws.append(['품명','브랜드','상품명','옵션명','브랜드 파일명','옵션 파일','썸네일 파일'])
    ws.append(['A','Brand','Title','one','LOGO','A-1','A-2'])
    ws.append([None,None,None,'two',None,'A-2',None])
    ws.append(['B','Other','Next','one',None,'B-1','B-2'])
    path = Path(tmp)/'group-test.xlsx'; wb.save(path)
    groups, errors = groups_from_excel(path)
    assert not errors and len(groups['A']['options']) == 2
    assert groups['A']['brand_refs'] == ['LOGO'] and groups['B']['brand_refs'] == []

expected = {'RL0001': ['RL0001-1.png','RL0001-2.png'],
            'LL0001': ['LL0001-1.png','LL0001-2.png'],
            'WM0001': ['WM0001-1.png','WM0001-2.png','WM0001-3.png']}
for code in SAMPLES:
    sample = report['samples'][code]
    assert sample['status'] == 'success'
    assert [o['output'] for o in sample['options']] == expected[code]
    thumb = Image.open(OUT/code/thumbnail_filename(report['groups'][code]))
    assert thumb.size == (1024,1024) and thumb.format == 'PNG'
    layout = sample['thumbnail']
    assert thumb.getpixel((0,0)) == (255,255,255)
    assert layout['frame_width'] == 26 and layout['frame_inset'] == 12
    assert all(thumb.getpixel((x,512)) == tuple(layout['frame_rgb']) for x in range(12,38))
    assert thumb.getpixel((38,512)) == (255,255,255)
    assert thumb.getpixel((44,44)) == (255,255,255)
    assert layout['badge_box'][2]-layout['badge_box'][0] == 160
    assert layout['badge_resized_product'] is False
    assert layout['badge_occupied_fraction'] < .02
    px,py,pw,ph = layout['product_box']
    assert 38 < px < pw < 986 and 38 < py < ph < 986
    assert abs((pw-px)/(ph-py)-layout['source_aspect_ratio']) < .003
    area = layout['product_area']
    assert min((area[2]-area[0])/(pw-px), (area[3]-area[1])/(ph-py)) < 1.003
    assert layout['logo_box'][3] < min(b[1] for b in layout['title_boxes'])
    cx,cy = [(layout['badge_box'][k]+layout['badge_box'][k+2])//2 for k in (0,1)]
    assert thumb.getpixel((cx,cy-60)) == tuple(layout['frame_rgb'])
    if layout['subtitle_boxes']:
        assert min(b[1] for b in layout['subtitle_boxes']) > max(b[3] for b in layout['title_boxes'])
        assert layout['product_box'][1] > max(b[3] for b in layout['subtitle_boxes'])
    else:
        assert layout['product_box'][1] > max(b[3] for b in layout['title_boxes'])
    for option in sample['options']:
        original = assets.image(option['source'])
        result = Image.open(OUT/code/'options'/option['output']).convert('RGBA')
        assert result.size == original.size == tuple(option['size'])
        box = option['logo_box']
        assert box[0] > result.width/2 and box[1] < result.height*.05
        diff = ImageChops.difference(original, result)
        channels = diff.split()
        combined = channels[0]
        for channel in channels[1:]: combined = ImageChops.lighter(combined, channel)
        bounds = combined.getbbox()
        assert bounds is not None
        assert bounds[0] >= box[0] and bounds[1] >= box[1]
        assert bounds[2] <= box[2] and bounds[3] <= box[3]
    with ZipFile(OUT/f'{code}.zip') as z:
        assert z.testzip() is None
        assert set(z.namelist()) == {f'{code}/{thumbnail_filename(report["groups"][code])}', *[f'{code}/options/{n}' for n in expected[code]]}
        for name in z.namelist(): assert z.read(name) == (OUT/name).read_bytes()
    Image.open(PREVIEWS/f'{code}-preview.png').verify()
assert set(report['samples']) == set(SAMPLES)
assert assets.match('RL0001-1','option')['archive'] == '화장품 썸네일-1.zip'

# Exercise shared fitting with both tall and wide inputs, not only sample shapes.
class SyntheticAssets:
    def __init__(self, size): self.size = size
    def match(self, value, role): return {'role': role}
    def image(self, item):
        return Image.new('RGBA', (240,40) if item['role'] == 'brand' else self.size,
                         'black' if item['role'] == 'brand' else '#257caf')

with tempfile.TemporaryDirectory() as tmp:
    product = {'brand_refs':['logo'], 'thumbnail_refs':['image'],
               'title':'A Longer Product Name That Wraps (First Note) (Second Note)'}
    results = []
    for size in [(200,700),(1000,250)]:
        layout = make_thumbnail(product, SyntheticAssets(size), Path(tmp)/f'{size[0]}.png')
        assert layout['subtitles'] == ['First Note','Second Note']
        assert layout['badge_resized_product'] is False
        assert len(layout['title_boxes']) > 1
        results.append(layout)
    assert results[0]['product_box'] != results[1]['product_box']
print('PASS: grouping, title splitting, exact sample mapping, 3 thumbnails, 7 options, geometry, source pixel preservation, 3 ZIPs, previews')

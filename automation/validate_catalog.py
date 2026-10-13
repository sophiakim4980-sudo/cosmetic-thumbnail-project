"""Audit every produced file, source mapping, sample preservation and archive."""
import csv
import io
import json
from pathlib import Path
from zipfile import ZipFile

from PIL import Image

from catalog import checked_option, checked_thumbnail, digest, atomic_json
from generate import Assets, groups_from_excel

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output'
state=json.loads((OUT/'catalog-state.json').read_text())
index=json.loads((OUT/'catalog-source-index.json').read_text())
groups=index['groups'];products=state['products']
assert set(groups)==set(products), 'Unrun/extra product groups'
assets=Assets(ROOT)
mark=Image.open(ROOT/'pick&mood.kr 로고.png').convert('RGBA')
protected=json.loads((ROOT/'automation/catalog-protected.json').read_text())
for name,checksum in protected.items():assert digest(ROOT/name)==checksum, f'Protected file changed: {name}'

counts={'raw_excel_product_codes':len(groups_from_excel(ROOT/'화장품 썸네일.xlsx')[0]),
        'corrected_product_groups':len(groups),'brands':len({g['brand'] for g in groups.values()}),
        'thumbnails':0,'options':0,'zips':0,'complete_products':0,'incomplete_products':0,
        'missing_thumbnail_products':[],'missing_option_references':[],
        'blank_option_reference_rows':[],'unexpected_render_failures':[]}
errors=[];rows=[];asset_missing=set()
for number,(code,g) in enumerate(groups.items(),1):
    p=products[code];thumb=p['thumbnail'];files={}
    try:
        assert len(g['brand_refs'])==len(g['thumbnail_refs'])==1
        assets.match(g['brand_refs'][0],'brand');assets.match(g['thumbnail_refs'][0],'thumbnail')
        available=True
    except FileNotFoundError as e:
        available=False;asset_missing.add(str(e).split(': ',1)[-1])
    assert available==(thumb['status']=='success'), f'Resolvable thumbnail not produced: {code}: {thumb}'
    if available:
        path=OUT/thumb['path'];assert digest(path)==thumb['sha256']
        checked_thumbnail(path,thumb['layout'],g,assets)
        files[f'{code}/thumbnail.png']=path
        counts['thumbnails']+=1
        if thumb['layout']['badge_occupied_fraction']>.02:
            review=thumb.get('visual_review')
            assert review and review['sha256']==thumb['sha256'], f'Unreviewed badge: {code}'
    else:
        counts['missing_thumbnail_products'].append(code)
        assert not (OUT/code/'thumbnail.png').exists(), 'Failed item has a stale thumbnail'
    refs={o['reference'] for o in g['options']}
    assert refs==set(p['options']), f'Missing option status: {code}'
    option_count=0
    for ref in refs:
        option=p['options'][ref]
        try:
            item=assets.match(ref,'option');available=True
        except FileNotFoundError:
            available=False;asset_missing.add(ref)
        assert available==(option['status']=='success'), f'Resolvable option not produced: {code}/{ref}'
        if available:
            assert option['source']['sha256']==item['sha256']
            path=OUT/option['path'];assert path.parent==OUT/code/'options'
            assert path.name==Path(item['filename']).stem+'.png'
            assert digest(path)==option['sha256']
            checked_option(path,option['layout'],assets.image(item),mark)
            files[f'{code}/options/{path.name}']=path
            option_count+=1;counts['options']+=1
        else:
            counts['missing_option_references'].append({'code':code,'reference':ref})
    assert set((OUT/code/'options').glob('*.png'))=={p for n,p in files.items() if '/options/' in n}
    issues=p['issues'];errors += [{'code':code,**issue} for issue in issues]
    counts['blank_option_reference_rows'] += [{'code':code,'row':i['row']} for i in issues if i['type']=='missing_option_reference']
    assert (p['status']=='complete') == (thumb['status']=='success' and option_count==len(refs) and not issues)
    counts['complete_products' if p['status']=='complete' else 'incomplete_products']+=1
    zip_path=ROOT/p['zip']['path'];assert digest(zip_path)==p['zip']['sha256']
    with ZipFile(zip_path) as z:
        assert z.testzip() is None
        assert set(z.namelist())==set(files)|{f'{code}/STATUS.json'}
        status=json.loads(z.read(f'{code}/STATUS.json'))
        assert status['status']==p['status'] and status['options_present']==option_count
        assert status['thumbnail_present']==(thumb['status']=='success')
        for name,path in files.items():assert z.read(name)==path.read_bytes(), name
    counts['zips']+=1
    rows.append([code,p['status'],thumb['status'],option_count,len(refs),'; '.join(i['type'] for i in issues)])
    if number%25==0:print(f'Validated {number}/{len(groups)} products',flush=True)

assert set(p.name for p in OUT.glob('*/thumbnail.png')) == {'thumbnail.png'}
assert len(list(OUT.glob('*/thumbnail.png')))==counts['thumbnails']
assert len(list(OUT.glob('*/options/*.png')))==counts['options']
assert len(list((ROOT/'archives').glob('*.zip')))==len(groups)
for path in (ROOT/'previews/catalog').glob('page-*.png'):Image.open(path).verify()
counts['unique_missing_asset_references']=sorted(asset_missing)
counts['validation']='passed for every produced file; incomplete entries remain explicitly recorded'
counts['protected_files_verified']=len(protected)
atomic_json(OUT/'catalog-summary.json',counts)
(OUT/'catalog-errors.jsonl').write_text(''.join(json.dumps(e,ensure_ascii=False)+'\n' for e in errors),encoding='utf-8')
buffer=io.StringIO();writer=csv.writer(buffer,lineterminator='\n')
writer.writerow(['code','status','thumbnail_status','options_generated','option_references','issues']);writer.writerows(rows)
(OUT/'catalog-completed.csv').write_text(buffer.getvalue(),encoding='utf-8-sig')
print(json.dumps(counts,ensure_ascii=False,indent=2),flush=True)

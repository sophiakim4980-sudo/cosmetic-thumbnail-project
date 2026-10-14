"""Resumable full-catalog production using the approved shared sample renderer."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo, BadZipFile

from PIL import Image, ImageChops, ImageDraw
from badge_rules import circle_intersects_box

from generate import (Assets, SAMPLES, font, groups_from_excel, make_option,
                      make_thumbnail, split_title, white_image, relocate_thumbnail, REVISION_ARCHIVES)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_json(path, data):
    temporary = path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    os.replace(temporary, path)


def checked_thumbnail(path, layout, group, assets):
    with Image.open(path) as im:
        im.load()
        assert im.format == 'PNG' and im.size == (1024,1024)
        assert im.getpixel((0,0)) == (255,255,255)
        assert im.getpixel((44,44)) == (255,255,255)
        color = tuple(layout['frame_rgb'])
        assert layout['frame_width'] == 26 and layout['frame_inset'] == 12
        assert all(im.getpixel((x,512)) == color for x in range(12,38))
        assert layout['main_title'], 'Empty main title'
        assert (layout['main_title'],layout['subtitles']) == split_title(group['title'])
        assert layout['brand_logo']['sha256'] == assets.match(group['brand_refs'][0],'brand')['sha256']
        assert layout['source']['sha256'] == assets.match(group['thumbnail_refs'][0],'thumbnail')['sha256']
        boxes = layout['title_boxes']+layout['subtitle_boxes']
        assert layout['logo_box'][3] < min(b[1] for b in layout['title_boxes'])
        assert max(b[3] for b in boxes) < layout['product_box'][1]
        if layout['subtitle_boxes']:
            assert min(b[1] for b in layout['subtitle_boxes']) > max(b[3] for b in layout['title_boxes'])
        x,y,x1,y1 = layout['product_box']
        assert 38 < x < x1 < 986 and 38 < y < y1 < 986
        assert abs((x1-x)/(y1-y)-layout['source_aspect_ratio']) < .01
        a=layout['product_area']
        assert min((a[2]-a[0])/(x1-x), (a[3]-a[1])/(y1-y)) < 1.004
        b=layout['badge_box']
        assert b[2]-b[0] == b[3]-b[1] == 160
        assert 78 <= b[0] < b[2] <= 946 and 78 <= b[1] < b[3] <= 946
        text_bottom=max(v[3] for v in boxes)
        assert b[1] >= text_bottom+12 and b[1]+80 <= layout['product_area'][1]+160
        assert layout['badge_position'] in ('upper_left','upper_right')
        assert layout['badge_frame_clearance'] >= 40
        if layout.get('design_version',5) >= 6:
            assert not any(circle_intersects_box((b[0]+80,b[1]+80),box) for box in layout['critical_regions']), 'Important label covered'
        else:
            assert layout['badge_occupied_fraction'] <= .02
        assert layout['badge_resized_product'] is False
        assert im.getpixel(((b[0]+b[2])//2,(b[1]+b[3])//2-60)) == color


def checked_option(path, details, source, mark):
    original = source.copy()
    with Image.open(path) as im:
        im.load()
        assert im.format == 'PNG' and im.size == original.size == tuple(details['size'])
        actual = im.convert('RGBA')
    b=details['logo_box']
    assert 0 <= b[0] < b[2] < original.width and 0 <= b[1] < b[3] < original.height
    assert b[0] > original.width/2 and b[1] < original.height*.1
    diff = ImageChops.difference(actual,original)
    merged=diff.split()[0]
    for channel in diff.split()[1:]: merged=ImageChops.lighter(merged,channel)
    bounds=merged.getbbox()
    assert bounds and bounds[0] >= b[0] and bounds[1] >= b[1] and bounds[2] <= b[2] and bounds[3] <= b[3]
    logo=mark.crop(mark.getbbox())
    logo.thumbnail((round(original.width*.19),round(original.height*.10)),Image.Resampling.LANCZOS)
    expected=original.copy(); expected.alpha_composite(logo,(b[0],b[1]))
    assert actual.tobytes() == expected.tobytes(), 'Logo composite differs'


def image_atomic(destination, create, validate):
    destination.parent.mkdir(parents=True,exist_ok=True)
    with NamedTemporaryFile(suffix='.png',dir=destination.parent,delete=False) as f:
        temporary=Path(f.name)
    try:
        details=create(temporary)
        validate(temporary,details)
        os.replace(temporary,destination)
        return details
    finally:
        temporary.unlink(missing_ok=True)


def source_fingerprint(group, references, renderer):
    value={'group':group,'sources':references,'renderer':renderer}
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def valid_saved(component, path, fingerprint):
    return (component.get('status') == 'success' and component.get('fingerprint') == fingerprint
            and path.exists() and component.get('sha256') == digest(path))


def render_catalog(root, output, only=(), retry_failed=False):
    if output == root or root.is_relative_to(output):
        raise ValueError('Output must not contain or equal the source root')
    output.mkdir(parents=True,exist_ok=True)
    state_path=output/'catalog-state.json'
    state=json.loads(state_path.read_text()) if state_path.exists() else {'schema':1,'products':{}}
    previous_index_path=output/'catalog-source-index.json'
    previous_groups=json.loads(previous_index_path.read_text()).get('groups',{}) if previous_index_path.exists() else {}
    previous=json.loads((output/'analysis.json').read_text()) if (output/'analysis.json').exists() else {}
    assets=Assets(root)
    overrides_path=root/'automation'/'catalog-overrides.json'
    overrides=json.loads(overrides_path.read_text()) if overrides_path.exists() else {}
    groups,excel_errors=groups_from_excel(root/'화장품 썸네일_수정.xlsx')
    for code in overrides.get('allow_product_translation', []):
        if code in groups: groups[code]['allow_product_translation'] = True
    for code, center in overrides.get('badge_centers', {}).items():
        if code in groups: groups[code]['badge_center'] = center
    annotations_path=root/'automation/catalog-important-regions.json'
    annotations=json.loads(annotations_path.read_text()).get('products',{}) if annotations_path.exists() else {}
    for code,annotation in annotations.items():
        if code in groups:
            groups[code].update(badge_policy_version=6,allow_product_translation=False,important_region_annotation=annotation)
    for code,translation in overrides.get('v6_product_translation',{}).items():
        if code in groups: groups[code]['v6_product_translation']=translation
    reviews_path=root/'automation/catalog-v6-reviews.json'
    v6_reviews=json.loads(reviews_path.read_text()) if reviews_path.exists() else {}
    baselines_path=output/'v5-original-layouts.json'
    baselines=json.loads(baselines_path.read_text()) if baselines_path.exists() else {}
    renderer=hashlib.sha256((digest(Path(__file__).with_name('generate.py'))+
                             digest(Path(__file__).with_name('badge_rules.py'))).encode()).hexdigest()
    mark=Image.open(root/'pick&mood.kr 로고.png').convert('RGBA')
    mark_hash=digest(root/'pick&mood.kr 로고.png')
    atomic_json(output/'catalog-source-index.json',{'archives':assets.archives,'groups':groups,'excel_errors':excel_errors,
                                                 'user_confirmed_overrides':overrides})
    unknown=set(only)-groups.keys()
    if unknown: raise ValueError(f'Unknown product codes: {sorted(unknown)}')
    selected=list(only) if only else list(groups)
    if retry_failed:
        selected=[c for c in selected if state['products'].get(c,{}).get('status') != 'complete']
    for count,code in enumerate(selected,1):
        group=groups[code]
        old=state['products'].get(code,{})
        result={'code':code,'status':'processing','thumbnail':old.get('thumbnail',{}),
                'options':{},'issues':[e for e in excel_errors if e.get('code') == code]}
        folder=output/code
        (folder/'options').mkdir(parents=True,exist_ok=True)
        conflicts=[e for e in result['issues'] if e['type'] == 'conflicting_metadata']
        ambiguous_brand=len(group['observed_brands']) > 1
        ambiguous_rows={e['row'] for e in conflicts if e.get('field') == '브랜드'}
        # A brand change on a blank-code continuation also taints subsequent rows
        # of that same different brand, already diagnosed by groups_from_excel.
        candidate_details=None
        try:
            if conflicts:
                raise ValueError('Conflicting Excel product metadata; correction required')
            if len(group['brand_refs']) != 1 or len(group['thumbnail_refs']) != 1:
                raise ValueError('Exactly one explicit brand/thumbnail reference required')
            refs=[assets.match(group['brand_refs'][0],'brand'),assets.match(group['thumbnail_refs'][0],'thumbnail')]
            fingerprint=source_fingerprint(group,[i['sha256'] for i in refs],renderer)
            path=folder/'thumbnail.png'
            if (valid_saved(old.get('thumbnail',{}),path,fingerprint)
                    and old['thumbnail']['layout'].get('design_version') in (5,6)):
                details=old['thumbnail']['layout']; reused=True
                checked_thumbnail(path,details,group,assets)
            elif (code not in annotations and previous_groups.get(code)==group
                    and old.get('thumbnail',{}).get('status')=='success' and path.exists()
                    and digest(path)==old['thumbnail'].get('sha256')):
                # Preserve already approved designs when sources and effective metadata match.
                details=old['thumbnail']['layout'];checked_thumbnail(path,details,group,assets);reused=True
            else:
                prior=old.get('thumbnail',{})
                baseline_path=path
                if (prior.get('status') != 'success' or code in annotations) and code in baselines:
                    prior=baselines[code]
                    baseline_path=root/'previews/v5-before'/f'{code}.png'
                layout=prior.get('layout',{})
                preserve=(code not in REVISION_ARCHIVES and prior.get('status') == 'success'
                    and baseline_path.exists() and digest(baseline_path) == prior.get('sha256')
                    and (layout.get('main_title'),layout.get('subtitles')) == split_title(group['title'])
                    and layout.get('source',{}).get('sha256') == refs[1]['sha256']
                    and layout.get('brand_logo',{}).get('sha256') == refs[0]['sha256'])
                create=(lambda p:relocate_thumbnail(group,assets,baseline_path,layout,p)) if preserve else (lambda p:make_thumbnail(group,assets,p))
                details=image_atomic(path,create,lambda p,d:checked_thumbnail(p,d,group,assets)); reused=False
            result['thumbnail']={'status':'success','path':str(path.relative_to(output)),
                                 'sha256':digest(path),'fingerprint':fingerprint,'reused':reused,'layout':details}
            if details.get('design_version') == 6:
                review=v6_reviews.get(code,{})
                approved=(review.get('decision')=='approved' and review.get('sha256')==digest(path)
                          and review.get('source_sha256')==details['source']['sha256'])
                if details.get('visual_review_required') and not approved:
                    candidate_details=details
                    raise ValueError('badge_review: V6 candidate awaits visual verification of important labels and design')
                if approved: result['thumbnail']['visual_review']=review
            elif details['badge_occupied_fraction'] > .02:
                result['issues'].append({'type':'badge_review','occupied_fraction':details['badge_occupied_fraction']})
        except Exception as e:
            stale=folder/'thumbnail.png'
            candidate=None
            if candidate_details and stale.exists():
                import shutil
                candidate_path=root/'previews/v6-candidates'/f'{code}.png'
                candidate_path.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(stale,candidate_path)
                candidate={'path':str(candidate_path.relative_to(root)),'sha256':digest(candidate_path),'layout':candidate_details}
            if stale.exists():
                backup=root/'previews'/'v5-before'/f'{code}.png'
                backup.parent.mkdir(parents=True,exist_ok=True)
                if not backup.exists():
                    import shutil
                    shutil.copy2(stale,backup)
                stale.unlink()
            result['thumbnail']={'status':'review_required' if 'badge_review:' in str(e) else 'failed','error':str(e)}
            if candidate: result['thumbnail']['candidate']=candidate
            result['issues'].append({'type':'thumbnail_review' if 'badge_review:' in str(e) else 'thumbnail_failed','error':str(e)})
        state['products'][code]=result
        atomic_json(state_path,state)
        for option in group['options']:
            ref=option['reference']
            if ref in result['options']:
                result['options'][ref]['rows'].append(option['row']); continue
            component={'reference':ref,'rows':[option['row']],'name':option['name']}
            try:
                if ambiguous_brand and option['row'] in ambiguous_rows:
                    raise ValueError('Blank product code changes brand; assigning this option would mix products')
                item=assets.match(ref,'option')
                filename=Path(item['filename']).stem+'.png'
                path=folder/'options'/filename
                fingerprint=source_fingerprint({'reference':ref},[item['sha256'],mark_hash],'option-v5-revised' if code in REVISION_ARCHIVES else 'option-v1')
                saved=old.get('options',{}).get(ref,{})
                source=assets.image(item)
                if valid_saved(saved,path,fingerprint):
                    details=saved['layout']; reused=True
                    checked_option(path,details,source,mark)
                else:
                    details=image_atomic(path,lambda p:make_option(source,mark,p),
                                         lambda p,d:checked_option(p,d,source,mark)); reused=False
                component.update({'status':'success','path':str(path.relative_to(output)),
                                  'sha256':digest(path),'fingerprint':fingerprint,'reused':reused,
                                  'source':item,'layout':details})
            except Exception as e:
                component.update({'status':'failed','error':str(e)})
                result['issues'].append({'type':'option_failed','row':option['row'],'reference':ref,'error':str(e)})
            result['options'][ref]=component
            atomic_json(state_path,state)
        component_failures=result['thumbnail']['status'] != 'success' or any(o['status'] != 'success' for o in result['options'].values())
        result['status']='incomplete' if component_failures or result['issues'] else 'complete'
        result['expected_option_references']=len({o['reference'] for o in group['options']})
        state['products'][code]=result
        atomic_json(state_path,state)
        print(f"[{count}/{len(selected)}] {code}: {result['status']}; thumbnail={result['thumbnail']['status']}; options={sum(o['status']=='success' for o in result['options'].values())}/{result['expected_option_references']}",flush=True)
    return state,groups


def update_archive(path, code, output, files, status):
    """Preserve an existing ZIP byte-for-byte if its contents are already current."""
    expected={str(Path(code)/file.relative_to(output/code)):file for file in files}
    status_name=f'{code}/STATUS.json'
    status_bytes=json.dumps(status,ensure_ascii=False,indent=2).encode('utf-8')
    if path.exists():
        try:
            with ZipFile(path) as archive:
                if (set(archive.namelist()) == set(expected)|{status_name}
                        and archive.testzip() is None and archive.read(status_name)==status_bytes
                        and all(archive.read(name)==file.read_bytes() for name,file in expected.items())):
                    return True
        except (OSError,ValueError,KeyError,BadZipFile):
            pass
    temporary=path.with_suffix('.zip.tmp')
    with ZipFile(temporary,'w',ZIP_DEFLATED) as archive:
        for name,file in expected.items(): archive.write(file,name)
        archive.writestr(ZipInfo(status_name,date_time=(1980,1,1,0,0,0)),status_bytes,compress_type=ZIP_DEFLATED)
    os.replace(temporary,path)
    return False


def package_and_previews(root,output,state,groups):
    archives=root/'archives'; archives.mkdir(exist_ok=True)
    previews=root/'previews'/'catalog'; previews.mkdir(parents=True,exist_ok=True)
    products=state['products']
    reviews_path=root/'automation'/'catalog-badge-reviews.json'
    reviews=json.loads(reviews_path.read_text()) if reviews_path.exists() else {}
    for code,product in products.items():
        review=reviews.get(code)
        if review and review['sha256'] == product['thumbnail'].get('sha256'):
            path=output/product['thumbnail']['path']
            if path.exists() and digest(path) == review['sha256']:
                product['issues']=[i for i in product['issues'] if i.get('type') != 'badge_review']
                product['thumbnail']['visual_review']=review
                failed=product['thumbnail']['status'] != 'success' or any(o['status'] != 'success' for o in product['options'].values())
                product['status']='incomplete' if failed or product['issues'] else 'complete'
    for code in groups:
        product=products.get(code,{'status':'unrun','thumbnail':{},'options':{}})
        files=[]
        if product['thumbnail'].get('status') == 'success':files.append(output/product['thumbnail']['path'])
        files += [output/o['path'] for o in product['options'].values() if o.get('status') == 'success']
        path=archives/f'{code}.zip'
        update_archive(path,code,output,files,{'code':code,'status':product['status'],
            'thumbnail_present':product['thumbnail'].get('status')=='success',
            'options_present':len(files)-(product['thumbnail'].get('status')=='success'),
            'issues':product.get('issues',[])})
        product['zip']={'path':str(path.relative_to(root)),'sha256':digest(path)}
    codes=list(groups)
    pages=[]
    for start in range(0,len(codes),24):
        page=Image.new('RGB',(1200,4*244),'white');draw=ImageDraw.Draw(page)
        for index,code in enumerate(codes[start:start+24]):
            x=index%6*200;y=index//6*244
            product=products.get(code,{})
            if product.get('thumbnail',{}).get('status') == 'success':
                with Image.open(output/product['thumbnail']['path']) as image:
                    page.paste(image.convert('RGB').resize((184,184),Image.Resampling.LANCZOS),(x+8,y+8))
            else:
                draw.rectangle((x+8,y+8,x+192,y+192),outline='#b42318',width=3)
                draw.text((x+18,y+75),'BLOCKED',font=font(20,True),fill='#b42318')
            draw.text((x+8,y+196),code,font=font(19,True),fill='black')
            label=product.get('status','unrun')
            draw.text((x+8,y+220),label,font=font(13),fill='#b42318' if label!='complete' else '#276749')
        name=f'page-{len(pages)+1:02}.png';page.save(previews/name);pages.append(name)
    # GitHub Markdown makes every product thumbnail/option directly navigable.
    index=['# 전체 상품 검수 목록','', '완료 상태는 catalog-state.json의 최종 검증 결과입니다. incomplete는 누락·불일치·디자인 검수 문제가 남은 항목입니다.','']
    index += [f'![page {i+1}]({name})' for i,name in enumerate(pages)]
    index += ['', '| 품명 | 상태 | 대표 PNG | 옵션 | ZIP |','|---|---|---|---|---|']
    for code in codes:
        p=products.get(code,{})
        thumb=f'[보기](../../output/{code}/thumbnail.png)' if p.get('thumbnail',{}).get('status')=='success' else '미제작'
        n=sum(o.get('status')=='success' for o in p.get('options',{}).values())
        index.append(f"| {code} | {p.get('status','unrun')} | {thumb} | [{n}개](../../output/{code}/options) | [다운로드](../../archives/{code}.zip) |")
    (previews/'README.md').write_text('\n'.join(index)+'\n',encoding='utf-8')
    atomic_json(output/'catalog-state.json',state)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output',type=Path)
    parser.add_argument('--only',nargs='+',default=())
    parser.add_argument('--retry-failed',action='store_true')
    parser.add_argument('--finalize-only',action='store_true',help='Refresh ZIPs and previews without rendering images')
    args=parser.parse_args();root=args.source.resolve();output=(args.output or root/'output').resolve()
    if args.finalize_only:
        state=json.loads((output/'catalog-state.json').read_text())
        groups=json.loads((output/'catalog-source-index.json').read_text())['groups']
    else:
        state,groups=render_catalog(root,output,args.only,args.retry_failed)
    package_and_previews(root,output,state,groups)
    counts={'products':len(groups),'complete':sum(p['status']=='complete' for p in state['products'].values()),
            'thumbnails':sum(p['thumbnail']['status']=='success' for p in state['products'].values()),
            'options':sum(sum(o['status']=='success' for o in p['options'].values()) for p in state['products'].values())}
    print(json.dumps(counts,ensure_ascii=False),flush=True)
    if any(p['status'] != 'complete' for p in state['products'].values()):
        raise SystemExit(2)


if __name__=='__main__':main()

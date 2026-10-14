"""Rename verified completed PNGs without rendering; safe to resume repeatedly."""
import json
from pathlib import Path
from PIL import Image
from catalog import atomic_json, digest
from generate import groups_from_excel, thumbnail_filename


def migrate(root):
    out=root/'output'
    groups,errors=groups_from_excel(root/'화장품 썸네일_수정.xlsx')
    conflicts=[e for e in errors if e['type']!='missing_option_reference']
    if conflicts: raise ValueError(f'Excel metadata errors: {conflicts}')
    state=json.loads((out/'catalog-state.json').read_text())
    plan=[];missing=[]
    for code,g in groups.items():
        name=thumbnail_filename(g)
        t=state['products'][code]['thumbnail']
        if t['status']!='success':
            missing.append({'code':code,'status':t['status'],'expected':f'{code}/{name}'})
            continue
        old=out/t['path'];new=out/code/name
        source=old if old.exists() else new
        if not source.exists() or digest(source)!=t['sha256']:
            raise ValueError(f'Unverified PNG: {code}')
        with Image.open(source) as im:
            assert im.format=='PNG' and im.size==(1024,1024)
        if new.exists() and new!=source: raise ValueError(f'Filename collision: {new}')
        plan.append((code,source,new,t['sha256']))
    options={str(p.relative_to(out)):digest(p) for p in out.glob('*/options/*.png')}
    for code,old,new,sha in plan:
        if old!=new: old.rename(new)
        state['products'][code]['thumbnail']['path']=str(new.relative_to(out))
        assert digest(new)==sha
    atomic_json(out/'catalog-state.json',state)
    protected_path=root/'automation/catalog-protected.json'
    protected=json.loads(protected_path.read_text())
    for code,old,new,sha in plan:
        key=f'output/{code}/thumbnail.png'
        if key in protected: protected[f'output/{code}/{new.name}']=protected.pop(key)
    atomic_json(protected_path,protected)
    assert options=={str(p.relative_to(out)):digest(p) for p in out.glob('*/options/*.png')}
    assert not list(out.glob('*/thumbnail.png'))
    report={'products':len(groups),'renamed':len(plan),'missing':missing,'filename_mismatches':[],
            'representative_sha256_preserved':True,'options_preserved':len(options),
            'files':[{'code':c,'old':f'{c}/thumbnail.png','new':str(n.relative_to(out)),'sha256':sha} for c,o,n,sha in plan]}
    atomic_json(out/'v7-filename-audit.json',report)
    return report


if __name__=='__main__':
    result=migrate(Path(__file__).resolve().parents[1])
    print(json.dumps({k:v for k,v in result.items() if k!='files'},ensure_ascii=False,indent=2))

"""Build a large standalone PNG/code/report bundle outside the Git checkout."""
import argparse
import hashlib
import os
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--destination',type=Path,default=ROOT.parent/'catalog-deliverables.zip')
args=parser.parse_args();destination=args.destination.resolve()
if destination.is_relative_to(ROOT):raise ValueError('Keep the large bundle outside the Git checkout')
destination.parent.mkdir(parents=True,exist_ok=True)
files=[ROOT/'README.md',*ROOT.glob('automation/*.py'),*ROOT.glob('automation/*.json'),
       ROOT/'automation/README.md',ROOT/'automation/requirements.txt',
       *ROOT.glob('output/*/thumbnail.png'),*ROOT.glob('output/*/options/*.png'),
       *ROOT.glob('output/catalog-*'),ROOT/'output/CATALOG_REPORT.md',
       *ROOT.glob('previews/catalog/*')]
files=sorted(set(p for p in files if p.is_file()))
temporary=destination.with_suffix('.zip.tmp')
with ZipFile(temporary,'w',ZIP_DEFLATED) as z:
    for p in files:z.write(p,p.relative_to(ROOT))
with ZipFile(temporary) as z:
    assert z.testzip() is None
    assert len(z.namelist())==len(files)
    for p in files:
        assert hashlib.sha256(z.read(p.relative_to(ROOT).as_posix())).hexdigest()==hashlib.sha256(p.read_bytes()).hexdigest()
os.replace(temporary,destination)
print(f'Bundle verified: {destination}; {len(files)} files; {destination.stat().st_size} bytes',flush=True)

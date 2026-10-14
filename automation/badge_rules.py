"""V6 label protection. Foreground occupancy ranks positions but is not a failure rule."""
import csv
import io
import subprocess
import tempfile
from pathlib import Path


def circle_intersects_box(center, box, radius=80, padding=3):
    cx,cy=center
    x0,y0,x1,y1=box
    nearest_x=max(x0-padding,min(cx,x1+padding))
    nearest_y=max(y0-padding,min(cy,y1+padding))
    return (cx-nearest_x)**2+(cy-nearest_y)**2 < radius**2


def important_regions(canvas, product_box, group, source_sha256):
    annotation=group.get('important_region_annotation')
    if annotation:
        if (annotation['source_sha256'] != source_sha256
                or list(annotation['product_box']) != list(product_box)):
            raise ValueError('badge_review: important-region annotation does not match source or geometry')
        return annotation['critical_regions'],'source-bound visual annotations'
    # OCR is only a conservative aid. Missing/small/non-English text and design
    # features cannot be certified by this pass, so overlaps still need visual review.
    x,y,x1,y1=product_box
    try:
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'product.png'
            canvas.crop(tuple(product_box)).save(path)
            raw=subprocess.check_output(['tesseract',str(path),'stdout','--psm','11','tsv'],
                                        stderr=subprocess.DEVNULL,text=True,timeout=20)
        regions=[]
        for row in csv.DictReader(io.StringIO(raw),delimiter='\t'):
            token=row.get('text','').strip()
            if len(token)<3 or not any(c.isalpha() for c in token) or float(row['conf'])<55:
                continue
            px,py,w,h=[int(row[k]) for k in ('left','top','width','height')]
            regions.append([x+px,y+py,x+px+w,y+py+h])
        return regions,'OCR aid only; visual review required for overlap'
    except (OSError,subprocess.SubprocessError,ValueError):
        return [],'OCR unavailable; visual review required for overlap'

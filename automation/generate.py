"""Analyze all source assets, render only the three authorized sample products."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

from openpyxl import load_workbook
from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageOps, ImageStat

SAMPLES = ('RL0001', 'LL0001', 'WM0001')
EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp', '.tif', '.tiff', '.bmp'}
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'


def font(size, bold=False):
    return ImageFont.truetype(BOLD if bold else FONT, size)


def split_title(text):
    notes = re.findall(r'\(([^()]*)\)', text)
    main = re.sub(r'\([^()]*\)', '', text)
    return ' '.join(main.split()), notes


def decode_name(info):
    name = info.filename
    if not info.flag_bits & 0x800:
        try:
            name = name.encode('cp437').decode('cp949')
        except (UnicodeError, LookupError):
            pass
    return name


class Assets:
    def __init__(self, root):
        self.root = root
        self.items = []
        self.archives = []
        for path in sorted(root.glob('*.zip')):
            with ZipFile(path) as z:
                bad = z.testzip()
                if bad:
                    raise ValueError(f'ZIP CRC failure: {path.name}: {bad}')
                members = []
                for info in z.infolist():
                    name = decode_name(info)
                    if info.is_dir() or Path(name).suffix.lower() not in EXTENSIONS:
                        continue
                    data = z.read(info)
                    item = {'archive': path.name, 'member': name,
                            'raw_member': info.filename, 'filename': Path(name).name,
                            'sha256': hashlib.sha256(data).hexdigest()}
                    self.items.append(item)
                    members.append({k: v for k, v in item.items() if k != 'raw_member'})
                self.archives.append({'archive': path.name, 'crc': 'passed', 'images': members})

    def match(self, value, role):
        if not value:
            raise ValueError('Empty image reference')
        value = str(value).strip().replace('\\', '/')
        p = Path(value)
        candidates = [i for i in self.items
                      if (('브랜드' in i['archive']) == (role == 'brand'))
                      and (i['filename'].casefold() == p.name.casefold()
                           if p.suffix else Path(i['filename']).stem.casefold() == p.name.casefold())]
        if len(p.parts) > 1:
            candidates = [i for i in candidates if i['member'].casefold().endswith(value.casefold())]
        if not candidates:
            raise FileNotFoundError(f'{role}: {value}')
        if len(candidates) > 1:
            raise ValueError(f'Ambiguous {role}: {value}: {candidates}')
        return candidates[0]

    def image(self, item):
        with ZipFile(self.root / item['archive']) as z:
            data = z.read(item['raw_member'])
        with Image.open(io.BytesIO(data)) as source:
            return ImageOps.exif_transpose(source).convert('RGBA')


def groups_from_excel(path):
    wb = load_workbook(path, read_only=True, data_only=True)
    rows = iter(wb.active.values)
    headers = next(rows)
    required = ('품명', '브랜드', '상품명', '옵션명', '브랜드 파일명', '옵션 파일', '썸네일 파일')
    indexes = {name: headers.index(name) for name in required}
    groups, errors, current = {}, [], None
    for number, cells in enumerate(rows, 2):
        row = {k: cells[i] if i < len(cells) else None for k, i in indexes.items()}
        if not any(row.values()):
            continue
        if row['품명']:
            current = str(row['품명']).strip()
            if current in groups:
                errors.append({'type': 'duplicate_product_group', 'row': number, 'code': current})
            groups.setdefault(current, {'code': current, 'rows': [], 'brand': None, 'title': None,
                                        'brand_refs': [], 'thumbnail_refs': [], 'options': [], 'observed_brands': []})
        if current is None:
            errors.append({'type': 'orphan_row', 'row': number})
            continue
        g = groups[current]
        g['rows'].append(number)
        if row['브랜드'] and str(row['브랜드']).strip() not in g['observed_brands']:
            g['observed_brands'].append(str(row['브랜드']).strip())
        for key, field in [('brand', '브랜드'), ('title', '상품명')]:
            if row[field]:
                value = str(row[field]).strip()
                if g[key] and g[key] != value:
                    errors.append({'type': 'conflicting_metadata', 'code': current, 'row': number, 'field': field})
                if not g[key]:
                    g[key] = value
        for key, field in [('brand_refs', '브랜드 파일명'), ('thumbnail_refs', '썸네일 파일')]:
            if row[field] and str(row[field]).strip() not in g[key]:
                g[key].append(str(row[field]).strip())
        if row['옵션 파일']:
            g['options'].append({'row': number, 'name': row['옵션명'], 'reference': str(row['옵션 파일']).strip()})
        elif row['옵션명']:
            errors.append({'type': 'missing_option_reference', 'code': current, 'row': number})
    wb.close()
    return groups, errors


def white_image(image):
    bg = Image.new('RGBA', image.size, 'white')
    bg.alpha_composite(image)
    return bg.convert('RGB')


def crop_whitespace(image, padding=12):
    # Crop exterior whitespace only; do not erase/recolor pixels inside the photo.
    image = white_image(image)
    diff = ImageChops.difference(image, Image.new('RGB', image.size, 'white'))
    mask = diff.convert('L').point(lambda p: 255 if p > 12 else 0)
    box = mask.getbbox()
    if not box:
        raise ValueError('Image has no visible content')
    x0, y0, x1, y1 = box
    return image.crop((max(0, x0-padding), max(0, y0-padding),
                       min(image.width, x1+padding), min(image.height, y1+padding)))


def wrap(text, face, max_width):
    lines, line = [], ''
    for word in text.split():
        trial = (line + ' ' + word).strip()
        if face.getlength(trial) > max_width and line:
            lines.append(line)
            line = word
        else:
            line = trial
    if line:
        lines.append(line)
    return lines


def draw_text(canvas, text, y, size, bold=False, max_lines=2):
    while size >= 18:
        face = font(size, bold)
        lines = wrap(text, face, 900)
        if len(lines) <= max_lines and all(face.getlength(s) <= 900 for s in lines):
            break
        size -= 1
    if len(lines) > max_lines or any(face.getlength(s) > 900 for s in lines):
        raise ValueError(f'Title cannot fit: {text}')
    draw = ImageDraw.Draw(canvas)
    boxes = []
    for line in lines:
        draw.text((512, y), line, font=face, fill='black', anchor='mt')
        boxes.append(draw.textbbox((512, y), line, font=face, anchor='mt'))
        y += size + 10
    return y, boxes


def frame_color(product):
    # Ignore white/neutral backgrounds, favor saturated package accent colors.
    small = product.resize((120, 120))
    bins = Counter()
    for r, g, b in small.getdata():
        if max(r, g, b) - min(r, g, b) >= 60 and 35 < (r+g+b)/3 < 235:
            bins[(r//24, g//24, b//24)] += 1
    if bins:
        key = bins.most_common(1)[0][0]
        color = tuple(min(255, int((v*24+12)*0.8+255*0.2)) for v in key)
    else:
        pixels = [p for p in small.getdata() if 35 < sum(p)/3 < 200]
        if not pixels:
            color = (92, 113, 130)
        else:
            color = tuple(int(sum(p[k] for p in pixels)/len(pixels)*0.85+255*0.15) for k in range(3))
    # Keep sufficient white badge-text contrast while using the same color on frame.
    luminance = lambda c: sum(w * ((v/255/12.92) if v/255 <= .04045 else ((v/255+.055)/1.055)**2.4)
                              for w, v in zip((.2126, .7152, .0722), c))
    while 1.05/(luminance(color)+.05) < 3.1:
        color = tuple(int(v*.96) for v in color)
    return color


def make_thumbnail(g, assets, destination):
    if len(g['brand_refs']) != 1 or len(g['thumbnail_refs']) != 1:
        raise ValueError('Exactly one brand logo and thumbnail reference required')
    logo_item = assets.match(g['brand_refs'][0], 'brand')
    product_item = assets.match(g['thumbnail_refs'][0], 'thumbnail')
    logo = crop_whitespace(assets.image(logo_item), 0)
    logo.thumbnail((350, 70), Image.Resampling.LANCZOS)
    product = crop_whitespace(assets.image(product_item), 16)
    color = frame_color(product)
    canvas = Image.new('RGB', (1024, 1024), 'white')
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 0, 1023, 1023), outline=color, width=14)
    canvas.paste(logo, ((1024-logo.width)//2, 64+(70-logo.height)//2))
    main, notes = split_title(g['title'])
    y, title_boxes = draw_text(canvas, main, 167, 54, True)
    subtitle_boxes = []
    for note in notes:
        y, boxes = draw_text(canvas, note, y+8, 30, False)
        subtitle_boxes.extend(boxes)
    top = max(340, y+32)
    product.thumbnail((700, 956-top), Image.Resampling.LANCZOS)
    x = (1024-product.width)//2
    py = top + (956-top-product.height)//2
    canvas.paste(product, (x, py))
    # Score fixed diameter circles against visible pixels, constrained below text.
    candidates = [(cx, cy) for cx in (126, 898) for cy in (top+82, (top+956)//2, 874)]
    foreground = ImageChops.difference(canvas, Image.new('RGB', canvas.size, 'white')).convert('L')
    scored = []
    for cx, cy in candidates:
        mask = Image.new('L', canvas.size, 0)
        ImageDraw.Draw(mask).ellipse((cx-82, cy-82, cx+82, cy+82), fill=255)
        score = ImageStat.Stat(foreground, mask=mask).mean[0]
        scored.append((score, cx, cy))
    score, cx, cy = min(scored)
    if score > 3:
        # Reserve a separate left column if a photo fills all candidate whitespace.
        canvas.paste('white', (28, top, 996, 970))
        product.thumbnail((630, 956-top), Image.Resampling.LANCZOS)
        x, py = 326, top+(956-top-product.height)//2
        canvas.paste(product, (x, py))
        cx, cy, score = 126, top+82, 0
    draw.ellipse((cx-80, cy-80, cx+80, cy+80), fill=color)
    draw.text((cx, cy), '1+1', fill='white', font=font(51, True), anchor='mm')
    canvas.save(destination)
    return {'source': product_item, 'brand_logo': logo_item, 'main_title': main,
            'subtitles': notes, 'title_boxes': title_boxes, 'subtitle_boxes': subtitle_boxes,
            'product_box': [x, py, x+product.width, py+product.height],
            'badge_box': [cx-80, cy-80, cx+80, cy+80], 'badge_occupancy_score': score,
            'frame_rgb': color, 'frame_width': 14, 'size': [1024, 1024]}


def make_option(source, mark, destination):
    canvas = source.copy()
    # Preserve alpha and original pixel dimensions, changing only the logo area.
    logo = mark.copy()
    box = logo.getbbox()
    if box:
        logo = logo.crop(box)
    logo.thumbnail((round(canvas.width*.19), round(canvas.height*.10)), Image.Resampling.LANCZOS)
    margin = max(12, round(min(canvas.size)*.028))
    x, y = canvas.width-margin-logo.width, margin
    canvas.alpha_composite(logo, (x, y))
    canvas.save(destination)
    return {'size': list(canvas.size), 'logo_box': [x, y, x+logo.width, y+logo.height]}


def preview(code, folder, options):
    paths = [folder/'thumbnail.png'] + [folder/'options'/name for name in options]
    columns = min(3, len(paths))
    rows = (len(paths)+columns-1)//columns
    page = Image.new('RGB', (columns*360, 80+rows*410), '#f1f3f5')
    draw = ImageDraw.Draw(page)
    draw.text((24, 20), code+' / sample review', font=font(25, True), fill='black')
    for i, path in enumerate(paths):
        image = white_image(Image.open(path).convert('RGBA'))
        image.thumbnail((328, 328), Image.Resampling.LANCZOS)
        x, y = i%columns*360+16, 80+i//columns*410
        page.paste(image, (x+(328-image.width)//2, y+(328-image.height)//2))
        draw.text((x, y+344), path.name, font=font(18), fill='black')
    return page


def run(root, output):
    if output == root or root.is_relative_to(output):
        raise ValueError('Output must not be the source directory or its ancestor')
    output.mkdir(parents=True, exist_ok=True)
    assets = Assets(root)
    groups, errors = groups_from_excel(root/'화장품 썸네일.xlsx')
    matches, missing = {}, []
    for code, g in groups.items():
        resolved = {'brand': [], 'thumbnail': [], 'options': []}
        for role, refs in [('brand', g['brand_refs']), ('thumbnail', g['thumbnail_refs']),
                           ('options', [o['reference'] for o in g['options']])]:
            if not refs:
                missing.append({'code': code, 'role': role, 'reference': None, 'error': 'No Excel reference'})
            for ref in refs:
                try:
                    resolved[role].append(assets.match(ref, 'option' if role == 'options' else role))
                except (ValueError, FileNotFoundError) as e:
                    missing.append({'code': code, 'role': role, 'reference': ref, 'error': str(e)})
        matches[code] = resolved
    duplicates = defaultdict(list)
    for item in assets.items:
        duplicates[item['filename'].casefold()].append(item)
    collisions = [{'filename': k, 'files': v, 'identical_bytes': len({i['sha256'] for i in v}) == 1}
                  for k, v in duplicates.items() if len(v) > 1]
    report = {'product_count': len(groups), 'brand_count': len({b for g in groups.values() for b in g['observed_brands']}),
              'product_group_brand_count': len({g['brand'] for g in groups.values()}),
              'option_reference_count': sum(len(g['options']) for g in groups.values()),
              'unique_option_reference_count': len({o['reference'] for g in groups.values() for o in g['options']}),
              'thumbnail_target_count': len(groups),
              'thumbnail_referenced_product_count': sum(bool(g['thumbnail_refs']) for g in groups.values()),
              'archive_image_count': len(assets.items), 'archives': assets.archives,
              'groups': groups, 'matches': matches, 'missing': missing,
              'filename_collisions': collisions, 'excel_errors': errors, 'samples': {}}
    mark = Image.open(root/'pick&mood.kr 로고.png').convert('RGBA')
    pages = []
    for code in SAMPLES:
        try:
            if code not in groups:
                raise ValueError('Product missing from Excel')
            if any(e['code'] == code for e in missing) or any(e.get('code') == code for e in errors):
                raise ValueError('Unresolved Excel or image matching issue; see analysis.json')
            g = groups[code]
            folder = output/code
            (folder/'options').mkdir(parents=True, exist_ok=True)
            layout = make_thumbnail(g, assets, folder/'thumbnail.png')
            options, option_results = [], []
            for option in g['options']:
                item = assets.match(option['reference'], 'option')
                name = Path(item['filename']).stem+'.png'
                if name in options:
                    raise ValueError(f'Duplicate output filename: {name}')
                details = make_option(assets.image(item), mark, folder/'options'/name)
                option_results.append({**option, 'source': item, 'output': name, **details})
                options.append(name)
            page = preview(code, folder, options)
            page.save(output/f'{code}-preview.png')
            pages.append(page)
            with ZipFile(output/f'{code}.zip', 'w', ZIP_DEFLATED) as z:
                for file in [folder/'thumbnail.png'] + [folder/'options'/name for name in options]:
                    z.write(file, file.relative_to(output))
            report['samples'][code] = {'status': 'success', 'thumbnail': layout, 'options': option_results}
        except Exception as e:
            report['samples'][code] = {'status': 'failed', 'error': str(e)}
    if pages:
        combined = Image.new('RGB', (max(p.width for p in pages), sum(p.height for p in pages)), '#f1f3f5')
        y = 0
        for page in pages:
            combined.paste(page, (0, y)); y += page.height
        combined.save(output/'all-samples-preview.png')
    (output/'analysis.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    logs = [json.dumps(e, ensure_ascii=False) for e in errors+missing+collisions]
    logs += [json.dumps({'code': k, **v}, ensure_ascii=False) for k, v in report['samples'].items() if v['status'] != 'success']
    (output/'errors.log').write_text('\n'.join(logs) + ('\n' if logs else 'No errors detected.\n'), encoding='utf-8')
    summary = {k: report[k] for k in ['product_count','brand_count','option_reference_count',
                                    'unique_option_reference_count','thumbnail_target_count','archive_image_count']}
    summary.update({'missing_count': len(missing), 'collision_count': len(collisions),
                    'excel_error_count': len(errors),
                    'samples': {c: {'status': s['status'], 'options': len(s.get('options', []))} for c, s in report['samples'].items()}})
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if any(s['status'] != 'success' for s in report['samples'].values()):
        raise SystemExit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output', type=Path, default=Path('/workspace/cosmetic-thumbnail-output'))
    args = parser.parse_args()
    run(args.source.resolve(), args.output.resolve())

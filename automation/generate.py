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
        for path in [root/'브랜드 로고.zip', *sorted(root.glob('화장품 썸네일-*.zip'))]:
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


def draw_text(canvas, text, y, size, bold=False, max_lines=3):
    minimum = 46 if bold else 25
    while size >= minimum:
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
        y = boxes[-1][3] + 6
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


def choose_badge(canvas, text_bottom, product_top, inset=40):
    """Find whitespace without ever reducing the independently fitted product."""
    foreground = ImageChops.difference(canvas, Image.new('RGB', canvas.size, 'white')).convert('L')
    occupied = foreground.point(lambda p: 255 if p > 18 else 0)
    radius = 80
    start = max(text_bottom+radius+12, product_top+radius)
    ys = list(range(start, 984-radius+1, 28))
    if not ys:
        raise ValueError('No room for a badge below the header')
    scored = []
    for cx in (inset+radius, 1024-inset-radius):
        for cy in ys:
            mask = Image.new('L', canvas.size, 0)
            ImageDraw.Draw(mask).ellipse((cx-radius, cy-radius, cx+radius, cy+radius), fill=255)
            fraction = ImageStat.Stat(occupied, mask=mask).mean[0]/255
            scored.append((fraction, cy, cx))
    fraction, cy, cx = min(scored)
    return cx, cy, fraction


def make_thumbnail(g, assets, destination):
    if len(g['brand_refs']) != 1 or len(g['thumbnail_refs']) != 1:
        raise ValueError('Exactly one brand logo and thumbnail reference required')
    logo_item = assets.match(g['brand_refs'][0], 'brand')
    product_item = assets.match(g['thumbnail_refs'][0], 'thumbnail')
    logo = crop_whitespace(assets.image(logo_item), 0)
    logo.thumbnail((340, 52), Image.Resampling.LANCZOS)
    # Tight outer crop only. No source pixels are erased or generated.
    product = crop_whitespace(assets.image(product_item), 6)
    cropped_size = product.size
    color = frame_color(product)
    canvas = Image.new('RGB', (1024, 1024), 'white')
    draw = ImageDraw.Draw(canvas)
    frame_inset, frame_width = 12, 26
    draw.rectangle((frame_inset, frame_inset, 1023-frame_inset, 1023-frame_inset),
                   outline=color, width=frame_width)
    logo_y = 58
    logo_x = (1024-logo.width)//2
    canvas.paste(logo, (logo_x, logo_y))
    logo_box = [logo_x, logo_y, logo_x+logo.width, logo_y+logo.height]
    main, notes = split_title(g['title'])
    y, title_boxes = draw_text(canvas, main, logo_box[3]+12, 52, True)
    subtitle_boxes = []
    for note in notes:
        y, boxes = draw_text(canvas, note, y+2, 29, False)
        subtitle_boxes.extend(boxes)
    text_bottom = max(b[3] for b in title_boxes+subtitle_boxes)
    top = text_bottom+20
    bottom, left, right = 970, 48, 976
    available = (right-left, bottom-top)
    if available[1] < 480:
        raise ValueError('Header leaves insufficient product area; review title length')
    scale = min(available[0]/product.width, available[1]/product.height)
    size = (round(product.width*scale), round(product.height*scale))
    product = product.resize(size, Image.Resampling.LANCZOS)
    x = (1024-product.width)//2
    # Bottom alignment uses the whole available height for vertical/set photos;
    # wide images rise toward the header rather than floating far beneath it.
    ratio = cropped_size[0]/cropped_size[1]
    py = top if ratio > 1.35 else bottom-product.height
    canvas.paste(product, (x, py))
    cx, cy, occupancy = choose_badge(canvas, text_bottom, top)
    draw.ellipse((cx-80, cy-80, cx+80, cy+80), fill=color)
    draw.text((cx, cy), '1+1', fill='white', font=font(51, True), anchor='mm')
    canvas.save(destination)
    return {'design_version': 2, 'source': product_item, 'brand_logo': logo_item,
            'main_title': main, 'subtitles': notes, 'logo_box': logo_box,
            'title_boxes': title_boxes, 'subtitle_boxes': subtitle_boxes,
            'cropped_source_size': list(cropped_size), 'product_scale': scale,
            'product_box': [x, py, x+product.width, py+product.height],
            'product_area': [left, top, right, bottom], 'source_aspect_ratio': ratio,
            'badge_box': [cx-80, cy-80, cx+80, cy+80],
            'badge_occupied_fraction': occupancy, 'badge_resized_product': False,
            'frame_rgb': color, 'frame_width': frame_width, 'frame_inset': frame_inset,
            'background_rgb': [255,255,255], 'size': [1024, 1024]}


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


def compare_preview(code, before, after):
    page = Image.new('RGB', (1080, 610), 'white')
    draw = ImageDraw.Draw(page)
    for x, label, source in [(20, 'BEFORE', before), (560, 'AFTER', after)]:
        draw.text((x, 16), code+' / '+label, font=font(26, True), fill='black')
        with Image.open(source) as image:
            page.paste(image.convert('RGB').resize((500, 500), Image.Resampling.LANCZOS), (x, 76))
    return page


def bundle_samples(root, output, previews):
    """Package the current PNGs and current code, never a stale nested bundle."""
    with ZipFile(root/'sample-deliverables.zip', 'w', ZIP_DEFLATED) as z:
        for code in SAMPLES:
            for file in sorted((output/code).rglob('*.png')):
                z.write(file, Path('output')/file.relative_to(output))
            z.write(output/f'{code}.zip', f'output/{code}.zip')
        for name in ['analysis.json','errors.log','REPORT.md','DESIGN_REVIEW.md','design-review.json']:
            file = output/name
            if file.exists():
                z.write(file, 'output/'+name)
        for file in sorted(previews.rglob('*.png')):
            z.write(file, Path('previews')/file.relative_to(previews))
        for name in ['generate.py','validate.py','requirements.txt','README.md']:
            z.write(root/'automation'/name, 'automation/'+name)


def run(root, output, reuse_options=False, preview_dir=None, compare_with=None):
    if output == root or root.is_relative_to(output):
        raise ValueError('Output must not be the source directory or its ancestor')
    output.mkdir(parents=True, exist_ok=True)
    preview_dir = preview_dir or output
    preview_dir.mkdir(parents=True, exist_ok=True)
    previous = json.loads((output/'analysis.json').read_text(encoding='utf-8')) if reuse_options else None
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
                if reuse_options:
                    old = next((o for o in previous['samples'][code]['options'] if o['output'] == name), None)
                    if old is None or old['source']['sha256'] != item['sha256']:
                        raise ValueError(f'Cannot reuse unverified option: {name}')
                    with Image.open(folder/'options'/name) as existing:
                        existing.load()
                        if list(existing.size) != old['size']:
                            raise ValueError(f'Existing option dimensions differ: {name}')
                    details = {k: old[k] for k in ('size','logo_box')}
                else:
                    details = make_option(assets.image(item), mark, folder/'options'/name)
                option_results.append({**option, 'source': item, 'output': name, **details})
                options.append(name)
            page = preview(code, folder, options)
            page.save(preview_dir/f'{code}-preview.png')
            if compare_with:
                compare_preview(code, compare_with/f'{code}.png', folder/'thumbnail.png').save(
                    preview_dir/f'{code}-comparison.png')
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
        combined.save(preview_dir/'all-samples-preview.png')
        thumbnails = Image.new('RGB', (1080, 420), 'white')
        for i, code in enumerate(SAMPLES):
            ImageDraw.Draw(thumbnails).text((i*360+16, 16), code, font=font(23, True), fill='black')
            with Image.open(output/code/'thumbnail.png') as image:
                thumbnails.paste(image.resize((340,340), Image.Resampling.LANCZOS), (i*360+10,64))
        thumbnails.save(preview_dir/'thumbnails-overview.png')
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
    parser.add_argument('--reuse-options', action='store_true', help='Keep previously verified option PNGs unchanged')
    parser.add_argument('--previews', type=Path, help='Separate preview directory')
    parser.add_argument('--compare-with', type=Path, help='Directory containing CODE.png before images')
    parser.add_argument('--bundle', action='store_true', help='Refresh the root sample-deliverables.zip')
    args = parser.parse_args()
    run(args.source.resolve(), args.output.resolve(), args.reuse_options,
        args.previews.resolve() if args.previews else None,
        args.compare_with.resolve() if args.compare_with else None)
    if args.bundle:
        bundle_samples(args.source.resolve(), args.output.resolve(),
                       args.previews.resolve() if args.previews else args.output.resolve())

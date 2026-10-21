"""Installed-font discovery and bounded, mixed-source d1-rgba atlas generation.

No font downloads and no runtime hooks. Locale decisions belong in profile JSON.
"""
from __future__ import annotations

import argparse
import copy
import io
import json
import os
from pathlib import Path
import re

from localize import TOKEN, filehash, write_json


def font_metadata(path):
    from fontTools.ttLib import TTFont
    with TTFont(path) as font:
        names = {str(i): list(dict.fromkeys(n.toUnicode() for n in font['name'].names if n.nameID == i))
                 for i in (0, 1, 2, 5, 6, 13, 14)}
        return dict(file=Path(path).name, sha256=filehash(Path(path)), format=font.sfntVersion,
                    names=names, weight=font['OS/2'].usWeightClass, units_per_em=font['head'].unitsPerEm,
                    cmap_count=len(font.getBestCmap()), outline_tables=[t for t in ('glyf', 'CFF ', 'CBDT', 'EBDT') if t in font])


def discover():
    roots = [Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts',
             Path(os.environ.get('LOCALAPPDATA', str(Path.home() / 'AppData/Local'))) / 'Microsoft/Windows/Fonts']
    candidates = set()
    for root in roots:
        if root.exists():
            candidates.update(p.resolve() for p in root.iterdir() if p.suffix.lower() in ('.ttf', '.otf', '.ttc')
                              and re.search(r'fusion|chillbitmap', p.name, re.I))
    if os.name == 'nt':
        import winreg
        for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            with winreg.OpenKey(hive, r'SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts') as key:
                for i in range(winreg.QueryInfoKey(key)[1]):
                    name, value, _ = winreg.EnumValue(key, i)
                    if not re.search(r'fusion|chillbitmap|寒蝉点阵|缝合像素', name, re.I):
                        continue
                    for p in [Path(value), *(root / value for root in roots)]:
                        if p.is_file():
                            candidates.add(p.resolve())
    return sorted(candidates)


def resolve_fonts(profile):
    candidates = discover()
    selected = {}
    for role, spec in profile['fonts'].items():
        hits = [p for p in candidates if p.name.casefold() == spec['file'].casefold()]
        if not hits:
            raise ValueError('Installed font not found: ' + spec['file'])
        path = next((p for p in hits if filehash(p) == spec['sha256']), None)
        if path is None:
            raise ValueError('Installed font identity changed: ' + spec['file'])
        selected[role] = path
    return selected


def printable(text):
    return {ord(c) for c in text if ord(c) >= 32 and c != '\ufeff'}


def title_char(c):
    return ord(c) >= 0x3000 and not 0xE000 <= ord(c) <= 0xF8FF


def route_titles(text, aliases, title=False):
    if not title:
        return text
    first, sep, rest = text.partition('|')
    return ''.join(chr(aliases[ord(c)]) if ord(c) in aliases else c for c in first) + sep + rest


def glyph_width(text, meta, spacing=1):
    """Conservative measured width; variable expansion must still be checked in-game."""
    width = 0
    pos = 0
    trailing_spacing = 0
    while pos < len(text):
        token = TOKEN.match(text, pos)
        if token:
            value = token.group()
            width += 24 if value.startswith('$') else 0
            if value.startswith('$'):
                trailing_spacing = 0
            pos = token.end()
        else:
            glyph = meta['glyphs'].get(str(ord(text[pos])), meta['glyphs'].get('0', {'logw': 12}))
            width += glyph['logw'] + spacing
            trailing_spacing = spacing
            pos += 1
    return max(0, width - trailing_spacing)


def wrap_text(text, meta, width, forbidden_start='', forbidden_end='', min_tail_width=0, preserve_whitespace=False):
    """Wrap physical document lines only, without splitting protected atoms/Latin words."""
    atom = re.compile(r'\x02[^\x01\r\n]*\x01|' + TOKEN.pattern + r'|[A-Za-z0-9]+(?:[\x27.-][A-Za-z0-9]+)*|[^\r\n]', re.S)
    output = []
    def visible(words):
        return [w for w in words if w.strip() and not (TOKEN.fullmatch(w) and not w.startswith('$'))]
    def trim_spaces(words):
        indexes = [i for i,w in enumerate(words) if w.strip() and not (TOKEN.fullmatch(w) and not w.startswith('$'))]
        first,last = (indexes[0],indexes[-1]) if indexes else (len(words),-1)
        return [w for i,w in enumerate(words) if w != ' ' or first <= i <= last]
    for paragraph in text.replace('\r\n', '\n').replace('\r', '\n').split('\n'):
        words = atom.findall(paragraph) if preserve_whitespace else trim_spaces(atom.findall(paragraph))
        if not words:
            output.append('')
        while words:
            end = 1
            while end < len(words) and glyph_width(''.join(words[:end+1]), meta) <= width:
                end += 1
            def valid_boundary(index):
                before, after = visible(words[:index]), visible(words[index:])
                return (not before or (TOKEN.sub('', before[-1]) or '\ufffc')[-1:] not in forbidden_end) and (not after or (TOKEN.sub('', after[0]) or '\ufffc')[:1] not in forbidden_start)
            chosen = end
            while chosen > 0 and not valid_boundary(chosen):
                chosen -= 1
            # An indivisible Latin word / punctuation cluster can exceed a very small
            # budget. Preserve it and report overflow rather than corrupting its text.
            if chosen == 0 or not visible(words[:chosen]):
                chosen = end
                while chosen < len(words) and not valid_boundary(chosen):
                    chosen += 1
            # Rebalance only a paragraph's last short tail, preserving punctuation atoms.
            if chosen < len(words) and min_tail_width:
                candidate = chosen
                while candidate > 1 and (glyph_width(''.join(words[candidate:]), meta) < min_tail_width or not valid_boundary(candidate)):
                    candidate -= 1
                if (candidate > 0 and valid_boundary(candidate)
                        and glyph_width(''.join(words[candidate:]), meta) <= width):
                    chosen = candidate
            line = ''.join(words[:chosen])
            output.append(line if preserve_whitespace else line.strip(' '))
            words = words[chosen:] if preserve_whitespace else trim_spaces(words[chosen:])
    return '\n'.join(output)


def layout_document(text, meta, profile, rule=None):
    """Fit explicitly selected documents inside their native bottom-aligned pane.

    Blank padding cannot shift visible text in a bottom-aligned pane: the extra
    measured height cancels its advance. Bound actual rows instead. Other
    documents retain their existing paragraph behavior.
    """
    rule = rule or {}
    width = rule.get('width', profile['document_width'])
    if rule.get('soft_lines'):
        # The editable source keeps semantic headings/blank paragraphs; physical
        # line breaks inside prose are not a second paragraph boundary.
        lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
        heading = lines.pop(0) if rule.get('keep_first_line') else None
        paragraphs = re.split(r'\n[ \t]*\n+', '\n'.join(lines).strip('\n'))
        text = '\n\n'.join(p.replace('\n', rule.get('soft_joiner', '')) for p in paragraphs)
        if heading is not None:
            text = heading + '\n' + text
    if rule.get('reflow'):
        parts, current = [], ''
        prefixes = tuple(rule.get('preserve_line_prefixes', []))
        suffixes = tuple(rule.get('preserve_line_suffixes', []))
        for line in text.replace('\r\n', '\n').replace('\r', '\n').split('\n'):
            if not line.strip():
                continue
            if prefixes and line.startswith(prefixes):
                if current:
                    parts.append(current)
                    current = ''
                parts.append(line)
            else:
                current += (rule.get('soft_joiner', '') if current else '') + line
                if suffixes and line.endswith(suffixes):
                    parts.append(current)
                    current = ''
        if current:
            parts.append(current)
        text = '\n'.join(parts)
    text = wrap_text(text, meta, width, profile['forbidden_start'], profile['forbidden_end'], rule.get('min_tail_width', 0), rule.get('preserve_whitespace', False))
    if rule:
        lines = text.split('\n')
        line_limit = rule.get('max_visible_lines')
        if line_limit is not None and len(lines) > line_limit:
            raise ValueError('Document layout line budget exceeded: %d > %d' % (len(lines),line_limit))
        if any(glyph_width(line, meta) > width for line in lines):
            raise ValueError('Document layout width budget exceeded')
        text = '\n' * rule.get('leading_lines', 0) + text
        if 'pane_height' in rule:
            spacing = rule.get('line_spacing', 0)
            height = (meta['linefeed'] + spacing) * len(text.split('\n')) - spacing
            if height > rule['pane_height']:
                raise ValueError('Document layout height budget exceeded')
    return text


def build_mixed(zar, records, profile):
    from PIL import Image, ImageDraw, ImageFont
    from fontTools.ttLib import TTFont
    paths = resolve_fonts(profile)
    name = 'FONTS/D2FONT_12X15'
    meta = json.loads(zar.read(name + '.JSON'))
    original_glyphs = copy.deepcopy(meta['glyphs'])
    original_atlas = Image.open(io.BytesIO(zar.read(name + '.PNG'))).convert('RGBA')
    required_text = ''.join(r['target'] or r['source'] for r in records) + ''.join(''.join(v) for v in profile['previews'].values()) + ''.join(profile.get('extra_texts', []))
    # A cmap entry is not coverage: shipped U+2026 has an empty alpha rectangle.
    blank_existing = []
    for code in printable(required_text):
        glyph = meta['glyphs'].get(str(code))
        if glyph and not chr(code).isspace() and not TOKEN.fullmatch(chr(code)):
            rect = (glyph['tx'], glyph['ty'], glyph['tx']+glyph['w'], glyph['ty']+glyph['h'])
            if original_atlas.crop(rect).getchannel('A').getbbox() is None:
                blank_existing.append(code)
    replace_ranges = profile.get('replace_existing_ranges', [])
    replaced_codes = sorted(int(c) for c in original_glyphs
                            if any(start <= int(c) <= end for start, end in replace_ranges) or int(c) in blank_existing)
    previews = profile['previews']
    all_text = ''.join(r['target'] or r['source'] for r in records) + ''.join(''.join(v) for v in previews.values()) + ''.join(profile.get('extra_texts', []))
    required = sorted(printable(all_text) | set(replaced_codes))
    if any(c > 65535 or 0xE000 <= c <= 0xF8FF for c in required):
        raise ValueError('Unsupported supplementary/private-use source character')
    title_text = ''.join((r['target'] or r['source']).partition('|')[0] for r in records if r['resource'] in profile['title_resources']) + ''.join(previews['title'])
    title_codes = sorted(c for c in printable(title_text) if title_char(chr(c)))
    aliases = {c: 0xE000 + i for i, c in enumerate(title_codes)}
    if aliases and max(aliases.values()) > 0xF8FF:
        raise ValueError('Title alias range exhausted')
    if any(str(c) in meta['glyphs'] for c in aliases.values()):
        raise ValueError('Title alias collides with original glyph')
    coverage = {}
    for role, path in paths.items():
        with TTFont(path) as font:
            cmap = font.getBestCmap()
        missing = [c for c in required if c not in cmap]
        coverage[role] = dict(required=len(required), covered=len(required)-len(missing), missing=missing,
                              punctuation=[c for c in required if 0x2000 <= c <= 0x303F or 0xFF00 <= c <= 0xFFEF],
                              metadata=font_metadata(path))
    body_codes = [c for c in required if str(c) not in meta['glyphs'] or c in replaced_codes]
    fallback_codes = sorted(set(body_codes) & set(coverage['body']['missing']))
    body_codes = [c for c in body_codes if c not in fallback_codes]
    for role, codes in [('body', body_codes), ('title', title_codes)]:
        if set(codes) & set(coverage[role]['missing']):
            raise ValueError('Required font glyph missing in ' + role)
    if set(fallback_codes) & set(coverage['title']['missing']):
        raise ValueError('Required font glyph missing in body and fallback')
    old = Image.open(io.BytesIO(zar.read(name + '.PNG'))).convert('RGBA')
    width = profile['atlas_width']
    if width < old.width:
        raise ValueError('Atlas cannot shrink original width')
    rows = []
    ybase = old.height + 1
    for role, codes in [('body', body_codes), ('fallback', fallback_codes), ('title', title_codes)]:
        cell = profile['fonts']['title' if role == 'fallback' else role]['pixel_size']
        cell_height = (17 if replaced_codes else 15) if role == 'body' else 16
        cols = width // (cell + 2)
        for i, c in enumerate(codes):
            rows.append((role, c, 1 + (i % cols) * (cell + 2), ybase + (i // cols) * (cell_height + 2), cell))
        ybase += ((len(codes) + cols - 1) // cols) * (cell_height + 2) + 1
    if ybase > profile['max_atlas_height']:
        raise ValueError('Atlas exceeds configured texture budget')
    atlas = Image.new('RGBA', (width, ybase))
    atlas.paste(old, (0, 0))
    fonts = {role: ImageFont.truetype(str(path), profile['fonts'][role]['pixel_size']) for role, path in paths.items()}
    fonts['fallback'] = fonts['title']
    for role, c, x, y, size in rows:
        font = fonts[role]
        height = 15 if role == 'body' else 16
        bounds = font.getbbox(chr(c))
        shift = 0
        if role == 'body' and c in replaced_codes:
            # Preserve the shared baseline, including accents above it and cedillas below.
            shift = max(0, -bounds[1])
            height = max(height, bounds[3] + shift)
        if bounds[0] < 0 or bounds[2] > size or bounds[1] + shift < 0 or bounds[3] + shift > height or height > (17 if role == 'body' else 16):
            raise ValueError('Native pixel glyph outside cell: %s U+%04X %s' % (role, c, bounds))
        # Do NOT center each glyph's ink box: punctuation must keep its baseline.
        mask = Image.new('L', (size, height))
        ImageDraw.Draw(mask).text((0, shift), chr(c), font=font, fill=255)
        mask = mask.point(lambda value: 255 if value >= 128 else 0)
        if not chr(c).isspace() and mask.getbbox() is None:
            raise ValueError('Empty raster glyph: U+%04X' % c)
        glyph = Image.new('RGBA', mask.size, (255,255,255,0)); glyph.putalpha(mask)
        atlas.paste(glyph, (x, y))
        key = aliases[c] if role == 'title' else c
        meta['glyphs'][str(key)] = dict(w=size, h=height, logw=round(font.getlength(chr(c))), xo=0,
                                      yo=-2 if role != 'body' else -shift, tx=x, ty=y)
    meta['linefeed'] = profile['linefeed']
    runtime = copy.deepcopy(records)
    layouts = []
    document_layouts = []
    for row in runtime:
        logical = row['target'] or row['source']
        text = route_titles(logical, aliases, row['resource'] in profile['title_resources'])
        if row['target'] and '/EXAMINE.' in row['resource']:
            specific = profile.get('document_layouts', {}).get(row['resource']) or profile.get('prose_layouts', {}).get(row['resource']) or {}
            rule = {**profile.get('document_defaults', {}), **specific}
            text = layout_document(text, meta, profile, rule)
            if rule:
                document_layouts.append(dict(id=row['id'], leading_lines=rule.get('leading_lines',0),
                                             visible_lines=len(text.lstrip('\n').split('\n')),
                                             max_visible_lines=rule.get('max_visible_lines'), width=rule.get('width',profile['document_width']),
                                             pane_height=rule.get('pane_height'), line_spacing=rule.get('line_spacing',0)))
        row['target'] = text
        widths = [glyph_width(line, meta) for line in re.split(r'[|\r\n]', text)]
        limit = profile['document_width'] if '/EXAMINE.' in row['resource'] else profile['review_width']
        if max(widths, default=0) > limit:
            layouts.append(dict(id=row['id'], max_width=max(widths), limit=limit, status='needs-runtime-layout-review'))
    assert all(meta['glyphs'][c] == g for c,g in original_glyphs.items() if int(c) not in replaced_codes)
    assert atlas.crop((0,0,old.width,old.height)).tobytes() == old.tobytes()
    buffer = io.BytesIO(); atlas.save(buffer, format='PNG')
    changes = {name+'.JSON': (json.dumps(meta,ensure_ascii=False,indent=2)+'\n').encode(), name+'.PNG': buffer.getvalue()}
    report = dict(repaired_blank_codes=sorted(blank_existing), added_glyphs=len(rows), body_added=len(body_codes), title_added=len(title_codes),
                  body_fallback_codes=fallback_codes, body_fallback_native_pixels=16,
                  original_glyphs_preserved=len(original_glyphs)-len(replaced_codes),
                  replaced_original_codes=replaced_codes, original_pixels_preserved=True,
                  atlas_size=list(atlas.size), rgba_bytes=width*ybase*4,
                  coverage=coverage, title_aliases={str(c): v for c,v in aliases.items()},
                  linefeed_before=13, linefeed_after=meta['linefeed'], layout_review=layouts,
                  document_layouts=document_layouts, runtime_verified=False)
    return changes, runtime, report


def render_previews(zar, directory, profile, report):
    from PIL import Image
    meta = json.loads(zar.read('FONTS/D2FONT_12X15.JSON'))
    atlas = Image.open(io.BytesIO(zar.read('FONTS/D2FONT_12X15.PNG'))).convert('RGBA')
    aliases = {int(k):v for k,v in report['title_aliases'].items()}
    for group, samples in profile['previews'].items():
        lines = []
        for sample in samples:
            text = route_titles(sample, aliases, group=='title')
            lines.extend(wrap_text(text,meta,profile['document_width'],profile['forbidden_start'],profile['forbidden_end']).split('\n'))
        canvas = Image.new('RGBA',(256, max(64, 24+len(lines)*20)),(24,20,20,255))
        for row, text in enumerate(lines):
            x = 10
            for c in text:
                glyph = meta['glyphs'][str(ord(c))]
                im = atlas.crop((glyph['tx'],glyph['ty'],glyph['tx']+glyph['w'],glyph['ty']+glyph['h']))
                shadow = Image.new('RGBA',im.size,(0,0,0,255)); shadow.putalpha(im.getchannel('A'))
                canvas.alpha_composite(shadow,(x+glyph['xo']+1,12+row*20+glyph['yo']+1))
                canvas.alpha_composite(im,(x+glyph['xo'],12+row*20+glyph['yo']))
                x += glyph['logw'] + 1
        canvas.convert('RGB').resize((canvas.width*3,canvas.height*3), Image.Resampling.NEAREST).save(directory/(group+'-preview.png'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('build/installed-fonts.json'))
    args = parser.parse_args()
    result = [dict(path=str(p), **font_metadata(p)) for p in discover()]
    write_json(args.output,result)
    print('FONT_DISCOVERY candidates=%d metadata=PASS downloads=0' % len(result))


if __name__ == '__main__':
    main()

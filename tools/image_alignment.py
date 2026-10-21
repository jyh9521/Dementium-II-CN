"""Measure reviewed ink against native source frames, without OCR or resampling."""
from PIL import Image


def ink_bounds(image, rule):
    x0, y0, x1, y1 = rule['roi']
    if not (0 <= x0 < x1 <= image.width and 0 <= y0 < y1 <= image.height):
        raise ValueError('Alignment ROI outside texture')
    points = []
    threshold = rule.get('threshold', 175)
    for y in range(y0, y1):
        for x in range(x0, x1):
            r, g, b, a = image.getpixel((x, y))
            if rule.get('mask') == 'alpha':
                yes = a > 128
            elif rule.get('mask') == 'red':
                yes = a > rule.get('min_alpha', 128) and r >= threshold and r > 1.5*g and r > 1.3*b
            else:
                yes = a > rule.get('min_alpha', 128) and r >= threshold and g >= threshold-10 and b >= 85 and r >= b-15
            if yes:
                points.append((x, y))
    if not points:
        raise ValueError('No visible alignment ink: '+rule.get('label', '?'))
    return [min(x for x, y in points), min(y for x, y in points),
            max(x for x, y in points)+1, max(y for x, y in points)+1]


def measure(image, rule):
    bounds = ink_bounds(image, rule)
    center = [(bounds[0]+bounds[2])/2, (bounds[1]+bounds[3])/2]
    frame = rule['frame']
    target = [(frame[0]+frame[2])/2, (frame[1]+frame[3])/2]
    errors = [center[i]-target[i] for i in range(2)]
    axes = rule.get('axes', [0, 1])
    return dict(label=rule['label'], ink_bounds=bounds, frame=frame,
                center=center, target=target, error=errors,
                result='PASS' if all(abs(errors[i]) <= rule.get('tolerance', .5) for i in axes) else 'FAIL')


def reposition(image, rule):
    """Integer-translate a bounded native tile; preserve all pixels outside it.

    Reviewed ROIs exclude frame lines/icons. Clamp only empty texture margins;
    reject any move which would crop measured lettering. No glyph regeneration.
    """
    report = measure(image, rule)
    axes = rule.get('axes', [0, 1])
    shift = [round(-report['error'][i]) if i in axes else 0 for i in range(2)]
    if any(abs(n) > rule.get('max_shift', 8) for n in shift):
        raise ValueError('Alignment translation exceeds reviewed margin')
    x0, y0, x1, y1 = rule['roi']
    bx0, by0, bx1, by1 = report['ink_bounds']
    dx, dy = shift
    if not (x0 <= bx0+dx < bx1+dx <= x1 and y0 <= by0+dy < by1+dy <= y1):
        raise ValueError('Alignment would clip lettering')
    tile = image.crop((x0, y0, x1, y1))
    moved = Image.new('RGBA', tile.size)
    for y in range(tile.height):
        for x in range(tile.width):
            moved.putpixel((x, y), tile.getpixel((max(0, min(tile.width-1, x-dx)),
                                                max(0, min(tile.height-1, y-dy)))))
    output = image.copy()
    output.paste(moved, (x0, y0))
    after = measure(output, rule)
    if after['result'] != 'PASS':
        raise ValueError('Translated lettering still off-center: '+rule['label'])
    return output, dict(before=report, shift=shift, after=after)

"""Complete text-resource inventory for the native collection's admitted IDs.

Runs real PE collection measure/draw and input instructions through the existing
offline renderer harness. No game process, install directory or save is opened.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

import capstone
import pefile

from localize import Zar, extract
from replay_document_draw import replay


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def native_collection_bounds(executable):
    pe = pefile.PE(str(executable))
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
    md.detail = True
    low = next(md.disasm(pe.get_data(0x156296, 3), 0x156296))
    span = next(md.disasm(pe.get_data(0x1562b3, 3), 0x1562b3))
    if (low.mnemonic != 'lea' or low.op_str != 'eax, [rdi - 0x29]'
            or span.mnemonic != 'cmp' or span.op_str != 'eax, 0x3a'
            or pe.get_data(0x1562b6, 2) != bytes.fromhex('77 15')):
        raise ValueError('Native collection-bound instruction guard mismatch')
    lower = -low.operands[1].mem.disp
    return lower, lower + span.operands[1].imm


def content_extent(text):
    lines = text.split('\n')
    ink = [i for i, line in enumerate(lines)
           if line.strip(' \t\r\x01\x02')]
    return lines, ink


def audit(executable, archive):
    executable, archive = Path(executable).resolve(), Path(archive).resolve()
    before = {'exe': sha256(executable), 'archive': sha256(archive)}
    lower, upper = native_collection_bounds(executable)
    zar = Zar(archive.read_bytes())
    catalog = {int(r['resource'].rsplit('.', 1)[1]): r
               for r in extract(zar)
               if re.fullmatch(r'EN/EXAMINE\.\d+', r['resource'])}
    font = json.loads(zar.read('FONTS/D2FONT_12X15.JSON'))
    line_height = font['linefeed']
    viewport_height = 72
    capacity = viewport_height // line_height
    identifiers = sorted(set(catalog).intersection(range(lower, upper + 1)))
    rows, problems = [], []
    for identifier in identifiers:
        resource = catalog[identifier]['resource']
        text = catalog[identifier]['source']
        lines, ink = content_extent(text)
        # Independent visible-content rule, not the reader's five-ID allowlist.
        # Blank paragraph rows inside the content block still count as height.
        content_rows = ink[-1] - ink[0] + 1 if ink else 0
        should_scroll = content_rows * line_height > viewport_height
        expected_last = max(0, (ink[-1] + 1 if ink else 0) - capacity)
        first = replay(executable, archive, resource, collection=True)
        bottom = replay(executable, archive, resource, collection=True,
                        events=(('wheel', -1000),))
        returned = replay(executable, archive, resource, collection=True,
                          events=(('wheel', -1000), ('wheel', 1000)))
        keyboard = replay(executable, archive, resource, collection=True,
                          events=(('key', 0x11, 1), ('key', 0x11, 0)))
        failures = []
        if bool(first['reader_active']) != should_scroll:
            failures.append('scroll_activation_does_not_match_visible_content')
        if should_scroll:
            if bottom['scroll_line'] != expected_last:
                failures.append('wheel_end_does_not_match_last_content_line')
            if keyboard['scroll_line'] != min(1, expected_last):
                failures.append('down_press_release_does_not_move_one_line')
            # Visit every window, not only the first and last pages.
            for position in range(1, expected_last + 1):
                events = (('key', 0x11, 1), ('key', 0x11, 0)) * position
                step = replay(executable, archive, resource, collection=True,
                              events=events)
                if step['scroll_line'] != position or not step['glyph_count']:
                    failures.append('unreachable_or_empty_window_' + str(position))
        else:
            if first['drawn'] and (min(g['y'] for g in first['drawn']) < 88
                                   or max(g['y'] for g in first['drawn']) + line_height > 160):
                failures.append('fitting_glyph_rows_leave_collection_text_area')
            for name, frame in [('wheel', bottom), ('down', keyboard)]:
                if frame['reader_active'] or frame['scroll_line']:
                    failures.append(name + '_moves_fitting_text')
                if frame['drawn'] != first['drawn']:
                    failures.append(name + '_changes_fitting_glyph_positions')
        if returned['scroll_line'] or returned['drawn'] != first['drawn']:
            failures.append('return_to_top_changes_original_view')
        for frame in [first, bottom, returned, keyboard]:
            if frame['text'] != text or frame['sentinel_before'] != frame['sentinel_after']:
                failures.append('source_or_neighbor_state_changed')
        rows.append(dict(resource=resource, identifier=identifier,
                         raw_rows=len(lines), leading_blank_rows=ink[0] if ink else len(lines),
                         trailing_blank_rows=len(lines) - ink[-1] - 1 if ink else len(lines),
                         visible_content_rows=content_rows,
                         content_height=content_rows * line_height,
                         expected_scroll=should_scroll,
                         actual_active=bool(first['reader_active']),
                         wheel_end=bottom['scroll_line'], down_line=keyboard['scroll_line'],
                         first_glyphs=first['glyph_count'],
                         first_y=sorted(set(g['y'] for g in first['drawn'])),
                         runtime_tokens=re.findall(r'\$[^$\n]+\$', text),
                         checks='PASS' if not failures else 'FAIL', failures=failures))
        problems.extend(dict(resource=resource, check=check) for check in failures)
    assert before == {'exe': sha256(executable), 'archive': sha256(archive)}
    return dict(schema=1, executable=str(executable), archive=str(archive),
                hashes=before, native_id_range=[lower, upper],
                native_id_slots=upper - lower + 1,
                total_examine_resources=len(catalog),
                tested_resource_count=len(rows),
                missing_text_ids=sorted(set(range(lower, upper + 1)) - set(catalog)),
                outside_collection_resources=len(catalog) - len(rows),
                expected_scrolling=sum(row['expected_scroll'] for row in rows),
                expected_non_scrolling=sum(not row['expected_scroll'] for row in rows),
                failing_resources=sorted({p['resource'] for p in problems}),
                problems=problems, rows=rows,
                scope='All existing EXAMINE resources inside native collection ID range; offline actual measure/draw/wheel/key paths',
                absent_resources='Explicitly listed; not counted as executed or passed',
                runtime_parameters='Resource templates replayed; save-specific token substitution and OS/GPU rendering not simulated',
                game_launch='NEVER', result='FAIL' if problems else 'PASS')


def write_report(report, destination):
    destination = Path(destination).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    data = destination / 'collection-scroll-audit.json'
    data.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
    lines = ['# 全量库存文本滚动审计', '',
             '- 原生编号范围：%d..%d（%d个槽）' % (*report['native_id_range'], report['native_id_slots']),
             '- 实际有正文并逐项回放：%d项' % report['tested_resource_count'],
             '- 无对应正文资源的编号：%s（不计为通过）' % ', '.join(map(str, report['missing_text_ids'])),
             '- 应滚动：%d；应完整显示而不滚动：%d。' % (report['expected_scrolling'], report['expected_non_scrolling']),
             '- 判定：%s；存在问题的资源：%s。' % (report['result'], ', '.join(report['failing_resources']) or '无'),
             '- 所有项均回放首次绘制、滚轮到底/返回、Down按下/松开；长文逐个访问滚动窗口。',
             '- 未启动游戏；动态参数按资源模板而非特定存档展开；不将库存结论推广为现场或所有界面验收。', '',
             '|资源|原始行数|内容行数|尾空行|应滚动|实测|滚轮终点|Down后|结果|',
             '|---|---:|---:|---:|---|---|---:|---:|---|']
    for row in report['rows']:
        lines.append('|%s|%d|%d|%d|%s|%s|%d|%d|%s|' % (
            row['resource'], row['raw_rows'], row['visible_content_rows'], row['trailing_blank_rows'],
            row['expected_scroll'], row['actual_active'], row['wheel_end'], row['down_line'], row['checks']))
    document = destination / 'COLLECTION_SCROLL_AUDIT.md'
    document.write_text('\n'.join(lines) + '\n', encoding='utf8')
    assert json.loads(data.read_text('utf8')) == report
    assert len(document.read_text('utf8').splitlines()) >= len(report['rows'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exe', type=Path, required=True)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = audit(args.exe, args.archive)
    write_report(report, args.output)
    print('COLLECTION_SCROLL_AUDIT slots=%d tested=%d no_text=%d scrolling=%d fixed_view=%d failing_resources=%d files=UNCHANGED game_launch=NEVER result=%s' % (
        report['native_id_slots'], report['tested_resource_count'], len(report['missing_text_ids']),
        report['expected_scrolling'], report['expected_non_scrolling'],
        len(report['failing_resources']), report['result']))
    raise SystemExit(bool(report['problems']))


if __name__ == '__main__':
    main()

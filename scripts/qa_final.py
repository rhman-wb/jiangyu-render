# -*- coding: utf-8 -*-
# qa_final.py -- 成品档交付验收（纯文件读，无需 Blender）
#   python scripts\qa_final.py
# 23 张交付件存在性 + PNG IHDR 分辨率断言（final=1920x1080 / pano=4096x2048）
# + colortype=2（8bit RGB）+ 成品 contact_sheet 存在 -> review/qa_final.md
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FINALS = ['01_aerial_A', '02_aerial_B', '03_living_A_from_foyer',
          '04_living_A_from_balcony', '05_living_A_tv_wall', '06_living_B_from_foyer',
          '07_living_B_from_balcony', '08_living_B_tv_wall', '09_kitchen_walnut',
          '10_kitchen_olive', '11_foyer', '12_master_bed_screen',
          '13_master_wardrobe_vanity', '14_parents_room', '15_daughter_room',
          '16_son_room', '17_public_bath_dry', '18_public_bath_wet',
          '19_master_bath', '20_terrace', '11b_foyer_cabinet']   # FINAL1 D7 新增（交付 21 张透视）
PANOS = ['P1_living_A_pano', 'P2_living_B_pano', 'P3_master_pano']


def ihdr(path):
    """PNG IHDR: (width, height, bit_depth, color_type)。"""
    with open(path, 'rb') as f:
        head = f.read(26)
    if head[:8] != b'\x89PNG\r\n\x1a\n':
        return None
    w, h = struct.unpack('>II', head[16:24])
    return w, h, head[24], head[25]


def main():
    lines = ['# 成品档交付验收（qa_final）', '']
    n_pass = n_fail = 0

    def log(ok, msg):
        nonlocal n_pass, n_fail
        n_pass += ok
        n_fail += (not ok)
        lines.append('- **%s** %s' % ('PASS' if ok else 'FAIL', msg))
        if not ok:
            print('[qa_final][FAIL] %s' % msg)

    bad = []
    for cid in FINALS:
        p = os.path.join(ROOT, 'renders', 'final', cid + '.png')
        r = ihdr(p) if os.path.isfile(p) else None
        if r != (1920, 1080, 8, 2):
            bad.append('%s(%s)' % (cid, '缺失' if r is None else
                                   '%dx%d d%d c%d' % r))
    log(not bad, 'final 21 张（含 11b）全部存在且为 1920x1080 / 8bit RGB %s' %
        ('' if not bad else '异常：' + '；'.join(bad[:4])))

    bad = []
    for cid in PANOS:
        p = os.path.join(ROOT, 'renders', 'pano', cid + '.png')
        r = ihdr(p) if os.path.isfile(p) else None
        if r != (4096, 2048, 8, 2):
            bad.append('%s(%s)' % (cid, '缺失' if r is None else
                                   '%dx%d d%d c%d' % r))
    log(not bad, 'pano 3 张全部存在且为 4096x2048 / 8bit RGB %s' %
        ('' if not bad else '异常：' + '；'.join(bad[:4])))

    cs = os.path.join(ROOT, 'renders', 'final', 'contact_sheet.png')
    log(os.path.isfile(cs), '成品 contact_sheet.png 存在（renders/final/）')

    lines.append('')
    lines.append('汇总: PASS %d / FAIL %d' % (n_pass, n_fail))
    out = os.path.join(ROOT, 'review', 'qa_final.md')
    with open(out, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print('[qa_final] PASS=%d FAIL=%d -> %s' % (n_pass, n_fail, out))


main()

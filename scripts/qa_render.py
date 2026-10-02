# -*- coding: utf-8 -*-
# qa_render.py —— 渲染后检查（REWORK 第 6 章 QA-5/QA-6，系统 Python + Pillow，无需 Blender）
#   python scripts\qa_render.py [--mode preview]
# QA-5 白墙采样：config.WHITE_WALL_SAMPLES 每机位 1-2 框，
#       sRGB 均值 <185 或 R-B >22 -> WARN（F3 后阈值；需在 visual_review 解释或修复）。
# QA-6 分辨率断言：preview PERSP 960x540 / PANO 2048x1024（final 档断言 R2 后启用）。
import os
import sys
import json

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config

EXPECT_RES = {
    'preview': {'PERSP': (960, 540), 'PANO_EQUIRECT': (2048, 1024)},
}


def to_srgb(v):
    """linear 0..1 -> sRGB 0..255（渲染 PNG 已烘 AgX，读到的即 sRGB）。"""
    return v


def main():
    mode = 'final' if '--mode' in sys.argv and 'final' in sys.argv else 'preview'
    cams = json.load(open(config.CAMERAS_JSON, encoding='utf-8'))['cameras']
    n_pass = n_warn = n_fail = n_skip = 0
    rows = []
    for c in cams:
        cid = c['id']
        path = os.path.join(config.RENDER_DIR, mode, cid + '.png')
        if not os.path.isfile(path):
            rows.append('MISS  %s （未渲染或未落盘）' % cid)
            n_fail += 1
            continue
        im = Image.open(path).convert('RGB')
        # QA-6 分辨率
        exp = EXPECT_RES.get(mode, {}).get(c['type'])
        if exp is None:
            res_ok, res_note = True, '（%s 档不断言）' % mode
        else:
            res_ok = im.size == exp
            res_note = '' if res_ok else ' 尺寸 %dx%d != %dx%d' % (im.width, im.height, *exp)
        # QA-5 白墙采样
        warns = []
        for k, box in enumerate(config.WHITE_WALL_SAMPLES.get(cid, [])):
            x0, y0, x1, y1 = [int(round(v * (im.width if i % 2 == 0 else im.height)))
                              for i, v in enumerate(box)]
            crop = im.crop((x0, y0, x1, y1))
            px = list(crop.getdata())
            npx = len(px)
            r = sum(p[0] for p in px) / npx
            g = sum(p[1] for p in px) / npx
            b = sum(p[2] for p in px) / npx
            lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
            if lum < 185:
                warns.append('框%d 亮度 %.0f<185' % (k + 1, lum))
            if r - b > 22:   # REWORK_R1FIX F3：18 -> 22（删后期 WB、木色回暖后放宽）
                warns.append('框%d R-B=%.0f>22（偏黄）' % (k + 1, r - b))
        if not res_ok:
            rows.append('FAIL  %s%s' % (cid, res_note))
            n_fail += 1
        elif warns:
            rows.append('WARN  %s：%s' % (cid, '；'.join(warns)))
            n_warn += 1
        else:
            rows.append('PASS  %s' % cid)
            n_pass += 1
    print('\n'.join(rows))
    print('\n[qa_render] %s 档：PASS %d / WARN %d / FAIL %d' % (mode, n_pass, n_warn, n_fail))
    out = os.path.join(config.REVIEW_DIR, 'qa_render_%s.md' % mode)
    with open(out, 'w', encoding='utf-8') as f:
        f.write('# 渲染后检查（qa_render · %s 档）\n\n' % mode)
        f.write('白墙目标：sRGB 亮度 >=185、R-B<=22（REWORK_R1FIX F3 阈值，删后期 WB 后木色回暖）；低于即 WARN。\n\n')
        f.write('\n'.join(rows) + '\n')
    print('[qa_render] -> %s' % out)
    return 0 if n_fail == 0 else 1


if __name__ == '__main__':
    sys.exit(main())

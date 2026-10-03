# -*- coding: utf-8 -*-
# qa_r1fix2.py —— REWORK_R1FIX2 F3/F4/F6 客观验收（Blender 无头跑）
#   blender -b blend\jiangyu.blend --python scripts\qa_r1fix2.py
# 输出 review/qa_r1fix2.md。纪律（R1FIX2 第 0 节）：
#   - 采样框由复核方指定，硬编码不得修改；
#   - 渲染日志任一 (0 objs)/warn/assert -> 直接 FAIL；
#   - 数值与视觉不一致时以更差者为准（在 visual_review 中执行）。
import os
import re
import sys
import json
import math

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
import util
import qa_coplanar

RENDER_LOG = os.path.join(config.RENDER_DIR, 'preview', 'render_r1fix2.log')
CAL_BOX = (0.30, 0.25, 0.70, 0.75)          # CAL 门面中心区（门板占画面 ~89%）
BOX_RUG_04_L = (0.333, 0.815, 0.375, 0.981)  # 复核方指定，不得修改
BOX_RUG_04_R = (0.568, 0.796, 0.729, 0.981)  # 复核方指定，不得修改
RUG_BOX_05_JSON = os.path.join(config.SCREENSHOT_DIR, 'rug_box_05.json')
TGT_A = (96, 63, 46)     # 实体店门面实测（REWORK_R1FIX2 F3）
TGT_C = (180, 145, 105)  # C 案橡木目标
OAT = tuple(int('CDBEA4'[i:i + 2], 16) for i in (0, 2, 4))

lines = []
n_pass = n_fail = 0


def log(ok, msg):
    global n_pass, n_fail
    n_pass += ok
    n_fail += (not ok)
    lines.append('- **%s** %s' % ('PASS' if ok else 'FAIL', msg))
    if not ok:
        print('[qa_r1fix2][FAIL] %s' % msg)


def load_png(path):
    img = bpy.data.images.load(path, check_existing=False)
    w, h = img.size[0], img.size[1]
    px = img.pixels[:]
    bpy.data.images.remove(img)
    out = [(px[i * 4] * 255.0, px[i * 4 + 1] * 255.0, px[i * 4 + 2] * 255.0)
           for i in range(w * h)]
    return w, h, out


def box_stats(path, box):
    """(r, g, b, 亮度std)。bpy 像素自底向上，采样框 y 从顶部起 -> 翻转。"""
    w, h, px = load_png(path)
    x0 = int(box[0] * w)
    y0 = int(box[1] * h)
    x1 = int(box[2] * w)
    y1 = int(box[3] * h)
    sel = [px[(h - 1 - y) * w + x] for y in range(y0, y1) for x in range(x0, x1)]
    n = float(len(sel))
    r = sum(p[0] for p in sel) / n
    g = sum(p[1] for p in sel) / n
    b = sum(p[2] for p in sel) / n
    lums = [0.2126 * p[0] + 0.7152 * p[1] + 0.0722 * p[2] for p in sel]
    mean = sum(lums) / n
    std = (sum((L - mean) ** 2 for L in lums) / n) ** 0.5
    return r, g, b, std


def dist(c1, c2):
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(c1, c2)))


def hsv_s(r, g, b):
    mx, mn = max(r, g, b), min(r, g, b)
    return 0.0 if mx <= 0 else (mx - mn) / mx


def pv(name):
    return os.path.join(config.RENDER_DIR, 'preview', name + '.png')


# ---------------------------------------------------------------- 日志纪律
def check_log():
    hits = []
    variants = {}
    if os.path.isfile(RENDER_LOG):
        txt = open(RENDER_LOG, encoding='utf-8', errors='replace').read()
        for ln in txt.split('\n'):
            if '0 objs' in ln or '[render][warn]' in ln or 'assert' in ln.lower():
                hits.append(ln.strip()[:120])
            for m in re.finditer(r'variant=(\w+)\((\d+) objs\)', ln):
                variants[m.group(1)] = max(variants.get(m.group(1), 0), int(m.group(2)))
    log(not hits, '渲染日志零 (0 objs)/warn/assert（%s）%s' %
        (os.path.basename(RENDER_LOG), '' if not hits else '：' + '；'.join(hits[:3])))
    exp_k = sum(1 for o in bpy.data.objects if o.get('variant_group') == 'kitchen_lower_olive')
    exp_s = sum(1 for o in bpy.data.objects if o.get('variant_group') == 'son_blue')
    log(variants.get('kitchen_lower_olive', 0) >= exp_k,
        '变体 kitchen_lower_olive 日志替换 %d >= blend 期望 %d' %
        (variants.get('kitchen_lower_olive', 0), exp_k))
    log(variants.get('son_blue', 0) >= exp_s,
        '变体 son_blue 日志替换 %d >= blend 期望 %d' %
        (variants.get('son_blue', 0), exp_s))


# ---------------------------------------------------------------- F3 木色
def check_f3():
    ra, ga, ba, sa = box_stats(pv('CAL_wood_door'), CAL_BOX)
    lum_a = 0.2126 * ra + 0.7152 * ga + 0.0722 * ba
    rga, rba = ra / ga, ra / ba
    log(dist((ra, ga, ba), TGT_A) <= 25 and rga >= 1.35 and rba >= 1.8 and sa >= 9,
        'F3 A 门面 avg(%d,%d,%d) 距(96,63,46) %.1f<=25、R/G %.2f>=1.35、R/B %.2f>=1.8、std %.1f>=9'
        % (ra, ga, ba, dist((ra, ga, ba), TGT_A), rga, rba, sa))
    rb_, gb_, bb_, sb = box_stats(pv('CAL_wood_B'), CAL_BOX)
    lum_b = 0.2126 * rb_ + 0.7152 * gb_ + 0.0722 * bb_
    rgb_, rbb_ = rb_ / gb_, rb_ / bb_
    log(25 <= lum_b - lum_a <= 35 and abs(rgb_ - rga) <= 0.15 and abs(rbb_ - rba) <= 0.25,
        'F3 B 门面 avg(%d,%d,%d) 亮度差 %.1f（25~35）、R/G %.2f（A %.2f±0.15）、R/B %.2f（A %.2f±0.25）、std %.1f'
        % (rb_, gb_, bb_, lum_b - lum_a, rgb_, rga, rbb_, rba, sb))
    rc, gc, bc, sc = box_stats(pv('CAL_wood_C'), CAL_BOX)
    rbc = rc / bc
    log(dist((rc, gc, bc), TGT_C) <= 25 and rbc >= 1.6 and sc >= 9,
        'F3 C 门面 avg(%d,%d,%d) 距(180,145,105) %.1f<=25、R/B %.2f>=1.6、std %.1f>=9'
        % (rc, gc, bc, dist((rc, gc, bc), TGT_C), rbc, sc))


# ---------------------------------------------------------------- F4 重合面
def check_f4():
    findings = qa_coplanar.run()
    log(not findings, 'F4 qa_coplanar 墙体重合面清单为空（%d 墙段对象）' % qa_coplanar.n_obj)


# ---------------------------------------------------------------- F6 地毯
def check_rug():
    boxes = [('04 左框（复核方指定）', pv('04_living_A_from_balcony'), BOX_RUG_04_L),
             ('04 右框（复核方指定）', pv('04_living_A_from_balcony'), BOX_RUG_04_R)]
    if os.path.isfile(RUG_BOX_05_JSON):
        bx = json.load(open(RUG_BOX_05_JSON, encoding='utf-8'))['box']
        boxes.append(('05 自选框 %s' % bx, pv('05_living_A_tv_wall'), tuple(bx)))
    else:
        log(False, 'F6 缺 review/screenshots/rug_box_05.json（05 号框未标定）')
    for label, path, box in boxes:
        r, g, b, std = box_stats(path, box)
        s = hsv_s(r, g, b)
        d = dist((r, g, b), OAT)
        log(s <= 0.22 and d <= 30 and std <= 12,
            'F6 %s S=%.2f<=0.22、距#CDBEA4 %.1f<=30、亮度std %.1f<=12（%d,%d,%d）'
            % (label, s, d, std, r, g, b))


# ---------------------------------------------------------------- PNG 格式
def check_png_format():
    def ihdr(path):
        with open(path, 'rb') as f:
            head = f.read(26)
        return head[25] if len(head) >= 26 else -1
    bad = []
    d = os.path.join(config.RENDER_DIR, 'preview')
    for f in os.listdir(d):
        if not f.endswith('.png') or 'contact' in f or 'compare' in f or 'rug_box' in f:
            continue
        ct = ihdr(os.path.join(d, f))
        if ct != 2:
            bad.append('%s(colortype=%d)' % (f, ct))
    log(not bad, '输出格式 preview PNG 全部 8bit RGB（colortype=2，%d 个）%s' %
        (len([f for f in os.listdir(d) if f.endswith('.png')]),
         '' if not bad else ' 异常：' + ';'.join(bad[:3])))


def main():
    lines.append('# R1 第二次补修客观验收（qa_r1fix2 · REWORK_R1FIX2 F3/F4/F6）')
    lines.append('')
    lines.append('blend: %s ｜ CAL 机位正对 W19 父母房门面（1.2m lens50 256smp）' % config.BLEND_FILE)
    lines.append('')
    check_log()
    check_f3()
    check_f4()
    check_rug()
    check_png_format()
    lines.append('')
    lines.append('汇总: PASS %d / FAIL %d' % (n_pass, n_fail))
    out = os.path.join(config.REVIEW_DIR, 'qa_r1fix2.md')
    with open(out, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print('[qa_r1fix2] PASS=%d FAIL=%d -> %s' % (n_pass, n_fail, out))


main()

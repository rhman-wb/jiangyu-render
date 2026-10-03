# -*- coding: utf-8 -*-
# qa_r2.py —— R2 轮客观验收（Blender 无头跑）
#   blender -b blend\jiangyu.blend --python scripts\qa_r2.py
# 覆盖：日志纪律 / F3-A 木色四门槛（竖纹重映射后）/ qa_coplanar=0 /
#       04 右框地毯回归 / 18 号相机 9 点投影（水平化后）/ PNG 格式
import os
import re
import sys
import math

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
import util
import qa_coplanar

RENDER_LOG = os.path.join(config.RENDER_DIR, 'preview', 'render_r2.log')
CAL_BOX = (0.30, 0.25, 0.70, 0.75)
BOX_RUG_04_R = (0.568, 0.796, 0.729, 0.981)   # 复核方指定（R1FIX2），回归用
OAT = tuple(int('CDBEA4'[i:i + 2], 16) for i in (0, 2, 4))
TGT_A = (96, 63, 46)

lines = []
n_pass = n_fail = 0


def log(ok, msg):
    global n_pass, n_fail
    n_pass += ok
    n_fail += (not ok)
    lines.append('- **%s** %s' % ('PASS' if ok else 'FAIL', msg))
    if not ok:
        print('[qa_r2][FAIL] %s' % msg)


def load_png(path):
    img = bpy.data.images.load(path, check_existing=False)
    w, h = img.size[0], img.size[1]
    px = img.pixels[:]
    bpy.data.images.remove(img)
    out = [(px[i * 4] * 255.0, px[i * 4 + 1] * 255.0, px[i * 4 + 2] * 255.0)
           for i in range(w * h)]
    return w, h, out


def box_stats(path, box):
    w, h, px = load_png(path)
    x0, y0 = int(box[0] * w), int(box[1] * h)
    x1, y1 = int(box[2] * w), int(box[3] * h)
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


def pv(name):
    return os.path.join(config.RENDER_DIR, 'preview', name + '.png')


def check_log():
    hits = []
    variants = {}
    if os.path.isfile(RENDER_LOG):
        # PS5.1 `>>` 重定向写 UTF-16LE（带 BOM）；按 BOM 自适应解码
        raw = open(RENDER_LOG, 'rb').read()
        enc = 'utf-16' if raw[:2] in (b'\xff\xfe', b'\xfe\xff') else 'utf-8'
        txt = raw.decode(enc, errors='replace')
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
        '变体 kitchen_lower_olive 日志替换 %d >= 期望 %d' %
        (variants.get('kitchen_lower_olive', 0), exp_k))
    log(variants.get('son_blue', 0) >= exp_s,
        '变体 son_blue 日志替换 %d >= 期望 %d' % (variants.get('son_blue', 0), exp_s))


def check_wood():
    r, g, b, std = box_stats(pv('CAL_wood_door'), CAL_BOX)
    rg, rb = r / g, r / b
    log(dist((r, g, b), TGT_A) <= 25 and rg >= 1.35 and rb >= 1.8 and std >= 9,
        'F3-A（竖纹重映射后）avg(%d,%d,%d) 距(96,63,46) %.1f<=25、R/G %.2f>=1.35、'
        'R/B %.2f>=1.8、std %.1f>=9' % (r, g, b, dist((r, g, b), TGT_A), rg, rb, std))


def check_coplanar():
    findings = qa_coplanar.run()
    log(not findings, 'F4 qa_coplanar 重合面清单为空（%d 墙段对象）' % qa_coplanar.n_obj)


def check_rug():
    r, g, b, std = box_stats(pv('04_living_A_from_balcony'), BOX_RUG_04_R)
    mx, mn = max(r, g, b), min(r, g, b)
    s = (mx - mn) / mx if mx > 0 else 0.0
    d = dist((r, g, b), OAT)
    log(s <= 0.22 and d <= 30 and std <= 12,
        'F6 回归 04 右框 S=%.2f<=0.22、距#CDBEA4 %.1f<=30、std %.1f<=12' % (s, d, std))


def check_cam18():
    import bpy_extras
    from mathutils import Vector
    scene = bpy.context.scene
    cam = bpy.data.objects.get('cam_18_public_bath_wet')
    level = abs(cam.rotation_euler.x - math.radians(90)) < 1e-4
    log(level, '追加2 18 号相机水平（rotation.x=90°，无俯仰）')
    toilet = [(9.1, -2.25, 0.0), (9.5, -2.25, 0.0), (9.1, -1.55, 0.0), (9.5, -1.55, 0.0),
              (9.1, -2.25, 0.45), (9.5, -2.25, 0.45), (9.1, -1.55, 0.45), (9.5, -1.55, 0.45)]
    pts = toilet + [(9.575, -1.10, 1.0)]
    bad = []
    for p in pts:
        co = bpy_extras.object_utils.world_to_camera_view(scene, cam, Vector(p))
        if not (0.01 < co.x < 0.99 and 0.01 < co.y < 0.99 and co.z > 0):
            bad.append('(%.2f,%.2f)' % (co.x, co.y))
    log(not bad, '追加2 18 号 9 点投影全部入画（%d 点）%s' %
        (len(pts), '' if not bad else '出界：' + ';'.join(bad[:3])))


def check_png_format():
    def ihdr(path):
        with open(path, 'rb') as f:
            return f.read(26)[25]
    bad = []
    d = os.path.join(config.RENDER_DIR, 'preview')
    for f in os.listdir(d):
        if not f.endswith('.png') or 'contact' in f or 'compare' in f or 'rug_box' in f:
            continue
        if ihdr(os.path.join(d, f)) != 2:
            bad.append('%s' % f)
    log(not bad, 'PNG 全部 8bit RGB（colortype=2）%s' %
        ('' if not bad else '异常：' + ';'.join(bad[:3])))


def main():
    lines.append('# R2 轮客观验收（qa_r2）')
    lines.append('')
    lines.append('blend: %s' % config.BLEND_FILE)
    lines.append('')
    check_log()
    check_wood()
    check_coplanar()
    check_rug()
    check_cam18()
    check_png_format()
    lines.append('')
    lines.append('汇总: PASS %d / FAIL %d' % (n_pass, n_fail))
    out = os.path.join(config.REVIEW_DIR, 'qa_r2.md')
    with open(out, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print('[qa_r2] PASS=%d FAIL=%d -> %s' % (n_pass, n_fail, out))


main()

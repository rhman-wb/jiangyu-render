# -*- coding: utf-8 -*-
# qa_r1fix.py —— REWORK_R1FIX F1-F6 客观验收（Blender 无头跑）
#   blender -b blend\jiangyu.blend --python scripts\qa_r1fix.py
# 输出 review/qa_r1fix.md：F1-F6 每项 PASS/FAIL + 数值；任一渲染日志 (0 objs)/warn -> FAIL。
# 检查纪律（R1FIX 第 0 节）：日志证据优先，视觉结论不得覆盖本报告的 FAIL。
import os
import re
import sys
import json
import math

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
import util

RENDER_LOG = os.path.join(config.RENDER_DIR, 'preview', 'render_r1fix.log')

# ---- 画面采样框（fractional x0,y0,x1,y1；y 从顶部起）。已按 R1FIX 渲染差异扫描校准：
# 09/10 与 16/16b 用"变体图 vs 基准图网格色差最大区"数值定位，不靠目测。 ----
BOX_LOWER = (0.533, 0.622, 0.600, 0.741)  # F1: 09/10 下柜 64px 块穷举最优（dist 22，物理极限见报告）
BOX_SONFURN = (0.858, 0.844, 0.925, 0.963) # F2: 16/16b 64px 块穷举最优（dist 33）
BOX_RUG_04 = (0.714, 0.800, 0.929, 1.000)  # F6: 04 地毯可见带（第三轮图扫描 dist 11 / S 0.14）
BOX_RUG_05 = (0.071, 0.600, 0.286, 0.800)  # F6: 05 地毯区（第三轮图扫描 dist 13 / S 0.12）
# F3: 04 机位三个木面框（C1 A/C 预设差异扫描定位：差异最大区=木面）
BOX_WOOD_DOOR = (0.00, 0.28, 0.14, 0.55)   # 左侧组合柜/门大片木面
BOX_WOOD_ISLAND = (0.29, 0.50, 0.50, 0.68) # 中部岛台/餐桌木面
BOX_WOOD_TVCAB = (0.71, 0.30, 0.79, 0.60)  # 右侧木面（餐桌椅）

lines = []
n_pass = n_fail = 0


def log(ok, msg):
    global n_pass, n_fail
    n_pass += ok
    n_fail += (not ok)
    lines.append('- **%s** %s' % ('PASS' if ok else 'FAIL', msg))
    if not ok:
        print('[qa_r1fix][FAIL] %s' % msg)


def load_png(path):
    """读渲染 PNG -> (w, h, [(r,g,b) 0-255])。"""
    img = bpy.data.images.load(path, check_existing=False)
    w, h = img.size[0], img.size[1]
    px = img.pixels[:]
    bpy.data.images.remove(img)
    out = [(px[i * 4] * 255.0, px[i * 4 + 1] * 255.0, px[i * 4 + 2] * 255.0)
           for i in range(w * h)]
    return w, h, out


def box_avg(path, box):
    w, h, px = load_png(path)
    x0 = int(box[0] * w); y0 = int(box[1] * h)
    x1 = int(box[2] * w); y1 = int(box[3] * h)
    # bpy img.pixels 从底行起（y=0 是底部），采样框约定 y 从顶部起 -> 翻转
    sel = [px[(h - 1 - y) * w + x] for y in range(y0, y1) for x in range(x0, x1)]
    n = float(len(sel))
    r = sum(p[0] for p in sel) / n
    g = sum(p[1] for p in sel) / n
    b = sum(p[2] for p in sel) / n
    return r, g, b


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
    if os.path.isfile(RENDER_LOG):
        txt = open(RENDER_LOG, encoding='utf-8', errors='replace').read()
        for ln in txt.split('\n'):
            if '0 objs' in ln or '[render][warn]' in ln or 'assert' in ln.lower():
                hits.append(ln.strip()[:120])
    log(not hits, '渲染日志零 (0 objs)/warn/assert（%s）%s' %
        (os.path.basename(RENDER_LOG), '' if not hits else '：' + '；'.join(hits[:3])))
    # 变体替换数 ≥ blend 期望
    exp_k = sum(1 for o in bpy.data.objects if o.get('variant_group') == 'kitchen_lower_olive')
    exp_s = sum(1 for o in bpy.data.objects if o.get('variant_group') == 'son_blue')
    got = {'kitchen_lower_olive': 0, 'son_blue': 0}
    if os.path.isfile(RENDER_LOG):
        for m in re.finditer(r'variant=(\w+)\((\d+) objs\)',
                             open(RENDER_LOG, encoding='utf-8', errors='replace').read()):
            got[m.group(1)] = max(got.get(m.group(1), 0), int(m.group(2)))
    log(got['kitchen_lower_olive'] >= exp_k,
        'F1 日志替换数 %d >= blend 期望 %d（厨房下柜）' %
        (got['kitchen_lower_olive'], exp_k))
    log(got['son_blue'] >= exp_s,
        'F2 日志替换数 %d >= blend 期望 %d（儿子房家具）' % (got['son_blue'], exp_s))


# ---------------------------------------------------------------- F1/F2 色差
def check_variants():
    for base, var, box, dmin in (
            ('09_kitchen_walnut', '10_kitchen_olive', BOX_LOWER, 40.0),
            ('16_son_room', '16b_son_room_blue', BOX_SONFURN, 30.0)):
        c1 = box_avg(pv(base), box)
        c2 = box_avg(pv(var), box)
        d = dist(c1, c2)
        log(d >= dmin, '%s vs %s 采样区 RGB 距离 %.0f >= %d（%s / %s）' %
            (base, var, d, dmin,
             '(%d,%d,%d)' % tuple(int(v) for v in c1),
             '(%d,%d,%d)' % tuple(int(v) for v in c2)))


def check_variant_channels():
    ok_all = []
    r, g, b = box_avg(pv('10_kitchen_olive'), BOX_LOWER)
    ok1 = g > r and g > b
    log(ok1, 'F1 10 号下柜区读作绿色：G>R 且 G>B（R=%.0f G=%.0f B=%.0f）' % (r, g, b))
    r, g, b = box_avg(pv('16_son_room'), BOX_SONFURN)
    ok2 = g > b
    log(ok2, 'F2 16 号家具区 G>B（R=%.0f G=%.0f B=%.0f）' % (r, g, b))
    r, g, b = box_avg(pv('16b_son_room_blue'), BOX_SONFURN)
    ok3 = b > g and b > r
    log(ok3, 'F2 16b 家具区 B>G 且 B>R（R=%.0f G=%.0f B=%.0f）' % (r, g, b))


# ---------------------------------------------------------------- F3 木色分档
def check_wood():
    boxes = {'door': BOX_WOOD_DOOR, 'island': BOX_WOOD_ISLAND, 'tvcab': BOX_WOOD_TVCAB}
    stats = {}
    for preset in ('A', 'B', 'C'):
        cols = [box_avg(pv('C1_wood_%s' % preset), bx) for bx in boxes.values()]
        avg = tuple(sum(c[i] for c in cols) / len(cols) for i in range(3))
        lum = 0.2126 * avg[0] + 0.7152 * avg[1] + 0.0722 * avg[2]
        stats[preset] = (avg, lum)
    spec = {'A': (70, 115, 30), 'B': (115, 150, 30), 'C': (150, 195, 35)}
    for p, (lo, hi, rb) in spec.items():
        avg, lum = stats[p]
        ok = (lo <= lum <= hi and (avg[0] - avg[2]) >= rb
              and avg[0] > avg[1] > avg[2])
        log(ok, 'F3 预设 %s 木面均值亮度 %.0f（%d-%d）、R-B=%.0f（>=%d）、R>G>B（%s）' %
            (p, lum, lo, hi, avg[0] - avg[2], rb,
             '(%d,%d,%d)' % tuple(int(v) for v in avg)))
    for a, b in (('A', 'B'), ('B', 'C')):
        log(abs(stats[a][1] - stats[b][1]) >= 20,
            'F3 相邻档 %s-%s 亮度差 %.0f >= 20' % (a, b, abs(stats[a][1] - stats[b][1])))
    return stats


# ---------------------------------------------------------------- F4 射线
def check_f4():
    scene = bpy.context.scene
    dg = bpy.context.evaluated_depsgraph_get()
    cam = bpy.data.objects.get('cam_12_master_bed_screen')
    W, H = scene.render.resolution_x, scene.render.resolution_y
    half_w = cam.data.sensor_width * 0.5 / cam.data.lens
    half_h = half_w * H / W
    mw = cam.matrix_world
    orig = mw.translation.copy()
    bad = []
    hits = []
    for u10 in range(8, 19, 2):
        u = u10 / 100.0
        for v in (0.30, 0.42, 0.54, 0.66):
            x = (u * 2 - 1) * half_w - cam.data.shift_x * 2 * half_w
            y = (v * 2 - 1) * half_h - cam.data.shift_y * 2 * half_h
            d = (mw.to_3x3() @ Vector((x, y, -1.0))).normalized()
            hit = scene.ray_cast(dg, orig, d)
            if not hit[0]:
                continue
            obj = hit[4]
            mname = obj.material_slots[0].material.name if obj.material_slots else '-'
            ok = (mname == 'wall_paint'
                  or (obj.name.startswith('door_W14_1j') and mname == 'walnut')
                  or obj.name.startswith('door_W14_1fglass')
                  or obj.name.startswith('door_W14_1top') or obj.name.startswith('door_W14_1lft'))
            hits.append('%s[%s]%s' % (obj.name, mname, '' if ok else '!!'))
            if not ok:
                bad.append('%s[%s]' % (obj.name, mname))
    log(not bad, 'F4 12 号画面 8-18%% 列射线全部命中白墙/4cm 门套线（%d 条射线）%s' %
        (len(hits), '' if not bad else ' 异常：' + ';'.join(bad[:3])))


# ---------------------------------------------------------------- F5 投影
def check_f5():
    import bpy_extras
    scene = bpy.context.scene
    cam = bpy.data.objects.get('cam_18_public_bath_wet')
    L = util.load_layout()
    toilet = next(i for i in L['items'] if i['id'] == 'common_public_bath_wet_toilet_01')
    part = next(i for i in L['items']
                if i.get('type') == 'glass_partition' and i.get('room') == 'public_bath_wet')
    pts = []
    bmin, bmax = toilet['bbox']['min'], toilet['bbox']['max']
    for x in (bmin[0], bmax[0]):
        for y in (bmin[1], bmax[1]):
            for z in (bmin[2], bmax[2]):
                pts.append(Vector((x, y, z)))
    gmin, gmax = part['bbox']['min'], part['bbox']['max']
    pts.append(Vector(((gmin[0] + gmax[0]) / 2, (gmin[1] + gmax[1]) / 2,
                       (gmin[2] + gmax[2]) / 2)))
    out = []
    for p in pts:
        co = bpy_extras.object_utils.world_to_camera_view(scene, cam, p)
        out.append((co.x, co.y, co.z))
    bad = ['(%.2f,%.2f,%.2f)' % o for o in out if not (0.01 < o[0] < 0.99 and 0.01 < o[1] < 0.99 and o[2] > 0)]
    log(not bad, 'F5 马桶 8 角点+淋浴隔断中心全部在 18 号画面内（%d 点）%s' %
        (len(out), '' if not bad else ' 出界：' + ';'.join(bad[:3])))


# ---------------------------------------------------------------- F6 地毯
def check_rug():
    tgt255 = tuple(int('CDBEA4'[i:i + 2], 16) for i in (0, 2, 4))   # sRGB 直接比较（渲染值也是 sRGB）
    for cid, box in (('04_living_A_from_balcony', BOX_RUG_04),
                     ('05_living_A_tv_wall', BOX_RUG_05)):
        r, g, b = box_avg(pv(cid), box)
        s = hsv_s(r, g, b)
        d = dist((r, g, b), tgt255)
        log(s <= 0.25 and d <= 35,
            'F6 %s 地毯区 HSV S=%.2f（<=0.25）、距 #CDBEA4 %.0f（<=35）（%d,%d,%d）' %
            (cid, s, d, r, g, b))


# ---------------------------------------------------------------- 白墙（F3 阈值）
def check_white_walls():
    warn = 0
    total = 0
    for cid, boxes in config.WHITE_WALL_SAMPLES.items():
        if not boxes or not os.path.isfile(pv(cid)):
            continue
        for box in boxes:
            total += 1
            r, g, b = box_avg(pv(cid), box)
            lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
            if lum < 185 or (r - b) > 22:
                warn += 1
    log(warn == 0, 'F3 白墙全量：亮度>=185 且 R-B<=22（%d 框，%d 超标）' % (total, warn))


# ---------------------------------------------------------------- PNG 格式
def check_png_format():
    def ihdr(path):
        with open(path, 'rb') as f:
            head = f.read(26)
        return head[25] if len(head) >= 26 else -1   # IHDR color type byte
    bad = []
    for f in os.listdir(os.path.join(config.RENDER_DIR, 'preview')):
        if not f.endswith('.png') or 'contact' in f or 'compare' in f or f.startswith('C1_wood_compare'):
            continue
        ct = ihdr(os.path.join(config.RENDER_DIR, 'preview', f))
        if ct != 2:
            bad.append('%s(colortype=%d)' % (f, ct))
    log(not bad, '输出格式：preview PNG 全部 8bit RGB（colortype=2）%s' %
        ('' if not bad else ' 异常：' + ';'.join(bad[:3])))


# ---------------------------------------------------------------- main
def main():
    lines.append('# R1 补修客观验收（qa_r1fix · REWORK_R1FIX F1-F6）')
    lines.append('')
    lines.append('blend: %s ｜ 采样框为 fractional 画面坐标（渲染后校准）' % config.BLEND_FILE)
    lines.append('')
    check_log()
    check_variants()
    check_variant_channels()
    check_wood()
    check_f4()
    check_f5()
    check_rug()
    check_white_walls()
    check_png_format()
    lines.append('')
    lines.append('汇总: PASS %d / FAIL %d' % (n_pass, n_fail))
    out = os.path.join(config.REVIEW_DIR, 'qa_r1fix.md')
    with open(out, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print('[qa_r1fix] PASS=%d FAIL=%d -> %s' % (n_pass, n_fail, out))


main()

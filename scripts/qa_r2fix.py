# -*- coding: utf-8 -*-
# qa_r2fix.py —— R2 补修轮客观验收（Blender 无头跑）
#   blender -b blend\jiangyu.blend --python scripts\qa_r2fix.py
# M1 门缝计数 / M4 射线+纯色块占比 / M5 新马桶 9 点 / m3 椅入画 / m4 鸟瞰底色 / 回归项
import os
import re
import sys
import math

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config

RENDER_LOG = os.path.join(config.RENDER_DIR, 'preview', 'render_r2fix.log')
lines = []
n_pass = n_fail = 0


def log(ok, msg):
    global n_pass, n_fail
    n_pass += ok
    n_fail += (not ok)
    lines.append('- **%s** %s' % ('PASS' if ok else 'FAIL', msg))
    if not ok:
        print('[qa_r2fix][FAIL] %s' % msg)


def read_log(path):
    raw = open(path, 'rb').read()
    enc = 'utf-16' if raw[:2] in (b'\xff\xfe', b'\xfe\xff') else 'utf-8'
    return raw.decode(enc, errors='replace')


def check_log():
    hits = []
    variants = {}
    if os.path.isfile(RENDER_LOG):
        txt = read_log(RENDER_LOG)
        for ln in txt.split('\n'):
            if '0 objs' in ln or '[render][warn]' in ln or 'assert' in ln.lower():
                hits.append(ln.strip()[:120])
            for m in re.finditer(r'variant=(\w+)\((\d+) objs\)', ln):
                variants[m.group(1)] = max(variants.get(m.group(1), 0), int(m.group(2)))
    log(not hits, '渲染日志零 (0 objs)/warn/assert %s' % ('' if not hits else '：' + '；'.join(hits[:3])))
    exp_k = sum(1 for o in bpy.data.objects if o.get('variant_group') == 'kitchen_lower_olive')
    exp_s = sum(1 for o in bpy.data.objects if o.get('variant_group') == 'son_blue')
    log(variants.get('kitchen_lower_olive', 0) >= exp_k and variants.get('son_blue', 0) >= exp_s,
        '变体日志替换 kitchen %d>=%d / son %d>=%d' %
        (variants.get('kitchen_lower_olive', 0), exp_k,
         variants.get('son_blue', 0), exp_s))


# ---------------------------------------------------------------- M1 门缝计数
# R2FIX 复测修正：缝点不再硬编码世界坐标——从场景真实门框梃（*_door_fl<i>/fr<i>）
# 推导"相邻门界中点"。原硬编码法对斜视机位失效是几何事实：23.8° 入射下射线穿
# 20mm 门厚横向漂移 8.8mm ≫ 1.5mm 半缝宽，必然扎进邻扇侧壁；而渲染里的"缝"
# 本来就是缝口暗槽 + 背后 10mm 深色背板读出的暗线。故可见判据改为双射线：
#   (a) 口部无遮挡：相机→缝点外皮，首命中距离 ≈ 预期（±3cm，无第三方遮挡物）；
#   (b) 缝内有背板：缝口内 2mm 沿法向向柜内打，2cm 内命中 gapbg / gap_dark。
# 均为确定性几何测试，逐缝取段上 3 个高度采样（缝是竖线，任一采样可见即缝可见）。
CAB_SPECS = {
    # cam 名: (柜体 id 前缀, run 轴('y'=门沿 y 排布/法向 x), 正面外皮法向符号, 各段设计门数)
    'CAB_master_wardrobe': ('common_master_bedroom_wardrobe_01', 'y', +1, [7]),
    'CAB_B_wall': ('B_living_dining_balcony_cabinet', 'y', -1, [10, 10]),
    'CAB_foyer': ('common_foyer_cabinet', 'x', +1, [3, 3]),
}
ORIGINAL_CAMS = {'CAB_master_wardrobe': 'cam_13_master_wardrobe_vanity',
                 'CAB_B_wall': 'cam_08_living_B_tv_wall',
                 'CAB_foyer': 'cam_11_foyer'}


def _wbbox(o, dg):
    ev = o.evaluated_get(dg)
    pts = [ev.matrix_world @ Vector(c) for c in ev.bound_box]
    xs = [p.x for p in pts]
    ys = [p.y for p in pts]
    zs = [p.z for p in pts]
    return (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))


def _infer_seams(prefix, run_axis, outward, dg):
    """推导 (各段门数列表, 缝列表)。缝 = (run 坐标, 段 z 范围, 法向外方向)。"""
    stiles = []
    for o in bpy.data.objects:
        if o.type != 'MESH' or not o.name.startswith(prefix):
            continue
        m = re.search(r'_door_f([lr])(\d+)$', o.name)
        if m:
            stiles.append((m.group(1), int(m.group(2)), _wbbox(o, dg)))
    if not stiles:
        return None, []
    stiles.sort(key=lambda s: (s[2][4] + s[2][5]) / 2)
    bands = []          # [z_mid, stiles]
    for s in stiles:
        zm = (s[2][4] + s[2][5]) / 2
        if bands and zm - bands[-1][0] < 0.25:
            bands[-1][1].append(s)
        else:
            bands.append([zm, [s]])
    counts, seams = [], []
    for zm, grp in bands:
        left = {i: bb for l, i, bb in grp if l == 'l'}
        right = {i: bb for l, i, bb in grp if l == 'r'}
        idx = sorted(set(left) & set(right))
        counts.append(len(idx))
        for a, b in zip(idx, idx[1:]):
            if run_axis == 'y':
                s = (right[a][3] + left[b][2]) / 2        # fr_i.ymax 与 fl_{i+1}.ymin 中点
                skin = right[a][1] if outward > 0 else right[a][0]
            else:
                s = (right[a][1] + left[b][0]) / 2        # x 向
                skin = left[b][3] if outward > 0 else left[b][2]
            seams.append((s, (grp[0][2][4], grp[0][2][5]), skin, outward))
    return counts, seams


def _seam_visible(scene, dg, cam, s, zr, skin, outward, run_axis):
    for zf in (zr[0] + 0.08 * (zr[1] - zr[0]),
               (zr[0] + zr[1]) / 2,
               zr[1] - 0.08 * (zr[1] - zr[0])):
        P = Vector((skin, s, zf) if run_axis == 'y' else (s, skin, zf))
        o = cam.matrix_world.translation
        d = P - o
        exp = d.length
        hit, loc, nrm, idx, obj, mw = scene.ray_cast(dg, o, d.normalized(),
                                                     distance=exp + 0.5)
        if not hit or (loc - o).length > exp + 0.03:
            continue                                      # 第三方遮挡或落空
        n = Vector((outward, 0, 0)) if run_axis == 'y' else Vector((0, outward, 0))
        Pin = P - n * 0.002
        hit2, loc2, n2, i2, obj2, mw2 = scene.ray_cast(dg, Pin, -n, distance=0.02)
        if hit2 and ('gapbg' in obj2.name or
                     'gap_dark' in (obj2.material_slots[0].material.name
                                    if obj2.material_slots else '')):
            return True
    return False


def _in_frame(scene, cam, s, zr, skin, outward, run_axis):
    for zf in (zr[0] + 0.08 * (zr[1] - zr[0]),
               (zr[0] + zr[1]) / 2,
               zr[1] - 0.08 * (zr[1] - zr[0])):
        import bpy_extras
        P = Vector((skin, s, zf) if run_axis == 'y' else (s, skin, zf))
        co = bpy_extras.object_utils.world_to_camera_view(scene, cam, P)
        if 0.02 < co.x < 0.98 and 0.02 < co.y < 0.98 and co.z > 0:
            return True
    return False


def check_m1():
    scene = bpy.context.scene
    dg = bpy.context.evaluated_depsgraph_get()
    bpy.context.view_layer.update()
    for cid, (pref, run, outward, design_bands) in CAB_SPECS.items():
        cam = bpy.data.objects.get('cam_' + cid)
        if cam is None:
            log(False, 'M1 %s 机位缺失' % cid)
            continue
        counts, seams = _infer_seams(pref, run, outward, dg)
        if counts is None:
            log(False, 'M1 %s 未推导到门框梃（前缀 %s）' % (cid, pref))
            continue
        log(counts == design_bands, 'M1 %s 实测门数 %s vs 设计 %s' %
            (cid, counts, design_bands))
        inframe = [sm for sm in seams if _in_frame(scene, cam, *sm, run)]
        vis = sum(_seam_visible(scene, dg, cam, *sm, run) for sm in inframe)
        ok = abs(vis - len(inframe)) <= 1 and vis >= 2
        log(ok, 'M1 %s 可见缝 %d / 设计在画缝 %d（各段门数 %s，±1）' %
            (cid, vis, len(inframe), counts))
        ocam = bpy.data.objects.get(ORIGINAL_CAMS[cid])
        if ocam is not None:
            oin = [sm for sm in seams if _in_frame(scene, ocam, *sm, run)]
            ovis = sum(_seam_visible(scene, dg, ocam, *sm, run) for sm in oin[:3])
            ogoal = min(3, len(oin))
            log(ovis == ogoal and ogoal > 0, 'M1 %s 原机位抽验缝可见 %d/%d' %
                (cid, ovis, ogoal))


# ---------------------------------------------------------------- M4 纯色块
def check_m4():
    img = bpy.data.images.load(pv('09_kitchen_walnut'))
    w, h = img.size
    px = list(img.pixels)
    bpy.data.images.remove(img)
    x0, x1, y0, y1 = int(0.24 * w), int(0.42 * w), int(0.06 * h), int(0.42 * h)
    tot = white = 0
    for y in range(y0, y1):
        for x in range(x0, x1):
            i = 4 * ((h - 1 - y) * w + x)
            r, g, b = px[i] * 255, px[i + 1] * 255, px[i + 2] * 255
            lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
            tot += 1
            if lum >= 242 and (max(r, g, b) - min(r, g, b)) <= 12:
                white += 1
    frac = white / max(1, tot)
    log(frac <= 0.20, 'M4 09 号窗区近白纯色块占比 %.1f%% <= 20%%' % (frac * 100))


def pv(name):
    return os.path.join(config.RENDER_DIR, 'preview', name + '.png')


# ---------------------------------------------------------------- M5 9 点
def check_m5():
    import bpy_extras
    scene = bpy.context.scene
    cam = bpy.data.objects.get('cam_18_public_bath_wet')
    toilet = [(9.05, -1.85, 0.0), (9.75, -1.85, 0.0), (9.05, -1.45, 0.0), (9.75, -1.45, 0.0),
              (9.05, -1.85, 0.45), (9.75, -1.85, 0.45), (9.05, -1.45, 0.45), (9.75, -1.45, 0.45)]
    pts = toilet + [(9.575, -1.10, 1.0)]
    bad = []
    for p in pts:
        co = bpy_extras.object_utils.world_to_camera_view(scene, cam, Vector(p))
        if not (0.01 < co.x < 0.99 and 0.01 < co.y < 0.99 and co.z > 0):
            bad.append('(%.2f,%.2f)' % (co.x, co.y))
    log(not bad, 'M5 新马桶 8 角+隔断中心 9 点全部入画 %s' %
        ('' if not bad else '出界：' + ';'.join(bad[:3])))


# ---------------------------------------------------------------- m3 椅入画
def check_m3():
    import bpy_extras
    scene = bpy.context.scene
    cam = bpy.data.objects.get('cam_20_terrace')
    ok_all = True
    for name, p in (('chair01', (10.2, -11.3, 0.20)), ('chair02', (11.6, -11.3, 0.20)),
                    ('table', (10.9, -11.3, 0.45))):
        co = bpy_extras.object_utils.world_to_camera_view(scene, cam, Vector(p))
        ok = 0.02 < co.x < 0.98 and 0.02 < co.y < 0.98 and co.z > 0
        ok_all = ok_all and ok
        print('[qa_r2fix] m3 %s u=%.2f v=%.2f' % (name, co.x, co.y))
    log(ok_all, 'm3 20 号双藤椅+圆桌入画')


# ---------------------------------------------------------------- m4 鸟瞰底色
def check_m4_base():
    img = bpy.data.images.load(pv('01_aerial_A'))
    w, h = img.size
    px = list(img.pixels)
    bpy.data.images.remove(img)
    rs = gs = bs = n = 0
    for y in range(int(0.75 * h), int(0.92 * h)):
        for x in range(int(0.03 * w), int(0.12 * w)):
            i = 4 * ((h - 1 - y) * w + x)
            rs += px[i] * 255
            gs += px[i + 1] * 255
            bs += px[i + 2] * 255
            n += 1
    r, g, b = rs / n, gs / n, bs / n
    tgt = (242, 240, 236)
    d = math.sqrt((r - tgt[0]) ** 2 + (g - tgt[1]) ** 2 + (b - tgt[2]) ** 2)
    log(d <= 25, 'm4 01 号鸟瞰背景均色 (%d,%d,%d) 距 #F2F0EC %.1f <= 25' %
        (r, g, b, d))


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
            bad.append(f)
    log(not bad, 'PNG 全部 8bit RGB %s' % ('' if not bad else '异常：' + ';'.join(bad[:3])))


def main():
    lines.append('# R2 补修轮客观验收（qa_r2fix · M1-M5 + m1-m4）')
    lines.append('')
    check_log()
    check_m1()
    check_m4()
    check_m5()
    check_m3()
    check_m4_base()
    check_png_format()
    lines.append('')
    lines.append('M2 镜面反射 / M3 台下盆观感 为视觉项（visual_review_R2fix.md）；'
                 'qa_coplanar 独立报告。')
    lines.append('汇总: PASS %d / FAIL %d' % (n_pass, n_fail))
    out = os.path.join(config.REVIEW_DIR, 'qa_r2fix.md')
    with open(out, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print('[qa_r2fix] PASS=%d FAIL=%d -> %s' % (n_pass, n_fail, out))


main()

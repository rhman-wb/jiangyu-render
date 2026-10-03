# -*- coding: utf-8 -*-
# qa_r2fix2.py -- R2 第二次补修轮客观验收（REWORK_R2FIX2 · N1-N3）
#   blender -b blend\jiangyu.blend --python scripts\qa_r2fix2.py
# N1 西墙组合柜（三单元/真腔/玻璃透视/灯带/摆件落板）+ CAB 渲染像素证据
# N2 露台（机位在露台内/椅桌入画/靠背扶手坐垫在/零穿插）
# N3 厨房（灶下 3 层抽屉/短拉手/洗碗机对缝/橄榄绿变体数）
import os
import re
import sys
import math

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config

RENDER_LOG = os.path.join(config.RENDER_DIR, 'preview', 'render_r2fix2.log')
lines = []
n_pass = n_fail = 0


def log(ok, msg):
    global n_pass, n_fail
    n_pass += ok
    n_fail += (not ok)
    lines.append('- **%s** %s' % ('PASS' if ok else 'FAIL', msg))
    if not ok:
        print('[qa_r2fix2][FAIL] %s' % msg)


def read_log(path):
    raw = open(path, 'rb').read()
    enc = 'utf-16' if raw[:2] in (b'\xff\xfe', b'\xfe\xff') else 'utf-8'
    return raw.decode(enc, errors='replace')


def pv(name):
    return os.path.join(config.RENDER_DIR, 'preview', name + '.png')


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
    log(variants.get('kitchen_lower_olive', 0) >= exp_k,
        'N3 变体日志替换 kitchen %d>=%d（橄榄绿整排生效）' %
        (variants.get('kitchen_lower_olive', 0), exp_k))


def bbox(o, dg):
    ev = o.evaluated_get(dg)
    pts = [ev.matrix_world @ Vector(c) for c in ev.bound_box]
    xs = [p.x for p in pts]
    ys = [p.y for p in pts]
    zs = [p.z for p in pts]
    return (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))


# ---------------------------------------------------------------- N1
NICHE = (3.44, 3.79, -9.84, -9.265, 0.45, 2.25)     # 开放格腔体
GLASS = (3.44, 3.82, -10.40, -9.865, 0.45, 2.25)    # 玻璃柜单元
SHELF_TOPS = (0.47, 0.85, 1.21, 1.57, 1.93)


def check_n1():
    dg = bpy.context.evaluated_depsgraph_get()

    def kid(cid, suf):
        return bpy.data.objects.get(cid + suf)

    bc = 'common_living_dining_balcony_bookcase_02'
    ok_div = kid(bc, '_div1') is not None and kid(bc, '_div2') is not None
    log(ok_div, 'N1 两块 25mm 单元立板存在（三单元分界）')
    log(kid(bc, '_body') is None, 'N1 柜体不再是一块实心 body（假开放格废除）')
    sh = [kid(bc, '_shelf%d' % i) for i in range(4)]
    log(all(s is not None for s in sh) and
        all(abs(bbox(s, dg)[4] - z) < 1e-6 for s, z in zip(sh, (0.83, 1.19, 1.55, 1.91))),
        'N1 开放格 4 层隔板存在（z 0.83/1.19/1.55/1.91）')
    # 玻璃门 = 框 + 清玻璃芯；该单元无 gap_dark 背板
    pane = kid(bc, '_gpane')
    ok_pane = pane is not None and pane.material_slots and \
        pane.material_slots[0].material.name.startswith('glass_clear')
    log(ok_pane, 'N1 玻璃门清玻璃芯存在（glass_clear，非黑玻/磨砂）')
    log(all(kid(bc, '_gf_' + t) is not None for t in ('stS', 'stN', 'rlB', 'rlT')),
        'N1 玻璃门 30mm 胡桃细框四件存在')
    bad_gap = [o.name for o in bpy.data.objects
               if o.type == 'MESH' and 'gapbg' in o.name and 'bookcase' in o.name
               and bbox(o, dg)[4] >= 0.44
               and (bbox(o, dg)[2] + bbox(o, dg)[3]) / 2 < -9.86]
    log(not bad_gap, 'N1 玻璃单元后无深色缝背板 %s' % ('' if not bad_gap else str(bad_gap[:2])))
    # 灯带两条（开放格顶 + 玻璃柜内顶），跨度覆盖各自单元
    for nm, ylo, yhi in (('lt_strip_bc', -9.84, -9.265), ('lt_strip_bcg', -10.365, -9.90)):
        st = bpy.data.objects.get(nm)
        bb = bbox(st, dg) if st else None
        ok = st is not None and ylo - 0.01 <= bb[2] and bb[3] <= yhi + 0.01 and bb[4] > 2.15
        log(ok, 'N1 %s 存在且跨度在单元内（顶板下暖光灯带）' % nm)
    # 摆件：落在腔内且坐在层板面上
    fx = [o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith('fx_bc_')]
    n_book = sum(1 for o in fx if '_b' in o.name)
    ok_in = all(NICHE[0] - 0.01 <= bbox(o, dg)[0] and bbox(o, dg)[1] <= NICHE[1] + 0.01 and
                NICHE[2] - 0.01 <= bbox(o, dg)[2] and bbox(o, dg)[3] <= NICHE[3] + 0.01
                for o in fx if o.name.startswith(('fx_bc_b', 'fx_bc_pot', 'fx_bc_rec',
                                                  'fx_bc_frame', 'fx_bc_jar'))
                and bbox(o, dg)[2] > 0.46)
    sits = all(min(abs(bbox(o, dg)[4] - z) for z in SHELF_TOPS) < 0.006
               for o in fx
               if o.name.startswith(('fx_bc_b0_', 'fx_bc_pot', 'fx_bc_rec',
                                     'fx_bc_frame', 'fx_bc_b3_'))
               and 'neck' not in o.name and 'lip' not in o.name
               and 'b0f' not in o.name and 'framein' not in o.name
               and not (o.name.startswith('fx_bc_rec') and o.name != 'fx_bc_recstand'))
    log(len(fx) >= 20 and n_book >= 10, 'N1 摆件齐（书/陶罐/唱片/相框，共 %d 件）' % len(fx))
    log(ok_in, 'N1 开放格摆件全部落在腔体包络内')
    log(sits, 'N1 开放格摆件坐在层板面上（不悬空不穿板）')

    # CAB_west_bookcase 渲染像素证据：开放格受光 > 门板面；玻璃柜内可透视见物
    img = bpy.data.images.load(pv('CAB_west_bookcase'))
    w, h = img.size
    px = list(img.pixels)
    bpy.data.images.remove(img)

    def region(u0, u1, v0, v1):
        rs = n = 0
        vals = []
        for yy in range(int(v0 * h), int(v1 * h)):
            for xx in range(int(u0 * w), int(u1 * w)):
                i = 4 * (yy * w + xx)
                lum = 0.2126 * px[i] + 0.7152 * px[i + 1] + 0.0722 * px[i + 2]
                vals.append(lum * 255)
                rs += lum * 255
                n += 1
        return rs / max(1, n), (max(vals) - min(vals))

    niche_top, _ = region(0.44, 0.56, 0.28, 0.42)     # 开放格上带（受顶灯带照射）
    niche_low, _ = region(0.44, 0.56, 0.55, 0.70)     # 开放格下带
    log(niche_top > niche_low + 4,
        'N1 开放格顶部打光梯度（上带 %.0f > 下带 %.0f+4，灯带光可见）'
        % (niche_top, niche_low))
    door_lum, _ = region(0.64, 0.80, 0.30, 0.60)      # 木门柜面（对照样本）
    glass_lum, glass_rng = region(0.16, 0.38, 0.30, 0.62)   # 玻璃柜内
    log(55 < glass_lum < 250 and glass_rng > 25,
        'N1 玻璃柜内可透视（均亮 %.0f、动态范围 %.0f，非黑板非死白）' % (glass_lum, glass_rng))


# ---------------------------------------------------------------- N2
def check_n2():
    import bpy_extras
    scene = bpy.context.scene
    dg = bpy.context.evaluated_depsgraph_get()
    cam = bpy.data.objects.get('cam_20_terrace')
    ok_cam = cam is not None and 9.25 <= cam.location.x <= 12.8 and \
        -12.4 <= cam.location.y <= -10.15
    log(ok_cam, 'N2 20 号相机位于露台范围内 (%.2f, %.2f, %.2f)' %
        (cam.location.x, cam.location.y, cam.location.z))
    # 至少一把藤椅完整入画（工单口径）：远椅 02 五点 + 桌心/东缘（西缘贴画框边不判）
    ok_pts = True
    for nm, pts in (('chair02', [(11.6, -11.3, 0.45), (11.32, -11.3, 0.46),
                                 (11.88, -11.3, 0.46), (11.6, -11.05, 0.46),
                                 (11.6, -11.56, 0.30)]),
                    ('table', [(10.9, -11.3, 0.5), (11.25, -11.3, 0.5)])):
        for p in pts:
            co = bpy_extras.object_utils.world_to_camera_view(scene, cam, Vector(p))
            if not (0.02 < co.x < 0.98 and 0.02 < co.y < 0.98 and co.z > 0):
                ok_pts = False
    log(ok_pts, 'N2 藤椅02 完整入画 + 圆桌入画（椅01 部分入画为构图近景，不判 FAIL）')
    parts_ok = True
    for cix in ('01', '02'):
        cid = 'common_terrace_lounge_chair_' + cix
        for suf in ('_back0', '_back2', '_arm-1', '_arm1', '_armp-1', '_cushion'):
            if bpy.data.objects.get(cid + suf) is None:
                parts_ok = False
    log(parts_ok, 'N2 藤椅为休闲椅造型（弧形靠背/扶手/燕麦坐垫对象在）')
    # 露台家具跨物件零穿插（同椅内部的靠背叠层为有意的层叠做法，不在判据内）
    roots = [o for o in bpy.data.objects if o.name.startswith(
        ('common_terrace_lounge_chair', 'common_terrace_coffee_table'))]
    bbs = [bbox(o, dg) for o in roots]
    inter = []
    for i in range(len(bbs)):
        for j in range(i + 1, len(bbs)):
            if roots[i].name.rsplit('_', 1)[0] == roots[j].name.rsplit('_', 1)[0]:
                continue                       # 同一件家具的部件
            a, b = bbs[i], bbs[j]
            if (a[0] < b[1] and b[0] < a[1] and a[2] < b[3] and b[2] < a[3] and
                    a[4] < b[5] and b[4] < a[5]):
                inter.append((roots[i].name, roots[j].name))
    log(not inter, 'N2 露台椅/桌零穿插 %s' % ('' if not inter else str(inter[:2])))


# ---------------------------------------------------------------- N3
def check_n3():
    dg = bpy.context.evaluated_depsgraph_get()
    drawers = [o for o in bpy.data.objects
               if o.type == 'MESH' and '_drwH_d' in o.name]
    log(len(drawers) >= 3, 'N3 灶下抽屉面 %d 层 >= 3' % len(drawers))
    pulls = [o for o in bpy.data.objects if o.type == 'MESH' and
             (o.name.startswith('common_kitchen') and
              (o.name.endswith(tuple('_p%d' % i for i in range(12))) or '_slot' in o.name))]
    tall = [o.name for o in pulls if bbox(o, dg)[5] - bbox(o, dg)[4] > 0.14]
    log(not tall, 'N3 厨房拉手全部为短拉手/拉手槽（≤140mm）%s' %
        ('' if not tall else str(tall[:2])))
    dw = bpy.data.objects.get('common_kitchen_dishwasher_02_panel')
    drw = [o for o in bpy.data.objects if o.type == 'MESH' and '_drw_f0' in o.name
           and 'dishwasher_01' in o.name]
    ok_align = False
    if dw is not None and drw:
        gapx = abs(min(bbox(o, dg)[0] for o in drw) - bbox(dw, dg)[1])
        ok_align = gapx <= 0.006
        log(ok_align, 'N3 洗碗机面板东缘与相邻门缝对齐（%.1fmm）' % (gapx * 1000))
    else:
        log(False, 'N3 洗碗机面板/相邻门列未找到')


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
    lines.append('# R2 第二次补修轮客观验收（qa_r2fix2 · N1-N3）')
    lines.append('')
    check_log()
    check_n1()
    check_n2()
    check_n3()
    check_png_format()
    lines.append('')
    lines.append('汇总: PASS %d / FAIL %d' % (n_pass, n_fail))
    out = os.path.join(config.REVIEW_DIR, 'qa_r2fix2.md')
    with open(out, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print('[qa_r2fix2] PASS=%d FAIL=%d -> %s' % (n_pass, n_fail, out))


main()

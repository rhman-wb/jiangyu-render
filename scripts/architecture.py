# -*- coding: utf-8 -*-
# architecture.py —— 硬装白模：地面、墙体（分段盒体）、窗框玻璃、门扇、吊顶、飘窗、露台栏杆
# 依据：CLAUDE.md 第 3/4/7/11 章 + data/layout.json（只读）。
# 自定细节见 review/decisions_log.md。
import math
import bpy

import config
import util

CEIL = config.CEIL_H  # 2.85

# A 组外墙：加厚 0.14->0.20，只向外侧扩（内面钉在中心线 ∓0.07）。id -> 外法向 (nx, ny)
EXT_WALLS = {
    'W01': (0, 1), 'W02': (0, 1), 'W05': (0, 1), 'W06': (0, 1),
    'W10': (1, 0), 'W11': (-1, 0), 'W16': (1, 0), 'W17': (0, -1),
    'W18': (0, -1), 'W21': (-1, 0), 'W23': (0, -1), 'W24': (-1, 0),
    'W25': (1, 0),
}

# 地板裁剪（decisions_log D-007）：living 优先；corridor 为 L 形避免空洞
FLOOR_XMAX_TRIM = {'foyer': 3.35, 'elevator_hall': 3.35}
CORRIDOR_SPLIT = [((9.25, -5.25), (10.75, -3.95)),   # 南段（让出与 living 的重叠带）
                  ((9.0, -3.95), (10.75, -2.35))]    # 北段
SKIP_FLOORS = {'parents_bay_window'}  # 飘窗台面由 build_bay 建 0~0.45 台体

MULLION_MAX = 1.5  # 窗宽超过此值加分中梃（等分）


# ================================================================ 墙体几何
def wall_geo(w, walls):
    """返回墙的几何参数 dict：axis, u0e/u1e(延伸后跨), v(中心线), v_center(盒体中心), t, ext"""
    axis = w['axis']
    v = w['y'] if axis == 'x' else w['x']
    n = EXT_WALLS.get(w['id'])
    t = config.WALL_T_EXT if n else config.WALL_T
    nv = (n[1] if axis == 'x' else n[0]) if n else 0
    v_center = v + 0.03 * nv if n else v

    def extend_end(u_end, direction):
        """端点落在垂直墙中心线上时，延伸到对方远面（A 组外侧 0.13 / 其余 0.07）。"""
        wv = w['y'] if axis == 'x' else w['x']  # 本墙固定坐标（在对方墙跨度轴上的位置）
        for o in walls:
            if o is w or o['axis'] == axis:
                continue
            ov = o['y'] if o['axis'] == 'x' else o['x']
            if abs(ov - u_end) > 0.02:
                continue
            lo, hi = sorted((o['start'], o['end']))
            if not (lo - 0.06 <= wv <= hi + 0.06):
                continue
            n_o = EXT_WALLS.get(o['id'])
            if n_o:
                n_ou = n_o[0] if axis == 'x' else n_o[1]
                ext = 0.13 if n_ou * direction > 0 else 0.07
            else:
                ext = 0.07
            return u_end + direction * ext
        return u_end

    return {
        'id': w['id'], 'axis': axis, 'v': v, 'v_center': v_center, 't': t, 'ext': bool(n),
        'u0e': extend_end(w['start'], -1),
        'u1e': extend_end(w['end'], +1),
    }


def normalize_openings(w):
    """洞口裁剪到墙跨内、排序；重叠/近距合并（冲突记 WARN 由调用方收集）。"""
    a0, a1 = sorted((w['start'], w['end']))
    ops = []
    for o in w.get('openings', []):
        s, e = sorted((o['start'], o['end']))
        s, e = max(s, a0), min(e, a1)
        if e - s <= 0.005:
            continue
        ops.append(dict(o, start=s, end=e))
    ops.sort(key=lambda o: o['start'])
    merged = []
    for o in ops:
        if merged and o['start'] - merged[-1]['end'] < 0.02:
            m = merged[-1]
            m['end'] = max(m['end'], o['end'])
            if m['type'] != o['type']:
                m['_warn'] = 'conflicting overlap merged: %s+%s' % (m['type'], o['type'])
        else:
            merged.append(o)
    return merged


def opening_bands(op):
    """洞口处的竖向墙带 (z0, z1) 列表；full_opening 无。"""
    typ = op['type']
    head = op.get('head', CEIL)
    if typ in ('door', 'glass_door'):
        return [(head, CEIL)]
    if typ == 'window':
        return [(0.0, op['sill']), (head, CEIL)]
    return []  # full_opening


def seg_box(g, ua, ub, z0, z1):
    """墙段 -> 世界坐标盒 (bmin, bmax)。"""
    if g['axis'] == 'x':
        return (ua, g['v_center'] - g['t'] / 2, z0), (ub, g['v_center'] + g['t'] / 2, z1)
    return (g['v_center'] - g['t'] / 2, ua, z0), (g['v_center'] + g['t'] / 2, ub, z1)


def build_walls(layout, mats, coll):
    walls = layout['walls']
    warns = []
    for w in walls:
        g = wall_geo(w, walls)
        ops = normalize_openings(w)
        segs = []
        cur = g['u0e']
        for op in ops:
            if op['start'] > cur + 1e-4:
                segs.append((cur, op['start'], 0.0, CEIL))
            for z0, z1 in opening_bands(op):
                segs.append((op['start'], op['end'], z0, z1))
            cur = op['end']
            if '_warn' in op:
                warns.append('%s: %s' % (w['id'], op['_warn']))
        if cur < g['u1e'] - 1e-4:
            segs.append((cur, g['u1e'], 0.0, CEIL))
        for i, (ua, ub, z0, z1) in enumerate(segs):
            bmin, bmax = seg_box(g, ua, ub, z0, z1)
            util.make_box('%s_s%02d' % (w['id'], i), bmin, bmax,
                          coll=coll, mat=mats['white'])
    return warns


# ================================================================ 地面
def build_floors(layout, mats, coll):
    for f in layout['floors']:
        fid = f['id']
        if fid in SKIP_FLOORS:
            continue
        (x0, y0), (x1, y1) = f['rect_min'], f['rect_max']
        x1 = FLOOR_XMAX_TRIM.get(fid, x1)
        rects = CORRIDOR_SPLIT if fid == 'corridor' else [((x0, y0), (x1, y1))]
        for j, ((rx0, ry0), (rx1, ry1)) in enumerate(rects):
            name = 'floor_%s' % fid if len(rects) == 1 else 'floor_%s_%d' % (fid, j)
            util.make_box(name, (rx0, ry0, -0.02), (rx1, ry1, 0.0),
                          coll=coll, mat=mats['white'])


# ================================================================ 窗
def build_windows(layout, mats, coll):
    """window 洞口：四周框 + 等分中梃 + 玻璃（玻璃关阴影，规格 6.3）。"""
    for w in layout['walls']:
        g = wall_geo(w, layout['walls'])
        for k, op in enumerate([o for o in normalize_openings(w) if o['type'] == 'window']):
            a, b = op['start'], op['end']
            s, h = op['sill'], op['head']
            fw, fd = 0.06, g['t'] * 0.8
            c = g['v_center']
            parts = [
                ('bot', (a, s), (b, s + fw)),
                ('top', (a, h - fw), (b, h)),
                ('lft', (a, s), (a + fw, h)),
                ('rgt', (b - fw, s), (b, h)),
            ]
            for tag, (u0, z0), (u1, z1) in parts:
                if g['axis'] == 'x':
                    bmin, bmax = (u0, c - fd / 2, z0), (u1, c + fd / 2, z1)
                else:
                    bmin, bmax = (c - fd / 2, u0, z0), (c + fd / 2, u1, z1)
                util.make_box('win_%s_%d%s' % (w['id'], k, tag), bmin, bmax,
                              coll=coll, mat=mats['white'])
            # 中梃（等分，间距 <= MULLION_MAX）
            npan = max(1, math.ceil((b - a) / MULLION_MAX - 1e-6))
            for m in range(1, npan):
                u = a + (b - a) * m / npan
                if g['axis'] == 'x':
                    bmin, bmax = (u - 0.025, c - fd / 2, s + fw), (u + 0.025, c + fd / 2, h - fw)
                else:
                    bmin, bmax = (c - fd / 2, u - 0.025, s + fw), (c + fd / 2, u + 0.025, h - fw)
                util.make_box('win_%s_%dmul%d' % (w['id'], k, m), bmin, bmax,
                              coll=coll, mat=mats['white'])
            # 玻璃
            if g['axis'] == 'x':
                bmin, bmax = (a + fw, c - 0.005, s + fw), (b - fw, c + 0.005, h - fw)
            else:
                bmin, bmax = (c - 0.005, a + fw, s + fw), (c + 0.005, b - fw, h - fw)
            gl = util.make_box('win_%s_%dglass' % (w['id'], k), bmin, bmax,
                               coll=coll, mat=mats['glass'])
            if gl:
                gl.visible_shadow = False


# ================================================================ 门
def _panel_frame(name_prefix, g, ua, ub, z0, z1, mats, coll, glass=False):
    """一块门扇：边框梃 + 芯板（玻璃或实心）。"""
    st, sd = 0.045, 0.035  # 梃宽 / 扇厚
    c = g['v_center']

    def box(tag, u0, u1, zz0, zz1, mat):
        if g['axis'] == 'x':
            bmin, bmax = (u0, c - sd / 2, zz0), (u1, c + sd / 2, zz1)
        else:
            bmin, bmax = (c - sd / 2, u0, zz0), (c + sd / 2, u1, zz1)
        util.make_box('%s%s' % (name_prefix, tag), bmin, bmax, coll=coll, mat=mat)

    box('_bot', ua, ub, z0, z0 + st, mats['white'])
    box('_top', ua, ub, z1 - st, z1, mats['white'])
    box('_lft', ua, ua + st, z0 + st, z1 - st, mats['white'])
    box('_rgt', ub - st, ub, z0 + st, z1 - st, mats['white'])
    if glass:
        box('_glass', ua + st, ub - st, z0 + st, z1 - st, mats['glass'])
        obj = bpy.data.objects.get('%s_glass' % name_prefix)
        if obj:
            obj.visible_shadow = False


def build_doors(layout, mats, coll):
    for w in layout['walls']:
        g = wall_geo(w, layout['walls'])
        for k, op in enumerate(normalize_openings(w)):
            typ, a, b = op['type'], op['start'], op['end']
            head = op.get('head', CEIL)
            if typ == 'door' and w['id'] == 'W12':
                pass  # 四联动门由 builtins.py 按 item（双轨道）建模
            elif typ == 'glass_door':
                # 开发商玻璃门（W15 两扇 / W17 三扇），关闭
                n = 2 if (b - a) < 1.5 else 3
                for i in range(n):
                    ua = a + (b - a) * i / n
                    ub = a + (b - a) * (i + 1) / n
                    _panel_frame('door_%s_%d' % (w['id'], i), g, ua + 0.015, ub - 0.015,
                                 0.05, head - 0.05, mats, coll, glass=True)
            elif typ == 'door':
                # 室内木门 / 入户门：门套（三边）+ 关闭门扇，白模
                fw = 0.04
                sd = 0.16  # 套深度，比墙厚每侧凸 1cm
                c = g['v_center']
                parts = [('lft', a - 0.01, a + fw - 0.01, 0.0, head + fw),
                         ('rgt', b - fw + 0.01, b + 0.01, 0.0, head + fw),
                         ('top', a - 0.01, b + 0.01, head, head + fw)]
                for tag, u0, u1, z0, z1 in parts:
                    if g['axis'] == 'x':
                        bmin, bmax = (u0, c - sd / 2, z0), (u1, c + sd / 2, z1)
                    else:
                        bmin, bmax = (c - sd / 2, u0, z0), (c + sd / 2, u1, z1)
                    util.make_box('door_%s_%d%s' % (w['id'], k, tag), bmin, bmax,
                                  coll=coll, mat=mats['white'])
                # 门扇（关），铰链在 start 端
                lw = (b - a) - 2 * fw
                if g['axis'] == 'x':
                    bmin, bmax = (a + fw, c - 0.022, 0.01), (a + fw + lw, c + 0.022, head - fw)
                else:
                    bmin, bmax = (c - 0.022, a + fw, 0.01), (c + 0.022, a + fw + lw, head - fw)
                util.make_box('door_%s_%dleaf' % (w['id'], k), bmin, bmax,
                              coll=coll, mat=mats['white'])
            # full_opening：无门扇


# ================================================================ 吊顶
def _cbox(name, bmin, bmax, coll, mat=None):
    return util.make_box(name, bmin, bmax, coll=coll, mat=mat)


def build_ceilings(layout, mats, coll):
    R = {f['id']: (tuple(f['rect_min']), tuple(f['rect_max'])) for f in layout['floors']}
    white = mats['white']

    # —— 客餐厅：周边吊 0.45 宽@2.60 + 双眼皮台阶@2.70 + 中央原顶 2.85（规格 4.3）
    (x0, y0), (x1, y1) = R['living_dining_balcony']
    i1, i2 = 0.45, 0.55  # 一级 / 二级内缩
    ring1 = [('S', (x0, y0), (x1, y0 + i1)), ('N', (x0, y1 - i1), (x1, y1)),
             ('W', (x0, y0 + i1), (x0 + i1, y1 - i1)), ('E', (x1 - i1, y0 + i1), (x1, y1 - i1))]
    for tag, (a, b), (c2, d) in ring1:
        _cbox('ceil_living_r1%s' % tag, (a, b, 2.60), (c2, d, 2.84), coll, white)
    ring2 = [('S', (x0, y0 + i1), (x1, y0 + i2)), ('N', (x0, y1 - i2), (x1, y1 - i1)),
             ('W', (x0 + i1, y0 + i2), (x0 + i2, y1 - i2)), ('E', (x1 - i2, y0 + i2), (x1 - i1, y1 - i2))]
    for tag, (a, b), (c2, d) in ring2:
        _cbox('ceil_living_r2%s' % tag, (a, b, 2.70), (c2, d, 2.84), coll, white)
    _cbox('ceil_living_slab', (x0, y0, 2.85), (x1, y1, 2.90), coll, white)
    # 中央空调出风口：电视墙(东)一侧边吊底面，2.4m x 0.1m 深色格栅（位置记 decisions_log）
    _cbox('ceil_living_ac_slot', (x1 - 0.275, -9.8, 2.585), (x1 - 0.175, -7.4, 2.602),
          coll, mats['dark'])

    # —— 卧室平顶 2.85 + 空调局部吊顶
    for rid in ('master_bedroom', 'parents_room', 'daughter_room', 'son_room', 'foyer'):
        (a, b), (c2, d) = R[rid]
        _cbox('ceil_%s_slab' % rid, (a, b, 2.85), (c2, d, 2.90), coll, white)
    _cbox('ceil_master_ac', (9.25, -6.25, 2.60), (9.85, -5.25, 2.84), coll, white)
    # 父母房：严格按 layout item ceiling_box（bbox 2.5~2.8）
    _cbox('ceil_parents_room_ac', (2.35, -7.4, 2.5), (3.3, -6.62, 2.8), coll, white)
    _cbox('ceil_daughter_ac', (7.95, -3.95, 2.60), (8.85, -3.35, 2.84), coll, white)
    _cbox('ceil_son_ac', (10.75, -3.35, 2.60), (11.35, -2.45, 2.84), coll, white)

    # —— 飘窗区顶板（父母房飘窗上方）
    (a, b), (c2, d) = R['parents_bay_window']
    _cbox('ceil_bay_slab', (a, b, 2.85), (c2, d, 2.90), coll, white)

    # —— 厨卫铝扣板 2.40 / 过道干区与电梯厅 2.60（整块填充，规格 4.3）
    fills = [('kitchen', 2.40), ('public_bath_wet', 2.40), ('master_bath', 2.40),
             ('corridor', 2.60), ('elevator_hall', 2.60)]
    for rid, z in fills:
        (a, b), (c2, d) = R[rid]
        _cbox('ceil_%s_fill' % rid, (a, b, z), (c2, d, 2.85), coll, white)
    # 露台无顶


# ================================================================ 飘窗与露台栏杆
def build_bay(layout, mats, coll):
    """父母房飘窗坐榻台面：0~0.45（顶面与 W23 窗台对齐）。"""
    util.make_box('bay_platform', (0.45, -10.55, 0.0), (3.05, -10.05, 0.45),
                  coll=coll, mat=mats['white'])


def build_terrace_railing(layout, mats, coll):
    """露台原样栏杆（规格 5.11 金属/玻璃）：高 1.05，南/东/西(南段) 三边。"""
    h_top, h_glass0, h_glass1 = 1.05, 0.15, 0.80
    edges = [('S', (9.25, -12.4), (12.8, -12.4)),
             ('E', (12.8, -12.4), (12.8, -10.15)),
             ('W', (9.25, -12.4), (9.25, -11.6))]
    for tag, (a, b), (c2, d) in edges:
        horizontal = abs(c2 - a) > abs(d - b)
        length = (c2 - a) if horizontal else (d - b)
        # 立柱（间距 <=1.3m）+ 顶扶手 + 玻璃栏板
        n = max(2, math.ceil(abs(length) / 1.3) + 1)
        for i in range(n):
            f = i / (n - 1)
            px, py = a + (c2 - a) * f, b + (d - b) * f
            if horizontal:
                bmin, bmax = (px - 0.025, py - 0.025, 0.0), (px + 0.025, py + 0.025, h_top)
            else:
                bmin, bmax = (px - 0.025, py - 0.025, 0.0), (px + 0.025, py + 0.025, h_top)
            util.make_box('rail_ter_%s_p%d' % (tag, i), bmin, bmax, coll=coll, mat=mats['white'])
        if horizontal:
            bmin, bmax = (min(a, c2), b - 0.035, h_top - 0.05), (max(a, c2), b + 0.035, h_top)
            gmin, gmax = (min(a, c2) + 0.05, b - 0.008, h_glass0), (max(a, c2) - 0.05, b + 0.008, h_glass1)
        else:
            bmin, bmax = (a - 0.035, min(b, d), h_top - 0.05), (a + 0.035, max(b, d), h_top)
            gmin, gmax = (a - 0.008, min(b, d) + 0.05, h_glass0), (a + 0.008, max(b, d) - 0.05, h_glass1)
        util.make_box('rail_ter_%s_top' % tag, bmin, bmax, coll=coll, mat=mats['white'])
        util.make_box('rail_ter_%s_glass' % tag, gmin, gmax, coll=coll, mat=mats['glass'])


# ================================================================ 入口
def build_all(mats, colls):
    layout = util.load_layout()
    common = colls['common']
    warns = []
    build_floors(layout, mats, common)
    warns += build_walls(layout, mats, common)
    build_windows(layout, mats, common)
    build_doors(layout, mats, common)
    build_ceilings(layout, mats, colls['ceilings'])
    build_bay(layout, mats, common)
    build_terrace_railing(layout, mats, common)
    return warns

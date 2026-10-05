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

# REWORK 2.2 / 2.4：贴砖墙角色（材质表 tile_* 对应）；未列出的墙 = wall_paint
# （与 materials.py WALL_TILE 表同键：W02/03/11/12 厨房、W09/10/14 主卫、W05/07/08 公卫）
WALL_TILE_ROLES = {
    'W02': 'wall_tile_kitchen', 'W03': 'wall_tile_kitchen',
    'W11': 'wall_tile_kitchen', 'W12': 'wall_tile_kitchen',
    'W09': 'wall_tile_bath_oat', 'W10': 'wall_tile_bath_oat', 'W14': 'wall_tile_bath_oat',
    'W05': 'wall_tile_bath_beige', 'W07': 'wall_tile_bath_beige', 'W08': 'wall_tile_bath_beige',
}

# REWORK 2.2：卫生间玻璃平开门（长虹玻璃）——(墙号, 洞口序号)
# W08 唯一 door = 公卫门；W14 第 2 个 door（10.9..11.7）= 主卫门（第 1 个是主卧木门）
FLUTED_DOORS = {('W08', 0), ('W14', 1)}


# ================================================================ 墙体几何
def _wall_thick(o):
    """墙厚（外墙 0.20 / 内墙 0.14）。"""
    return config.WALL_T_EXT if o['id'] in EXT_WALLS else config.WALL_T


def _wall_vcenter(o):
    """墙 B 的实际盒体中心（外墙向外偏 0.03，见 wall_geo）。"""
    n = EXT_WALLS.get(o['id'])
    if not n:
        return o['y'] if o['axis'] == 'x' else o['x']
    return (o['y'] + 0.03 * n[1]) if o['axis'] == 'x' else (o['x'] + 0.03 * n[0])


def _collinear_covers(b, junction, walls):
    """是否存在与 b 同轴同线、跨度覆盖交界点 junction 的墙（b 的直墙链延续）。"""
    vb = b['y'] if b['axis'] == 'x' else b['x']
    for o in walls:
        if o is b or o['axis'] != b['axis']:
            continue
        vo = o['y'] if o['axis'] == 'x' else o['x']
        if abs(vo - vb) > 0.02:
            continue
        lo, hi = sorted((o['start'], o['end']))
        if lo - 0.06 <= junction <= hi + 0.06:
            return True
    return False


def wall_geo(w, walls):
    """返回墙的几何参数 dict：axis, u0e/u1e(延伸后跨), v(中心线), v_center(盒体中心), t, ext"""
    axis = w['axis']
    v = w['y'] if axis == 'x' else w['x']
    n = EXT_WALLS.get(w['id'])
    t = config.WALL_T_EXT if n else config.WALL_T
    nv = (n[1] if axis == 'x' else n[0]) if n else 0
    v_center = v + 0.03 * nv if n else v

    def extend_end(u_end, direction):
        """REWORK_R1FIX2 F4：墙端规则（替换旧"一律延伸到对方远面"——旧规则把端面
        推到贯通墙室内面同一平面产生闪烁，且在直墙链节点伸进同线邻墙体）：
        1. 本墙端点处有同轴同线墙延续（直墙链相接，如 W01/W05/W06、W12/W13）
           -> 不延伸，端帽与邻墙端帽对接（法线相反，无重合面）；
        2. 垂直墙 B 在端点 ±(t_B/2+2cm) 内：
           - B 于交界处被同轴线墙延续（链节点），或 B 贯穿本墙（T 交）
             -> 对接 B 近面（端点落在 B 板内时回缩，回缩段由 B 实体覆盖）；
           - 真 L 角（互为端点、双方均无链延续，如 W14/W10）：厚度大者
             （同厚 id 小者）贯穿到 B 远面内 2mm 补全角部，另一侧对接近面。
        所有交接零体积重叠（贯穿者与对接者足迹相隔一个墙面）-> qa_coplanar 为空。"""
        wv = w['y'] if axis == 'x' else w['x']  # 本墙固定坐标（在对方墙跨度轴上的位置）
        # 1) 同轴延续
        for o in walls:
            if o is w or o['axis'] != axis:
                continue
            ov = o['y'] if o['axis'] == 'x' else o['x']
            if abs(ov - v) > 0.02:
                continue
            lo, hi = sorted((o['start'], o['end']))
            if lo - 0.06 <= u_end <= hi + 0.06:
                return u_end
        # 2) 垂直墙
        for o in walls:
            if o is w or o['axis'] == axis:
                continue
            ov = o['y'] if o['axis'] == 'x' else o['x']
            t_o = _wall_thick(o)
            if abs(ov - u_end) > t_o / 2 + 0.02:
                continue
            lo, hi = sorted((o['start'], o['end']))
            if not (lo - 0.06 <= wv <= hi + 0.06):
                continue
            c_o = _wall_vcenter(o)
            mutual = (abs(wv - lo) <= 0.06) or (abs(wv - hi) <= 0.06)
            # 对方在交界处有链延续（或 T 交）-> 对接近面
            if not mutual or _collinear_covers(o, wv, walls):
                return c_o - direction * (t_o / 2)
            t_w = config.WALL_T_EXT if n else config.WALL_T
            if (t_w, w['id']) > (t_o, o['id']):
                return c_o + direction * (t_o / 2 - 0.002)
            return c_o - direction * (t_o / 2)
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
            # REWORK role：贴砖墙按墙号给 tile 角色（apply_all 按面朝向双材质）
            tile = WALL_TILE_ROLES.get(w['id'])
            util.make_box('%s_s%02d' % (w['id'], i), bmin, bmax,
                          coll=coll, mat=mats['white'], role=tile or 'wall')
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
                          coll=coll, mat=mats['white'], role='floor')


# ================================================================ 窗
def build_windows(layout, mats, coll):
    """window 洞口：四周框 + 等分中梃 + 玻璃（玻璃关阴影，规格 6.3）。"""
    for w in layout['walls']:
        g = wall_geo(w, layout['walls'])
        for k, op in enumerate([o for o in normalize_openings(w) if o['type'] == 'window']):
            a, b = op['start'], op['end']
            s, h = op['sill'], op['head']
            # R2FIX 复测修正：框深原为墙厚 80%（居中）→ 框四周留 2cm 贯通空腔，
            # 室外补光束灌入腔内多次反弹成"光管"，从室内侧溢出把框体+窗头墙带
            # 打到 255，再经玻璃反射成白矩形（qa 采样框 30% 白）。框改为贯穿全墙厚。
            fw, fd = 0.06, g['t']
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
                              coll=coll, mat=mats['white'], role='win_frame')
            # 中梃（等分，间距 <= MULLION_MAX）
            npan = max(1, math.ceil((b - a) / MULLION_MAX - 1e-6))
            for m in range(1, npan):
                u = a + (b - a) * m / npan
                if g['axis'] == 'x':
                    bmin, bmax = (u - 0.025, c - fd / 2, s + fw), (u + 0.025, c + fd / 2, h - fw)
                else:
                    bmin, bmax = (c - fd / 2, u - 0.025, s + fw), (c + fd / 2, u + 0.025, h - fw)
                util.make_box('win_%s_%dmul%d' % (w['id'], k, m), bmin, bmax,
                              coll=coll, mat=mats['white'], role='win_frame')
            # 玻璃
            if g['axis'] == 'x':
                bmin, bmax = (a + fw, c - 0.005, s + fw), (b - fw, c + 0.005, h - fw)
            else:
                bmin, bmax = (c - 0.005, a + fw, s + fw), (c + 0.005, b - fw, h - fw)
            gl = util.make_box('win_%s_%dglass' % (w['id'], k), bmin, bmax,
                               coll=coll, mat=mats['glass'], role='win_glass')
            if gl:
                gl.visible_shadow = False


# ================================================================ 门
def _panel_frame(name_prefix, g, ua, ub, z0, z1, mats, coll, glass=False,
                 frame_role='door_frame_wood', glass_role='glass_clear'):
    """一块门扇：边框梃 + 芯板（玻璃或实心）。role 由调用方给（REWORK 2.2）。"""
    st, sd = 0.045, 0.035  # 梃宽 / 扇厚
    c = g['v_center']

    def box(tag, u0, u1, zz0, zz1, mat, role):
        if g['axis'] == 'x':
            bmin, bmax = (u0, c - sd / 2, zz0), (u1, c + sd / 2, zz1)
        else:
            bmin, bmax = (c - sd / 2, u0, zz0), (c + sd / 2, u1, zz1)
        util.make_box('%s%s' % (name_prefix, tag), bmin, bmax, coll=coll, mat=mat,
                      role=role)

    box('_bot', ua, ub, z0, z0 + st, mats['white'], frame_role)
    box('_top', ua, ub, z1 - st, z1, mats['white'], frame_role)
    box('_lft', ua, ua + st, z0 + st, z1 - st, mats['white'], frame_role)
    box('_rgt', ub - st, ub, z0 + st, z1 - st, mats['white'], frame_role)
    if glass:
        box('_glass', ua + st, ub - st, z0 + st, z1 - st, mats['glass'], glass_role)
        obj = bpy.data.objects.get('%s_glass' % name_prefix)
        if obj:
            obj.visible_shadow = False


def _door_handle(name, g, u_edge, mats, coll, half_t=0.026):
    """黑色细长竖拉手 30cm（规格 4.3 / REWORK 2.2）：贴门扇自由边，两侧微凸。"""
    hh = 0.30
    zc = 1.05
    c = g['v_center']
    if g['axis'] == 'x':
        bmin = (u_edge - 0.030, c - half_t, zc - hh / 2)
        bmax = (u_edge + 0.005, c + half_t, zc + hh / 2)
    else:
        bmin = (c - half_t, u_edge - 0.030, zc - hh / 2)
        bmax = (c + half_t, u_edge + 0.005, zc + hh / 2)
    util.make_box(name, bmin, bmax, coll=coll, mat=mats['dark'], role='metal_black')


def _jamb_lines(wid, k, g, a, b, head, mats, coll, frame_role='door_frame_wood',
                gap_w=0.04):
    """门套窄线条（REWORK_R1FIX F4 / 规格 4.3 "4cm 可见宽度"）：
    洞口三边（左右顶）各两条 4cm 线，贴两侧墙皮向外凸 4cm。
    FINAL1 F11：洞口侧壁（reveal）加与门套同 role 的衬里盒（左右竖 + 顶横，
    跨全墙厚，内缩 0.5mm 避共面），封掉门扇与洞口边之间的亮白缝；
    role 跟随 frame_role —— D2 换门色时衬里自动跟随。
    gap_w = 门扇边到洞口边的间隙宽（木门/长虹门 0.04，开发商玻璃门 0.015）。"""
    fw = 0.04
    c = g['v_center']
    t = config.WALL_T_EXT if g['ext'] else config.WALL_T
    for tag, u0, u1, z0, z1 in (('jlft', a - 0.01, a + fw - 0.01, 0.0, head + fw),
                                ('jrgt', b - fw + 0.01, b + 0.01, 0.0, head + fw),
                                ('jtop', a - 0.01, b + 0.01, head, head + fw)):
        for side, sgn in (('o', 1), ('i', -1)):
            v0 = c + sgn * t / 2
            v1 = c + sgn * (t / 2 + fw)
            if g['axis'] == 'x':
                bmin, bmax = (u0, min(v0, v1), z0), (u1, max(v0, v1), z1)
            else:
                bmin, bmax = (min(v0, v1), u0, z0), (max(v0, v1), u1, z1)
            util.make_box('door_%s_%d%s%s' % (wid, k, tag, side), bmin, bmax,
                          coll=coll, mat=mats['white'], role=frame_role)
    # F11 洞口侧壁衬里：覆盖 gap_w 宽的 reveal 环带（内缩 0.5mm 避与墙段端面共面）
    e = 0.0005
    for tag, u0, u1, z0, z1 in (('lin_l', a + e, a + gap_w - e, 0.0, head),
                                ('lin_r', b - gap_w + e, b - e, 0.0, head),
                                ('lin_t', a + e, b - e, head - gap_w + e, head - e)):
        if g['axis'] == 'x':
            bmin, bmax = (u0, c - t / 2, z0), (u1, c + t / 2, z1)
        else:
            bmin, bmax = (c - t / 2, u0, z0), (c + t / 2, u1, z1)
        util.make_box('door_%s_%d%s' % (wid, k, tag), bmin, bmax,
                      coll=coll, mat=mats['white'], role=frame_role)


def _fluted_door(wid, k, g, a, b, head, mats, coll):
    """REWORK 2.2：卫生间长虹玻璃平开门 —— 木色细框 4cm + 长虹玻璃芯 + 黑色竖拉手。"""
    fw = 0.04
    sd = 0.08  # 玻璃门扇厚
    c = g['v_center']

    def box(tag, u0, u1, z0, z1, mat, role):
        if g['axis'] == 'x':
            bmin, bmax = (u0, c - sd / 2, z0), (u1, c + sd / 2, z1)
        else:
            bmin, bmax = (c - sd / 2, u0, z0), (c + sd / 2, u1, z1)
        util.make_box('door_%s_%d%s' % (wid, k, tag), bmin, bmax, coll=coll,
                      mat=mat, role=role)

    # 门套：窄线条（F4，见 _jamb_lines；旧版 16cm 筒子板即主卧竖条根因）
    _jamb_lines(wid, k, g, a, b, head, mats, coll)
    # 门扇：细框 4cm + 长虹玻璃芯（关闭，铰链在 start 端）
    lw = (b - a) - 2 * fw
    la = a + fw
    lb = la + lw
    box('lft', la, la + fw, 0.01, head - fw, mats['white'], 'door_frame_wood')
    box('rgt', lb - fw, lb, 0.01, head - fw, mats['white'], 'door_frame_wood')
    box('top', la, lb, head - 2 * fw, head - fw, mats['white'], 'door_frame_wood')
    box('bot', la, lb, 0.01, 0.01 + fw, mats['white'], 'door_frame_wood')
    box('fglass', la + fw, lb - fw, 0.01 + fw, head - 2 * fw, mats['glass'],
        'glass_fluted')
    _door_handle('door_%s_%dhdl' % (wid, k), g, lb - fw, mats, coll, half_t=0.045)


def build_doors(layout, mats, coll):
    for w in layout['walls']:
        g = wall_geo(w, layout['walls'])
        for k, op in enumerate(normalize_openings(w)):
            typ, a, b = op['type'], op['start'], op['end']
            head = op.get('head', CEIL)
            if typ == 'door' and w['id'] == 'W12':
                pass  # 四联动门由 builtins.py 按 item（双轨道）建模
            elif typ == 'glass_door':
                # 开发商玻璃门（W15 两扇 / W17 三扇），关闭。
                # REWORK 2.2：深灰铝框 + 清玻璃，绝不能是木门
                # FINAL1 F7：门扇装配顶从 head-0.05 改到 head —— 原本装配顶 2.35 与
                # 过梁带底 head=2.40 之间留 5cm 通长水平缝，太阳从缝直入，掠射到
                # 主卧床头东墙成斜光带（探针 OPEN 直射区 y-8.7..-7.05/z1.6..2.0）。
                # F11：玻璃门洞口加石墨色 reveal 衬里（gap 1.5cm）。
                _jamb_lines(w['id'], k, g, a, b, head, mats, coll,
                            frame_role='door_frame_graphite', gap_w=0.015)
                n = 2 if (b - a) < 1.5 else 3
                for i in range(n):
                    ua = a + (b - a) * i / n
                    ub = a + (b - a) * (i + 1) / n
                    _panel_frame('door_%s_%d' % (w['id'], i), g, ua + 0.015, ub - 0.015,
                                 0.05, head, mats, coll, glass=True,
                                 frame_role='door_frame_graphite',
                                 glass_role='glass_clear')
            elif typ == 'door' and (w['id'], k) in FLUTED_DOORS:
                # REWORK 2.2：公卫门 / 主卫门 -> 长虹玻璃平开门
                _fluted_door(w['id'], k, g, a, b, head, mats, coll)
            elif typ == 'door':
                # 室内木门 / 入户门：门套（三边窄线条）+ 关闭门扇 + 黑色竖拉手
                fw = 0.04
                c = g['v_center']
                _jamb_lines(w['id'], k, g, a, b, head, mats, coll)
                # 门扇（关），铰链在 start 端
                lw = (b - a) - 2 * fw
                if g['axis'] == 'x':
                    bmin, bmax = (a + fw, c - 0.022, 0.01), (a + fw + lw, c + 0.022, head - fw)
                else:
                    bmin, bmax = (c - 0.022, a + fw, 0.01), (c + 0.022, a + fw + lw, head - fw)
                util.make_box('door_%s_%dleaf' % (w['id'], k), bmin, bmax,
                              coll=coll, mat=mats['white'], role='door_leaf_wood')
                # 黑色细长竖拉手（自由边）
                _door_handle('door_%s_%dhdl' % (w['id'], k), g,
                             a + fw + lw - fw, mats, coll)
            # full_opening：无门扇


# ================================================================ 吊顶
def _cbox(name, bmin, bmax, coll, mat=None, role='ceiling_paint'):
    return util.make_box(name, bmin, bmax, coll=coll, mat=mat, role=role)


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
          coll, mats['dark'], role='ac_slot')

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
    fills = [('kitchen', 2.40, 'ceiling_alu'), ('public_bath_wet', 2.40, 'ceiling_alu'),
             ('master_bath', 2.40, 'ceiling_alu'), ('corridor', 2.60, 'ceiling_alu'),
             ('elevator_hall', 2.60, 'ceiling_paint')]
    for rid, z, crole in fills:
        (a, b), (c2, d) = R[rid]
        _cbox('ceil_%s_fill' % rid, (a, b, z), (c2, d, 2.85), coll, white, role=crole)
    # 露台无顶


# ================================================================ 飘窗与露台栏杆
def build_bay(layout, mats, coll):
    """父母房飘窗坐榻台面：0~0.45（顶面与 W23 窗台对齐；胡桃木饰面 规格五.9）。"""
    util.make_box('bay_platform', (0.45, -10.55, 0.0), (3.05, -10.05, 0.45),
                  coll=coll, mat=mats['white'], role='wood')


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
            util.make_box('rail_ter_%s_p%d' % (tag, i), bmin, bmax, coll=coll,
                          mat=mats['white'], role='metal_black')
        if horizontal:
            bmin, bmax = (min(a, c2), b - 0.035, h_top - 0.05), (max(a, c2), b + 0.035, h_top)
            gmin, gmax = (min(a, c2) + 0.05, b - 0.008, h_glass0), (max(a, c2) - 0.05, b + 0.008, h_glass1)
        else:
            bmin, bmax = (a - 0.035, min(b, d), h_top - 0.05), (a + 0.035, max(b, d), h_top)
            gmin, gmax = (a - 0.008, min(b, d) + 0.05, h_glass0), (a + 0.008, max(b, d) - 0.05, h_glass1)
        util.make_box('rail_ter_%s_top' % tag, bmin, bmax, coll=coll,
                      mat=mats['white'], role='metal_black')
        util.make_box('rail_ter_%s_glass' % tag, gmin, gmax, coll=coll,
                      mat=mats['glass'], role='glass_clear')


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

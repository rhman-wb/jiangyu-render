# -*- coding: utf-8 -*-
# furniture.py —— M3 成品家具与软装（白模）
# item 类家具 + 规格补充软装（窗帘/床品/抱枕/摆件/吸顶灯/筒灯几何/琴叶榕）。
# 复用 builtins 的 item_root/child/_front_plane（util.load_module 加载）。
import math
import bpy

import config
import util

B = util.load_module('builtins')


# ---------------------------------------------------------------- 基础
def R(item, mats, coll):
    root = B.item_root(item, coll)
    return root


def box(root, name, bmin, bmax, coll, mat, bevel=None, glass=False, role=None):
    return B.child(root, name, bmin, bmax, coll, mat, bevel=bevel, glass=glass,
                   role=role)


def legs(root, cid, bmin, bmax, coll, mat, n=4, h=0.12, s=0.04, inset=0.05,
         role='wood'):
    """桌/柜木腿（规格 7.3：A 沙发 5cm 木腿等由调用方传参）。"""
    xs = (bmin[0] + inset, bmax[0] - inset)
    ys = (bmin[1] + inset, bmax[1] - inset)
    i = 0
    for x in xs:
        for y in ys:
            box(root, '%s_leg%d' % (cid, i), (x - s / 2, y - s / 2, bmin[2]),
                (x + s / 2, y + s / 2, bmin[2] + h), coll, mat, role=role)
            i += 1


# ---------------------------------------------------------------- 床
def build_bed(item, mats, coll):
    """床：框架 + 床垫 + 床品（被子下垂边 + 2 枕 + 盖毯）+ parts 床头板。
    REWORK #3/4.3：枕头、床头软包、盖毯位置由 config.BED_HEAD_SIDE 决定。"""
    cid = item['id']
    room = item.get('room', '')
    kids = room in ('daughter_room', 'son_room')
    furn_role = 'kids_furn' if kids else 'wood'
    bedding_role = 'kids_bedding' if kids else 'bedding'
    bmin, bmax = item['bbox']['min'], item['bbox']['max']
    root = R(item, mats, coll)
    x0, y0, z0 = bmin
    x1, y1, z1 = bmax
    # 床架 + 床垫（REWORK 2.3：孩子房床架不用木色）
    box(root, cid + '_frame', (x0, y0, 0.0), (x1, y1, z1 - 0.18), coll,
        mats['wood'], role=furn_role)
    box(root, cid + '_mattress', (x0 + 0.03, y0 + 0.03, z1 - 0.18),
        (x1 - 0.03, y1 - 0.03, z1), coll, mats['white'], bevel=0.02,
        role=bedding_role)
    for p in item.get('parts', []):
        pb = p['bbox']
        # 床头板：孩子房 = 家具本色；主卧独立 headboard item 另建；其余 = 软包
        hb_role = furn_role if kids else 'headboard'
        box(root, cid + '_headboard', tuple(pb['min']), tuple(pb['max']),
            coll, mats['white'], bevel=0.03, role=hb_role)
    # 床头端（REWORK 4.3：BED_HEAD_SIDE；主卧 +X，其余 -X）
    head_pos = config.BED_HEAD_SIDE.get(room, '-X') == '+X'
    # 被子（床头对侧起 2/3，下垂边收在 bbox 内）+ 枕头（床头端）+ 盖毯（床尾 1/3）
    if (x1 - x0) > (y1 - y0):
        hx0, hx1 = (x1 - 0.52, x1 - 0.10) if head_pos else (x0 + 0.10, x0 + 0.52)
        t0, t1 = (x0 + 0.35, x0 + 0.75) if head_pos else (x1 - 0.75, x1 - 0.35)
        dx0, dx1 = (x0 + 0.04, x1 - 0.55) if head_pos else (x0 + 0.55, x1 - 0.04)
        box(root, cid + '_duvet', (dx0, y0 - 0.0, z1 - 0.06),
            (dx1, y1 + 0.0, z1 + 0.04), coll, mats['white'], bevel=0.025,
            role=bedding_role)
        box(root, cid + '_duvetdrop', (dx0, y0, z1 - 0.30),
            (dx1, y0 + 0.03, z1 - 0.04), coll, mats['white'], bevel=0.02,
            role=bedding_role)
        box(root, cid + '_duvetdrop2', (dx0, y1 - 0.03, z1 - 0.30),
            (dx1, y1, z1 - 0.04), coll, mats['white'], bevel=0.02,
            role=bedding_role)
        py = (y0 + y1) / 2
        box(root, cid + '_pillow1', (hx0, py - 0.50, z1),
            (hx1, py - 0.02, z1 + 0.11), coll, mats['white'], bevel=0.045,
            role=bedding_role)
        box(root, cid + '_pillow2', (hx0, py + 0.02, z1),
            (hx1, py + 0.50, z1 + 0.11), coll, mats['white'], bevel=0.045,
            role=bedding_role)
        # 孩子房点缀色抱枕（REWORK 2.3）
        if kids:
            box(root, cid + '_pillow_acc', (hx0 + 0.06, py - 0.34, z1 + 0.09),
                (hx0 + 0.40, py + 0.34, z1 + 0.17), coll, mats['white'],
                bevel=0.05, role='kids_accent')
        box(root, cid + '_throw', (t0, y0, z1 + 0.01),
            (t1, y1, z1 + 0.05), coll, mats['white'], bevel=0.015,
            role='throw_oat')
    else:
        hy0, hy1 = (y1 - 0.52, y1 - 0.10) if head_pos else (y0 + 0.10, y0 + 0.52)
        t0, t1 = (y0 + 0.35, y0 + 0.75) if head_pos else (y1 - 0.75, y1 - 0.35)
        dy0, dy1 = (y0 + 0.04, y1 - 0.55) if head_pos else (y0 + 0.55, y1 - 0.04)
        box(root, cid + '_duvet', (x0, dy0, z1 - 0.06),
            (x1, dy1, z1 + 0.04), coll, mats['white'], bevel=0.025,
            role=bedding_role)
        box(root, cid + '_duvetdrop', (x0, dy0, z1 - 0.30),
            (x0 + 0.03, dy1, z1 - 0.04), coll, mats['white'], bevel=0.02,
            role=bedding_role)
        box(root, cid + '_duvetdrop2', (x1 - 0.03, dy0, z1 - 0.30),
            (x1, dy1, z1 - 0.04), coll, mats['white'], bevel=0.02,
            role=bedding_role)
        px = (x0 + x1) / 2
        box(root, cid + '_pillow1', (px - 0.50, hy0, z1),
            (px - 0.02, hy1, z1 + 0.11), coll, mats['white'], bevel=0.045,
            role=bedding_role)
        box(root, cid + '_pillow2', (px + 0.02, hy0, z1),
            (px + 0.50, hy1, z1 + 0.11), coll, mats['white'], bevel=0.045,
            role=bedding_role)
        box(root, cid + '_throw', (x0, t0, z1 + 0.01),
            (x1, t1, z1 + 0.05), coll, mats['white'], bevel=0.015,
            role='throw_oat')


def build_headboard(item, mats, coll):
    cid = item['id']
    bmin, bmax = item['bbox']['min'], item['bbox']['max']
    root = R(item, mats, coll)
    # 主卧焦糖软包薄床头（规格 5.6）
    box(root, cid + '_pad', bmin, bmax, coll, mats['wood'], bevel=0.03,
        role='leather_caramel' if 'master' in cid else 'fabric_oat')


# ---------------------------------------------------------------- 沙发
def build_sofa(item, mats, coll):
    """沙发：底座+座垫分块+靠背分块+扶手(+parts 转角/靠背增高)；抱枕另加。"""
    cid = item['id']
    bmin, bmax = item['bbox']['min'], item['bbox']['max']
    root = R(item, mats, coll)
    x0, y0, z0 = bmin
    x1, y1, z1 = bmax
    parts_hi = item.get('parts', [])
    # 朝向：面朝东(+X)（规格 7.2），靠背在 x0 侧（parts bbox x0..x0+0.25 即靠背增高段）
    back_x0 = x0
    if parts_hi:
        pb = parts_hi[0]['bbox']
        if pb['min'][0] < (x0 + x1) / 2:
            back_x0 = x0  # 靠背在西
            back_zone = (pb['min'][0], pb['max'][0], pb['min'][1], pb['max'][1])
        else:
            back_zone = (x1 - 0.25, x1, y0, y1)
    else:
        back_zone = (x0, x0 + 0.25, y0, y1)
    bx0, bx1 = back_zone[0], back_zone[1]
    # 底座（贴地）；无 parts 的低模块（B 转角段）靠背/座垫不超 bbox 顶
    back_top = z1 + 0.36 if parts_hi else z1 - 0.01
    seat_top = z1 + 0.05 if parts_hi else z1 - 0.01
    sofa_role = 'leather_caramel' if item.get('group') == 'A' else 'sofa_b_fabric'
    if item.get('group') == 'A':
        # R2 #14：A 皮沙发 5cm 实木细腿（替换贴地箱体，规格 5.2）
        box(root, cid + '_base', (x0, y0, 0.05), (x1, y1, z1 - 0.14), coll,
            mats['white'], role=sofa_role)
        legs(root, cid, (x0 + 0.02, y0 + 0.02, 0.0), (x1 - 0.02, y1 - 0.02, 0.05),
             coll, mats['wood'], n=6, h=0.05, s=0.05, inset=0.06, role='wood')
    else:
        box(root, cid + '_base', (x0, y0, 0.03), (x1, y1, z1 - 0.14), coll,
            mats['white'], role=sofa_role)
    # 靠背（分块）
    n = max(2, round((y1 - y0) / 0.9))
    w = (y1 - y0) / n
    for i in range(n):
        box(root, '%s_back%d' % (cid, i), (bx0 + 0.02, y0 + i * w + 0.015, z1 - 0.16),
            (bx1 - 0.02, y0 + (i + 1) * w - 0.015, back_top), coll, mats['white'],
            bevel=0.03, role=sofa_role)
    # 座垫（分块）
    for i in range(n):
        box(root, '%s_seat%d' % (cid, i), (bx1 + 0.01, y0 + i * w + 0.02, z1 - 0.13),
            (x1 - 0.06, y0 + (i + 1) * w - 0.02, seat_top), coll, mats['white'],
            bevel=0.035, role=sofa_role)
    # 扶手（两端）；无 parts 低模块扶手同高收低
    arm_top = z1 + 0.20 if parts_hi else z1 - 0.01
    for j, ay in ((0, y0), (1, y1 - 0.18)):
        box(root, '%s_arm%d' % (cid, j), (bx0 + 0.02, ay + 0.015, 0.03),
            (x1 - 0.06, ay + 0.165, arm_top), coll, mats['white'], bevel=0.04,
            role=sofa_role)
    # 抱枕（墨绿/砖红，规格 5.2；低模块不放）
    if parts_hi:
        box(root, cid + '_pillow_olive', (bx1 + 0.06, y0 + 0.30, z1 + 0.02),
            (bx1 + 0.30, y0 + 0.62, z1 + 0.30), coll, mats['dark'], bevel=0.05,
            role='pillow_olive')
        box(root, cid + '_pillow_brick', (bx1 + 0.05, y1 - 0.75, z1 + 0.02),
            (bx1 + 0.29, y1 - 0.45, z1 + 0.30), coll, mats['wood'], bevel=0.05,
            role='pillow_brick')
    # parts 第二块（B 转角段）单独成体
    if len(parts_hi) > 1 and item['group'] == 'B':
        pass  # B_sofa_02 是独立 item


def build_ottoman(item, mats, coll):
    cid = item['id']
    bmin, bmax = item['bbox']['min'], item['bbox']['max']
    root = R(item, mats, coll)
    # A 方案脚踏：焦糖皮（REWORK 2.4 禁木色）
    box(root, cid + '_pad', bmin, (bmax[0], bmax[1], bmax[2]), coll, mats['wood'],
        bevel=0.05, role='leather_caramel')
    box(root, cid + '_base', (bmin[0] + 0.08, bmin[1] + 0.08, 0.0),
        (bmax[0] - 0.08, bmax[1] - 0.08, 0.12), coll, mats['wood'],
        role='leather_caramel')


# ---------------------------------------------------------------- 桌几
def build_dining_table(item, mats, coll):
    """A 餐桌 / B 长桌（island_02）：40mm 面板圆角 + 收分腿/板式腿。"""
    cid = item['id']
    bmin, bmax = item['bbox']['min'], item['bbox']['max']
    root = R(item, mats, coll)
    x0, y0, z0 = bmin
    x1, y1, z1 = bmax
    box(root, cid + '_top', (x0, y0, z1 - 0.04), (x1, y1, z1), coll, mats['wood'],
        bevel=0.012, role='wood')
    if item['group'] == 'A':  # 四条收分腿
        for i, (lx, ly) in enumerate(((x0 + 0.10, y0 + 0.10), (x1 - 0.10, y0 + 0.10),
                                      (x0 + 0.10, y1 - 0.10), (x1 - 0.10, y1 - 0.10))):
            box(root, '%s_leg%d' % (cid, i), (lx - 0.035, ly - 0.035, 0.0),
                (lx + 0.035, ly + 0.035, z1 - 0.04), coll, mats['wood'], bevel=0.01,
                role='wood')
    else:  # B 板式腿两块
        box(root, cid + '_panel0', (x0 + 0.15, y0 + 0.12, 0.0),
            (x0 + 0.15 + 0.05, y1 - 0.12, z1 - 0.04), coll, mats['wood'], role='wood')
        box(root, cid + '_panel1', (x1 - 0.20, y0 + 0.12, 0.0),
            (x1 - 0.15, y1 - 0.12, z1 - 0.04), coll, mats['wood'], role='wood')


def build_desk(item, mats, coll):
    """书桌（主卧/女儿/儿子）：面板 + 侧板或四腿 + 薄抽屉条。"""
    cid = item['id']
    room = item.get('room', '')
    furn_role = 'kids_furn' if room in ('daughter_room', 'son_room') else 'wood'
    bmin, bmax = item['bbox']['min'], item['bbox']['max']
    root = R(item, mats, coll)
    x0, y0, z0 = bmin
    x1, y1, z1 = bmax
    box(root, cid + '_top', (x0, y0, z1 - 0.04), (x1, y1, z1), coll, mats['wood'],
        bevel=0.01, role=furn_role)
    box(root, cid + '_drawer', (x0 + 0.06, y0 + 0.05, z1 - 0.16),
        (x1 - 0.06, y1 - 0.05, z1 - 0.04), coll, mats['white'], role=furn_role)
    for i, (lx, ly) in enumerate(((x0 + 0.08, y0 + 0.06), (x1 - 0.08, y0 + 0.06),
                                  (x0 + 0.08, y1 - 0.06), (x1 - 0.08, y1 - 0.06))):
        box(root, '%s_leg%d' % (cid, i), (lx - 0.025, ly - 0.025, 0.0),
            (lx + 0.025, ly + 0.025, z1 - 0.16), coll, mats['wood'], role=furn_role)
    if item['room'] == 'master_bedroom':
        box(root, cid + '_monitor', (x1 - 0.55, (y0 + y1) / 2 - 0.21, z1),
            (x1 - 0.50, (y0 + y1) / 2 + 0.21, z1 + 0.33), coll, mats['dark'],
            bevel=0.008, role='black_glass')
        box(root, cid + '_monstand', (x1 - 0.53, (y0 + y1) / 2 - 0.09, z1),
            (x1 - 0.50, (y0 + y1) / 2 + 0.09, z1 + 0.18), coll, mats['dark'],
            role='metal_black')


def build_coffee_table(item, mats, coll):
    """圆茶几/圆边几（cylinder item）：圆台面 + 三锥腿 -> 白模圆柱+腿。"""
    cid = item['id']
    c = item['center']
    r = item['radius']
    z0 = item.get('z_base', 0.0)
    h = item['height']
    root = R(item, mats, coll)
    cyl(root, cid + '_top', c, r, z0 + h - 0.04, z0 + h, coll, mats['wood'],
        role='wood')
    for i in range(3):
        a = math.radians(120 * i + 30)
        px, py = c[0] + math.cos(a) * r * 0.6, c[1] + math.sin(a) * r * 0.6
        box(root, '%s_leg%d' % (cid, i), (px - 0.02, py - 0.02, z0),
            (px + 0.02, py + 0.02, z0 + h - 0.04), coll, mats['wood'], role='wood')


def cyl(root, name, center_xy, radius, z0, z1, coll, mat, verts=24, role=None):
    mesh = bpy.data.meshes.new(name + '_mesh')
    bm = bmesh_new_cylinder(radius, z1 - z0, verts)
    bm.to_mesh(mesh)
    bm.free()
    o = bpy.data.objects.new(name, mesh)
    o.location = (center_xy[0], center_xy[1], z0)
    if mat is not None:
        o.data.materials.append(mat)
    if role is not None:
        o['role'] = role
    coll.objects.link(o)
    if root is not None:
        o.parent = root
    return o


def bmesh_new_cylinder(r, h, verts=24):
    """底面在 z=0、顶面在 z=h 的圆柱（create_cone 是居中的，平移 h/2）。"""
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=verts,
                          radius1=r, radius2=r, depth=h)
    for v in bm.verts:
        v.co.z += h / 2
    return bm


def build_side_table(item, mats, coll):
    build_coffee_table(item, mats, coll)


# ---------------------------------------------------------------- 椅
_TABLE_CENTER_CACHE = {}


def _table_center(group):
    """同组餐桌（*_island_02）中心，FINAL1 F10 靠背朝向用。"""
    if group not in _TABLE_CENTER_CACHE:
        tc = None
        for it in util.load_layout()['items']:
            if it.get('group') == group and it['id'].endswith('island_02'):
                b = it['bbox']
                tc = ((b['min'][0] + b['max'][0]) / 2, (b['min'][1] + b['max'][1]) / 2)
                break
        _TABLE_CENTER_CACHE[group] = tc
    return _TABLE_CENTER_CACHE[group]


def build_dining_chair(item, mats, coll):
    """中古弧形扶手餐椅 / 混搭椅：座垫 + 薄弧背 + 四腿 + 扶手条。
    FINAL1 F10：靠背按椅心-桌心四向（±x/±y）判定，端椅（x 向）不再把靠背
    做成横贯全宽的 0.32m 实心块；背板厚一律 ≤4cm。椅型/材质留 D5。"""
    cid = item['id']
    bmin, bmax = item['bbox']['min'], item['bbox']['max']
    root = R(item, mats, coll)
    x0, y0, z0 = bmin
    x1, y1, z1 = bmax
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    tc = _table_center(item.get('group'))
    dx = cx - tc[0] if tc else 0.0
    dy = cy - tc[1] if tc else 1.0
    back_x = abs(dx) > abs(dy)          # 靠背在 x 远桌侧（端椅）
    bt = 0.04                            # 背板厚 ≤4cm
    if back_x:
        bu0, bu1 = ((x1 - bt, x1) if dx > 0 else (x0, x0 + bt))
        box(root, cid + '_back', (bu0, y0 + 0.02, 0.47), (bu1, y1 - 0.02, z1 - 0.015),
            coll, mats['wood'], bevel=0.012, role='wood')
    else:
        bv0, bv1 = ((y1 - bt, y1) if dy > 0 else (y0, y0 + bt))
        box(root, cid + '_back', (x0 + 0.02, bv0, 0.47), (x1 - 0.02, bv1, z1 - 0.015),
            coll, mats['wood'], bevel=0.012, role='wood')
    box(root, cid + '_seat', (x0 + 0.02, y0 + 0.02, 0.40), (x1 - 0.02, y1 - 0.02, 0.47),
        coll, mats['white'], bevel=0.02, role='seat_oat')
    # R2 #14：收分腿（上粗下细两段）
    for i, (lx, ly) in enumerate(((x0 + 0.035, y0 + 0.035), (x1 - 0.035, y0 + 0.035),
                                  (x0 + 0.035, y1 - 0.035), (x1 - 0.035, y1 - 0.035))):
        box(root, '%s_leg%d' % (cid, i), (lx - 0.018, ly - 0.018, 0.20),
            (lx + 0.018, ly + 0.018, 0.40), coll, mats['wood'], role='wood')
        box(root, '%s_legt%d' % (cid, i), (lx - 0.012, ly - 0.012, 0.0),
            (lx + 0.012, ly + 0.012, 0.20), coll, mats['wood'], role='wood')
    # 扶手：两根侧轨平行于朝桌方向 + 前端下俯支撑
    if back_x:
        for j, ay in ((0, y0 + 0.05), (1, y1 - 0.05)):
            box(root, '%s_arm%d' % (cid, j), (x0 + 0.06, ay - 0.018, 0.62),
                (x1 - 0.06, ay + 0.018, 0.66), coll, mats['wood'], bevel=0.01,
                role='wood')
            axf = (x0 + 0.31) if dx > 0 else (x1 - 0.31)
            ax2 = axf - (0.25 if dx > 0 else -0.25)   # 向桌侧收（不出 bbox）
            box(root, '%s_armf%d' % (cid, j),
                (min(axf, ax2), ay - 0.016, 0.575),
                (max(axf, ax2), ay + 0.016, 0.625),
                coll, mats['wood'], bevel=0.012, role='wood')
    else:
        for j, ax in ((0, x0 + 0.05), (1, x1 - 0.05)):
            box(root, '%s_arm%d' % (cid, j), (ax - 0.018, y0 + 0.06, 0.62),
                (ax + 0.018, y1 - 0.06, 0.66), coll, mats['wood'], bevel=0.01,
                role='wood')
            ayf = (y0 + 0.31) if dy > 0 else (y1 - 0.31)
            ay2 = ayf - (0.25 if dy > 0 else -0.25)   # 向桌侧收（不出 bbox）
            box(root, '%s_armf%d' % (cid, j), (ax - 0.016,
                min(ayf, ay2), 0.575),
                (ax + 0.016, max(ayf, ay2), 0.625),
                coll, mats['wood'], bevel=0.012, role='wood')


def build_chair(item, mats, coll):
    """书桌椅：座+薄背+五星脚简化为四腿+脚轮条。"""
    cid = item['id']
    room = item.get('room', '')
    seat_role = 'kids_furn' if room in ('daughter_room', 'son_room') else 'seat_oat'
    bmin, bmax = item['bbox']['min'], item['bbox']['max']
    root = R(item, mats, coll)
    x0, y0 = bmin[0], bmin[1]
    x1, y1 = bmax[0], bmax[1]
    z1 = bmax[2]
    box(root, cid + '_seat', (x0 + 0.02, y0 + 0.02, 0.42), (x1 - 0.02, y1 - 0.02, 0.50),
        coll, mats['wood'], bevel=0.03, role=seat_role)
    box(root, cid + '_back', (x0 + 0.02, y0 + 0.02, 0.50), (x1 - 0.02, y0 + 0.10, z1 - 0.015),
        coll, mats['wood'], bevel=0.03, role=seat_role)
    box(root, cid + '_post', ((x0 + x1) / 2 - 0.03, (y0 + y1) / 2 - 0.03, 0.05),
        ((x0 + x1) / 2 + 0.03, (y0 + y1) / 2 + 0.03, 0.42), coll, mats['dark'],
        role='metal_black')
    box(root, cid + '_base', (x0 + 0.02, y0 + 0.02, 0.0), (x1 - 0.02, y1 - 0.02, 0.05),
        coll, mats['dark'], bevel=0.015, role='metal_black')


def build_lounge_chair(item, mats, coll):
    """中古单椅（A 墨绿面料 + 胡桃木框，REWORK 2.4）/ 露台藤编单椅。"""
    cid = item['id']
    if item.get('shape') == 'cylinder':
        # R2FIX2 N2：露台椅改中古休闲椅——弧形靠背（三段渐斜板拼弧）+ 扶手 +
        # 低座（座高 0.38）+ 藤编织座背（rattan 双 Wave 编织凹凸，#C9B08A）+
        # 燕麦坐垫；朝向面向圆桌（由布局内建：x<10.9 朝东，x>10.9 朝西）。
        # 全部部件落在 layout 包络圆 r=0.28 内、总高 ≤0.48（h0.45+3cm 容差）。
        c, r, z0, h = item['center'], item['radius'], item.get('z_base', 0.0), item['height']
        root = R(item, mats, coll)
        rmat = mats.get('rattan', mats['wood'])
        sgn = 1.0 if c[0] < 10.9 else -1.0        # 朝桌方向（椅1 东、椅2 西）

        def P(du, dv):                             # 局部(朝桌向 du, 侧向 dv) -> 世界
            return (c[0] + du * sgn, c[1] + dv)

        def PB(nm, du0, dv0, zl, du1, dv1, zh, mat, bev=None, role=None):
            """局部盒 -> 世界盒；sgn=-1 时角点自动排序（防 min>max 被丢弃）。"""
            ax, ay = P(du0, dv0)
            bx, by = P(du1, dv1)
            box(root, nm, (min(ax, bx), min(ay, by), zl),
                (max(ax, bx), max(ay, by), zh), coll, mat, bevel=bev, role=role)

        seat_h = 0.38
        # 座框（藤面）+ 燕麦坐垫（外沿 ±0.92r 贴合包络圆，qa 边缘 ±2cm 内）
        PB(cid + '_seat', -r * 0.92, -r * 0.92, z0 + seat_h - 0.05,
           r * 0.92, r * 0.92, z0 + seat_h, rmat, bev=0.012, role='rattan')
        PB(cid + '_cushion', -r * 0.70, -r * 0.70, z0 + seat_h,
           r * 0.70, r * 0.70, z0 + seat_h + 0.035, mats.get('oat'),
           bev=0.015, role='fabric_oat')
        # 弧形靠背：三段渐斜板拼弧（在椅后 du≈-0.88r，底段起于座面，总高 ≤0.48 容差）
        for i, dz in enumerate((seat_h, seat_h + 0.045, seat_h + 0.08)):
            lean = 0.050 - i * 0.018               # 底段最靠后，上段前移 -> 弧
            du_b = -r * 0.88 + lean * (i + 1) / 3.0
            PB('%s_back%d' % (cid, i), du_b - 0.026, -r * 0.74, z0 + dz,
               du_b + 0.026, r * 0.74, min(h + 0.03, dz + 0.09), rmat,
               bev=0.008, role='rattan')
        # 扶手 ×2：侧藤立板 + 木扶手面（dv ±0.83r..0.93r；顶 ≤0.48 容差）
        for sd in (-1, 1):
            PB('%s_arm%d' % (cid, sd), -r * 0.66, sd * r * 0.78 - 0.02 * sd, z0 + seat_h,
               r * 0.36, sd * r * 0.78 + 0.02 * sd, z0 + seat_h + 0.075, rmat,
               bev=0.008, role='rattan')
            PB('%s_armp%d' % (cid, sd), -r * 0.68, sd * r * 0.83 - 0.028 * sd, z0 + seat_h + 0.075,
               r * 0.38, sd * r * 0.83 + 0.028 * sd, z0 + 0.48, mats['wood'],
               bev=0.008, role='wood')
        # 四锥形木腿（座下）
        for i in range(4):
            a = math.radians(90 * i + 45)
            du, dv = math.cos(a) * r * 0.62, math.sin(a) * r * 0.62
            px, py = P(du, dv)
            box(root, '%s_leg%d' % (cid, i), (px - 0.022, py - 0.022, z0),
                (px + 0.022, py + 0.022, z0 + seat_h - 0.05), coll, mats['wood'],
                role='wood')
        return
    bmin, bmax = item['bbox']['min'], item['bbox']['max']
    root = R(item, mats, coll)
    x0, y0, z0 = bmin
    x1, y1, z1 = bmax
    # REWORK 2.4：A 中古单椅 = 墨绿面料（座/背）+ 胡桃木框（腿/扶手），禁大块黑
    seat_role = 'fabric_olive' if item['room'] == 'living_dining_balcony' else 'fabric_oat'
    box(root, cid + '_seat', (x0 + 0.02, y0 + 0.02, 0.36), (x1 - 0.02, y1 - 0.02, 0.46),
        coll, mats['white'], bevel=0.04, role=seat_role)
    box(root, cid + '_back', (x0 + 0.02, y0 + 0.02, 0.44), (x1 - 0.02, y0 + 0.14, z1),
        coll, mats['white'], bevel=0.04, role=seat_role)
    for i, (lx, ly) in enumerate(((x0 + 0.04, y0 + 0.04), (x1 - 0.04, y0 + 0.04),
                                  (x0 + 0.04, y1 - 0.04), (x1 - 0.04, y1 - 0.04))):
        box(root, '%s_leg%d' % (cid, i), (lx - 0.02, ly - 0.02, 0.0),
            (lx + 0.02, ly + 0.02, 0.36), coll, mats['wood'], role='wood')
    for j, ax in ((0, x0 + 0.05), (1, x1 - 0.05)):
        box(root, '%s_arm%d' % (cid, j), (ax - 0.02, y0 + 0.05, 0.55),
            (ax + 0.02, y1 - 0.07, 0.60), coll, mats['wood'], bevel=0.015,
            role='wood')


# ---------------------------------------------------------------- 柜/架/凳
def build_wardrobe_kids(item, mats, coll):
    """孩子房成品衣柜（仅示意）：箱体+门缝；REWORK 2.3 一律家具本色（非木色）。"""
    B.build_wardrobe(item, mats, coll, box_role='kids_furn', front_role='kids_furn')


def build_shelf(item, mats, coll):
    """矮书格/窄书架：两侧板+背板+3-4 层板。"""
    cid = item['id']
    room = item.get('room', '')
    furn_role = 'kids_furn' if room in ('daughter_room', 'son_room') else 'wood'
    bmin, bmax = item['bbox']['min'], item['bbox']['max']
    root = R(item, mats, coll)
    axis, face, inward = B._front_plane(bmin, bmax, item.get('room'))
    t = 0.025
    box(root, cid + '_side0', (bmin[0], bmin[1], bmin[2]), (bmin[0] + t, bmax[1], bmax[2]),
        coll, mats['wood'], role=furn_role)
    box(root, cid + '_side1', (bmax[0] - t, bmin[1], bmin[2]), (bmax[0], bmax[1], bmax[2]),
        coll, mats['wood'], role=furn_role)
    box(root, cid + '_top', (bmin[0], bmin[1], bmax[2] - t), (bmax[0], bmax[1], bmax[2]),
        coll, mats['wood'], role=furn_role)
    n = max(2, round((bmax[2] - bmin[2]) / 0.32))
    dz = (bmax[2] - t - (bmin[2] + t)) / n
    for i in range(1, n):
        z = bmin[2] + t + i * dz
        box(root, '%s_sh%d' % (cid, i), (bmin[0] + t, bmin[1] + 0.01, z),
            (bmax[0] - t, bmax[1] - 0.01, z + t), coll, mats['wood'], role=furn_role)


def build_stool(item, mats, coll):
    """小圆凳/换鞋凳/梳妆凳（cylinder 或 box）。"""
    cid = item['id']
    if item.get('shape') == 'cylinder':
        c, r, z0, h = item['center'], item['radius'], item.get('z_base', 0.0), item['height']
        root = R(item, mats, coll)
        cyl(root, cid + '_top', c, r, z0 + h - 0.05, z0 + h, coll, mats['wood'],
            role='wood')
        cyl(root, cid + '_post', c, r * 0.18, z0, z0 + h - 0.05, coll, mats['wood'],
            role='wood')
        for p in item.get('parts', []):
            if p.get('shape') == 'sphere':
                # 端景小圆凳上的乳白陶罐（规格 5.1，REWORK 2.4 禁木色）
                sph(root, cid + '_jar', tuple(p['center']), p['radius'], coll,
                    mats['white'], role='vase_white')
    else:
        bmin, bmax = item['bbox']['min'], item['bbox']['max']
        root = R(item, mats, coll)
        # 主卧梳妆凳 = 燕麦色软垫（规格 5.6）；其余（玄关换鞋凳）胡桃木
        pad_role = 'fabric_oat' if 'master' in cid else 'wood'
        box(root, cid + '_pad', (bmin[0], bmin[1], bmax[2] - 0.06), bmax, coll,
            mats['wood'], bevel=0.03, role=pad_role)
        legs(root, cid, (bmin[0], bmin[1], 0.0), (bmax[0], bmax[1], bmax[2] - 0.06),
             coll, mats['wood'], h=bmax[2] - 0.06, s=0.035, inset=0.06,
             role='wood')


def sph(root, name, center, r, coll, mat, seg=16, role=None):
    import bmesh
    mesh = bpy.data.meshes.new(name + '_mesh')
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg * 2, v_segments=seg, radius=r)
    bm.to_mesh(mesh)
    bm.free()
    o = bpy.data.objects.new(name, mesh)
    o.location = center
    if mat is not None:
        o.data.materials.append(mat)
    if role is not None:
        o['role'] = role
    coll.objects.link(o)
    if root is not None:
        o.parent = root
    return o


# ---------------------------------------------------------------- 灯/电视/画/绿植
def build_pendant_lamp(item, mats, coll):
    """乳白玻璃球吊灯：吊杆 + 球（item 即球心半径）。"""
    cid = item['id']
    c = item['center']
    r = item['radius']
    root = R(item, mats, coll)
    cyl(root, cid + '_rod', (c[0], c[1]), 0.008, c[2] + r, 2.60, coll, mats['dark'],
        role='metal_black')
    sph(root, cid + '_ globe', (c[0], c[1], c[2]), r, coll, mats['glass'],
        role='opal_glass')


def build_floor_lamp(item, mats, coll):
    """R2FIX m2 弧形落地灯：圆盘底座 + Bezier 弧形细杆（弯向沙发侧上方）+
    半球乳白灯罩悬于杆端。旧版两根断开的竖直圆柱+悬空直筒罩废弃。"""
    cid = item['id']
    c = item['center']
    z0 = item.get('z_base', 0.0)
    h = item['height']
    root = R(item, mats, coll)
    # 圆盘底座
    cyl(root, cid + '_base', c, 0.15, z0, z0 + 0.02, coll, mats['dark'],
        role='metal_black')
    # 弧形细杆：Bezier 三段（立直 -> 弯弧 -> 水平悬伸），bevel 成 Ø24mm 杆
    # FINAL1 F1：add(2) 只得 3 点而 pts 有 4 个，zip 截断末点 -> 弧臂止于 x+0.16、
    # 灯罩悬空在 x+0.46。改为 add(len(pts)-1)，弧臂接到灯罩正上方。
    cu = bpy.data.curves.new(cid + '_arc', 'CURVE')
    cu.dimensions = '3D'
    sp = cu.splines.new('BEZIER')
    pts = [(c[0], c[1], z0),
           (c[0], c[1], z0 + h * 0.60),
           (c[0] + 0.16, c[1], z0 + h * 0.92),
           (c[0] + 0.46, c[1], z0 + h * 0.97)]
    sp.bezier_points.add(len(pts) - 1)
    for bp, p in zip(sp.bezier_points, pts):
        bp.co = p
        bp.handle_left_type = bp.handle_right_type = 'AUTO'
    cu.bevel_depth = 0.012
    arc = bpy.data.objects.new(cid + '_arc', cu)
    arc.data.materials.append(mats['dark'])
    arc['role'] = 'metal_black'
    coll.objects.link(arc)
    arc.parent = root
    # 半球灯罩（开口朝下，悬于杆端）
    import bmesh
    me = bpy.data.meshes.new(cid + '_shade_mesh')
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=12, radius=0.16)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < -0.001],
                     context='VERTS')
    bm.to_mesh(me)
    bm.free()
    so = bpy.data.objects.new(cid + '_shade', me)
    so.location = (c[0] + 0.46, c[1], z0 + h * 0.97 - 0.06)
    so.data.materials.append(mats['white'])
    so['role'] = 'opal_glass'
    coll.objects.link(so)
    so.parent = root
    return root


def build_tv(item, mats, coll):
    """电视：A 悬空电视柜上方固定 85 寸 / B 移动电视（可推移支架）。
    REWORK #9：B 移动电视渲染时停放在东墙北段柜前，中心 (8.25,-6.0)、屏幕朝西，
    豁免 layout 位置铁律（decisions_log）。
    R2 #14：B 支架细杆化——Ø24mm 单立杆 + 三斜撑 + 250mm 圆盘底座（黑色细杆，禁方墩）。"""
    cid = item['id']
    bmin, bmax = item['bbox']['min'], item['bbox']['max']
    root = R(item, mats, coll)
    if item.get('group') == 'B':
        # 屏幕薄板：中心 (8.25,-6.0)，法向 X（面朝西 -X）
        sw, sh_ = bmax[1] - bmin[1], bmax[2] - bmin[2]   # 原始宽高（Y/Z 尺寸）
        cx, cy = 8.25, -6.0
        sbmin = (cx - 0.05, cy - sw / 2, 0.60)
        sbmax = (cx + 0.05, cy + sw / 2, 0.60 + sh_)
        box(root, cid + '_screen', sbmin, sbmax, coll, mats['dark'], bevel=0.004,
            role='black_glass')
        # 细杆立杆（中心，屏后）
        cyl(root, cid + '_pole', (cx + 0.03, cy), 0.012, 0.10, 0.62, coll,
            mats['dark'], role='metal_black')
        # 三斜撑（杆底向外张）
        for i, (dx, dy) in enumerate(((0.16, 0.0), (-0.10, 0.12), (-0.10, -0.12))):
            box(root, cid + '_brace%d' % i,
                (min(cx + 0.03, cx + dx) - 0.008, min(cy, cy + dy) - 0.008, 0.0),
                (max(cx + 0.03, cx + dx) + 0.008, max(cy, cy + dy) + 0.008, 0.10),
                coll, mats['dark'], role='metal_black')
        # 圆盘底座
        cyl(root, cid + '_base', (cx + 0.04, cy), 0.125, 0.0, 0.018, coll,
            mats['dark'], role='metal_black')
        return root
    box(root, cid + '_screen', bmin, bmax, coll, mats['dark'], bevel=0.004,
        role='black_glass')
    for p in item.get('parts', []):
        pb = p['bbox']
        box(root, cid + '_stand', tuple(pb['min']), tuple(pb['max']), coll,
            mats['dark'], role='metal_black')


def build_artwork(item, mats, coll):
    """端景挂画 + 画灯（规格 5.1：暖色抽象画 + 黑色画灯；REWORK 4.1 art_abstract）。"""
    cid = item['id']
    bmin, bmax = item['bbox']['min'], item['bbox']['max']
    root = R(item, mats, coll)
    box(root, cid + '_canvas', bmin, bmax, coll, mats['wood'], bevel=0.008,
        role='art_abstract')
    # 画上方画灯（收在 bbox 上沿内）
    ym = (bmin[1] + bmax[1]) / 2
    box(root, cid + '_lamp', (bmin[0] + 0.015, ym - 0.3, bmax[2]),
        (bmax[0], ym + 0.3, bmax[2] + 0.06), coll, mats['dark'], role='metal_black')


def _leaf_blade(root, name, cx, cy, z_base, ang, length, width, lean0, lean1,
                coll, mat, role='plant_leaf'):
    """程序化弯曲叶片（REWORK #13 禁方块叶）：自基点向上生长，外倾角 lean0->lean1
    渐变（先直立后外拱，弧度），叶宽向叶尖收窄的锥形曲面。"""
    import bmesh
    n = 6
    mesh = bpy.data.meshes.new(name + '_mesh')
    bm = bmesh.new()
    ca, sa = math.cos(ang), math.sin(ang)
    px, py = -sa, ca   # 叶宽方向
    x, y, z = float(cx), float(cy), float(z_base)
    step = length / n
    rows = []
    for i in range(n + 1):
        t = i / n
        th = lean0 + (lean1 - lean0) * t
        w = width * (1.0 - 0.70 * t) / 2.0
        rows.append((bm.verts.new((x - px * w, y - py * w, z)),
                     bm.verts.new((x + px * w, y + py * w, z))))
        x += ca * math.sin(th) * step
        y += sa * math.sin(th) * step
        z += math.cos(th) * step
    for i in range(n):
        a0, a1 = rows[i]
        b0, b1 = rows[i + 1]
        bm.faces.new((a0, a1, b1, b0))
    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()
    o = bpy.data.objects.new(name, mesh)
    if mat is not None:
        o.data.materials.append(mat)
    o['role'] = role
    coll.objects.link(o)
    if root is not None:
        o.parent = root
    return o


def _seg_means(a, b, n=6):
    """_leaf_blade 折线的分段位移均值：段 k 用起点处 th（与几何一致）。"""
    cs = ss = 0.0
    for i in range(n):
        th = a + (b - a) * (i / n)
        cs += math.cos(th)
        ss += math.sin(th)
    return cs / n, ss / n


def _blade_fit(base, tip_z, rho, lean0):
    """解叶片长度与末端外倾角：叶尖高度=tip_z、水平伸展=rho（迭代收敛）。"""
    lean1 = lean0
    ln = 0.1
    for _ in range(6):
        cs, _s = _seg_means(lean0, lean1)
        ln = max(0.05, (tip_z - base) / max(cs, 1e-3))
        lo, hi = lean0, 1.30
        for _ in range(20):
            mid = (lo + hi) / 2
            _c, s2 = _seg_means(lean0, mid)
            if s2 * ln < rho:
                lo = mid
            else:
                hi = mid
        lean1 = (lo + hi) / 2
    return ln, lean1


def build_plant(item, mats, coll):
    """绿植（REWORK #13：禁方块/黑盒）：茎 + 多片直立微拱弯叶。
    包络是高瘦圆柱（r 0.22-0.24，h 0.8-1.3）：叶长按"叶尖够到包络顶"反解，
    外倾角按"水平伸展够到包络边"反解，既真实又填满 bbox（铁律）。
    端景大盆的盆由 planter item 建；露台小盆栽在这里补一个陶盆。"""
    cid = item['id']
    c = item['center']
    r = item['radius']
    z0 = item.get('z_base', 0.0)
    h = item['height']
    root = R(item, mats, coll)
    big = h >= 1.0
    zb = z0                                    # 叶/茎起始高度
    if cid.startswith('common_terrace_plant'):
        zb = z0 + 0.22
        cyl(root, cid + '_pot', c, r * 0.82, z0, z0 + 0.22, coll,
            mats['wood'], role='plant_pot_brick')
    cyl(root, cid + '_stem', c, 0.02, zb + 0.004, zb + (h - (zb - z0)) * (0.55 if big else 0.40),
        coll, mats['wood'], role='plant_stem')
    n = 8 if big else 6
    top = z0 + h - 0.02
    rho = r - 0.008                     # 水平伸展目标：贴包络边、留 8mm 不出界
    for i in range(n):
        # 12° 起排：保证有叶片正对 ±X/±Y 四个方向（贴边检查）
        ang = math.radians(360.0 / n * i + 12)
        base = zb + 0.02 + (0.05 * (h - (zb - z0)) if i % 2 else 0.0)
        tip_z = top - (top - base) * 0.12 * (i / max(1, n - 1))
        w = (0.16 if big else 0.11) * (1.0 - 0.10 * (i % 3))
        lean0 = 0.03 + 0.05 * (i / max(1, n - 1))
        ln, lean1 = _blade_fit(base, tip_z, rho, lean0)
        _leaf_blade(root, '%s_leaf%d' % (cid, i), c[0], c[1], base, ang,
                    ln, w, lean0, lean1, coll, mats['dark'], role='plant_leaf')


def build_planter(item, mats, coll):
    cid = item['id']
    c = item['center']
    r = item['radius']
    z0 = item.get('z_base', 0.0)
    root = R(item, mats, coll)
    # 端景砖红釉陶盆（规格 5.1，REWORK 2.4 陶盆禁木色）
    cyl(root, cid + '_pot', c, r * 0.98, z0, z0 + item['height'], coll,
        mats['wood'], role='plant_pot_brick')


def build_rug(item, mats, coll):
    cid = item['id']
    room = item.get('room', '')
    # REWORK 4.1：rug_A→rug_geo、孩子房→点缀纹、其余→rug_plain
    if item.get('group') == 'A' and room == 'living_dining_balcony':
        role = 'rug_a'
    elif room in ('daughter_room', 'son_room'):
        role = 'kids_rug'
    else:
        role = 'rug'
    bmin, bmax = item['bbox']['min'], item['bbox']['max']
    root = R(item, mats, coll)
    box(root, cid + '_pile', bmin, bmax, coll, mats['wood'], role=role)
    # F6：A 方案地毯加一圈 3cm 深燕麦边（rug_plain BFAE92，几何边框不占纹理面积）
    if role == 'rug_a':
        bw = 0.03
        z0, z1 = bmin[2], bmax[2] + 0.002
        borders = [
            ((bmin[0], bmin[1]), (bmin[0] + bw, bmax[1])),             # 南边
            ((bmax[0] - bw, bmin[1]), (bmax[0], bmax[1])),             # 北边
            ((bmin[0] + bw, bmin[1]), (bmax[0] - bw, bmin[1] + bw)),   # 西边
            ((bmin[0] + bw, bmax[1] - bw), (bmax[0] - bw, bmax[1])),   # 东边
        ]
        for i, ((x0, y0), (x1, y1)) in enumerate(borders):
            box(root, '%s_border%d' % (cid, i), (x0, y0, z0), (x1, y1, z1),
                coll, mats['white'], role='rug')


def build_cushion(item, mats, coll):
    """飘窗软垫（靠枕另加两枚：墨绿/砖红，规格 5.9）。"""
    cid = item['id']
    bmin, bmax = item['bbox']['min'], item['bbox']['max']
    root = R(item, mats, coll)
    box(root, cid + '_pad', bmin, bmax, coll, mats['white'], bevel=0.03,
        role='fabric_oat')
    box(root, cid + '_pil_olive', (bmin[0] + 0.15, bmax[1] - 0.34, bmax[2]),
        (bmin[0] + 0.52, bmax[1] - 0.05, bmax[2] + 0.24), coll, mats['dark'],
        bevel=0.06, role='pillow_olive')
    box(root, cid + '_pil_brick', (bmax[0] - 0.52, bmax[1] - 0.34, bmax[2]),
        (bmax[0] - 0.15, bmax[1] - 0.05, bmax[2] + 0.24), coll, mats['wood'],
        bevel=0.06, role='pillow_brick')


def build_bay_seat_cover(item, mats, coll):
    build_rug(item, mats, coll)


def build_screen_fallback(item, mats, coll):
    B.BUILDERS['screen'](item, mats, coll)


def build_nightstand(item, mats, coll):
    """床头柜：箱体 + 单抽屉面板 + 短腿。"""
    cid = item['id']
    bmin, bmax = item['bbox']['min'], item['bbox']['max']
    root = R(item, mats, coll)
    box(root, cid + '_body', (bmin[0], bmin[1], 0.10), (bmax[0], bmax[1], bmax[2] - 0.02),
        coll, mats['wood'], role='wood')
    axis, face, inward = B._front_plane(bmin, bmax, item.get('room'))
    a0, a1 = (bmin[1], bmax[1]) if axis == 'x' else (bmin[0], bmax[0])
    B.add_fronts(root, cid, coll, mats['wood'], axis, face, inward, a0, a1,
                 0.12, bmax[2] - 0.06, 'drw', max_w=0.5, pulls=True,
                 pull_mat=mats['dark'], role='wood')
    legs(root, cid, (bmin[0], bmin[1], 0.0), (bmax[0], bmax[1], 0.10), coll,
         mats['wood'], h=0.10, s=0.03, inset=0.05, role='wood')


def build_dressing_table(item, mats, coll):
    """主卧一体梳妆台：胡桃木台面 + 侧板 + 奶白小吊柜(parts) + 镜子。
    FINAL1 F4：旧版 side0/side1 立在 x 两端（贴墙面 + 朝房正面），把台面下正面
    封死（13 号看不到容膝空腔）；中横板 _shelf 也挡膝。现侧板移到 y 两端，
    删中横板，台面下挂 0.08m 薄抽屉（容膝净高 ≥0.62 硬门槛优先于工单 0.12，
    偏差记 qa_final1）。本轮不改材质（D1 处理）。"""
    cid = item['id']
    bmin, bmax = item['bbox']['min'], item['bbox']['max']
    root = R(item, mats, coll)
    x0, y0 = bmin[0], bmin[1]
    x1, y1 = bmax[0], bmax[1]
    box(root, cid + '_top', (x0, y0, 0.70), (x1, y1, 0.75), coll, mats['wood'],
        bevel=0.01, role='wood')
    box(root, cid + '_side0', (x0, y0, 0.0), (x1, y0 + 0.04, 0.70),
        coll, mats['wood'], role='wood')
    box(root, cid + '_side1', (x0, y1 - 0.04, 0.0), (x1, y1, 0.70),
        coll, mats['wood'], role='wood')
    # 薄抽屉：体 + 东侧前脸 + 120mm 短拉手（容膝空腔 y 0.92 / z 0.62）
    box(root, cid + '_drw', (x0 + 0.03, y0 + 0.05, 0.62), (x1 - 0.025, y1 - 0.05, 0.70),
        coll, mats['wood'], role='wood')
    B.add_fronts(root, cid + 'drw', coll, mats['wood'], 'x', x1 - 0.005, -1,
                 y0 + 0.05, y1 - 0.05, 0.625, 0.695, 'drw', max_w=0.5,
                 pulls=True, pull_len=0.12, pull_mat=mats['dark'], role='wood')
    for p in item.get('parts', []):
        pb = p['bbox']
        # R2FIX M1-0：吊柜体前脸缩到门板内皮（原 body 前皮盖门板 5mm）
        box(root, cid + '_upper', (pb['min'][0], pb['min'][1], pb['min'][2]),
            (pb['max'][0] - 0.025, pb['max'][1], pb['max'][2]), coll,
            mats['white'], role='cabinet_box')
        B.add_fronts(root, cid, coll, mats['white'], 'x', pb['max'][0] - 0.005, -1,
                     pb['min'][1], pb['max'][1], pb['min'][2] + 0.02,
                     pb['max'][2] - 0.02, 'door', max_w=0.35, framed=True,
                     pulls=True, pull_mat=mats['dark'], role='cabinet_front')
    # 镜子（台面与吊柜之间，贴墙）
    box(root, cid + '_mirror', (x0 + 0.01, (y0 + y1) / 2 - 0.28, 0.85),
        (x0 + 0.035, (y0 + y1) / 2 + 0.28, 1.35), coll, mats['mirror'],
        role='mirror')


# ---------------------------------------------------------------- 分发
BUILDERS = {
    'bed': build_bed,
    'headboard': build_headboard,
    'sofa': build_sofa,
    'ottoman': build_ottoman,
    'island': build_dining_table,   # _02 餐桌/长桌
    'desk': build_desk,
    'coffee_table': build_coffee_table,
    'side_table': build_side_table,
    'dining_chair': build_dining_chair,
    'chair': build_chair,
    'lounge_chair': build_lounge_chair,
    'wardrobe': build_wardrobe_kids,
    'shelf': build_shelf,
    'stool': build_stool,
    'pendant_lamp': build_pendant_lamp,
    'floor_lamp': build_floor_lamp,
    'tv': build_tv,
    'artwork': build_artwork,
    'plant': build_plant,
    'planter': build_planter,
    'rug': build_rug,
    'cushion': build_cushion,
    'nightstand': build_nightstand,
    'dressing_table': build_dressing_table,
}


def scheme_coll(item, colls):
    g = item.get('group', 'common')
    if g == 'A':
        return colls['scheme_a']
    if g == 'B':
        return colls['scheme_b']
    return colls['common']


# ---------------------------------------------------------------- 规格补充软装（layout 外，规格 5/4.3 要求）
def pleated_panel(name, u0, u1, v, z0, z1, amp, period, coll, mat, axis='x',
                  role='curtain_sheer'):
    """正弦褶皱帘体（规格 7.3：手工褶皱）。axis='x' 帘沿 X 展开、法向 Y。"""
    import bmesh
    n = max(8, int((u1 - u0) / period * 8))
    mesh = bpy.data.meshes.new(name + '_mesh')
    bm = bmesh.new()
    rows = []
    for row in (0, 1):
        verts = []
        for i in range(n + 1):
            u = u0 + (u1 - u0) * i / n
            w = math.sin((u - u0) / period * 2 * math.pi) * amp
            z = z0 if row == 0 else z1
            if axis == 'x':
                verts.append(bm.verts.new((u, v + w, z)))
            else:
                verts.append(bm.verts.new((v + w, u, z)))
        rows.append(verts)
    for i in range(n):
        try:
            bm.faces.new((rows[0][i], rows[0][i + 1], rows[1][i + 1], rows[1][i]))
        except ValueError:
            pass
    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()
    o = bpy.data.objects.new(name, mesh)
    if mat is not None:
        o.data.materials.append(mat)
    o['role'] = role
    coll.objects.link(o)
    return o


def assign_scheme(obj, group):
    """REWORK 4.2：fx_ 软装/灯光按所属方案挂集合（A/B/公共）。
    group: 'A'|'B'|'common'。返回 obj 方便链式调用。"""
    coll_name = {'A': config.COL_SCHEME_A, 'B': config.COL_SCHEME_B}.get(group, config.COL_COMMON)
    coll = bpy.data.collections.get(coll_name)
    if coll is not None and obj is not None:
        for c in list(obj.users_collection):
            c.objects.unlink(obj)
        coll.objects.link(obj)
    return obj


def _fx_curtains(mats, colls):
    """窗帘（REWORK #2：窗帘按所在方案挂对应集合）。"""
    c = colls['common']
    sheer, blackout = mats['glass'], mats['white']
    # 客餐厅南窗（W18 x3.5..9.1）：纱帘拉 2/3（西侧），遮光帘收两侧（A/B 方案各一份）
    for grp in ('A', 'B'):
        cc = colls['scheme_a' if grp == 'A' else 'scheme_b']
        pleated_panel('fx_curt_living_sheer_%s' % grp, 3.5, 7.1, -11.44, 0.55, 2.45,
                      0.035, 0.16, cc, sheer)
        pleated_panel('fx_curt_living_bo_w_%s' % grp, 3.5, 4.3, -11.36, 0.55, 2.45,
                      0.05, 0.14, cc, blackout, role='curtain_blackout')
        pleated_panel('fx_curt_living_bo_e_%s' % grp, 8.3, 9.1, -11.36, 0.55, 2.45,
                      0.05, 0.14, cc, blackout, role='curtain_blackout')
    # 主卧落地门窗（W17 x9.6..12.4）：纱帘全幅 + 遮光帘两侧
    # FINAL1 F7：帘顶 2.28 -> 2.38 —— 原帘顶低于玻璃门顶（玻璃芯顶 2.355），
    # 露出 7.5cm 未遮挡玻璃带，太阳（玻璃关阴影）从带内直穿，在床头东墙投出
    # 斜光带（diag_f7 探针 GLASS 光路链证实）；帘装门头(2.40)下沿为真实做法。
    pleated_panel('fx_curt_master_sheer', 9.6, 12.4, -10.30, 0.02, 2.38, 0.035, 0.16, c, sheer)
    pleated_panel('fx_curt_master_bo_w', 9.6, 10.3, -10.22, 0.02, 2.38, 0.05, 0.14,
                  c, blackout, role='curtain_blackout')
    pleated_panel('fx_curt_master_bo_e', 11.7, 12.4, -10.22, 0.02, 2.38, 0.05, 0.14,
                  c, blackout, role='curtain_blackout')
    # 父母房飘窗（W23 x0.55..2.95）：纱帘 + 卷帘箱
    # R2 #20：帘改窗洞内挂——x 收进两端矮书格之间（0.85..2.65），底边离坐榻面 2cm（0.47），
    # 不再横穿坐榻与书格
    pleated_panel('fx_curt_parents_sheer', 0.85, 2.65, -10.36, 0.47, 2.28, 0.03, 0.14, c, sheer)
    box(None, 'fx_curt_parents_roller', (0.85, -10.40, 2.28), (2.65, -10.34, 2.36),
        c, mats['white'], role='cabinet_white')
    # 孩子房北窗（W01/W06）：双层帘（REWORK 2.3 女儿房遮光帘带雾粉）
    pleated_panel('fx_curt_daughter_sheer', 6.55, 8.75, -0.32, 0.92, 2.36, 0.03, 0.14,
                  c, sheer)
    pleated_panel('fx_curt_daughter_bo_w', 6.55, 7.2, -0.24, 0.92, 2.36, 0.05, 0.13,
                  c, blackout, role='curtain_daughter')
    pleated_panel('fx_curt_daughter_bo_e', 8.1, 8.75, -0.24, 0.92, 2.36, 0.05, 0.13,
                  c, blackout, role='curtain_daughter')
    pleated_panel('fx_curt_son_sheer', 11.45, 12.95, -0.32, 0.92, 2.26, 0.03, 0.14, c, sheer)
    pleated_panel('fx_curt_son_bo_w', 11.45, 12.0, -0.24, 0.92, 2.26, 0.05, 0.13,
                  c, blackout, role='curtain_blackout')
    pleated_panel('fx_curt_son_bo_e', 12.4, 12.95, -0.24, 0.92, 2.26, 0.05, 0.13,
                  c, blackout, role='curtain_blackout')
    # 主卫窗（W10 y-4.9..-3.8，sill 1.2 / head 2.2）：防水百叶帘放下 1/3。
    # FINAL1 F6：旧版 9 片 z=0.8+i*0.12 覆 0.80-1.95，叶片压到窗台以下、占窗下 2/3。
    # 现叶片只占窗洞上 1/3（约 1.87-2.16，6 片、片高 0.04、节距 0.05），y 收进
    # 窗洞内 2cm，顶部 4cm 帘头盒；x 保持在 W10 reveal 内。
    box(None, 'fx_blind_mb_head', (13.574, -4.88, 2.16), (13.586, -3.82, 2.20),
        c, mats['white'], role='blind')
    for i in range(6):
        box(None, 'fx_blind_mb_slats%d' % i, (13.574, -4.88, 1.87 + i * 0.05),
            (13.586, -3.82, 1.91 + i * 0.05), c, mats['white'], role='blind')


def _fx_lights(mats, coll, ceil_coll=None):
    c = coll
    ceil = ceil_coll if ceil_coll is not None else c
    # 卧室吸顶灯（薄款乳白）——R2 #16：顶面安装件入 COL_CEILINGS（鸟瞰藏顶不悬浮）
    for rid, (cx, cy) in {'master_bedroom': (11.0, -7.7), 'parents_room': (1.75, -8.3),
                          'daughter_room': (7.65, -2.05), 'son_room': (12.2, -1.8)}.items():
        cyl(None, 'fx_ceiling_%s' % rid, (cx, cy), 0.24, 2.79, 2.85, ceil,
            mats['glass'], role='opal_glass')
    # 客餐厅边吊筒灯（底面 2.60，间距约 1.1，避开东带出风口）
    spots = []
    for x in (4.3, 5.4, 6.5, 7.6, 8.4):
        spots += [(x, -11.35), (x, -4.20)]
    for y in (-10.2, -9.1, -6.8, -5.6):
        spots += [(3.57, y)]
    for y in (-10.9, -6.9, -5.6):
        spots += [(9.02, y)]
    for i, (x, y) in enumerate(spots):
        cyl(None, 'fx_spot_living%02d' % i, (x, y), 0.0375, 2.575, 2.60, ceil,
            mats['glass'], role='spot_glass')
        cyl(None, 'fx_spot_living%02d_r' % i, (x, y), 0.05, 2.60, 2.615, ceil,
            mats['white'], role='spot_ring')
    # 卧室/过道筒灯
    for i, (x, y, z) in enumerate([(11.0, -8.8, 2.85), (11.0, -6.6, 2.85),
                                   (1.75, -9.5, 2.85), (7.65, -3.0, 2.85),
                                   (12.2, -2.9, 2.85), (9.9, -4.4, 2.60),
                                   (10.6, -3.0, 2.60), (2.7, -5.7, 2.85)]):
        cyl(None, 'fx_spot_room%d' % i, (x, y), 0.0375, z - 0.025, z, ceil,
            mats['glass'], role='spot_glass')
    # 床头壁灯（主卧两侧 + 父母房床头）
    for i, (x, y) in enumerate([(12.68, -7.0), (12.68, -9.2), (0.24, -8.65)]):
        box(None, 'fx_wall_lamp%d' % i, (x - 0.02 if x > 6 else x, y - 0.09, 1.35),
            (x + 0.06 if x > 6 else x + 0.08, y + 0.09, 1.55), c, mats['dark'],
            role='metal_black')
        cyl(None, 'fx_wall_lamp%d_sh' % i, (x + (0.12 if x > 6 else -0.12), y), 0.06,
            1.32, 1.50, c, mats['glass'], role='opal_glass')


def _shelf_tops(niche_id):
    """FINAL1 F9：读开放格层板顶面 z（builtins.build_open_niche 写入 root 的
    自定义属性）。缺属性即 raise——摆件坐标禁止再硬编码。"""
    r = bpy.data.objects.get(niche_id)
    ts = r.get('shelf_top_zs') if r is not None else None
    if not ts:
        raise RuntimeError('[furniture] shelf_top_zs missing on %s' % niche_id)
    return [float(z) for z in ts]


def _fx_props(mats, colls):
    """摆件（REWORK #2：B 整墙柜开放格摆件挂 SCHEME_B；#18 香草盆归位台面）。
    FINAL1 F9：开放格摆件底面 z 一律由 _shelf_tops 从层板顶面计算，
    不再硬编码（旧版 B 格 1.06/0.94/1.10 vs 实际层板顶 0.98/1.33，悬空+穿插）。"""
    c = colls['common']
    # 玄关端景格：乳白陶罐 + 小画（art_abstract）——底面落在层板顶 0.98
    ftop = _shelf_tops('common_foyer_open_niche_01')[0]
    sph(None, 'fx_foyer_jar', (2.55, -6.48, ftop + 0.09), 0.09, c, mats['white'],
        role='vase_white')
    box(None, 'fx_foyer_pic', (2.95, -6.56, ftop), (3.15, -6.52, ftop + 0.22), c,
        mats['wood'], role='art_abstract')
    # 厨房台面：砧板 + 油壶 + 香草盆（规格 5.4；REWORK #18 归位到北台面）
    box(None, 'fx_kn_board', (5.0, -1.62, 0.9), (5.6, -1.42, 0.918), c,
        mats['wood'], bevel=0.006, role='wood')
    cyl(None, 'fx_kn_oil', (5.85, -1.55), 0.045, 0.9, 1.08, c, mats['dark'],
        role='metal_black')
    cyl(None, 'fx_kn_herb', (6.05, -1.55), 0.07, 0.9, 1.02, c, mats['white'],
        role='vase_white')
    _leaf_blade(None, 'fx_kn_herb_leaf1', 6.05, -1.55, 1.02, math.radians(20),
                0.12, 0.03, 0.15, 0.90, c, mats['dark'], role='plant_leaf')
    _leaf_blade(None, 'fx_kn_herb_leaf2', 6.05, -1.55, 1.02, math.radians(160),
                0.12, 0.03, 0.15, 0.90, c, mats['dark'], role='plant_leaf')
    # 岛台台面：托盘
    box(None, 'fx_island_tray', (4.7, -5.6, 0.9), (5.1, -5.2, 0.915), c,
        mats['wood'], bevel=0.006, role='wood')
    # R2FIX2 N1：西墙实木组合柜真腔摆件（与 builtins.build_bookcase 新腔体配对）。
    # 开放格内净空 x 3.44..3.77 / y -9.84..-9.265，层板面 z=0.47/0.85/1.21/1.57/1.93；
    # 书+陶罐+唱片+小相框，每层 1-2 组留白。玻璃展示柜内 y -10.355..-9.89，
    # 层板面 z=0.47/1.17/1.71。
    spine_roles = ('fabric_oat', 'leather_caramel', 'fabric_olive', 'pillow_brick')
    # — 开放格 L0（z0.47）：书组 5 直立 + 2 平放
    for k in range(5):
        bh = 0.20 + 0.02 * (k % 3)
        yy = -9.72 + k * 0.034
        box(None, 'fx_bc_b0_%d' % k, (3.50, yy, 0.47), (3.70, yy + 0.034, 0.47 + bh),
            c, mats['white'], role=spine_roles[k % 4])
    for k in range(2):
        box(None, 'fx_bc_b0f_%d' % k, (3.52, -9.55 + k * 0.014, 0.47 + 0.24 + k * 0.034),
            (3.68, -9.32 - k * 0.02, 0.47 + 0.24 + (k + 1) * 0.034), c,
            mats['white'], role=spine_roles[(k + 1) % 4])
    # — 开放格 L1（z0.85）：砖红陶罐（三段旋转体）+ 小相框
    cyl(None, 'fx_bc_pot', (3.62, -9.60), 0.075, 0.85, 0.99, c, mats['white'],
        verts=20, role='ceramic_brick')
    cyl(None, 'fx_bc_potneck', (3.62, -9.60), 0.040, 0.99, 1.075, c, mats['white'],
        verts=20, role='ceramic_brick')
    cyl(None, 'fx_bc_potlip', (3.62, -9.60), 0.055, 1.075, 1.098, c, mats['white'],
        verts=20, role='ceramic_brick')
    box(None, 'fx_bc_frame', (3.50, -9.44, 0.85), (3.66, -9.422, 1.07), c,
        mats['dark'], role='metal_black')
    box(None, 'fx_bc_framein', (3.506, -9.416, 0.886), (3.654, -9.410, 1.034), c,
        mats['white'], role='fabric_oat')
    # — 开放格 L2（z1.21）：唱片立盘 x3 + 支架（盘心 1.335 = 支架面 1.235 + 半径 0.10）
    for k in range(3):
        d = cyl(None, 'fx_bc_rec%d' % k, (3.62, -9.68 + k * 0.05), 0.10, 1.332, 1.338,
                c, mats['dark'], verts=24, role='metal_black')
        d.rotation_euler = (0.0, math.radians(90), 0.0)
    box(None, 'fx_bc_recstand', (3.50, -9.74, 1.21), (3.74, -9.52, 1.235), c,
        mats['white'], role='wood')
    # — 开放格 L3（z1.57）：小书组 3 本 + 乳白小球罐
    for k in range(3):
        bh = 0.19 + 0.015 * (k % 2)
        yy = -9.56 + k * 0.034
        box(None, 'fx_bc_b3_%d' % k, (3.52, yy, 1.57), (3.70, yy + 0.034, 1.57 + bh),
            c, mats['white'], role=spine_roles[(k + 2) % 4])
    sph(None, 'fx_bc_jar3', (3.62, -9.38, 1.655), 0.055, c, mats['white'],
        role='vase_white')
    # — 开放格 L4（z1.93）：留白 + 小白罐
    cyl(None, 'fx_bc_pot4', (3.62, -9.66), 0.045, 1.93, 2.045, c, mats['white'],
        verts=20, role='vase_white')
    # — 玻璃展示柜内（透过清玻璃可见）：底层书堆+小罐 / 中层书排 / 顶层陶罐
    for k in range(3):
        box(None, 'fx_bc_g0_%d' % k, (3.50, -10.26 + k * 0.05, 0.47),
            (3.70, -10.06 + k * 0.05, 0.47 + 0.05), c, mats['white'],
            role=spine_roles[k % 4])
    cyl(None, 'fx_bc_gpot', (3.62, -9.95, 0.47), 0.05, 0.47, 0.60, c, mats['white'],
        verts=20, role='vase_white')
    for k in range(4):
        bh = 0.19 + 0.02 * (k % 3)
        yy = -10.24 + k * 0.034
        box(None, 'fx_bc_g1_%d' % k, (3.50, yy, 1.17), (3.70, yy + 0.034, 1.17 + bh),
            c, mats['white'], role=spine_roles[(k + 1) % 4])
    cyl(None, 'fx_bc_gpot2', (3.60, -10.10, 1.71), 0.055, 1.71, 1.83, c, mats['white'],
        verts=20, role='ceramic_brick')
    # B 整墙柜开放格：书 + 孩子作品（REWORK #2 → SCHEME_B）
    cb = colls['scheme_b']
    # R2FIX m1 + FINAL1 F9：B 开放格摆件重做——彩色方块换成可辨识物件：
    # 书组（3-6 本/组、高矮不一、低饱和书脊、部分平放叠置）/ 陶罐 / 唱片+支架，
    # 每格 1-3 组留白。书脊色即四种点缀/软装低饱和色（role 复用）。
    # z 全部由层板顶面推导：下层 z0=tops[0]（净空到上层板底），
    # 上层 tops[1] 净空仅 ~0.15m，只放平放唱片/小罐。
    bt = _shelf_tops('B_living_dining_balcony_open_niche_01')   # [0.98, 1.33]
    z0 = bt[0]
    spine_roles = ('fabric_oat', 'leather_caramel', 'fabric_olive', 'pillow_brick')
    shelf_y = (-9.9, -9.3, -8.7, -8.1, -7.5, -6.9, -6.3, -5.8)
    for i, y in enumerate(shelf_y):
        kind = i % 3
        if kind == 0:                       # 书组：5 本直立 + 顶上 2 本平放
            nb = 5
            th = 0.032
            for k in range(nb):
                bh = 0.20 + 0.02 * ((i + k) % 3)
                yy = y - 0.12 + k * th
                box(None, 'fx_Bs%d_b%d' % (i, k), (8.99, yy, z0),
                    (9.15, yy + th, z0 + bh), cb, mats['white'],
                    role=spine_roles[(i + k) % 4])
            for k in range(2):              # 平放叠置
                box(None, 'fx_Bs%d_f%d' % (i, k),
                    (8.99, y - 0.10 + k * 0.012, z0 + 0.24 + k * 0.032),
                    (9.15, y + 0.12 - k * 0.02, z0 + 0.24 + (k + 1) * 0.032), cb,
                    mats['white'], role=spine_roles[(i + k + 1) % 4])
        elif kind == 1:                     # 陶罐（旋转体：罐身+颈+沿口）
            pot = 'ceramic_brick' if i % 2 else 'vase_white'
            cyl(None, 'fx_Bs%d_pot' % i, (9.075, y), 0.085, z0, z0 + 0.16, cb,
                mats['white'], verts=20, role=pot)
            cyl(None, 'fx_Bs%d_neck' % i, (9.075, y), 0.045, z0 + 0.16, z0 + 0.26, cb,
                mats['white'], verts=20, role=pot)
            cyl(None, 'fx_Bs%d_lip' % i, (9.075, y), 0.062, z0 + 0.26, z0 + 0.285, cb,
                mats['white'], verts=20, role=pot)
        else:                               # 唱片：立放圆盘 x3 + 小支架
            box(None, 'fx_Bs%d_recstand' % i, (8.99, y - 0.10, z0),
                (9.15, y + 0.10, z0 + 0.025), cb, mats['wood'], role='wood')
            for k in range(3):
                zc = z0 + 0.025 + 0.102
                d = cyl(None, 'fx_Bs%d_rec%d' % (i, k), (9.075, y - 0.05 + k * 0.05),
                        0.10, zc - 0.003, zc + 0.003, cb, mats['dark'], verts=24,
                        role='metal_black')
                d.rotation_euler = (0.0, math.radians(90), 0.0)
    # 上层（tops[1] 净空 ~0.15m）：平放唱片 + 乳白小罐，3 处留白式点缀
    for j, y in enumerate((-9.3, -7.5, -6.3)):
        d = cyl(None, 'fx_Bu_rec%d' % j, (9.075, y), 0.10, bt[1], bt[1] + 0.012, cb,
                mats['dark'], verts=24, role='metal_black')
        sph(None, 'fx_Bu_jar%d' % j, (9.075, y + 0.14, bt[1] + 0.05), 0.05, cb,
            mats['white'], role='vase_white')
    # 主卧书桌上方开放格：书 + 小件（落层板顶）
    mt = _shelf_tops('common_master_bedroom_open_niche_01')   # [1.38, 1.73, 2.08]
    for i, y in enumerate((-6.3, -5.8)):
        box(None, 'fx_desk_book%d' % i, (12.46, y - 0.1, mt[i]),
            (12.66, y + 0.1, mt[i] + 0.24), c, mats['white' if i % 2 else 'wood'],
            role='book')
    # 琴叶榕（规格 5.1；REWORK #13 弯曲叶）
    cyl(None, 'fx_fiddle_pot', (3.75, -11.15), 0.19, 0.0, 0.38, c, mats['wood'],
        role='plant_pot_brick')
    cyl(None, 'fx_fiddle_stem', (3.75, -11.15), 0.02, 0.38, 1.05, c, mats['wood'],
        role='plant_stem')
    for i in range(7):
        ang = math.radians(50 * i + 10)
        _leaf_blade(None, 'fx_fiddle_leaf%d' % i, 3.75, -11.15, 0.70 + 0.055 * i,
                    ang, 0.30, 0.13, 0.12, 0.75, c, mats['dark'], role='plant_leaf')


def build_extras(mats, colls):
    """规格补充软装：窗帘、吸顶灯/筒灯/壁灯几何、摆件、琴叶榕。
    REWORK #2：fx_ 对象按所属方案/房间挂对应集合。"""
    _fx_curtains(mats, colls)
    _fx_lights(mats, colls['common'], colls.get('ceilings'))
    _fx_props(mats, colls)
    print('[furniture] extras done')


def build_all(mats, colls):
    built, skipped = [], []
    for item in util.load_layout()['items']:
        typ = item.get('type')
        iid = item['id']
        if bpy.data.objects.get(iid) is not None:
            continue  # M2 已建（含 covered）
        if typ in ('marker', 'wall_finish'):
            skipped.append(iid)  # wall_finish -> M4 材质阶段
            continue
        fn = BUILDERS.get(typ)
        if fn is None:
            skipped.append('%s(%s)' % (iid, typ))
            continue
        fn(item, mats, scheme_coll(item, colls))
        built.append(iid)
    print('[furniture] built=%d skipped=%d' % (len(built), len(skipped)))
    return built, skipped

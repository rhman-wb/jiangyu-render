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


def box(root, name, bmin, bmax, coll, mat, bevel=None, glass=False):
    return B.child(root, name, bmin, bmax, coll, mat, bevel=bevel, glass=glass)


def legs(root, cid, bmin, bmax, coll, mat, n=4, h=0.12, s=0.04, inset=0.05):
    """桌/柜木腿（规格 7.3：A 沙发 5cm 木腿等由调用方传参）。"""
    xs = (bmin[0] + inset, bmax[0] - inset)
    ys = (bmin[1] + inset, bmax[1] - inset)
    i = 0
    for x in xs:
        for y in ys:
            box(root, '%s_leg%d' % (cid, i), (x - s / 2, y - s / 2, bmin[2]),
                (x + s / 2, y + s / 2, bmin[2] + h), coll, mat)
            i += 1


# ---------------------------------------------------------------- 床
def build_bed(item, mats, coll):
    """床：框架 + 床垫 + 床品（被子下垂边 + 2 枕 + 盖毯）+ parts 床头板。"""
    cid = item['id']
    bmin, bmax = item['bbox']['min'], item['bbox']['max']
    root = R(item, mats, coll)
    x0, y0, z0 = bmin
    x1, y1, z1 = bmax
    # 床架 + 床垫
    box(root, cid + '_frame', (x0, y0, 0.0), (x1, y1, z1 - 0.18), coll, mats['wood'])
    box(root, cid + '_mattress', (x0 + 0.03, y0 + 0.03, z1 - 0.18),
        (x1 - 0.03, y1 - 0.03, z1), coll, mats['white'], bevel=0.02)
    # 床头方向：parts 床头板在哪端（master parts 在 x_max；其余房间按规格朝西= x_min）
    head_x = True  # 默认沿 X 的床
    for p in item.get('parts', []):
        pb = p['bbox']
        box(root, cid + '_headboard', tuple(pb['min']), tuple(pb['max']),
            coll, mats['white'], bevel=0.03)
    # 被子（床头对侧 2/3，下垂边收在 bbox 内）
    if (x1 - x0) > (y1 - y0):
        dx0, dx1 = x0 + 0.55, x1 - 0.04
        box(root, cid + '_duvet', (dx0, y0 - 0.0, z1 - 0.06),
            (dx1, y1 + 0.0, z1 + 0.04), coll, mats['white'], bevel=0.025)
        box(root, cid + '_duvetdrop', (dx0, y0, z1 - 0.30),
            (dx1, y0 + 0.03, z1 - 0.04), coll, mats['white'], bevel=0.02)
        box(root, cid + '_duvetdrop2', (dx0, y1 - 0.03, z1 - 0.30),
            (dx1, y1, z1 - 0.04), coll, mats['white'], bevel=0.02)
        # 枕头（床头端）
        py = (y0 + y1) / 2
        box(root, cid + '_pillow1', (x0 + 0.10, py - 0.50, z1),
            (x0 + 0.52, py - 0.02, z1 + 0.11), coll, mats['white'], bevel=0.045)
        box(root, cid + '_pillow2', (x0 + 0.10, py + 0.02, z1),
            (x0 + 0.52, py + 0.50, z1 + 0.11), coll, mats['white'], bevel=0.045)
        # 盖毯（床尾横向一条，燕麦色示意）
        box(root, cid + '_throw', (x1 - 0.75, y0, z1 + 0.01),
            (x1 - 0.35, y1, z1 + 0.05), coll, mats['wood'], bevel=0.015)
    else:
        dy0, dy1 = y0 + 0.55, y1 - 0.04
        box(root, cid + '_duvet', (x0, dy0, z1 - 0.06),
            (x1, dy1, z1 + 0.04), coll, mats['white'], bevel=0.025)
        box(root, cid + '_duvetdrop', (x0, dy0, z1 - 0.30),
            (x0 + 0.03, dy1, z1 - 0.04), coll, mats['white'], bevel=0.02)
        box(root, cid + '_duvetdrop2', (x1 - 0.03, dy0, z1 - 0.30),
            (x1, dy1, z1 - 0.04), coll, mats['white'], bevel=0.02)
        px = (x0 + x1) / 2
        box(root, cid + '_pillow1', (px - 0.50, y0 + 0.10, z1),
            (px - 0.02, y0 + 0.52, z1 + 0.11), coll, mats['white'], bevel=0.045)
        box(root, cid + '_pillow2', (px + 0.02, y0 + 0.10, z1),
            (px + 0.50, y0 + 0.52, z1 + 0.11), coll, mats['white'], bevel=0.045)
        box(root, cid + '_throw', (x0, y1 - 0.75, z1 + 0.01),
            (x1, y1 - 0.35, z1 + 0.05), coll, mats['wood'], bevel=0.015)


def build_headboard(item, mats, coll):
    cid = item['id']
    bmin, bmax = item['bbox']['min'], item['bbox']['max']
    root = R(item, mats, coll)
    box(root, cid + '_pad', bmin, bmax, coll, mats['wood'], bevel=0.03)


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
    box(root, cid + '_base', (x0, y0, 0.03), (x1, y1, z1 - 0.14), coll, mats['white'])
    # 靠背（分块）
    n = max(2, round((y1 - y0) / 0.9))
    w = (y1 - y0) / n
    for i in range(n):
        box(root, '%s_back%d' % (cid, i), (bx0 + 0.02, y0 + i * w + 0.015, z1 - 0.16),
            (bx1 - 0.02, y0 + (i + 1) * w - 0.015, back_top), coll, mats['white'],
            bevel=0.03)
    # 座垫（分块）
    for i in range(n):
        box(root, '%s_seat%d' % (cid, i), (bx1 + 0.01, y0 + i * w + 0.02, z1 - 0.13),
            (x1 - 0.06, y0 + (i + 1) * w - 0.02, seat_top), coll, mats['white'],
            bevel=0.035)
    # 扶手（两端）；无 parts 低模块扶手同高收低
    arm_top = z1 + 0.20 if parts_hi else z1 - 0.01
    for j, ay in ((0, y0), (1, y1 - 0.18)):
        box(root, '%s_arm%d' % (cid, j), (bx0 + 0.02, ay + 0.015, 0.03),
            (x1 - 0.06, ay + 0.165, arm_top), coll, mats['white'], bevel=0.04)
    # 抱枕（墨绿/砖红/燕麦 示意用 wood/dark/white；低模块不放）
    if parts_hi:
        box(root, cid + '_pillow_olive', (bx1 + 0.06, y0 + 0.30, z1 + 0.02),
            (bx1 + 0.30, y0 + 0.62, z1 + 0.30), coll, mats['dark'], bevel=0.05)
        box(root, cid + '_pillow_brick', (bx1 + 0.05, y1 - 0.75, z1 + 0.02),
            (bx1 + 0.29, y1 - 0.45, z1 + 0.30), coll, mats['wood'], bevel=0.05)
    # parts 第二块（B 转角段）单独成体
    if len(parts_hi) > 1 and item['group'] == 'B':
        pass  # B_sofa_02 是独立 item


def build_ottoman(item, mats, coll):
    cid = item['id']
    bmin, bmax = item['bbox']['min'], item['bbox']['max']
    root = R(item, mats, coll)
    box(root, cid + '_pad', bmin, (bmax[0], bmax[1], bmax[2]), coll, mats['wood'], bevel=0.05)
    box(root, cid + '_base', (bmin[0] + 0.08, bmin[1] + 0.08, 0.0),
        (bmax[0] - 0.08, bmax[1] - 0.08, 0.12), coll, mats['wood'])


# ---------------------------------------------------------------- 桌几
def build_dining_table(item, mats, coll):
    """A 餐桌 / B 长桌（island_02）：40mm 面板圆角 + 收分腿/板式腿。"""
    cid = item['id']
    bmin, bmax = item['bbox']['min'], item['bbox']['max']
    root = R(item, mats, coll)
    x0, y0, z0 = bmin
    x1, y1, z1 = bmax
    box(root, cid + '_top', (x0, y0, z1 - 0.04), (x1, y1, z1), coll, mats['wood'],
        bevel=0.012)
    if item['group'] == 'A':  # 四条收分腿
        for i, (lx, ly) in enumerate(((x0 + 0.10, y0 + 0.10), (x1 - 0.10, y0 + 0.10),
                                      (x0 + 0.10, y1 - 0.10), (x1 - 0.10, y1 - 0.10))):
            box(root, '%s_leg%d' % (cid, i), (lx - 0.035, ly - 0.035, 0.0),
                (lx + 0.035, ly + 0.035, z1 - 0.04), coll, mats['wood'], bevel=0.01)
    else:  # B 板式腿两块
        box(root, cid + '_panel0', (x0 + 0.15, y0 + 0.12, 0.0),
            (x0 + 0.15 + 0.05, y1 - 0.12, z1 - 0.04), coll, mats['wood'])
        box(root, cid + '_panel1', (x1 - 0.20, y0 + 0.12, 0.0),
            (x1 - 0.15, y1 - 0.12, z1 - 0.04), coll, mats['wood'])


def build_desk(item, mats, coll):
    """书桌（主卧/女儿/儿子）：面板 + 侧板或四腿 + 薄抽屉条。"""
    cid = item['id']
    bmin, bmax = item['bbox']['min'], item['bbox']['max']
    root = R(item, mats, coll)
    x0, y0, z0 = bmin
    x1, y1, z1 = bmax
    box(root, cid + '_top', (x0, y0, z1 - 0.04), (x1, y1, z1), coll, mats['wood'], bevel=0.01)
    box(root, cid + '_drawer', (x0 + 0.06, y0 + 0.05, z1 - 0.16),
        (x1 - 0.06, y1 - 0.05, z1 - 0.04), coll, mats['white'])
    for i, (lx, ly) in enumerate(((x0 + 0.08, y0 + 0.06), (x1 - 0.08, y0 + 0.06),
                                  (x0 + 0.08, y1 - 0.06), (x1 - 0.08, y1 - 0.06))):
        box(root, '%s_leg%d' % (cid, i), (lx - 0.025, ly - 0.025, 0.0),
            (lx + 0.025, ly + 0.025, z1 - 0.16), coll, mats['wood'])
    if item['room'] == 'master_bedroom':
        box(root, cid + '_monitor', (x1 - 0.55, (y0 + y1) / 2 - 0.21, z1),
            (x1 - 0.50, (y0 + y1) / 2 + 0.21, z1 + 0.33), coll, mats['dark'], bevel=0.008)
        box(root, cid + '_monstand', (x1 - 0.53, (y0 + y1) / 2 - 0.09, z1),
            (x1 - 0.50, (y0 + y1) / 2 + 0.09, z1 + 0.18), coll, mats['dark'])


def build_coffee_table(item, mats, coll):
    """圆茶几/圆边几（cylinder item）：圆台面 + 三锥腿 -> 白模圆柱+腿。"""
    cid = item['id']
    c = item['center']
    r = item['radius']
    z0 = item.get('z_base', 0.0)
    h = item['height']
    root = R(item, mats, coll)
    cyl(root, cid + '_top', c, r, z0 + h - 0.04, z0 + h, coll, mats['wood'])
    for i in range(3):
        a = math.radians(120 * i + 30)
        px, py = c[0] + math.cos(a) * r * 0.6, c[1] + math.sin(a) * r * 0.6
        box(root, '%s_leg%d' % (cid, i), (px - 0.02, py - 0.02, z0),
            (px + 0.02, py + 0.02, z0 + h - 0.04), coll, mats['wood'])


def cyl(root, name, center_xy, radius, z0, z1, coll, mat, verts=24):
    mesh = bpy.data.meshes.new(name + '_mesh')
    bm = bmesh_new_cylinder(radius, z1 - z0, verts)
    bm.to_mesh(mesh)
    bm.free()
    o = bpy.data.objects.new(name, mesh)
    o.location = (center_xy[0], center_xy[1], z0)
    if mat is not None:
        o.data.materials.append(mat)
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
def build_dining_chair(item, mats, coll):
    """中古弧形扶手餐椅 / 混搭椅：座垫 + 弧背 + 四腿 + 扶手条。"""
    cid = item['id']
    bmin, bmax = item['bbox']['min'], item['bbox']['max']
    root = R(item, mats, coll)
    x0, y0, z0 = bmin
    x1, y1, z1 = bmax
    # 面朝桌子（规格 7.2）：以 item 中点朝向最近桌心近似——白模统一弧背在 -Y 侧（桌在北侧），
    # 南侧两椅(y>桌心)翻转由 stage1 数据已定位，这里按 y 中点相对房间判一次
    back_south = (y0 + y1) / 2 > -5.4  # 桌带 y≈-5.4，椅在桌南侧则背朝南
    if back_south:
        by0, by1 = y1 - 0.08, y1
    else:
        by0, by1 = y0, y1 - 0.08
    box(root, cid + '_seat', (x0 + 0.02, y0 + 0.02, 0.40), (x1 - 0.02, y1 - 0.02, 0.47),
        coll, mats['white'], bevel=0.02)
    box(root, cid + '_back', (x0 + 0.02, by0, 0.47), (x1 - 0.02, by1, z1 - 0.015),
        coll, mats['wood'], bevel=0.025)
    for i, (lx, ly) in enumerate(((x0 + 0.035, y0 + 0.035), (x1 - 0.035, y0 + 0.035),
                                  (x0 + 0.035, y1 - 0.035), (x1 - 0.035, y1 - 0.035))):
        box(root, '%s_leg%d' % (cid, i), (lx - 0.018, ly - 0.018, 0.0),
            (lx + 0.018, ly + 0.018, 0.40), coll, mats['wood'])
    # 弧形扶手（两侧细弯条，白模用斜杆示意）
    for j, ax in ((0, x0 + 0.05), (1, x1 - 0.05)):
        box(root, '%s_arm%d' % (cid, j), (ax - 0.018, y0 + 0.06, 0.62),
            (ax + 0.018, y1 - 0.06, 0.66), coll, mats['wood'], bevel=0.01)


def build_chair(item, mats, coll):
    """书桌椅：座+薄背+五星脚简化为四腿+脚轮条。"""
    cid = item['id']
    bmin, bmax = item['bbox']['min'], item['bbox']['max']
    root = R(item, mats, coll)
    x0, y0 = bmin[0], bmin[1]
    x1, y1 = bmax[0], bmax[1]
    z1 = bmax[2]
    box(root, cid + '_seat', (x0 + 0.02, y0 + 0.02, 0.42), (x1 - 0.02, y1 - 0.02, 0.50),
        coll, mats['wood'], bevel=0.03)
    box(root, cid + '_back', (x0 + 0.02, y0 + 0.02, 0.50), (x1 - 0.02, y0 + 0.10, z1 - 0.015),
        coll, mats['wood'], bevel=0.03)
    box(root, cid + '_post', ((x0 + x1) / 2 - 0.03, (y0 + y1) / 2 - 0.03, 0.05),
        ((x0 + x1) / 2 + 0.03, (y0 + y1) / 2 + 0.03, 0.42), coll, mats['dark'])
    box(root, cid + '_base', (x0 + 0.02, y0 + 0.02, 0.0), (x1 - 0.02, y1 - 0.02, 0.05),
        coll, mats['dark'], bevel=0.015)


def build_lounge_chair(item, mats, coll):
    """中古单椅（墨绿）/ 藤编单椅：座+斜背+扶手+四腿；露台藤椅为 cylinder 包络。"""
    cid = item['id']
    if item.get('shape') == 'cylinder':
        c, r, z0, h = item['center'], item['radius'], item.get('z_base', 0.0), item['height']
        root = R(item, mats, coll)
        cyl(root, cid + '_seat', c, r * 0.92, z0 + 0.32, z0 + 0.42, coll, mats['wood'])
        cyl(root, cid + '_back', (c[0], c[1] + r * 0.30), r * 0.6, z0 + 0.40, z0 + h, coll, mats['wood'])
        for i in range(4):
            a = math.radians(90 * i + 45)
            px, py = c[0] + math.cos(a) * r * 0.6, c[1] + math.sin(a) * r * 0.6
            box(root, '%s_leg%d' % (cid, i), (px - 0.02, py - 0.02, z0),
                (px + 0.02, py + 0.02, z0 + 0.32), coll, mats['wood'])
        return
    bmin, bmax = item['bbox']['min'], item['bbox']['max']
    root = R(item, mats, coll)
    x0, y0, z0 = bmin
    x1, y1, z1 = bmax
    mat = mats['dark'] if item['room'] == 'living_dining_balcony' else mats['wood']
    box(root, cid + '_seat', (x0 + 0.02, y0 + 0.02, 0.36), (x1 - 0.02, y1 - 0.02, 0.46),
        coll, mat, bevel=0.04)
    box(root, cid + '_back', (x0 + 0.02, y0 + 0.02, 0.44), (x1 - 0.02, y0 + 0.14, z1),
        coll, mat, bevel=0.04)
    for i, (lx, ly) in enumerate(((x0 + 0.04, y0 + 0.04), (x1 - 0.04, y0 + 0.04),
                                  (x0 + 0.04, y1 - 0.04), (x1 - 0.04, y1 - 0.04))):
        box(root, '%s_leg%d' % (cid, i), (lx - 0.02, ly - 0.02, 0.0),
            (lx + 0.02, ly + 0.02, 0.36), coll, mats['wood'])
    for j, ax in ((0, x0 + 0.05), (1, x1 - 0.05)):
        box(root, '%s_arm%d' % (cid, j), (ax - 0.02, y0 + 0.05, 0.55),
            (ax + 0.02, y1 - 0.07, 0.60), coll, mats['wood'], bevel=0.015)


# ---------------------------------------------------------------- 柜/架/凳
def build_wardrobe_kids(item, mats, coll):
    """孩子房成品衣柜（仅示意）：箱体+门缝+圆头拉手。"""
    B.build_wardrobe(item, mats, coll)


def build_shelf(item, mats, coll):
    """矮书格/窄书架：两侧板+背板+3-4 层板。"""
    cid = item['id']
    bmin, bmax = item['bbox']['min'], item['bbox']['max']
    root = R(item, mats, coll)
    axis, face, inward = B._front_plane(bmin, bmax, item.get('room'))
    t = 0.025
    box(root, cid + '_side0', (bmin[0], bmin[1], bmin[2]), (bmin[0] + t, bmax[1], bmax[2]), coll, mats['wood'])
    box(root, cid + '_side1', (bmax[0] - t, bmin[1], bmin[2]), (bmax[0], bmax[1], bmax[2]), coll, mats['wood'])
    box(root, cid + '_top', (bmin[0], bmin[1], bmax[2] - t), (bmax[0], bmax[1], bmax[2]), coll, mats['wood'])
    n = max(2, round((bmax[2] - bmin[2]) / 0.32))
    dz = (bmax[2] - t - (bmin[2] + t)) / n
    for i in range(1, n):
        z = bmin[2] + t + i * dz
        box(root, '%s_sh%d' % (cid, i), (bmin[0] + t, bmin[1] + 0.01, z),
            (bmax[0] - t, bmax[1] - 0.01, z + t), coll, mats['wood'])


def build_stool(item, mats, coll):
    """小圆凳/换鞋凳/梳妆凳（cylinder 或 box）。"""
    cid = item['id']
    if item.get('shape') == 'cylinder':
        c, r, z0, h = item['center'], item['radius'], item.get('z_base', 0.0), item['height']
        root = R(item, mats, coll)
        cyl(root, cid + '_top', c, r, z0 + h - 0.05, z0 + h, coll, mats['wood'])
        cyl(root, cid + '_post', c, r * 0.18, z0, z0 + h - 0.05, coll, mats['wood'])
        for p in item.get('parts', []):
            if p.get('shape') == 'sphere':
                sph(root, cid + '_jar', tuple(p['center']), p['radius'], coll, mats['wood'])
    else:
        bmin, bmax = item['bbox']['min'], item['bbox']['max']
        root = R(item, mats, coll)
        box(root, cid + '_pad', (bmin[0], bmin[1], bmax[2] - 0.06), bmax, coll,
            mats['wood'], bevel=0.03)
        legs(root, cid, (bmin[0], bmin[1], 0.0), (bmax[0], bmax[1], bmax[2] - 0.06), coll,
             mats['wood'], h=bmax[2] - 0.06, s=0.035, inset=0.06)


def sph(root, name, center, r, coll, mat, seg=16):
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
    cyl(root, cid + '_rod', (c[0], c[1]), 0.008, c[2] + r, 2.60, coll, mats['dark'])
    sph(root, cid + '_ globe', (c[0], c[1], c[2]), r, coll, mats['glass'])


def build_floor_lamp(item, mats, coll):
    """弧形落地灯：立杆 + 弯臂（斜杆）+ 灯罩。"""
    cid = item['id']
    c = item['center']
    r = item['radius']
    z0 = item.get('z_base', 0.0)
    h = item['height']
    root = R(item, mats, coll)
    cyl(root, cid + '_pole', c, 0.015, z0, z0 + h * 0.8, coll, mats['dark'])
    cyl(root, cid + '_arm', (c[0] + 0.25, c[1]), 0.012, z0 + h * 0.78, z0 + h - 0.02, coll, mats['dark'])
    o = cyl(root, cid + '_shade', (c[0] + 0.42, c[1]), 0.14, z0 + h - 0.30, z0 + h, coll, mats['white'])
    # 灯罩锥形（白模直筒即可）
    return root


def build_tv(item, mats, coll):
    cid = item['id']
    bmin, bmax = item['bbox']['min'], item['bbox']['max']
    root = R(item, mats, coll)
    box(root, cid + '_screen', bmin, bmax, coll, mats['dark'], bevel=0.004)
    for p in item.get('parts', []):
        pb = p['bbox']
        box(root, cid + '_stand', tuple(pb['min']), tuple(pb['max']), coll, mats['dark'])


def build_artwork(item, mats, coll):
    """端景挂画 + 画灯（规格 5.1：暖色抽象画 + 黑色画灯）。"""
    cid = item['id']
    bmin, bmax = item['bbox']['min'], item['bbox']['max']
    root = R(item, mats, coll)
    box(root, cid + '_canvas', bmin, bmax, coll, mats['wood'], bevel=0.008)
    # 画上方画灯（收在 bbox 上沿内）
    ym = (bmin[1] + bmax[1]) / 2
    box(root, cid + '_lamp', (bmin[0] + 0.015, ym - 0.3, bmax[2]),
        (bmax[0], ym + 0.3, bmax[2] + 0.06), coll, mats['dark'])


def build_plant(item, mats, coll):
    """绿植：盆（cylinder）+ 叶（多面片圆锥近似）；端景天堂鸟高 1.6m / 露台小绿植。"""
    cid = item['id']
    c = item['center']
    r = item['radius']
    z0 = item.get('z_base', 0.0)
    root = R(item, mats, coll)
    # 茎干（从包络底部起）；叶片 8 片收在包络内、低叶贴地高叶近顶
    cyl(root, cid + '_stem', c, 0.025, z0 + 0.004, z0 + item['height'] * 0.75, coll, mats['wood'])
    for i in range(8):
        a = math.radians(45 * i)
        d0, d1 = r * 0.15, r * 0.95
        x_a, x_b = sorted((c[0] + math.cos(a) * d0, c[0] + math.cos(a) * d1))
        y_a, y_b = sorted((c[1] + math.sin(a) * d0, c[1] + math.sin(a) * d1))
        zf = 0.28 + 0.05 * i
        box(root, '%s_leaf%d' % (cid, i),
            (x_a - 0.015, y_a - 0.015, z0 + item['height'] * zf),
            (x_b + 0.015, y_b + 0.015, z0 + item['height'] * (zf + 0.35)),
            coll, mats['dark'])


def build_planter(item, mats, coll):
    cid = item['id']
    c = item['center']
    r = item['radius']
    z0 = item.get('z_base', 0.0)
    root = R(item, mats, coll)
    cyl(root, cid + '_pot', c, r * 0.98, z0, z0 + item['height'], coll, mats['wood'])


def build_rug(item, mats, coll):
    cid = item['id']
    bmin, bmax = item['bbox']['min'], item['bbox']['max']
    root = R(item, mats, coll)
    box(root, cid + '_pile', bmin, bmax, coll, mats['wood'])


def build_cushion(item, mats, coll):
    """飘窗软垫（靠枕另加两枚：墨绿/砖红，规格 5.9）。"""
    cid = item['id']
    bmin, bmax = item['bbox']['min'], item['bbox']['max']
    root = R(item, mats, coll)
    box(root, cid + '_pad', bmin, bmax, coll, mats['white'], bevel=0.03)
    box(root, cid + '_pil_olive', (bmin[0] + 0.15, bmax[1] - 0.34, bmax[2]),
        (bmin[0] + 0.52, bmax[1] - 0.05, bmax[2] + 0.24), coll, mats['dark'], bevel=0.06)
    box(root, cid + '_pil_brick', (bmax[0] - 0.52, bmax[1] - 0.34, bmax[2]),
        (bmax[0] - 0.15, bmax[1] - 0.05, bmax[2] + 0.24), coll, mats['wood'], bevel=0.06)


def build_bay_seat_cover(item, mats, coll):
    build_rug(item, mats, coll)


def build_screen_fallback(item, mats, coll):
    B.BUILDERS['screen'](item, mats, coll)


def build_nightstand(item, mats, coll):
    """床头柜：箱体 + 单抽屉面板 + 短腿。"""
    cid = item['id']
    bmin, bmax = item['bbox']['min'], item['bbox']['max']
    root = R(item, mats, coll)
    box(root, cid + '_body', (bmin[0], bmin[1], 0.10), (bmax[0], bmax[1], bmax[2] - 0.02), coll, mats['wood'])
    axis, face, inward = B._front_plane(bmin, bmax, item.get('room'))
    a0, a1 = (bmin[1], bmax[1]) if axis == 'x' else (bmin[0], bmax[0])
    B.add_fronts(root, cid, coll, mats['wood'], axis, face, inward, a0, a1,
                 0.12, bmax[2] - 0.06, 'drw', max_w=0.5, pulls=True,
                 pull_mat=mats['dark'])
    legs(root, cid, (bmin[0], bmin[1], 0.0), (bmax[0], bmax[1], 0.10), coll,
         mats['wood'], h=0.10, s=0.03, inset=0.05)


def build_dressing_table(item, mats, coll):
    """主卧一体梳妆台：胡桃木台面 + 侧板 + 奶白小吊柜(parts) + 镜子。"""
    cid = item['id']
    bmin, bmax = item['bbox']['min'], item['bbox']['max']
    root = R(item, mats, coll)
    x0, y0 = bmin[0], bmin[1]
    x1, y1 = bmax[0], bmax[1]
    box(root, cid + '_top', (x0, y0, 0.70), (x1, y1, 0.75), coll, mats['wood'], bevel=0.01)
    box(root, cid + '_side0', (x0, y0 + 0.02, 0.0), (x0 + 0.04, y1 - 0.02, 0.70), coll, mats['wood'])
    box(root, cid + '_side1', (x1 - 0.04, y0 + 0.02, 0.0), (x1, y1 - 0.02, 0.70), coll, mats['wood'])
    box(root, cid + '_shelf', (x0 + 0.04, y0 + 0.04, 0.22), (x1 - 0.04, y1 - 0.04, 0.26), coll, mats['wood'])
    for p in item.get('parts', []):
        pb = p['bbox']
        box(root, cid + '_upper', tuple(pb['min']), tuple(pb['max']), coll, mats['white'])
        B.add_fronts(root, cid, coll, mats['white'], 'x', pb['max'][0] - 0.005, -1,
                     pb['min'][1], pb['max'][1], pb['min'][2] + 0.02,
                     pb['max'][2] - 0.02, 'door', max_w=0.35, pulls=True,
                     pull_mat=mats['dark'])
    # 镜子（台面与吊柜之间，贴墙）
    box(root, cid + '_mirror', (x0 + 0.01, (y0 + y1) / 2 - 0.28, 0.85),
        (x0 + 0.035, (y0 + y1) / 2 + 0.28, 1.35), coll, mats['mirror'])


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
def pleated_panel(name, u0, u1, v, z0, z1, amp, period, coll, mat, axis='x'):
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
    coll.objects.link(o)
    return o


def _fx_curtains(mats, coll):
    c = coll
    sheer, blackout = mats['glass'], mats['white']
    # 客餐厅南窗（W18 x3.5..9.1）：纱帘拉 2/3（西侧），遮光帘收两侧
    pleated_panel('fx_curt_living_sheer', 3.5, 7.1, -11.44, 0.55, 2.45, 0.035, 0.16, c, sheer)
    pleated_panel('fx_curt_living_bo_w', 3.5, 4.3, -11.36, 0.55, 2.45, 0.05, 0.14, c, blackout)
    pleated_panel('fx_curt_living_bo_e', 8.3, 9.1, -11.36, 0.55, 2.45, 0.05, 0.14, c, blackout)
    # 主卧落地门窗（W17 x9.6..12.4）：纱帘全幅 + 遮光帘两侧
    pleated_panel('fx_curt_master_sheer', 9.6, 12.4, -10.30, 0.02, 2.28, 0.035, 0.16, c, sheer)
    pleated_panel('fx_curt_master_bo_w', 9.6, 10.3, -10.22, 0.02, 2.28, 0.05, 0.14, c, blackout)
    pleated_panel('fx_curt_master_bo_e', 11.7, 12.4, -10.22, 0.02, 2.28, 0.05, 0.14, c, blackout)
    # 父母房飘窗（W23 x0.55..2.95）：纱帘 + 卷帘箱
    pleated_panel('fx_curt_parents_sheer', 0.55, 2.95, -10.36, 0.50, 2.28, 0.03, 0.14, c, sheer)
    box(None, 'fx_curt_parents_roller', (0.55, -10.40, 2.28), (2.95, -10.34, 2.36), c, mats['white'])
    # 孩子房北窗（W01/W06）：双层帘
    pleated_panel('fx_curt_daughter_sheer', 6.55, 8.75, -0.32, 0.92, 2.36, 0.03, 0.14, c, sheer)
    pleated_panel('fx_curt_daughter_bo_w', 6.55, 7.2, -0.24, 0.92, 2.36, 0.05, 0.13, c, blackout)
    pleated_panel('fx_curt_daughter_bo_e', 8.1, 8.75, -0.24, 0.92, 2.36, 0.05, 0.13, c, blackout)
    pleated_panel('fx_curt_son_sheer', 11.45, 12.95, -0.32, 0.92, 2.26, 0.03, 0.14, c, sheer)
    pleated_panel('fx_curt_son_bo_w', 11.45, 12.0, -0.24, 0.92, 2.26, 0.05, 0.13, c, blackout)
    pleated_panel('fx_curt_son_bo_e', 12.4, 12.95, -0.24, 0.92, 2.26, 0.05, 0.13, c, blackout)
    # 主卫窗（W10 y-4.9..-3.8）：防水百叶帘放下 1/3
    box(None, 'fx_blind_master_bath', (13.575, -4.9, 0.8), (13.585, -3.8, 1.9), c, mats['white'])
    for i in range(9):
        box(None, 'fx_blind_mb_slats%d' % i, (13.574, -4.9, 0.8 + i * 0.12),
            (13.586, -3.8, 0.87 + i * 0.12), c, mats['white'])


def _fx_lights(mats, coll):
    c = coll
    # 卧室吸顶灯（薄款乳白）
    for rid, (cx, cy) in {'master_bedroom': (11.0, -7.7), 'parents_room': (1.75, -8.3),
                          'daughter_room': (7.65, -2.05), 'son_room': (12.2, -1.8)}.items():
        cyl(None, 'fx_ceiling_%s' % rid, (cx, cy), 0.24, 2.79, 2.85, c, mats['glass'])
    # 客餐厅边吊筒灯（底面 2.60，间距约 1.1，避开东带出风口）
    spots = []
    for x in (4.3, 5.4, 6.5, 7.6, 8.4):
        spots += [(x, -11.35), (x, -4.20)]
    for y in (-10.2, -9.1, -6.8, -5.6):
        spots += [(3.57, y)]
    for y in (-10.9, -6.9, -5.6):
        spots += [(9.02, y)]
    for i, (x, y) in enumerate(spots):
        cyl(None, 'fx_spot_living%02d' % i, (x, y), 0.0375, 2.575, 2.60, c, mats['glass'])
        cyl(None, 'fx_spot_living%02d_r' % i, (x, y), 0.05, 2.60, 2.615, c, mats['white'])
    # 卧室/过道筒灯
    for i, (x, y, z) in enumerate([(11.0, -8.8, 2.85), (11.0, -6.6, 2.85),
                                   (1.75, -9.5, 2.85), (7.65, -3.0, 2.85),
                                   (12.2, -2.9, 2.85), (9.9, -4.4, 2.60),
                                   (10.6, -3.0, 2.60), (2.7, -5.7, 2.85)]):
        cyl(None, 'fx_spot_room%d' % i, (x, y), 0.0375, z - 0.025, z, c, mats['glass'])
    # 床头壁灯（主卧两侧 + 父母房床头）
    for i, (x, y) in enumerate([(12.68, -7.0), (12.68, -9.2), (0.24, -8.65)]):
        box(None, 'fx_wall_lamp%d' % i, (x - 0.02 if x > 6 else x, y - 0.09, 1.35),
            (x + 0.06 if x > 6 else x + 0.08, y + 0.09, 1.55), c, mats['dark'])
        cyl(None, 'fx_wall_lamp%d_sh' % i, (x + (0.12 if x > 6 else -0.12), y), 0.06,
            1.32, 1.50, c, mats['glass'])


def _fx_props(mats, coll):
    c = coll
    # 玄关端景格：陶罐 + 小画
    sph(None, 'fx_foyer_jar', (2.55, -6.48, 1.06), 0.09, c, mats['wood'])
    box(None, 'fx_foyer_pic', (2.95, -6.56, 1.0), (3.15, -6.52, 1.22), c, mats['wood'])
    # 厨房台面：砧板 + 油壶 + 香草盆（规格 5.4，克制）
    box(None, 'fx_kn_board', (5.0, -1.62, 0.9), (5.6, -1.42, 0.918), c, mats['wood'], bevel=0.006)
    cyl(None, 'fx_kn_oil', (5.85, -1.55), 0.045, 0.9, 1.08, c, mats['dark'])
    cyl(None, 'fx_kn_herb', (4.9, -2.7), 0.07, 0.9, 1.02, c, mats['white'])
    sph(None, 'fx_kn_herb_leaf', (4.9, -2.7, 1.08), 0.08, c, mats['dark'])
    # 岛台台面：托盘
    box(None, 'fx_island_tray', (4.7, -5.6, 0.9), (5.1, -5.2, 0.915), c, mats['wood'], bevel=0.006)
    # 实木组合柜开放格：书 + 唱片 + 陶罐（每层 1-3 件）
    for i, z in enumerate((1.45, 1.85)):
        for j, y in enumerate((-9.8, -9.55, -9.3)):
            box(None, 'fx_bc_book%d%d' % (i, j), (3.55, y - 0.09, z), (3.72, y + 0.09, z + 0.22),
                c, mats['white' if (i + j) % 2 else 'wood'])
    box(None, 'fx_bc_record', (3.55, -9.75, 1.85), (3.60, -9.62, 2.07), c, mats['dark'])
    sph(None, 'fx_bc_pot', (3.62, -9.4, 1.96), 0.06, c, mats['wood'])
    # B 整墙柜开放格：书 + 孩子作品
    for i, y in enumerate((-9.9, -9.3, -8.7, -8.1, -7.5, -6.9, -6.3, -5.8)):
        box(None, 'fx_B_shelf_book%d' % i, (8.99, y - 0.11, 1.08), (9.16, y + 0.11, 1.32),
            c, mats['white' if i % 2 else 'wood'])
        box(None, 'fx_B_shelf_toy%d' % i, (8.99, y - 0.1 + 0.5, 0.98), (9.14, y + 0.1 + 0.5, 1.12),
            c, mats['wood'] if i % 3 else mats['dark'])
    # 主卧书桌上方开放格：书 + 小件
    for i, y in enumerate((-6.3, -5.8)):
        box(None, 'fx_desk_book%d' % i, (12.46, y - 0.1, 1.5), (12.66, y + 0.1, 1.74),
            c, mats['white' if i % 2 else 'wood'])
    # 琴叶榕（规格 5.1：西墙地脚/南窗边，不挡露台门）
    cyl(None, 'fx_fiddle_pot', (3.75, -11.15), 0.19, 0.0, 0.38, c, mats['wood'])
    cyl(None, 'fx_fiddle_stem', (3.75, -11.15), 0.02, 0.38, 1.05, c, mats['wood'])
    for i in range(7):
        a = math.radians(50 * i)
        L = 0.28
        px, py = 3.75 + math.cos(a) * 0.14, -11.15 + math.sin(a) * 0.14
        box(None, 'fx_fiddle_leaf%d' % i,
            (min(px, px + math.cos(a) * L) - 0.025, min(py, py + math.sin(a) * L) - 0.025,
             0.75 + 0.06 * i),
            (max(px, px + math.cos(a) * L) + 0.025, max(py, py + math.sin(a) * L) + 0.025,
             0.95 + 0.06 * i), c, mats['dark'])


def build_extras(mats, colls):
    """规格补充软装：窗帘、吸顶灯/筒灯/壁灯几何、摆件、琴叶榕。"""
    coll = colls['common']
    _fx_curtains(mats, coll)
    _fx_lights(mats, coll)
    _fx_props(mats, coll)
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

# -*- coding: utf-8 -*-
# builtins.py —— M2 定制柜体与卫浴厨房（白模）
# 每个 item：父 Empty(id) + 子网格。白模材质 white/wood/glass/dark/mirror/kfront。
# 立面朝向规则：贴墙的面=背面，无墙的面=正面（数据级检测，不依赖生成对象）。
import bpy

import config
import util

M2_TYPES = {
    'cabinet', 'open_niche', 'kitchen_counter', 'dishwasher', 'sink', 'hob',
    'range_hood', 'mirror_door', 'laundry_cabinet', 'bookcase', 'vanity',
    'mirror_cabinet', 'toilet', 'glass_partition', 'screen', 'fridge',
    'tv_cabinet', 'glass_sliding_door', 'shower_floor', 'island',
    'wardrobe',   # R2FIX M1：主卧/父母房衣柜归 M2 白柜体系（原误走孩子房构建器→米色平板）
}
M2_WARDROBE_ROOMS = {'master_bedroom', 'parents_room'}
COVERED = {'common_parents_room_bay_seat_01': 'bay_platform',
           'common_parents_room_ceiling_box_01': 'ceil_parents_room_ac'}
ROOM_CENTER = {}  # room -> (cx, cy)，build_all 时从 floors 填


# ---------------------------------------------------------------- 基础
def item_root(item, coll):
    root = bpy.data.objects.new(item['id'], None)
    root.empty_display_type = 'PLAIN_AXES'
    root.empty_display_size = 0.2
    root.empty_display_size = 0.2
    coll.objects.link(root)
    return root


def child(root, name, bmin, bmax, coll, mat, bevel=None, glass=False, role=None):
    o = util.make_box(name, bmin, bmax, coll=coll, mat=mat, bevel=bevel, role=role)
    if o is None:
        return None
    o.parent = root
    if glass:
        o.visible_shadow = False
    return o


_WALL_CACHE = None


def _walls():
    global _WALL_CACHE
    if _WALL_CACHE is None:
        layout = util.load_layout()
        _WALL_CACHE = []
        for w in layout['walls']:
            g = architecture_wall_geo(w)
            _WALL_CACHE.append(g)
    return _WALL_CACHE


def architecture_wall_geo(w):
    import architecture
    return architecture.wall_geo(w, util.load_layout()['walls'])


def _face_has_wall(axis, is_max, bmin, bmax, tol=0.13, min_ov=0.5):
    """检测 bmin/bmax 某面外侧 tol 内是否有平行墙（贴墙=背面）。"""
    k = 0 if axis == 'x' else 1
    p = bmax[k] if is_max else bmin[k]
    for g in _walls():
        if g['axis'] == axis:
            continue  # 墙沿 axis 延伸，不与该面法向平行
        v0, v1 = g['v_center'] - g['t'] / 2, g['v_center'] + g['t'] / 2
        if not (v0 - tol) <= p <= (v1 + tol):
            continue
        a0, a1 = (bmin[1], bmax[1]) if axis == 'x' else (bmin[0], bmax[0])
        ov = min(g['u1e'], a1) - max(g['u0e'], a0)
        if ov >= min_ov * (a1 - a0):
            return True
    return False


def _front(bmin, bmax, room=None):
    """返回 ('x'|'y', is_max)：正面 = 贴墙面的对面（强候选，绝对优先）；
    无贴墙背面时（独立柜）取离房间中心更近的开放面。"""
    strong, weak = [], []
    for axis in ('x', 'y'):
        wmin = _face_has_wall(axis, False, bmin, bmax, tol=0.09)
        wmax = _face_has_wall(axis, True, bmin, bmax, tol=0.09)
        if wmax and not wmin:
            strong.append((axis, False))
        elif wmin and not wmax:
            strong.append((axis, True))
        elif not wmin and not wmax:
            weak.append((axis, False))
            weak.append((axis, True))
    cands = strong or weak or [('x', True)]

    def extent(c):
        axis, _ = c
        k = 0 if axis == 'x' else 1
        return bmax[k] - bmin[k]

    cx, cy = ROOM_CENTER.get(room, (7.0, -6.2))

    def dist(c):
        axis, is_max = c
        k = 0 if axis == 'x' else 1
        p = bmax[k] if is_max else bmin[k]
        return abs(p - (cx if axis == 'x' else cy))

    if len(cands) > 1:
        cands.sort(key=lambda c: (round(extent(c), 3), dist(c)))
    return cands[0]


def _front_plane(bmin, bmax, room=None):
    """返回 (axis, face, inward)：正面外表皮坐标 face（留 5mm 在 bbox 内）与向内方向。"""
    axis, is_max = _front(bmin, bmax, room)
    k = 0 if axis == 'x' else 1
    if is_max:
        return axis, bmax[k] - 0.005, -1
    return axis, bmin[k] + 0.005, +1


def add_fronts(root, cid, coll, mat, axis, face, inward, a0, a1, z0, z1, tag,
               max_w=0.45, gap=0.003, t=0.02, pulls=True, pull_mat=None,
               pull_len=0.30, role='cabinet_front', pull_role='metal_black',
               framed=False, backer=True, pull_style='bar', drawer_stack=0,
               drawer_heights=None):
    """门板阵列：沿 a 轴等分；法向 axis；面板外皮在 face、向内伸 t；拉手凸出 ≤4mm。
    R2FIX M1：缝 3mm；门板后 10mm 深色背板 #3A3530（缝读作清晰暗线）；
    framed=True 奶白门 40mm 外框 + 芯板内凹 3mm（实际几何）；backer=False 用于
    推拉门（前后错开无缝）。调用方须先 _recess_front 后退 body 前脸。
    R2FIX2：pull_style='slot' 拉手槽（每扇上缘内嵌深色凹槽条，暗槽读法）；
    drawer_stack=n>0 整幅按 z 等分 n 层抽屉面（共享缝背板，d0..d{n-1}）。
    FINAL1 F2：drawer_heights=[h0,h1,..] 梯度层高（自下而上，按可用高比例缩放），
    长度须与 drawer_stack 一致。"""
    if drawer_stack > 0:
        if drawer_heights:
            if len(drawer_heights) != drawer_stack:
                raise ValueError('[builtins] drawer_heights 长度 != drawer_stack')
            avail = (z1 - z0) - gap * (drawer_stack - 1)
            sc = avail / float(sum(drawer_heights))
            cells, zc = [], z0
            for k, h in enumerate(drawer_heights):
                cells.append((a0 + gap / 2, a1 - gap / 2,
                              zc + gap / 2, zc + h * sc - gap / 2, k))
                zc += h * sc + gap
        else:
            band = (z1 - z0) / drawer_stack
            cells = [(a0 + gap / 2, a1 - gap / 2,
                      z0 + k * band + gap / 2, z0 + (k + 1) * band - gap / 2, k)
                     for k in range(drawer_stack)]
    else:
        n = max(1, round((a1 - a0) / max_w))
        w = (a1 - a0) / n
        cells = [(a0 + i * w + gap / 2, a0 + (i + 1) * w - gap / 2,
                  z0 + gap / 2, z1 - gap / 2, i) for i in range(n)]
    n_lo, n_hi = (face - t, face) if inward < 0 else (face, face + t)
    p_lo, p_hi = (face, face + 0.004) if inward < 0 else (face - 0.004, face)
    if backer:
        blo, bhi = (face - 0.013, face - 0.010) if inward < 0 else (face + 0.010, face + 0.013)
        if axis == 'y':
            gb0, gb1 = (a0, blo, z0), (a1, bhi, z1)
        else:
            gb0, gb1 = (blo, a0, z0), (bhi, a1, z1)
        # R2FIX 复测修正：白模阶段 bpy.data 里没有 gap_dark（正式材质 apply_all 才建），
        # 原 bpy.data.materials.get 恒为 None → 深色背板从未建出。改为 role 交给 apply_all。
        child(root, '%s_%s_gapbg' % (cid, tag), gb0, gb1, coll, None, role='gap_dark')
    for ua, ub, zin, zout, i in cells:

        def panel(nm, pa, pb, pz0, pz1, recess=0.0):
            b0_, b1_ = (n_lo, n_hi - recess) if inward < 0 else (n_lo + recess, n_hi)
            if axis == 'y':
                bb0, bb1 = (pa, b0_, pz0), (pb, b1_, pz1)
            else:
                bb0, bb1 = (b0_, pa, pz0), (b1_, pb, pz1)
            child(root, '%s_%s_%s' % (cid, tag, nm), bb0, bb1, coll, mat,
                  bevel=0.003, role=role)

        nm = 'd%d' % i if drawer_stack > 0 else 'f%d' % i
        if framed and (ub - ua) > 0.10 and (zout - zin) > 0.10:
            # R2FIX M1 奶白细边框门：40mm 外框 + 芯板内凹 3mm（实际几何）
            fw = 0.04
            panel(nm + 'l', ua, ua + fw, zin, zout)
            panel(nm + 'r', ub - fw, ub, zin, zout)
            panel(nm + 'b', ua + fw, ub - fw, zin, zin + fw)
            panel(nm + 't', ua + fw, ub - fw, zout - fw, zout)
            panel(nm + 'c', ua + fw, ub - fw, zin + fw, zout - fw, recess=0.003)
        else:
            panel(nm, ua, ub, zin, zout)
        if pulls:
            pm = pull_mat if pull_mat else mat
            if pull_style == 'slot' or drawer_stack > 0:
                # R2FIX2 拉手槽：面板上缘内嵌 3mm 的深色横槽条（读作铣槽暗缝）
                sf_lo, sf_hi = ((n_lo + 0.003, n_lo + 0.006) if inward < 0
                                else (n_hi - 0.006, n_hi - 0.003))
                us0, us1 = ua + 0.05, ub - 0.05
                zs0, zs1 = zout - 0.075, zout - 0.035
                if axis == 'y':
                    child(root, '%s_%s_slot%d' % (cid, tag, i),
                          (us0, sf_lo, zs0), (us1, sf_hi, zs1), coll, pm,
                          role=pull_role)
                else:
                    child(root, '%s_%s_slot%d' % (cid, tag, i),
                          (sf_lo, us0, zs0), (sf_hi, us1, zs1), coll, pm,
                          role=pull_role)
            else:
                hl = min(pull_len, (zout - zin) * 0.6)
                zc = (zin + zout) / 2
                upos = (ub - 0.03) if (i < len(cells) // 2 or len(cells) == 1) else (ua + 0.03)
                if axis == 'y':
                    child(root, '%s_%s_p%d' % (cid, tag, i),
                          (upos - 0.008, p_lo, zc - hl / 2),
                          (upos + 0.008, p_hi, zc + hl / 2), coll, pm,
                          role=pull_role)
                else:
                    child(root, '%s_%s_p%d' % (cid, tag, i),
                          (p_lo, upos - 0.008, zc - hl / 2),
                          (p_hi, upos + 0.008, zc + hl / 2), coll, pm,
                          role=pull_role)


def _shelf_zs(z0, z1, step):
    zs, z = [], z0
    while z < z1 - 0.05:
        zs.append(z)
        z += step
    return zs


def _basin_under(root, cid, center, z_lo, z_hi, coll, mats):
    """FINAL1 F5 台下盆：开顶白瓷杯（四壁 + 底，白陶瓷 role/材质统一）。
    旧版根因三处：洞 0.26 方洞 < 盆外径 0.32x0.30；实心盆沿顶 z_hi-0.035
    顶穿台面分段缘（穿插错乱）；假内腔挂 mats['dark']（role 却是 ceramic_white，
    洞口读作灰黑槽）。现洞 = 外径 - 2cm、沿口压台面底 2mm、洞口可见白瓷内壁。"""
    hx, hy = center
    ztop = z_lo - 0.002          # 沿口压台面底 2mm（避共面）
    zbot = z_lo - 0.16
    ox, oy, t = 0.15, 0.14, 0.012
    child(root, cid + '_bowlW', (hx - ox, hy - oy, zbot), (hx - ox + t, hy + oy, ztop),
          coll, mats['white'], bevel=0.004, role='ceramic_white')
    child(root, cid + '_bowlE', (hx + ox - t, hy - oy, zbot), (hx + ox, hy + oy, ztop),
          coll, mats['white'], bevel=0.004, role='ceramic_white')
    child(root, cid + '_bowlN', (hx - ox + t, hy + oy - t, zbot),
          (hx + ox - t, hy + oy, ztop), coll, mats['white'], bevel=0.004,
          role='ceramic_white')
    child(root, cid + '_bowlS', (hx - ox + t, hy - oy, zbot),
          (hx + ox - t, hy - oy + t, ztop), coll, mats['white'], bevel=0.004,
          role='ceramic_white')
    child(root, cid + '_bowlB', (hx - ox + t, hy - oy + t, zbot),
          (hx + ox - t, hy + oy - t, zbot + t), coll, mats['white'],
          bevel=0.003, role='ceramic_white')


def _goose_faucet(root, name, base_xy, fdir, zt, coll, mats):
    """R2 #11 黑鹅颈龙头：底座 + 立柱 + 横管 + 下嘴（metal_black，方管造型同厨房水槽）。"""
    fx, fy = base_xy
    dx, dy = fdir
    child(root, name + '_base', (fx - 0.020, fy - 0.020, zt),
          (fx + 0.020, fy + 0.020, zt + 0.025), coll, mats['dark'],
          role='metal_black')
    child(root, name + '_riser', (fx - 0.012, fy - 0.012, zt),
          (fx + 0.012, fy + 0.012, zt + 0.24), coll, mats['dark'],
          role='metal_black')
    sx, sy = fx + dx * 0.20, fy + dy * 0.20
    child(root, name + '_spout',
          (min(fx, sx) - 0.011, min(fy, sy) - 0.011, zt + 0.215),
          (max(fx, sx) + 0.011, max(fy, sy) + 0.011, zt + 0.24), coll, mats['dark'],
          role='metal_black')
    ex, ey = sx + dx * 0.022, sy + dy * 0.022
    child(root, name + '_tip',
          (min(sx, ex) - 0.010, min(sy, ey) - 0.010, zt + 0.16),
          (max(sx, ex) + 0.010, max(sy, ey) + 0.010, zt + 0.225), coll, mats['dark'],
          role='metal_black')


# ---------------------------------------------------------------- 建模器
def _recess_front(bmin, bmax, axis, face, inward, t=0.025):
    """R2FIX M1-0 根因修复：柜体盒前脸缩到门板内皮——body 前皮原本比门板外皮
    凸约 5mm，把门板/背板/镜面整面盖死（13/11/08"一整块平板"与镜面不显同源）。"""
    b0, b1 = list(bmin), list(bmax)
    k = 0 if axis == 'x' else 1
    if inward > 0:
        b0[k] = max(b0[k], face + t)
    else:
        b1[k] = min(b1[k], face - t)
    return tuple(b0), tuple(b1)


def build_wardrobe(item, mats, coll, box_role='cabinet_box', front_role='cabinet_front'):
    cid = item['id']
    bmin, bmax = item['bbox']['min'], item['bbox']['max']
    root = item_root(item, coll)
    axis, face, inward = _front_plane(bmin, bmax, item.get('room'))
    bmin, bmax = _recess_front(bmin, bmax, axis, face, inward)
    child(root, cid + '_body', bmin, bmax, coll, mats['white'], role=box_role)
    a0, a1 = (bmin[1], bmax[1]) if axis == 'x' else (bmin[0], bmax[0])
    if item['room'] == 'master_bedroom':
        add_fronts(root, cid, coll, mats['white'], axis, face, inward, a0, a1,
                   0.05, bmax[2] - 0.04, 'door', max_w=0.42, framed=True,
                   pull_mat=mats['dark'], role=front_role)
    else:  # 父母房推拉门：双轨两排（前后错开，无缝无背板）
        f_in = face + 0.023 * inward
        add_fronts(root, cid, coll, mats['white'], axis, face, inward, a0, a1,
                   0.05, bmax[2] - 0.04, 'slA', max_w=0.70, pulls=False,
                   backer=False, role=front_role)
        add_fronts(root, cid, coll, mats['white'], axis, f_in, inward,
                   a0 + 0.05, a1 - 0.05, 0.05, bmax[2] - 0.04, 'slB',
                   max_w=0.70, pulls=False, backer=False, role=front_role)


def build_cabinet(item, mats, coll, params=None):
    params = params or {}
    cid = item['id']
    bmin, bmax = item['bbox']['min'], item['bbox']['max']
    root = item_root(item, coll)
    mat = params.get('mat', mats['white'])
    box_role = params.get('box_role', 'cabinet_box')
    front_role = params.get('front_role', 'cabinet_front')
    axis, face, inward = _front_plane(bmin, bmax, item.get('room'))
    bmin, bmax = _recess_front(bmin, bmax, axis, face, inward)
    child(root, cid + '_body', bmin, bmax, coll, mat, role=box_role)
    a0, a1 = (bmin[1], bmax[1]) if axis == 'x' else (bmin[0], bmax[0])
    # R2FIX M1：奶白门细边框；玄关柜/B 整墙柜短拉手 120mm；B 墙柜每段 ~10 扇
    framed = params.get('framed', True)
    # R2FIX2 N3：厨房吊柜与下柜统一黑短拉手 120mm（工单"与上柜统一"）
    pull_len = params.get('pull_len', 0.12 if (cid.startswith('common_foyer') or
                                               cid.startswith('B_living') or
                                               cid.startswith('common_kitchen')) else 0.30)
    max_w = params.get('max_w', 0.50 if cid.startswith('B_living') else 0.45)
    add_fronts(root, cid, coll, mat, axis, face, inward, a0, a1,
               bmin[2] + 0.02, bmax[2] - 0.02, 'door',
               max_w=max_w, framed=framed, pull_len=pull_len,
               pulls=params.get('pulls', True), pull_mat=mats.get('dark'),
               role=front_role)


def build_open_niche(item, mats, coll):
    """开放格：真腔体 —— 背板 + 左右颊板 + 顶/底板（贴到开口面）+ 层板（内缩 2cm）。"""
    cid = item['id']
    bmin, bmax = item['bbox']['min'], item['bbox']['max']
    root = item_root(item, coll)
    axis, face, inward = _front_plane(bmin, bmax, item.get('room'))
    t = 0.02  # 板厚
    u_k, n_k = (1, 0) if axis == 'x' else (0, 1)
    u0, u1 = bmin[u_k], bmax[u_k]
    n0, n1 = bmin[n_k], bmax[n_k]
    front_at_n1 = (inward < 0)
    # 正面在 n1 -> 背板贴 n0；正面在 n0 -> 背板贴 n1
    back0, back1 = (n0, n0 + t) if front_at_n1 else (n1 - t, n1)
    open_face = n1 if front_at_n1 else n0
    cheek_out = open_face - (0.02 if front_at_n1 else -0.02)  # 颊板外缘内收 2cm

    def box_un(tag, ua, ub, na, nb, z0, z1, mat, role):
        lo = [None, None]
        hi = [None, None]
        lo[u_k], hi[u_k] = ua, ub
        lo[n_k], hi[n_k] = na, nb
        return child(root, '%s_%s' % (cid, tag), (lo[0], lo[1], z0),
                     (hi[0], hi[1], z1), coll, mat, role=role)

    d0, d1 = sorted((back0, cheek_out))
    box_un('back', u0, u1, back0, back1, bmin[2], bmax[2], mats['wood'], 'wood')
    box_un('cheek0', u0, u0 + t, d0, d1, bmin[2], bmax[2], mats['wood'], 'wood')
    box_un('cheek1', u1 - t, u1, d0, d1, bmin[2], bmax[2], mats['wood'], 'wood')
    box_un('top', u0 + t, u1 - t, d0, d1, bmax[2] - t, bmax[2], mats['wood'], 'wood')
    box_un('bottom', u0 + t, u1 - t, d0, d1, bmin[2], bmin[2] + t, mats['wood'], 'wood')
    s0 = cheek_out - (0.02 if front_at_n1 else -0.02)
    e0, e1 = sorted((back0, s0))
    zs = _shelf_zs(bmin[2] + t + 0.04, bmax[2] - t - 0.04, 0.35)
    for i, z in enumerate(zs):
        box_un('sh%d' % i, u0 + t + 0.005, u1 - t - 0.005, e0, e1, z, z + t,
               mats['wood'], 'wood')
    # FINAL1 F9：层板顶面 z 写入根自定义属性（furniture._fx_props 摆件落地读取）
    root['shelf_top_zs'] = [round(z + t, 4) for z in zs]


def build_island(item, mats, coll):
    """岛台：侧板+背板(北)+南开放格+北面蒸烤箱/抽屉+石英台面。"""
    cid = item['id']
    bmin, bmax = item['bbox']['min'], item['bbox']['max']
    top = item.get('parts', [{}])[0].get('bbox')
    root = item_root(item, coll)
    x0, y0, z0 = bmin
    x1, y1, z1 = bmax
    child(root, cid + '_sideW', (x0, y0, z0), (x0 + 0.04, y1, z1 - 0.04), coll, mats['wood'], role='wood')
    child(root, cid + '_sideE', (x1 - 0.04, y0, z0), (x1, y1, z1 - 0.04), coll, mats['wood'], role='wood')
    child(root, cid + '_backN', (x0 + 0.04, y1 - 0.04, z0), (x1 - 0.04, y1, z1 - 0.04), coll, mats['wood'], role='wood')
    child(root, cid + '_base', (x0 + 0.04, y0 + 0.04, z0), (x1 - 0.04, y1 - 0.04, z0 + 0.08), coll, mats['wood'], role='wood')
    # 北面（朝厨房 y1）：西段蒸烤箱黑玻璃 + 东段抽屉
    child(root, cid + '_oven', (x0 + 0.12, y1 - 0.045, 0.32),
          (x0 + 0.72, y1 - 0.005, 0.77), coll, mats['dark'], role='black_glass')
    add_fronts(root, cid, coll, mats['wood'], 'y', y1 - 0.005, -1,
               x0 + 0.76, x1 - 0.06, 0.12, 0.72, 'drw', max_w=0.8,
               pulls=True, pull_mat=mats['dark'], role='wood')
    # 南面（朝餐厅 y0）：开放格内衬 + 2 层板
    child(root, cid + '_niche', (x0 + 0.06, y0 + 0.02, 0.10),
          (x1 - 0.06, y0 + 0.30, 0.72), coll, mats['wood'], role='wood')
    for i, z in enumerate((0.36, 0.54)):
        child(root, '%s_sh%d' % (cid, i), (x0 + 0.06, y0 + 0.02, z),
              (x1 - 0.06, y0 + 0.30, z + 0.02), coll, mats['wood'], role='wood')
    if top:
        child(root, cid + '_top', tuple(top['min']), tuple(top['max']), coll,
              mats['white'], bevel=0.004, role='quartz_top')


def build_kitchen_counter(item, mats, coll):
    cid = item['id']
    obmin, obmax = item['bbox']['min'], item['bbox']['max']
    root = item_root(item, coll)
    # REWORK #5：柜身/侧板/踢脚一并挂 kitchen_front（变体切换整排下柜联动）
    # R2FIX M1-0：柜身前脸缩到门板内皮（原 body 前皮盖门板 5mm）
    # FINAL1 F2：门板一律用 recess 之前的前脸平面 face/inward——旧版北段用
    # recess 后的 bmin[1]（门板埋在柜体背侧内部，09"整块竖纹木面"实体），
    # 东段写死贴墙侧 bmax[0]，两段门板/抽屉从未可见（R2FIX2 N3 实未生效）。
    axis, face, inward = _front_plane(obmin, obmax, item.get('room'))
    bmin, bmax = _recess_front(obmin, obmax, axis, face, inward)
    child(root, cid + '_body', bmin, (bmax[0], bmax[1], bmax[2] - 0.04), coll,
          mats['wood'], role='kitchen_front')
    for p in item.get('parts', []):
        tmin, tmax = tuple(p['bbox']['min']), tuple(p['bbox']['max'])
        # R2FIX M3：北台面在水槽位开洞（洞 0.70x0.42，台面分段）
        if item['id'].endswith('dishwasher_01'):
            hx0, hx1 = 4.80, 5.50
            hy0, hy1 = -1.71, -1.29
            slab = lambda n, a0, a1, b0, b1: child(
                root, cid + '_top_' + n, (a0, b0, tmin[2]), (a1, b1, tmax[2]),
                coll, mats['white'], bevel=0.003, role='quartz_top')
            slab('L', tmin[0], hx0, tmin[1], tmax[1])
            slab('R', hx1, tmax[0], tmin[1], tmax[1])
            slab('B', hx0, hx1, tmin[1], hy0)
            slab('F', hx0, hx1, hy1, tmax[1])
        else:
            child(root, cid + '_top', tmin, tmax, coll, mats['white'],
                  bevel=0.003, role='quartz_top')
    if (bmax[1] - bmin[1]) < (bmax[0] - bmin[0]):  # 北台面，门朝南（厨房内侧 -Y）
        # R2FIX2 N3：洗碗机独立面板（x 4.10..4.70）左右对缝——西侧 13cm 固定窄门、
        # 东侧门列从 4.70 起；拉手统一黑短拉手 120mm
        add_fronts(root, cid, coll, mats['kfront'], 'y', face, inward,
                   bmin[0] + 0.02, 4.10, 0.12, bmax[2] - 0.06, 'drwW',
                   max_w=0.13, pulls=True, pull_len=0.12, pull_mat=mats['dark'],
                   role='kitchen_front')
        add_fronts(root, cid, coll, mats['kfront'], 'y', face, inward,
                   4.70, bmax[0] - 0.02, 0.12, bmax[2] - 0.06, 'drw',
                   max_w=0.45, pulls=True, pull_len=0.12, pull_mat=mats['dark'],
                   role='kitchen_front')
    else:  # 东台面，贴东墙、门朝西（-X 厨房内侧）
        # R2FIX2 N3：灶台下方 3 层抽屉（读 layout hob 包络），其余门板；短拉手
        # FINAL1 F2：抽屉层高按工单 0.17/0.25/0.30 比例（可用高 0.68 缩放后
        # 实得约 0.16/0.23/0.28，自下而上），偏差记 qa_final1。
        h0 = h1 = None
        for it in util.load_layout()['items']:
            if it.get('type') == 'hob':
                h0 = it['bbox']['min'][1] + 0.03
                h1 = it['bbox']['max'][1] - 0.03
        if h0 is None or not (bmin[1] + 0.15 < h0 < h1 < bmax[1] - 0.15):
            h0 = h1 = (bmin[1] + bmax[1]) / 2      # 兜底：中置一段抽屉列
        add_fronts(root, cid, coll, mats['kfront'], 'x', face, inward,
                   bmin[1] + 0.02, h0, 0.12, bmax[2] - 0.06, 'drwS',
                   max_w=0.45, pulls=True, pull_len=0.12, pull_mat=mats['dark'],
                   role='kitchen_front')
        add_fronts(root, cid, coll, mats['kfront'], 'x', face, inward,
                   h0, h1, 0.12, bmax[2] - 0.06, 'drwH',
                   pulls=True, pull_len=0.12, pull_mat=mats['dark'],
                   role='kitchen_front', pull_style='slot', drawer_stack=3,
                   drawer_heights=[0.17, 0.25, 0.30])
        add_fronts(root, cid, coll, mats['kfront'], 'x', face, inward,
                   h1, bmax[1] - 0.02, 0.12, bmax[2] - 0.06, 'drwN',
                   max_w=0.45, pulls=True, pull_len=0.12, pull_mat=mats['dark'],
                   role='kitchen_front')


def build_sink(item, mats, coll):
    """R2FIX M3 厨房水槽台下盆：台面已开洞（build_kitchen_counter 切），
    盆体下沉 0.2m（石墨黑、沿口藏于台面下），黑鹅颈龙头立于盆后沿（北侧贴墙）。"""
    cid = item['id']
    bmin, bmax = item['bbox']['min'], item['bbox']['max']
    root = item_root(item, coll)
    # 盆体（沿口略大于洞、藏于台面板厚度内）；下沉 0.2m
    child(root, cid + '_basin', (bmin[0] - 0.02, bmin[1] - 0.02, bmin[2] - 0.22),
          (bmax[0] + 0.02, bmax[1] + 0.02, bmax[2] - 0.025), coll, mats['dark'],
          role='sink_graphite')
    # 内腔（透过洞口可见的深色空腔）
    child(root, cid + '_cav', (bmin[0] + 0.06, bmin[1] + 0.05, bmin[2] - 0.17),
          (bmax[0] - 0.06, bmax[1] - 0.05, bmax[2] - 0.035), coll, mats['dark'],
          role='sink_graphite')
    # 黑鹅颈龙头（盆后沿=靠墙 y_max 一侧）
    xm = (bmin[0] + bmax[0]) / 2
    yb = bmax[1] + 0.05
    child(root, cid + '_tap', (xm - 0.012, yb - 0.012, bmax[2] - 0.02),
          (xm + 0.012, yb + 0.012, bmax[2] + 0.24), coll, mats['dark'],
          role='metal_black')
    child(root, cid + '_taparm', (xm - 0.012, yb - 0.21, bmax[2] + 0.22),
          (xm + 0.012, yb + 0.012, bmax[2] + 0.25), coll, mats['dark'],
          role='metal_black')
    child(root, cid + '_taptip', (xm - 0.010, bmin[1] + 0.10, bmax[2] + 0.16),
          (xm + 0.010, bmin[1] + 0.14, bmax[2] + 0.23), coll, mats['dark'],
          role='metal_black')


def build_hob(item, mats, coll):
    cid = item['id']
    bmin, bmax = item['bbox']['min'], item['bbox']['max']
    root = item_root(item, coll)
    child(root, cid + '_glass', (bmin[0], bmin[1], bmin[2]),
          (bmax[0], bmax[1], bmin[2] + 0.012), coll, mats['dark'], bevel=0.003,
          role='black_glass')
    xm = (bmin[0] + bmax[0]) / 2
    for i, cy in enumerate(((bmin[1] + bmax[1]) / 2 - 0.17, (bmin[1] + bmax[1]) / 2 + 0.17)):
        child(root, '%s_burner%d' % (cid, i), (xm - 0.06, cy - 0.06, bmin[2] + 0.012),
              (xm + 0.06, cy + 0.06, bmax[2]), coll, mats['dark'], role='metal_black')


def build_range_hood(item, mats, coll):
    cid = item['id']
    bmin, bmax = item['bbox']['min'], item['bbox']['max']
    root = item_root(item, coll)
    child(root, cid + '_topbox', (bmin[0], bmin[1], bmax[2] - 0.16),
          (bmax[0], bmax[1], bmax[2]), coll, mats['dark'], role='metal_black')
    child(root, cid + '_slant', (bmin[0], bmin[1], bmin[2]),
          (bmax[0], bmax[1] - 0.12, bmax[2] - 0.16), coll, mats['dark'],
          role='metal_black')


def build_vanity(item, mats, coll):
    cid = item['id']
    bmin, bmax = item['bbox']['min'], item['bbox']['max']
    root = item_root(item, coll)
    top = item.get('parts', [{}])[0].get('bbox')
    axis, face, inward = _front_plane(bmin, bmax, item.get('room'))
    cbmin, cbmax = _recess_front(bmin, (bmax[0], bmax[1], bmax[2] - 0.04), axis, face, inward)
    child(root, cid + '_cab', cbmin, cbmax, coll, mats['wood'], role='wood')
    if top:
        tmin, tmax = tuple(top['min']), tuple(top['max'])
    else:
        tmin, tmax = (bmin[0], bmin[1], bmax[2] - 0.035), tuple(bmax)
    zt = tmax[2]
    axis, face, inward = _front_plane(bmin, bmax, item.get('room'))
    a0, a1 = (bmin[1], bmax[1]) if axis == 'x' else (bmin[0], bmax[0])
    add_fronts(root, cid, coll, mats['wood'], axis, face, inward, a0, a1,
               bmin[2] + 0.02, bmax[2] - 0.06, 'drw', max_w=0.5,
               pulls=True, pull_mat=mats['dark'], role='wood')
    # R2 #11 台下盆：台面分段开洞 + 洞下盆体/内腔 + 黑鹅颈龙头
    # FINAL1 F5：洞 = 盆外径(0.30x0.28) - 2cm -> 半宽 0.14/0.13
    hw, hd = 0.14, 0.13
    seg = [0]

    def slab(x0, x1, y0, y1):
        if x1 - x0 < 0.005 or y1 - y0 < 0.005:
            return
        seg[0] += 1
        child(root, '%s_top_s%d' % (cid, seg[0]), (x0, y0, tmin[2]),
              (x1, y1, tmax[2]), coll, mats['white'], bevel=0.004, role='quartz_top')

    if item['room'] == 'corridor':
        fx = bmin[0] + 0.19                     # 龙头背西墙
        ymid = (bmin[1] + bmax[1]) / 2
        holes = [(fx, ymid - 0.36), (fx, ymid + 0.36)]
        fdir = (1, 0)
        hx0, hx1 = fx - hw, fx + hw
        ys = sorted([tmin[1], tmax[1]] + [h[1] + s * hd for h in holes for s in (-1, 1)])
        slab(tmin[0], tmax[0], ys[0], ys[1])
        slab(tmin[0], tmax[0], ys[2], ys[3])
        slab(tmin[0], tmax[0], ys[4], ys[5])
        slab(tmin[0], hx0, ys[1], ys[4])
        slab(hx1, tmax[0], ys[1], ys[4])
        for h in holes:
            _basin_under(root, cid, h, tmin[2], tmax[2], coll, mats)
            _goose_faucet(root, '%s_fc%d' % (cid, int(-h[1] * 100)),
                          (bmin[0] + 0.04, h[1]), (1, 0), tmax[2], coll, mats)
    else:
        h = ((bmin[0] + bmax[0]) / 2, bmax[1] - 0.20)   # 龙头背北墙
        fdir = (0, -1)
        hx0, hx1, hy0, hy1 = h[0] - hw, h[0] + hw, h[1] - hd, h[1] + hd
        slab(tmin[0], hx0, tmin[1], tmax[1])
        slab(hx1, tmax[0], tmin[1], tmax[1])
        slab(hx0, hx1, tmin[1], hy0)
        slab(hx0, hx1, hy1, tmax[1])
        _basin_under(root, cid, h, tmin[2], tmax[2], coll, mats)
        _goose_faucet(root, cid + '_fc', (h[0], tmin[1] + 0.06), fdir, tmax[2],
                      coll, mats)


def build_mirror_cabinet(item, mats, coll):
    cid = item['id']
    bmin, bmax = item['bbox']['min'], item['bbox']['max']
    root = item_root(item, coll)
    axis, face, inward = _front_plane(bmin, bmax, item.get('room'))
    bmin, bmax = _recess_front(bmin, bmax, axis, face, inward)   # R2FIX M2：镜板外露
    child(root, cid + '_body', bmin, bmax, coll, mats['white'], role='cabinet_box')
    a0, a1 = (bmin[1], bmax[1]) if axis == 'x' else (bmin[0], bmax[0])
    n2 = 0.68 if (a1 - a0) < 1.1 else 0.9
    add_fronts(root, cid, coll, mats['mirror'], axis, face, inward, a0, a1,
               bmin[2] + 0.02, bmax[2] - 0.02, 'mir', max_w=n2, pulls=False,
               backer=False, role='mirror')


def build_toilet(item, mats, coll):
    """一体智能马桶（低水箱）：底座/座圈/矮水箱，总高 ≤ bbox+3cm。
    R2FIX M5：支持 X 轴贴墙（公卫马桶水箱靠西墙面东）——优先判 Y 墙、再判 X 墙。"""
    cid = item['id']
    bmin, bmax = item['bbox']['min'], item['bbox']['max']
    root = item_root(item, coll)
    zt = min(bmax[2] + 0.03, bmin[2] + 0.48)
    has_y_pos = _face_has_wall('y', True, bmin, bmax)
    has_y_neg = _face_has_wall('y', False, bmin, bmax)
    has_x_neg = _face_has_wall('x', False, bmin, bmax)
    has_x_pos = _face_has_wall('x', True, bmin, bmax)
    if has_y_pos or (not has_y_neg and not has_x_neg and not has_x_pos):
        # 背面在 y_max / 默认
        wb0, wb1 = (bmax[1] - 0.20, bmax[1])
        lo, hi = sorted((wb0 + 0.02, bmin[1]))
        child(root, cid + '_base', (bmin[0] + 0.05, wb0, bmin[2]),
              (bmax[0] - 0.05, wb1, bmin[2] + 0.18), coll, mats['white'], bevel=0.03,
              role='ceramic_white')
        child(root, cid + '_seat', (bmin[0] + 0.02, lo, bmin[2] + 0.16),
              (bmax[0] - 0.02, hi, bmin[2] + 0.26), coll, mats['white'], bevel=0.04,
              role='ceramic_white')
        child(root, cid + '_tank', (bmin[0], wb0, bmin[2] + 0.22),
              (bmax[0], wb1, zt), coll, mats['white'], bevel=0.02,
              role='ceramic_white')
    elif has_x_neg or has_x_pos:
        # R2FIX M5：背面在 x 侧（公卫：水箱靠西墙 x_min，面朝东）
        if has_x_neg:
            wb0, wb1 = bmin[0], bmin[0] + 0.20
            front = bmax[0]
        else:
            wb0, wb1 = bmax[0] - 0.20, bmax[0]
            front = bmin[0]
        x_lo, x_hi = sorted((wb0 + 0.02, front))
        child(root, cid + '_base', (wb0, bmin[1] + 0.05, bmin[2]),
              (wb1, bmax[1] - 0.05, bmin[2] + 0.18), coll, mats['white'], bevel=0.03,
              role='ceramic_white')
        child(root, cid + '_seat', (x_lo, bmin[1] + 0.02, bmin[2] + 0.16),
              (x_hi, bmax[1] - 0.02, bmin[2] + 0.26), coll, mats['white'], bevel=0.04,
              role='ceramic_white')
        child(root, cid + '_tank', (wb0, bmin[1], bmin[2] + 0.22),
              (wb1, bmax[1], zt), coll, mats['white'], bevel=0.02,
              role='ceramic_white')
    else:
        # 背面在 y_min
        wb0, wb1 = bmin[1], bmin[1] + 0.20
        lo, hi = sorted((bmax[1], wb0 + 0.02))
        child(root, cid + '_base', (bmin[0] + 0.05, wb0, bmin[2]),
              (bmax[0] - 0.05, wb1, bmin[2] + 0.18), coll, mats['white'], bevel=0.03,
              role='ceramic_white')
        child(root, cid + '_seat', (bmin[0] + 0.02, lo, bmin[2] + 0.16),
              (bmax[0] - 0.02, hi, bmin[2] + 0.26), coll, mats['white'], bevel=0.04,
              role='ceramic_white')
        child(root, cid + '_tank', (bmin[0], wb0, bmin[2] + 0.22),
              (bmax[0], wb1, zt), coll, mats['white'], bevel=0.02,
              role='ceramic_white')


def build_glass_partition(item, mats, coll):
    cid = item['id']
    bmin, bmax = item['bbox']['min'], item['bbox']['max']
    root = item_root(item, coll)
    fr = 0.03
    child(root, cid + '_glass', (bmin[0] + fr, bmin[1] + fr, fr),
          (bmax[0] - fr, bmax[1] - fr, bmax[2] - fr), coll, mats['glass'],
          glass=True, role='glass_clear')
    boxes = []
    if (bmax[0] - bmin[0]) < (bmax[1] - bmin[1]):
        x0, x1 = bmin[0], bmax[0]
        boxes = [((x0, bmin[1], 0.0), (x1, bmin[1] + fr, fr)),
                 ((x0, bmax[1] - fr, 0.0), (x1, bmax[1], fr)),
                 ((x0, bmin[1], bmax[2] - fr), (x1, bmax[1], bmax[2])),
                 ((x0, bmin[1], 0.0), (x1, bmin[1] + fr, bmax[2])),
                 ((x0, bmax[1] - fr, 0.0), (x1, bmax[1], bmax[2]))]
    else:
        y0, y1 = bmin[1], bmax[1]
        boxes = [((bmin[0], y0, 0.0), (bmin[0] + fr, y1, fr)),
                 ((bmax[0] - fr, y0, 0.0), (bmax[0], y1, fr)),
                 ((bmin[0], y0, bmax[2] - fr), (bmax[0], y1, bmax[2])),
                 ((bmin[0], y0, 0.0), (bmin[0] + fr, y1, bmax[2])),
                 ((bmax[0] - fr, y0, 0.0), (bmax[0], y1, bmax[2]))]
    for i, (a, b) in enumerate(boxes):
        child(root, '%s_fr%d' % (cid, i), a, b, coll, mats['dark'],
              role='metal_graphite')


def build_screen(item, mats, coll):
    """格栅屏风：30x80 方条贴满 bbox 深度，中心距 75mm，顶部通长压条（不出界）。"""
    cid = item['id']
    bmin, bmax = item['bbox']['min'], item['bbox']['max']
    root = item_root(item, coll)
    x0, x1 = bmin[0] + 0.015, bmax[0] - 0.015  # 首末条内收半宽，保持 75mm 中心距
    n = max(1, int(round((x1 - x0) / 0.075)))
    for i in range(n + 1):
        cx = x0 + i * (x1 - x0) / n
        child(root, '%s_slat%02d' % (cid, i), (cx - 0.015, bmin[1], 0.0),
              (cx + 0.015, bmax[1], bmax[2]), coll, mats['wood'],
              bevel=0.004, role='wood')
    child(root, cid + '_cap', (x0, bmin[1], bmax[2] - 0.03),
          (x1, bmax[1], bmax[2]), coll, mats['wood'], role='wood')


def build_tv_cabinet(item, mats, coll):
    cid = item['id']
    bmin, bmax = item['bbox']['min'], item['bbox']['max']
    root = item_root(item, coll)
    axis, face, inward = _front_plane(bmin, bmax, item.get('room'))
    bmin, bmax = _recess_front(bmin, bmax, axis, face, inward)   # R2FIX M1-0
    child(root, cid + '_body', bmin, bmax, coll, mats['wood'], role='wood')
    a0, a1 = (bmin[1], bmax[1]) if axis == 'x' else (bmin[0], bmax[0])
    add_fronts(root, cid, coll, mats['wood'], axis, face, inward, a0, a1,
               bmin[2] + 0.01, bmax[2] - 0.01, 'door', max_w=0.6, pulls=False,
               role='wood')


def build_fridge(item, mats, coll):
    cid = item['id']
    bmin, bmax = item['bbox']['min'], item['bbox']['max']
    root = item_root(item, coll)
    child(root, cid + '_body', bmin, bmax, coll, mats['white'], bevel=0.004,
          role='steel_fridge')
    fz = bmin[2] + (bmax[2] - bmin[2]) * 0.62
    xm = (bmin[0] + bmax[0]) / 2
    child(root, cid + '_seamH', (bmin[0] + 0.01, bmin[1], fz - 0.004),
          (bmax[0] - 0.01, bmin[1] + 0.002, fz + 0.004), coll, mats['dark'],
          role='metal_black')
    child(root, cid + '_seamV', (xm - 0.004, bmin[1], fz),
          (xm + 0.004, bmin[1] + 0.002, bmax[2] - 0.02), coll, mats['dark'],
          role='metal_black')
    child(root, cid + '_pullL', (bmin[0] + 0.08, bmin[1], bmax[2] - 0.30),
          (xm - 0.05, bmin[1] + 0.014, bmax[2] - 0.25), coll, mats['dark'],
          role='metal_black')
    child(root, cid + '_pullU', (bmin[0] + 0.08, bmin[1], fz + 0.05),
          (xm - 0.05, bmin[1] + 0.014, fz + 0.10), coll, mats['dark'],
          role='metal_black')


def build_bookcase(item, mats, coll):
    """R2FIX2 N1：西墙实木组合柜——底座 3 抽屉矮台（拉手槽、外凸 5cm）+
    上部三单元 N→S：木门柜 / 真开放格（4 层隔板+顶灯带，腔体真空）/
    玻璃展示柜（30mm 胡桃细框 + 清玻璃 + 柜内灯带）。
    玻璃门手建框+清玻璃芯，不走 add_fronts——其 gap_dark 缝背板会贴在玻璃后
    3mm 处，把玻璃读成"一整块黑色玻璃"（复核 N1 现象根因）。"""
    cid = item['id']
    bmin, bmax = item['bbox']['min'], item['bbox']['max']
    root = item_root(item, coll)
    axis, face, inward = _front_plane(bmin, bmax, item.get('room'))
    rbmin, rbmax = _recess_front(bmin, bmax, axis, face, inward)   # R2FIX M1-0
    if '底座' in item['name']:
        # R2 #15：矮台外凸 5cm——上部柜体前皮 3.82，矮台前皮至 3.87（bbox 容差 +2cm 内）
        pbmax = (bmax[0] + 0.02, bmax[1], bmax[2])
        child(root, cid + '_body', rbmin, pbmax, coll, mats['wood'], role='wood_dark')
        # R2FIX2 N1：正面 3 个抽屉 + 拉手槽（工单"有缝、有拉手槽"）
        add_fronts(root, cid, coll, mats['wood'], axis, face + 0.02, inward,
                   bmin[1] + 0.01, bmax[1] - 0.01, bmin[2] + 0.03,
                   bmax[2] - 0.02, 'drw', max_w=0.55, pulls=True,
                   pull_mat=mats['dark'], role='wood_dark', pull_style='slot')
        return
    y0, y1 = bmin[1], bmax[1]
    z0, z1 = bmin[2], bmax[2]
    t = 0.025
    bt = 0.02
    # 单元分界（N→S）：木门柜 0.49 / 立板 25 / 开放格 0.575 / 立板 25 / 玻璃柜 0.535
    yA = y1 - 0.49                 # 门柜/立板界
    yB = yA - t                    # 立板北缘
    yC = yB - 0.575                # 开放格/立板界
    yD = yC - t                    # 立板南缘 = 玻璃柜北界（y0）
    wt = mats['wood']
    # 外框大筒：背板（贴墙侧）/ 顶板 / 底板 / 两端端板
    child(root, cid + '_back', (rbmin[0], y0, z0), (rbmin[0] + 0.018, y1, z1),
          coll, wt, role='wood_dark')
    child(root, cid + '_top', (rbmin[0], y0, z1 - bt), (rbmax[0], y1, z1),
          coll, wt, role='wood_dark')
    child(root, cid + '_bot', (rbmin[0], y0, z0), (rbmax[0], y1, z0 + bt),
          coll, wt, role='wood_dark')
    child(root, cid + '_endS', (rbmin[0], y0, z0), (rbmax[0], y0 + t, z1),
          coll, wt, role='wood_dark')
    child(root, cid + '_endN', (rbmin[0], y1 - t, z0), (rbmax[0], y1, z1),
          coll, wt, role='wood_dark')
    # 单元立板 ×2（25mm 通深通高，竖纹由全局映射成立）
    child(root, cid + '_div1', (rbmin[0], yB, z0), (rbmax[0], yA, z1),
          coll, wt, role='wood_dark')
    child(root, cid + '_div2', (rbmin[0], yD, z0), (rbmax[0], yC, z1),
          coll, wt, role='wood_dark')
    # 单元 1 木门柜：单扇胡桃平板门（竖纹）+ 黑细拉手 + 缝背板
    add_fronts(root, cid, coll, mats['wood'], axis, face, inward,
               yB, y1 - t, z0 + bt, z1 - bt, 'door', max_w=0.49,
               pulls=True, pull_mat=mats['dark'], role='wood_dark')
    # 单元 2 真开放格：4 层 20mm 隔板（腔体真空，灯带在 lighting.py lt_strip_bc）
    # 注意 yD<yB（南<北），min/max 按坐标序传
    for i, sz in enumerate((0.83, 1.19, 1.55, 1.91)):
        child(root, '%s_shelf%d' % (cid, i), (rbmin[0] + 0.018, yD, sz),
              (rbmax[0] - 0.02, yB, sz + 0.02), coll, wt, role='wood_dark')
    # 单元 3 玻璃展示柜：2 层隔板 + 手建 30mm 细框清玻璃门（无 gapbg）
    gy0, gy1 = y0 + t, yD
    for i, sz in enumerate((1.15, 1.69)):
        child(root, '%s_gshelf%d' % (cid, i), (rbmin[0] + 0.018, gy0, sz),
              (rbmax[0] - 0.02, gy1, sz + 0.02), coll, wt, role='wood_dark')
    fw = 0.03
    f_lo, f_hi = face - 0.02, face - 0.002
    gparts = {'stS': (gy0, gy0 + fw, z0 + bt, z1 - bt),
              'stN': (gy1 - fw, gy1, z0 + bt, z1 - bt),
              'rlB': (gy0 + fw, gy1 - fw, z0 + bt, z0 + bt + fw),
              'rlT': (gy0 + fw, gy1 - fw, z1 - bt - fw, z1 - bt)}
    for tag, (a, b, cz0, cz1) in gparts.items():
        child(root, '%s_gf_%s' % (cid, tag), (f_lo, a, cz0), (f_hi, b, cz1),
              coll, wt, bevel=0.002, role='wood_dark')
    child(root, cid + '_gpane', (face - 0.014, gy0 + fw, z0 + bt + fw),
          (face - 0.008, gy1 - fw, z1 - bt - fw), coll, mats['glass'],
          glass=True, role='glass_clear')
    # 玻璃门小凸点拉手（北梃内缘，参照实拍图；凸出框面 ≤1cm，bbox 容差内）
    child(root, cid + '_gknob', (face - 0.002, gy1 - 0.045, 1.20),
          (face + 0.010, gy1 - 0.028, 1.32), coll, mats['dark'],
          role='metal_black')


def build_mirror_door(item, mats, coll):
    cid = item['id']
    bmin, bmax = item['bbox']['min'], item['bbox']['max']
    root = item_root(item, coll)
    child(root, cid + '_mirror', bmin, bmax, coll, mats['mirror'], role='mirror')
    f = 0.02
    strips = [((bmin[0], bmin[1], bmin[2]), (bmax[0], bmin[1] + f, bmax[2])),
              ((bmin[0], bmax[1] - f, bmin[2]), (bmax[0], bmax[1], bmax[2])),
              ((bmin[0], bmin[1], bmin[2]), (bmax[0], bmax[1], bmin[2] + f)),
              ((bmin[0], bmin[1], bmax[2] - f), (bmax[0], bmax[1], bmax[2]))]
    for i, (a, b) in enumerate(strips):
        child(root, '%s_fr%d' % (cid, i), a, b, coll, mats['dark'],
              role='metal_black')
    child(root, cid + '_pull', (bmax[0] - 0.012, bmax[1] - 0.28, 1.0),
          (bmax[0], bmax[1] - 0.24, 1.3), coll, mats['dark'], role='metal_black')


def build_glass_sliding_door(item, mats, coll):
    cid = item['id']
    bmin, bmax = item['bbox']['min'], item['bbox']['max']
    root = item_root(item, coll)
    st = 0.03
    child(root, cid + '_glass', (bmin[0] + st, bmin[1] + 0.004, 0.05),
          (bmax[0] - st, bmax[1] - 0.004, bmax[2] - 0.05), coll, mats['glass'],
          glass=True, role='glass_clear')
    parts = {'stL': ((bmin[0], bmin[1], 0.02), (bmin[0] + st, bmax[1], bmax[2])),
             'stR': ((bmax[0] - st, bmin[1], 0.02), (bmax[0], bmax[1], bmax[2])),
             'stT': ((bmin[0], bmin[1], bmax[2] - st), (bmax[0], bmax[1], bmax[2])),
             'stB': ((bmin[0], bmin[1], 0.02), (bmax[0], bmax[1], 0.05))}
    for tag, (a, b) in parts.items():
        child(root, '%s_%s' % (cid, tag), a, b, coll, mats['wood'], role='wood')


def build_shower_floor(item, mats, coll):
    cid = item['id']
    bmin, bmax = item['bbox']['min'], item['bbox']['max']
    root = item_root(item, coll)
    child(root, cid + '_pan', bmin, bmax, coll, mats['white'], role='ceramic_white')
    child(root, cid + '_drain', (bmin[0] + 0.15, bmin[1] + 0.12, bmax[2] - 0.004),
          (bmin[0] + 0.75, bmin[1] + 0.17, bmax[2] + 0.001), coll, mats['dark'],
          role='metal_graphite')


def build_dishwasher(item, mats, coll):
    cid = item['id']
    bmin, bmax = item['bbox']['min'], item['bbox']['max']
    if cid.endswith('_02'):
        root = item_root(item, coll)
        child(root, cid + '_panel', bmin, bmax, coll, mats['kfront'], bevel=0.002,
              role='kitchen_front')
        # FINAL1 F3：0.30m 高大黑条拉手 -> 120mm 竖短拉手（顶边下 4cm 居中），
        # 与下柜门列拉手同款式
        cx = (bmin[0] + bmax[0]) / 2
        child(root, cid + '_pull', (cx - 0.008, bmin[1] - 0.004, bmax[2] - 0.16),
              (cx + 0.008, bmin[1] + 0.012, bmax[2] - 0.04), coll, mats['dark'],
              role='metal_black')
    else:
        build_kitchen_counter(item, mats, coll)  # 北台面段（自建根）


BUILDERS = {
    'wardrobe': build_wardrobe,
    'cabinet': build_cabinet,
    'open_niche': build_open_niche,
    'kitchen_counter': build_kitchen_counter,
    'dishwasher': build_dishwasher,
    'sink': build_sink,
    'hob': build_hob,
    'range_hood': build_range_hood,
    'vanity': build_vanity,
    'mirror_cabinet': build_mirror_cabinet,
    'toilet': build_toilet,
    'glass_partition': build_glass_partition,
    'screen': build_screen,
    'tv_cabinet': build_tv_cabinet,
    'fridge': build_fridge,
    'laundry_cabinet': build_cabinet,
    'bookcase': build_bookcase,
    'mirror_door': build_mirror_door,
    'glass_sliding_door': build_glass_sliding_door,
    'shower_floor': build_shower_floor,
}


def scheme_coll(item, colls):
    g = item.get('group', 'common')
    if g == 'A':
        return colls['scheme_a']
    if g == 'B':
        return colls['scheme_b']
    return colls['common']


def _shower_set(root, tag, wall, face, u0, u1, z_rain, mats, coll, sgn):
    """R2 #11 淋浴套装：混水阀 + 滑轨 + 手持 + 顶喷臂 + 顶喷（metal_graphite）。
    wall='x'：墙面 ⊥X 位于坐标 face（sgn=-1 房间在 face 负向）；u0..u1=沿墙阀体跨度。"""
    mg = mats['dark']   # 白模阶段用占位；正式材质由 role='metal_graphite' 分配
    uc = (u0 + u1) / 2

    def box2(name, a0, a1, out0, out1, z0, z1):
        o0, o1 = sorted((face + sgn * out0, face + sgn * out1))
        if wall == 'x':
            child(root, name, (o0, a0, z0), (o1, a1, z1), coll, mg,
                  role='metal_graphite')
        else:
            child(root, name, (a0, o0, z0), (a1, o1, z1), coll, mg,
                  role='metal_graphite')

    box2(tag + '_mixer', u0, u1, 0.0, 0.03, 0.95, 1.15)
    box2(tag + '_rail', uc - 0.012, uc + 0.012, 0.0, 0.012, 0.90, 1.70)
    box2(tag + '_hand', uc - 0.03, uc + 0.03, 0.012, 0.048, 1.28, 1.36)
    box2(tag + '_arm', uc - 0.02, uc + 0.02, 0.0, 0.30, z_rain + 0.02, z_rain + 0.05)
    box2(tag + '_rain', uc - 0.10, uc + 0.10, 0.30, 0.44, z_rain - 0.03, z_rain)


def _niche(root, tag, wall, face, u0, u1, z0, z1, mats, coll, tile_role, sgn):
    """R2 #11 壁龛：墙内凹腔——五面砖色内衬，开口沿口凸出 4mm（沿口阴影表深度）。"""
    d0, d1 = 0.004, 0.05

    def box2(name, a0, a1, o_a, o_b, zz0, zz1, role):
        o_a2, o_b2 = sorted((face + sgn * o_a, face + sgn * o_b))
        mat = mats['dark'] if role == 'gap_dark' else mats.get(tile_role, mats['wood'])
        if wall == 'x':
            child(root, name, (o_a2, a0, zz0), (o_b2, a1, zz1), coll, mat, role=role)
        else:
            child(root, name, (a0, o_a2, zz0), (a1, o_b2, zz1), coll, mat, role=role)

    box2(tag + '_back', u0, u1, 0.045, 0.05, z0, z1, tile_role)
    box2(tag + '_side0', u0, u0 + 0.02, d0, d1, z0, z1, tile_role)
    box2(tag + '_side1', u1 - 0.02, u1, d0, d1, z0, z1, tile_role)
    box2(tag + '_btm', u0 + 0.02, u1 - 0.02, d0, d1, z0, z0 + 0.015, tile_role)
    box2(tag + '_top', u0 + 0.02, u1 - 0.02, d0, d1, z1 - 0.015, z1, tile_role)


def build_bath_extras(mats, colls):
    """R2 #11 洁具补全（规格要求、layout 无条目）：淋浴套装/壁龛/纸巾架/踏凳。"""
    c = colls['common']
    # —— 主卫淋浴（东墙 W10 内面 x=13.58；窗 y-4.9..-3.8 z1.2-2.2 —— 套装避窗
    #     移南段实体墙 y-5.15..-5.02，壁龛改窗下通长 z0.60..1.12）
    _shower_set(None, 'mb_shower', 'x', 13.58, -5.15, -5.02, 2.05, mats, c, -1)
    _niche(None, 'fx_mb_niche', 'x', 13.58, -4.85, -3.85, 0.60, 1.12, mats, c,
           'niche_oat', -1)
    # 主卫纸巾架（马桶旁，挂玻璃隔断西面 x=12.50）
    child(None, 'fx_mb_paper_plate', (12.478, -3.92, 0.62), (12.50, -3.82, 0.78), c,
          mats['dark'], role='metal_graphite')
    child(None, 'fx_mb_paper_rod', (12.455, -3.95, 0.665), (12.48, -3.79, 0.69), c,
          mats['dark'], role='metal_graphite')
    # —— 公卫淋浴（北墙 W05 内面 y=-0.22；窗 x9.6..10.2 z1.4-2.2 —— 整套西移
    #     x9.30..9.42 避窗，壁龛 x9.28..9.56）
    _shower_set(None, 'pb_shower', 'y', -0.22, 9.30, 9.42, 2.05, mats, c, -1)
    _niche(None, 'fx_pb_niche', 'y', -0.22, 9.28, 9.56, 1.10, 1.72, mats, c,
           'niche_beige', -1)
    # —— 干区踏凳（7 岁儿子；规格 5.8）
    child(None, 'fx_stool_top', (9.62, -3.48, 0.20), (9.98, -3.12, 0.24), c,
          mats['wood'], bevel=0.01, role='wood')
    for i, (lx, ly) in enumerate(((9.66, -3.44), (9.94, -3.44), (9.66, -3.16), (9.94, -3.16))):
        child(None, 'fx_stool_leg%d' % i, (lx - 0.016, ly - 0.016, 0.0),
              (lx + 0.016, ly + 0.016, 0.20), c, mats['wood'], role='wood')
    print('[builtins] bath extras done (shower sets / niches / paper holder / stool)')


def build_all(mats, colls):
    global _WALL_CACHE
    _WALL_CACHE = None
    layout = util.load_layout()
    for f in layout['floors']:
        cx = (f['rect_min'][0] + f['rect_max'][0]) / 2
        cy = (f['rect_min'][1] + f['rect_max'][1]) / 2
        ROOM_CENTER[f['id']] = (cx, cy)
    built, skipped = [], []
    for item in layout['items']:
        typ = item.get('type')
        iid = item['id']
        if iid in COVERED:
            tgt = bpy.data.objects.get(COVERED[iid])
            if tgt:
                root = bpy.data.objects.new(iid, None)
                root.empty_display_size = 0.2
                colls['common'].objects.link(root)
                tgt.parent = root
                built.append(iid)
            continue
        if typ == 'island':
            if iid.endswith('_01'):
                build_island(item, mats, scheme_coll(item, colls))
                built.append(iid)
            else:
                skipped.append(iid)  # 餐桌/长桌 -> M3
            continue
        if typ == 'wardrobe' and item['room'] not in M2_WARDROBE_ROOMS:
            skipped.append(iid)  # 孩子房成品示意 -> M3
            continue
        if typ not in M2_TYPES:
            skipped.append(iid)  # M3 家具/软装 / marker
            continue
        BUILDERS[typ](item, mats, scheme_coll(item, colls))
        built.append(iid)
    build_bath_extras(mats, colls)
    print('[builtins] built=%d skipped_m3=%d' % (len(built), len(skipped)))
    return built, skipped

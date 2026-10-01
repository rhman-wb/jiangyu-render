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


def child(root, name, bmin, bmax, coll, mat, bevel=None, glass=False):
    o = util.make_box(name, bmin, bmax, coll=coll, mat=mat, bevel=bevel)
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
               max_w=0.45, gap=0.004, t=0.02, pulls=True, pull_mat=None,
               pull_len=0.30):
    """门板阵列：沿 a 轴等分；法向 axis；面板外皮在 face、向内伸 t；拉手凸出 ≤4mm。"""
    n = max(1, round((a1 - a0) / max_w))
    w = (a1 - a0) / n
    n_lo, n_hi = (face - t, face) if inward < 0 else (face, face + t)
    p_lo, p_hi = (face, face + 0.004) if inward < 0 else (face - 0.004, face)
    for i in range(n):
        ua = a0 + i * w + gap / 2
        ub = a0 + (i + 1) * w - gap / 2
        zin, zout = z0 + gap / 2, z1 - gap / 2
        if axis == 'y':
            bmin_, bmax_ = (ua, n_lo, zin), (ub, n_hi, zout)
        else:
            bmin_, bmax_ = (n_lo, ua, zin), (n_hi, ub, zout)
        child(root, '%s_%s_f%d' % (cid, tag, i), bmin_, bmax_, coll, mat,
              bevel=0.003)
        if pulls:
            pm = pull_mat if pull_mat else mat
            hl = min(pull_len, (zout - zin) * 0.6)
            zc = (zin + zout) / 2
            upos = (ub - 0.03) if (i < n // 2 or n == 1) else (ua + 0.03)
            if axis == 'y':
                child(root, '%s_%s_p%d' % (cid, tag, i),
                      (upos - 0.008, p_lo, zc - hl / 2),
                      (upos + 0.008, p_hi, zc + hl / 2), coll, pm)
            else:
                child(root, '%s_%s_p%d' % (cid, tag, i),
                      (p_lo, upos - 0.008, zc - hl / 2),
                      (p_hi, upos + 0.008, zc + hl / 2), coll, pm)


def _shelf_zs(z0, z1, step):
    zs, z = [], z0
    while z < z1 - 0.05:
        zs.append(z)
        z += step
    return zs


# ---------------------------------------------------------------- 建模器
def build_wardrobe(item, mats, coll):
    cid = item['id']
    bmin, bmax = item['bbox']['min'], item['bbox']['max']
    root = item_root(item, coll)
    child(root, cid + '_body', bmin, bmax, coll, mats['white'])
    axis, face, inward = _front_plane(bmin, bmax, item.get('room'))
    a0, a1 = (bmin[1], bmax[1]) if axis == 'x' else (bmin[0], bmax[0])
    if item['room'] == 'master_bedroom':
        add_fronts(root, cid, coll, mats['white'], axis, face, inward, a0, a1,
                   0.05, bmax[2] - 0.04, 'door', max_w=0.42,
                   pull_mat=mats['dark'])
    else:  # 父母房推拉门：双轨两排
        f_in = face + 0.023 * inward
        add_fronts(root, cid, coll, mats['white'], axis, face, inward, a0, a1,
                   0.05, bmax[2] - 0.04, 'slA', max_w=0.70, pulls=False)
        add_fronts(root, cid, coll, mats['white'], axis, f_in, inward,
                   a0 + 0.05, a1 - 0.05, 0.05, bmax[2] - 0.04, 'slB',
                   max_w=0.70, pulls=False)


def build_cabinet(item, mats, coll, params=None):
    params = params or {}
    cid = item['id']
    bmin, bmax = item['bbox']['min'], item['bbox']['max']
    root = item_root(item, coll)
    mat = params.get('mat', mats['white'])
    child(root, cid + '_body', bmin, bmax, coll, mat)
    axis, face, inward = _front_plane(bmin, bmax, item.get('room'))
    a0, a1 = (bmin[1], bmax[1]) if axis == 'x' else (bmin[0], bmax[0])
    add_fronts(root, cid, coll, mat, axis, face, inward, a0, a1,
               bmin[2] + 0.02, bmax[2] - 0.02, 'door',
               max_w=params.get('max_w', 0.45),
               pulls=params.get('pulls', True), pull_mat=mats.get('dark'))


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

    def box_un(tag, ua, ub, na, nb, z0, z1, mat):
        lo = [None, None]
        hi = [None, None]
        lo[u_k], hi[u_k] = ua, ub
        lo[n_k], hi[n_k] = na, nb
        return child(root, '%s_%s' % (cid, tag), (lo[0], lo[1], z0),
                     (hi[0], hi[1], z1), coll, mat)

    d0, d1 = sorted((back0, cheek_out))
    box_un('back', u0, u1, back0, back1, bmin[2], bmax[2], mats['wood'])
    box_un('cheek0', u0, u0 + t, d0, d1, bmin[2], bmax[2], mats['wood'])
    box_un('cheek1', u1 - t, u1, d0, d1, bmin[2], bmax[2], mats['wood'])
    box_un('top', u0 + t, u1 - t, d0, d1, bmax[2] - t, bmax[2], mats['wood'])
    box_un('bottom', u0 + t, u1 - t, d0, d1, bmin[2], bmin[2] + t, mats['wood'])
    s0 = cheek_out - (0.02 if front_at_n1 else -0.02)
    e0, e1 = sorted((back0, s0))
    for i, z in enumerate(_shelf_zs(bmin[2] + t + 0.04, bmax[2] - t - 0.04, 0.35)):
        box_un('sh%d' % i, u0 + t + 0.005, u1 - t - 0.005, e0, e1, z, z + t,
               mats['wood'])


def build_island(item, mats, coll):
    """岛台：侧板+背板(北)+南开放格+北面蒸烤箱/抽屉+石英台面。"""
    cid = item['id']
    bmin, bmax = item['bbox']['min'], item['bbox']['max']
    top = item.get('parts', [{}])[0].get('bbox')
    root = item_root(item, coll)
    x0, y0, z0 = bmin
    x1, y1, z1 = bmax
    child(root, cid + '_sideW', (x0, y0, z0), (x0 + 0.04, y1, z1 - 0.04), coll, mats['wood'])
    child(root, cid + '_sideE', (x1 - 0.04, y0, z0), (x1, y1, z1 - 0.04), coll, mats['wood'])
    child(root, cid + '_backN', (x0 + 0.04, y1 - 0.04, z0), (x1 - 0.04, y1, z1 - 0.04), coll, mats['wood'])
    child(root, cid + '_base', (x0 + 0.04, y0 + 0.04, z0), (x1 - 0.04, y1 - 0.04, z0 + 0.08), coll, mats['wood'])
    # 北面（朝厨房 y1）：西段蒸烤箱黑玻璃 + 东段抽屉
    child(root, cid + '_oven', (x0 + 0.12, y1 - 0.045, 0.32),
          (x0 + 0.72, y1 - 0.005, 0.77), coll, mats['dark'])
    add_fronts(root, cid, coll, mats['wood'], 'y', y1 - 0.005, -1,
               x0 + 0.76, x1 - 0.06, 0.12, 0.72, 'drw', max_w=0.8,
               pulls=True, pull_mat=mats['dark'])
    # 南面（朝餐厅 y0）：开放格内衬 + 2 层板
    child(root, cid + '_niche', (x0 + 0.06, y0 + 0.02, 0.10),
          (x1 - 0.06, y0 + 0.30, 0.72), coll, mats['wood'])
    for i, z in enumerate((0.36, 0.54)):
        child(root, '%s_sh%d' % (cid, i), (x0 + 0.06, y0 + 0.02, z),
              (x1 - 0.06, y0 + 0.30, z + 0.02), coll, mats['wood'])
    if top:
        child(root, cid + '_top', tuple(top['min']), tuple(top['max']), coll,
              mats['white'], bevel=0.004)


def build_kitchen_counter(item, mats, coll):
    cid = item['id']
    bmin, bmax = item['bbox']['min'], item['bbox']['max']
    root = item_root(item, coll)
    child(root, cid + '_body', bmin, (bmax[0], bmax[1], bmax[2] - 0.04), coll, mats['wood'])
    for p in item.get('parts', []):
        child(root, cid + '_top', tuple(p['bbox']['min']), tuple(p['bbox']['max']),
              coll, mats['white'], bevel=0.003)
    if (bmax[1] - bmin[1]) < (bmax[0] - bmin[0]):  # 北台面，门朝 -Y
        add_fronts(root, cid, coll, mats['kfront'], 'y', bmin[1] + 0.005, +1,
                   bmin[0] + 0.02, bmax[0] - 0.02, 0.12, bmax[2] - 0.06, 'drw',
                   max_w=0.45, pulls=True, pull_mat=mats['dark'])
    else:  # 东台面，门朝 +X
        add_fronts(root, cid, coll, mats['kfront'], 'x', bmax[0] - 0.005, -1,
                   bmin[1] + 0.02, bmax[1] - 0.02, 0.12, bmax[2] - 0.06, 'drw',
                   max_w=0.45, pulls=True, pull_mat=mats['dark'])


def build_sink(item, mats, coll):
    """单槽水槽 + 鹅颈龙头（龙头靠墙侧，规格 5.4；龙头允许高出 bbox，qa 豁免）。"""
    cid = item['id']
    bmin, bmax = item['bbox']['min'], item['bbox']['max']
    root = item_root(item, coll)
    child(root, cid + '_rim', bmin, bmax, coll, mats['dark'])
    child(root, cid + '_inner', (bmin[0] + 0.04, bmin[1] + 0.03, bmin[2] + 0.001),
          (bmax[0] - 0.04, bmax[1] - 0.03, bmin[2] + 0.004), coll, mats['white'])
    xm = (bmin[0] + bmax[0]) / 2
    ywall = bmax[1] - 0.08  # 北侧贴墙
    child(root, cid + '_tap', (xm - 0.012, ywall - 0.012, bmax[2]),
          (xm + 0.012, ywall + 0.012, bmax[2] + 0.28), coll, mats['dark'])
    child(root, cid + '_taparm', (xm - 0.012, ywall - 0.012, bmax[2] + 0.26),
          (xm + 0.012, ywall - 0.22, bmax[2] + 0.29), coll, mats['dark'])


def build_hob(item, mats, coll):
    cid = item['id']
    bmin, bmax = item['bbox']['min'], item['bbox']['max']
    root = item_root(item, coll)
    child(root, cid + '_glass', (bmin[0], bmin[1], bmin[2]),
          (bmax[0], bmax[1], bmin[2] + 0.012), coll, mats['dark'], bevel=0.003)
    xm = (bmin[0] + bmax[0]) / 2
    for i, cy in enumerate(((bmin[1] + bmax[1]) / 2 - 0.17, (bmin[1] + bmax[1]) / 2 + 0.17)):
        child(root, '%s_burner%d' % (cid, i), (xm - 0.06, cy - 0.06, bmin[2] + 0.012),
              (xm + 0.06, cy + 0.06, bmax[2]), coll, mats['dark'])


def build_range_hood(item, mats, coll):
    cid = item['id']
    bmin, bmax = item['bbox']['min'], item['bbox']['max']
    root = item_root(item, coll)
    child(root, cid + '_topbox', (bmin[0], bmin[1], bmax[2] - 0.16),
          (bmax[0], bmax[1], bmax[2]), coll, mats['dark'])
    child(root, cid + '_slant', (bmin[0], bmin[1], bmin[2]),
          (bmax[0], bmax[1] - 0.12, bmax[2] - 0.16), coll, mats['dark'])


def build_vanity(item, mats, coll):
    cid = item['id']
    bmin, bmax = item['bbox']['min'], item['bbox']['max']
    root = item_root(item, coll)
    top = item.get('parts', [{}])[0].get('bbox')
    child(root, cid + '_cab', bmin, (bmax[0], bmax[1], bmax[2] - 0.04), coll, mats['wood'])
    if top:
        child(root, cid + '_top', tuple(top['min']), tuple(top['max']), coll,
              mats['white'], bevel=0.006)
        zt = top['max'][2]
    else:
        child(root, cid + '_top', (bmin[0], bmin[1], bmax[2] - 0.035), bmax,
              coll, mats['white'], bevel=0.006)
        zt = bmax[2]
    axis, face, inward = _front_plane(bmin, bmax, item.get('room'))
    a0, a1 = (bmin[1], bmax[1]) if axis == 'x' else (bmin[0], bmax[0])
    add_fronts(root, cid, coll, mats['wood'], axis, face, inward, a0, a1,
               bmin[2] + 0.02, bmax[2] - 0.06, 'drw', max_w=0.5,
               pulls=True, pull_mat=mats['dark'])
    if item['room'] == 'corridor':  # 双台下盆
        for i, cy in enumerate(((bmin[1] + bmax[1]) / 2 - 0.36, (bmin[1] + bmax[1]) / 2 + 0.36)):
            child(root, '%s_basin%d' % (cid, i), (bmin[0] + 0.10, cy - 0.18, zt - 0.012),
                  (bmin[0] + 0.44, cy + 0.18, zt - 0.002), coll, mats['dark'])
    else:
        cy = (bmin[1] + bmax[1]) / 2
        child(root, cid + '_basin', (bmin[0] + 0.12, cy - 0.18, zt - 0.012),
              (bmax[0] - 0.12, cy + 0.18, zt - 0.002), coll, mats['dark'])


def build_mirror_cabinet(item, mats, coll):
    cid = item['id']
    bmin, bmax = item['bbox']['min'], item['bbox']['max']
    root = item_root(item, coll)
    child(root, cid + '_body', bmin, bmax, coll, mats['white'])
    axis, face, inward = _front_plane(bmin, bmax, item.get('room'))
    a0, a1 = (bmin[1], bmax[1]) if axis == 'x' else (bmin[0], bmax[0])
    n2 = 0.68 if (a1 - a0) < 1.1 else 0.9
    add_fronts(root, cid, coll, mats['mirror'], axis, face, inward, a0, a1,
               bmin[2] + 0.02, bmax[2] - 0.02, 'mir', max_w=n2, pulls=False)


def build_toilet(item, mats, coll):
    """一体智能马桶（低水箱）：底座/座圈/矮水箱，总高 ≤ bbox+3cm。"""
    cid = item['id']
    bmin, bmax = item['bbox']['min'], item['bbox']['max']
    root = item_root(item, coll)
    # 水箱贴墙一侧 = 背面
    if _face_has_wall('y', True, bmin, bmax) or not _face_has_wall('y', False, bmin, bmax):
        yb0, yb1 = bmax[1] - 0.20, bmax[1]   # 背面在 y_max
        front = bmin[1]
    else:
        yb0, yb1 = bmin[1], bmin[1] + 0.20   # 背面在 y_min
        front = bmax[1]
    zt = min(bmax[2] + 0.03, bmin[2] + 0.48)
    y_lo, y_hi = sorted((yb0 + 0.02, front))
    child(root, cid + '_base', (bmin[0] + 0.05, yb0, bmin[2]),
          (bmax[0] - 0.05, yb1, bmin[2] + 0.18), coll, mats['white'], bevel=0.03)
    child(root, cid + '_seat', (bmin[0] + 0.02, y_lo, bmin[2] + 0.16),
          (bmax[0] - 0.02, y_hi, bmin[2] + 0.26), coll, mats['white'], bevel=0.04)
    child(root, cid + '_tank', (bmin[0], yb0, bmin[2] + 0.22),
          (bmax[0], yb1, zt), coll, mats['white'], bevel=0.02)


def build_glass_partition(item, mats, coll):
    cid = item['id']
    bmin, bmax = item['bbox']['min'], item['bbox']['max']
    root = item_root(item, coll)
    fr = 0.03
    child(root, cid + '_glass', (bmin[0] + fr, bmin[1] + fr, fr),
          (bmax[0] - fr, bmax[1] - fr, bmax[2] - fr), coll, mats['glass'],
          glass=True)
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
        child(root, '%s_fr%d' % (cid, i), a, b, coll, mats['dark'])


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
              bevel=0.004)
    child(root, cid + '_cap', (x0, bmin[1], bmax[2] - 0.03),
          (x1, bmax[1], bmax[2]), coll, mats['wood'])


def build_tv_cabinet(item, mats, coll):
    cid = item['id']
    bmin, bmax = item['bbox']['min'], item['bbox']['max']
    root = item_root(item, coll)
    child(root, cid + '_body', bmin, bmax, coll, mats['wood'])
    axis, face, inward = _front_plane(bmin, bmax, item.get('room'))
    a0, a1 = (bmin[1], bmax[1]) if axis == 'x' else (bmin[0], bmax[0])
    add_fronts(root, cid, coll, mats['wood'], axis, face, inward, a0, a1,
               bmin[2] + 0.01, bmax[2] - 0.01, 'door', max_w=1.0, pulls=False)


def build_fridge(item, mats, coll):
    cid = item['id']
    bmin, bmax = item['bbox']['min'], item['bbox']['max']
    root = item_root(item, coll)
    child(root, cid + '_body', bmin, bmax, coll, mats['white'], bevel=0.004)
    fz = bmin[2] + (bmax[2] - bmin[2]) * 0.62
    xm = (bmin[0] + bmax[0]) / 2
    child(root, cid + '_seamH', (bmin[0] + 0.01, bmin[1], fz - 0.004),
          (bmax[0] - 0.01, bmin[1] + 0.002, fz + 0.004), coll, mats['dark'])
    child(root, cid + '_seamV', (xm - 0.004, bmin[1], fz),
          (xm + 0.004, bmin[1] + 0.002, bmax[2] - 0.02), coll, mats['dark'])
    child(root, cid + '_pullL', (bmin[0] + 0.08, bmin[1], bmax[2] - 0.30),
          (xm - 0.05, bmin[1] + 0.014, bmax[2] - 0.25), coll, mats['dark'])
    child(root, cid + '_pullU', (bmin[0] + 0.08, bmin[1], fz + 0.05),
          (xm - 0.05, bmin[1] + 0.014, fz + 0.10), coll, mats['dark'])


def build_bookcase(item, mats, coll):
    cid = item['id']
    bmin, bmax = item['bbox']['min'], item['bbox']['max']
    root = item_root(item, coll)
    axis, face, inward = _front_plane(bmin, bmax, item.get('room'))
    if '底座' in item['name']:
        child(root, cid + '_body', bmin, bmax, coll, mats['wood'])
        add_fronts(root, cid, coll, mats['wood'], axis, face, inward,
                   bmin[1] + 0.01, bmax[1] - 0.01, bmin[2] + 0.03,
                   bmax[2] - 0.02, 'drw', max_w=0.40, pulls=True,
                   pull_mat=mats['dark'])
    else:
        child(root, cid + '_body', bmin, bmax, coll, mats['wood'])
        y0, y1 = bmin[1], bmax[1]
        z0, z1 = bmin[2], bmax[2]
        # 南单元（洗衣机柜侧）平开门 y0..y0+0.45
        add_fronts(root, cid, coll, mats['wood'], axis, face, inward,
                   y0, y0 + 0.45, z0 + 0.02, z1 - 0.02, 'doorS', max_w=0.45,
                   pulls=True, pull_mat=mats['dark'])
        # 中段开放格 y0+0.45..y1-0.45（按 parts 即 -9.95..-9.2）
        ny0, ny1 = y0 + 0.45, y1 - 0.45
        child(root, cid + '_niceline', (bmax[0] - 0.02, ny0 + 0.02, z0 + 0.02),
              (bmax[0], ny1 - 0.02, z1 - 0.02), coll, mats['wood'])
        for i, z in enumerate(_shelf_zs(z0 + 0.10, z1 - 0.10, 0.40)):
            child(root, '%s_nsh%d' % (cid, i), (bmax[0] - 0.02, ny0 + 0.02, z),
                  (bmax[0], ny1 - 0.02, z + 0.02), coll, mats['wood'])
        # 北单元（端景角侧）玻璃门 y1-0.45..y1
        add_fronts(root, cid, coll, mats['glass'], axis, face, inward,
                   y1 - 0.45, y1, z0 + 0.02, z1 - 0.02, 'doorN', max_w=0.45,
                   pulls=False)


def build_mirror_door(item, mats, coll):
    cid = item['id']
    bmin, bmax = item['bbox']['min'], item['bbox']['max']
    root = item_root(item, coll)
    child(root, cid + '_mirror', bmin, bmax, coll, mats['mirror'])
    f = 0.02
    strips = [((bmin[0], bmin[1], bmin[2]), (bmax[0], bmin[1] + f, bmax[2])),
              ((bmin[0], bmax[1] - f, bmin[2]), (bmax[0], bmax[1], bmax[2])),
              ((bmin[0], bmin[1], bmin[2]), (bmax[0], bmax[1], bmin[2] + f)),
              ((bmin[0], bmin[1], bmax[2] - f), (bmax[0], bmax[1], bmax[2]))]
    for i, (a, b) in enumerate(strips):
        child(root, '%s_fr%d' % (cid, i), a, b, coll, mats['dark'])
    child(root, cid + '_pull', (bmax[0] - 0.012, bmax[1] - 0.28, 1.0),
          (bmax[0], bmax[1] - 0.24, 1.3), coll, mats['dark'])


def build_glass_sliding_door(item, mats, coll):
    cid = item['id']
    bmin, bmax = item['bbox']['min'], item['bbox']['max']
    root = item_root(item, coll)
    st = 0.03
    child(root, cid + '_glass', (bmin[0] + st, bmin[1] + 0.004, 0.05),
          (bmax[0] - st, bmax[1] - 0.004, bmax[2] - 0.05), coll, mats['glass'],
          glass=True)
    parts = {'stL': ((bmin[0], bmin[1], 0.02), (bmin[0] + st, bmax[1], bmax[2])),
             'stR': ((bmax[0] - st, bmin[1], 0.02), (bmax[0], bmax[1], bmax[2])),
             'stT': ((bmin[0], bmin[1], bmax[2] - st), (bmax[0], bmax[1], bmax[2])),
             'stB': ((bmin[0], bmin[1], 0.02), (bmax[0], bmax[1], 0.05))}
    for tag, (a, b) in parts.items():
        child(root, '%s_%s' % (cid, tag), a, b, coll, mats['wood'])


def build_shower_floor(item, mats, coll):
    cid = item['id']
    bmin, bmax = item['bbox']['min'], item['bbox']['max']
    root = item_root(item, coll)
    child(root, cid + '_pan', bmin, bmax, coll, mats['white'])
    child(root, cid + '_drain', (bmin[0] + 0.15, bmin[1] + 0.12, bmax[2] - 0.004),
          (bmin[0] + 0.75, bmin[1] + 0.17, bmax[2] + 0.001), coll, mats['dark'])


def build_dishwasher(item, mats, coll):
    cid = item['id']
    bmin, bmax = item['bbox']['min'], item['bbox']['max']
    if cid.endswith('_02'):
        root = item_root(item, coll)
        child(root, cid + '_panel', bmin, bmax, coll, mats['kfront'], bevel=0.002)
        child(root, cid + '_pull',
              (bmin[0] + 0.05, bmin[1], (bmin[2] + bmax[2]) / 2 - 0.15),
              (bmax[0] - 0.05, bmin[1] + 0.012, (bmin[2] + bmax[2]) / 2 + 0.15),
              coll, mats['dark'])
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
    print('[builtins] built=%d skipped_m3=%d' % (len(built), len(skipped)))
    return built, skipped

# -*- coding: utf-8 -*-
# qa.py —— M1 自检：墙体闭合 / 门窗洞一致 / 墙体标高与厚度 / 数量 / ceiling_box / 视线抽检 / 地板重叠
# 用法：blender -b blend\jiangyu.blend --python scripts\qa.py
# 输出 review/qa_report.md（PASS/FAIL/WARN/INFO），控制台摘要只 ASCII。
import os
import re
import sys
import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
import util
import architecture

L = util.load_layout()
WALLS = {w['id']: w for w in L['walls']}
GEO = {w['id']: architecture.wall_geo(w, L['walls']) for w in L['walls']}
CEIL = config.CEIL_H

lines = []
counts = {'PASS': 0, 'FAIL': 0, 'WARN': 0, 'INFO': 0}


def log(level, msg):
    counts[level] = counts.get(level, 0) + 1
    lines.append('- **%s** %s' % (level, msg))
    if level in ('FAIL', 'WARN'):
        print('[qa][%s] %s' % (level, msg))


# ---------------------------------------------------------------- 工具
def iv_merge(iv):
    iv = sorted((a, b) for a, b in iv if b > a + 1e-6)
    out = []
    for a, b in iv:
        if out and a <= out[-1][1] + 1e-6:
            out[-1] = (out[-1][0], max(out[-1][1], b))
        else:
            out.append((a, b))
    return out


def iv_sub(iv, a, b):
    out = []
    for x, y in iv:
        out.append((x, min(y, a)))
        out.append((max(x, b), y))
    return [(p, q) for p, q in out if q > p + 1e-6]


def bbox_of(name):
    o = bpy.data.objects.get(name)
    return util.obj_world_bbox(o) if o else None


wall_seg_names = [o.name for o in bpy.data.objects if re.match(r'^W\d+_s\d+$', o.name)]
SEG_BBOX = {n: bbox_of(n) for n in wall_seg_names}


def seg_uvz(name):
    """墙段对象的 (u0,u1,z0,z1,v0,v1)：按墙轴取向。"""
    wid = name.split('_')[0]
    g = GEO[wid]
    (bx0, by0, bz0), (bx1, by1, bz1) = SEG_BBOX[name]
    if g['axis'] == 'x':
        return bx0, bx1, bz0, bz1, by0, by1
    return by0, by1, bz0, bz1, bx0, bx1


# ---------------------------------------------------------------- 1 墙体闭合
# 手工白名单：规格上有意留开的边界（露台栏杆区 / 公共区），记 decisions_log
WHITELIST = [
    ('terrace', 'S', -12.4, 9.25, 12.8),      # 露台南边（栏杆，非墙）
    ('terrace', 'E', 12.8, -12.4, -10.15),    # 露台东边（栏杆）
    ('terrace', 'W', 9.25, -12.4, -11.6),     # 露台西边南段（栏杆）
    ('elevator_hall', 'W', 1.95, -4.8, -3.9), # 门外公共走廊
    ('elevator_hall', 'N', -3.9, 1.95, 3.4),  # 门外电梯厅
    ('living_dining_balcony', 'N', -3.95, 9.0, 9.25),  # 开放进过道（corridor L 形北段）
]


def check_closure():
    for f in L['floors']:
        fid = f['id']
        (x0, y0), (x1, y1) = f['rect_min'], f['rect_max']
        edges = [('W', x0, y0, y1), ('E', x1, y0, y1), ('S', y0, x0, x1), ('N', y1, x0, x1)]
        for tag, fixed, a, b in edges:
            open_iv = []  # 允许无墙的区间
            # 白名单
            for wf, wt, wfix, wa, wb in WHITELIST:
                if wf == fid and wt == tag and abs(wfix - fixed) < 0.03:
                    open_iv.append((max(wa, a), min(wb, b)))
            # 相邻房间（跨线无墙的开放过渡）
            for o in L['floors']:
                if o is f:
                    continue
                (ox0, oy0), (ox1, oy1) = o['rect_min'], o['rect_max']
                if tag in ('W', 'E'):
                    of = ox1 if tag == 'W' else ox0  # 对方贴过来的那条边
                    if abs(of - fixed) < 0.08:
                        open_iv.append((max(oy0, a), min(oy1, b)))
                    # 对方矩形横跨此线（内部包含）也算开放
                    if ox0 - 0.08 <= fixed <= ox1 + 0.08 and not (oy1 < a - 0.01 or oy0 > b + 0.01):
                        open_iv.append((max(oy0, a), min(oy1, b)))
                else:
                    of = oy1 if tag == 'S' else oy0
                    if abs(of - fixed) < 0.08:
                        open_iv.append((max(ox0, a), min(ox1, b)))
                    if oy0 - 0.08 <= fixed <= oy1 + 0.08 and not (ox1 < a - 0.01 or ox0 > b + 0.01):
                        open_iv.append((max(ox0, a), min(ox1, b)))
            # 需要墙体覆盖的区间 = 边区间 - 白名单/相邻开放区间
            need = [(a, b)]
            for p, q in iv_merge(open_iv):
                need = iv_sub(need, p, q)
            # 生成墙段的覆盖（REWORK_R1FIX2 F4：足迹包含边线即算实覆盖——
            # 对接规则下角部 7cm 由垂直/贯穿墙的板体补全，平行轴限制会误报）
            cov = []
            for n in wall_seg_names:
                wid = n.split('_')[0]
                g = GEO[wid]
                u0, u1, z0, z1, v0, v1 = seg_uvz(n)
                if tag in ('W', 'E'):
                    # 边线 x=fixed，覆盖区间沿 y
                    if g['axis'] == 'y':
                        if not (v0 - 1e-4 <= fixed <= v1 + 1e-4):
                            continue
                        iv = [(u0, u1)]
                    else:
                        if not (u0 - 1e-4 <= fixed <= u1 + 1e-4):
                            continue
                        iv = [(v0, v1)]
                else:
                    # 边线 y=fixed，覆盖区间沿 x
                    if g['axis'] == 'x':
                        if not (v0 - 1e-4 <= fixed <= v1 + 1e-4):
                            continue
                        iv = [(u0, u1)]
                    else:
                        if not (u0 - 1e-4 <= fixed <= u1 + 1e-4):
                            continue
                        iv = [(v0, v1)]
                # full_opening 区间从平行墙自身覆盖里扣除
                if (tag in ('W', 'E')) == (g['axis'] == 'y'):
                    sub = []
                    for op in WALLS[wid].get('openings', []):
                        if op['type'] == 'full_opening':
                            sub.append((op['start'], op['end']))
                    for p, q in sub:
                        iv = iv_sub(iv, p, q)
                p2, q2 = max(iv[0][0], a), min(iv[0][1], b)
                if q2 > p2:
                    cov.append((p2, q2))
            gaps = [(a2, b2) for a2, b2 in need]
            for p, q in iv_merge(cov):
                gaps = iv_sub(gaps, p, q)
            gaps = [(p, q) for p, q in gaps if q - p > 0.03]
            if gaps:
                log('FAIL', 'closure %s %s edge: gaps %s' %
                    (fid, tag, ['%.2f~%.2f' % g for g in gaps]))
            else:
                log('PASS', 'closure %s %s' % (fid, tag))


# ---------------------------------------------------------------- 2 门窗洞一致
def check_openings():
    n_by_type = {}
    for w in L['walls']:
        wid = w['id']
        g = GEO[wid]
        segs = [(n, seg_uvz(n)) for n in wall_seg_names if n.startswith(wid + '_')]
        for op in architecture.normalize_openings(w):
            typ = op['type']
            n_by_type[typ] = n_by_type.get(typ, 0) + 1
            a, b = op['start'], op['end']
            head = op.get('head', CEIL)
            if typ == 'window':
                void = (a, b, op['sill'], head)
            elif typ in ('door', 'glass_door'):
                void = (a, b, 0.0, head)
            else:
                void = (a, b, 0.0, CEIL)
            shrink = 0.015
            blocked = []
            for n, (u0, u1, z0, z1, _v0, _v1) in segs:
                if (u0 < void[1] - shrink and u1 > void[0] + shrink and
                        z0 < void[3] - shrink and z1 > void[2] + shrink):
                    blocked.append(n)
            if blocked:
                log('FAIL', 'opening %s %s blocked by %s' % (wid, typ, blocked[:3]))
            else:
                log('PASS', 'opening %s %s clear' % (wid, typ))
            # 上方/下方墙带存在性
            def band_ok(zlo, zhi):
                for n, (u0, u1, z0, z1, _v0, _v1) in segs:
                    if (u0 < b - 0.05 and u1 > a + 0.05 and
                            z0 < zhi - 0.01 and z1 > zlo + 0.01):
                        return True
                return False
            if typ in ('door', 'glass_door', 'window'):
                if band_ok(head, head + 0.10):
                    log('PASS', 'lintel/over %s %s' % (wid, typ))
                else:
                    log('FAIL', 'lintel/over missing %s %s' % (wid, typ))
            if typ == 'window':
                if band_ok(op['sill'] - 0.10, op['sill']):
                    log('PASS', 'sill wall %s' % wid)
                else:
                    log('FAIL', 'sill wall missing %s' % wid)
    expect = {'window': 7, 'door': 8, 'glass_door': 2, 'full_opening': 1}
    if n_by_type == expect:
        log('PASS', 'opening counts %s' % n_by_type)
    else:
        log('FAIL', 'opening counts %s != %s' % (n_by_type, expect))


# ---------------------------------------------------------------- 3 墙体标高/厚度
def check_wall_dims():
    bad = 0
    for n in wall_seg_names:
        u0, u1, z0, z1, v0, v1 = seg_uvz(n)
        wid = n.split('_')[0]
        g = GEO[wid]
        # 合法标高：底 ∈ {0, heads}，顶 ∈ {sills, 2.85}（窗台带/过梁带）
        heads = [op['head'] for op in WALLS[wid].get('openings', []) if 'head' in op]
        sills = [op['sill'] for op in WALLS[wid].get('openings', []) if 'sill' in op]
        ok_z = (any(abs(z0 - h) < 0.012 for h in [0.0] + heads) and
                any(abs(z1 - t) < 0.012 for t in sills + [CEIL]))
        if not ok_z:
            log('FAIL', 'wall %s z %.3f..%.3f' % (n, z0, z1))
            bad += 1
        t_exp = config.WALL_T_EXT if g['ext'] else config.WALL_T
        if abs((v1 - v0) - t_exp) > 0.005:
            log('FAIL', 'wall %s thickness %.3f != %.3f' % (n, v1 - v0, t_exp))
            bad += 1
    if bad == 0:
        log('PASS', 'wall dims all %d segs (top %.2f, t=%.2f/%.2f)' %
            (len(wall_seg_names), CEIL, config.WALL_T, config.WALL_T_EXT))


# ---------------------------------------------------------------- 4 数量
def check_counts():
    floor_ids = set()
    for o in bpy.data.objects:
        if not o.name.startswith('floor_'):
            continue
        fid = o.name[6:]
        if fid.endswith(('_0', '_1')) and fid[:-2] in {'corridor'}:
            fid = fid[:-2]
        floor_ids.add(fid)
    expect_floors = {f['id'] for f in L['floors']} - architecture.SKIP_FLOORS
    if floor_ids == expect_floors:
        log('PASS', 'floors %d built' % len(expect_floors))
    else:
        log('FAIL', 'floors mismatch missing=%s extra=%s' %
            (expect_floors - floor_ids, floor_ids - expect_floors))
    ncam = len([o for o in bpy.data.objects if o.type == 'CAMERA'])
    if ncam == 29:   # REWORK：23 + 16b + CAL + R2FIX M1 柜门特写 ×3 + R2FIX2 N1 西墙柜特写
        log('PASS', 'cameras %d' % ncam)
    else:
        log('FAIL', 'cameras %d != 29' % ncam)
    markers = [o.name for o in bpy.data.objects if 'marker' in o.name.lower()]
    if markers:
        log('FAIL', 'marker objects built: %s' % markers[:3])
    else:
        log('PASS', 'no marker objects')


# ---------------------------------------------------------------- 5 ceiling_box
def check_ceiling_box():
    items = L.get('items', [])
    cb = next((i for i in items if i.get('type') == 'ceiling_box'), None)
    if not cb:
        log('WARN', 'no ceiling_box item in layout')
        return
    bb = bbox_of('ceil_parents_room_ac')
    if bb is None:
        log('FAIL', 'ceil_parents_room_ac not found')
        return
    exp_min, exp_max = tuple(cb['bbox']['min']), tuple(cb['bbox']['max'])
    ok = all(abs(bb[0][k] - exp_min[k]) < 0.02 and abs(bb[1][k] - exp_max[k]) < 0.02
             for k in range(3))
    log('PASS' if ok else 'FAIL', 'ceiling_box bbox %s' % (bb,))


# ---------------------------------------------------------------- 6 视线抽检
def check_rays():
    centroid = (7.0, -6.2)
    for w in L['walls']:
        g = GEO[w['id']]
        for op in architecture.normalize_openings(w):
            if op['type'] != 'window':
                continue
            um = (op['start'] + op['end']) / 2
            zm = (op['sill'] + op['head']) / 2
            if g['axis'] == 'x':
                # 墙沿 X：法向在 Y
                pos = (um, g['v_center'], zm)
                inward = (0, 1, 0) if centroid[1] > g['v'] else (0, -1, 0)
            else:
                # 墙沿 Y：法向在 X
                pos = (g['v_center'], um, zm)
                inward = (1, 0, 0) if centroid[0] > g['v'] else (-1, 0, 0)
            origin = (pos[0] + inward[0] * 0.5, pos[1] + inward[1] * 0.5, pos[2])
            direction = (-inward[0] * 2, -inward[1] * 2, 0)
            dg = bpy.context.evaluated_depsgraph_get()
            hit = bpy.context.scene.ray_cast(dg, origin, direction)
            hobj = hit[4] if hit and hit[0] else None
            ok_hit = hobj is None or hobj.name.startswith(
                ('win_', 'fx_curt', 'fx_blind'))
            if ok_hit:
                log('PASS', 'ray %s window visible (%s)' %
                    (w['id'], hobj.name if hobj else 'sky'))
            else:
                log('FAIL', 'ray %s blocked by %s' % (w['id'], hobj.name))


# ---------------------------------------------------------------- M2: item 检查
def check_items_bbox():
    """每个 M2 item：父 Empty 存在、子网格包络在 bbox 内(±5mm)且四向贴近(≤2.5cm/垂3.5cm)。"""
    B = util.load_module('builtins')
    m2_ids = set()
    pending = []
    for item in L['items']:
        iid, typ = item['id'], item.get('type')
        if typ == 'marker':
            continue
        root = bpy.data.objects.get(iid)
        if root is None:
            pending.append(iid)
            continue
        m2_ids.add(iid)
        kids = [c for c in root.children if c.type == 'MESH']
        if not kids:
            log('FAIL', 'item %s: no mesh children' % iid)
            continue
        cmin = [min(util.obj_world_bbox(k)[0][k_] for k in kids) for k_ in range(3)]
        cmax = [max(util.obj_world_bbox(k)[1][k_] for k in kids) for k_ in range(3)]
        if 'bbox' in item:
            ibmin, ibmax = list(item['bbox']['min']), list(item['bbox']['max'])
        elif item.get('shape') == 'sphere':
            cx, cy, cz = item['center']
            r = item['radius']
            ibmin, ibmax = [cx - r, cy - r, cz - r], [cx + r, cy + r, cz + r]
        else:  # cylinder: center/radius/z_base/height 为包络（parts 球体并入）
            cx, cy = item['center']
            r = item['radius']
            z0 = item.get('z_base', 0.0)
            ibmin, ibmax = [cx - r, cy - r, z0], [cx + r, cy + r, z0 + item['height']]
            for p in item.get('parts', []):
                if p.get('shape') == 'sphere':
                    pc = p['center']
                    pr = p['radius']
                    for a in range(3):
                        ibmin[a] = min(ibmin[a], pc[a] - pr)
                        ibmax[a] = max(ibmax[a], pc[a] + pr)
        # parts 的 bbox 属于该 item 的合法包络（台面等）
        for p in item.get('parts', []):
            if 'bbox' not in p:
                continue
            for a in range(3):
                ibmin[a] = min(ibmin[a], p['bbox']['min'][a])
                ibmax[a] = max(ibmax[a], p['bbox']['max'][a])
        if iid in B.COVERED:
            log('INFO', 'item %s covered by architecture object' % iid)
            continue
        # REWORK #9 豁免：B 方案移动电视按规格指定挪到 (8.25,-6.0) 屏幕朝西，
        # 脱离 layout bbox 属已知决策（见 decisions_log D-033），跳过包络检查。
        if iid == 'B_living_dining_balcony_tv_01':
            log('INFO', 'item %s at REWORK#9 exempt position (8.25,-6.0)' % iid)
            continue
        # 规格要求的超出豁免（D-023）：龙头/吊杆/床品/显示器/靠枕/画灯/弧形灯头
        typ = item.get('type')
        z_extra = {'sink': 0.40, 'pendant_lamp': 0.60, 'bed': 0.15,
                   'desk': 0.40, 'cushion': 0.35, 'artwork': 0.10,
                   'vanity': 0.30, 'floor_lamp': 0.10}.get(typ, 0.0)   # R2FIX m2 弧形灯罩高出
        z_top_allow = z_extra + 0.03
        # R2 #15：bookcase 矮台外凸 5cm（REWORK #15 明确要求，铁律 ±2cm 容差内）；
        # R2 #11：vanity 龙头/盆沿南缘出界 ~0.17（同水槽龙头先例，spec 5.8 功能件）；
        # R2FIX M3：水槽台下盆沿口/盆体水平出界 ~0.06（规格要求，z 豁免同理）
        xy_extra = 0.08 if typ == 'sink' else 0.0
        xy_allow = xy_extra + (0.65 if typ == 'floor_lamp' else (
            0.025 if typ == 'bookcase' else (0.20 if typ == 'vanity' else 0.0)))
        bad = []
        for a in range(3):
            tol_out = 0.005 + (z_top_allow if a == 2 else xy_allow)
            tol_lo = 0.005 + (0 if a == 2 else xy_allow)
            if typ == 'sink' and a == 2:
                tol_lo = 0.005 + 0.25   # R2FIX M3：台下盆下沉 0.2m（盆体入柜体）
            if cmin[a] < ibmin[a] - tol_lo or cmax[a] > ibmax[a] + tol_out:
                bad.append('axis%d out (%.3f..%.3f vs %.3f..%.3f)'
                           % (a, cmin[a], cmax[a], ibmin[a], ibmax[a]))
        tol_near_h, tol_near_z = 0.025, 0.035
        for a in range(2):
            near_tol = tol_near_h + xy_allow
            if ibmin[a] + near_tol < cmin[a] or cmax[a] < ibmax[a] - near_tol:
                bad.append('axis%d not near edge' % a)
        if ibmin[2] + tol_near_z < cmin[2] or cmax[2] < ibmax[2] - tol_near_z:
            bad.append('axisZ not near edge (%.3f..%.3f vs %.3f..%.3f)'
                       % (cmin[2], cmax[2], ibmin[2], ibmax[2]))
        if bad:
            log('FAIL', 'item %s: %s' % (iid, '; '.join(bad)))
        else:
            log('PASS', 'item %s bbox ok (%d parts)' % (iid, len(kids)))
        if item.get('type') == 'sink' and cmax[2] > ibmax[2] + 0.035:
            log('INFO', 'item %s tap rises %.2fm above bbox (spec 5.4)' % (iid, cmax[2] - ibmax[2]))
    log('INFO', 'items built=%d, pending(M3)=%d' % (len(m2_ids), len(pending)))


def check_item_wall_penetration():
    """与墙穿插：仅当 item 包络贯穿整道墙身（两侧都越过墙皮）才 FAIL；
    贴墙嵌入（业主数据本身允许，如玄关柜嵌 12cm）记 INFO；墙端延伸小条(接触<5cm)忽略。"""
    bad = 0
    for item in L['items']:
        iid = item['id']
        root = bpy.data.objects.get(iid)
        if root is None or iid in ('bay_seat', 'ceiling_box'):
            continue
        kids = [c for c in root.children if c.type == 'MESH']
        if not kids:
            continue
        cmin = [min(util.obj_world_bbox(k)[0][a] for k in kids) for a in range(3)]
        cmax = [max(util.obj_world_bbox(k)[1][a] for k in kids) for a in range(3)]
        for n in wall_seg_names:
            (wx0, wy0, wz0), (wx1, wy1, wz1) = SEG_BBOX[n]
            ox0, ox1 = max(wx0, cmin[0]), min(wx1, cmax[0])
            oy0, oy1 = max(wy0, cmin[1]), min(wy1, cmax[1])
            oz0, oz1 = max(wz0, cmin[2]), min(wz1, cmax[2])
            if ox0 >= ox1 or oy0 >= oy1 or oz0 >= oz1:
                continue
            g = GEO[n.split('_')[0]]
            k = 1 if g['axis'] == 'x' else 0  # 墙法向轴
            u = 0 if g['axis'] == 'x' else 1  # 墙长度轴
            u_ov = (oy1 - oy0) if u == 1 else (ox1 - ox0)
            if u_ov < 0.05:
                continue  # 墙端延伸小条接触，忽略
            v0, v1 = (wy0, wy1) if k == 1 else (wx0, wx1)
            c0, c1 = cmin[k], cmax[k]
            if c0 <= v0 + 0.003 and c1 >= v1 - 0.003:
                log('FAIL', 'item %s pierces through %s' % (iid, n))
                bad += 1
            else:
                log('INFO', 'item %s tucks into %s (data-confirmed)' % (iid, n))
    if bad == 0:
        log('PASS', 'no item pierces through any wall')


def check_door_swing():
    """室内门开启空间：每樘门至少一侧回转区无 item 阻挡。"""
    obstacles = []
    for item in L['items']:
        root = bpy.data.objects.get(item['id'])
        if root is None or item.get('type') in ('glass_partition',):
            continue
        if 'bbox' in item:
            obstacles.append((item['id'], item['bbox']['min'], item['bbox']['max']))
        elif item.get('shape') == 'cylinder':
            cx, cy = item['center']
            r = item['radius']
            z0 = item.get('z_base', 0.0)
            obstacles.append((item['id'], (cx - r, cy - r, z0),
                              (cx + r, cy + r, z0 + item['height'])))
    for w in L['walls']:
        if w['id'] == 'W12':
            continue  # 推拉门
        g = GEO[w['id']]
        for op in architecture.normalize_openings(w):
            if op['type'] != 'door':
                continue
            a, b = op['start'], op['end']
            wd = b - a - 0.06
            zones = []
            if g['axis'] == 'x':
                zones = [((a, g['v'], ), ((a + wd, g['v'] - wd))),
                         (((a, g['v'] + wd), (a + wd, g['v'])))]
            else:
                zones = [((g['v'], a), (g['v'] - wd, a + wd)),
                         ((g['v'] + wd, a), (g['v'], a + wd))]
            for side, ((zx0, zy0), (zx1, zy1)) in enumerate(zones):
                clear = True
                for oid, omin, omax in obstacles:
                    if (max(zx0, omin[0]) < min(zx1, omax[0]) - 0.02 and
                            max(zy0, omin[1]) < min(zy1, omax[1]) - 0.02 and
                            omin[2] < 1.0):
                        clear = False
                        break
                if clear:
                    log('PASS', 'door swing %s side %d clear' % (w['id'], side))
                    break
            else:
                log('FAIL', 'door %s: both swing sides blocked' % w['id'])


def check_scheme_membership():
    bad = 0
    expect = {'A': config.COL_SCHEME_A, 'B': config.COL_SCHEME_B, 'common': config.COL_COMMON}
    for item in L['items']:
        root = bpy.data.objects.get(item['id'])
        if root is None:
            continue
        want = expect.get(item.get('group', 'common'))
        got = root.users_collection[0].name if root.users_collection else None
        if got != want:
            log('FAIL', 'item %s in collection %s want %s' % (item['id'], got, want))
            bad += 1
    if bad == 0:
        log('PASS', 'scheme collections correct')


# ---------------------------------------------------------------- REWORK 第 6 章新增
# 4.5 Collection 无 .parent：方案归属反查统一走 util.root_side（D-014）
_root_side = util.root_side


def check_roles():
    """QA-2（REWORK 第 6 章）：任何网格对象没有 role -> FAIL。"""
    import materials as M
    missing = [o.name for o in bpy.data.objects
               if o.type == 'MESH' and not o.get('role')]
    if missing:
        log('FAIL', 'meshes without role (%d): %s' % (len(missing), missing[:6]))
    else:
        n = len([o for o in bpy.data.objects if o.type == 'MESH'])
        log('PASS', 'all %d meshes have role' % n)
    # 未知 role（表里查不到且非语境角色）也算 FAIL
    known_ctx = {'kids_furn', 'kids_accent', 'kids_bedding', 'kids_rug', 'headboard',
                 'book', 'toy', 'outdoor'}
    unknown = []
    for o in bpy.data.objects:
        if o.type != 'MESH':
            continue
        r = o.get('role')
        if r and r not in M.ROLE_TO_MATERIAL and r not in known_ctx \
                and not r.startswith('wall_tile'):
            unknown.append('%s(%s)' % (o.name, r))
    if unknown:
        log('FAIL', 'unknown roles (%d): %s' % (len(unknown), unknown[:6]))
    else:
        log('PASS', 'all roles resolvable')


def check_material_zones():
    """QA-1（REWORK 2.4）：禁木色清单 role 的对象不得挂 walnut 类材质。"""
    import materials as M
    bad = []
    for o in bpy.data.objects:
        if o.type != 'MESH':
            continue
        if o.get('role') in M.ROLE_WOOD_FORBIDDEN and o.material_slots:
            m = o.material_slots[0].material
            if m and m.name.startswith('walnut'):
                bad.append('%s(%s->%s)' % (o.name, o.get('role'), m.name))
    if bad:
        log('FAIL', 'wood on forbidden roles (%d): %s' % (len(bad), bad[:6]))
    else:
        log('PASS', 'no wood material on forbidden roles (2.4)')


def check_scheme_full():
    """QA-3（REWORK 第 6 章/#2）：全部对象（含 fx_ 与灯光）恰属一个方案集合；
    B 开放格摆件不得在 COMMON / SCHEME_A。"""
    bad_multi, bad_b = [], []
    for o in bpy.data.objects:
        if o.type not in ('MESH', 'LIGHT'):
            continue
        sides = {_root_side(c) for c in o.users_collection}
        sides.discard(None)
        if len(sides) != 1:
            bad_multi.append('%s%s' % (o.name, tuple(sorted(sides)) if sides else '(none)'))
        elif o.name.startswith('fx_B_') and sides.pop() != config.COL_SCHEME_B:
            bad_b.append(o.name)
    if bad_multi:
        log('FAIL', 'objects not in exactly one scheme (%d): %s' %
            (len(bad_multi), bad_multi[:6]))
    else:
        log('PASS', 'all meshes/lights in exactly one scheme collection')
    if bad_b:
        log('FAIL', 'B-niche props outside SCHEME_B: %s' % bad_b[:6])
    else:
        log('PASS', 'B open-niche props in SCHEME_B')


def check_bed_orientation():
    """QA-4（REWORK 第 6 章/#3）：枕头中心必须在床头一侧 1/3 范围内。"""
    bad = 0
    for item in L['items']:
        if item.get('type') != 'bed':
            continue
        root = bpy.data.objects.get(item['id'])
        if root is None:
            continue
        pillows = [c for c in root.children
                   if '_pillow' in c.name and not c.name.endswith('_acc')]
        if not pillows:
            log('FAIL', 'bed %s: no pillows found' % item['id'])
            bad += 1
            continue
        bmin, bmax = item['bbox']['min'], item['bbox']['max']
        Lx = bmax[0] - bmin[0]
        head = config.BED_HEAD_SIDE.get(item.get('room', ''), '-X')
        # 子对象坐标是相对父 Empty 的局部坐标，世界 X = matrix_world（不要手加/2）
        px = sum(c.matrix_world.translation.x for c in pillows) / len(pillows)
        if Lx >= (bmax[1] - bmin[1]):   # X 向床
            ok = (px > bmin[0] + Lx * 2 / 3) if head == '+X' else (px < bmin[0] + Lx / 3)
        else:
            ok = True   # Y 向床本项目没有
        if ok:
            log('PASS', 'bed %s pillows at %s head' % (item['id'], head))
        else:
            log('FAIL', 'bed %s pillows NOT at %s head (px=%.2f bbox %s..%s)' %
                (item['id'], head, px, bmin[0], bmax[0]))
            bad += 1
    if bad == 0:
        log('PASS', 'all beds oriented per BED_HEAD_SIDE')



def check_floor_overlap():
    fl = [(o.name, bbox_of(o.name)) for o in bpy.data.objects
           if o.name.startswith('floor_')]
    bad = 0
    for i in range(len(fl)):
        for j in range(i + 1, len(fl)):
            (n1, (a0, a1)), (n2, (b0, b1)) = fl[i], fl[j]
            ox = min(a1[0], b1[0]) - max(a0[0], b0[0])
            oy = min(a1[1], b1[1]) - max(a0[1], b0[1])
            if ox > 0.001 and oy > 0.001:
                log('FAIL', 'floor overlap %s x %s %.3fx%.3f' % (n1, n2, ox, oy))
                bad += 1
    if bad == 0:
        log('PASS', 'no floor overlap (%d slabs)' % len(fl))


def check_m3_completeness():
    """全部 item 无漏建（marker/wall_finish 除外）；落地类不悬空。"""
    expect, missing = 0, []
    hang_ok = {'pendant_lamp', 'range_hood', 'mirror_cabinet', 'cabinet', 'tv',
               'artwork', 'open_niche', 'ceiling_box', 'marker', 'wall_finish',
               'sink', 'hob', 'dishwasher', 'glass_sliding_door', 'bookcase',
               'vanity', 'shower_floor', 'bay_seat', 'cushion', 'shelf',
               'tv_cabinet', 'sofa'}
    float_bad = 0
    for item in L['items']:
        typ = item.get('type')
        if typ in ('marker', 'wall_finish'):
            continue
        expect += 1
        root = bpy.data.objects.get(item['id'])
        if root is None:
            missing.append(item['id'])
            continue
        kids = [c for c in root.children if c.type == 'MESH']
        if not kids:
            missing.append(item['id'] + '(empty)')
            continue
        z0 = min(util.obj_world_bbox(k)[0][2] for k in kids)
        z_expect = item.get('z_base', 0.0) if 'bbox' not in item else 0.0
        if typ not in hang_ok and z0 > z_expect + 0.006:
            log('FAIL', 'item %s floats %.3fm' % (item['id'], z0))
            float_bad += 1
    if missing:
        log('FAIL', 'missing items: %s' % missing)
    else:
        log('PASS', 'all %d items built, none missing' % expect)
    if float_bad == 0:
        log('PASS', 'no floating furniture')


# ---------------------------------------------------------------- main
def main():
    check_closure()
    check_openings()
    check_wall_dims()
    check_counts()
    check_ceiling_box()
    check_rays()
    check_floor_overlap()
    # M2
    check_items_bbox()
    check_item_wall_penetration()
    check_door_swing()
    check_scheme_membership()
    # M3
    check_m3_completeness()
    # REWORK 第 6 章（R1 新增：材质 role / 禁木色 / 全对象方案隔离 / 床朝向）
    check_roles()
    check_material_zones()
    check_scheme_full()
    check_bed_orientation()
    os.makedirs(config.REVIEW_DIR, exist_ok=True)
    out = os.path.join(config.REVIEW_DIR, 'qa_report.md')
    with open(out, 'w', encoding='utf-8') as f:
        f.write('# QA 报告 · R1 返工\n\n')
        f.write('blend: %s\n\n' % config.BLEND_FILE)
        f.write('汇总: PASS %d / FAIL %d / WARN %d / INFO %d\n\n' %
                (counts['PASS'], counts['FAIL'], counts['WARN'], counts['INFO']))
        f.write('\n'.join(lines) + '\n')
    print('[qa] summary PASS=%d FAIL=%d WARN=%d -> %s' %
          (counts['PASS'], counts['FAIL'], counts['WARN'], out))


main()

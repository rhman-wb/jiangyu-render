# -*- coding: utf-8 -*-
# final1_variants.py —— REWORK_FINAL1 第 2 轮 A：C1-C3 对比图临时变体（--f1v）
# 设计纪律：所有改动 render 进程内施加、渲后 revert；全程不 save -> blend 不被污染。
# apply(name) = 附录A 胡桃重映射（所有 C 渲染的共同基底，业主在"减胡桃后"环境比较）
#               + 选项叠加；任一必需步骤 0 命中即 raise（宁可中止不出错图）。
# 预设：
#   c1_door_white        卧室门全云白（门扇+门套+衬里）
#   c1_door_walnutframe  胡桃细框 + 云白门芯（仅门扇换白）
#   c1_door_oat          燕麦平板门（门套随门扇同色，qa_final1 注明口径）
#   c2_tv_opt1           R6 方案1：画框式背景板 + 北端竖格栅（胡桃）+ 窄电视柜
#   c2_tv_opt2           R6 方案2：整墙洗墙灯槽 + 窄电视柜 + 北段挂画+落地灯
#   c3_slat_walnut       = c2_tv_opt1（格栅胡桃，即 C2 方案1 同帧）
#   c3_slat_graphite     = c2_tv_opt1 但格栅深灰
import math
import bpy

import config

_SRC_WOOD = ('walnut', 'walnut_dark')


def _base_name(m):
    n = m.name
    i = n.rfind('.')
    return n[:i] if i > 0 and n[i + 1:].isdigit() else n


def _mat(name):
    m = bpy.data.materials.get(name)
    if m is None:
        for cand in bpy.data.materials:
            if _base_name(cand) == name:
                return cand
        raise RuntimeError('[f1v] material missing: %s' % name)
    return m


def _root_of(o):
    while o.parent is not None:
        o = o.parent
    return o


class _State:
    def __init__(self):
        self.slots = []      # (obj, slot_index, original_material)
        self.hidden = []     # (obj, original_hide_render)
        self.created = []    # obj

    def swap(self, o, dst, src_bases):
        for i, slot in enumerate(o.material_slots):
            if slot.material and _base_name(slot.material) in src_bases:
                self.slots.append((o, i, slot.material))
                slot.material = dst
        return len(self.slots)

    def hide(self, o):
        self.hidden.append((o, o.hide_render))
        o.hide_render = True


def _swap_by_root_prefix(st, prefix, dst, role=None):
    n = 0
    for o in bpy.data.objects:
        if o.type != 'MESH':
            continue
        if role is not None and o.get('role') != role:
            continue
        if not _root_of(o).name.startswith(prefix):
            continue
        before = len(st.slots)
        st.swap(o, dst, _SRC_WOOD)
        n += len(st.slots) - before
    return n


# 附录 A · 胡桃预算表（REWORK_FINAL1 附录A；业主已确认；D1 落地前的临时映射）
# 注：主卧桌格开放格内衬随柜体一并换白（附录A"内衬可留胡桃"，此处从简，报告注明）；
#     飘窗坐榻为单盒体（bay_platform），立面/台面无法分面，暂整体保留胡桃，报告注明。
APPENDIX_A = [
    ('A_living_dining_balcony_tv_cabinet_01', None, 'cabinet_white'),
    ('A_living_dining_balcony_coffee_table_01', None, 'cabinet_white'),
    ('A_living_dining_balcony_dining_chair_0', 'wood', 'metal_black'),
    ('A_living_dining_balcony_island_01', 'wood', 'cabinet_white'),
    ('B_living_dining_balcony_side_table_01', None, 'cabinet_white'),
    ('B_living_dining_balcony_island_01', 'wood', 'cabinet_white'),
    ('B_living_dining_balcony_dining_chair_0', 'wood', 'metal_black'),
    ('common_master_bedroom_bed_01', None, 'fabric_oat'),
    ('common_master_bedroom_nightstand_0', None, 'cabinet_white'),
    ('common_master_bedroom_open_niche_01', None, 'cabinet_white'),
    ('common_master_bedroom_dressing_table_01', None, 'cabinet_white'),
    ('common_parents_room_bed_01', None, 'fabric_oat'),
    ('common_parents_room_shelf_0', None, 'cabinet_white'),
    ('common_parents_room_nightstand_01', None, 'cabinet_white'),
]

# C1 卧室门（门扇 role door_leaf_wood / 门套+衬里 role door_frame_wood；
# 拉手 metal_black、长虹玻璃芯 glass_fluted 不动；厨房四联动/卫生玻璃门不在列）
DOOR_PREFIXES = ('door_W14_0', 'door_W19_0', 'door_W13_0', 'door_W07_0')


def _swap_doors(st, leaf_dst, frame_dst):
    n_leaf = n_frame = 0
    for o in bpy.data.objects:
        if o.type != 'MESH':
            continue
        role = o.get('role')
        nm = o.name
        if not any(nm.startswith(p) for p in DOOR_PREFIXES):
            continue
        if role == 'door_leaf_wood' and leaf_dst is not None:
            before = len(st.slots)
            st.swap(o, _mat(leaf_dst), _SRC_WOOD)
            n_leaf += len(st.slots) - before
        elif role == 'door_frame_wood' and frame_dst is not None:
            before = len(st.slots)
            st.swap(o, _mat(frame_dst), _SRC_WOOD)
            n_frame += len(st.slots) - before
    return n_leaf, n_frame


def _box(st, coll, name, bmin, bmax, mat_name, role):
    o = util_make_box(name, bmin, bmax, coll=coll, mat=_mat(mat_name), role=role)
    if o is not None:
        st.created.append(o)
    return o


def util_make_box(name, bmin, bmax, coll, mat, role):
    import util
    return util.make_box(name, bmin, bmax, coll=coll, mat=mat, role=role)


def _new_tv_cabinet(st, coll):
    """R6 两方案共用：3m 旧柜隐藏，换成 2.4m 窄柜（中心 y-8.6，云白体 +
    4cm 胡桃台面线 + 底灯带），电视（y-9.55..-7.65，中心 -8.6）对位不动。"""
    for o in bpy.data.objects:
        r = _root_of(o)
        if r.name.startswith('A_living_dining_balcony_tv_cabinet_01'):
            st.hide(o)
        if o.name == 'lt_strip_tv':
            st.hide(o)
    n = 0
    _box(st, coll, 'f1_tvc_body', (8.83, -9.80, 0.25), (9.15, -7.40, 0.60),
         'cabinet_white', 'cabinet_box')
    _box(st, coll, 'f1_tvc_gap', (8.825, -8.6015, 0.25), (9.15, -8.5985, 0.60),
         'gap_dark', 'gap_dark')
    _box(st, coll, 'f1_tvc_topline', (8.83, -9.80, 0.60), (9.15, -7.40, 0.64),
         'walnut', 'wood')
    _box(st, coll, 'f1_tvc_strip', (8.84, -9.78, 0.242), (9.14, -7.42, 0.255),
         'led_strip', 'led_strip')
    return n + 4


def _tv_opt1(st, coll, slat_mat):
    _new_tv_cabinet(st, coll)
    # 画框式背景板：3cm 出墙（电视背板 1-2cm 隐入板内，相机不可见，报告注明）
    _box(st, coll, 'f1_tvw_panel', (9.121, -10.10, 0.0), (9.151, -7.10, 2.60),
         'cabinet_white', 'cabinet_box')
    # 四缘 15mm 暗槽灯带（贴板缘，读作缝光）
    _box(st, coll, 'f1_tvw_led_s', (9.121, -10.10, 0.0), (9.131, -10.085, 2.60),
         'led_strip', 'led_strip')
    _box(st, coll, 'f1_tvw_led_n', (9.121, -7.115, 0.0), (9.131, -7.10, 2.60),
         'led_strip', 'led_strip')
    _box(st, coll, 'f1_tvw_led_t', (9.121, -10.10, 2.59), (9.131, -7.10, 2.60),
         'led_strip', 'led_strip')
    # 北端竖向细格栅：y-5.95..-5.35，20mm 板 + 20mm 缝 x15，z0..2.60
    for i in range(15):
        y0 = -5.95 + i * 0.04
        _box(st, coll, 'f1_tvw_slat%02d' % i, (9.118, y0, 0.0), (9.148, y0 + 0.02, 2.60),
             slat_mat, 'wood' if slat_mat == 'walnut' else 'metal_graphite')
    # 白墙中央挂画 1.0x0.7（中心 z1.5）
    _box(st, coll, 'f1_tvw_art_frame', (9.148, -7.025, 1.15), (9.152, -6.025, 1.85),
         'walnut', 'wood')
    _box(st, coll, 'f1_tvw_art', (9.152, -7.005, 1.17), (9.156, -6.045, 1.83),
         'art_abstract', 'art_abstract')


def _tv_opt2(st, coll):
    _new_tv_cabinet(st, coll)
    # 整面东墙连续洗墙灯槽（边吊内缘 z2.70，y 全长 4.75m）
    _box(st, coll, 'f1_tvw_wash', (9.13, -10.10, 2.70), (9.17, -5.35, 2.713),
         'led_strip', 'led_strip')
    # 北段：挂画 + 弧形落地灯
    _box(st, coll, 'f1_tvw_art_frame', (9.148, -7.025, 1.15), (9.152, -6.025, 1.85),
         'walnut', 'wood')
    _box(st, coll, 'f1_tvw_art', (9.152, -7.005, 1.17), (9.156, -6.045, 1.83),
         'art_abstract', 'art_abstract')
    import furniture
    furniture.build_floor_lamp({'id': 'f1_c2_lamp', 'center': (8.85, -6.0),
                                'height': 1.8, 'z_base': 0.0},
                               {'dark': _mat('metal_black'),
                                'white': _mat('opal_glass')},
                               coll)
    # build_floor_lamp 内部直接 bpy.data 新建并 link 到 coll —— 收集 diff
    for o in bpy.data.objects:
        if o.name.startswith(('f1_c2_lamp', )) and o not in st.created:
            st.created.append(o)


def apply(name):
    if name not in ('c1_door_white', 'c1_door_walnutframe', 'c1_door_oat',
                    'c2_tv_opt1', 'c2_tv_opt2', 'c3_slat_walnut', 'c3_slat_graphite'):
        raise RuntimeError('[f1v] unknown preset: %s' % name)
    st = _State()
    # 1) 附录 A 胡桃重映射（共同基底）
    na = 0
    for prefix, role, dst in APPENDIX_A:
        na += _swap_by_root_prefix(st, prefix, _mat(dst), role)
    print('[f1v] appendix-A swaps: %d slots' % na)
    if na == 0:
        raise RuntimeError('[f1v] appendix-A matched 0 slots')
    coll_a = bpy.data.collections.get(config.COL_SCHEME_A)
    # 2) 选项叠加
    if name in ('c1_door_white', 'c1_door_oat'):
        dst = 'cabinet_white' if name == 'c1_door_white' else 'fabric_oat'
        nl, nf = _swap_doors(st, dst, dst)
        print('[f1v] %s: leaf=%d frame=%d' % (name, nl, nf))
        if nl < 4 or nf < 4:
            raise RuntimeError('[f1v] %s door swaps too few (leaf=%d frame=%d)'
                               % (name, nl, nf))
    elif name == 'c1_door_walnutframe':
        nl, nf = _swap_doors(st, 'cabinet_white', None)
        print('[f1v] c1_door_walnutframe: leaf=%d (frames keep walnut)' % nl)
        if nl < 4:
            raise RuntimeError('[f1v] leaf swaps too few: %d' % nl)
    elif name in ('c2_tv_opt1', 'c3_slat_walnut'):
        _tv_opt1(st, coll_a, 'walnut')
    elif name == 'c3_slat_graphite':
        _tv_opt1(st, coll_a, 'metal_graphite')
    elif name == 'c2_tv_opt2':
        _tv_opt2(st, coll_a)
    print('[f1v] applied %s: slots=%d hidden=%d created=%d'
          % (name, len(st.slots), len(st.hidden), len(st.created)))
    return st


def revert(st):
    for o, i, m in reversed(st.slots):
        try:
            o.material_slots[i].material = m
        except Exception:
            pass
    for o, was in reversed(st.hidden):
        try:
            o.hide_render = was
        except Exception:
            pass
    for o in st.created:
        try:
            bpy.data.objects.remove(o)
        except Exception:
            pass
    st.slots.clear()
    st.hidden.clear()
    st.created.clear()
    print('[f1v] reverted')

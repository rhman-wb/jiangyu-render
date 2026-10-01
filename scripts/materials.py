# -*- coding: utf-8 -*-
# materials.py —— M4 材质表（CLAUDE.md 6.3 一比一实现）+ 全屋分配
# 地砖/墙砖网格用世界坐标（Geometry Position）保证全屋对缝；木纹用 Poly Haven CC0 贴图。
import bpy
import os
import math

import config
import util

ASSET = config.ASSET_DIR
WOOD_DIFF = os.path.join(ASSET, 'walnut_diff_2k.jpg')
WOOD_ROUGH = os.path.join(ASSET, 'walnut_rough_2k.jpg')
WOOD_NOR = os.path.join(ASSET, 'walnut_nor_gl_2k.jpg')


def lin(hexstr):
    return util.srgb_to_linear(hexstr)


def _nt(mat):
    return mat.node_tree


def _bsdf(mat):
    return next(n for n in _nt(mat).nodes if n.type == 'BSDF_PRINCIPLED')


def _out(mat):
    return next(n for n in _nt(mat).nodes if n.type == 'OUTPUT_MATERIAL')


def _node(mat, ntype, x, y, label=None):
    n = _nt(mat).nodes.new(ntype)
    n.location = (x, y)
    if label:
        n.label = label
    return n


def _link(mat, a, b):
    _nt(mat).links.new(a, b)


def _set(bsdf, name, val):
    i = bsdf.inputs.get(name)
    if i is not None:
        i.default_value = val


def base_mat(name, hexcol, rough, metallic=0.0, alpha=1.0, disp_hex=None):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = _bsdf(m)
    _set(b, 'Base Color', (*lin(hexcol), 1.0))
    _set(b, 'Roughness', rough)
    _set(b, 'Metallic', metallic)
    if alpha < 1.0 and hasattr(m, 'blend_method'):
        try:
            m.blend_method = 'BLEND'
        except Exception:
            pass
    c = lin(hexcol)
    m.diffuse_color = (c[0], c[1], c[2], alpha)
    return m


def _bump_noise(mat, strength, scale, detail=6):
    """轻微噪波凹凸（墙面/皮革/织物）。"""
    b = _bsdf(mat)
    nz = _node(mat, 'ShaderNodeTexNoise', -500, -200)
    nz.inputs['Scale'].default_value = scale
    nz.inputs['Detail'].default_value = detail
    bp = _node(mat, 'ShaderNodeBump', -300, -200)
    bp.inputs['Strength'].default_value = strength
    _link(mat, nz.outputs['Fac'], bp.inputs['Height'])
    _link(mat, bp.outputs['Normal'], b.inputs['Normal'])


# ---------------------------------------------------------------- 特殊材质
def make_floor_tile(name, hexcol, groove_hex, tile, rough, gx, gy):
    """世界坐标方砖网格：Brick 方形网格 + 噪波颗粒。gx/gy=起铺原点。"""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = _bsdf(m)
    # 世界坐标 -> 网格空间
    geo = _node(m, 'ShaderNodeNewGeometry', -900, 0)
    sep = _node(m, 'ShaderNodeSeparateXYZ', -780, 0)
    _link(mat=m, a=geo.outputs['Position'], b=sep.inputs['Vector'])
    cmb = _node(m, 'ShaderNodeCombineXYZ', -660, 0)
    _link(m, sep.outputs['X'], cmb.inputs['X'])
    _link(m, sep.outputs['Y'], cmb.inputs['Y'])
    br = _node(m, 'ShaderNodeTexBrick', -500, 100)
    br.offset = 0.0
    br.inputs['Brick Width'].default_value = 1.0
    br.inputs['Row Height'].default_value = 1.0
    br.inputs['Mortar Size'].default_value = 0.0025 / tile * 1.0
    br.inputs['Mortar'].default_value = (*lin(groove_hex), 1.0)
    br.inputs['Color1'].default_value = (*lin(hexcol), 1.0)
    br.inputs['Color2'].default_value = (*lin('DCCDB4' if tile > 0.6 else hexcol), 1.0)
    br.inputs['Bias'].default_value = 0.08
    # 映射：world -> (p-origin)/tile
    mx = _node(m, 'ShaderNodeMath', -660, -150, 'x/tile-gx')
    mx.operation = 'DIVIDE'
    mx.inputs[1].default_value = tile
    my = _node(m, 'ShaderNodeMath', -660, -260, 'y/tile-gy')
    my.operation = 'DIVIDE'
    my.inputs[1].default_value = tile
    sx = _node(m, 'ShaderNodeMath', -560, -150, '-gx/tile')
    sx.operation = 'SUBTRACT'
    sx.inputs[1].default_value = gx / tile
    sy = _node(m, 'ShaderNodeMath', -560, -260, '-gy/tile')
    sy.operation = 'SUBTRACT'
    sy.inputs[1].default_value = gy / tile
    ax = _node(m, 'ShaderNodeMath', -460, -150, 'x-gx')
    ax.operation = 'ADD'
    ay = _node(m, 'ShaderNodeMath', -460, -260, 'y-gy')
    ay.operation = 'ADD'
    _link(m, sep.outputs['X'], mx.inputs[0])
    _link(m, sep.outputs['Y'], my.inputs[0])
    _link(m, mx.outputs['Value'], sx.inputs[0])
    _link(m, my.outputs['Value'], sy.inputs[0])
    _link(m, sx.outputs['Value'], ax.inputs[0])
    _link(m, sy.outputs['Value'], ay.inputs[1])
    _link(m, ax.outputs['Value'], cmb.inputs['X'])
    _link(m, ay.outputs['Value'], cmb.inputs['Y'])
    _link(m, cmb.outputs['Vector'], br.inputs['Vector'])
    # 细颗粒（砖面石纹）
    nz = _node(m, 'ShaderNodeTexNoise', -500, -150)
    nz.inputs['Scale'].default_value = 240.0
    nz.inputs['Detail'].default_value = 8
    mix = _node(m, 'ShaderNodeMixRGB', -300, 60)
    mix.blend_type = 'MULTIPLY'
    mix.inputs['Fac'].default_value = 0.06
    _link(m, br.outputs['Color'], mix.inputs['Color1'])
    _link(m, nz.outputs['Color'], mix.inputs['Color2'])
    _link(m, mix.outputs['Color'], b.inputs['Base Color'])
    _set(b, 'Roughness', rough)
    bp = _node(m, 'ShaderNodeBump', -300, -160)
    bp.inputs['Strength'].default_value = 0.04
    nz2 = _node(m, 'ShaderNodeTexNoise', -500, -300)
    nz2.inputs['Scale'].default_value = 150.0
    _link(m, nz2.outputs['Fac'], bp.inputs['Height'])
    _link(m, bp.outputs['Normal'], b.inputs['Normal'])
    m.diffuse_color = (*lin(hexcol), 1.0)
    return m


def make_wall_tile(name, hexcol, groove_hex, w, h, rough):
    """80x40 墙砖（通缝）：世界坐标，按面法向自动选 (x,z) 或 (y,z) 平面。"""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = _bsdf(m)
    geo = _node(m, 'ShaderNodeNewGeometry', -1100, 0)

    def brick_plane(coord_out, tag, y):
        sep = _node(m, 'ShaderNodeSeparateXYZ', -960, y)
        _link(m, geo.outputs[coord_out], sep.inputs['Vector'])
        br = _node(m, 'ShaderNodeTexBrick', -700, y, tag)
        br.offset = 0.0
        br.inputs['Brick Width'].default_value = 1.0
        br.inputs['Row Height'].default_value = 1.0
        br.inputs['Mortar Size'].default_value = 0.0015 / w
        br.inputs['Mortar'].default_value = (*lin(groove_hex), 1.0)
        br.inputs['Color1'].default_value = (*lin(hexcol), 1.0)
        br.inputs['Color2'].default_value = (*lin(hexcol), 1.0)
        # x/w、z/h
        mx = _node(m, 'ShaderNodeMath', -860, y - 60)
        mx.operation = 'DIVIDE'
        mx.inputs[1].default_value = w
        mz = _node(m, 'ShaderNodeMath', -860, y + 60)
        mz.operation = 'DIVIDE'
        mz.inputs[1].default_value = h
        cmb = _node(m, 'ShaderNodeCombineXYZ', -760, y)
        _link(m, sep.outputs['X'], mx.inputs[0])
        _link(m, sep.outputs['Z'], mz.inputs[0])
        _link(m, mx.outputs['Value'], cmb.inputs['X'])
        _link(m, mz.outputs['Value'], cmb.inputs['Y'])
        _link(m, cmb.outputs['Vector'], br.inputs['Vector'])
        return br

    brx = brick_plane('Position', 'px', 200)  # 以 x,z 为平面（法向 Y 的墙）
    # 法向 X 分量权重
    nrm = _node(m, 'ShaderNodeSeparateXYZ', -960, 420)
    _link(m, geo.outputs['Normal'], nrm.inputs['Vector'])
    abx = _node(m, 'ShaderNodeMath', -820, 420)
    abx.operation = 'ABSOLUTE'
    _link(m, nrm.outputs['X'], abx.inputs[0])
    aby = _node(m, 'ShaderNodeMath', -820, 330)
    aby.operation = 'ABSOLUTE'
    _link(m, nrm.outputs['Y'], aby.inputs[0])
    # 两个平面都用 (x,z)；法向 X 的墙用 (y,z)：再建一个以 y,z 的
    sep2 = _node(m, 'ShaderNodeSeparateXYZ', -960, -160)
    _link(m, geo.outputs['Position'], sep2.inputs['Vector'])
    my2 = _node(m, 'ShaderNodeMath', -860, -120)
    my2.operation = 'DIVIDE'
    my2.inputs[1].default_value = w
    mz2 = _node(m, 'ShaderNodeMath', -860, -220)
    mz2.operation = 'DIVIDE'
    mz2.inputs[1].default_value = h
    cmb2 = _node(m, 'ShaderNodeCombineXYZ', -760, -160)
    _link(m, sep2.outputs['Y'], my2.inputs[0])
    _link(m, sep2.outputs['Z'], mz2.inputs[0])
    _link(m, my2.outputs['Value'], cmb2.inputs['X'])
    _link(m, mz2.outputs['Value'], cmb2.inputs['Y'])
    bry = _node(m, 'ShaderNodeTexBrick', -700, -160, 'py')
    bry.offset = 0.0
    bry.inputs['Brick Width'].default_value = 1.0
    bry.inputs['Row Height'].default_value = 1.0
    bry.inputs['Mortar Size'].default_value = 0.0015 / w
    bry.inputs['Mortar'].default_value = (*lin(groove_hex), 1.0)
    bry.inputs['Color1'].default_value = (*lin(hexcol), 1.0)
    bry.inputs['Color2'].default_value = (*lin(hexcol), 1.0)
    _link(m, cmb2.outputs['Vector'], bry.inputs['Vector'])
    mix = _node(m, 'ShaderNodeMixRGB', -480, 60)
    _link(m, abx.outputs['Value'], mix.inputs['Fac'])
    _link(m, brx.outputs['Color'], mix.inputs['Color2'])   # |nx| 大 -> 用 x,z 版
    _link(m, bry.outputs['Color'], mix.inputs['Color1'])
    _link(m, mix.outputs['Color'], b.inputs['Base Color'])
    _set(b, 'Roughness', rough)
    m.diffuse_color = (*lin(hexcol), 1.0)
    return m


def make_wood(name, tint=1.0):
    """胡桃木：Poly Haven 贴图（Box 投影 Object 坐标），缺文件回退程序化。"""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = _bsdf(m)
    if os.path.isfile(WOOD_DIFF):
        tc = _node(m, 'ShaderNodeTexCoord', -900, 100)
        for slot, path, colorspace in (('Color', WOOD_DIFF, 'sRGB'),
                                       ('Roughness', WOOD_ROUGH, 'Non-Color'),
                                       ('Normal', WOOD_NOR, 'Non-Color')):
            img = bpy.data.images.get(os.path.basename(path))
            if img is None:
                img = bpy.data.images.load(path)
                img.colorspace_settings.name = colorspace
                img.name = 'jy_' + os.path.basename(path)
            tex = _node(m, 'ShaderNodeTexImage', -700, 100 if slot == 'Color'
                        else (-100 if slot == 'Roughness' else -300))
            tex.image = img
            tex.projection = 'BOX'
            tex.interpolation = 'Smart'
            _link(m, tc.outputs['Object'], tex.inputs['Vector'])
            if slot == 'Color':
                mix = _node(m, 'ShaderNodeMixRGB', -480, 100)
                mix.blend_type = 'MULTIPLY'
                mix.inputs['Fac'].default_value = 1.0
                mix.inputs['Color2'].default_value = (tint, tint, tint, 1.0)
                _link(m, tex.outputs['Color'], mix.inputs['Color1'])
                _link(m, mix.outputs['Color'], b.inputs['Base Color'])
            elif slot == 'Roughness':
                rr = _node(m, 'ShaderNodeMath', -480, -100)
                rr.operation = 'MULTIPLY'
                rr.inputs[1].default_value = 0.55
                _link(m, tex.outputs['Color'], rr.inputs[0])
                _link(m, rr.outputs['Value'], b.inputs['Roughness'])
            else:
                nrm = _node(m, 'ShaderNodeNormalMap', -480, -300)
                nrm.inputs['Strength'].default_value = 0.6
                _link(m, tex.outputs['Color'], nrm.inputs['Color'])
                _link(m, nrm.outputs['Normal'], b.inputs['Normal'])
    else:
        _set(b, 'Base Color', (*lin('6B4A33'), 1.0))
        _set(b, 'Roughness', 0.45)
    m.diffuse_color = (*lin('6B4A33'), 1.0)
    return m


def make_rug_geo():
    """几何纹地毯：燕麦底 + 墨绿/砖红细线（Wave 条纹）。"""
    m = bpy.data.materials.new('rug_geo')
    m.use_nodes = True
    b = _bsdf(m)
    _set(b, 'Base Color', (*lin('CDBEA4'), 1.0))
    _set(b, 'Roughness', 0.95)
    tc = _node(m, 'ShaderNodeTexCoord', -800, 100)
    w1 = _node(m, 'ShaderNodeTexWave', -600, 150)
    w1.inputs['Scale'].default_value = 2.2
    w1.inputs['Distortion'].default_value = 2.0
    w1.bands_direction = 'X'
    w2 = _node(m, 'ShaderNodeTexWave', -600, -60)
    w2.inputs['Scale'].default_value = 1.6
    w2.inputs['Distortion'].default_value = 2.5
    w2.bands_direction = 'Y'
    m1 = _node(m, 'ShaderNodeMixRGB', -400, 150)
    m1.inputs['Fac'].default_value = 0.16
    m1.inputs['Color2'].default_value = (*lin('5F6B45'), 1.0)
    _link(m, tc.outputs['Object'], w1.inputs['Vector'])
    _link(m, tc.outputs['Object'], w2.inputs['Vector'])
    _link(m, w1.outputs['Fac'], m1.inputs['Fac'])
    m2 = _node(m, 'ShaderNodeMixRGB', -260, 60)
    m2.inputs['Fac'].default_value = 0.12
    m2.inputs['Color2'].default_value = (*lin('A5533F'), 1.0)
    _link(m, m1.outputs['Color'], m2.inputs['Color1'])
    _link(m, w2.outputs['Fac'], m2.inputs['Fac'])
    _link(m, m2.outputs['Color'], b.inputs['Base Color'])
    m.diffuse_color = (*lin('CDBEA4'), 1.0)
    return m


def make_wood_deck():
    m = bpy.data.materials.new('wood_deck')
    m.use_nodes = True
    b = _bsdf(m)
    _set(b, 'Base Color', (*lin('9C8366'), 1.0))
    _set(b, 'Roughness', 0.7)
    tc = _node(m, 'ShaderNodeTexCoord', -700, 100)
    br = _node(m, 'ShaderNodeTexBrick', -500, 100)
    br.offset = 0.5
    br.inputs['Brick Width'].default_value = 1.2
    br.inputs['Row Height'].default_value = 0.14 / 1.2
    br.inputs['Mortar Size'].default_value = 0.008
    br.inputs['Mortar'].default_value = (0.02, 0.015, 0.01, 1.0)
    br.inputs['Color1'].default_value = (*lin('9C8366'), 1.0)
    br.inputs['Color2'].default_value = (*lin('94806A'), 1.0)
    _link(m, tc.outputs['Generated'], br.inputs['Vector'])
    mix = _node(m, 'ShaderNodeMixRGB', -300, 100)
    mix.blend_type = 'MULTIPLY'
    mix.inputs['Fac'].default_value = 0.3
    mix.inputs['Color2'].default_value = (*lin('9C8366'), 1.0)
    _link(m, br.outputs['Color'], mix.inputs['Color1'])
    _link(m, mix.outputs['Color'], b.inputs['Base Color'])
    m.diffuse_color = (*lin('9C8366'), 1.0)
    return m


def build_all_materials():
    """按规格 6.3 材质表建全部材质（名字与表一致）。"""
    mats = {}
    mats['wall_paint'] = base_mat('wall_paint', 'F3EFE7', 0.9)
    _bump_noise(mats['wall_paint'], 0.02, 80)
    mats['wall_art_plaster'] = base_mat('wall_art_plaster', 'ECE5D8', 0.85)
    _bump_noise(mats['wall_art_plaster'], 0.05, 6)
    mats['floor_tile_800'] = make_floor_tile('floor_tile_800', 'E3D5C0', 'D3C3AB',
                                             0.8, 0.32, 3.35, -3.95)
    mats['bath_floor_600'] = make_floor_tile('bath_floor_600', 'CFC6B8', 'BFB5A5',
                                             0.6, 0.6, 0.0, 0.0)
    mats['tile_kitchen_wall'] = make_wall_tile('tile_kitchen_wall', 'F1ECE3',
                                               'E2DBCF', 0.8, 0.4, 0.25)
    mats['tile_bath_beige'] = make_wall_tile('tile_bath_beige', 'E6DCCB',
                                             'D8CCB6', 0.8, 0.4, 0.3)
    mats['tile_bath_oat'] = make_wall_tile('tile_bath_oat', 'D4C5AE',
                                           'C4B49B', 0.8, 0.4, 0.3)
    mats['walnut'] = make_wood('walnut', 1.0)
    mats['walnut_dark'] = make_wood('walnut_dark', 0.9)
    mats['cabinet_white'] = base_mat('cabinet_white', 'EFE9DF', 0.55)
    mats['quartz_top'] = base_mat('quartz_top', 'F4F1EC', 0.2)
    mats['leather_caramel'] = base_mat('leather_caramel', '9A5B32', 0.45)
    _bump_noise(mats['leather_caramel'], 0.08, 400)
    mats['fabric_oat'] = base_mat('fabric_oat', 'D8CBB3', 0.95)
    _set(_bsdf(mats['fabric_oat']), 'Sheen Weight', 0.3)
    _bump_noise(mats['fabric_oat'], 0.06, 300)
    mats['fabric_olive'] = base_mat('fabric_olive', '5F6B45', 0.9)
    _bump_noise(mats['fabric_olive'], 0.06, 300)
    mats['ceramic_brick'] = base_mat('ceramic_brick', 'A5533F', 0.4)
    mats['linen_sheer'] = base_mat('linen_sheer', 'EEE7DB', 0.9, alpha=0.62)
    _set(_bsdf(mats['linen_sheer']), 'Transmission Weight', 0.5)
    mats['metal_black'] = base_mat('metal_black', '2A2827', 0.35, metallic=0.8)
    mats['metal_graphite'] = base_mat('metal_graphite', '4A4A4A', 0.3, metallic=0.9)
    mats['window_frame_graphite'] = base_mat('window_frame_graphite', '4B4D50', 0.4,
                                             metallic=0.6)
    mats['glass_clear'] = base_mat('glass_clear', 'FFFFFF', 0.0)
    _set(_bsdf(mats['glass_clear']), 'Transmission Weight', 1.0)
    _set(_bsdf(mats['glass_clear']), 'IOR', 1.45)
    mats['opal_glass'] = base_mat('opal_glass', 'FFF6E6', 0.3)
    b = _bsdf(mats['opal_glass'])
    _set(b, 'Emission Color', (1.0, 0.75, 0.5, 1.0))
    _set(b, 'Emission Strength', 1.2)
    mats['mirror'] = base_mat('mirror', 'FFFFFF', 0.02, metallic=1.0)
    mats['steel_fridge'] = base_mat('steel_fridge', 'C9C6C0', 0.3, metallic=0.7)
    mats['black_glass'] = base_mat('black_glass', '111111', 0.05)
    mats['rug_geo'] = make_rug_geo()
    mats['rug_plain'] = base_mat('rug_plain', 'BFAE92', 0.95)
    mats['kitchen_lower_olive'] = base_mat('kitchen_lower_olive', '6E7A52', 0.5)
    # 表外补充
    mats['ceiling_aluminum'] = base_mat('ceiling_aluminum', 'F0F0EE', 0.28, metallic=0.3)
    mats['public_stone'] = base_mat('public_stone', 'BDB8B0', 0.25, metallic=0.05)
    mats['wood_deck'] = make_wood_deck()
    mats['bedding_white'] = base_mat('bedding_white', 'F5F2EA', 0.95)
    _set(_bsdf(mats['bedding_white']), 'Sheen Weight', 0.2)
    mats['ceramic_white'] = base_mat('ceramic_white', 'F7F6F2', 0.12)
    mats['entry_door_dark'] = base_mat('entry_door_dark', '3A3F45', 0.4, metallic=0.5)
    mats['led_strip'] = base_mat('led_strip', 'FFFFFF', 0.5)
    b = _bsdf(mats['led_strip'])
    _set(b, 'Emission Color', (1.0, 0.72, 0.45, 1.0))
    _set(b, 'Emission Strength', 3.0)
    # 孩子房（柔和版 stage1 色 -> 材质）
    for name, hexc in (('kids_d_pink', 'E3AFA8'), ('kids_d_lilac', 'C6B6DA'),
                       ('kids_mist_blue', '8FB7CF'), ('kids_butter', 'F0CF7E'),
                       ('kids_grass', '9DBE8C'), ('kids_milk', 'F3EEE6')):
        mats[name] = base_mat(name, hexc, 0.6)
    mats['plant_leaf'] = base_mat('plant_leaf', '4E6E3A', 0.5)
    mats['plant_pot'] = mats['ceramic_brick']
    mats['kitchen_front'] = make_wood('kitchen_front', 1.0)  # 橄榄绿变体挂载点
    return mats


# ================================================================ 分配
FLOOR_BY_ROOM = {
    'living_dining_balcony': 'floor_tile_800', 'kitchen': 'floor_tile_800',
    'daughter_room': 'floor_tile_800', 'corridor': 'floor_tile_800',
    'son_room': 'floor_tile_800', 'master_bedroom': 'floor_tile_800',
    'parents_room': 'floor_tile_800', 'foyer': 'floor_tile_800',
    'public_bath_wet': 'bath_floor_600', 'master_bath': 'bath_floor_600',
    'terrace': 'wood_deck', 'elevator_hall': 'public_stone',
}
# 墙 id -> (砖材质, 区域质心)  —— 只给朝该区域的面贴砖
WALL_TILE = {
    'W02': ('tile_kitchen_wall', (5.15, -2.55)), 'W03': ('tile_kitchen_wall', (5.15, -2.55)),
    'W11': ('tile_kitchen_wall', (5.15, -2.55)), 'W12': ('tile_kitchen_wall', (5.15, -2.55)),
    'W09': ('tile_bath_oat', (12.2, -4.35)), 'W10': ('tile_bath_oat', (12.2, -4.35)),
    'W14': ('tile_bath_oat', (12.2, -4.35)),
    'W05': ('tile_bath_beige', (9.875, -1.25)), 'W07': ('tile_bath_beige', (9.875, -1.25)),
    'W08': ('tile_bath_beige', (9.875, -1.25)),
}
ALU_CEIL = ('ceil_kitchen_fill', 'ceil_public_bath_wet_fill', 'ceil_master_bath_fill',
            'ceil_corridor_fill')


def _slot(obj, mat):
    if obj.material_slots:
        obj.material_slots[0].material = mat
    else:
        obj.data.materials.append(mat)


def _kids_mat(root_name, obj_name):
    daughter = root_name.startswith('common_daughter')
    n = obj_name
    if '_chair' in root_name or '_arm' in n:
        return 'kids_d_pink' if daughter else 'kids_mist_blue'
    if '_bed' in root_name:
        if '_headboard' in n or 'headboard' in n:
            return 'kids_d_pink' if daughter else 'kids_mist_blue'
        if '_frame' in n:
            return 'walnut'
        return 'kids_milk'
    if '_wardrobe' in root_name:
        return 'kids_d_pink' if daughter else 'kids_mist_blue'
    if '_desk' in root_name or '_shelf' in root_name:
        if 'desk' in root_name:
            return 'kids_grass' if not daughter else 'kids_milk'
        return 'kids_milk'
    if '_rug' in root_name:
        return 'rug_plain'
    return 'kids_milk'


def apply_all(mats, colls):
    """把 clay 白模材质替换为正式材质（按对象名/房间路由）。"""
    import re

    def assign(obj, mat_name):
        _slot(obj, mats[mat_name])

    for o in bpy.data.objects:
        if o.type != 'MESH' or not o.data.materials:
            continue
        n = o.name
        cur = o.material_slots[0].material.name if o.material_slots else ''
        m = re.match(r'^W\d\d_s\d+$', n)
        # ---- 建筑：地面/墙体/吊顶/窗/门
        if n.startswith('floor_'):
            room = n[6:].rsplit('_', 1)[0]
            assign(o, FLOOR_BY_ROOM.get(room, 'floor_tile_800'))
            continue
        if m:
            wid = n.split('_')[0]
            if wid in WALL_TILE:
                tile_name, cen = WALL_TILE[wid]
                o.data.materials.clear()
                o.data.materials.append(mats['wall_paint'])
                o.data.materials.append(mats[tile_name])
                from mathutils import Vector
                for p in o.data.polygons:
                    c = Vector((0.0, 0.0, 0.0))
                    for vi in p.vertices:
                        c += o.data.vertices[vi].co
                    c /= len(p.vertices)
                    w = o.matrix_world @ c
                    nrm = p.normal.copy()
                    nrm.rotate(o.matrix_world)
                    to_zone = Vector((cen[0] - w.x, cen[1] - w.y, 0.0))
                    p.material_index = 1 if nrm.dot(to_zone) > 0 else 0
            else:
                assign(o, 'wall_paint')
            continue
        if n.startswith('ceil_'):
            assign(o, 'ceiling_aluminum' if n in ALU_CEIL else 'wall_paint')
            continue
        if n == 'ceil_living_ac_slot':
            assign(o, 'metal_black')
            continue
        if n.startswith('win_'):
            assign(o, 'glass_clear' if 'glass' in n else 'window_frame_graphite')
            continue
        if n.startswith('door_'):
            assign(o, 'walnut')
            continue
        if n.startswith('rail_ter'):
            assign(o, 'glass_clear' if 'glass' in n else 'metal_black')
            continue
        if n == 'bay_platform':
            assign(o, 'walnut')
            continue
        # ---- fx 软装
        if n.startswith('fx_curt'):
            assign(o, 'linen_sheer' if 'sheer' in n else 'fabric_oat')
            continue
        if n.startswith('fx_blind'):
            assign(o, 'fabric_oat')
            continue
        if n.startswith('fx_spot') and n.endswith('_r'):
            assign(o, 'cabinet_white')
            continue
        if n.startswith('fx_spot') or n.startswith('fx_ceiling'):
            assign(o, 'opal_glass')
            continue
        if n.startswith('fx_wall_lamp'):
            assign(o, 'opal_glass' if n.endswith('_sh') else 'metal_black')
            continue
        if n.startswith('fx_fiddle_leaf') or n.endswith('_leaf') and o.parent and 'plant' in o.parent.name:
            assign(o, 'plant_leaf')
            continue
        if n.startswith('fx_fiddle_pot'):
            assign(o, 'plant_pot')
            continue
        if n.startswith('fx_fiddle_stem'):
            assign(o, 'plant_leaf')
            continue
        if n == 'fx_curt_parents_roller':
            assign(o, 'cabinet_white')
            continue
        # ---- item 子件：按 clay 材质路由
        root = o.parent.name if o.parent else ''
        if cur == 'clay_wood':
            if 'bookcase' in root:
                assign(o, 'walnut_dark')
            elif '_stem' in n:
                assign(o, 'plant_leaf')
            else:
                assign(o, 'walnut')
            continue
        if cur == 'clay_kfront':
            assign(o, 'kitchen_front')
            continue
        if cur == 'clay_mirror':
            assign(o, 'mirror')
            continue
        if cur == 'white_glass':
            assign(o, 'opal_glass' if ('globe' in n or n.startswith('fx_ceiling'))
                   else 'glass_clear')
            continue
        if cur == 'slot_dark':
            assign(o, 'black_glass' if ('hob' in root and 'glass' in n) else 'metal_black')
            continue
        if cur != 'white_clay':
            continue
        # white_clay 的语境细分
        if root.startswith('common_daughter') or root.startswith('common_son'):
            assign(o, _kids_mat(root, n))
            continue
        if '_top' in n and ('island' in root or 'vanity' in root
                            or 'counter' in root or 'dishwasher' in root):
            assign(o, 'quartz_top')
            continue
        if 'toilet' in root:
            assign(o, 'ceramic_white')
            continue
        if '_bed_' in root:
            if '_frame' in n:
                assign(o, 'walnut')
            elif '_throw' in n:
                assign(o, 'fabric_oat')
            else:
                assign(o, 'bedding_white')
            continue
        if '_headboard' in root:
            assign(o, 'leather_caramel' if 'master' in root else 'fabric_oat')
            continue
        if '_sofa' in root or '_ottoman' in root:
            if root.startswith('A_'):
                assign(o, 'leather_caramel')
            elif root.startswith('B_'):
                assign(o, 'fabric_oat')
            else:
                assign(o, 'fabric_oat')
            continue
        if 'pillow_olive' in n or '_pil_olive' in n:
            assign(o, 'fabric_olive')
            continue
        if 'pillow_brick' in n or '_pil_brick' in n:
            assign(o, 'ceramic_brick')
            continue
        if '_rug' in root:
            assign(o, 'rug_geo' if root.startswith('A_') else 'rug_plain')
            continue
        if '_cushion' in root and '_pad' in n:
            assign(o, 'fabric_oat')
            continue
        if 'fridge' in root and '_body' in n:
            assign(o, 'steel_fridge')
            continue
        if '_tv' in root:
            assign(o, 'black_glass')
            continue
        if 'lounge_chair' in root and root.startswith('A_'):
            assign(o, 'fabric_olive')  # 墨绿中古单椅
            continue
        if n.endswith('_screen') or 'dining_chair_seat' in n:
            assign(o, 'fabric_oat' if 'dining_chair' in n else 'cabinet_white')
            if 'dining_chair' in n:
                continue
        assign(o, 'cabinet_white')

    # A 方案电视墙艺术涂料面板（挂 SCHEME_A；规格 5.2）
    art = util.make_box('fx_art_wall_A', (9.1785, -10.10, 0.0), (9.1835, -5.35, 2.60),
                        coll=colls['scheme_a'], mat=mats['wall_art_plaster'])
    art.visible_shadow = True
    print('[materials] applied')

# -*- coding: utf-8 -*-
# materials.py —— M4 材质表（CLAUDE.md 6.3 一比一实现）+ 全屋分配
# 地砖/墙砖网格用世界坐标（Geometry Position）保证全屋对缝；木纹用 Poly Haven CC0 贴图。
import bpy
import os
import math

import config
import util

ASSET = config.ASSET_DIR
# REWORK 2.1：换 Poly Haven black_walnut_veneer_03（视觉分析：平直横向直纹、灰棕中深、
# 低饱和、细密）——三案预设共用此直纹基底，仅色彩/尺度转向不同。选型记录 decisions_log。
WOOD_DIFF = os.path.join(ASSET, 'walnut2_diff_2k.jpg')
WOOD_ROUGH = os.path.join(ASSET, 'walnut2_rough_2k.jpg')
WOOD_NOR = os.path.join(ASSET, 'walnut2_nor_gl_2k.jpg')


def _math_frac_op():
    """Blender Math 节点 Fraction 的枚举名探测（版本拼写防御）。"""
    try:
        ids = [i.identifier for i in
               bpy.types.ShaderNodeMath.bl_rna.properties['operation'].enum_items]
    except Exception:
        return 'FRACTION'
    for cand in ('FRACTION', 'FRACT'):
        if cand in ids:
            return cand
    return 'FRACTION'


RUG_FRAC_OP = _math_frac_op()

# REWORK 2.1 木色预设：A 胡桃默认(#5E4330 中深棕/直纹/低饱和/哑光)，
# B 浅胡桃(#7A5C43)，C 橡木(#B48E66)。diff/rough/nor 可按预设换贴图。
# REWORK_R1FIX2 F3：以实物门面 (96,63,46)/std13.5 为基准校准；
# contrast/contrast_mid = 贴图线性域对比注入 (c-m)*k+m——steer 目标色混合
# 会拉平纹理，先放大对比保住门面亮度 std>=9（木纹可见）。终值经
# CAL_wood_door 校准循环迭代，定版记录 render_log / decisions_log。
WOOD_PRESETS = {
    'A': dict(target='603F2E', sat=0.95, hue=0.50, value=0.75, steer=0.40,
              contrast=1.7, contrast_mid=(0.495, 0.324, 0.24),
              scale=1.0, rough=0.52, rough_scale=0.90, rough_add=0.30,
              nor_strength=0.80,
              # REWORK_R1FIX2 F3：换 smoked_walnut_veneer（直纹、内在 std 16.6，
              # 旧 black_walnut_03 仅 8.8 撑不起 std>=9；选型实测见 decisions_log）
              diff_tex='walnut3_diff_2k.jpg', rough_tex='walnut3_rough_2k.jpg',
              nor_tex='walnut3_nor_gl_2k.jpg'),
    'B': dict(target='865840', sat=1.10, hue=0.50, value=1.30, steer=0.40,
              contrast=1.7, contrast_mid=(0.495, 0.324, 0.24),
              scale=1.0, rough=0.52, rough_scale=0.90, rough_add=0.30,
              nor_strength=0.75,
              diff_tex='walnut3_diff_2k.jpg', rough_tex='walnut3_rough_2k.jpg',
              nor_tex='walnut3_nor_gl_2k.jpg'),
    'C': dict(target='B48E66', sat=1.00, hue=0.50, value=1.90, steer=0.35,
              contrast=4.0, contrast_mid=(0.71, 0.48, 0.30),
              scale=0.55, rough=0.50, rough_scale=1.10, rough_add=0.30,
              nor_strength=0.70,
              # C 案浅色橡木贴图（oak_veneer_02 #DBB894），steer 0.32——
              # target 比橡木贴图暗，贴图主导亮度
              diff_tex='oak2_diff_2k.jpg', rough_tex='oak2_rough_2k.jpg',
              nor_tex='oak2_nor_gl_2k.jpg'),
}


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


def make_wood(name, preset=None):
    """木色材质（REWORK 2.1 预设 A/B/C）：贴图 + HSL 调整 + 目标色混合。
    preset=None 时用 config.WOOD_PRESET。"""
    p = WOOD_PRESETS[preset or config.WOOD_PRESET]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    _build_wood_nodes(m, p)
    m.diffuse_color = (*lin(p['target']), 1.0)
    return m


def _load_tex_img(path, colorspace):
    """加载/复用贴图（修 bug：改名后按 jy_ 前缀查，避免重复加载 3 套）。"""
    img = bpy.data.images.get('jy_' + os.path.basename(path))
    if img is None and bpy.data.images.get(os.path.basename(path)) is not None:
        img = bpy.data.images.get(os.path.basename(path))
    if img is None:
        if not os.path.isfile(path):
            return None
        img = bpy.data.images.load(path)
        img.colorspace_settings.name = colorspace
        img.name = 'jy_' + os.path.basename(path)
    return img


def _build_wood_nodes(m, p):
    """按预设 (re)build 木纹节点树；apply_wood_preset 在线切换复用。"""
    nt = _nt(m)
    nt.nodes.clear()
    nt.links.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    out.location = (400, 0)
    b = nt.nodes.new('ShaderNodeBsdfPrincipled')
    b.location = (100, 0)
    # 注意：预设里 rough=粗糙度数值，贴图覆盖键用 diff_tex/rough_tex/nor_tex，避免撞名。
    # 预设里的 *_tex 是裸文件名（assets/ 下），必须拼 ASSET 目录——相对 CWD 永远找不到。
    def _tex_path(key, fallback):
        t = p.get(key)
        return os.path.join(ASSET, t) if t else fallback
    diff = _load_tex_img(_tex_path('diff_tex', WOOD_DIFF), 'sRGB')
    rough = _load_tex_img(_tex_path('rough_tex', WOOD_ROUGH), 'Non-Color')
    nor = _load_tex_img(_tex_path('nor_tex', WOOD_NOR), 'Non-Color')
    if diff is not None:
        tc = _node(m, 'ShaderNodeTexCoord', -1400, 100)
        mp = _node(m, 'ShaderNodeMapping', -1250, 100, 'scale')
        mp.inputs['Scale'].default_value = (p['scale'], p['scale'], p['scale'])
        _link(m, tc.outputs['Object'], mp.inputs['Vector'])
        # 彩色链：贴图 -> HSL(降饱和/偏色) -> 目标色混合 -> Base Color
        texc = _node(m, 'ShaderNodeTexImage', -1050, 100)
        texc.image = diff
        texc.projection = 'BOX'
        texc.interpolation = 'Smart'
        _link(m, mp.outputs['Vector'], texc.inputs['Vector'])
        hsl = _node(m, 'ShaderNodeHueSaturation', -860, 100, 'desat')
        hsl.inputs['Hue'].default_value = p['hue']
        hsl.inputs['Saturation'].default_value = p['sat']
        hsl.inputs['Value'].default_value = p['value']
        hsl.inputs['Fac'].default_value = 1.0
        # REWORK_R1FIX2 F3：对比度注入 c' = m + (c-m)*k（m 为逐通道贴图均值、
        # 线性域，负值截 0）——steer 目标色混合会拉平纹理，先放大贴图对比
        # 保住门面亮度 std>=9；逐通道 m 避免单标量把蓝通道压碎
        ck = float(p.get('contrast', 1.0))
        if abs(ck - 1.0) > 1e-3:
            cm = p.get('contrast_mid', (0.3, 0.3, 0.3))
            if not isinstance(cm, (tuple, list)):
                cm = (cm, cm, cm)
            vsub = _node(m, 'ShaderNodeVectorMath', -950, 60, 'contrast sub')
            vsub.operation = 'SUBTRACT'
            vsub.inputs[1].default_value = tuple(cm)
            vsc = _node(m, 'ShaderNodeVectorMath', -950, -60, 'contrast k')
            vsc.operation = 'SCALE'
            vsc.inputs['Scale'].default_value = ck
            vadd = _node(m, 'ShaderNodeVectorMath', -950, -220, 'contrast add')
            vadd.operation = 'ADD'
            vadd.inputs[1].default_value = tuple(cm)
            vmax = _node(m, 'ShaderNodeVectorMath', -950, -380, 'clamp0')
            vmax.operation = 'MAXIMUM'
            vmax.inputs[1].default_value = (0.0, 0.0, 0.0)
            _link(m, texc.outputs['Color'], vsub.inputs[0])
            _link(m, vsub.outputs['Vector'], vsc.inputs[0])
            _link(m, vsc.outputs['Vector'], vadd.inputs[0])
            _link(m, vadd.outputs['Vector'], vmax.inputs[0])
            _link(m, vmax.outputs['Vector'], hsl.inputs['Color'])
        else:
            _link(m, texc.outputs['Color'], hsl.inputs['Color'])
        mixt = _node(m, 'ShaderNodeMixRGB', -640, 100, 'target mix')
        mixt.blend_type = 'MIX'
        mixt.inputs['Fac'].default_value = p['steer']
        mixt.inputs['Color2'].default_value = (*lin(p['target']), 1.0)
        _link(m, hsl.outputs['Color'], mixt.inputs['Color1'])
        _link(m, mixt.outputs['Color'], b.inputs['Base Color'])
        if rough is not None:
            texr = _node(m, 'ShaderNodeTexImage', -1050, -150)
            texr.image = rough
            texr.projection = 'BOX'
            _link(m, mp.outputs['Vector'], texr.inputs['Vector'])
            rr = _node(m, 'ShaderNodeMath', -640, -150, 'rough')
            rr.operation = 'MULTIPLY'
            rr.use_clamp = True
            rr.inputs[1].default_value = p['rough_scale']
            _link(m, texr.outputs['Color'], rr.inputs[0])
            rv = _node(m, 'ShaderNodeMath', -460, -150, 'rough add')
            rv.operation = 'ADD'
            rv.use_clamp = True
            rv.inputs[1].default_value = p['rough_add']
            _link(m, rr.outputs['Value'], rv.inputs[0])
            _link(m, rv.outputs['Value'], b.inputs['Roughness'])
        else:
            _set(b, 'Roughness', p['rough'])
        if nor is not None:
            texn = _node(m, 'ShaderNodeTexImage', -1050, -380)
            texn.image = nor
            texn.projection = 'BOX'
            _link(m, mp.outputs['Vector'], texn.inputs['Vector'])
            nrm = _node(m, 'ShaderNodeNormalMap', -640, -380)
            nrm.inputs['Strength'].default_value = p['nor_strength']
            _link(m, texn.outputs['Color'], nrm.inputs['Color'])
            _link(m, nrm.outputs['Normal'], b.inputs['Normal'])
    else:
        _set(b, 'Base Color', (*lin(p['target']), 1.0))
        _set(b, 'Roughness', p['rough'])
    _link(m, b.outputs['BSDF'], out.inputs['Surface'])


def apply_wood_preset(preset):
    """REWORK 2.1/第 7 章：在线切换木色预设（walnut/walnut_dark/kitchen_front
    三块同源联动；render.py --wood 调用，不复制几何）。返回切换的材质名列表。"""
    if preset not in WOOD_PRESETS:
        raise ValueError('wood preset must be A/B/C, got %r' % preset)
    p = WOOD_PRESETS[preset]
    changed = []
    for name, dark in (('walnut', False), ('walnut_dark', True), ('kitchen_front', False)):
        m = bpy.data.materials.get(name)
        if m is None:
            continue
        pp = dict(p)
        if dark:   # walnut_dark 比 walnut 深 8%
            pp['target'] = '%02X%02X%02X' % tuple(
                max(0, min(255, int(c * 0.92))) for c in
                (int(pp['target'][0:2], 16), int(pp['target'][2:4], 16),
                 int(pp['target'][4:6], 16)))
            pp['value'] = p['value'] * 0.92
        _build_wood_nodes(m, pp)
        m.diffuse_color = (*lin(pp['target']), 1.0)
        changed.append(name)
    print('[materials] wood preset -> %s (%s)' % (preset, ','.join(changed)))
    return changed


def make_rug_geo():
    """几何纹地毯（REWORK_R1FIX2 F6 重写）：燕麦底 CDBEA4 + 墨绿/砖红稀疏细线。
    旧版 Wave->双元素 CONSTANT ColorRamp 的 CONSTANT 语义把 Fac>=0.518 全部
    出线（线宽≈半个周期），渲成密集红绿格子（复核实测格子边长 ~5cm）。
    新版 FRACT 数学直算：周期 SPACING、线宽 WIDTH，X 向线墨绿、Y 向线砖红，
    双向覆盖 = 2*WIDTH/SPACING ≈ 5% <= 8%；远看燕麦色、近看细线。"""
    SPACING = 0.25   # 线距 25cm（规格带 15-25cm 内取最稀，远读作纯燕麦底）
    WIDTH = 0.004    # 线宽 4mm（规格带 4-8mm 内取最细）
    m = bpy.data.materials.new('rug_geo')
    m.use_nodes = True
    b = _bsdf(m)
    _set(b, 'Base Color', (*lin('DBCFBA'), 1.0))
    _set(b, 'Roughness', 0.95)
    tc = _node(m, 'ShaderNodeTexCoord', -1000, 100)
    sep = _node(m, 'ShaderNodeSeparateXYZ', -860, 100)
    _link(m, tc.outputs['Object'], sep.inputs['Vector'])

    def line_mask(tag, coord, y):
        """|frac(coord/SPACING) - 0.5| < 半线宽比 -> 线（1）。"""
        div = _node(m, 'ShaderNodeMath', -700, y, tag + '/spacing')
        div.operation = 'DIVIDE'
        div.inputs[1].default_value = SPACING
        fr = _node(m, 'ShaderNodeMath', -560, y, tag + '/frac')
        fr.operation = RUG_FRAC_OP
        half = _node(m, 'ShaderNodeMath', -420, y, tag + '-0.5')
        half.operation = 'SUBTRACT'
        half.inputs[1].default_value = 0.5
        ab = _node(m, 'ShaderNodeMath', -300, y, tag + '/abs')
        ab.operation = 'ABSOLUTE'
        lt = _node(m, 'ShaderNodeMath', -160, y, tag + '/line')
        lt.operation = 'LESS_THAN'
        lt.inputs[1].default_value = (WIDTH / SPACING) / 2.0
        _link(m, sep.outputs[coord], div.inputs[0])
        _link(m, div.outputs['Value'], fr.inputs[0])
        _link(m, fr.outputs['Value'], half.inputs[0])
        _link(m, half.outputs['Value'], ab.inputs[0])
        _link(m, ab.outputs['Value'], lt.inputs[0])
        return lt

    mx = line_mask('X', 'X', 160)   # X 向线 -> 墨绿
    my = line_mask('Y', 'Y', -60)   # Y 向线 -> 砖红
    m1 = _node(m, 'ShaderNodeMixRGB', 40, 160)
    m1.blend_type = 'MIX'
    m1.inputs['Color1'].default_value = (*lin('DBCFBA'), 1.0)
    m1.inputs['Color2'].default_value = (*lin('5F6B45'), 1.0)
    m2 = _node(m, 'ShaderNodeMixRGB', 200, 60)
    m2.blend_type = 'MIX'
    m2.inputs['Color2'].default_value = (*lin('A5533F'), 1.0)
    _link(m, mx.outputs['Value'], m1.inputs['Fac'])
    _link(m, m1.outputs['Color'], m2.inputs['Color1'])
    _link(m, my.outputs['Value'], m2.inputs['Fac'])
    _link(m, m2.outputs['Color'], b.inputs['Base Color'])
    m.diffuse_color = (*lin('DBCFBA'), 1.0)
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


def make_art_abstract():
    """REWORK 4.1：挂画画芯 = 程序化抽象色块（暖米/焦糖/墨绿三大色面）。"""
    m = bpy.data.materials.new('art_abstract')
    m.use_nodes = True
    b = _bsdf(m)
    _set(b, 'Base Color', (*lin('E4D8C4'), 1.0))
    _set(b, 'Roughness', 0.85)
    tc = _node(m, 'ShaderNodeTexCoord', -700, 100)
    sep = _node(m, 'ShaderNodeSeparateXYZ', -560, 100)
    _link(m, tc.outputs['Generated'], sep.inputs['Vector'])
    # 三段横带：暖米 / 焦糖 / 墨绿（Generated Z 0..1，边界轻扰动）
    nz = _node(m, 'ShaderNodeTexNoise', -560, -120)
    nz.inputs['Scale'].default_value = 6.0
    nz.inputs['Detail'].default_value = 4
    blend = _node(m, 'ShaderNodeMath', -420, 100, 'z+noise')
    blend.operation = 'ADD'
    blend.use_clamp = False
    _link(m, sep.outputs['Z'], blend.inputs[0])
    _link(m, nz.outputs['Fac'], blend.inputs[1])
    m1 = _node(m, 'ShaderNodeMixRGB', -260, 120, 'band12')
    m1.blend_type = 'MIX'
    m1.inputs['Color1'].default_value = (*lin('E4D8C4'), 1.0)
    m1.inputs['Color2'].default_value = (*lin('B0713C'), 1.0)
    m2 = _node(m, 'ShaderNodeMixRGB', -120, 60, 'band23')
    m2.blend_type = 'MIX'
    m2.inputs['Color1'].default_value = (*lin('B0713C'), 1.0)   # 占位，由 m1 接入
    m2.inputs['Color2'].default_value = (*lin('5F6B45'), 1.0)
    for node, thr, target in ((m1, 0.34, 'thr1'), (m2, 0.66, 'thr2')):
        gr = _node(m, 'ShaderNodeMath', -420, -220, target)
        gr.operation = 'GREATER_THAN'
        gr.inputs[1].default_value = thr
        _link(m, blend.outputs['Value'], gr.inputs[0])
        _link(m, gr.outputs['Value'], node.inputs['Fac'])
    _link(m, m1.outputs['Color'], m2.inputs['Color1'])
    _link(m, m2.outputs['Color'], b.inputs['Base Color'])
    m.diffuse_color = (*lin('B0713C'), 1.0)
    return m


def make_glass_fluted():
    """REWORK 2.2：长虹玻璃（竖向细条纹 ~1.8cm 周期 + 磨砂夹胶半透）。"""
    m = bpy.data.materials.new('glass_fluted')
    m.use_nodes = True
    b = _bsdf(m)
    _set(b, 'Base Color', (*lin('EFECE6'), 1.0))
    _set(b, 'Roughness', 0.42)
    _set(b, 'Transmission Weight', 0.7)
    _set(b, 'IOR', 1.45)
    tc = _node(m, 'ShaderNodeTexCoord', -700, 100)
    wv = _node(m, 'ShaderNodeTexWave', -520, 100, 'flutes')
    wv.bands_direction = 'X'
    wv.wave_type = 'BANDS'
    wv.inputs['Scale'].default_value = 55.0      # 1/0.018m ≈ 55：周期约 1.8cm
    wv.inputs['Distortion'].default_value = 0.0
    wv.inputs['Detail'].default_value = 1.0
    _link(m, tc.outputs['Object'], wv.inputs['Vector'])
    bp = _node(m, 'ShaderNodeBump', -300, 100)
    bp.inputs['Strength'].default_value = 0.30
    _link(m, wv.outputs['Fac'], bp.inputs['Height'])
    _link(m, bp.outputs['Normal'], b.inputs['Normal'])
    m.diffuse_color = (*lin('EFECE6'), 0.9)
    return m


def make_rug_accent(name, base_hex, line_hex):
    """孩子房地毯：浅燕麦底 + 点缀色细几何线（REWORK 2.3）。"""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = _bsdf(m)
    _set(b, 'Base Color', (*lin(base_hex), 1.0))
    _set(b, 'Roughness', 0.95)
    tc = _node(m, 'ShaderNodeTexCoord', -800, 100)
    w1 = _node(m, 'ShaderNodeTexWave', -600, 150)
    w1.inputs['Scale'].default_value = 2.6
    w1.inputs['Distortion'].default_value = 1.6
    w1.bands_direction = 'X'
    w2 = _node(m, 'ShaderNodeTexWave', -600, -60)
    w2.inputs['Scale'].default_value = 1.9
    w2.inputs['Distortion'].default_value = 2.2
    w2.bands_direction = 'Y'
    m1 = _node(m, 'ShaderNodeMixRGB', -400, 150)
    m1.inputs['Fac'].default_value = 0.10
    m1.inputs['Color2'].default_value = (*lin(line_hex), 1.0)
    _link(m, tc.outputs['Object'], w1.inputs['Vector'])
    _link(m, tc.outputs['Object'], w2.inputs['Vector'])
    _link(m, w1.outputs['Fac'], m1.inputs['Fac'])
    m2 = _node(m, 'ShaderNodeMixRGB', -260, 60)
    m2.inputs['Fac'].default_value = 0.07
    m2.inputs['Color2'].default_value = (*lin(line_hex), 1.0)
    _link(m, m1.outputs['Color'], m2.inputs['Color1'])
    _link(m, w2.outputs['Fac'], m2.inputs['Fac'])
    _link(m, m2.outputs['Color'], b.inputs['Base Color'])
    m.diffuse_color = (*lin(base_hex), 1.0)
    return m


def build_all_materials():
    """按规格 6.3 材质表建全部材质（名字与表一致）。"""
    mats = {}
    mats['wall_paint'] = base_mat('wall_paint', 'F3F1EC', 0.9)  # F3：F3EFE7→略冷奶白（删后期 WB 后的白墙补偿，D-044）
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
    mats['walnut'] = make_wood('walnut')                    # 预设见 config.WOOD_PRESET
    mats['walnut_dark'] = make_wood('walnut_dark')
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
    # F1 根因修复：变体材质平时无对象使用（0 user），save_as_mainfile 不保存 0-user
    # 数据块 → 渲染进程里 get() 为 None（日志 variant material missing / 0 objs）。
    # use_fake_user 让它随 blend 存活。
    mats['kitchen_lower_olive'].use_fake_user = True
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
    # REWORK 2.5 白平衡收敛：2800K 暖橙 -> 4300K 暖白（17 条 cove 灯带是客厅墙主要暖源）
    _set(b, 'Emission Color', (1.0, 0.90, 0.78, 1.0))
    _set(b, 'Emission Strength', 2.2)
    # 孩子房材质统一移至 REWORK 色板块（下方）
    mats['plant_leaf'] = base_mat('plant_leaf', '4E6E3A', 0.5)
    mats['plant_pot'] = mats['ceramic_brick']
    mats['kitchen_front'] = make_wood('kitchen_front')  # 橄榄绿变体挂载点（REWORK #5 整排下柜共用）
    # ---- REWORK 新增材质 ----
    mats['art_abstract'] = make_art_abstract()          # 挂画画芯（#1/4.1）
    mats['glass_fluted'] = make_glass_fluted()          # 长虹玻璃门芯（2.2）
    mats['book_paper'] = base_mat('book_paper', 'EAE2D3', 0.8)
    mats['book_tan'] = base_mat('book_tan', 'B08B64', 0.75)
    mats['curtain_rose'] = base_mat('curtain_rose', 'E9D9D4', 0.95)  # 女儿房遮光帘（奶白加雾粉）
    _set(_bsdf(mats['curtain_rose']), 'Sheen Weight', 0.3)
    # 孩子房色板（REWORK 2.3，颜色来自 config.KIDS_PALETTE）
    kp = config.KIDS_PALETTE
    mats['kids_son_green'] = base_mat('kids_son_green', kp['son_main'], 0.6)
    mats['kids_son_blue'] = base_mat('kids_son_blue', kp['son_alt'], 0.6)   # 16b 对比版
    mats['kids_son_blue'].use_fake_user = True   # F2：同 kitchen_lower_olive 的 0-user 修复
    mats['kids_daughter_oat'] = base_mat('kids_daughter_oat', kp['daughter_main'], 0.6)
    mats['kids_daughter_rose'] = base_mat('kids_daughter_rose', kp['daughter_accent'], 0.9)
    _set(_bsdf(mats['kids_daughter_rose']), 'Sheen Weight', 0.3)
    mats['kids_milk'] = base_mat('kids_milk', kp['bedding'], 0.6)
    mats['kids_son_tint'] = base_mat('kids_son_tint', 'C9D6C2', 0.9)        # 儿子房床品浅灰绿点缀
    _set(_bsdf(mats['kids_son_tint']), 'Sheen Weight', 0.2)
    mats['kids_butter'] = base_mat('kids_butter', 'F0CF7E', 0.6)            # B 开放格孩子作品用
    mats['rug_son'] = make_rug_accent('rug_son', 'E3D8C2', kp['son_main'])
    mats['rug_daughter'] = make_rug_accent('rug_daughter', 'E9DFCE', kp['daughter_accent'])
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
# 贴砖墙 role -> (砖材质, 湿区/厨房质心) —— 只给朝该区域的面贴砖
WALL_TILE_ZONE = {
    'wall_tile_kitchen': ('tile_kitchen_wall', (5.15, -2.55)),
    'wall_tile_bath_oat': ('tile_bath_oat', (12.2, -4.35)),
    'wall_tile_bath_beige': ('tile_bath_beige', (9.875, -1.25)),
}


def _slot(obj, mat):
    if obj.material_slots:
        obj.material_slots[0].material = mat
    else:
        obj.data.materials.append(mat)


# ================================================================ role 材质体系（REWORK 4.1）
# 直接映射表：role -> 材质名（语境角色在 _resolve_role 里解析）
ROLE_TO_MATERIAL = {
    # 建筑与固定件
    'wall': 'wall_paint',
    'ceiling_paint': 'wall_paint',
    'ceiling_alu': 'ceiling_aluminum',
    'ac_slot': 'metal_black',
    'win_frame': 'window_frame_graphite',
    'win_glass': 'glass_clear',
    'door_frame_wood': 'walnut',
    'door_leaf_wood': 'walnut',
    'door_frame_graphite': 'window_frame_graphite',   # REWORK 2.2 开发商玻璃门框
    'glass_clear': 'glass_clear',
    'glass_fluted': 'glass_fluted',                   # REWORK 2.2 长虹玻璃门芯
    'metal_black': 'metal_black',
    'metal_graphite': 'metal_graphite',
    'floor': None,                                    # 按对象名房间解析（FLOOR_BY_ROOM）
    # 木作与柜体
    'wood': 'walnut',
    'wood_dark': 'walnut_dark',
    'kitchen_front': 'kitchen_front',                 # REWORK #5 变体挂载点
    'quartz_top': 'quartz_top',
    'cabinet_box': 'cabinet_white',
    'cabinet_front': 'cabinet_white',
    'cabinet_white': 'cabinet_white',
    'mirror': 'mirror',
    # 洁具与电器
    'ceramic_white': 'ceramic_white',
    'steel_fridge': 'steel_fridge',
    'black_glass': 'black_glass',
    'sink_graphite': 'metal_graphite',
    # 软装（REWORK 2.4：以下一律禁木色）
    'leather_caramel': 'leather_caramel',
    'sofa_b_fabric': 'fabric_oat',
    'fabric_oat': 'fabric_oat',
    'fabric_olive': 'fabric_olive',
    'seat_oat': 'fabric_oat',
    'pillow_olive': 'fabric_olive',
    'pillow_brick': 'ceramic_brick',
    'throw_oat': 'fabric_oat',
    'bedding': 'bedding_white',
    'rug_a': 'rug_geo',
    'rug': 'rug_plain',
    'art_abstract': 'art_abstract',
    'vase_white': 'ceramic_white',
    'blind': 'fabric_oat',
    'curtain_sheer': 'linen_sheer',
    'curtain_blackout': 'fabric_oat',
    'curtain_daughter': 'curtain_rose',
    # 绿植（REWORK #13：禁黑色方块）
    'plant_leaf': 'plant_leaf',
    'plant_stem': 'plant_leaf',
    'plant_pot_brick': 'ceramic_brick',
    # 灯具
    'opal_glass': 'opal_glass',
    'spot_glass': 'opal_glass',
    'spot_ring': 'metal_black',
    'led_strip': 'led_strip',
    'wall_art': 'wall_art_plaster',
}

# 2.4 禁木色清单（qa.py 材质禁区检查共用）：这些 role 的对象不得挂 walnut 类
ROLE_WOOD_FORBIDDEN = {
    'rug', 'rug_a', 'kids_rug', 'pillow_olive', 'pillow_brick', 'throw_oat',
    'bedding', 'kids_bedding', 'kids_accent', 'cushion_pad', 'fabric_oat',
    'fabric_olive', 'seat_oat', 'sofa_b_fabric', 'leather_caramel',
    'curtain_sheer', 'curtain_blackout', 'curtain_daughter', 'blind',
    'vase_white', 'art_abstract', 'plant_leaf', 'plant_stem', 'plant_pot_brick',
    'kids_furn', 'book', 'toy',
}


def _resolve_role(role, n, root):
    """语境角色解析（孩子房房间色 / 床头软包 / 书与玩具交替色）。返回材质名或 None。"""
    if role in ROLE_TO_MATERIAL:
        return ROLE_TO_MATERIAL[role]
    son = root.startswith('common_son') or '_son_' in root or 'son_room' in root
    daughter = root.startswith('common_daughter') or '_daughter_' in root
    if role == 'kids_furn':
        return 'kids_son_green' if son else 'kids_daughter_oat'
    if role == 'kids_accent':
        return 'kids_son_tint' if son else 'kids_daughter_rose'
    if role == 'kids_bedding':
        return 'bedding_white'   # 奶白底，点缀色由 kids_accent 抱枕体现
    if role == 'kids_rug':
        return 'rug_son' if son else 'rug_daughter'
    if role == 'headboard':
        return 'leather_caramel' if 'master' in root else 'fabric_oat'
    if role == 'book':
        tail = ''.join(ch for ch in n if ch.isdigit())[-1:]
        odd = (int(tail) % 2 == 1) if tail else (len(n) % 2 == 1)
        return 'book_tan' if odd else 'book_paper'
    if role == 'toy':
        idx = int(''.join(ch for ch in n if ch.isdigit()) or 0)
        return ('kids_son_green', 'kids_daughter_rose', 'kids_butter')[idx % 3]
    return None


def _assign_wall_tile(o, mats, role):
    """贴砖墙：wall_paint + tile 双材质，朝湿区/厨房质心的面贴砖（沿用 M4 面分配）。
    REWORK_R1FIX2 F4：端帽面（法线沿墙长轴）一律 wall_paint——砖只能出现在
    朝湿区/厨房的长向面上，不得出现在端面或朝卧室/过道/客厅的面。"""
    zone = WALL_TILE_ZONE[role]
    tile_name, cen = zone
    o.data.materials.clear()
    o.data.materials.append(mats['wall_paint'])
    o.data.materials.append(mats[tile_name])
    from mathutils import Vector
    dims = o.dimensions
    long_x = abs(dims.x) >= abs(dims.y)   # 墙长轴方向
    for p in o.data.polygons:
        c = Vector((0.0, 0.0, 0.0))
        for vi in p.vertices:
            c += o.data.vertices[vi].co
        c /= len(p.vertices)
        w = o.matrix_world @ c
        nrm = p.normal.copy()
        nrm.rotate(o.matrix_world)
        if (long_x and abs(nrm.x) > 0.9) or ((not long_x) and abs(nrm.y) > 0.9):
            p.material_index = 0   # 端帽面不贴砖
            continue
        to_zone = Vector((cen[0] - w.x, cen[1] - w.y, 0.0))
        p.material_index = 1 if nrm.dot(to_zone) > 0 else 0


def apply_all(mats, colls):
    """REWORK #1：正式材质一律由 role 决定（建模时语义角色直给），
    彻底废除"按白模 clay 材质路由"。没有 role 的网格记录并交 qa 判 FAIL。"""
    missing = []
    assigned = 0
    for o in bpy.data.objects:
        if o.type != 'MESH':
            continue
        role = o.get('role')
        if not role:
            missing.append(o.name)
            continue
        if role == 'outdoor':
            continue   # 室外环境在 lighting.py 直接挂最终材质
        n = o.name
        root = o.parent.name if o.parent else ''
        if role.startswith('wall_tile'):
            _assign_wall_tile(o, mats, role)
            assigned += 1
            continue
        if role == 'floor':
            room = n[6:].rsplit('_', 1)[0] if n.startswith('floor_') else ''
            _slot(o, mats[FLOOR_BY_ROOM.get(room, 'floor_tile_800')])
            assigned += 1
            continue
        mat_name = _resolve_role(role, n, root)
        if mat_name is None:
            missing.append('%s(role=%s)' % (n, role))
            continue
        _slot(o, mats[mat_name])
        assigned += 1
    if missing:
        print('[materials] WARN no-role meshes (%d): %s' %
              (len(missing), ', '.join(missing[:8])))
    # A 方案电视墙艺术涂料面板（挂 SCHEME_A；规格 5.2）
    art = util.make_box('fx_art_wall_A', (9.1785, -10.10, 0.0), (9.1835, -5.35, 2.60),
                        coll=colls['scheme_a'], mat=mats['wall_art_plaster'],
                        role='wall_art')
    art.visible_shadow = True
    print('[materials] applied by role: %d assigned, %d missing role' %
          (assigned, len(missing)))

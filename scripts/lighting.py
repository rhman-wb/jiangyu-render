# -*- coding: utf-8 -*-
# lighting.py —— M4 灯光（REWORK R1 版）：晴天 HDRI + 5800K 太阳 + 3000K 点缀灯
# + 无日照房间窗外补光（2.5）+ 室外环境：地坪/树/楼（2.6）
import math
import os

import bpy

import config
import util

# REWORK 2.6：roof_garden（地面层玻璃顶棚花园）弃用，换晴天/薄云、无建筑、天空干净的 HDRI
# （Poly Haven kloofendal_48d_partly_cloudy_puresky：48° 太阳高度≈上午，纯天空版，选型见 decisions_log）
HDRI = os.path.join(config.ASSET_DIR, 'kloofendal_48d_partly_cloudy_puresky_4k.hdr')
K3000 = (1.0, 0.50, 0.25)     # 3000K→3300K 折中（点缀：灯带/壁灯/吊灯；qa_render R-B 超标后收敛）
K4000 = (1.0, 0.70, 0.44)     # 4000K（厨卫筒灯：无日照房间的摄影补光感，避免整屋偏橙）
K6500 = (1.0, 0.99, 0.97)     # 6500K
K5700 = (1.0, 0.955, 0.925)  # 5700K（R1FIX：白墙 R-B<=22 第三轮）（R1FIX F3：5200K 再提白，白墙 R-B<=22 不靠后期） 主照明（筒灯/吸顶）：REWORK 2.5 白墙 R-B<=18 的硬约束（REWORK 2.5 白平衡收敛：太阳+补光提白压暖）


def _light(name, ltype, loc, coll, energy, color=K3000, parent=None, **kw):
    data = bpy.data.lights.new(name, ltype)
    data.energy = energy
    data.color = color
    for k, v in kw.items():
        try:
            setattr(data, k, v)
        except Exception:
            pass
    o = bpy.data.objects.new(name, data)
    o.location = loc
    coll.objects.link(o)
    if parent is not None:
        o.parent = parent
    return o


def _fill_light(name, loc, rot, size, energy, coll, color=K6500):
    """REWORK 2.5 不可见补光面光：只贡献照明，相机/反射里不直接可见。
    FINAL1 F12：补 visible_transmission=False——旧版漏关透射可见性，隔着窗
    玻璃能看见白面光本体（15/16/18/19"窗内白块"的实体）。"""
    lt = _light(name, 'AREA', loc, coll, energy, color=color,
                size=size[0], size_y=size[1], spread=math.radians(75))
    lt.rotation_euler = rot
    lt.visible_camera = False
    lt.visible_diffuse = False
    lt.visible_glossy = False
    lt.visible_transmission = False
    return lt


def build_world():
    world = bpy.data.worlds.get('jy_world')
    if world is None:
        world = bpy.data.worlds.new('jy_world')
    bpy.context.scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    bg = next(n for n in nt.nodes if n.type == 'BACKGROUND')
    if os.path.isfile(HDRI):
        env = nt.nodes.new('ShaderNodeTexEnvironment')
        env.image = bpy.data.images.load(HDRI)
        env.image.colorspace_settings.name = 'Linear Rec.709'
        env.location = (-600, 0)
        # REWORK 2.5 白平衡收敛：HDRI 是暖调（草地+上午光），间接光区全屋偏黄。
        # 输出接 HueSaturation 降饱和提亮 -> 环境漫射整体提白（qa_render R-B<=18）。
        hsv = nt.nodes.new('ShaderNodeHueSaturation')
        hsv.inputs['Saturation'].default_value = 0.60
        hsv.inputs['Value'].default_value = 1.12
        hsv.location = (-430, 0)
        nt.links.new(env.outputs['Color'], hsv.inputs['Color'])
        nt.links.new(hsv.outputs['Color'], bg.inputs['Color'])
    else:
        # 干净天空色回退（屋顶花园 HDRI 已弃用，宁缺毋滥）
        bg.inputs['Color'].default_value = (0.52, 0.62, 0.78, 1.0)
    bg.inputs['Strength'].default_value = 0.7   # 暖 HDRI 降权（R-B 收敛）


def build_sun(coll):
    """太阳来自南偏西（光行进方向 ≈ (+0.25,+0.94,down)），5800K，2.5° 柔角。"""
    s = _light('lt_sun', 'SUN', (0, 0, 10), coll, 4.5, color=K6500,
               angle=math.radians(2.5))
    s.rotation_euler = (math.radians(76.7), 0.0, math.radians(-15.4))
    return s


LIVING_SPOTS = [(4.3, -11.35), (5.4, -11.35), (6.5, -11.35), (7.6, -11.35), (8.4, -11.35),
                (4.3, -4.20), (5.4, -4.20), (6.5, -4.20), (7.6, -4.20), (8.4, -4.20),
                (3.57, -10.2), (3.57, -9.1), (3.57, -6.8), (3.57, -5.6),
                (9.02, -10.9), (9.02, -6.9), (9.02, -5.6)]
ROOM_SPOTS = [(11.0, -8.8, 2.85, 5.0, K5700), (11.0, -6.6, 2.85, 5.0, K5700),
              (1.75, -9.5, 2.85, 5.0, K5700), (7.65, -3.0, 2.85, 5.0, K5700),
              (12.2, -2.9, 2.85, 5.0, K5700), (9.9, -4.4, 2.60, 8.0, K4000),
              (10.6, -3.0, 2.60, 8.0, K4000), (2.7, -5.7, 2.85, 5.0, K5700),
              # 厨房 / 主卫 / 公卫（铝扣板顶筒灯：无日照房间，4000K 摄影补光感）
              (4.6, -2.6, 2.395, 10.0, (1.0, 0.83, 0.68)), (5.7, -2.6, 2.395, 10.0, (1.0, 0.83, 0.68)),  # R1FIX F1: 厨房筒灯 4700K 让 olive 读作绿
              (11.3, -4.9, 2.395, 10.0, K4000), (12.6, -4.6, 2.395, 10.0, K4000),
              (9.5, -1.9, 2.395, 10.0, K4000), (10.4, -0.7, 2.395, 10.0, K4000)]
CEILING_LAMPS = {'master': (11.0, -7.7, 13.0), 'parents': (1.75, -8.3, 10.0),
                 'daughter': (7.65, -2.05, 10.0), 'son': (12.2, -1.8, 10.0)}


def build_lights(mats, colls):
    import mathutils
    common = colls['common']
    build_world()
    build_sun(common)
    for i, (x, y) in enumerate(LIVING_SPOTS):
        _light('lt_spot_liv%02d' % i, 'SPOT', (x, y, 2.595), common, 5.0, color=K5700,
               spot_size=math.radians(55), shadow_soft_size=0.08)
    for i, (x, y, z, watts, col) in enumerate(ROOM_SPOTS):
        _light('lt_spot_room%d' % i, 'SPOT', (x, y, z), common, watts, color=col,
               spot_size=math.radians(55), shadow_soft_size=0.08)
    for rid, (cx, cy, w) in CEILING_LAMPS.items():
        _light('lt_ceiling_%s' % rid, 'POINT', (cx, cy, 2.77), common, w, color=K5700,
               shadow_soft_size=0.15)
    # 床头壁灯
    for i, (x, y) in enumerate([(12.60, -7.0), (12.60, -9.2), (0.32, -8.65)]):
        _light('lt_wall%d' % i, 'POINT', (x, y, 1.42), common, 4.0,
               color=(1.0, 0.80, 0.62), shadow_soft_size=0.10)  # 壁灯 4600K 暖点缀
    # 吊灯（跟方案走：挂在 item 父 Empty 下）
    for iid, loc in (('A_living_dining_balcony_pendant_lamp_01', (4.9, -5.4, 2.02)),
                     ('A_living_dining_balcony_pendant_lamp_02', (6.55, -5.4, 1.97)),
                     ('B_living_dining_balcony_pendant_lamp_01', (4.9, -5.4, 2.02)),
                     ('B_living_dining_balcony_pendant_lamp_02', (6.8, -5.42, 1.97))):
        root = bpy.data.objects.get(iid)
        if root is None:
            continue
        coll = root.users_collection[0]
        _light('lt_pendant_' + iid[-2:], 'POINT', loc, coll, 20.0,
               shadow_soft_size=0.20, parent=root)
    # 灯带（自发光条，见光不见灯）。REWORK #2：方案专用灯带挂对应集合
    common_strips = []
    # 客餐厅边吊内缘（cove 向上）
    x0, y0, x1, y1 = 3.80, -11.15, 8.80, -4.40
    common_strips += [('S', (x0, y0 - 0.02, 2.845), (x1, y0 + 0.01, 2.858)),
                      ('N', (x0, y1 - 0.01, 2.845), (x1, y1 + 0.02, 2.858)),
                      ('W', (x0 - 0.02, y0, 2.845), (x0 + 0.01, y1, 2.858)),
                      ('E', (x1 - 0.01, y0, 2.845), (x1 + 0.02, y1, 2.858))]
    # 厨房吊柜底
    common_strips += [('kc1', (5.95, -2.46, 1.495), (6.30, -1.26, 1.508)),
                      ('kc2', (3.96, -3.26, 1.395), (4.30, -1.86, 1.408))]
    # 玄关：柜底 + 开放格顶
    common_strips += [('fyb', (2.00, -6.56, 0.192), (3.35, -6.24, 0.205)),
                      ('fyn', (2.00, -6.56, 1.282), (3.35, -6.44, 1.295))]
    # 组合柜开放格顶 / 玻璃柜内顶（R2FIX2 N1：跨度收进真腔单元）/ 镜柜底 / 梳妆台吊柜底
    common_strips += [('bc', (3.45, -9.83, 2.216), (3.78, -9.285, 2.229)),
                      ('bcg', (3.45, -10.365, 2.216), (3.78, -9.90, 2.229)),
                      ('mb', (10.87, -3.60, 1.192), (11.73, -3.52, 1.205)),
                      ('cb', (9.07, -3.85, 1.142), (9.15, -2.49, 1.155)),
                      ('dt', (9.32, -10.06, 1.392), (9.63, -9.14, 1.405))]
    for tag, a, b in common_strips:
        util.make_box('lt_strip_%s' % tag, a, b, coll=common, mat=mats['led_strip'],
                      role='led_strip')
    # A 方案电视柜底灯带 → SCHEME_A
    util.make_box('lt_strip_tv', (8.82, -10.06, 0.242), (9.13, -7.14, 0.255),
                  coll=colls['scheme_a'], mat=mats['led_strip'], role='led_strip')
    # B 方案整墙柜开放格顶灯带 → SCHEME_B
    util.make_box('lt_strip_bn', (8.97, -10.13, 1.482), (9.18, -5.37, 1.495),
                  coll=colls['scheme_b'], mat=mats['led_strip'], role='led_strip')

    # ---- REWORK 2.5：无日照房间窗外不可见补光（模拟真实摄影补光）----
    RX = math.radians(-90)   # 面光朝 -Y（南）
    RY = math.radians(90)    # 面光朝 -X（西）
    fills = [
        # (名, 位置, 旋转, 尺寸, 功率)  —— 南北窗 / 东西窗
        ('lt_fill_daughter', (7.65, 0.75, 1.75), (RX, 0, 0), (2.2, 1.4), 120.0),  # W01
        ('lt_fill_son', (12.2, 0.75, 1.7), (RX, 0, 0), (1.6, 1.3), 100.0),        # W06
        # R2FIX 复测修正：厨房穿窗补光在本窗洞几何下（窗下紧贴亮台面）光束回弹
        # 必然把窗头墙带+窗框打到 255（6 轮灯位/尺寸/功率/俯仰实验复现，过程记
        # decisions_log），且窗框周腔已修仍不解决。删除该补光，改由世界光承担、
        # 09/10 机位曝光提至 2.25（cameras.py）——qa 采样框白占比 0%。
        # ('lt_fill_kitchen', (5.15, 0.30, 1.50), (RX, 0, 0), (0.9, 0.55), 45.0),  # 已停用
        ('lt_fill_pbath', (9.9, 0.55, 1.85), (RX, 0, 0), (0.6, 0.7), 60.0),       # W05
        ('lt_fill_mbath', (14.45, -4.35, 1.75), (0, RY, 0), (1.0, 0.9), 60.0),    # W10
        ('lt_fill_corridor', (10.2, -3.6, 2.52), (0, 0, 0), (1.5, 1.0), 25.0),    # 干区顶柔光
    ]
    for name, loc, rot, size, watts in fills:
        _fill_light(name, loc, rot, size, watts, common)
    print('[lighting] done')


# ================================================================ 室外环境（REWORK 2.6）
def _outdoor_mat(name, hexcol, rough, noise_scale=30.0, noise_mix=0.15):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    i = b.inputs.get('Base Color')
    if i is not None:
        i.default_value = (*util.srgb_to_linear(hexcol), 1.0)
    ri = b.inputs.get('Roughness')
    if ri is not None:
        ri.default_value = rough
    nz = m.node_tree.nodes.new('ShaderNodeTexNoise')
    nz.inputs['Scale'].default_value = noise_scale
    nz.inputs['Detail'].default_value = 8
    mix = m.node_tree.nodes.new('ShaderNodeMixRGB')
    mix.inputs['Fac'].default_value = noise_mix
    mix.inputs['Color1'].default_value = (*util.srgb_to_linear(hexcol), 1.0)
    mix.inputs['Color2'].default_value = (*util.srgb_to_linear('6E7F58'), 1.0)
    m.node_tree.links.new(nz.outputs['Color'], mix.inputs['Fac'])
    m.node_tree.links.new(mix.outputs['Color'], b.inputs['Base Color'])
    c = util.srgb_to_linear(hexcol)
    m.diffuse_color = (c[0], c[1], c[2], 1.0)
    return m


def _bldg_window_mat(name, hexcol, win_hex, rough=0.6):
    """R2FIX M4：远处住宅楼 + 窗格（TexBrick 暗带=窗），避免大面纯色块。"""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    tc = m.node_tree.nodes.new('ShaderNodeTexCoord')
    br = m.node_tree.nodes.new('ShaderNodeTexBrick')
    br.inputs['Scale'].default_value = 1.0
    br.inputs['Color1'].default_value = (*util.srgb_to_linear(hexcol), 1.0)
    br.inputs['Color2'].default_value = (*util.srgb_to_linear(hexcol), 1.0)
    br.inputs['Mortar'].default_value = (*util.srgb_to_linear(win_hex), 1.0)
    br.inputs['Mortar Size'].default_value = 0.22
    br.inputs['Brick Width'].default_value = 1.4
    br.inputs['Row Height'].default_value = 0.85
    m.node_tree.links.new(tc.outputs['Object'], br.inputs['Vector'])
    m.node_tree.links.new(br.outputs['Color'], b.inputs['Base Color'])
    ri = b.inputs.get('Roughness')
    if ri is not None:
        ri.default_value = rough
    c = util.srgb_to_linear(hexcol)
    m.diffuse_color = (c[0], c[1], c[2], 1.0)
    return m


def build_outdoor(mats_unused, colls):
    """REWORK 2.6：3 楼室外环境 —— 地坪 Z=-6.0（草地+园路）、南北树（冠 6-10m）、
    远处 1-2 栋浅色住宅楼；从室内看出去是"略高于树冠、俯视花园"。"""
    common = colls['common']
    out = util.get_collection('OUTDOOR', parent=common)
    Z = -6.0
    # R2 #16：草地更"草地"（旧 7E8F63 在鸟瞰曝光下读作沥青灰）
    grass = _outdoor_mat('out_grass', '8CA465', 0.95, noise_scale=8.0, noise_mix=0.35)
    path = _outdoor_mat('out_path', 'C9C2B4', 0.85, noise_scale=40.0, noise_mix=0.10)
    canopy = _outdoor_mat('out_canopy', '5A7048', 0.9, noise_scale=6.0, noise_mix=0.45)
    trunk = _outdoor_mat('out_trunk', '6B5A48', 0.9, noise_scale=60.0, noise_mix=0.2)
    bldg = _outdoor_mat('out_building', 'D8D4CC', 0.7, noise_scale=3.0, noise_mix=0.06)

    # 草地（大平面）+ 园路（南侧两条弧感直道示意）
    util.make_box('out_ground', (-25.0, -40.0, Z - 0.1), (40.0, 15.0, Z),
                  coll=out, mat=grass, role='outdoor')
    util.make_box('out_path_s', (-2.0, -19.5, Z), (30.0, -18.0, Z + 0.02),
                  coll=out, mat=path, role='outdoor')
    util.make_box('out_path_n', (0.0, 5.5, Z), (26.0, 6.8, Z + 0.02),
                  coll=out, mat=path, role='outdoor')

    # R2 #17：Poly Haven 真树替换低多边形球冠——Jacaranda（阔冠，南 8 棵）+
    # Tree Small 02（直干庭院树，北 6 棵）。glTF(1k 纹理) 导入后 decimate 减面
    # （LOD0 约 3.9M/2.0M tri，背景 15-25m 用量），linked duplicate 复用 14 处。
    import random
    import bmesh
    rnd = random.Random(20261002)   # 可复现
    spots_s = [(-8.0, -20.5), (-2.5, -23.0), (5.0, -21.0), (12.0, -24.0),
               (18.5, -20.0), (25.0, -22.5), (-14.0, -17.5), (30.0, -18.0)]
    # FINAL1 F12：北窗新增 2 棵加大树——女儿房 W01(x6.5-8.8)/儿子房 W06(x11.4-13.0)
    # 视线原先只擦过远树，窗上部读作死白。追加在既有 6 点之后（随机序列不漂移）。
    spots_n = [(0.0, 8.5), (6.5, 11.0), (13.0, 9.0), (20.0, 12.5), (-6.0, 11.5),
               (27.0, 8.0), (7.6, 9.5), (12.2, 9.5)]
    FORCE_SCALE = {(6.5, 11.0): 3.2,   # 厨房北窗（R2FIX M4 既有）
                   (7.6, 9.5): 3.0,    # FINAL1 F12 女儿房 W01
                   (12.2, 9.5): 3.0}   # FINAL1 F12 儿子房 W06
    tree_specs = [('jacaranda_tree_1k', 0.40, 0.12, spots_s),
                  ('tree_small_02_1k', 1.9, 0.18, spots_n)]
    for aid, sc, dec_ratio, spots in tree_specs:
        path = os.path.join(config.ASSET_DIR, 'trees', aid, aid + '.gltf')
        if not os.path.isfile(path):
            print('[lighting][warn] tree asset missing: %s' % path)
            continue
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=path)
        imported = list(set(bpy.data.objects) - before)
        mesh_objs = [o for o in imported if o.type == 'MESH']
        for o in imported:                      # 非网格（空节点）直接删
            if o.type != 'MESH':
                bpy.data.objects.remove(o)
        if not mesh_objs:
            print('[lighting][warn] no mesh imported from %s' % aid)
            continue
        tmpl = mesh_objs[0]
        tmpl.select_set(True)
        bpy.context.view_layer.objects.active = tmpl
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        dec = tmpl.modifiers.new('dec', 'DECIMATE')
        dec.ratio = dec_ratio
        bpy.ops.object.modifier_apply(modifier='dec')
        # 原点归树底：包围盒最低点移到 Z
        zs = [tmpl.matrix_world @ v.co for v in tmpl.data.vertices]
        z_base = min(v.z for v in zs)
        for v in tmpl.data.vertices:
            v.co.z -= z_base
        tmpl.data.update()
        for o in mesh_objs[1:]:
            bpy.data.objects.remove(o)
        for o in mesh_objs:
            o['role'] = 'outdoor'
            o.select_set(False)
        # R2FIX 复测修正：树冠向阳面在日光+曝光下读作纯白高光块（09 号采样框
        # 树冠命中像素 255/0 实测），整树 Base Color 乘 0.5 压高光——模板材质
        # 为 linked duplicate 共享，一处修改全 14 处生效
        for ms in tmpl.material_slots:
            m = ms.material
            if m is None or not m.use_nodes:
                continue
            bnode = next((n for n in m.node_tree.nodes
                          if n.type == 'BSDF_PRINCIPLED'), None)
            if bnode is None:
                continue
            bc = bnode.inputs['Base Color']
            if bc.is_linked:
                mul = m.node_tree.nodes.new('ShaderNodeMixRGB')
                mul.blend_type = 'MULTIPLY'
                mul.inputs['Fac'].default_value = 1.0
                mul.inputs['Color2'].default_value = (0.5, 0.5, 0.5, 1.0)
                src = bc.links[0].from_socket
                m.node_tree.links.new(src, mul.inputs['Color1'])
                m.node_tree.links.new(mul.outputs['Color'], bc)
            else:
                c4 = bc.default_value
                bc.default_value = (c4[0] * 0.5, c4[1] * 0.5, c4[2] * 0.5, c4[3])
        # 14 处布点由两品种分担：linked duplicate（共享网格数据）
        # R2FIX M4：北窗旁 (6.5,11.0) 一棵加大（tree_small 3.2x ≈ 15m），冠面
        # 填满厨房北窗上半（原天空带读作白色空块）
        for i, (px, py) in enumerate(spots):
            dup = tmpl.copy()                   # 共享网格（linked）
            s = sc * (0.9 + rnd.random() * 0.25)
            if aid.startswith('tree_small') and (px, py) in FORCE_SCALE:
                s = sc * FORCE_SCALE[(px, py)]
            dup.location = (px, py, Z)
            dup.scale = (s, s, s)
            dup.rotation_euler = (0.0, 0.0, rnd.random() * 6.28)
            dup['role'] = 'outdoor'
            out.objects.link(dup)
        # 模板本体隐藏（仅作数据源）
        tmpl.location = (0.0, 0.0, -30.0)
        tmpl.hide_render = True
        tmpl.hide_viewport = True
        tmpl['role'] = 'outdoor'
        out.objects.link(tmpl)

    # 远处浅色住宅楼体块（南北各一，隔花园相望）
    # R2FIX M4：北楼原在 (-22..-6, 22..38)——09/10 号厨房窗外视野锥（东北向）内
    # 无任何室外景物，窗内读作白色空块（ray_cast 证实脱靶）。北楼挪入厨房北窗
    # 视野锥内的远端（离窗 >15m），上下窗段均有景物。
    # R2FIX M4：北楼带窗格材质（挪入厨房北窗视野锥远端，离窗 >15m）——
    # 楼体调深 + 窗带加宽，避免阳光曝成"近白纯色块"（首版 D8D4CC 实测 49.9% 近白；
    # 二轮 B5AC9F 向阳面仍读 255/0，三轮再压深至 8A8275）
    bldgwin = _bldg_window_mat('out_bldg_n_win', '8A8275', '252B31', 0.6)
    util.make_box('out_bldg_s', (10.0, -48.0, Z), (26.0, -32.0, Z + 34.0),
                  coll=out, mat=bldg, role='outdoor')
    util.make_box('out_bldg_n', (8.0, 18.0, Z), (22.0, 30.0, Z + 30.0),
                  coll=out, mat=bldgwin, role='outdoor')

    # R2FIX m4：鸟瞰浅色纯底（REWORK 2.7 #F2F0EC）——自发光抬亮抵消 AgX/光照衰减，
    # render.py 在鸟瞰机位隐 grass 显本底（树保留，投影淡淡落在底上）
    aerial_base = bpy.data.materials.new('out_aerial_base')
    aerial_base.use_nodes = True
    ab_b = next(n for n in aerial_base.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    ab_b.inputs['Base Color'].default_value = (*util.srgb_to_linear('F2F0EC'), 1.0)
    ab_b.inputs['Roughness'].default_value = 0.9
    ei = ab_b.inputs.get('Emission Color')
    es = ab_b.inputs.get('Emission Strength')
    if ei is not None and es is not None:
        ei.default_value = (*util.srgb_to_linear('F2F0EC'), 1.0)
        es.default_value = 0.55
    c_ab = util.srgb_to_linear('F2F0EC')
    aerial_base.diffuse_color = (c_ab[0], c_ab[1], c_ab[2], 1.0)
    ab = util.make_box('out_aerial_base', (-25.0, -40.0, Z - 0.09), (40.0, 15.0, Z - 0.08),
                       coll=out, mat=aerial_base, role='outdoor')
    ab.hide_render = True
    ab.hide_viewport = True
    print('[lighting] outdoor env done')


def build_all(mats, colls):
    build_lights(mats, colls)
    build_outdoor(mats, colls)

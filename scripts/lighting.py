# -*- coding: utf-8 -*-
# lighting.py —— M4 灯光：Poly Haven HDRI + 太阳（南偏西）+ 3000K 室内灯 + 灯带
import math
import os

import bpy

import config
import util

HDRI = os.path.join(config.ASSET_DIR, 'roof_garden_4k.hdr')
K3000 = (1.0, 0.445, 0.194)   # 3000K 线性色（Blackbody 等效）
K5200 = (1.0, 0.93, 0.85)


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
        env.location = (-400, 0)
        nt.links.new(env.outputs['Color'], bg.inputs['Color'])
    else:
        bg.inputs['Color'].default_value = (0.55, 0.62, 0.72, 1.0)
    bg.inputs['Strength'].default_value = 1.0


def build_sun(coll):
    """太阳来自南偏西（光行进方向 ≈ (+0.25,+0.94,down)），5200K，2.5° 柔角。"""
    s = _light('lt_sun', 'SUN', (0, 0, 10), coll, 3.5, color=K5200,
               angle=math.radians(2.5))
    s.rotation_euler = (math.radians(76.7), 0.0, math.radians(-15.4))
    return s


LIVING_SPOTS = [(4.3, -11.35), (5.4, -11.35), (6.5, -11.35), (7.6, -11.35), (8.4, -11.35),
                (4.3, -4.20), (5.4, -4.20), (6.5, -4.20), (7.6, -4.20), (8.4, -4.20),
                (3.57, -10.2), (3.57, -9.1), (3.57, -6.8), (3.57, -5.6),
                (9.02, -10.9), (9.02, -6.9), (9.02, -5.6)]
ROOM_SPOTS = [(11.0, -8.8, 2.85, 5.0), (11.0, -6.6, 2.85, 5.0),
              (1.75, -9.5, 2.85, 5.0), (7.65, -3.0, 2.85, 5.0),
              (12.2, -2.9, 2.85, 5.0), (9.9, -4.4, 2.60, 8.0),
              (10.6, -3.0, 2.60, 8.0), (2.7, -5.7, 2.85, 5.0),
              # 厨房 / 主卫 / 公卫（铝扣板顶筒灯，无日照需更高功率）
              (4.6, -2.6, 2.395, 15.0), (5.7, -2.6, 2.395, 15.0),
              (11.3, -4.9, 2.395, 15.0), (12.6, -4.6, 2.395, 15.0),
              (9.5, -1.9, 2.395, 15.0), (10.4, -0.7, 2.395, 15.0)]
CEILING_LAMPS = {'master': (11.0, -7.7), 'parents': (1.75, -8.3),
                 'daughter': (7.65, -2.05), 'son': (12.2, -1.8)}


def build_lights(mats, colls):
    import mathutils
    common = colls['common']
    build_world()
    build_sun(common)
    down = mathutils.Vector((0.0, 0.0, -1.0))
    for i, (x, y) in enumerate(LIVING_SPOTS):
        # Spot 默认朝 -Z（向下），无需旋转
        _light('lt_spot_liv%02d' % i, 'SPOT', (x, y, 2.595), common, 5.0,
               spot_size=math.radians(55), shadow_soft_size=0.08)
    for i, (x, y, z, watts) in enumerate(ROOM_SPOTS):
        _light('lt_spot_room%d' % i, 'SPOT', (x, y, z), common, watts,
               spot_size=math.radians(55), shadow_soft_size=0.08)
    for rid, (cx, cy) in CEILING_LAMPS.items():
        _light('lt_ceiling_%s' % rid, 'POINT', (cx, cy, 2.77), common, 16.0,
               shadow_soft_size=0.15)
    # 床头壁灯
    for i, (x, y) in enumerate([(12.60, -7.0), (12.60, -9.2), (0.32, -8.65)]):
        _light('lt_wall%d' % i, 'POINT', (x, y, 1.42), common, 10.0,
               shadow_soft_size=0.10)
    # 吊灯（跟方案走：挂在 item 父 Empty 下）
    for iid, loc in (('A_living_dining_balcony_pendant_lamp_01', (4.9, -5.4, 2.02)),
                     ('A_living_dining_balcony_pendant_lamp_02', (6.55, -5.4, 1.97)),
                     ('B_living_dining_balcony_pendant_lamp_01', (4.9, -5.4, 2.02)),
                     ('B_living_dining_balcony_pendant_lamp_02', (6.8, -5.42, 1.97))):
        root = bpy.data.objects.get(iid)
        if root is None:
            continue
        coll = root.users_collection[0]
        _light('lt_pendant_' + iid[-2:], 'POINT', loc, coll, 30.0,
               shadow_soft_size=0.20, parent=root)
    # 灯带（自发光条，见光不见灯）
    strips = []
    # 客餐厅边吊内缘（cove 向上）
    x0, y0, x1, y1 = 3.80, -11.15, 8.80, -4.40
    strips += [('S', (x0, y0 - 0.02, 2.845), (x1, y0 + 0.01, 2.858)),
               ('N', (x0, y1 - 0.01, 2.845), (x1, y1 + 0.02, 2.858)),
               ('W', (x0 - 0.02, y0, 2.845), (x0 + 0.01, y1, 2.858)),
               ('E', (x1 - 0.01, y0, 2.845), (x1 + 0.02, y1, 2.858))]
    # 厨房吊柜底
    strips += [('kc1', (5.95, -2.46, 1.495), (6.30, -1.26, 1.508)),
               ('kc2', (3.96, -3.26, 1.395), (4.30, -1.86, 1.408))]
    # 玄关：柜底 + 开放格顶
    strips += [('fyb', (2.00, -6.56, 0.192), (3.35, -6.24, 0.205)),
               ('fyn', (2.00, -6.56, 1.282), (3.35, -6.44, 1.295))]
    # 电视柜底（A）
    strips += [('tv', (8.82, -10.06, 0.242), (9.13, -7.14, 0.255))]
    # B 整墙柜开放格顶 / 组合柜开放格顶
    strips += [('bn', (8.97, -10.13, 1.482), (9.18, -5.37, 1.495)),
               ('bc', (3.44, -9.93, 2.222), (3.80, -9.22, 2.235))]
    # 镜柜底（主卫/过道）
    strips += [('mb', (10.87, -3.60, 1.192), (11.73, -3.52, 1.205)),
               ('cb', (9.07, -3.85, 1.142), (9.15, -2.49, 1.155))]
    # 梳妆台吊柜底 + 镜顶
    strips += [('dt', (9.32, -10.06, 1.392), (9.63, -9.14, 1.405))]
    for tag, a, b in strips:
        util.make_box('lt_strip_%s' % tag, a, b, coll=common, mat=mats['led_strip'])
    print('[lighting] done')


def build_all(mats, colls):
    build_lights(mats, colls)

# -*- coding: utf-8 -*-
# cameras.py —— 读 cameras.json 建 23 个机位。
# 规则（cameras.json meta）：透视机位两点透视（水平，shift_y 调构图）；
# 鸟瞰允许俯视（Track To）；PANO 用 EQUIRECT（Blender 4.0+ 在 camera.data）。
import math
import bpy

import config
import util

SHIFT_LIMIT = 0.15

# 机位碰撞微调（cameras.json meta 规则：0.3m 内调整并记录）
# REWORK #9：03/06、11、16/16b、18 机位遮挡修正；REWORK 2.5：全机位曝光初值（+0.7~+1.5，按白墙采样迭代）
CAM_OVERRIDES = {
    # --- REWORK #9 遮挡修正 ---
    '03_living_A_from_foyer': {'location': (3.95, -6.35, 1.35), 'exposure': 1.80},
    '06_living_B_from_foyer': {'location': (3.95, -6.35, 1.35), 'exposure': 1.80},
    '11_foyer': {'location': (2.65, -6.02, 1.5), 'look_at': (2.60, -4.85, 1.05), 'lens': 18,
                 'exposure': 2.25},   # FINAL1 D7：回看入户门；D3 曝光反推 147->210
    '11b_foyer_cabinet': {'exposure': 2.25},   # FINAL1 D7 新增：端景柜+鞋柜+镜面门
    '16_son_room': {'location': (11.3, -2.6, 1.45), 'exposure': 1.95},
    '16b_son_room_blue': {'location': (11.3, -2.6, 1.45), 'exposure': 1.95},
    '18_public_bath_wet': {'location': (9.90, -2.20, 1.35),   # FINAL1 D11：正常视高（取代 D-056）
                           'look_at': (9.55, -0.55, 1.10), 'lens': 19,
                           'exposure': 2.25},
    # --- 曝光初值（其余机位）---
    '01_aerial_A': {'exposure': 1.15},   # R2FIX m4：+0.3 提亮浅色纯底
    '02_aerial_B': {'exposure': 1.15},
    '04_living_A_from_balcony': {'exposure': 1.80},
    '05_living_A_tv_wall': {'exposure': 1.55},
    '07_living_B_from_balcony': {'exposure': 1.80},
    '08_living_B_tv_wall': {'exposure': 1.80},
    '09_kitchen_walnut': {'exposure': 1.95},   # FINAL1 D3：WB+世界光提权后压曝光保缝线对比
    '10_kitchen_olive': {'exposure': 1.95},
    '12_master_bed_screen': {'exposure': 1.75},
    '13_master_wardrobe_vanity': {'exposure': 2.20},   # D3：224/231 略超 225 降一档
    '14_parents_room': {'exposure': 1.15},   # D3：242.6 略超 225
    '15_daughter_room': {'exposure': 1.95},   # 北向无直射光
    '17_public_bath_dry': {'exposure': 2.15},   # D3：176->210
    '19_master_bath': {'exposure': 2.25},   # D3：188->210
    '20_terrace': {'exposure': 0.75,
                   # R2FIX2 N2：相机移入露台范围内（工单定值 (9.65,-10.5,1.5) 望
                   # (11.6,-11.7,0.6)，lens 18；plant_01 (9.6,-10.5) 在机位下方不碰；
                   # 前景栏杆穿画与"悬空机位"废弃。俯视目标由 shift_y 机制自动承担）
                   'location': (9.65, -10.5, 1.5), 'look_at': (11.6, -11.7, 0.6),
                   'lens': 18},
    'P1_living_A_pano': {'exposure': 1.75},
    'P2_living_B_pano': {'exposure': 1.75},
    'P3_master_pano': {'exposure': 1.95},
}


def _shift_y(loc, look, lens_mm, res):
    """两点透视 shift_y：让目标高的点大致落在画面中心。"""
    dx, dy = look[0] - loc[0], look[1] - loc[1]
    dist = math.hypot(dx, dy)
    if dist < 1e-6:
        return 0.0, 0.0
    tan_t = (look[2] - loc[2]) / dist
    aspect = res[0] / res[1]
    sensor_h = 36.0 / aspect  # sensor_fit=HORIZONTAL 时的等效传感器高
    s = lens_mm * tan_t / sensor_h
    clamped = max(-SHIFT_LIMIT, min(SHIFT_LIMIT, s))
    return s, clamped


def build_all(coll):
    cams = util.load_cameras()['cameras']
    made = []
    for c in cams:
        cid = c['id']
        ov = CAM_OVERRIDES.get(cid, {})   # REWORK #9：支持 location/look_at/lens/exposure 覆盖
        loc = ov.get('location', c['location'])
        look = ov.get('look_at', c['look_at'])
        cam_data = bpy.data.cameras.new('cd_%s' % cid)
        cam = bpy.data.objects.new('cam_%s' % cid, cam_data)
        coll.objects.link(cam)
        cam.location = loc
        if 'exposure' in ov:
            cam['exposure'] = ov['exposure']
        cam_data.sensor_fit = 'HORIZONTAL'
        cam_data.sensor_width = c.get('sensor_width_mm', 36)
        cam_data.clip_start = 0.02
        cam_data.clip_end = 300.0

        is_pano = c['type'] == 'PANO_EQUIRECT'
        is_aerial = 'aerial' in cid
        if is_pano:
            cam_data.type = 'PANO'
            cam_data.panorama_type = 'EQUIRECTANGULAR'  # 4.0+ 位置在 camera.data
            yaw = math.atan2(-(look[0] - cam.location[0]),
                              look[1] - cam.location[1])
            cam.rotation_euler = (math.radians(90), 0.0, yaw)
            shift_raw = shift_used = 0.0
        elif is_aerial:
            aim = bpy.data.objects.new('aim_%s' % cid, None)
            aim.location = look
            aim.empty_display_size = 0.5
            coll.objects.link(aim)
            con = cam.constraints.new('TRACK_TO')
            con.target = aim
            con.track_axis = 'TRACK_NEGATIVE_Z'
            con.up_axis = 'UP_Y'
            cam_data.lens = ov.get('lens', c.get('lens_mm', 32))
            shift_raw = shift_used = 0.0
        else:
            cam_data.lens = ov.get('lens', c.get('lens_mm', 18))
            d = look
            yaw = math.atan2(-(d[0] - cam.location[0]), d[1] - cam.location[1])
            # REWORK_R1FIX F5：tilt_deg 允许低机位俯拍（两点透视无解的机位）
            rx = 90.0 - ov.get('tilt_deg', 0.0)
            cam.rotation_euler = (math.radians(rx), 0.0, yaw)
            shift_raw, shift_used = _shift_y(cam.location, d,
                                             cam_data.lens, c.get('resolution', (1920, 1080)))
            if 'shift_y' in ov:                 # REWORK_R1FIX F5：允许显式覆盖 shift
                shift_used = ov['shift_y']
            cam_data.shift_y = shift_used

        # 元数据存自定义属性，render.py / qa 读取
        cam['cam_id'] = cid
        cam['scheme'] = c.get('scheme', 'A')
        cam['cam_type'] = c['type']
        cam['description'] = c.get('description', '')
        cam['hide_ceilings'] = bool(c.get('hide_ceilings', False))
        if c.get('variant'):
            cam['variant'] = c['variant']
        if abs(shift_raw) > SHIFT_LIMIT:
            cam['shift_clamped'] = True
        made.append(cam)

    # REWORK_R1FIX2 F3：木色校准机位（不在 cameras.json）——正对客厅西墙 W19
    # 父母房木门扇面（门洞 y -8.6..-7.75，门扇面 x=3.361），距门面 1.2m、lens 50，
    # 画面覆盖 0.864x0.486m，门板占画面 ~89%（复核单要求 >=70%）。
    # 渲染：render.py --cams CAL --preset preview --samples 256 --wood A|B|C
    cd = bpy.data.cameras.new('cd_CAL_wood_door')
    cam = bpy.data.objects.new('cam_CAL_wood_door', cd)
    coll.objects.link(cam)
    cam.location = (4.561, -8.175, 1.05)
    cam.rotation_euler = (math.radians(90), 0.0, math.radians(90.0))
    cd.sensor_fit = 'HORIZONTAL'
    cd.sensor_width = 36.0
    cd.lens = 50.0
    cd.clip_start = 0.02
    cd.clip_end = 300.0
    cam['cam_id'] = 'CAL_wood_door'
    cam['scheme'] = 'A'
    cam['cam_type'] = 'PERSP'
    cam['description'] = 'F3 wood calibration: W19 parents door face at 1.2m lens50'
    cam['exposure'] = 1.80   # 校准定版后记录 render_log
    made.append(cam)

    # R2FIX M1：柜门特写机位 ×3（门缝/细边框/拉手近观；距离按"全宽入画"微调记录）
    cab_specs = [
        # (名, 相机位, look_at, lens, 方案, 曝光) —— 主卧衣柜前皮 x≈9.85 全宽 2.85
        ('CAB_master_wardrobe', (12.15, -7.675, 1.30), (9.85, -7.675, 1.30), 28, 'A', 1.75),
        # B 整墙柜前皮 x≈8.75，中段（上下柜全高）
        ('CAB_B_wall', (6.55, -7.75, 1.30), (9.20, -7.75, 1.30), 24, 'B', 1.80),
        # 玄关端景柜前皮 y≈-6.20，全宽 1.45（含上下段与中段开放格）
        ('CAB_foyer', (2.675, -4.90, 1.70), (2.675, -6.20, 1.70), 24, 'A', 2.10),
        # R2FIX2 N1：西墙实木组合柜特写（工单：正对柜中心、距 2.0m、高 1.3m、lens 28；
        # shift_y -0.15 让底部矮台 3 抽屉入画——否则竖向画面 z0.58..2.02 装不下 z0.45
        # 的矮台，柜顶 0.4m 相应出画，如实记录）
        ('CAB_west_bookcase', (5.82, -9.575, 1.30), (3.82, -9.575, 1.30), 28, 'A', 1.80),
    ]
    cab_shift = {'CAB_west_bookcase': -0.15}
    for nm, loc, look, lens, sch, exp in cab_specs:
        cd = bpy.data.cameras.new('cd_' + nm)
        cd.sensor_fit = 'HORIZONTAL'
        cd.sensor_width = 36.0
        cd.lens = lens
        cd.clip_start = 0.02
        cd.clip_end = 300.0
        cam = bpy.data.objects.new('cam_' + nm, cd)
        coll.objects.link(cam)
        cam.location = loc
        yaw = math.atan2(-(look[0] - loc[0]), look[1] - loc[1])
        cam.rotation_euler = (math.radians(90), 0.0, yaw)   # 水平，竖线竖直
        if nm in cab_shift:
            cd.shift_y = cab_shift[nm]   # R2FIX2 N1：竖向构图微调（记录在案）
        cam['cam_id'] = nm
        cam['scheme'] = sch
        cam['cam_type'] = 'PERSP'
        cam['description'] = 'R2FIX M1 cabinet close-up'
        cam['exposure'] = exp
        made.append(cam)
    return made

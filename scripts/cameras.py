# -*- coding: utf-8 -*-
# cameras.py —— 读 cameras.json 建 23 个机位。
# 规则（cameras.json meta）：透视机位两点透视（水平，shift_y 调构图）；
# 鸟瞰允许俯视（Track To）；PANO 用 EQUIRECT（Blender 4.0+ 在 camera.data）。
import math
import bpy

import config
import util

SHIFT_LIMIT = 0.15


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
        cam_data = bpy.data.cameras.new('cd_%s' % cid)
        cam = bpy.data.objects.new('cam_%s' % cid, cam_data)
        coll.objects.link(cam)
        cam.location = c['location']
        cam_data.sensor_fit = 'HORIZONTAL'
        cam_data.sensor_width = c.get('sensor_width_mm', 36)
        cam_data.clip_start = 0.02
        cam_data.clip_end = 300.0

        is_pano = c['type'] == 'PANO_EQUIRECT'
        is_aerial = 'aerial' in cid
        if is_pano:
            cam_data.type = 'PANO'
            cam_data.panorama_type = 'EQUIRECTANGULAR'  # 4.0+ 位置在 camera.data
            yaw = math.atan2(-(c['look_at'][0] - cam.location[0]),
                              c['look_at'][1] - cam.location[1])
            cam.rotation_euler = (math.radians(90), 0.0, yaw)
            shift_raw = shift_used = 0.0
        elif is_aerial:
            aim = bpy.data.objects.new('aim_%s' % cid, None)
            aim.location = c['look_at']
            aim.empty_display_size = 0.5
            coll.objects.link(aim)
            con = cam.constraints.new('TRACK_TO')
            con.target = aim
            con.track_axis = 'TRACK_NEGATIVE_Z'
            con.up_axis = 'UP_Y'
            cam_data.lens = c.get('lens_mm', 32)
            shift_raw = shift_used = 0.0
        else:
            cam_data.lens = c.get('lens_mm', 18)
            d = c['look_at']
            yaw = math.atan2(-(d[0] - cam.location[0]), d[1] - cam.location[1])
            cam.rotation_euler = (math.radians(90), 0.0, yaw)
            shift_raw, shift_used = _shift_y(cam.location, d,
                                             cam_data.lens, c.get('resolution', (1920, 1080)))
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
    return made

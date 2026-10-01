# -*- coding: utf-8 -*-
# render.py —— 后台渲染入口（M1 最小版：--white 白模 Workbench 出图）
# 用法：
#   blender -b blend\jiangyu.blend --python scripts\render.py -- --white --cams 01,03,12,11 [--scheme A]
# 机位给编号前缀（01 -> cam_01_aerial_A）。输出 review/screenshots/。
import os
import sys
import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
import util


def parse_args():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    opts = {'white': '--white' in argv, 'cams': [], 'scheme': 'A'}
    if '--cams' in argv:
        opts['cams'] = [c.strip() for c in argv[argv.index('--cams') + 1].split(',') if c.strip()]
    if '--scheme' in argv:
        opts['scheme'] = argv[argv.index('--scheme') + 1].upper()
    return opts


def setup_workbench(scene):
    scene.render.engine = 'BLENDER_WORKBENCH'
    s = scene.display.shading
    s.light = 'STUDIO'
    s.color_type = 'MATERIAL'
    s.show_object_outline = True
    s.object_outline_color = (0.05, 0.05, 0.05)
    for attr, val in (('show_cavity', True), ('cavity_type', 'BOTH'),
                      ('cavity_ridge_factor', 0.6), ('cavity_valley_factor', 0.9),
                      ('show_shadows', True), ('shadow_strength', 0.5),
                      ('background_type', 'VIEWPORT'),
                      ('background_color', (0.85, 0.87, 0.90))):
        try:
            setattr(s, attr, val)
        except Exception:
            pass
    try:
        scene.display.render_aa = '5'
    except Exception:
        pass
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    # 白模阶段用 Standard 视图变换（AgX 会压灰，M4 再切）
    try:
        scene.view_settings.view_transform = 'Standard'
    except Exception:
        pass


def find_cam(prefix):
    """机位匹配：相机名 cam_<id>_...，要求 id 首段（下划线前）与 prefix 完全相等。"""
    for o in bpy.data.objects:
        if o.type != 'CAMERA' or not o.name.startswith('cam_'):
            continue
        if o.name[4:].split('_')[0] == prefix:
            return o
    return None


def main():
    opts = parse_args()
    if not opts['white'] or not opts['cams']:
        print('[render] nothing to do (need --white --cams ...)')
        return
    scene = bpy.context.scene
    os.makedirs(config.SCREENSHOT_DIR, exist_ok=True)
    setup_workbench(scene)
    util.set_scheme_visibility(scene, opts['scheme'])

    ceil_coll = bpy.data.collections.get(config.COL_CEILINGS)
    for prefix in opts['cams']:
        cam = find_cam(prefix)
        if cam is None:
            print('[render][warn] camera not found: %s' % prefix)
            continue
        scene.camera = cam
        if ceil_coll is not None:
            ceil_coll.hide_render = bool(cam.get('hide_ceilings', False))
        cid = cam.get('cam_id', prefix)
        out = os.path.join(config.SCREENSHOT_DIR, 'M1_%s.png' % cid)
        scene.render.filepath = out
        bpy.ops.render.render(write_still=True)
        print('[render] saved %s' % out)
    if ceil_coll is not None:
        ceil_coll.hide_render = False


main()

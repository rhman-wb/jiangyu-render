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
    opts = {'white': '--white' in argv, 'cams': [], 'scheme': 'A',
            'preset': None, 'variant': None}
    if '--cams' in argv:
        opts['cams'] = [c.strip() for c in argv[argv.index('--cams') + 1].split(',') if c.strip()]
    if '--scheme' in argv:
        opts['scheme'] = argv[argv.index('--scheme') + 1].upper()
    if '--preset' in argv:
        opts['preset'] = argv[argv.index('--preset') + 1]
    if '--variant' in argv:
        opts['variant'] = argv[argv.index('--variant') + 1]
    return opts


def enable_gpu():
    try:
        prefs = bpy.context.preferences.addons['cycles'].preferences
        prefs.compute_device_type = 'ONEAPI'
        try:
            prefs.get_devices()
        except Exception:
            pass
        ok = False
        for d in prefs.devices:
            if d.type == 'ONEAPI':
                d.use = True
                ok = True
            else:
                d.use = False
        if ok:
            bpy.context.scene.cycles.device = 'GPU'
            return 'GPU'
    except Exception:
        pass
    bpy.context.scene.cycles.device = 'CPU'
    return 'CPU'


def setup_cycles(scene, preset, variant):
    import materials as M
    p = config.PRESETS[preset]
    scene.render.engine = 'CYCLES'
    dev = enable_gpu()
    cy = scene.cycles
    cy.samples = p['samples']
    cy.adaptive_threshold = p['threshold']
    cy.use_denoising = True
    try:
        cy.denoiser = 'OPENIMAGEDENOISE'
    except TypeError:
        pass
    lp = config.LIGHT_PATHS
    cy.max_bounces = lp['max_bounces']
    cy.diffuse_bounces = lp['diffuse']
    cy.glossy_bounces = lp['glossy']
    cy.transmission_bounces = lp['transmission']
    cy.transparent_max_bounces = lp['transparent']
    cy.clamp_indirect = lp['clamp_indirect']
    cy.use_persistent_data = True
    cy.seed = config.RENDER_SEED
    try:
        scene.view_settings.view_transform = 'AgX'
        scene.view_settings.look = 'Medium High Contrast'
    except Exception:
        pass
    if variant == 'kitchen_lower_olive':
        m_olive = bpy.data.materials.get('kitchen_lower_olive')
        if m_olive is None:
            m_olive = M.base_mat('kitchen_lower_olive', '6E7A52', 0.5)
        for o in bpy.data.objects:
            if o.type == 'MESH' and o.material_slots:
                if o.material_slots[0].material and o.material_slots[0].material.name == 'kitchen_front':
                    o.material_slots[0].material = m_olive
    return dev


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
    if not opts['cams']:
        print('[render] nothing to do (need --cams ...)')
        return
    scene = bpy.context.scene
    if opts['white']:
        os.makedirs(config.SCREENSHOT_DIR, exist_ok=True)
        setup_workbench(scene)
        outdir = config.SCREENSHOT_DIR
        prefix_out = 'M1_'
    else:
        preset = opts['preset'] or 'preview'
        dev = setup_cycles(scene, preset, opts['variant'])
        print('[render] preset=%s device=%s' % (preset, dev))
        outdir = os.path.join(config.RENDER_DIR,
                              'final' if preset == 'final' else
                              ('pano' if preset == 'pano_final' else 'preview'))
        prefix_out = ''
    os.makedirs(outdir, exist_ok=True)
    util.set_scheme_visibility(scene, opts['scheme'])

    ceil_coll = bpy.data.collections.get(config.COL_CEILINGS)
    for cam_prefix in opts['cams']:
        cam = find_cam(cam_prefix)
        if cam is None:
            print('[render][warn] camera not found: %s' % cam_prefix)
            continue
        scene.camera = cam
        if not opts['white']:
            p = config.PRESETS[opts['preset'] or 'preview']
            if cam.get('cam_type', '') == 'PANO_EQUIRECT':
                res = p.get('pano_res') or (2048, 1024)
            else:
                res = p['res']
            scene.render.resolution_x, scene.render.resolution_y = res
            scene.view_settings.exposure = cam.get('exposure', 0.0)
        if ceil_coll is not None:
            ceil_coll.hide_render = bool(cam.get('hide_ceilings', False))
        cid = cam.get('cam_id', cam_prefix)
        out = os.path.join(outdir, '%s%s.png' % (prefix_out, cid))
        scene.render.filepath = out
        bpy.ops.render.render(write_still=True)
        print('[render] saved %s' % out)
    if ceil_coll is not None:
        ceil_coll.hide_render = False
    scene.view_settings.exposure = 0.0


main()

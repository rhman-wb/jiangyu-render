# -*- coding: utf-8 -*-
# render.py —— 后台渲染入口
# 用法：
#   blender -b blend\jiangyu.blend --python scripts\render.py -- --cams 01,03 [--scheme A]
#       [--preset preview|final|pano_final] [--variant kitchen_lower_olive|son_blue]
#       [--wood A|B|C] [--out NAME] [--white]
# 机位给编号前缀（01 -> cam_01_aerial_A；16b -> cam_16b_son_room_blue）。
# REWORK #7：pano_final 必须 4096x2048，渲染后读回尺寸断言。
# REWORK #25：--wood 在线切换木色预设（对比图 C1_wood_*）。
# REWORK #28：cameras.json 里带 variant 的机位（10 橄榄绿 / 16b 雾霾蓝）自动套用变体。
import os
import sys
import time
import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
import util

# 变体 = (基准材质, 变体材质)；按对象 variant_group 属性批量切换全部 slots 的材质。
# REWORK_R1FIX F1/F2：旧版按 slot0 材质名精确匹配，而变体材质 0-user 不随 blend
# 保存导致 get()=None 直接 0 objs（日志有 variant material missing 为证）。
# 新版：材质 use_fake_user 保活（materials.py）+ variant_group 属性精确圈定对象。
VARIANT_PAIRS = {
    'kitchen_lower_olive': ('kitchen_front', 'kitchen_lower_olive'),
    'son_blue': ('kids_son_green', 'kids_son_blue'),
}


def _base_name(m):
    """材质基础名：去掉 .001 这类数字后缀。"""
    n = m.name
    i = n.rfind('.')
    return n[:i] if i > 0 and n[i + 1:].isdigit() else n


def parse_args():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    opts = {'white': '--white' in argv, 'cams': [], 'scheme': 'A',
            'preset': None, 'variant': None, 'wood': None, 'out': None,
            'samples': None}
    if '--cams' in argv:
        opts['cams'] = [c.strip() for c in argv[argv.index('--cams') + 1].split(',') if c.strip()]
    if '--scheme' in argv:
        opts['scheme'] = argv[argv.index('--scheme') + 1].upper()
    if '--preset' in argv:
        opts['preset'] = argv[argv.index('--preset') + 1]
    if '--variant' in argv:
        opts['variant'] = argv[argv.index('--variant') + 1]
    if '--wood' in argv:
        opts['wood'] = argv[argv.index('--wood') + 1].upper()
    if '--out' in argv:
        opts['out'] = argv[argv.index('--out') + 1]
    if '--samples' in argv:   # REWORK_R1FIX2 F3：CAL=256 / C1=128（降噪抹木纹的补救）
        opts['samples'] = int(argv[argv.index('--samples') + 1])
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


def set_variant(name, active):
    """变体材质互换（active=True 套用 / False 还原）。REWORK_R1FIX F1/F2。
    按 obj['variant_group'] 圈定对象，遍历全部 slots，按材质基础名匹配替换。
    替换数为 0 时 raise（不许静默渲出未变体的图）。"""
    if name not in VARIANT_PAIRS:
        return 0
    base, var = VARIANT_PAIRS[name]
    src, dst = (var, base) if not active else (base, var)
    m_dst = bpy.data.materials.get(dst)
    if m_dst is None:
        have = sorted({m.name for m in bpy.data.materials})[:20]
        raise RuntimeError('[render] variant material missing: %s (blend has %s...)'
                           % (dst, have))
    n = 0
    for o in bpy.data.objects:
        if o.type != 'MESH' or o.get('variant_group') != name:
            continue
        for slot in o.material_slots:
            if slot.material and _base_name(slot.material) == src:
                slot.material = m_dst
                n += 1
                break   # 每对象换一次即可（同一基准材质只挂一个 slot）
    return n


def setup_cycles(scene, preset):
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
    if preset in ('final', 'pano_final'):
        # 成品档：OIDN Albedo+Normal 输入通道（CLAUDE.md 第 9 章）
        try:
            cy.denoising_input_passes = 'RGB_ALBEDO_NORMAL'
            cy.denoising_prefilter = 'ACCURATE'
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
    except Exception:
        pass
    util.set_agx_look(scene)   # REWORK 2.5（枚举拼写兼容）
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
    try:
        scene.view_settings.view_transform = 'Standard'
    except Exception:
        pass


def find_cam(prefix):
    """机位匹配：相机名 cam_<id>；前缀与 id 首段相等，或与完整 id 相等
    （R2FIX M1：多词特写机位 id 如 CAB_master_wardrobe）。"""
    for o in bpy.data.objects:
        if o.type != 'CAMERA' or not o.name.startswith('cam_'):
            continue
        tail = o.name[4:]
        if tail == prefix or tail.split('_')[0] == prefix:
            return o
    return None


def assert_output_size(path, res):
    """REWORK #7：渲染后读回图片尺寸并断言。"""
    img = bpy.data.images.load(path, check_existing=False)
    w, h = img.size[0], img.size[1]
    bpy.data.images.remove(img)
    if (w, h) != tuple(res):
        raise RuntimeError('[render] SIZE ASSERT FAIL %s: %dx%d != %dx%d' %
                           (path, w, h, res[0], res[1]))
    print('[render] size OK %dx%d %s' % (w, h, os.path.basename(path)))


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
        dev = setup_cycles(scene, preset)
        if opts['samples']:
            scene.cycles.samples = opts['samples']
        print('[render] preset=%s device=%s look=%s%s' %
              (preset, dev, config.AGX_LOOK,
               (' samples=%d' % opts['samples']) if opts['samples'] else ''))
        outdir = os.path.join(config.RENDER_DIR,
                              'final' if preset == 'final' else
                              ('pano' if preset == 'pano_final' else 'preview'))
        prefix_out = ''
    # REWORK_R1FIX 第 1 节：8bit RGB（无 alpha）输出
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.image_settings.color_depth = '8'
    os.makedirs(outdir, exist_ok=True)
    util.set_scheme_visibility(scene, opts['scheme'])

    # REWORK #25：木色在线切换（C1_wood_B / C1_wood_C 对比图）
    if opts['wood']:
        import materials as M
        M.apply_wood_preset(opts['wood'])

    ceil_coll = bpy.data.collections.get(config.COL_CEILINGS)
    for cam_prefix in opts['cams']:
        cam = find_cam(cam_prefix)
        if cam is None:
            print('[render][warn] camera not found: %s' % cam_prefix)
            continue
        # REWORK #9 保险：--scheme 与机位 scheme 不一致时告警（不渲染错误组合）
        cam_scheme = cam.get('scheme', 'A')
        if cam_scheme != opts['scheme']:
            print('[render][warn] scheme mismatch: cam %s is scheme %s but --scheme %s' %
                  (cam_prefix, cam_scheme, opts['scheme']))
        scene.camera = cam
        res = None
        if not opts['white']:
            p = config.PRESETS[opts['preset'] or 'preview']
            if cam.get('cam_type', '') == 'PANO_EQUIRECT':
                res = p.get('pano_res') or p['res']   # REWORK #7：pano_final 回退 p['res']
            else:
                res = p['res']
            scene.render.resolution_x, scene.render.resolution_y = res
            scene.view_settings.exposure = cam.get('exposure', 0.0)
        if ceil_coll is not None:
            ceil_coll.hide_render = bool(cam.get('hide_ceilings', False))
        # R2FIX m4：鸟瞰机位切换浅色纯底（隐草地显 base），非鸟瞰恢复
        aerial_base = bpy.data.objects.get('out_aerial_base')
        ground = bpy.data.objects.get('out_ground')
        if aerial_base is not None and ground is not None:
            aerial = bool(cam.get('hide_ceilings', False))
            aerial_base.hide_render = not aerial
            ground.hide_render = aerial
        cid = cam.get('cam_id', cam_prefix)
        # 变体：CLI 显式优先，否则用机位自带（10 橄榄绿 / 16b 雾霾蓝）
        variant = opts['variant'] or cam.get('variant')
        nv = 0
        if variant:
            # REWORK_R1FIX F1/F2：关 Persistent Data 防材质缓存；0 objs 直接 raise
            scene.cycles.use_persistent_data = False
            nv = set_variant(variant, True)
            if nv == 0:
                raise RuntimeError('[render] variant %s matched 0 objects on cam %s'
                                   % (variant, cam_prefix))
        base = opts['out'] if opts['out'] else ('%s%s' % (prefix_out, cid))
        out = os.path.join(outdir, '%s.png' % base)
        scene.render.filepath = out
        t0 = time.perf_counter()
        bpy.ops.render.render(write_still=True)
        print('[render] saved %s (%.1fs, exp=%.2f%s)' %
              (out, time.perf_counter() - t0, cam.get('exposure', 0.0),
               (' variant=%s(%d objs)' % (variant, nv)) if variant else ''))
        if variant:
            set_variant(variant, False)
            scene.cycles.use_persistent_data = True
        if res is not None:
            assert_output_size(out, res)
    if ceil_coll is not None:
        ceil_coll.hide_render = False
    aerial_base = bpy.data.objects.get('out_aerial_base')
    ground = bpy.data.objects.get('out_ground')
    if aerial_base is not None:
        aerial_base.hide_render = True
    if ground is not None:
        ground.hide_render = False
    scene.view_settings.exposure = 0.0


main()

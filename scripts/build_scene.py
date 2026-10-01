# -*- coding: utf-8 -*-
# build_scene.py —— 入口：清场 -> 材质/集合 -> 硬装 -> 相机 -> 保存 .blend
# 用法（无头）：blender -b --python scripts\build_scene.py
import os
import sys
import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
import util
import architecture
import cameras
import materials
import lighting

builtins_mod = util.load_module('builtins')  # 与 Python 内置 builtins 同名，走文件加载
furniture_mod = util.load_module('furniture')


def make_white_materials():
    """M1 白模材质（M4 换 materials.py 正式材质表）。"""
    def base(name, hexcol, rough, alpha=1.0):
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        bsdf = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
        lin = util.srgb_to_linear(hexcol)
        i = bsdf.inputs.get('Base Color')
        if i is not None:
            i.default_value = (*lin, 1.0)
        i = bsdf.inputs.get('Roughness')
        if i is not None:
            i.default_value = rough
        m.diffuse_color = (*lin, alpha)  # Workbench MATERIAL 颜色走这里
        if alpha < 1.0 and hasattr(m, 'blend_method'):
            try:
                m.blend_method = 'BLEND'
            except Exception:
                pass
        return m

    return {
        'white': base('white_clay', 'D9D9D9', 0.85),
        'glass': base('white_glass', 'C9D4DA', 0.10, alpha=0.30),
        'dark': base('slot_dark', '3A3A3A', 0.6),
        # M2 白模辅助色（M4 换正式材质表）
        'wood': base('clay_wood', 'B4A99C', 0.85),      # 木作示意
        'mirror': base('clay_mirror', 'AEBEC8', 0.15),  # 镜面示意
        'kfront': base('clay_kfront', 'A79E92', 0.7),   # 厨房下柜门板（独立实例，橄榄绿变体挂载点）
    }


def enable_render_device():
    """按 config.RENDER_DEVICE 设置 Cycles 设备；oneAPI 不可用回退 CPU。"""
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    if config.RENDER_DEVICE != 'GPU':
        scene.cycles.device = 'CPU'
        return 'CPU'
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
            scene.cycles.device = 'GPU'
            return 'GPU'
    except Exception:
        pass
    scene.cycles.device = 'CPU'
    return 'CPU'


def main():
    util.clear_scene()
    scene = bpy.context.scene

    # 单位与色彩（AgX 在 M4 启用；白模阶段用 Standard）
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 1.0
    device = enable_render_device()

    mats = make_white_materials()
    colls = util.link_all_collections()

    warns = architecture.build_all(mats, colls)
    builtins_mod.build_all(mats, colls)
    furniture_mod.build_all(mats, colls)
    furniture_mod.build_extras(mats, colls)
    cameras.build_all(colls['cameras'])

    # M4：正式材质 + 灯光 + AgX（规格 6/8 章）
    mats4 = materials.build_all_materials()
    materials.apply_all(mats4, colls)
    lighting.build_all(mats4, colls)
    try:
        scene.view_settings.view_transform = 'AgX'
        scene.view_settings.look = 'Medium High Contrast'
    except Exception:
        pass

    # MCP Poly Haven 开关是场景级属性（decisions_log D-004）
    try:
        scene.blendermcp_use_polyhaven = True
    except Exception:
        pass

    os.makedirs(os.path.dirname(config.BLEND_FILE), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=config.BLEND_FILE, compress=True)

    n_obj = len(bpy.data.objects)
    faces = sum(len(o.data.polygons) for o in bpy.data.objects if o.type == 'MESH')
    print('[build] device=%s objects=%d faces=%d cameras=%d' %
          (device, n_obj, faces, len(bpy.data.cameras)))
    print('[build] saved %s' % config.BLEND_FILE)
    for wmsg in warns:
        print('[build][warn] %s' % wmsg)


main()

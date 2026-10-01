# -*- coding: utf-8 -*-
# M0 环境测速：同一测试场景，Cycles CPU vs oneAPI GPU（960x540 / 64spp / OIDN）
# 用法（无头命令行，不走 MCP）：
#   "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" -b --python scripts\m0_bench.py
# 结果写入 review/m0_bench.json；控制台输出只用 ASCII。
import bpy
import time
import json
import os
import math
import gc

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REVIEW_DIR = os.path.join(ROOT, "review")
os.makedirs(REVIEW_DIR, exist_ok=True)

# ---------------------------------------------------------------- helpers
def hex_to_linear(h):
    c = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    return tuple(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in c)


def make_mat(name, base_hex, rough=0.5, metallic=0.0, transmission=0.0,
             emission_hex=None, emission_strength=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    bc = bsdf.inputs.get('Base Color')
    if bc is not None:
        bc.default_value = (*hex_to_linear(base_hex), 1.0)
    for key, val in (('Roughness', rough), ('Metallic', metallic),
                     ('Transmission Weight', transmission)):
        i = bsdf.inputs.get(key)
        if i is not None:
            i.default_value = val
    if emission_hex is not None:
        ec = bsdf.inputs.get('Emission Color')
        es = bsdf.inputs.get('Emission Strength')
        if ec is not None:
            ec.default_value = (*hex_to_linear(emission_hex), 1.0)
        if es is not None:
            es.default_value = emission_strength
    return m


def add_box(name, dims, center, mat, bevel_m=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=center)
    o = bpy.context.active_object
    o.name = name
    o.scale = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel_m:
        bv = o.modifiers.new('Bevel', 'BEVEL')
        bv.width = bevel_m
        bv.segments = 2
    o.data.materials.append(mat)
    return o


def clear_scene():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.data.orphans_purge(do_recursive=True)


# ---------------------------------------------------------------- test scene
def build_test_scene():
    clear_scene()

    m_wall = make_mat('bench_wall', 'D9D6CF', rough=0.9)
    m_floor = make_mat('bench_floor', 'BFAE92', rough=0.4)
    m_wood = make_mat('bench_wood', '6B4A33', rough=0.45)
    m_frame = make_mat('bench_frame', '4B4D50', rough=0.4, metallic=0.6)
    m_glass = make_mat('bench_glass', 'FFFFFF', rough=0.05, transmission=1.0)
    m_rug = make_mat('bench_rug', 'CDBEA4', rough=0.95)
    m_emit = make_mat('bench_led', 'FFFFFF',
                      emission_hex='FFB27A', emission_strength=3.0)  # ~3000K

    t = 0.14  # wall thickness
    H = 2.85
    RX, RY = 4.2, 3.2  # interior

    # floor / ceiling
    add_box('bench_floor', (RX + 2 * t, RY + 2 * t, 0.10), (RX / 2, RY / 2, -0.05), m_floor)
    add_box('bench_ceiling', (RX + 2 * t, RY + 2 * t, 0.10), (RX / 2, RY / 2, H + 0.05), m_wall)

    # north wall (y=RY side, solid)
    add_box('bench_wall_n', (RX + 2 * t, t, H), (RX / 2, RY + t / 2, H / 2), m_wall)
    # east wall (solid)
    add_box('bench_wall_e', (t, RY, H), (RX + t / 2, RY / 2, H / 2), m_wall)

    # south wall (y=0) with window x[1.2,3.0] sill 0.9 head 2.4
    add_box('bench_wall_s_l', (1.2 + t, t, H), ((-t + 1.2) / 2, -t / 2, H / 2), m_wall)
    add_box('bench_wall_s_r', (RX - 3.0 + t, t, H), ((3.0 + RX + t) / 2, -t / 2, H / 2), m_wall)
    add_box('bench_wall_s_b', (1.8, t, 0.9), (2.1, -t / 2, 0.45), m_wall)
    add_box('bench_wall_s_t', (1.8, t, H - 2.4), (2.1, -t / 2, (2.4 + H) / 2), m_wall)

    # west wall (x=0) with door y[1.0,1.9] head 2.1
    add_box('bench_wall_w_a', (t, 1.0, H), (-t / 2, 0.5, H / 2), m_wall)
    add_box('bench_wall_w_b', (t, RY - 1.9, H), (-t / 2, (1.9 + RY) / 2, H / 2), m_wall)
    add_box('bench_wall_w_lintel', (t, 0.9, H - 2.1), (-t / 2, 1.45, (2.1 + H) / 2), m_wall)

    # window frame + glass + sill board
    fw, fd = 0.06, 0.10
    cx, sill, head = 2.1, 0.9, 2.4
    add_box('bench_wf_bottom', (1.8, fd, fw), (cx, -t / 2, sill + fw / 2), m_frame)
    add_box('bench_wf_top', (1.8, fd, fw), (cx, -t / 2, head - fw / 2), m_frame)
    add_box('bench_wf_l', (fw, fd, head - sill), (cx - 0.9 + fw / 2, -t / 2, (sill + head) / 2), m_frame)
    add_box('bench_wf_r', (fw, fd, head - sill), (cx + 0.9 - fw / 2, -t / 2, (sill + head) / 2), m_frame)
    add_box('bench_glass', (1.8 - 2 * fw, 0.006, head - sill - 2 * fw), (cx, -t / 2, (sill + head) / 2), m_glass)
    add_box('bench_sill', (1.8 + 0.08, 0.16, 0.03), (cx, 0.0, sill - 0.015), m_frame)

    # door leaf open 30 deg into room (hinge at y=1.0)
    leaf = add_box('bench_door', (0.045, 0.9, 2.05), (0.03, 1.45, 1.025), m_wood, bevel_m=0.008)
    bpy.context.scene.cursor.location = (0.03, 1.0, 1.025)
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    leaf.rotation_euler.z = math.radians(30)

    # furniture proxies
    add_box('bench_table_top', (1.2, 0.7, 0.04), (2.6, 1.9, 0.74), m_wood, bevel_m=0.008)
    for i, (lx, ly) in enumerate(((2.06, 1.62), (3.14, 1.62), (2.06, 2.18), (3.14, 2.18))):
        add_box(f'bench_table_leg{i}', (0.05, 0.05, 0.72), (lx, ly, 0.36), m_wood)
    add_box('bench_chair_seat', (0.42, 0.42, 0.05), (2.0, 1.15, 0.46), m_wood, bevel_m=0.015)
    add_box('bench_chair_back', (0.42, 0.05, 0.50), (2.0, 0.96, 0.72), m_wood, bevel_m=0.015)
    add_box('bench_rug', (2.0, 1.4, 0.012), (2.6, 1.8, 0.006), m_rug)
    add_box('bench_led_strip', (1.5, 0.08, 0.02), (2.1, 0.35, H - 0.03), m_emit)

    # camera
    cam_data = bpy.data.cameras.new('bench_cam')
    cam = bpy.data.objects.new('bench_cam', cam_data)
    bpy.context.collection.objects.link(cam)
    cam.location = (2.1, 2.9, 1.45)
    cam.rotation_euler = (math.radians(90), 0, math.pi)
    cam_data.lens = 24
    bpy.context.scene.camera = cam

    # sun through the window (from -Y, 40 deg elevation)
    sun_data = bpy.data.lights.new('bench_sun', 'SUN')
    sun_data.energy = 3.5
    sun_data.angle = math.radians(2.5)
    sun = bpy.data.objects.new('bench_sun', sun_data)
    bpy.context.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(40), 0, 0)

    # world: plain color, strength 1.0 (no HDRI -> reproducible)
    world = bpy.data.worlds.get('bench_world') or bpy.data.worlds.new('bench_world')
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == 'BACKGROUND')
    bg.inputs['Color'].default_value = (0.45, 0.52, 0.62, 1.0)
    bg.inputs['Strength'].default_value = 1.0


def apply_render_settings(scene):
    scene.render.engine = 'CYCLES'
    scene.render.resolution_x = 960
    scene.render.resolution_y = 540
    scene.render.resolution_percentage = 100
    cy = scene.cycles
    cy.samples = 64
    cy.adaptive_threshold = 0.1
    cy.use_denoising = True
    try:
        cy.denoiser = 'OPENIMAGEDENOISE'
    except TypeError:
        pass
    cy.max_bounces = 8
    cy.diffuse_bounces = 4
    cy.glossy_bounces = 4
    cy.transmission_bounces = 8
    cy.transparent_max_bounces = 8
    cy.clamp_indirect = 8.0
    if hasattr(cy, 'use_light_tree'):
        cy.use_light_tree = True
    cy.use_persistent_data = True
    cy.seed = 42


def enable_oneapi():
    prefs = bpy.context.preferences.addons['cycles'].preferences
    try:
        prefs.compute_device_type = 'ONEAPI'
    except TypeError:
        return []
    try:
        prefs.get_devices()  # 4.5 返回 None，只起刷新作用，真源在 prefs.devices
    except Exception:
        pass
    enabled = []
    for d in prefs.devices:
        want = (d.type == 'ONEAPI')
        try:
            d.use = want
        except Exception:
            pass
        if want and d.use:
            enabled.append(d.name)
    return enabled


def timed_render(scene):
    t0 = time.perf_counter()
    bpy.ops.render.render(write_still=False)
    dt = time.perf_counter() - t0
    gc.collect()
    return dt


def main():
    scene = bpy.context.scene
    build_test_scene()
    apply_render_settings(scene)

    result = {
        'blender': bpy.app.version_string,
        'resolution': '960x540',
        'samples': 64,
        'denoiser': 'OIDN',
        'cpu_threads': bpy.context.scene.render.threads,
    }

    # 1) CPU
    scene.cycles.device = 'CPU'
    result['cpu_s'] = timed_render(scene)
    print('[bench] CPU done: %.2f s' % result['cpu_s'])

    # 2) GPU cold + warm
    gpu_names = enable_oneapi()
    result['gpu_devices'] = gpu_names
    if gpu_names:
        scene.cycles.device = 'GPU'
        result['gpu_cold_s'] = timed_render(scene)
        print('[bench] GPU cold done: %.2f s' % result['gpu_cold_s'])
        result['gpu_warm_s'] = timed_render(scene)
        print('[bench] GPU warm done: %.2f s' % result['gpu_warm_s'])
        result['speedup_warm'] = round(result['cpu_s'] / result['gpu_warm_s'], 2)
        chosen = 'GPU' if result['gpu_warm_s'] < result['cpu_s'] else 'CPU'
    else:
        result['gpu_cold_s'] = None
        result['gpu_warm_s'] = None
        result['speedup_warm'] = None
        chosen = 'CPU'
    result['chosen_device'] = chosen

    out = os.path.join(REVIEW_DIR, 'm0_bench.json')
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print('[bench] chosen device:', chosen)
    print('[bench] results written to', out)


main()

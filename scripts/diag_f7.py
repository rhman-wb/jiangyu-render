# -*- coding: utf-8 -*-
# diag_f7.py —— REWORK_FINAL1 F7：主卧床头墙斜光带诊断（两轮未修，禁删太阳/调暗掩盖）
# 用法（无头）：
#   blender -b blend\jiangyu.blend --python scripts\diag_f7.py -- --render          # 基线 vs 藏太阳 各渲一张 16smp
#   blender -b blend\jiangyu.blend --python scripts\diag_f7.py -- --render --hide lt_pendant_01   # 藏指定灯（逐灯二分用）
#   blender -b blend\jiangyu.blend --python scripts\diag_f7.py -- --probe           # 床头墙网格 ray_cast 反查漏光缝
# 输出：review/screenshots/f7_diag_base.png / f7_diag_nosun.png + 差异带定位 + 逐点光路表
import os
import sys
import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
import util

CAM = '12'
OUTDIR = os.path.join(config.REVIEW_DIR, 'screenshots')
RAMP = ' .:-=+*#%@'


def _find_cam(prefix):
    for o in bpy.data.objects:
        if o.type == 'CAMERA' and o.name.startswith('cam_'):
            tail = o.name[4:]
            if tail == prefix or tail.split('_')[0] == prefix:
                return o
    return None


def _setup(scene):
    scene.render.engine = 'CYCLES'
    try:
        prefs = bpy.context.preferences.addons['cycles'].preferences
        prefs.compute_device_type = 'ONEAPI'
        try:
            prefs.get_devices()
        except Exception:
            pass
        for d in prefs.devices:
            d.use = (d.type == 'ONEAPI')
        scene.cycles.device = 'GPU'
    except Exception:
        scene.cycles.device = 'CPU'
    cy = scene.cycles
    cy.samples = 16
    cy.adaptive_threshold = 0.15
    cy.use_denoising = True
    try:
        cy.denoiser = 'OPENIMAGEDENOISE'
    except TypeError:
        pass
    cy.max_bounces = 8
    cy.use_persistent_data = False
    cy.seed = config.RENDER_SEED
    scene.view_settings.view_transform = 'AgX'
    util.set_agx_look(scene)
    scene.render.resolution_x, scene.render.resolution_y = (960, 540)
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.image_settings.color_depth = '8'


def _pixels(path):
    img = bpy.data.images.load(path, check_existing=False)
    w, h = img.size
    px = list(img.pixels)
    bpy.data.images.remove(img)
    return w, h, px


def _ascii(w, h, px, tag):
    print('[f7] luminance grid %s (%dx%d):' % (tag, w, h))
    for gy in range(27):
        row = ''
        for gx in range(48):
            x0, x1 = int(gx * w / 48), int((gx + 1) * w / 48)
            y0, y1 = int(gy * h / 27), int((gy + 1) * h / 27)
            s = n = 0
            for yy in range(y0, max(y0 + 1, y1)):
                for xx in range(x0, max(x0 + 1, x1)):
                    i = 4 * (yy * w + xx)
                    s += 0.2126 * px[i] + 0.7152 * px[i + 1] + 0.0722 * px[i + 2]
                    n += 1
            v = s / max(1, n)
            row += RAMP[min(9, int(v * 10))]
        print('   ' + row)


def _stats(w, h, px, tag):
    for name, (u0, u1, v0, v1) in (('right-third', (0.66, 1.0, 0.0, 1.0)),
                                   ('right-upper', (0.66, 1.0, 0.05, 0.45))):
        s = r = b = n = 0
        for yy in range(int(v0 * h), int(v1 * h)):
            for xx in range(int(u0 * w), int(u1 * w)):
                i = 4 * (yy * w + xx)
                s += 0.2126 * px[i] + 0.7152 * px[i + 1] + 0.0722 * px[i + 2]
                r += px[i]
                b += px[i + 2]
                n += 1
        print('[f7] %s %-12s mean=%.3f  R-B=%.3f' %
              (tag, name, s / n, (r - b) / n))


def do_render(hide_names):
    scene = bpy.context.scene
    cam = _find_cam(CAM)
    if cam is None:
        raise RuntimeError('[f7] camera %s not found' % CAM)
    _setup(scene)
    util.set_scheme_visibility(scene, 'A')
    scene.camera = cam
    scene.view_settings.exposure = cam.get('exposure', 0.0)
    os.makedirs(OUTDIR, exist_ok=True)

    targets = []
    for nm in hide_names:
        if nm.endswith('*'):
            targets += [o for o in bpy.data.objects if o.name.startswith(nm[:-1])]
        else:
            o = bpy.data.objects.get(nm)
            if o is not None:
                targets.append(o)
    if not targets:
        raise RuntimeError('[f7] nothing to hide matched: %s' % hide_names)

    out_base = os.path.join(OUTDIR, 'f7_diag_base.png')
    out_hid = os.path.join(OUTDIR, 'f7_diag_%s.png' % targets[0].name)
    scene.render.filepath = out_base
    bpy.ops.render.render(write_still=True)
    print('[f7] base rendered (everything visible)')
    prev = [(o, o.hide_render) for o in targets]
    for o in targets:
        o.hide_render = True
    scene.render.filepath = out_hid
    bpy.ops.render.render(write_still=True)
    print('[f7] hidden-render done: %s' % [o.name for o in targets])
    for o, was in prev:
        o.hide_render = was

    wb, hb, pb = _pixels(out_base)
    wh, hh, ph = _pixels(out_hid)
    _ascii(wb, hb, pb, 'base')
    _ascii(wh, hh, ph, 'hidden=%s' % targets[0].name)
    _stats(wb, hb, pb, 'base')
    _stats(wh, hh, ph, 'hidden')
    # 差异带：|hidden - base| 逐像素，找 >0.10 的簇的 bbox 与每行轮廓
    m = 0
    bx0, bx1, by0, by1 = wb, -1, hb, -1
    rows = []
    for yy in range(hb):
        cnt = 0
        for xx in range(wb):
            i = 4 * (yy * wb + xx)
            d = (abs(ph[i] - pb[i]) + abs(ph[i + 1] - pb[i + 1]) +
                 abs(ph[i + 2] - pb[i + 2])) / 3
            if d > 0.10:
                cnt += 1
                m += 1
                bx0, bx1 = min(bx0, xx), max(bx1, xx)
                by0, by1 = min(by0, yy), max(by1, yy)
        rows.append(cnt)
    print('[f7] diff>0.10 pixels=%d (%.1f%%)  bbox x[%d..%d] y[%d..%d] (y 从顶部)' %
          (m, 100.0 * m / (wb * hb), bx0, bx1, by0, by1))
    step = max(1, hb // 27)
    print('[f7] diff row profile (每 %d 行的像素数):' % step)
    print('   ' + ' '.join(str(sum(rows[i:i + step])) for i in range(0, hb, step)))


def _classify(name, role):
    if role in ('win_glass',) or name.startswith('win_') or 'glass' in name:
        return 'glass'
    if any(k in name for k in ('curtain', 'sheer', 'blind', 'sh_glass')):
        return 'sheer'
    return 'opaque'


def do_probe():
    scene = bpy.context.scene
    dg = bpy.context.evaluated_depsgraph_get()
    sun = bpy.data.objects.get('lt_sun')
    if sun is None:
        raise RuntimeError('[f7] lt_sun not found')
    d = Vector((0.0, 0.0, -1.0))
    d.rotate(sun.rotation_euler)          # 光行进方向
    back = -d.copy()
    print('[f7] sun travel dir = (%.3f, %.3f, %.3f)  probe dir = (%.3f, %.3f, %.3f)'
          % (d.x, d.y, d.z, back.x, back.y, back.z))
    PX = 12.60
    y0, y1, ys = -9.9, -6.6, 0.15
    z0, z1, zs = 0.90, 2.60, 0.10
    print('[f7] probe plane x=%.2f  y %.2f..%.2f step %.2f  z %.2f..%.2f step %.2f'
          % (PX, y0, y1, ys, z0, z1, zs))
    hdr = ['OPEN(直射!)', 'GLASS(穿玻璃)', 'SHEER(穿纱帘)', 'OPAQUE(被挡)']
    counts = {}
    band = {}
    nz = int(round((z1 - z0) / zs)) + 1
    rows = []
    for iz in range(nz - 1, -1, -1):
        z = z0 + iz * zs
        cells = ''
        for iy in range(int(round((y1 - y0) / ys)) + 1):
            y = y0 + iy * ys
            p = Vector((PX, y, z))
            org = p.copy()
            hits = []
            for _ in range(12):
                ok, loc, nrm, idx, obj, mtrx = scene.ray_cast(dg, org, back)
                if not ok:
                    break
                nm = obj.name if obj else '?'
                role = obj.get('role', '') if obj else ''
                hits.append((nm, role, _classify(nm, role),
                             (loc - p).length))
                org = loc + back * 0.002
            if not hits:
                k = 'OPEN'
            else:
                kinds = [h[2] for h in hits]
                if 'opaque' in kinds:
                    k = 'OPAQUE'
                elif 'sheer' in kinds:
                    k = 'SHEER'
                else:
                    k = 'GLASS'
            counts[k] = counts.get(k, 0) + 1
            if k in ('OPEN', 'GLASS', 'SHEER'):
                band.setdefault(k, []).append((round(y, 2), round(z, 2), hits))
            cells += {'OPEN': '!', 'GLASS': '+', 'SHEER': '~',
                      'OPAQUE': '.'}[k]
        rows.append('z=%.2f %s' % (z, cells))
    print('[f7] map: x=12.60 平面，列=y(西->东即 %.2f..%.2f)，!=直射 +=穿玻璃 ~=穿纱帘 .=被挡' % (y0, y1))
    for r in rows:
        print('   ' + r)
    print('[f7] counts: %s' % counts)
    for k in ('OPEN', 'GLASS', 'SHEER'):
        pts = band.get(k, [])
        if not pts:
            continue
        ys_ = [p[0] for p in pts]
        zs_ = [p[1] for p in pts]
        print('[f7] %s 区: y %.2f..%.2f  z %.2f..%.2f  (%d 点)  光路样例:' %
              (k, min(ys_), max(ys_), min(zs_), max(zs_), len(pts)))
        for p in pts[:6]:
            chain = ' -> '.join('%s[%s]@%.2fm' % (h[0], h[2], h[3]) for h in p[2][:5])
            print('     y=%.2f z=%.2f : %s' % (p[0], p[1], chain))


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    if '--probe' in argv:
        do_probe()
    elif '--render' in argv:
        i = argv.index('--hide') if '--hide' in argv else -1
        hide = [t for t in argv[i + 1].split(',') if t] if i >= 0 else ['lt_sun']
        do_render(hide)
    else:
        print('[f7] need --render or --probe')


main()

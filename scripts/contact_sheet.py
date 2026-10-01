# -*- coding: utf-8 -*-
# contact_sheet.py —— 拼总览图：23 张预览 + 标题 + 中文说明（MSYH 字体）
# 用法：blender -b --python scripts\contact_sheet.py [-- --final]
import os
import sys
import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
import util

FONT_PATH = r'C:\Windows\Fonts\msyh.ttc'
TILE_W, TILE_H, LABEL_H = 480, 270, 44
COLS, MARG, GAP, TITLE_H = 4, 28, 22, 108

ORDER = ['01', '02', '03', '06', '04', '07', '05', '08',
         '09', '10', '11', 'P1', '12', '13', 'P3', '14',
         '15', '16', '17', '18', '19', '20', 'P2']
KIDS_NOTE = {'15': '（家具仅示意，以实际选购为准）', '16': '（家具仅示意，以实际选购为准）'}


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    final_mode = '--final' in argv
    src_dir = config.RENDER_DIR if final_mode else os.path.join(config.RENDER_DIR, 'preview')
    out_name = 'contact_sheet.png' if final_mode else 'contact_sheet_preview.png'

    cams = {c['id']: c for c in util.load_cameras()['cameras']}
    by_prefix = {}
    for cid in cams:
        by_prefix[cid.split('_')[0]] = cid

    # 清空默认场景
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)

    font = None
    if os.path.isfile(FONT_PATH):
        try:
            font = bpy.data.fonts.load(FONT_PATH)
        except Exception:
            font = None

    def txt(name, s, x, y, size):
        curve = bpy.data.curves.new(name, type='FONT')
        curve.body = s
        if font:
            curve.font = font
        curve.size = size
        curve.align_x = 'LEFT'
        curve.align_y = 'TOP'
        obj = bpy.data.objects.new(name, curve)
        obj.location = (x, y, 0)
        bpy.context.scene.collection.objects.link(obj)
        return obj

    def plane(name, img_path, x, y, w, h):
        img = bpy.data.images.load(img_path)
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        bsdf = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
        _in = bsdf.inputs.get('Base Color')
        tex = mat.node_tree.nodes.new('ShaderNodeTexImage')
        tex.image = img
        mat.node_tree.links.new(tex.outputs['Color'], _in)
        _set = bsdf.inputs.get('Emission Color')
        if _set is not None:
            e = mat.node_tree.nodes.new('ShaderNodeEmission')
            mat.node_tree.nodes.remove(bsdf)
            outn = next(n for n in mat.node_tree.nodes if n.type == 'OUTPUT_MATERIAL')
            mat.node_tree.links.new(tex.outputs['Color'], e.inputs['Color'])
            e.inputs['Strength'].default_value = 1.0
            mat.node_tree.links.new(e.outputs['Emission'], outn.inputs['Surface'])
        m = bpy.data.meshes.new(name)
        import bmesh
        bm = bmesh.new()
        bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5)
        verts = [(v.co.x * w, v.co.y * h, 0.0) for v in bm.verts]
        bm.free()
        m.from_pydata(verts, [], [(0, 1, 3, 2)])
        m.update()
        o = bpy.data.objects.new(name, m)
        o.location = (x + w / 2, y - h / 2, 0)
        o.data.materials.append(mat)
        bpy.context.scene.collection.objects.link(o)
        return o

    # 背景（纯色材质）
    rows = (len(ORDER) + COLS - 1) // COLS
    W = MARG * 2 + COLS * TILE_W + (COLS - 1) * GAP
    H = TITLE_H + rows * (TILE_H + LABEL_H + GAP) + MARG
    bgm = bpy.data.materials.new('sheet_bg_mat')
    bgm.use_nodes = True
    _bs = next(n for n in bgm.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    _bs.inputs['Base Color'].default_value = (0.09, 0.09, 0.10, 1.0)
    import bmesh as _bm2
    _m = bpy.data.meshes.new('sheet_bg')
    _b = _bm2.new()
    _bm2.ops.create_grid(_b, x_segments=1, y_segments=1, size=0.5)
    _verts = [(v.co.x * W, v.co.y * H, -0.01) for v in _b.verts]
    _b.free()
    _m.from_pydata(_verts, [], [(0, 1, 3, 2)])
    _m.update()
    bg = bpy.data.objects.new('sheet_bg', _m)
    bg.location = (W / 2, -H / 2, 0)
    bg.data.materials.append(bgm)
    bpy.context.scene.collection.objects.link(bg)

    title = ('江语云庭 143㎡ 效果图 · 轻中古' if final_mode
             else '江语云庭 143㎡ 效果图 · 轻中古（预览档 preview）')
    txt('sheet_title', title, MARG, -34, 44)
    txt('sheet_sub', '机位 23 张：20 透视 + 3 全景（720° 需查看原文件）', MARG, -84, 20)

    for i, pref in enumerate(ORDER):
        cid = by_prefix.get(pref)
        if not cid:
            continue
        path = os.path.join(src_dir, cid + '.png')
        if not os.path.isfile(path):
            continue
        r, c = divmod(i, COLS)
        x = MARG + c * (TILE_W + GAP)
        y = -(TITLE_H + r * (TILE_H + LABEL_H + GAP))
        plane('tile_%s' % pref, path, x, y, TILE_W, TILE_H)
        desc = cams[cid].get('description', '')
        label = '%s · %s' % (pref, desc.split('：', 1)[-1][:22])
        if pref in KIDS_NOTE:
            label += KIDS_NOTE[pref]
        txt('label_%s' % pref, label, x, y - TILE_H - 6, 22)

    cam_data = bpy.data.cameras.new('sheet_cam')
    cam_data.type = 'ORTHO'
    cam = bpy.data.objects.new('sheet_cam', cam_data)
    cam.location = (W / 2, -H / 2, 100)
    cam.rotation_euler = (0, 0, 0)
    bpy.context.scene.collection.objects.link(cam)
    cam_data.ortho_scale = W
    bpy.context.scene.camera = cam
    s = bpy.context.scene
    s.render.resolution_x = int(W)
    s.render.resolution_y = int(H)
    s.render.resolution_percentage = 100
    s.render.engine = 'CYCLES'
    s.cycles.samples = 16
    s.cycles.device = 'CPU'
    try:
        s.view_settings.view_transform = 'Standard'
    except Exception:
        pass
    out = os.path.join(src_dir, out_name)
    s.render.filepath = out
    bpy.ops.render.render(write_still=True)
    print('[sheet] saved %s' % out)


main()

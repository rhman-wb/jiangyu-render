# -*- coding: utf-8 -*-
# util.py —— 通用工具：JSON 加载、盒体创建、集合/材质管理、坐标换算
# 盒体一律用 bmesh 直接生成最终尺寸（对象 scale 保持 1，Bevel 修改器不受非均匀缩放影响）。
import bpy
import bmesh
import json
import math
import os
import importlib.util

import config


def load_module(mod_name):
    """按路径加载 scripts/ 下的模块（builtins.py 与 Python 内置 builtins 同名，无法直接 import）。"""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), mod_name + '.py')
    spec = importlib.util.spec_from_file_location('jy_' + mod_name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_layout():
    return load_json(config.LAYOUT_JSON)


def load_cameras():
    return load_json(config.CAMERAS_JSON)


def srgb_to_linear(hexstr):
    """'#RRGGBB' 或 'RRGGBB' -> (r,g,b) linear。规格 6.3 的转换公式。"""
    h = hexstr.lstrip('#')
    c = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    return tuple(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
                 for v in c)


# ---------------------------------------------------------------- 场景管理
def clear_scene():
    """彻底清空场景：删对象、清数据块（防 walnut.001 类残留）。"""
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for coll in list(bpy.data.collections):
        bpy.data.collections.remove(coll)
    bpy.data.orphans_purge(do_recursive=True)


def get_collection(name, parent=None):
    """按名取/建集合；给 parent 时建成子集合并返回。"""
    coll = bpy.data.collections.get(name)
    if coll is None:
        coll = bpy.data.collections.new(name)
        (parent if parent else bpy.context.scene.collection).children.link(coll)
    elif parent is not None and coll.name not in {c.name for c in parent.children}:
        parent.children.link(coll)
    return coll


def link_all_collections():
    """建规格 3.2 的集合树，返回 dict。"""
    common = get_collection(config.COL_COMMON)
    return {
        'common': common,
        'scheme_a': get_collection(config.COL_SCHEME_A),
        'scheme_b': get_collection(config.COL_SCHEME_B),
        'ceilings': get_collection(config.COL_CEILINGS, parent=common),
        'cameras': get_collection(config.COL_CAMERAS, parent=common),
    }


def set_scheme_visibility(scene, scheme):
    """渲染方案 A 时隐藏 SCHEME_B，反之亦然（hide_render + hide_viewport）。"""
    coll_a = bpy.data.collections.get(config.COL_SCHEME_A)
    coll_b = bpy.data.collections.get(config.COL_SCHEME_B)
    if coll_a:
        coll_a.hide_render = (scheme != 'A')
        coll_a.hide_viewport = (scheme != 'A')
    if coll_b:
        coll_b.hide_render = (scheme != 'B')
        coll_b.hide_viewport = (scheme != 'B')


# ---------------------------------------------------------------- 几何
def make_box(name, bmin, bmax, coll=None, mat=None, bevel=None, origin_at=None):
    """轴对齐盒体。bmin/bmax 为世界坐标 3 元组。
    origin_at: 指定对象原点的世界坐标（默认盒中心）；旋转门扇等用。
    bevel: 修改器宽度（米），不 apply。
    """
    # create_cube(size=1) 立方体范围为 ±0.5，所以缩放用全尺寸
    sx, sy, sz = (bmax[0] - bmin[0], bmax[1] - bmin[1], bmax[2] - bmin[2])
    if min(sx, sy, sz) <= 0:
        return None
    cx, cy, cz = ((bmin[0] + bmax[0]) / 2, (bmin[1] + bmax[1]) / 2, (bmin[2] + bmax[2]) / 2)
    if origin_at is None:
        origin_at = (cx, cy, cz)

    mesh = bpy.data.meshes.new(name + '_mesh')
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    tx, ty, tz = cx - origin_at[0], cy - origin_at[1], cz - origin_at[2]
    for v in bm.verts:
        v.co.x = v.co.x * sx + tx
        v.co.y = v.co.y * sy + ty
        v.co.z = v.co.z * sz + tz
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new(name, mesh)
    obj.location = origin_at
    if bevel:
        bv = obj.modifiers.new('Bevel', 'BEVEL')
        bv.width = bevel
        bv.segments = 2
    if mat is not None:
        obj.data.materials.append(mat)
    target = coll if coll is not None else bpy.context.scene.collection
    target.objects.link(obj)
    return obj


def obj_world_bbox(obj, depsgraph=None):
    """evaluated mesh 的世界包络盒（qa 用；Bevel 未 apply 不影响外轮廓）。"""
    dg = depsgraph or bpy.context.evaluated_depsgraph_get()
    ob = obj.evaluated_get(dg)
    coords = [ob.matrix_world @ v.co for v in ob.to_mesh().vertices]
    ob.to_mesh_clear()
    xs = [c.x for c in coords]
    ys = [c.y for c in coords]
    zs = [c.z for c in coords]
    return ((min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs)))

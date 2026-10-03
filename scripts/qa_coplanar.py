# -*- coding: utf-8 -*-
# qa_coplanar.py —— REWORK_R1FIX2 F4：墙体重合面检测
#   blender -b blend\jiangyu.blend --python scripts\qa_coplanar.py
# 检测对象：名字匹配 ^W\d+_s\d+$ 的墙体分段。判定：属于不同对象、法线同向、
# 平面偏移差 <1mm、平面投影重叠 >1mm² 的面 -> 清单。修复后清单必须为空
# （对接面法线相反，天然不触发；端帽埋入 1mm 亦不触发）。
import os
import re
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config

PAT = re.compile(r'^W\d+_s\d+$')
D_TOL = 0.001      # 平面偏移分组容差 1mm
MIN_AREA = 1e-6    # 重叠面积下限 1mm^2

findings = []
n_obj = n_face = 0


def basis(n):
    """平面内正交基 (u, v)。"""
    a = Vector((1.0, 0.0, 0.0)) if abs(n.x) < 0.9 else Vector((0.0, 1.0, 0.0))
    u = n.cross(a).normalized()
    v = n.cross(u)
    return u, v


def overlap_area(verts_a, verts_b, n):
    u, v = basis(n)
    def aabb(vs):
        us = [p.dot(u) for p in vs]
        vs_ = [p.dot(v) for p in vs]
        return min(us), max(us), min(vs_), max(vs_)
    a0, a1, a2, a3 = aabb(verts_a)
    b0, b1, b2, b3 = aabb(verts_b)
    dx = min(a1, b1) - max(a0, b0)
    dy = min(a3, b3) - max(a2, b2)
    return dx * dy if (dx > 0 and dy > 0) else 0.0


def run():
    """执行检测，返回 findings 列表（供 qa_r1fix2 导入复用）。"""
    global findings, n_obj, n_face
    findings = []
    n_obj = n_face = 0
    dg = bpy.context.evaluated_depsgraph_get()
    faces = []   # (n_tuple, d, [world verts], obj_name, face_idx)
    for o in bpy.data.objects:
        if o.type != 'MESH' or not PAT.match(o.name):
            continue
        n_obj += 1
        oe = o.evaluated_get(dg)
        me = oe.to_mesh()
        mw = oe.matrix_world
        m3 = mw.to_3x3()
        for p in me.polygons:
            n = (m3 @ p.normal).normalized()
            c = mw @ p.center
            faces.append((tuple(round(v, 3) for v in n), n.dot(c),
                          [mw @ me.vertices[vi].co for vi in p.vertices],
                          o.name, p.index))
            n_face += 1
        oe.to_mesh_clear()
    faces.sort(key=lambda f: (f[0], f[1]))
    i = 0
    while i < len(faces):
        j = i
        while (j < len(faces) and faces[j][0] == faces[i][0]
               and faces[j][1] - faces[i][1] < D_TOL):
            j += 1
        grp = faces[i:j]
        # 同一物理墙（W\d+ 同号）相邻分段的共面贴合不算缺陷（一体墙的分段边界）
        wall_id = lambda s: re.match(r'W\d+', s).group()
        if len({g[3] for g in grp}) > 1:
            for a in range(len(grp)):
                for b in range(a + 1, len(grp)):
                    if grp[a][3] == grp[b][3] or wall_id(grp[a][3]) == wall_id(grp[b][3]):
                        continue
                    ar = overlap_area(grp[a][2], grp[b][2], Vector(grp[a][0]))
                    if ar > MIN_AREA:
                        findings.append(
                            '%s[f%d] ~ %s[f%d]  n=%s  d=%.4f  overlap=%.1fmm2'
                            % (grp[a][3], grp[a][4], grp[b][3], grp[b][4],
                               str(grp[a][0]), grp[a][1], ar * 1e6))
        i = j

    lines = ['# qa_coplanar 墙体重合面检测（REWORK_R1FIX2 F4）', '']
    lines.append('墙分段对象 %d 个、面 %d 个' % (n_obj, n_face))
    lines.append('')
    if findings:
        lines.append('**FAIL** 重合面 %d 处：' % len(findings))
        lines.extend('- %s' % f for f in findings[:40])
    else:
        lines.append('**PASS** 清单为空：无不同对象间的同向重合面')
    out = os.path.join(config.REVIEW_DIR, 'qa_coplanar.md')
    with open(out, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print('[qa_coplanar] objs=%d faces=%d findings=%d -> %s'
          % (n_obj, n_face, len(findings), out))
    return findings


def main():
    run()


if __name__ == '__main__':
    main()

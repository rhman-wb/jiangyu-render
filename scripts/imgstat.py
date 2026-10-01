# -*- coding: utf-8 -*-
# imgstat.py —— 渲染图快速统计（辅助自检：防止空图/全黑/全白）
# 用法：blender -b --python scripts\imgstat.py -- <png1> <png2> ...
import os
import sys
import numpy as np
import bpy

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
for path in argv:
    if not os.path.isfile(path):
        print('[imgstat] missing %s' % path)
        continue
    img = bpy.data.images.load(path)
    arr = np.array(img.pixels[:]).reshape(-1, 4)
    lum = arr[:, 0] * 0.2126 + arr[:, 1] * 0.7152 + arr[:, 2] * 0.0722
    print('[imgstat] %-40s mean=%.3f std=%.3f bright>0.85=%.1f%% dark<0.08=%.1f%%' %
          (os.path.basename(path), lum.mean(), lum.std(),
           100.0 * (lum > 0.85).mean(), 100.0 * (lum < 0.08).mean()))

    # ASCII 亮度网格（暗->亮: ' .:-=+*#%@'），48x27，供无视觉环境下人工判读
    h, w = img.size[1], img.size[0]
    gw, gh = 48, 27
    grid = lum.reshape(h, w)
    rows = []
    for gy in range(gh):
        y0, y1 = gy * h // gh, (gy + 1) * h // gh
        if y1 <= y0:
            continue
        seg = ''
        for gx in range(gw):
            x0, x1 = gx * w // gw, (gx + 1) * w // gw
            v = grid[y0:y1, x0:x1].mean()
            seg += ' .:-=+*#%@'[min(9, int(v * 10))]
        rows.append('|' + seg + '|')
    print('\n'.join(rows))
    bpy.data.images.remove(img)

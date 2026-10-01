# -*- coding: utf-8 -*-
# config.py —— 全局配置：路径、设备、渲染档位、场景常量
# 设备结论依据 review/env_report.md（M0 测速）。
import os

# ---- 路径（全部 ASCII） ----
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, 'data')
BLEND_DIR = os.path.join(ROOT, 'blend')
RENDER_DIR = os.path.join(ROOT, 'renders')
REVIEW_DIR = os.path.join(ROOT, 'review')
SCREENSHOT_DIR = os.path.join(REVIEW_DIR, 'screenshots')
ASSET_DIR = os.path.join(ROOT, 'assets')

BLEND_FILE = os.path.join(BLEND_DIR, 'jiangyu.blend')
LAYOUT_JSON = os.path.join(DATA_DIR, 'layout.json')
CAMERAS_JSON = os.path.join(DATA_DIR, 'cameras.json')

# ---- 渲染设备（M0 测速结论：oneAPI Arc 核显显著快于 CPU；回退 CPU 的条件见 env_report） ----
RENDER_DEVICE = 'GPU'  # 'GPU' | 'CPU'

# ---- 集合命名 ----
COL_COMMON = 'COMMON'
COL_SCHEME_A = 'SCHEME_A'
COL_SCHEME_B = 'SCHEME_B'
COL_CEILINGS = 'CEILINGS'   # COMMON 的子集，便于鸟瞰机位整体隐藏
COL_CAMERAS = 'CAMERAS'     # COMMON 的子集

# ---- 场景常量（layout.json meta 的只读镜像，勿在此改尺寸） ----
WALL_T = 0.14        # 内墙/中心线厚度
WALL_T_EXT = 0.20    # 外墙加厚后（只向外侧加）
CEIL_H = 2.85        # 结构净高（顶板底面）
DOOR_HEAD = 2.10     # 室内门洞高

# A 组外墙（加厚到 0.20，只向外侧扩；内侧法向见 architecture.py 的 EXT_WALLS 表）
# ---- 渲染档位（CLAUDE.md 第 9 章） ----
PRESETS = {
    'preview':    dict(res=(960, 540),   pano_res=(2048, 1024), samples=64,  threshold=0.10),
    'final':      dict(res=(1920, 1080), pano_res=None,          samples=256, threshold=0.02),
    'pano_final': dict(res=(4096, 2048), pano_res=None,          samples=256, threshold=0.02),
}

# 光路（全档共用）
LIGHT_PATHS = dict(
    max_bounces=8, diffuse=4, glossy=4,
    transmission=8, transparent=8, clamp_indirect=8.0,
)

# 采样固定 seed（可复现）
RENDER_SEED = 42

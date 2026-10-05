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

# ---- REWORK R1 返工配置 ----

# 木色预设（REWORK 2.1）：A 胡桃默认 / B 浅胡桃 / C 橡木；材质切换用，不复制几何
WOOD_PRESET = 'A'   # 'A' | 'B' | 'C'

# 床头朝向（REWORK 4.3）：枕头/软包/盖毯按此布置
BED_HEAD_SIDE = {
    'master_bedroom': '+X',
    'parents_room':   '-X',
    'daughter_room':  '-X',
    'son_room':       '-X',
}

# 孩子房色板（REWORK 2.3）：儿子鼠尾草绿（对比雾霾蓝）、女儿燕麦米+雾粉、床品奶白
KIDS_PALETTE = {
    'son_main':    '9CAF94',   # 鼠尾草绿（主）
    'son_alt':     '8FA7B8',   # 雾霾蓝（16b 对比版）
    'daughter_main':   'D9C7AD',  # 燕麦米
    'daughter_accent': 'D8B4AE',  # 雾粉（点缀：床品/窗帘/地毯/抱枕/小物件）
    'bedding':     'F3EEE6',   # 奶白（床品底色）
}

# AgX Look（REWORK 2.5：不用 Medium High Contrast；4.5 枚举名带 "AgX - " 前缀，
# util.set_agx_look 会做拼写兼容）
AGX_LOOK = 'AgX - Base Contrast'

# 白墙采样框（REWORK 第 6 章 QA-5）：画面 fractional 坐标 (x0,y0,x1,y1)，y 从顶部起。
# 初值按各机位构图推定，首轮渲染后按实际画面校准。
WHITE_WALL_SAMPLES = {
    '01_aerial_A': [], '02_aerial_B': [], '20_terrace': [],   # 户外/鸟瞰无白墙
    # 框位经 R1 渲染后逐张视觉校准（初版按几何推测全落在了天花/门框/暖灯区）
    '03_living_A_from_foyer': [(0.30, 0.10, 0.45, 0.22)],
    '04_living_A_from_balcony': [(0.72, 0.10, 0.88, 0.22)],
    '05_living_A_tv_wall': [(0.05, 0.25, 0.15, 0.42), (0.88, 0.28, 0.98, 0.45)],
    '06_living_B_from_foyer': [(0.30, 0.10, 0.45, 0.22)],
    '07_living_B_from_balcony': [(0.72, 0.10, 0.88, 0.22)],
    '08_living_B_tv_wall': [(0.05, 0.08, 0.22, 0.20)],
    '09_kitchen_walnut': [(0.05, 0.05, 0.20, 0.15)],   # 奶白吊柜门板
    '10_kitchen_olive': [(0.05, 0.05, 0.20, 0.15)],
    '11_foyer': [(0.84, 0.20, 0.96, 0.30)],
    '12_master_bed_screen': [(0.30, 0.10, 0.44, 0.24)],   # FINAL1 D3 校准：原框落 3000K 壁灯光锥，移主照明受光区
    '13_master_wardrobe_vanity': [(0.05, 0.06, 0.30, 0.22), (0.42, 0.10, 0.56, 0.22)],
    '14_parents_room': [(0.05, 0.05, 0.28, 0.20)],
    '15_daughter_room': [(0.62, 0.08, 0.75, 0.20)],
    '16_son_room': [(0.20, 0.64, 0.32, 0.74)],
    '16b_son_room_blue': [(0.20, 0.64, 0.32, 0.74)],
    '17_public_bath_dry': [(0.05, 0.10, 0.20, 0.25)],
    '18_public_bath_wet': [(0.60, 0.10, 0.75, 0.22)],  # 暖米墙砖（无白墙，砖色即规格）
    '19_master_bath': [(0.60, 0.05, 0.75, 0.18)],      # 燕麦墙砖（同上）
    'P1_living_A_pano': [(0.40, 0.32, 0.52, 0.42)],
    'P2_living_B_pano': [(0.40, 0.32, 0.52, 0.42)],
    'P3_master_pano': [(0.44, 0.40, 0.56, 0.50)],
}

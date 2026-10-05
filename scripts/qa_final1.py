# -*- coding: utf-8 -*-
# qa_final1.py —— REWORK_FINAL1 数值验收（纯 python + PIL，免 Blender）
# 用法：python scripts\qa_final1.py [--after]   # 默认读 renders/preview；--after 不变
# 输出：review/qa_final1.md
# 口径：
#   - 白墙均值/R-B：config.WHITE_WALL_SAMPLES 逐机位采样框（记录项；200-225/R-B<=22 硬门槛属 D3）
#   - 窗区 >=250 像素占比：15/16（FINAL1 硬门槛 <=30%）+ 18/19 记录
#   - 遮挡条：18 左缘 / 19 右缘（本轮只报数，D11/D12 才设门槛）
#   - 胡桃采样：03/09 受光胡桃面均值（本轮留数，D1 验收用）
import os
import sys
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config

RENDER_DIR = config.RENDER_DIR
OUT = os.path.join(config.REVIEW_DIR, 'qa_final1.md')

# 窗区框（x0,y0,x1,y1，y 自顶部；首渲后校准一次并记录）
WIN_BOXES = {
    '15_daughter_room': (0.10, 0.05, 0.45, 0.30),
    '16_son_room': (0.55, 0.05, 0.88, 0.30),
    '18_public_bath_wet': (0.30, 0.05, 0.55, 0.30),
    '19_master_bath': (0.55, 0.05, 0.88, 0.35),
}
OCC_BOXES = {
    '18_public_bath_wet': ('left', (0.00, 0.05, 0.12, 0.95)),
    '19_master_bath': ('right', (0.88, 0.05, 1.00, 0.95)),
}
WALNUT_BOXES = {
    '03_living_A_from_foyer': (0.04, 0.55, 0.14, 0.75),
    '09_kitchen_walnut': (0.30, 0.55, 0.50, 0.75),
}
IMAGES = ['01_aerial_A', '02_aerial_B', '03_living_A_from_foyer',
          '04_living_A_from_balcony', '05_living_A_tv_wall', '06_living_B_from_foyer',
          '07_living_B_from_balcony', '08_living_B_tv_wall', '09_kitchen_walnut',
          '10_kitchen_olive', '11_foyer', '12_master_bed_screen',
          '13_master_wardrobe_vanity', '14_parents_room', '15_daughter_room',
          '16_son_room', '17_public_bath_dry', '18_public_bath_wet',
          '19_master_bath', '20_terrace']


def box_stats(img, box):
    w, h = img.size
    x0, y0, x1, y1 = box
    px = img.load()
    n = rs = gs = bs = w255 = 0
    for yy in range(int(y0 * h), int(y1 * h)):
        for xx in range(int(x0 * w), int(x1 * w)):
            r, g, b = px[xx, yy][:3]
            rs += r
            gs += g
            bs += b
            if r >= 250 and g >= 250 and b >= 250:
                w255 += 1
            n += 1
    return (rs / n, gs / n, bs / n, 100.0 * w255 / n)


def main():
    rows_white, rows_win, rows_occ, rows_wal = [], [], [], []
    fails = []
    for cid in IMAGES:
        path = os.path.join(RENDER_DIR, 'preview', cid + '.png')
        if not os.path.isfile(path):
            fails.append('%s: preview 缺文件' % cid)
            continue
        img = Image.open(path).convert('RGB')
        # 白墙采样（config.WHITE_WALL_SAMPLES；键为完整相机 id）
        for i, box in enumerate(config.WHITE_WALL_SAMPLES.get(cid, [])):
            r, g, b, w255 = box_stats(img, box)
            rows_white.append('| %s | 框%d | %.1f | %.1f | %.1f | %.1f | %+.1f |'
                              % (cid, i, r, g, b, (r + g + b) / 3, r - b))
        if cid in WIN_BOXES:
            r, g, b, w255 = box_stats(img, WIN_BOXES[cid])
            ok = w255 <= 30.0
            rows_win.append('| %s | %.1f,%.1f,%.1f,%.1f | %.1f%% | %s |'
                            % (cid, *WIN_BOXES[cid], w255, 'PASS' if ok else 'FAIL'))
            if not ok:
                fails.append('%s: 窗区近白 %.1f%% > 30%%' % (cid, w255))
        if cid in OCC_BOXES:
            side, box = OCC_BOXES[cid]
            r, g, b, w255 = box_stats(img, box)
            rows_occ.append('| %s | %s | 均值 %.1f | 近白 %.1f%% |'
                            % (cid, side, (r + g + b) / 3, w255))
        if cid in WALNUT_BOXES:
            r, g, b, _ = box_stats(img, WALNUT_BOXES[cid])
            rows_wal.append('| %s | #%02X%02X%02X | R-B %+.1f |'
                            % (cid, round(r), round(g), round(b), r - b))
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write('# qa_final1 数值验收（FINAL1 第 1 轮 preview）\n\n')
        f.write('生成：scripts/qa_final1.py ｜ 输入：renders/preview ｜ '
                '白墙采样框沿用 config.WHITE_WALL_SAMPLES\n\n')
        f.write('## 白墙受光区（记录项；D3 才设 200-225 / R-B<=22 硬门槛）\n\n')
        f.write('| 图 | 框 | R | G | B | 均值 | R-B |\n|---|---|---|---|---|---|---|\n')
        f.write('\n'.join(rows_white) + '\n\n')
        f.write('## 窗区近白占比（FINAL1 F12 门槛 <=30%）\n\n')
        f.write('| 图 | 框 | >=250 占比 | 判定 |\n|---|---|---|---|\n')
        f.write('\n'.join(rows_win) + '\n\n')
        f.write('## 遮挡条（18 左缘 / 19 右缘；只报数）\n\n')
        f.write('| 图 | 侧 | 均值 | 近白 |\n|---|---|---|---|\n')
        f.write('\n'.join(rows_occ) + '\n\n')
        f.write('## 胡桃采样（留数，D1 验收区间 #5A3E2C-#8A6648）\n\n')
        f.write('| 图 | 均值 | R-B |\n|---|---|---|\n')
        f.write('\n'.join(rows_wal) + '\n\n')
        f.write('## 结论\n\n')
        if fails:
            f.write('FAIL %d 项：\n' % len(fails))
            f.write('\n'.join('- ' + s for s in fails) + '\n')
        else:
            f.write('全部数值项 PASS（白墙为记录项）。\n')
    print('[qa_final1] -> %s  FAIL=%d' % (OUT, len(fails)))
    for s in fails:
        print('  ' + s)


main()

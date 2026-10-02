# -*- coding: utf-8 -*-
# contact_sheet.py —— 拼版工具（REWORK #8 后整体重写为 Pillow 独立脚本）
# 旧版用 Blender 贴图渲染拼版，from_pydata 丢 UV + 正交取景算错 → 纯色块/裁切。
# 新版：系统 Python 直接跑（无需 Blender）：
#   python scripts\contact_sheet.py                # preview 档总览 -> renders/preview/
#   python scripts\contact_sheet.py --mode final   # 成品档总览 -> renders/final/
#   python scripts\contact_sheet.py --compare      # C1 木色三联对比图
# 版式（REWORK #8）：每行 3 张、缩略图宽 600px、两行中文说明、msyh 字体、留足边距。
import os
import sys
import json

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config

FONT_PATH = r'C:\Windows\Fonts\msyh.ttc'
TILE_W = 600            # 缩略图宽（REWORK：>=600px）
TILE_H = 338            # 16:9
CAP_H = 62              # 两行说明
GAP = 24
MARGIN = 40
TITLE_H = 96
COLS = 3
BG = (244, 242, 238)
FG = (52, 48, 44)
ACCENT = (139, 90, 43)
KIDS_NOTE = '（家具仅示意，以实际选购为准）'


def font(size):
    return ImageFont.truetype(FONT_PATH, size)


def load_imgs_map(mode='preview'):
    """按档位扫 renders/ 下 png：文件名(去扩展) -> 路径。
    preview 档只扫 preview/（避免被 M6 同名 final 图覆盖）；final 档扫 final/+pano/。"""
    m = {}
    subs = ['preview'] if mode == 'preview' else ['final', 'pano']
    for sub in subs:
        d = os.path.join(config.RENDER_DIR, sub)
        if not os.path.isdir(d):
            continue
        for f in os.listdir(d):
            if f.endswith('.png'):
                m[os.path.splitext(f)[0]] = os.path.join(d, f)   # d 已含子目录名
    return m


def find_img(imgs, cid):
    return imgs.get(cid)   # id 唯一，同名优先即本身


def thumb(path, w=TILE_W, h=TILE_H):
    """读图 -> 8bit RGB -> 等比缩放居中（留白填充），根治 RGBA/16bit/纯色块问题。"""
    im = Image.open(path).convert('RGB')          # REWORK #8：统一转 8bit RGB
    im.thumbnail((w, h), Image.LANCZOS)
    canvas = Image.new('RGB', (w, h), (238, 236, 232))
    canvas.paste(im, ((w - im.width) // 2, (h - im.height) // 2))
    return canvas


def draw_caption(d, x, y, w, line1, line2, kids=False):
    d.text((x, y), line1, font=font(21), fill=FG)
    if kids:
        line2 = line2 + KIDS_NOTE
    d.text((x, y + 27), line2[:30], font=font(16), fill=(120, 112, 104))


def make_sheet(mode='preview'):
    cams = json.load(open(config.CAMERAS_JSON, encoding='utf-8'))['cameras']
    imgs = load_imgs_map(mode)
    tiles = []
    for c in cams:
        cid = c['id']
        path = find_img(imgs, cid)
        if path is None:
            print('[sheet][warn] missing %s' % cid)
            continue
        tiles.append((cid, path, c.get('description', ''), cid.startswith(('15', '16'))))
    rows = (len(tiles) + COLS - 1) // COLS
    W = MARGIN * 2 + COLS * TILE_W + (COLS - 1) * GAP
    H = TITLE_H + rows * (TILE_H + CAP_H + 18) + MARGIN
    sheet = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(sheet)
    title = ('江语云庭 143㎡ 效果图 · 轻中古 —— 预览总览（R1）' if mode == 'preview'
             else '江语云庭 143㎡ 效果图 · 轻中古')
    d.text((MARGIN, 26), title, font=font(34), fill=FG)
    d.text((MARGIN, 68), '返工 R1 轮 preview 档 · 木色 A（默认）· 孩子房家具仅示意见标注' if mode == 'preview'
           else '成品档 1920x1080 / 全景 4096x2048', font=font(17), fill=(120, 112, 104))
    for i, (cid, path, desc, kids) in enumerate(tiles):
        r, cix = divmod(i, COLS)
        x = MARGIN + cix * (TILE_W + GAP)
        y = TITLE_H + r * (TILE_H + CAP_H + 18)
        sheet.paste(thumb(path), (x, y))
        d.rectangle([x, y, x + TILE_W - 1, y + TILE_H - 1], outline=(210, 205, 198), width=1)
        num = cid.split('_')[0]
        name = cid[len(num) + 1:].replace('_', ' ')
        draw_caption(d, x, y + TILE_H + 6, TILE_W, '%s · %s' % (num, name), desc, kids)
    out = os.path.join(config.RENDER_DIR, mode, 'contact_sheet_%s.png' % mode)
    sheet.save(out, 'PNG')
    print('[sheet] %s (%dx%d, %d tiles)' % (out, W, H, len(tiles)))
    return out


def make_compare():
    """REWORK 第 7 章：C1 木色三联对比图。"""
    imgs = load_imgs_map('preview')
    trio = [('C1_wood_A', 'A 胡桃（默认 #5E4330）'),
            ('C1_wood_B', 'B 浅胡桃（#7A5C43）'),
            ('C1_wood_C', 'C 橡木（#B48E66）')]
    W = MARGIN * 2 + COLS * TILE_W + (COLS - 1) * GAP
    H = TITLE_H + TILE_H + CAP_H + MARGIN
    sheet = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(sheet)
    d.text((MARGIN, 26), '木色对比（同 04 机位，其他条件完全相同）', font=font(34), fill=FG)
    d.text((MARGIN, 68), '业主看图选定后全屋统一换成选定的一套', font=font(17), fill=(120, 112, 104))
    for i, (key, label) in enumerate(trio):
        path = imgs.get(key)
        if path is None:
            print('[sheet][warn] missing %s' % key)
            continue
        x = MARGIN + i * (TILE_W + GAP)
        y = TITLE_H
        sheet.paste(thumb(path), (x, y))
        d.rectangle([x, y, x + TILE_W - 1, y + TILE_H - 1], outline=(210, 205, 198), width=1)
        d.text((x, y + TILE_H + 8), label, font=font(21), fill=ACCENT)
    out = os.path.join(config.RENDER_DIR, 'preview', 'C1_wood_compare.png')
    sheet.save(out, 'PNG')
    print('[sheet] %s' % out)
    return out


if __name__ == '__main__':
    args = sys.argv[1:]
    if '--compare' in args:
        make_compare()
    else:
        mode = 'final' if '--mode' in args and 'final' in args else 'preview'
        make_sheet(mode)

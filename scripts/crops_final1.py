# -*- coding: utf-8 -*-
# crops_final1.py —— REWORK_FINAL1 证据图工具（纯 python + PIL，msyh 中文字体）
# 用法：
#   python scripts\crops_final1.py --crop     # F 项修前(final)/修后(preview)并排放大裁图
#   python scripts\crops_final1.py --plan R1  # R 项顶视示意图（R1..R7）
#   python scripts\crops_final1.py --plan all
#   python scripts\crops_final1.py --compare  # C1-C3 标签对比拼图
import json
import os
import sys
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config

ROOT = config.ROOT
CROPS = os.path.join(config.REVIEW_DIR, 'crops_final1')
COMPARE = os.path.join(config.REVIEW_DIR, 'compare_final1')
FONT_PATH = r'C:\Windows\Fonts\msyh.ttc'


def font(size):
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except Exception:
        try:
            return ImageFont.truetype(r'C:\Windows\Fonts\msyh.ttf', size)
        except Exception:
            return ImageFont.load_default()


def _load(kind, cid):
    sub = {'final': os.path.join(config.RENDER_DIR, 'final'),
           'pano': os.path.join(config.RENDER_DIR, 'pano'),
           'preview': os.path.join(config.RENDER_DIR, 'preview')}[kind]
    return Image.open(os.path.join(sub, cid + '.png')).convert('RGB')


def crop_pair(before_img, after_img, box, zoom, label_l, label_r, title):
    """box=(x0,y0,x1,y1) 分数坐标（y 自顶）。返回并排放大裁图。"""
    def cut(img):
        w, h = img.size
        return img.crop((int(box[0] * w), int(box[1] * h),
                         int(box[2] * w), int(box[3] * h)))
    lb, la = cut(before_img), cut(after_img)
    lb = lb.resize((lb.width * zoom, lb.height * zoom), Image.LANCZOS)
    la = la.resize((la.width * zoom, la.height * zoom), Image.LANCZOS)
    pad, cap = 8, 30
    out = Image.new('RGB', (lb.width + la.width + pad * 3,
                            max(lb.height, la.height) + cap + pad * 2), (24, 24, 24))
    d = ImageDraw.Draw(out)
    out.paste(lb, (pad, pad + cap))
    out.paste(la, (lb.width + pad * 2, pad + cap))
    d.text((pad, pad), '修前(final) ' + label_l, font=font(17), fill=(240, 240, 240))
    d.text((lb.width + pad * 2, pad), '修后(preview) ' + label_r, font=font(17),
           fill=(150, 220, 150))
    d.text((out.width - 8, out.height - 4), title, font=font(12), fill=(120, 120, 120),
           anchor='rb')
    return out


# ---- F 项裁图规格：(输出名, before_kind, before_id, after_id, box, zoom, 左标, 右标)
CROP_SPECS = [
    ('F1_03_floorlamp',      'final', '03_living_A_from_foyer',     '03_living_A_from_foyer',     (0.55, 0.30, 0.95, 0.90), 2, '落地灯弧臂-灯罩', '弧臂连续'),
    ('F1_06_floorlamp',      'final', '06_living_B_from_foyer',     '06_living_B_from_foyer',     (0.55, 0.30, 0.95, 0.90), 2, '落地灯弧臂-灯罩', '弧臂连续'),
    ('F2_09_kitchen_fronts', 'final', '09_kitchen_walnut',          '09_kitchen_walnut',          (0.05, 0.45, 0.75, 0.98), 2, '下柜整块竖纹', '门板/抽屉/拉手可数'),
    ('F3_09_dishwasher',     'final', '09_kitchen_walnut',          '09_kitchen_walnut',          (0.00, 0.55, 0.35, 1.00), 2, '大黑条拉手', '120mm 短拉手'),
    ('F4_13_dressing',       'final', '13_master_wardrobe_vanity',  '13_master_wardrobe_vanity',  (0.05, 0.45, 0.60, 1.00), 2, '台面下封死', '容膝空腔+薄抽屉'),
    ('F5_17_vanity',         'final', '17_public_bath_dry',         '17_public_bath_dry',         (0.15, 0.25, 0.90, 0.85), 2, '台面错乱灰槽', '整面台面双盆腔'),
    ('F6_19_blind',          'final', '19_master_bath',             '19_master_bath',             (0.50, 0.05, 1.00, 0.65), 2, '百叶占窗下 2/3', '叶片只在窗顶 1/3'),
    ('F7_12_lightband',      'final', '12_master_bed_screen',       '12_master_bed_screen',       (0.30, 0.00, 1.00, 0.60), 2, '床头斜光带', '连续均匀白墙'),
    ('F8_01_aerial_lights',  'final', '01_aerial_A',                '01_aerial_A',                (0.20, 0.35, 0.90, 0.80), 2, '悬空灯球/发光条', '顶装件全部隐藏'),
    ('F8_02_aerial_lights',  'final', '02_aerial_B',                '02_aerial_B',                (0.20, 0.35, 0.90, 0.80), 2, '悬空灯球/发光条', '顶装件全部隐藏'),
    ('F9_06_niche_props',    'final', '06_living_B_from_foyer',     '06_living_B_from_foyer',     (0.45, 0.05, 0.95, 0.75), 2, '摆件悬空', '摆件落层板'),
    ('F9_11_foyer_jar',      'final', '11_foyer',                   '11_foyer',                   (0.05, 0.15, 0.60, 0.80), 2, '陶罐悬空', '陶罐落层板'),
    ('F10_04_chair_back',    'final', '04_living_A_from_balcony',   '04_living_A_from_balcony',   (0.25, 0.35, 0.75, 0.95), 2, '端椅实心靠背', '薄靠背 <=4cm'),
    ('F11_04_door_reveal',   'final', '04_living_A_from_balcony',   '04_living_A_from_balcony',   (0.00, 0.10, 0.40, 0.90), 2, '门边亮白缝', '衬里同门套色'),
    ('F11_13_door_reveal',   'final', '13_master_wardrobe_vanity',  '13_master_wardrobe_vanity',  (0.55, 0.10, 1.00, 0.90), 2, '门边亮白缝', '衬里同门套色'),
    ('F12_15_window',        'final', '15_daughter_room',           '15_daughter_room',           (0.00, 0.00, 0.60, 0.50), 2, '窗内白块', '窗外树冠层次'),
    ('F12_16_window',        'final', '16_son_room',                '16_son_room',                (0.35, 0.00, 1.00, 0.50), 2, '窗内白块', '窗外树冠层次'),
    ('F12_18_window',        'final', '18_public_bath_wet',         '18_public_bath_wet',         (0.10, 0.00, 0.70, 0.50), 2, '窗内白矩形', '白矩形消失'),
    ('F12_19_window',        'final', '19_master_bath',             '19_master_bath',             (0.35, 0.00, 1.00, 0.55), 2, '窗上部死白', '天空层次'),
]


def do_crop():
    os.makedirs(CROPS, exist_ok=True)
    for name, bk, bid, aid, box, zoom, ll, lr in CROP_SPECS:
        before = _load('pano' if bid.startswith('P') else 'final', bid)
        after = _load('preview', aid)
        out = crop_pair(before, after, box, zoom, ll, lr, name)
        out.save(os.path.join(CROPS, name + '.jpg'), quality=92)
        print('[crops] %s.jpg' % name)


# ---- R 项顶视图
def _draw_plan(rid, floors, items, walls, annot):
    S = 90  # px per meter
    xs0 = 0.0
    xs1 = 14.0
    ys0 = -12.6
    ys1 = 0.0
    W, H = int((xs1 - xs0) * S) + 80, int((ys1 - ys0) * S) + 120
    img = Image.new('RGB', (W, H), (250, 250, 248))
    d = ImageDraw.Draw(img)

    def T(x, y):
        return (40 + (x - xs0) * S, 40 + (y - ys0) * S)

    for f in floors:
        (x0, y0), (x1, y1) = f['rect_min'], f['rect_max']
        d.rectangle([T(x0, y0), T(x1, y1)], fill=(240, 238, 232), outline=(180, 175, 165))
    for w in walls:
        if w['axis'] == 'x':
            d.line([T(w['start'], w['y']), T(w['end'], w['y'])], fill=(90, 90, 90), width=3)
        else:
            d.line([T(w['x'], w['start']), T(w['x'], w['end'])], fill=(90, 90, 90), width=3)
    for it in items:
        b = it['bbox']
        x0, y0 = T(b['min'][0], b['min'][1])
        x1, y1 = T(b['max'][0], b['max'][1])
        col = it.get('_col', (200, 120, 60))
        d.rectangle([x0, y0, x1, y1], outline=col, width=2,
                    fill=(col[0], col[1], col[2], 0) if False else None)
        d.text((x0 + 2, y0 + 2), it.get('_tag', it['id'].split('_')[-1]),
               font=font(13), fill=(60, 30, 10))
    y_txt = H - 70
    d.text((40, 8), annot.get('title', rid), font=font(20), fill=(30, 30, 30))
    for i, line in enumerate(annot.get('lines', [])):
        d.text((40, y_txt + i * 20), line, font=font(14), fill=(50, 50, 50))
    out = os.path.join(CROPS, '%s_plan.png' % rid)
    img.save(out)
    print('[crops] %s' % out)


def _layout():
    with open(config.LAYOUT_JSON, encoding='utf-8') as f:
        return json.load(f)


def _items(ld, pred, col=None, tags=None):
    out = []
    for it in ld['items']:
        if pred(it):
            it = dict(it)
            it['_col'] = col or (200, 120, 60)
            if tags and it['id'] in tags:
                it['_tag'] = tags[it['id']]
            out.append(it)
    return out


def do_plan(rid):
    os.makedirs(CROPS, exist_ok=True)
    ld = _layout()
    walls = ld['walls']
    floors = [f for f in ld['floors']
              if f['id'] in ('daughter_room', 'son_room', 'foyer', 'elevator_hall',
                             'living_dining_balcony', 'kitchen', 'parents_room',
                             'corridor', 'public_bath_dry', 'public_bath_wet',
                             'master_bedroom', 'master_bath')]
    if rid == 'R1':
        tags = {'common_daughter_room_bed_01': '女儿床',
                'common_daughter_room_wardrobe_01': '衣柜南', 'common_daughter_room_wardrobe_02': '衣柜西',
                'common_daughter_room_desk_01': '书桌', 'common_son_room_bed_01': '儿子床',
                'common_son_room_wardrobe_01': '衣柜', 'common_son_room_desk_01': '书桌',
                'common_son_room_shelf_01': '书架'}
        items = _items(ld, lambda it: 'daughter_room' in it['id'] or 'son_room' in it['id'],
                       (200, 120, 60), tags)
        annot = {'title': 'R1 孩子房床位（现状顶视，方案见报告）',
                 'lines': ['现状：女儿床南沿 y-1.80 距北窗墙 y-0.15 = 0.15m（内墙皮 -0.22 -> 0.07m 净距）',
                           '儿子床 y-1.75 -> 0.10m；工单目标床外缘离北窗 >=0.60m',
                           '虚线=北窗（W01 6.5-8.8 / W06 11.4-13.0，sill0.9）']}

        def win(it):
            return False
        items += [dict(id='win_%s' % w['id'], type='marker',
                       bbox={'min': [o['start'], -0.15, 0], 'max': [o['end'], -0.10, 0]},
                       group='common', room='x', _col=(70, 130, 200),
                       _tag='北窗')
                  for w in walls if w['id'] in ('W01', 'W06')
                  for o in w['openings'] if o['type'] == 'window']
    elif rid == 'R2':
        tags = {'common_foyer_mirror_door_01': '镜面门', 'common_foyer_cabinet_01': '端景下柜',
                'common_foyer_cabinet_02': '端景上柜', 'common_foyer_open_niche_01': '开放格',
                'common_foyer_stool_01': '换鞋凳', 'common_elevator_hall_cabinet_01': '电梯口柜'}
        items = _items(ld, lambda it: it.get('room') in ('foyer', 'elevator_hall'),
                       (200, 120, 60), tags)
        annot = {'title': 'R2 玄关 + 电梯口鞋柜（现状顶视，方案见报告）',
                 'lines': ['可用墙段与鞋柜方案尺寸见 layout_proposals_final1.md',
                           '镜面门(电箱)开启范围不得占用']}
    elif rid == 'R3':
        tags = {('A_living_dining_balcony_dining_chair_%02d' % i): '椅%d' % (i + 1) for i in range(5)}
        tags.update({'A_living_dining_balcony_island_01': '岛台',
                     'A_living_dining_balcony_island_02': '餐桌1.6m'})
        items = _items(ld, lambda it: it['id'].startswith('A_living_dining_balcony_island')
                       or it['id'].startswith('A_living_dining_balcony_dining_chair'),
                       (200, 120, 60), tags)
        annot = {'title': 'R3 A 方案 6 餐位（现状：南北各 2 + 东端 1，方案见报告）',
                 'lines': ['工单：删东端 chair_05，南北两侧各 3 把（间距均分 1.6/3），净距 >=0.75m']}
    elif rid == 'R4':
        tags = {'common_kitchen_cabinet_02': '西墙浅吊柜(改)', 'common_kitchen_cabinet_01': '东墙吊柜',
                'common_kitchen_dishwasher_01': '北台面', 'common_kitchen_kitchen_counter_01': '东台面',
                'common_kitchen_dishwasher_02': '洗碗机', 'common_kitchen_range_hood_01': '烟机',
                'common_kitchen_sink_01': '水槽', 'common_kitchen_hob_01': '灶',
                'common_kitchen_fridge_01': '冰箱'}
        items = _items(ld, lambda it: it.get('room') == 'kitchen', (200, 120, 60), tags)
        annot = {'title': 'R4 厨房西墙通高储物柜（现状顶视，方案见报告）',
                 'lines': ['cabinet_02 现为 z1.4-2.3 浅吊柜；方案改 0.35m 深通高柜 z0-2.3',
                           '过道净宽按 report 数值']}
    elif rid == 'R5':
        tags = {'common_parents_room_bed_01': '床1.8m', 'common_parents_room_nightstand_01': '床头柜(改壁挂)',
                'common_parents_room_bay_seat_01': '坐榻', 'common_parents_room_wardrobe_01': '衣柜',
                'common_parents_room_cushion_01': '软垫'}
        items = _items(ld, lambda it: it.get('room') == 'parents_room', (200, 120, 60), tags)
        annot = {'title': 'R5 父母房壁挂床头柜（现状顶视，方案见报告）',
                 'lines': ['工单：1.8m 床不变，床头柜改壁挂(离地>=0.45)',
                           '报告含：床南沿-坐榻 / 床北沿-衣柜净宽、壁灯/夜灯/地脚灯点位']}
    elif rid == 'R6':
        tags = {'A_living_dining_balcony_wall_finish_01': '东墙4.75m',
                'A_living_dining_balcony_tv_cabinet_01': '电视柜3m',
                'A_living_dining_balcony_tv_01': '电视85寸',
                'A_living_dining_balcony_sofa_01': '沙发'}
        items = _items(ld, lambda it: it['id'] in tags, (200, 120, 60), tags)
        annot = {'title': 'R6 A 方案电视墙（现状顶视，两方案尺寸见报告/C2 对比图）',
                 'lines': ['北段空白 y-7.1..-5.35 约 1.75m；电视/沙发对位不动',
                           '方案1=画框背景板+北端格栅（C2/C3）；方案2=整墙洗墙灯槽+软装']}
    elif rid == 'R7':
        tags = {'common_public_bath_wet_toilet_01': '马桶',
                'common_public_bath_wet_glass_partition_01': '淋浴隔断',
                'common_public_bath_wet_shower_floor_01': '淋浴区'}
        items = _items(ld, lambda it: it.get('room') == 'public_bath_wet', (200, 120, 60), tags)
        annot = {'title': 'R7 公卫安全设施（现状顶视，方案见报告）',
                 'lines': ['L 扶手(离地0.70)/折叠凳(座高0.45)/竖扶手/挡水+线性地漏 见报告']}
    else:
        raise SystemExit('unknown plan %s' % rid)
    _draw_plan(rid, floors, items, walls, annot)


# ---- C1-C3 拼图
def _grid(images, titles, cols, out_path, title):
    cell_w = max(im.width for im in images)
    cell_h = max(im.height for im in images) + 34
    rows = (len(images) + cols - 1) // cols
    pad = 10
    W = cols * cell_w + pad * (cols + 1)
    H = rows * cell_h + pad * 3 + 50
    out = Image.new('RGB', (W, H), (245, 244, 240))
    d = ImageDraw.Draw(out)
    d.text((pad, 8), title, font=font(26), fill=(40, 40, 40))
    for i, (im, t) in enumerate(zip(images, titles)):
        r, c = divmod(i, cols)
        x = pad + c * (cell_w + pad)
        y = 50 + pad + r * cell_h
        out.paste(im, (x, y))
        d.rectangle([x - 1, y - 1, x + im.width, y + im.height], outline=(180, 180, 180))
        d.text((x, y + im.height + 4), t, font=font(18), fill=(60, 60, 60))
    os.makedirs(COMPARE, exist_ok=True)
    out.save(out_path, quality=92)
    print('[crops] %s' % out_path)


def do_compare():
    pv = os.path.join(config.RENDER_DIR, 'preview')
    g = lambda n: Image.open(os.path.join(pv, n + '.png')).convert('RGB')
    _grid([g('C1_door_white_04'), g('C1_door_walnutframe_04'), g('C1_door_oat_04'),
           g('C1_door_white_13'), g('C1_door_walnutframe_13'), g('C1_door_oat_13')],
          ['云白平板门', '胡桃细框+云白芯', '燕麦平板门'] * 2, 3,
          os.path.join(COMPARE, 'C1_door_3opt.png'),
          'C1 卧室门色三选一（上：04 一帧三门 / 下：13 主卧门特写 ｜ 已套附录A 减胡桃环境）')
    _grid([g('C2_tv_opt1_05'), g('C2_tv_opt2_05'), g('C2_tv_opt1_04'), g('C2_tv_opt2_04')],
          ['方案1 画框背景+格栅', '方案2 整墙洗墙灯+软装'] * 2, 2,
          os.path.join(COMPARE, 'C2_tv_wall.png'),
          'C2 电视墙两方案（上：05 机位 / 下：04 机位）')
    _grid([g('C3_slat_walnut_05'), g('C3_slat_graphite_05')],
          ['格栅-胡桃', '格栅-深灰'], 2,
          os.path.join(COMPARE, 'C3_slats.png'),
          'C3 格栅颜色（05 机位，方案1 几何）')


def main():
    argv = sys.argv
    if '--crop' in argv:
        do_crop()
    if '--compare' in argv:
        do_compare()
    if '--plan' in argv:
        i = argv.index('--plan')
        what = argv[i + 1] if i + 1 < len(argv) else 'all'
        for rid in (['R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7'] if what == 'all' else [what]):
            do_plan(rid)


main()

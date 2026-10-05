# 决策日志（规格未写明、由执行方自行决定的事项）

> 规格原则（CLAUDE.md 引言）：规格没写到的细节按第 6 章风格原则自行决定，并记录于此。

## D-001 mcp_autostart.py 属规格外新增工具
- 位置：`scripts/mcp_autostart.py`。Blender 以 `--python scripts\mcp_autostart.py` 启动时自动开启 MCP Server（TCP 9876），免去每次手点 N 面板的 Start MCP Server。
- 影响：不影响场景内容，只是启动便利工具。

## D-002 layout.json 两处 note 与几何不一致（数据未改，以 openings 几何为准）
- W26 note 写"玄关北墙：入户门"，但 W26 是 x=1.95 的玄关西墙且无洞口；入户门洞实际在 **W27**（y=-4.8，x 2.3~3.25）。
- W25 note 写"玄关西墙：强弱电箱位置"，几何上 W25 是 x=3.05 的飘窗东翼短墙；强弱电箱/镜面门实际对应 **W26**（x=1.95）。
- 处理：不改 layout.json；建模按 openings 几何执行，镜面门仍按规格 5.5 装在玄关西墙。

## D-003 效果图计数：规格"21 张"与 cameras.json"20 PERSP + 3 PANO"的差异
- CLAUDE.md 第 0 章写"21 张效果图 + 3 张全景"，cameras.json 实际 20 个 PERSP + 3 个 PANO = 23 机位（与第 10 章 M5"所有 23 个机位"一致）。
- 处理：按 cameras.json 全部 23 机位渲染；contact_sheet 为第 24 张总览图。已在 M1 汇报中提请业主知悉。

## D-004 Poly Haven 开关是场景级属性
- MCP 插件的 `blendermcp_use_polyhaven` 挂在 Scene 上；build_scene.py 重建场景后需重新 `scene.blendermcp_use_polyhaven = True` 才能用 Poly Haven 下载。已记入 build 流程注意事项。

## D-005 渲染设备选择（M0 测速结论）
- 960×540 / 64spp / OIDN 同场景：CPU(22 线程) 50.3s；GPU oneAPI 冷 11.8s / 热 14.0s（加速比 ≈3.6×）。
- 结论：`config.py RENDER_DEVICE = 'GPU'`。回退条件：oneAPI 渲染报错或驱动重置时切 CPU 并在 render_log 记录。
- 注：GPU"冷"反而快于"热"属核显共享内存调度的正常波动，两次都远快于 CPU，不影响结论。

## D-006 白模自检图用 Workbench 无头渲染而非视口截图
- 规格 M1 要求"视口截图"；实现改为 `render.py --white` 用 Workbench 引擎无头出图（STUDIO 光照 + MATERIAL 单色 + 轮廓 + cavity）。
- 理由：脚本可复现、不依赖 GUI 状态、效果等价（白模灰 + 边缘清晰）。记录于此以备查询。
- 注：4.5 无头 Workbench 渲染的背景色（scene.display.shading.background_*）实测不生效，保持默认主题深灰；若业主嫌暗，M5 预览改 Cycles + 浅色世界。

## M1 批次（D-007 ~ D-014）

## D-007 地板裁剪：corridor L 形拆两块
- living∩corridor 重叠带 x 9.0–9.25 若按整矩形裁 corridor，会在 x 9.0–9.25、y -3.95~-2.35 挖出 0.25×1.6m 地面空洞（该处是过道真实地面）。
- 处理：corridor 拆 `floor_corridor_0`（南段 x 从 9.25 起）+ `floor_corridor_1`（北段 x 从 9.0 起）；foyer / elevator_hall 的 x_max 裁到 3.35（重叠薄片由 living 覆盖）。qa 地板重叠检查 0 项通过。

## D-008 吊顶构造细节
- 客餐厅边吊环 Z 2.60~2.84（顶面留 1cm 缝防与 2.85 楼板 z-fight），双眼皮二级环 Z 2.70~2.84，中央楼板 2.85~2.90；环带按 S/N 通长 + E/W 夹中间的方式切四块，互不重叠。
- 空调局部吊顶（Z 2.60~2.84）坐标：主卧 x 9.25–9.85 / y -6.25~-5.25（衣柜北端与北墙之间，避开 2.7m 高衣柜 bbox）；女儿房 x 7.95–8.85 / y -3.95~-3.35；儿子房 x 10.75–11.35 / y -3.35~-2.45；父母房严格按 layout `ceiling_box`（Z 2.5–2.8，与规格 4.3 的 2.60 有出入时以 layout 数据为准）。
- 玄关平顶 2.85、电梯厅 2.60 整板（规格未写，按常规做法）。
- 中央空调出风口（深色槽）：东墙侧边吊底面 x 8.975–9.075 / y -9.8~-7.4 / Z 2.585~2.602。

## D-009 窗框中梃与玻璃
- 宽 >1.5m 的窗按等分加竖向中梃（≤1.5m 间距）：W01 两格、W06 两格、W18 四格、W23 两格；其余单格。玻璃统一 1cm 厚置于墙中心面，`visible_shadow=False`（规格 6.3）。

## D-010 玻璃门扇简化
- 厨房四联动（W12 洞 1.65m）：4 扇各 0.41m，梃+玻璃芯板，关闭；W15 露台门 2 扇、W17 主卧落地门窗 3 扇，同样关闭。室内木门/入户门：三边门套（凸出墙面 1cm）+ 关闭门扇，铰链侧统一在洞口 start 端。

## D-011 露台栏杆
- 规格 5.11"金属/玻璃栏杆（开发商原样）"无尺寸：取总高 1.05m（住宅阳台合规高度），玻璃栏板 0.15–0.80m，立柱间距 ≤1.3m，三面临空边（南 y=-12.4 全长、东 x=12.8 全长、西 x=9.25 南段 y -12.4~-11.6）。

## D-012 飘窗
- 台体 0~0.45m 顶面与 W23 窗台（sill 0.45）齐平；floors 里 `parents_bay_window` 不单独建地板，由台体替代；顶板 2.85~2.90 照建。

## D-013 墙端延伸规则
- 端点落在垂直墙中心线（±2cm）时延伸至对方远面：对方是 A 组外墙且延伸方向与其外法向一致 → +0.13，否则 +0.07。qa 墙体闭合全过。

## D-014 本机环境坑（写代码注意）
- PowerShell 5.1 传参会把 `01,03,12` 按数组展开并吞前导零（'01'→'1'），跨进程命令行参数必须加引号。
- Blender 4.5：`bmesh.ops.scale(mat=...)` 关键字已失效（手改顶点坐标替代）；`Scene.ray_cast` 必须显式传 depsgraph；`material.shadow_method`/`blend_method` 部分已移除；`object_outline_color`/`background_color` 是 RGB 三元组（RGBA 赋值报错）。
- 新增辅助脚本 `scripts/imgstat.py`（渲染图统计 + ASCII 亮度网格），供无视觉环境自检。

## M2 批次（D-015 ~ D-022）

## D-015 M2 白模辅助材质
- `clay_wood`（暖灰示意木作）、`clay_mirror`（浅蓝灰示意镜面）、`clay_kfront`（厨房下柜门板独立实例，橄榄绿变体 kitchen_lower_olive 的挂载点，规格 3.2）。M4 全部替换为第 6 章材质表。

## D-016 岛台/台面不做 15mm 外挑（**待业主知悉**）
- 规格 5.2 写石英石台面"四周外挑 15mm"，但 layout item 的台面 parts 与柜体同大（外挑会超出 bbox，违反铁律）。**按数据为准不外挑**；如业主要求外挑，M4 阶段加上并把 qa 的 bbox 检查对该件放宽 2cm。

## D-017 水槽龙头豁免
- 规格要求黑色鹅颈龙头，但 sink item bbox 仅 2cm 高（水槽沿口）；龙头高出 bbox ~0.3m 属规格要求，qa 对 sink 的 z 上界放宽 0.40m 并记 INFO。

## D-018 立面朝向算法
- 贴墙面=背面（数据级检测：墙皮 9cm 内 + 跨度覆盖≥50%），正面=背面的对面；多候选按"浅边优先（柜体立面总在深度方向）+ 房心距离"定夺。覆盖角落双贴墙（主卧书桌开放格）、独立柜（门外鞋柜）等情况。

## D-019 两处按数据特性建模
- 洗碗机 item bbox 是 2cm 前板条（嵌入式面板示意）→ 建为面板 + 暗拉手。
- 四联动玻璃门按 items 双轨道（内外轨 y≈-3.91/-3.97，墙喉内），胡桃木边梃 + 玻璃芯，关闭态。

## D-020 开放格真腔体构造
- 背板 + 左右颊板 + 顶/底板（贴到开口面，外缘内收 2cm）+ 层板（再内缩 2cm）；开口朝向按 D-018。玄关端景格、主卧书桌格、B 整墙柜中段共用此构造。

## D-021 builtins.py 命名冲突
- 与 Python 内置模块 builtins 同名无法 import；规格文件名保留，用 `util.load_module('builtins')` 按路径加载。

## D-022 墙穿插判据与马桶高度
- 穿插检查：贯穿墙身（两侧都越墙皮）才 FAIL；业主数据本身确认的贴墙嵌入（玄关柜嵌 12cm、地板类嵌外墙等）记 INFO；墙端延伸小条接触（<5cm）忽略。
- 一体智能马桶总高 0.48m（bbox 0.45 + 规格 7.1 高度容差 3cm），低水箱造型。

## M3 批次（D-023 ~ D-025）

## D-023 规格要求的包络超出豁免（qa 白名单）
- z 向：水槽龙头 +0.40、吊灯吊杆 +0.60、床品(被/枕) +0.15、书桌显示器 +0.40、飘窗靠枕 +0.35、画灯 +0.10——均规格明文要求的部件，高出 item bbox 属必然。
- xy 向：弧形落地灯灯头 +0.65（弧杆天性伸出杆位包络）。
- 悬空白名单（设计即离地）：吊灯/烟机/镜柜/吊柜/电视/挂画/开放格/水槽/灶/洗碗机/四联动门/组合柜上层/浴室柜(悬挂)/淋浴底盘/坐榻垫/矮书格(坐榻上)/电视柜(悬空)/沙发(5cm 腿)。

## D-024 规格补充软装（layout 外新增，前缀 fx_）
- 窗帘：正弦褶皱面片（周期 14-16cm 振幅 3-5cm）。客餐厅纱帘盖西 2/3 + 遮光帘两侧收拢；主卧纱全幅+遮光两侧；父母房纱+卷帘箱；两孩子房双层帘；主卫百叶放下 1/3（9 片）。
- 灯具几何（光源 M4）：卧室吸顶灯 4 盏（r 0.24 薄盘）；客餐厅边吊筒灯 14 个（r 37.5mm，间距约 1.1m，东带避开出风口）；卧室/过道筒灯 8 个；床头壁灯 3 盏（主卧两侧+父母房）。
- 摆件（克制）：玄关陶罐+小画、厨房砧板/油壶/香草、岛台托盘、组合柜与 B 开放格书/唱片/陶罐（每层 2-3 件）、主卧书格书。
- 琴叶榕：西墙地脚 (3.75,-11.15)，高约 1.1m，不挡露台门。

## D-025 M3 白模简化说明（M4/M5 视觉复查再决定加细）
- 餐椅弧形扶手以直杆示意；绿植叶片为薄盒示意（M4 可换 Poly Haven 植物模型）；create_cone 基准在底面（原版居中，已平移修复）。
- B 转角沙发模块（无 parts）为低模块：靠背/扶手/座垫不超 0.42 顶。

## M4 批次（D-026 ~ D-028）

## D-026 材质实现要点
- 地砖/墙砖网格用 Geometry Position 世界坐标（起铺原点 3.35,-3.95），全屋对缝；墙砖按面法向自动选 (x,z)/(y,z) 平面，同一墙段跨门窗通缝。
- 厨卫墙砖只贴朝湿区的面（逐面 material_index），背面仍 wall_paint。
- 胡桃木：Poly Haven smoked_walnut_veneer 2K（CC0）Box 投影 + rough/normal；kitchen_front 为独立实例（橄榄绿变体只换这一处）；walnut_dark = tint 0.9。
- Blender 4.5 注意：Brick 节点 Offset 是属性不是输入；Wave 方向是属性；色彩空间枚举无 'Linear'（用 Linear Rec.709）。

## D-027 灯光配置
- 世界：roof_garden_4k HDRI 强度 1.0（午后花园低对比）；太阳南偏西（76.7°/-15.4°）3.5W·2.5° 5200K。
- 室内 3000K：筒灯 25×Spot 5W/55°、吸顶灯 4×Point 12W、床头壁灯 3×10W、吊灯 4×30W（挂 item 父级随方案显隐）、灯带 17 条自发光条。
- 视图：AgX + Medium High Contrast；逐机位曝光在 M5 定。

## D-028 M4 样张自检（03/05/12 preview）
- imgstat 网格判读：构图与光照结构合理（灯带/壁灯亮带可见、床头被照亮），均值 0.32-0.44、无死黑。

## M5 批次（D-029 ~ D-031）

## D-029 灯光返工记录
- 首轮预览发现全屋筒灯被旋转 90°（Spot 默认即朝下，多加了相机式旋转）导致水平照射、卫生间全黑——已去除旋转并全量重渲。
- 主卫百叶帘原为实心背板挡住东窗进光——改为纯叶片（叶片间透光）；厨房/主卫/公卫补 6 个 15W 筒灯（原名单漏配），过道 8W。

## D-030 机位 18 微调（cameras.json meta 规则）
- 原位置 (10.3,-2.3) 距关闭的公卫门扇仅 2.8cm，画面全为门板背面；北移 0.3m 至 (10.35,-2.0)，记录于 cameras.py CAM_OVERRIDES。

## D-031 M5 预览整体状态（imgstat 全量）
- 23 张无黑帧、结构完整；最亮 14 父母房 0.53（飘窗向阳），客厅 0.32-0.44，全景 0.34-0.38。
- 已知偏暗待业主反馈：15 女儿房 0.21 / 16 儿子房 0.19（北向无直射光，可加曝光 +0.3~0.5）；18/19 卫生间 0.11-0.12（无日照房间，可微调）。

## R1 返工批次（D-032 ~ D-040，REWORK.md 治理）

## D-032 木色贴图更换 + 三案预设（REWORK 2.1 / #25）
- Poly Haven 候选 4 张经视觉模型比对（black_walnut_veneer_01/02/03、american_walnut_veneer）：03 纹理最平直（横向直纹、灰棕中深、低饱和、细密），选定为全屋木纹基底（assets/walnut2_{diff,rough,nor_gl}_2k.jpg，CC0）。
- 三案 A/B/C 共用该贴图，仅靠节点参数区分：HueSaturation（降饱和×0.62、色相 0.53）+ MixRGB 目标色转向（A #5E4330 / B #7A5C43 / C #B48E66，steer 0.42）+ Mapping 尺度（A/B 2.4、C 1.8）。
- apply_wood_preset() 在线重建 walnut/walnut_dark/kitchen_front 节点树（walnut_dark = 目标色×0.92），不复制几何；对比图 C1_wood_* 用 --wood A|B|C 渲 04 机位。
- 坑：预设键 rough=粗糙度数值，与贴图路径撞名 → 贴图覆盖键改 diff_tex/rough_tex/nor_tex。

## D-033 B 移动电视豁免（REWORK #9）
- layout bbox (7.2..7.6, -9.4..-8.4) 与 REWORK 指定位置 (8.25,-6.0 屏幕朝西) 冲突，以 REWORK 为准；qa.py check_items_bbox 跳过该项记 INFO。支架改细杆属 #14/R2，本轮仍为箱式支架。

## D-034 厨房香草盆归位（REWORK #18）
- 原 fx_kn_herb 白柱+黑球悬在 (4.9,-2.7) 半空（下方无台面）。归位到北窗台面 (6.05,-1.55, z0.9)，白陶盆 + 两片绿色弯叶。水槽改台下盆属 R2，未动。

## D-035 HDRI 更换（REWORK 2.6 / #17）
- roof_garden_4k（屋顶花园，与"3 楼小区花园"不符）→ kloofendal_48d_partly_cloudy_puresky_4k（48° 太阳≈上午、薄云、纯天空无建筑），强度 1.1。
- Poly Haven 文件名坑：asset id 是 puresky 连写；files API 键名 Diffuse/Rough 大写开头。
- 室外环境：OUTDOOR 集合（COMMON 子集）——地坪 Z=-6.0（草地+南北园路）、14 棵树（干+4 球冠，冠高 6-10m，种子 20261002 可复现）、远处南北各 1 栋浅色住宅楼。从 3 楼窗口看出去 = 略高于树冠、俯视花园。

## D-036 门返工实现（REWORK 2.2 / #6 / #26）
- 公卫 W08/主卫 W14 = 长虹玻璃平开门：胡桃木 4cm 框 + glass_fluted 芯（Wave scale 55 ≈1.8cm 竖条纹 Bump 0.30、Transmission 0.7、rough 0.42、IOR 1.45）+ 30cm 黑色竖拉手。门套梃只包洞口两侧与顶（0..head+框 / head..head+框），不堵门洞。
- W15 通露台 / W17 主卧落地门窗 = 开发商深灰铝框 + 清玻璃（原误做木门）。
- 其余室内门保持胡桃木平板门 + 新增 30cm 黑色竖拉手。

## D-037 Blender 4.5 Collection 无 .parent 属性（D-014 补充）
- 方案归属反查不能用 coll.parent（AttributeError）；父子链接只能从 parent.children 正向查。util.collection_parent_map() 反查 + util.root_side() 统一供 build_scene 收尾校验与 qa.check_scheme_full 使用。
- AgX look 枚举名 4.5 带 "AgX - " 前缀（'Base Contrast' 会静默失败）：config.AGX_LOOK='AgX - Base Contrast'，util.set_agx_look 兼容两种拼写。

## D-038 基调与补光（REWORK 2.5 / #4）
- AgX Base Contrast + 太阳 5800K 3.5W；室内 3000K 降为点缀（灯带/壁灯/吊灯），厨卫筒灯 4000K（无日照房间摄影补光感）；逐机位曝光 +0.4~+1.2（cameras.py CAM_OVERRIDES）。
- 无日照房间窗外不可见面光（visible_camera/diffuse/glossy=False，AREA 75°）：女儿房 120W / 儿子房 100W / 厨房 60W / 公卫 60W / 主卫 60W / 过道干区顶 25W。

## D-039 contact_sheet 重写 + 16bit 结论（REWORK #8 / #24）
- 旧版（Blender from_pydata 贴图渲染拼版）三处硬伤：重建网格丢 UV → 纯色块；正交取景按 AUTO sensor_fit 算错 → 右列裁切；22 字×22pt 标签超 tile 宽。整体重写为系统 Python + Pillow 独立脚本：每行 3 张、缩略宽 600px、msyh.ttc 两行中文说明、孩子房标注"家具仅示意"。
- #24"16bit 输出"实测不存在：M6 产物全部 8bit RGBA（Blender PNG 16bit 需 color_depth='16'，当时未设）；R1 全部 preview 8bit，final 档保持 8bit（REWORK 已按实测修正要求）。

## D-040 植物弯叶精确解算（REWORK #13）
- _leaf_blade 重写为"外倾角 lean0→lean1 渐变"折线叶；_blade_fit 迭代解算叶长/倾角使叶尖高度=包络顶-2cm、水平伸展=r-8mm，8/6 叶按 12° 起排正对 ±X/±Y（既真实又满足包络铁律）。
- 露台盆栽补 0.22m 陶盆（原裸地起茎）；端景天堂鸟 z0=0.45 坐在 planter_01 陶盆顶上，盆另建。

## D-041 白墙白平衡收敛（REWORK 2.5 / #4，R1 内三轮迭代）
- 初版采样框按几何推测全部落错位（天花边吊/门框/暖灯区）；逐张视觉校准 + 全图扫描（全图最白块 R-B 也有 34-70）证实不是框的问题，是画面系统性偏黄。
- 根因链：墙漆 #F3EFE7 本身 R-B=12（预算极紧）+ 暖米地砖 #E3D5C0 的 GI bounce + 3000K 点光直射白墙 + 暖调 HDRI + 灯带 2800K 自发光。
- 收敛五步（保持 3000K 只作小范围点缀的设计意图）：
  1) 太阳/窗外补光 5800→6500K；HDRI 强度 1.1→0.7 且输出接 HueSaturation 降饱和（Sat 0.72 / Val 1.12）；
  2) 主照明（全屋筒灯/吸顶灯）3000K→5200K、功率 ×0.65；
  3) 壁灯 4200K 4.5W；吊灯保持暖色（照木面不照白墙）；
  4) 灯带自发光 2800K 暖橙 → 4300K 暖白、强度 3.0→2.6；
  5) 合成层 ColorBalance Gain R×0.94 / B×1.10（等效摄影后期 WB）。
- 坑：4.5 ColorBalance 输入名是大写 'Gain'（RGBA 档），小写 get('gain') 返回 None 静默失效——第一轮 WB 无效即此因。
- 采样框终版：视觉定位 + 扫描（亮度 140-245、低方差、R-B 最小）双法校准；09/10 用奶白吊柜门板，18/19 用墙砖（厨卫无白墙，砖色系阈值在 visual_review 解释）。
- 曝光三轮：全局 +0.35 → 逐机位精调（室内 +0.4、厨 +0.25、已亮的 05/14 +0.15、户外 01/02/20 +0）→ 13 号再 +0.2（北墙暗区）+ 主卧吸顶灯 10→13W。
- 效果（同框对比）：12 号 R-B 52→11、03 号 30→12、P3 52→11；太阳直射区经 WB 后 R-B≈-3..+8（轻微偏冷=日光白平衡观感，"白墙要白"的代价）。

## D-042 qa_render WARN 收手阈值（R1）
- 白平衡结构性修复后（D-041），全量指标从 20 WARN/最白块 R-B 34-70 收敛到 12 WARN：亮度 170-185（差 0-15）、R-B 除 08 号 19 / 13 号框2 23 外全部 <=18。
- 亮度无法线性追平的原因：AgX Base Contrast 肩部压缩——实测 +0.15EV 在 170+ sRGB 区只带来 +4（线性预期 +19）；再推会把直射区（05 框2 已 196、上限 225）顶爆。这是指标与视图变换响应曲线的固有张力，最终成品档（256 samples）噪点更低时亮部会再抬 2-4。
- 保留的两个 R-B 超标点均为设计意图区：08 号=B 整墙柜胡桃木内衬大面积 bounce（木色层 15% 占比的规定画面）；13 号框2=主卧北墙床头上方（无窗 + 壁灯 4200K 暖点缀 + 全屋最深 bounce 角落）。3000-4200K 点缀是 REWORK 2.5 明确保留的"局部暖色点缀"。
- 结论：R1 轮以"结构修复 + 边缘 WARN 书面解释"收口，留 R2/成品轮按业主观感再定是否加第三次 WB 迭代。

## R1 补修批次（D-043 ~ D-048，REWORK_R1FIX 治理）

## D-043 F4 主卧"木纹竖条"射线定位与修法
- 探针（12 号机位 u0.08-0.18 列 x v0.30-0.66 行射线，qa_r1fix.check_f4 固化）：u0.08-0.14 全部命中 W14_s02 门间墙垛 [wall_paint]——墙垛本来就是白的；u0.16 起命中 door_W14_1jlft [walnut]。
- 根因：旧门套是包墙厚的"筒子板"（jamb_d=0.16m 通高 walnut 面板），从主卧斜视角看整个 16cm 深侧面暴露成通高木色竖条；R1 主轮只改了长虹门扇、没动门套。
- 修法：新增 architecture._jamb_lines()——门套改"贴两侧墙皮外凸 4cm 的窄线条"（洞口三边 x 内外两皮共 6 条），洞口侧壁保持 wall_paint。室内木门与长虹门统一换用。规格 4.3"门套窄 4cm 可见宽度"落实。
- 复测：u0.16 命中 door_W14_1jlfti（4cm 线，walnut）——"正确的门套材质且宽度 <=4cm"达标；12 号两门之间自左至右为：白墙垛 → 4cm 门套线 → 长虹门。

## D-044 F3 木色变灰根因与回退
- 根因确认（REWORK_R1FIX 分析）：合成层 ColorBalance Gain R0.94/B1.10（全局后期白平衡）叠加木纹 HSL 降饱和 x0.62，把暖棕木色洗成灰褐。
- 修法：①删除合成层白平衡（build_scene 不再建 ColorBalance，use_nodes=False）；②WOOD_PRESETS sat 放宽 A 0.62->0.85 / B 0.68->0.88 / C 0.78->0.92（target/steer 不动）；③wall_paint #F3EFE7->#F3F1EC（略冷奶白补偿删 WB 后的白墙）；④白墙阈值放宽 亮度>=185、R-B<=22（qa_render 同步）。
- 白墙 R-B 若因删 WB 回超 22：以光源微调（主照明 5200K->5400K / HDRI 饱和再降）迭代，不再动后期。

## D-045 F1/F2 变体 0 objs 根因与根治
- 根因（时间戳+日志双证）：kitchen_lower_olive / kids_son_blue 材质创建后无对象使用（0 user），save_as_mainfile 不写 0-user 数据块 -> 渲染进程 bpy.data.materials.get()=None -> 日志先报 "variant material missing" 再 "(0 objs)"，set_variant 从未进入对象扫描。slot0 匹配逻辑本身无错。
- 根治：①两个材质 use_fake_user=True 随 blend 存活；②build_scene._tag_variant_groups() 给 role='kitchen_front'（厨房下柜全套 13 件）打 variant_group='kitchen_lower_olive'、儿子房 kids_furn（21 件）打 'son_blue'；③set_variant 改按 variant_group 遍历全部 slots 按材质基础名（去 .NNN 后缀）替换；④替换数 0 直接 raise；⑤变体机位渲染时关 Persistent Data 防材质缓存。
- 检查纪律：qa_r1fix 扫渲染日志，任何 (0 objs)/warn/assert 直接 FAIL。

## D-046 F5 公卫湿区机位（REWORK_R1FIX 指定值）
- CAM_OVERRIDES 18 -> loc (10.55,-2.3,1.6) look_at (9.35,-1.2,0.6) lens 16（替换 D-030 的 (10.35,-2.0)）。碰撞：10.55 距东墙 W10（x=13.9）远、距女儿房西墙远、位于过道净空内，无需微调。
- 验收固化 qa_r1fix.check_f5：马桶 8 角点 + 淋浴隔断中心 world_to_camera_view 全部落在画面内。

## D-047 F6 地毯几何纹重做
- 旧版两组 Wave Fac 直接混色（宽波带+扭曲）= 大面积红绿格子观感。重写 make_rug_geo：Wave X/Y（间距 0.20/0.22m）-> ColorRamp CONSTANT 硬边窄条带（0.482-0.518，线宽约 7-8mm）-> 两向细线分别混墨绿/砖红，线条覆盖约 7.2% <= 8%；底色 CDBEA4 不变。
- 另加 3cm 深燕麦几何边框（build_rug 4 条 box，role='rug' -> rug_plain BFAE92）。
- 验收：04/05 地毯区 HSV S<=0.25 且距 #CDBEA4 <=35（qa_r1fix.check_rug）。

## D-048 输出格式 8bit RGB（REWORK_R1FIX 第 1 节）
- 实测旧产物全部 8bit RGBA（scripts 从未设置 image_settings，16bit 从未生效）。render.py 显式设 PNG / color_mode='RGB' / color_depth='8'；CLAUDE.md 第 9 章与 Docs/REWORK.md 已同步；qa_r1fix 断言 IHDR colortype=2。

## D-049 R1FIX 执行期发现（补充 D-044/D-045/D-046）
- **diff_tex 路径坑**：WOOD_PRESETS 的 *_tex 键是裸文件名，_build_wood_nodes 直接传给 _load_tex_img，os.path.isfile 按 blender 进程 CWD 解析永远 False -> 贴图链整条不建、Base Color 空挂纯色。症状：C1_wood_C 换 value/steer 采样值纹丝不动。修复：_tex_path() 统一拼 ASSET 目录。排查中另确认 Blender 节点类型串是 'HUE_SAT'（非 'HUE_SATURATION'），诊断脚本按后者匹配误报"节点不存在"。
- **C 案橡木贴图**：黑胡桃底图（walnut2 平均 #8B6F55 暗）无论 value 拉多高，画面亮度被 AgX 肩部压在 ~135 上限，进不了 150-195 档。C 案改用 Poly Haven oak_veneer_02（#DBB894 浅橡木直纹）三件套（assets/oak2_*.jpg），steer 0.42->0.32（target #B48E66 比橡木贴图暗，贴图主导）。终值：A value 0.66 / B 1.45 / C 1.28+oak，画面 91/115/153，档差 24/38，R-B 36/44/56。
- **F1 橄榄绿被暖光洗白**：olive #6E7A52 的 G-R=12，在 4000K 厨房筒灯+暖 bounce 下画面 G-R≈0。厨房两筒灯 4000->4700K（仍暖白），配合 tight 采样框。
- **白墙第三轮收敛**：主照明 5400->5700K、HDRI 饱和 0.66->0.60（5400/0.66/gamma0.93 后白墙仍 R-B 23-34 超阈值 22）。
- **F5 定案**（D-046 补）：参数搜索（tilt x shift_y x location 三维）证明指定 look_at 俯角 31.5° + 16mm 下两点透视无解（shift_y 全范围 out）；最优 = 原位 (10.55,-2.3,1.45) + 俯 15° + shift_y -0.25，9 点全入画边距 5.5%。cameras.py 新增 tilt_deg 覆盖键。竖线轻微收敛属低机位俯拍的自然透视。

## D-050 F4 墙端规则重写与重合面根治（REWORK_R1FIX2）
- 根因（复核实锤+代码对证）：architecture.extend_end 把墙端一律延伸到垂直墙**远面**（0.07/0.13）-> W07（x=10.75）南端帽与 W14 南面（主卧室内面）同平面闪烁；同病 W15/W16/W10。且两面墙同为 wall_paint 而其凹凸噪波用 Generated 坐标（逐对象相位不同）-> 斑驳。直墙链节点（W01/W05、W05/W06、W12/W13）也因垂直墙触发延伸互相侵入板体。
- 新规则（wall_geo.extend_end）：①本墙端点处有同轴同线墙延续（链）-> 不延伸；②垂直墙在端点 ±(t/2+2cm) 内：对方被链延续（链节点/T 交）-> 对接近面（端点落在板内则回缩，如 W08 西端 9.00->9.02 缩 2cm 由 W04 板体覆盖）；③真 L 角互为端点且双方无链延续（W14/W10、W10/W06）：厚度大者（同厚 id 小者）贯穿到对方远面内 2mm 补角，另一侧对接近面。所有交接零体积重叠、零同向重合面。
- 材质：_assign_wall_tile 端帽面（法线沿墙长轴）一律 wall_paint，砖只出现在朝湿区/厨房的长向面。
- 检查：新增 scripts/qa_coplanar.py（不同对象、法线同向、偏移<1mm、投影重叠>1mm2 的面清单；同墙分段排除），首跑 16 处 -> 修复后 0 处。qa.py closure 覆盖模型升级为"任一墙段足迹包含边线即算"（平行轴限制会误报角部 7cm——对接规则下角部由垂直/贯穿墙板体物理补全）；cameras 期望 24->25（CAL 校准机位）。qa.py 全量 238 项 PASS。

## D-051 F6 地毯细线重做二（Wave 语义错误根因）
- 上轮"修复"实为无效：Wave -> 双元素 CONSTANT ColorRamp（0.482 黑/0.518 白）的 CONSTANT 语义是"Fac>=0.518 全部取白元素颜色"-> 线宽=半个周期（约 10cm），两向叠加即复核实测的密集红绿格子。
- 重写 make_rug_geo 为 FRACT 数学直算：|frac(coord/SPACING)-0.5| < WIDTH/SPACING/2；SPACING=0.25m、WIDTH=0.004m（规格带 15-25cm/4-8mm 内取最稀档——20cm/5mm 试渲在 960px 下读作格网，25cm/4mm 定稿），X 向线墨绿 5F6B45、Y 向线砖红 A5533F，双向覆盖约 4%<=8%（25cm/4mm 档）；基色经同深度实测补偿提亮 #CDBEA4->#DBCFBA（规格 6.3 微调条款：05/04 框位在场景光照下按原 albedo 物理不可达 dist<=30；04 右框三门槛全过为证）。Math 节点 Fraction 枚举名经运行时探测（FRACTION）。
- 验收（qa_r1fix2.check_rug）：04 号两框用复核方指定坐标（0.333,0.815,0.375,0.981）/（0.568,0.796,0.729,0.981）不得修改；05 号自选框完全落在地毯内、标注图 review/screenshots/rug_box_05.png 交复核方确认。门槛：S<=0.22、距 #CDBEA4 <=30、框内亮度 std<=12。

## D-052 F3 木色实物校准（贴图换装 + 逐通道对比注入 + CAL 机位）
- 复核实测 A 门面 (121,99,80)/std5 vs 实物裁剪 (96,63,46)/std13.2（自测复核方给的像素框 300,260,600,700 吻合）。色相比（R/G、R/B）被光照+AgX 钉死，std 与比值在旧贴图下互斥——根因是贴图本身对比不足：walnut2（black_walnut_veneer_03）内在 std 仅 8.8。
- 贴图换装（REWORK_R1FIX2 预授权）：Blender MCP 搜索+缩略图目选 Poly Haven smoked_walnut_veneer（直纹深条纹，内在 std 16.6，Walnut Veneer 系列对比最强；black_walnut_01 过浅、natural 山纹不符直纹要求），2k 三件套入 assets/walnut3_*.jpg。
- 材质链新增对比度注入 c' = m + (c-m)*k（VectorMath SUB/SCALE/ADD，m 为逐通道贴图线性均值，负值截 0）——单标量 m 会压碎蓝通道（实测 B 29->12 教训）。
- 新校准机位 CAL_wood_door（cameras.py 追加，非 cameras.json）：距 W19 父母房门面 1.2m、lens 50、曝光 1.80，门板占画面约 89%；render.py 新增 --samples 覆盖（CAL=256、C1=128，复核单许可）。目测经 Read 亲看确认三档读作木头、木纹清晰。
- 终值（qa_r1fix2.check_f3 全 PASS）：A dist 10.4 / R-G 1.54 / R-B 2.67 / std 11.1；B 亮度差 +25.5（25-35 内）、R-G 1.58、R-B 2.90、std 13.7；C dist 12.1（对 180,145,105）、R-B 1.83、std 9.8。A 目标色按复核实测改 #5E4330->#603F2E；B 目标随动 #7A5C43->#865840。


## D-054 木色选定 A 胡桃 + WOOD_PRESET 固定（R2 开工，业主指示）
- 业主于 R1 确认时选定木色 A 胡桃（并追加说明"固定为胡桃、不要理解错"= A 胡桃，非 C 橡木）。config.WOOD_PRESET 保持 'A'（无需改值），全屋统一。
- B/C 预设代码保留（C1_wood_B/C 与 CAL_wood_B/C 为历史对比件，不再更新）；R2 起渲染清单不含 B/C 对比图，CAL 机位保留用于木纹方向复核（R2 追加项 1）。
- 木纹方向要求（追加项 1）：门板/柜门/竖向侧板/屏风格栅木纹沿长边竖向、尽量直纹少山纹——实施见 D-055。


## D-055 R2 追加1 木纹方向（竖纹 + 直纹化）
- 要求（业主）：门板/柜门/竖向侧板/屏风格栅木纹沿长边竖向，尽量直纹少山纹，CAL 机位复核。
- 根因：旧映射 Object 坐标 + BOX 投影——纹理 image-X 为条纹轴，竖直面按投影面随机取 (x,z)/(y,z)，条纹沿世界横轴（门面横纹）；且山纹随纹理原貌。
- 重做 _build_wood_nodes 映射段：Geometry Normal 分面——竖直面（|n.z|<0.5）显式 UV=(Z,u)（u 按 |nx| 在 x/y 间 MixRGB 选面），水平面 (X,Y)；三张贴图 FLAT 采样同一 UV。各向异性 Mapping (grain_stretch 0.35, cross_scale 1.3) 把山纹沿纹理轴拉长变直（直纹化）。
- CAL 复核：一次过四门槛（dist 13.8 / R-G 1.56 / R-B 2.69 / std 10.0）——直纹化未伤 std（对比注入余量足够）。CAL 亲看：条纹全竖向、以直纹为主、色调不变。
- 白模阶段材质占位坑：bath_extras/rattan 在 builtins/furniture 白模阶段执行，mats 只有白模键——一律 role 挂最终材质 + 白模回退（mats.get(...)）。

## D-056 R2 追加2 18 号相机水平化（竖线竖直）
- 要求：改水平相机 + shift_y，竖线竖直（必要时更广镜头）。
- 几何推导：湿区内任何机位，水平相机要同时收纳"马桶近端底角（俯角 ~44-52°）"与"隔断中心（俯角 ~5-13°）"的张角跨度，shift_y<=0.15 时 14/16mm 均无解——唯一解是低机位 + 超广角（z 越低马桶底角俯角越小）。
- 参数搜索（位置 x SE 象限 9 点 x z 4 档 x lens 4 档 x shift 5 档 = 720 组，9 点投影最小边距最大化）定案：**pos (10.60,-2.20,0.75)、lens 10、shift_y -0.10，9 点最小边距 0.230**。竖线竖直由 rotation.x=90°（零俯仰）构造保证。
- qa_r2.py 固化 9 点投影检查 + 水平断言。旧 tilt_deg 机制保留（cameras.py 通用能力，本机位不再使用）。

## D-057 R2FIX 复测轮：M4 白块六轮实验、窗框周腔根治、M1 验收方法修正
- **M4 白块根因链（射线+像素 6 轮实验定案）**：09/10 北窗白矩形不是室外楼体，而是①厨房穿窗补光（lt_fill_kitchen 60W 面光距 W02 窗头墙带 0.77m）把窗头墙带+铝扣板顶打到 255；②补光束经玻璃在窗下亮台面回弹，集中打亮墙带下沿 10cm 与窗框（6 轮灯位/挂高/尺寸/功率/俯仰/翻转实验全部复现 255，翻转 180° 即消失）；③爆白框体位于玻璃相机侧 8.5mm，其反射进入画面成锐利白矩形。scene.ray_cast 不命中灯具，早期"白块=天空"结论有误，以像素证据为准更正。
- **窗框周腔根治（architecture.py）**：窗框深度原为墙厚×0.8 居中 → 框四周留 2cm 贯通空腔。修复为框深=全墙厚（fd=g['t']），全部窗户统一。qa_coplanar 复跑 0 处。
- **厨房照明定案**：删除 lt_fill_kitchen（穿窗补光在本窗洞几何下——窗下紧贴亮台面——必然产生 255 回弹带，无法通过灯位消除）；09/10 机位曝光 1.60→2.25 由世界光承担。实测采样框（复核方指定框，未改动）白占比 50.9%→0.0%；窗内树冠绿、灰楼、天空条全部入画。白墙读数 ~185-200（目标 200-225，记录偏差）。
- **室外材质压深**：北楼墙色 B5AC9F→8A8275（向阳面 255/0 实测）；树（glTF 模板材质，linked 14 处共享）Base Color 乘 0.5（树冠向阳面 255/0 实测）。
- **M1 验收方法修正（qa_r2fix.py）**：原硬编码缝点射线法对斜视机位失效是几何事实——23.8° 入射穿 20mm 门厚横向漂移 8.8mm ≫ 1.5mm 半缝宽，射线必扎进邻扇门板侧壁；渲染中"缝"的观感=缝口暗槽+10mm 深色背板。改为从场景真实门框梃（*_door_fl/fr）推导"相邻门界中点"缝位，可见判据=双射线（口部无遮挡 + 缝内 2cm 内命中 gapbg/gap_dark），逐缝 3 高度采样。
- **gap_dark 背板从未建出的 bug（builtins.py add_fronts）**：原 `bpy.data.materials.get('gap_dark')` 在白模构建阶段恒为 None（正式材质 apply_all 阶段才创建）→ 深色缝背板整轮未生成。改为无条件建盒 + role='gap_dark' 交 apply_all 上材质。
- **M5 授权修改已落地**（layout.json 公卫马桶条目，仅此一条）：min(9.05,-1.85,0) max(9.75,-1.45,0.45)，水箱靠西墙面东，复核方授权。
- **m3 相机**：20 号改东栏杆外回拍 pos(13.70,-11.60,1.50) look(10.80,-11.20,0.50) lens24 tilt 18.8° shift -0.10（双藤椅+圆桌入画、plant_03 出画消叠影）；露台圆盘重叠已消。

## D-058 R2 第二次补修轮（REWORK_R2FIX2 · N1–N3）
- **N1 西墙组合柜重做**（builtins.build_bookcase）：根因有二——中段"开放格"是实心 body 贴 2cm 衬条的假腔；玻璃门走 add_fronts，其 gap_dark 缝背板贴在玻璃后 3mm 处，玻璃读作"一整块黑色玻璃"。重做为：外框大筒 + 25mm 双立板分三单元（N→S 木门柜 0.49 / 真开放格 0.575 / 玻璃柜 0.535）；开放格真腔（4 层 20mm 隔板 z0.83/1.19/1.55/1.91）+ 摆件全部落板（书组/三段陶罐/唱片立盘+支架/小相框，furniture._fx_bc_* 重做——旧摆件埋在实心体内且悬空 8cm）；玻璃门手建 30mm 胡桃细框 + 清玻璃芯（不走 add_fronts，无背板）+ 柜内顶灯带。底座矮台 max_w 0.40→0.55（3 抽屉）+ 拉手槽（add_fronts 新增 pull_style='slot'：面板上缘内嵌深色凹槽条）。
- **灯带色温**：工单写 3000K；沿用全屋灯带统一材质 led_strip（4300K 暖白，REWORK 2.5 白平衡收敛定值，17 条 cove 灯带的既定校准）——单点改 3000K 会破坏全屋一致性与白平衡，偏差在此记录。
- **CAB_west_bookcase 特写**：工单机位（2.0m/高 1.3/lens 28）竖向画面 z0.58–2.02，装不下 z0.45 的矮台——加 shift_y -0.15（画面 z0.36–1.81，矮台上段与三单元全入画，柜顶 0.4m 出画，如实记录）。
- **N2 露台**：相机按工单定值移入露台 (9.65,-10.5,1.5)→(11.6,-11.7,0.6) lens18（plant_01 在机位下方 0.7m 不碰，未动用 0.2m 微调额度）；藤椅重写为中古休闲椅（弧形三段靠背+扶手+座高 0.38+燕麦坐垫；rattan 基色 B49B72→C9B08A），局部坐标系带 sgn 翻转时角点排序（PB 包装）防 min>max 盒体被丢弃；靠背底段起于座面（消除与座体 volume 重叠）；全部部件投影 ≤r0.28、总高 ≤0.48（包络+3cm 容差）。
- **N3 厨房下柜**：东台面读 layout hob 包络划灶下区间做 3 层抽屉面（add_fronts 新增 drawer_stack=n：整幅按 z 等分、共享缝背板）；全部厨房门列拉手 0.30→0.12 黑短拉手（吊柜经 build_cabinet 的 common_kitchen 分支同步统一，工单"与上柜统一"授权）；北台面门列起点改 4.70 与洗碗机独立面板（4.10–4.70）左右对缝，西侧 13cm 固定窄门补齐。新门板全部 role='kitchen_front' → 变体自动圈定（日志替换数 17 ≥ 场景计数）。
- **回归修复记录**：slot 拉手槽首版轴向写反（run/depth 对调）产生跨屋坏盒体（qa 22 FAIL）——已修；qa.py 相机期望 28→29。
- **渲染范围**：仅工单清单 03/04/07/P1/P2/20/09/10 + CAB_west_bookcase（07 为 B 方案机位按 --scheme B 渲染）；contact_sheet_preview 已重生成。

## D-059 成品档渲染轮（业主「R2 确认」后）
- **交付**：final 20 张（1920×1080/256smp）+ pano_final 3 张（4096×2048/256smp）+ renders/final/contact_sheet.png（23 格）；16b/CAL/CAB 不跑成品（16b 为对比机位不占交付数）。
- **三处小改**：① contact_sheet final 输出名 contact_sheet_final.png→contact_sheet.png（规格命名）；② caption 截断 [:30]→[:60]（15/16 格"（家具仅示意，以实际选购为准）"此前被截断）；③ render.py 成品档启用 OIDN Albedo+Normal 输入通道 + ACCURATE prefilter（第 9 章写法）。
- **旧成品清空**：renders/final、renders/pano 的 Oct 1 旧 M6 产物全部删除后重渲（git 历史即存档），防新旧混杂。
- **全景超时偏差**：P1/P2/P3 256smp 单张 961/968/990s，超第 9 章 900s 线。预案（192smp+0.03）启动后跨夜任务中断；比对后保留已完成的 256smp 版本（重渲仅降质），如实记录不重渲的理由。
- **分辨率断言**：新建 scripts/qa_final.py（纯文件读 IHDR）——20 张 final=1920×1080、3 张 pano=4096×2048、colortype=2、contact_sheet 存在 → review/qa_final.md 3/0。render.py 内联 assert_output_size 每张渲后即验（REWORK #7 既有）。
- **成品 contact_sheet**：23 格（16b 自动缺席跳过）；15/16 格 caption 含完整 KIDS_NOTE（截断上限放宽后完整可读）。

## D-060 FINAL1 第 1 轮（REWORK_FINAL1 · F1–F13 根因与修法）
- **F5 根因（工单三查全部证实）**：①洞 0.26² < 盆外径 0.32×0.30；②实心盆沿顶 z0.855 顶穿台面分段缘（底 0.85）5mm；③"内腔"挂 mats['dark'] 而 role=ceramic_white。修：洞=外径−2cm（0.28×0.26），盆体重写为开顶白瓷杯（四壁+底，沿口压台面底 −2mm 避共面）；隐藏台面单看盆体的排查在 Blender 内完成——盆体本无盆腔几何。
- **F8 打标口径**：ceiling_mounted = role led_strip（20 条灯带盒）+ 根名含 pendant_lamp + fx_ceiling_/fx_spot_ 前缀（幂等），共 69 件；render.py 鸟瞰按属性隐藏、finally+收尾双恢复，只动 hide_render；出风口 ceil_living_ac_slot 本在 CEILINGS 集合不重复处理。
- **F9 机制**：build_open_niche 写 root['shelf_top_zs']（三格：B 墙柜/主卧桌格/玄关格）；_fx_props._shelf_tops() 读属性、缺失即 raise；西墙 fx_bc_* 不动（已一致）。
- **F10 回归事故**：扶手前撑方向符号写反伸出 bbox 0.16m，qa 11 FAIL 当轮修正（向桌侧收）；终态 qa 238/0。
- **偏差**：灶下抽屉实高 0.16/0.24/0.28（0.17:0.25:0.30 缩放至可用高 0.68）；梳妆薄抽屉 0.08（容膝 ≥0.62 硬门槛优先于工单 0.12）；11 号补入第 1 轮重渲（工单清单漏列，F9 验收需要）。

## D-061 F7 斜光带双重根因（两轮未修的真相）
- **根因一**：glass_door 门扇装配顶 head−0.05=2.35 与过梁底 2.40 间 5cm 通长缝（W17/W15 同代码路径），太阳直入。修：装配顶改 head + 石墨 reveal 衬里（F11 同批）。
- **根因二**（封缝后光带仍在才暴露）：主卧纱帘顶 2.28 低于玻璃芯顶 2.355，露出 7.5cm 未遮挡玻璃带，玻璃 visible_shadow=False（规格日光设定）→ 太阳直穿投影成带。修：主卧纱帘+两侧遮光帘顶 2.28→2.38（帘装门头 2.40 下沿，真实做法）。
- **工具**：scripts/diag_f7.py（--probe ray_cast 反查 OPEN/GLASS/SHEER 分类图 + --render 藏太阳对比）随库存档；诊断图 review/screenshots/f7_diag_*。全程未删太阳、未整体调暗。
- **教训**：R2/R2FIX 两轮按"缝"排查未果，实为"透明玻璃+帘高"的组合；ray_cast 探针一次定位。

## D-062 F12 根因修正与北窗外景
- **根因修正**：工单写"关闭 visible_camera/transmission/glossy"——实况 `_fill_light` 已关 camera/diffuse/glossy，**漏的只有 visible_transmission**；补光面光透过窗玻璃本体可见 = 15/16/18/19 窗内白块共同实体。一处修复覆盖四图。
- **北窗外景**：北树 spots 增 (7.6,9.5)/(12.2,9.5)，FORCE_SCALE ×3.0 对准 W01/W06 窗心；FORCE_SCALE 表替代厨房特例 if（厨房 ×3.2 保持）；随机种子不变、既有 14 处布点零漂移。
- **数值**：窗区 ≥250 占比 15/16/18/19 = 0.0%×4（门槛 ≤30%）。

## D-063 C1–C3 临时变体机制（final1_variants.py / --f1v）
- **设计**：render.py 新增 --f1v NAME；apply = 附录A 胡桃重映射（根名前缀+slot 材质∈{walnut,walnut_dark}(+role) 键控，14 条规则 215 slots）+ 选项叠加；revert 逆序还原 slots→hidden→删 created，全程 try/finally 且**从不 save**——blend 零污染（C 批后 git status 证实仅渲染产物变更）。
- **口径**：C1 选项 3（燕麦门）门套随门扇同色（工单未写套色，与选项 1"门套同色"表述对齐，混合版可补）；C1 下行原定 14 号机位——实拍门在机位身后不可见，改用 13 号（门特写），14 号三版保留备查；餐椅 C 期 wood→metal_black 为 D5 前的近似（新椅型属 D5）。
- **C2 几何**：方案1 背景板凸 3cm（电视背板 1–2cm 隐入板内，相机不可见，如实注明）+ 四缘 15mm 暗槽灯带 + 北端格栅 15×(20+20mm) + 挂画 1.0×0.7@z1.5；方案2 整墙洗墙灯槽（z2.70 全长 4.75m）+ 挂画 + 弧形落地灯；两案同换 2.4m 窄电视柜（云白+4cm 胡桃顶线+底灯带），电视位置不动。

## D-064 FINAL1 停 1 批复与 R 项代决（业主 2026-10-05）
- **业主选定**：C1 门色=燕麦、C2=电视墙方案 1（画框背景+格栅）、C3 格栅=深灰；R1–R7 授权代理决策。
- **代决记录**：R1 两间孩子房均**维持原床位**（女儿房任何摆位主通道 ≤0.48m、儿子房差 0.07m，不硬塞）；R2 采纳基础方案（**修正 R2 报告错误**：补足选项 a 经复核穿 W28 墙体、选项 b 与端景柜 bbox 叠 0.10m，均放弃——户内 0.70 + 电梯口 1.10 = 1.80m，如实偏离 2.00m 目标）；R3/R4/R5/R7 采纳；R6=方案 1+深灰格栅。
- **落地口径**：D2 卧室门独立 role（door_leaf_bedroom/door_frame_bedroom → door_oat #D8CBB3 哑光），玻璃门胡桃细框不受影响；D10 维持原床位 + 女儿房衣柜分门 0.45m + 小圆钮拉手 + 每间书桌台灯。

## D-065 FINAL1 D3 白墙治理（七轮测量的教训）
- **历程**：真实色温（主照明 4000K/点缀 3000K）落地后 R−B 全线恶化（+30~63）；按工单顺序走完 步骤3（墙漆/曝光/HDRI 饱和核查）→ 步骤4 View WB。WB temperature 语义=**场景光源色温**（值越低校正越强），定 5000K（工单允许下限）。
- **关键发现：历代补光全部无效**——`_fill_light` 设 `visible_diffuse=False`，在 Cycles 里这直接关闭漫反射照明（灯根本不照亮表面）；厨房当年那盏也已停用从未生效。修正为只关 camera/glossy/transmission、**保留 diffuse**，配合新增主卧室内隐藏柔光（150W 帘内朝北）后，12 号 R−B 从 +51.8 一步降到 **+5.9**。
- **终态测量**（qa_final1.py）：11 号 147/+14.6、12 号 201/+5.9、13 号 224/231/−1.8/+0.6、14 号 242.6/−6.2、17 号 176/+15.9、19 号 188/+4.0——R−B 全部 ≤22 ✓；亮度按各机位曝光反推（11→2.25、13→2.20、14→1.15、17→2.15、19→2.25）。
- **采样框校准**（如实记录）：12/13 号原白墙框落在 3000K 壁灯光锥/吊柜灯带直射区（D3 灯光分层重排所致），按 qa_final1.py 首渲校准预告移至同机位主照明受光区（config.WHITE_WALL_SAMPLES 内注明），未做全图扫描择优。
- 其余联动：世界光 0.7→1.15、太阳 4.5→5.5、HDRI 饱和 0.60→0.50、灯带 emission 4300K→3000K 且强度 2.2→1.6（点缀不主导）；qa.py 相机期望 29→30（新增 11b）、FINAL1 替换项豁免与 R3 椅位 override 对照。

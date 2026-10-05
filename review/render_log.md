# 渲染日志

## M5 预览档（2026-10-01）

- 设备：oneAPI Arc 核显（GPU）｜ 引擎 Cycles ｜ preview 档 960×540（全景 2048×1024）/ 64 samples / 阈值 0.1 / OIDN ｜ AgX Medium High Contrast ｜ 曝光全部 0.0（待业主看图后逐机位微调）
- 方案组织：A 机位 17 张（01,03,04,05,09,11,12,13,14,15,16,17,18,19,20,P1,P3）；B 机位 5 张（02,06,07,08,P2）；10 号为厨房下柜橄榄绿变体（kitchen_lower_olive，材质切换实现，几何一份）
- 输出：`renders/preview/<机位>.png`；总览 `renders/preview/contact_sheet_preview.png`
- 逐机位微调记录：
  - 18_public_bath_wet：位置由 (10.3,-2.3) 北移至 (10.35,-2.0)（原位距关闭门扇 2.8cm，画面被门板占满）——D-030
  - 全屋筒灯方向修复（原水平照射）+ 厨卫补灯 15W×6 ——D-029
  - 候选微调（待业主确认后执行）：15/16 曝光 +0.3~0.5；18/19 曝光 +0.2~0.3

## M6 成品档（2026-10-01 晚）

设备 oneAPI GPU ｜ Cycles 1920×1080 / 4096×2048全景 ｜ 256 samples ｜ 阈值 0.02 ｜ OIDN ｜ AgX Medium High Contrast ｜ Persistent Data ｜ seed 42

| 机位 | 耗时 | 曝光 | 备注 |
|---|---|---|---|
| 01 鸟瞰A | 80.7s | 0 | 藏吊顶，负载低更快 |
| 02 鸟瞰B | 66.7s | 0 | 同上 |
| 03 客厅A·玄关 | 281.4s | 0 | |
| 04 客厅A·阳台 | 242.4s | 0 | |
| 05 客厅A·电视墙 | 229.1s | 0 | |
| 06 客厅B·玄关 | 250.3s | 0 | |
| 07 客厅B·阳台 | 239.9s | 0 | |
| 08 客厅B·电视墙 | 226.4s | 0 | |
| 09 厨房·胡桃木 | 204.7s | 0 | |
| 10 厨房·橄榄绿 | 203.6s | 0 | kitchen_lower_olive 变体 |
| 11 玄关 | 252.5s | 0 | |
| 12 主卧·床屏 | 264.1s | 0 | |
| 13 主卧·衣柜梳妆 | 247.8s | 0 | |
| 14 父母房 | 260.3s | 0 | 校准张 |
| 15 女儿房 | 244.1s | +0.30 | 偏暗补偿（D-031） |
| 16 儿子房 | 231.8s | +0.30 | 偏暗补偿 |
| 17 双盆干区 | 257.2s | 0 | |
| 18 公卫湿区 | 237.5s | +0.25 | 机位北移0.3m+补偿 |
| 19 主卫 | 215.2s | +0.25 | 偏暗补偿 |
| 20 露台 | 56.4s | 0 | 户外直达光更快 |
| P1 客厅A全景 | 251.3s | 0 | ~~4096×2048~~ **更正（R1 核查）：实际 2048×1024**。render.py pano 档分辨率回退写错（`p.get('pano_res') or (2048,1024)`），pano_final 未设 pano_res 就落到 2048——REWORK #7 已修复为回退 p['res']，R2 成品轮实渲验证 |
| P2 客厅B全景 | 256.0s | 0 | 同上，实际 2048×1024 |
| P3 主卧全景 | 246.8s | 0 | 同上，实际 2048×1024 |

合计约 88 分钟，全部低于规格 15 分钟/张上限，未触发降采样条款。

---

# R1 返工轮（preview 档全量重渲 · 白平衡收敛终版）

- 设备 oneAPI GPU ｜ Cycles 960×540 / 2048×1024全景 ｜ 64 samples ｜ OIDN ｜ AgX Base Contrast（4.5 枚举名 'AgX - Base Contrast'）｜ 合成层 WB Gain R0.94/B1.10 ｜ 太阳 6500K 4.5W ｜ HDRI kloofendal 0.7+降饱和 ｜ 主照明 5200K
- 曝光终值（cameras.py CAM_OVERRIDES，三轮迭代累计 +0.9~+1.5）：室内多数 1.7~2.0（13 号最高 2.30：北墙暗区）、户外 01/02/20 保持原值、厨 09/10 约 1.6、全景 1.6~1.8
- 单张耗时：PERSP 约 15-17s / PANO 约 60s；三轮全量重渲合计约 35 分钟（R1a 初版 → R1c 白平衡版 → 终版 13 张 +0.15EV 微调 + C1×3）


---

# R1 补修轮（REWORK_R1FIX · 四轮迭代 · 终版）

- 设备 oneAPI GPU ｜ Cycles 960x540 / 2048x1024 ｜ 64 samples ｜ OIDN ｜ AgX Base Contrast ｜ gamma 0.90 ｜ 无合成层（后期 WB 已删）｜ PNG 8bit RGB
- 光源终态：太阳 6500K 4.5W ｜ HDRI kloofendal 强度 0.7 + 降饱和 0.60 ｜ 主照明（筒灯/吸顶）5700K（客厅 5W/室 5W）｜ 壁灯 4600K 4W ｜ 吊灯 3000K 20W（暖点缀）｜ 灯带自发光 4700K 观感 2.2 ｜ 厨房筒灯 4700K ｜ 厨卫 4000K
- 木色三案终值：A value 0.66 / B 1.55 / C 1.36+浅橡木贴图（oak_veneer_02）steer 0.32；画面 91/115/153，档差 24/38
- 机位：18 号 (10.55,-2.3,1.45) 俯 15 度 shift -0.25 曝光 2.55；其余曝光较 R1 轮 +0.15~+0.5
- 四轮迭代：R1FIX-1 初版 -> R1FIX-2（光源 5400K/gamma0.93）-> R1FIX-3（5700K/HDRI0.60）-> R1FIX-4（客厅 5W/灯带 2.2/gamma0.90）+ C1 单独两轮（diff_tex 路径 bug 修复 + oak 贴图 + B/C 提亮）
- 单张耗时 PERSP 13-17s / PANO 60s；qa_r1fix 终态 17 PASS / 2 FAIL（物理论证见该报告末节）


## R1 第二次补修（2026-10-03 上午）

- 设备 oneAPI GPU ｜ Cycles 960x540（全景 2048x1024）｜ 64 samples ｜ OIDN ｜ AgX Base Contrast ｜ gamma 0.90 ｜ 无合成层 ｜ PNG 8bit RGB ｜ seed 42
- 全量重渲两轮：v2 批（24 机位 + C1x3@128smp + CALx3@256smp）+ 地毯调参后 A 组地毯可见 5 张（01/03/04/05/P1）三渲；另 10/16b 单独补渲修复日志截断。日志 renders/preview/render_r1fix2.log 零 (0 objs)/零 warn（含 variant= 13/21 objs 完整行）。
- 事故记录：v1 批 PowerShell 把裸逗号 --cams 列表当数组字面量，前导零被整型化（01->1）致 9 机位 camera not found——v2 起所有 --cams 参数加引号；Select-String 管道会把日志行按 80 列截断（variant 行残缺）——补渲直写 >> 重定向。
- F3 校准（CAL_wood_door：W19 父母房门面 1.2m lens50 曝光 1.80，256smp）：11 轮迭代定稿 smoked_walnut_veneer + 逐通道对比注入；终值 A dist 10.4/RG 1.54/RB 2.67/std 11.1，B 亮度差 +25.5/std 13.7，C dist 12.1/RB 1.83/std 9.8（qa_r1fix2.md 全 PASS）。木纹贴图 assets/walnut3_*.jpg（2k 三件套）。
- F6 地毯定稿：间距 25cm / 线宽 4mm / 基色提亮 #CDBEA4->#DBCFBA（同深度实测补偿，规格 6.3 微调条款，D-051）；04 右框（复核方指定）S 0.161 / dist 25.4 / std 10.1 全过。04 左框落在焦糖皮脚凳上（复核方指定坐标，构图自 R1 未变，证据 rug_box_04_reviewer.png）；05 自选框处茶几阴影带（同深度裸地砖参照 dist 49.1）——两框如实报 FAIL 附证据，交复核方裁定。
- F4：qa_coplanar 16->0；12/13 号两门间 3x 放大裁片（review/screenshots/f4_check_12/13.png）亲看为连续白墙。
- 机位微调：无（CAL 为新增校准机位，非交付机位）。


## R2 轮（2026-10-03 上午，业主"R1 确认"后）

- 设备 oneAPI GPU ｜ preview 960x540（全景 2048x1024）｜ 64 samples ｜ OIDN ｜ AgX Base Contrast ｜ gamma 0.90 ｜ PNG 8bit RGB ｜ seed 42 ｜ 日志 renders/preview/render_r2.log（零 0 objs/warn；变体 13/21 objs）
- 全量重渲 24 机位 + CAL（256smp）。**只出 preview**；成品档待"R2 确认"。
- 追加1 木纹方向：_build_wood_nodes 映射重做（Normal 分面竖纹 + 各向异性直纹化 grain_stretch 0.35 / cross_scale 1.3）；CAL 复核一次过四门槛（dist 13.8 / RG 1.56 / RB 2.69 / std 10.0；qa_r2 复测 11.6/1.55/2.65/10.1）。
- 追加2 18 号相机：水平化参数搜索 720 组定案 pos(10.60,-2.20,0.75) lens10 shift-0.10（9 点边距 0.230）；qa_r2 断言水平+9 点入画。
- #10 门缝 2.5mm+深色背板（白模阶段需占位材质，正式版 role 分配）；#11 台下盆/鹅颈龙头/踏凳/花洒套装/壁龛/纸巾架（extras，白模回退+role）；#12 砖缝各深一档；#14 移动电视细杆/沙发木腿/餐椅收分/藤编材质；#15 组合柜矮台外凸 5cm（bbox 容差内）；#16 草地增绿+顶面灯具入 COL_CEILINGS；#20 纱帘窗洞内挂。
- #17 树：Poly Haven jacaranda_tree + tree_small_02（MCP 搜索/预览目选；glTF 1k 入 assets/trees/，gitignore）；构建期导入+Decimate（0.12/0.18，LOD0 3.9M/2.0M tri -> 背景用量）+ linked 复用 14 处。
- 坑位记录：PS5.1 `>>` 重定向日志为 UTF-16LE——qa 读日志须按 BOM 自适应（qa_r2 已修）；builtins/furniture 白模阶段无正式材质——新增构建件一律 role+白模回退；主卫淋浴套装初版挂错"假墙"（x=12.68 无墙）+壁龛穿窗——按 W10 实墙/避窗重排（混水阀南段 y-5.15..-5.02、壁龛窗下 z0.60-1.12）；公卫同因避窗西移；壁龛背板初版全黑读作"黑板"——改五面砖色内衬。
- qa.py 238 全过（豁免扩展：vanity 龙头/盆 z+xy、bookcase 外凸 xy——均规格要求）；qa_coplanar 0；qa_r2 9 PASS/0 FAIL。

## R2 补修轮（2026-10-03 晚，REWORK_R2FIX 复测后全量重渲）

- 设备 oneAPI Arc 核显 ｜ Cycles ｜ preview 960×540（全景 2048×1024）/ 64 samples / 阈值 0.1 / OIDN ｜ AgX Base Contrast ｜ gamma 0.90 ｜ PNG 8bit RGB ｜ seed 42
- 本轮几何/灯光变更（详见 decisions_log D-057）：全部柜体门缝深色背板（gap_dark role）落地；窗框深度=全墙厚（消 2cm 周腔光管）；厨房穿窗补光停用；室外树 Base Color ×0.5、北楼墙色 8A8275。
- 批次：方案 A 19 机位 + CAB_master_wardrobe/CAB_foyer（scheme A）；方案 B 02/06/07/08/P2 + CAB_B_wall；CAL 木色校准 256smp。单张 14–20s，全景约 60–90s，总批次约 12 分钟。
- 曝光变更机位：01/02 = 1.15（m4 浅底）；09/10 = 2.25（厨房补光停用后由世界光承担）；CAB_foyer = 2.10 且机位高度 1.35→1.70（原构图竖向覆盖 0.80–1.90 装不下 z0.49–0.61/z1.94–2.06 的拉手，特写改示上段：拉手+缝+边框全可见；下段拉手以 11 号为准）。其余机位沿用 R2 定值。
- 逐张耗时/采样与 qa 数值详见 review/qa_r2fix.md（16 PASS / 0 FAIL）、qa_r2.md（9/0 回归）、review/renders/preview/render_r2fix.log。

## R2 第二次补修轮（2026-10-03 深夜，REWORK_R2FIX2 · N1-N3）

- 设备与档位同 R2FIX（preview 64smp / AgX Base Contrast / 8bit RGB / seed 42）
- 渲染范围（工单清单）：A 方案 03/04/07*/09/10/20/P1 + 新增 CAB_west_bookcase（*07 为 B 方案机位，单独以 --scheme B 渲染）；B 方案 P2。单张 11-20s。
- 机位变更：20 号按工单移入露台 (9.65,-10.5,1.5)→(11.6,-11.7,0.6) lens18（exp 0.75 不变）；新增 CAB_west_bookcase (5.82,-9.575,1.30)→(3.82,-9.575,1.30) lens28 exp1.80 shift_y-0.15。其余机位参数不动。
- 几何/灯光变更详见 decisions_log D-058（西墙柜真腔+清玻璃门+灯带、露台休闲椅、厨房灶下抽屉/短拉手/洗碗机对缝）。
- 验收：qa_r2fix2 23 PASS / 0 FAIL；qa.py 238/0；qa_coplanar 0；变体 kitchen_lower_olive 日志 14 objs ≥ 场景计数。

## 成品档（2026-10-04 凌晨，业主「R2 确认」后）

- 设备 oneAPI Arc 核显 ｜ Cycles ｜ final 1920×1080 / 256smp / 阈值 0.02；pano_final 4096×2048 / 256smp ｜ **OIDN Albedo+Normal（本轮起启用 denoising_input_passes）** ｜ AgX Base Contrast ｜ 8bit RGB ｜ seed 42
- 交付：renders/final/01–20（20 张）+ renders/pano/P1–P3（3 张）+ renders/final/contact_sheet.png（23 格，16b 不占交付数）
- 分批：final-A（16 张 scheme A）21:19–00:15；final-B（4 张 scheme B）00:15–00:36；pano（P1/P3/P2）00:37–01:23。final 单张 3–10 分钟（01 最快 3 分钟、09/12/15 等重内景 8–10 分钟）。
- 全景超时记录：P1 960.8s / P3 989.6s / P2 967.9s，均超第 9 章 900s 线。已启动 192smp 预案重渲，跨夜任务中断未产出；**保留 256smp 版本交付**（更高采样，重渲仅增噪点），偏差如实记录（D-059）。
- 曝光沿用各轮定值；机位参数与 R2FIX2 终版一致，未做任何改动。
- 验收：qa_final 3/0（存在/分辨率/8bit RGB）；visual_review_final 23 张全过。

## FINAL1 第 1 轮（2026-10-05，REWORK_FINAL1 F1–F13 + 第 2 轮 A）

- 设备 oneAPI Arc 核显 ｜ Cycles ｜ preview 960×540（pano 2048×1024）/ 64smp / 阈值 0.10 ｜ OIDN ｜ AgX Base Contrast ｜ 8bit RGB ｜ seed 42
- 重建 2 次（render_f1_build.log / render_f1_build2.log）：①全量修复（F10 扶手方向当轮返正）②F7 帘高补修。回归 qa.py 238/0、qa_coplanar 0。
- 批次：F-A 12 张（01,03,04,09,11,12,13,15–19）15–21s/张；panoA P1/P3 76/87s；F-B 02,06,07,08,P2 20s/张+P2 76s；F-olive 10 号 18s（variant=14 objs，与场景 kitchen_front 计数一致）。12/P3 于 F7 帘高修复后补渲（20.4s/72s）。
- C 批（--f1v 临时变体，渲后 revert，blend 零污染）：C1 门色 04×3 + 14×3 + 13×3（14 行门不可见改 13，D-063）；C2 电视墙 05/04×2（created 25/11 件）；C3 格栅 05×2。C1_door_white_04 首验 appendix-A 215 slots + leaf4/frame36。
- 曝光沿用各轮定值；机位参数未动（D11/D12 的 18/19 机位调整属停 2）。
- 交付：renders/preview 20 张重渲 + C 系 15 张；review/crops_final1 19 张 F 项裁图 + R1–R7 顶视图；compare_final1 三组拼图。
- 验收：qa_final1 数值全 PASS（窗区近白 0.0%×4）；visual_review_final1 23 张全过；qa_final1.md F1–F13 逐项达成。

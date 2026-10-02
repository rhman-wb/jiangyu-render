# 渲染后检查（qa_render · preview 档）

白墙目标：sRGB 均值 200-225、R-B<=18（REWORK 2.5）；亮度 <185 或 R-B>18 -> WARN。

PASS  01_aerial_A
PASS  02_aerial_B
WARN  03_living_A_from_foyer：框1 亮度 175<185
WARN  04_living_A_from_balcony：框1 亮度 171<185
WARN  05_living_A_tv_wall：框1 亮度 169<185
WARN  06_living_B_from_foyer：框1 亮度 184<185
WARN  07_living_B_from_balcony：框1 亮度 173<185
WARN  08_living_B_tv_wall：框1 亮度 170<185；框1 R-B=19>18（偏黄）
PASS  09_kitchen_walnut
PASS  10_kitchen_olive
WARN  11_foyer：框1 亮度 180<185
PASS  12_master_bed_screen
WARN  13_master_wardrobe_vanity：框1 亮度 175<185；框2 R-B=23>18（偏黄）
PASS  14_parents_room
PASS  15_daughter_room
PASS  16_son_room
PASS  16b_son_room_blue
WARN  17_public_bath_dry：框1 亮度 170<185
PASS  18_public_bath_wet
WARN  19_master_bath：框1 亮度 176<185
PASS  20_terrace
WARN  P1_living_A_pano：框1 亮度 175<185
WARN  P2_living_B_pano：框1 亮度 184<185
PASS  P3_master_pano

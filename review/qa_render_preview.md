# 渲染后检查（qa_render · preview 档）

白墙目标：sRGB 亮度 >=185、R-B<=22（REWORK_R1FIX F3 阈值，删后期 WB 后木色回暖）；低于即 WARN。

PASS  01_aerial_A
PASS  02_aerial_B
WARN  03_living_A_from_foyer：框1 亮度 169<185；框1 R-B=24>22（偏黄）
WARN  04_living_A_from_balcony：框1 亮度 164<185；框1 R-B=31>22（偏黄）
WARN  05_living_A_tv_wall：框1 亮度 163<185；框1 R-B=30>22（偏黄）
WARN  06_living_B_from_foyer：框1 亮度 179<185
WARN  07_living_B_from_balcony：框1 亮度 166<185；框1 R-B=29>22（偏黄）
WARN  08_living_B_tv_wall：框1 亮度 163<185；框1 R-B=33>22（偏黄）
PASS  09_kitchen_walnut
PASS  10_kitchen_olive
WARN  11_foyer：框1 亮度 174<185；框1 R-B=26>22（偏黄）
WARN  12_master_bed_screen：框1 亮度 181<185
WARN  13_master_wardrobe_vanity：框1 亮度 168<185；框1 R-B=27>22（偏黄）；框2 亮度 180<185；框2 R-B=33>22（偏黄）
PASS  14_parents_room
PASS  15_daughter_room
PASS  16_son_room
PASS  16b_son_room_blue
WARN  17_public_bath_dry：框1 亮度 160<185；框1 R-B=26>22（偏黄）
WARN  18_public_bath_wet：框1 亮度 144<185；框1 R-B=26>22（偏黄）
WARN  19_master_bath：框1 亮度 170<185
PASS  20_terrace
WARN  P1_living_A_pano：框1 亮度 168<185；框1 R-B=26>22（偏黄）
WARN  P2_living_B_pano：框1 亮度 178<185
WARN  P3_master_pano：框1 亮度 183<185

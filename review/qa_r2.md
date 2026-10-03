# R2 轮客观验收（qa_r2）

blend: D:\ClaudeCodeProject2026\jiangyu-render\blend\jiangyu.blend

- **PASS** 渲染日志零 (0 objs)/warn/assert（render_r2.log）
- **PASS** 变体 kitchen_lower_olive 日志替换 13 >= 期望 13
- **PASS** 变体 son_blue 日志替换 21 >= 期望 21
- **PASS** F3-A（竖纹重映射后）avg(93,60,35) 距(96,63,46) 11.6<=25、R/G 1.55>=1.35、R/B 2.65>=1.8、std 10.1>=9
- **PASS** F4 qa_coplanar 重合面清单为空（71 墙段对象）
- **PASS** F6 回归 04 右框 S=0.15<=0.22、距#CDBEA4 21.7<=30、std 10.4<=12
- **PASS** 追加2 18 号相机水平（rotation.x=90°，无俯仰）
- **PASS** 追加2 18 号 9 点投影全部入画（9 点）
- **PASS** PNG 全部 8bit RGB（colortype=2）

汇总: PASS 9 / FAIL 0

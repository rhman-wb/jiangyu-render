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

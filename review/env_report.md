# 环境与设备报告（M0）

日期：2026-10-01 ｜ 结论：**环境全部就绪，渲染设备定为 oneAPI GPU（核显）**

## 1. 基础环境
| 项目 | 值 |
|---|---|
| 操作系统 | Windows 11 Home 64 位 (26200) |
| Blender | **4.5.10 LTS**，`C:\Program Files\Blender Foundation\Blender 4.5\blender.exe` |
| 运行方式 | Claude Code + mcp-for-blender（uvx 0.8.3） |
| CPU | Intel Core Ultra 7 155H（22 线程可用于渲染） |
| GPU | Intel Arc Graphics 核显（Meteor Lake，共享显存 ~15.8GB） |
| GPU 驱动 | **32.0.101.9033**（注：CLAUDE.md 第 1 章表格里的 32.0.101.5768 是修复前的旧驱动；2026-10-01 业主手动升级 WHQL 包后 oneAPI Level Zero 栈修复，ze_loader 1.32.0。测速在新驱动下完成） |

## 2. MCP 与资源
- MCP 插件 blender_mcp v1.8，protocol 13，up_to_date=True；TCP 9876 连接正常。
- 启动方式：Blender GUI 挂 `scripts/mcp_autostart.py` 自动开 Server（见 decisions_log D-001）。
- **Poly Haven：可用**（集成开关已打开）。注意该开关是场景级属性，重建场景后需重设（D-004）。
- 不使用 Sketchfab / AI 生成模型（规格 6.4）。

## 3. Cycles 设备测速（M0 正式对比）
- 方法：`scripts/m0_bench.py`，无头运行，同一脚本化测试场景（含窗玻璃、多次反弹、发光灯带、OIDN 降噪），960×540 / 64 samples / 噪波阈值 0.1，计时顺序 CPU → GPU 冷 → GPU 热。原始数据 `review/m0_bench.json`。
- 结果：

| 设备 | 耗时 | 相对 |
|---|---|---|
| CPU（22 线程） | 50.3 s | 1.0× |
| GPU oneAPI（冷启动，含设备初始化） | 11.8 s | 4.2× |
| GPU oneAPI（热跑） | 14.0 s | 3.6× |

- **结论：`RENDER_DEVICE = 'GPU'`**（config.py）。核显共享内存调度有 ±20% 波动（冷快于热属正常），但都数量级领先 CPU。
- 粗估（仅量级参考）：final 档（1920×1080 / 256spp）负载约为本次测速的 20 倍，单张约 4–8 分钟，符合规格第 9 章"超 15 分钟先降采样"的冗余。

## 4. 渲染设备启用方式（供脚本引用）
```python
prefs = bpy.context.preferences.addons['cycles'].preferences
prefs.compute_device_type = 'ONEAPI'
prefs.get_devices()          # 4.5 返回 None，仅刷新；真源在 prefs.devices
for d in prefs.devices:
    d.use = (d.type == 'ONEAPI')
scene.cycles.device = 'GPU'
```

## 5. 遗留与注意
- oneAPI 长时间渲染的驱动稳定性未知：render.py 按机位逐张起新进程（每次一个 blender 实例）以隔离风险。
- 本报告与 m0_bench.json、decisions_log D-001~D-006 同批提交（git: M0 commit）。

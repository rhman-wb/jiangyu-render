# 启动 Blender 后自动开启 MCP for Blender 的 socket server（TCP 9876）
# 用法: blender --python mcp_autostart.py
# 说明: 正常情况下 blender --python 脚本在插件注册之后执行,直接调用即可;
#       若个别情况下插件注册更晚,用 timer 每秒重试最多 10 次。
import bpy


def _try_start():
    try:
        bpy.ops.blendermcp.start_server()
        print("[mcp_autostart] MCP server started on port 9876")
        return True
    except Exception as e:
        print("[mcp_autostart] start failed:", repr(e))
        return False


if not _try_start():
    state = {"n": 0}

    def _retry():
        if state["n"] >= 10:
            print("[mcp_autostart] gave up after 10 retries")
            return None
        state["n"] += 1
        if _try_start():
            return None
        return 1.0

    bpy.app.timers.register(_retry)

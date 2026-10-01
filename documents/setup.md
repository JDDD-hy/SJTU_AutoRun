# AutoRun 复现指南

环境：Windows、雷电模拟器 9、Python 3.9；已验证交我办 3.6.4。先在模拟器中安装应用并自行登录。

本版精简了依赖：只保留 OpenCV contrib，移除未使用的 OCR 等包，限制 NumPy `<2`；新增依赖版本快照和离线检查。路线执行仍使用原项目代码。

## 1. 安装

交我办目前无法直接下载，可从 [APK 下载页](https://github.com/JDDD-hy/SJTU_AutoRun/releases/tag/jwb-apk-3.6.4) 获取 3.6.4 安装包，再导入雷电模拟器安装并登录。下载页同时提供 SHA-256 校验文件。

在仓库根目录的 PowerShell 中执行，需要已安装 Conda。每条命令成功后再执行下一条；不要覆盖已有环境。

```powershell
conda create --prefix .\.venv python=3.9.25 pip -y
.\.venv\python.exe -m pip install -r requirements-lock.txt
.\.venv\python.exe -m pip install -e .
.\.venv\python.exe -m pip check
.\.venv\python.exe check_env.py
```

这里使用 Conda 环境，解释器为 `.venv\python.exe`；标准 venv 的路径通常是 `.venv\Scripts\python.exe`。

## 2. 配置

编辑 `sjtuautorun/data/default_settings.yaml`，保留其他字段：

```yaml
emulator:
  emulator_dir: "" # 自动读取雷电安装位置；失败时在本地填 dnplayer.exe 完整路径
  emulator_name: emulator-5554
PLAN_ROOT:
plan: "宣怀大道" # 路线文件名，不带 .yaml
```

默认路线目录为 `sjtuautorun/data/plans/`。自定义路线按以下结构保存，经纬度点需自行填写，至少两个：

```yaml
speed: [5.0, 5.0] # 分钟/公里，4 km 理论上约 20 分钟
locating_error: 15 # 每轴随机偏移上限为 15 × 0.000001 度，不是 15 米
mode: single_trip
points: [] # 每项为 [经度, 纬度]；填写完整路线后才能运行
```

`single_trip` 将点列表执行一次；`circular` 和 `back-and-forth` 会持续循环。路线已包含返程时仍用 `single_trip`。脚本在相邻点间直线插值，需要保留转弯点。抖动和应用采样会使显示配速、里程与理论值有所不同。

已提供[法国帕莱索约 4 km 路线](../sjtuautorun/data/plans/palaiseau-4km.yaml)：253 个点，包含完整返程，配速 5 分钟/km、抖动 15。使用时将主配置改为 `plan: "palaiseau-4km"`，保持 `PLAN_ROOT` 留空；路线模式为 `single_trip`，执行一次往返后停止。

## 3. 启动与结束

以下入口自动识别起跑前确认，并在路线完成后点击暂停、长按结束。把代码保存为根目录 `run_selected_route.py`：

```python
import os

from sjtuautorun.constants.data_roots import DATA_ROOT
from sjtuautorun.mygo import RunPlan
from sjtuautorun.scripts.main import start_script_emulator

timer = start_script_emulator(None)
timer.config.PLAN_ROOT = timer.config.PLAN_ROOT or os.path.join(DATA_ROOT, "plans")
plan = RunPlan(timer)
if plan.plan_args["mode"] != "single_trip":
    raise ValueError("Use single_trip for this launcher")
print("Plan:", timer.config.plan, "Pace:", plan.plan_args["speed"])
plan.start_run()
result = plan.finish_run()
print("App result:" if result["confirmed"] else "Check recording in the app:")
print(result["text"] if result["confirmed"] else result["error"])
print("Screenshot:", result["screenshot"])
input("Press Enter to close: ")
if not result["confirmed"]:
    raise SystemExit(1)
```

1. 确认旧脚本已退出，打开模拟器和应用。
2. 执行 `.\.venv\python.exe -u run_selected_route.py`，等待终端提示。
3. 60 秒内进入“运动健康”或跑步页面；脚本依次识别“去跑步 → 好的 → 好的 → 开始跑步”，缺席的确认页直接跳过。
4. 确认应用计时、里程增长；路线完成后脚本自动点击暂停、长按结束 3.5 秒。
5. 查看终端的应用结果 OCR 原文和结果截图；窗口等待回车后退出。识别失败时需在应用中核实并手动处理。

Windows OCR 需要系统已安装相应语言的识别组件。纯按键实机测试已通过；完整路线结束后的正式结果页 OCR 仍待实机验证。短记录“不计入成绩”提示在正式模式下留给使用者确认，不会自动丢弃。

中途停止用脚本终端的 Ctrl+C。**停止脚本不会结束应用记录**，也不要同时运行两份定位脚本。

## 4. 常见问题

| 问题 | 处理 |
| --- | --- |
| 雷电模拟器无法联网 | 关闭雷电模拟器中的“虚拟服务”，重启模拟器后重新检查联网 |
| 起跑识别超时、找不到按钮 | 查看日志截图；必要时把 `plan.start_run()` 替换为先设置首点、手动开始计时并回车、再调用 `plan.run()` |
| `Minicap setup up failed` | 本次验证中报错后仍可取得截图并执行路线；结合后续连接状态和实际里程判断，未根治该错误 |
| 改了路线却仍运行旧路线 | 检查 `plan`、`PLAN_ROOT` 和实际加载的 YAML |
| 起点错误 | 先设首点、等地图更新，再开始应用计时 |
| 依赖或 Python 版本冲突 | 使用项目独立环境和明确的解释器路径，重新执行两项检查 |
| 多开时离线检查失败 | `check_env.py` 当前限定 `emulator-5554`；多开需调整检查并核实实际设备 |

`pip check` 与 `check_env.py` 已通过。离线检查覆盖导入、OpenCV、模板图像、内置路线及距离计算，不代表应用自动导航或记录认可规则已验证。

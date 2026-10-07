# 交我润 (SJTU_AutoRun)

## 项目简介

基于雷电模拟器的上海交通大学自动跑步脚本，脱胎于[AutoWSGR](https://github.com/huan-yp/Auto-WSGR)

## 使用方法

安装、配置、起跑与排障见[复现指南](documents/setup.md)。`RunPlan.start_run()` 支持识别跑步前的确认弹窗和起跑按钮；确认页缺席时直接继续，检测到暂停按钮后推进路线。路线完成后调用 `RunPlan.finish_run()`，自动点击暂停、长按结束 3.5 秒，并通过 Windows OCR 核实结果页。离线流程检查：`python test_auto_confirm.py`、`python test_auto_finish.py`。


`route_for_distance()` 可按目标距离调整配置中的路线，配合 `random.uniform(4.05, 4.30)` 实现每次 4.05–4.30 km 的计划距离浮动；用法见复现指南。原路线文件不变，必要时沿原路回走。离线检查：`python test_route_distance.py`。

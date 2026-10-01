# 交我润 (SJTU_AutoRun)

## 项目简介

基于雷电模拟器的上海交通大学自动跑步脚本，脱胎于[AutoWSGR](https://github.com/huan-yp/Auto-WSGR)

## 使用方法

安装、配置、起跑与排障见[复现指南](documents/setup.md)。`RunPlan.start_run()` 支持识别跑步前的确认弹窗和起跑按钮；确认页缺席时直接继续，检测到暂停按钮后推进路线。路线完成后调用 `RunPlan.finish_run()`，自动点击暂停、长按结束 3.5 秒，并通过 Windows OCR 核实结果页。离线流程检查：`python test_auto_confirm.py`、`python test_auto_finish.py`。


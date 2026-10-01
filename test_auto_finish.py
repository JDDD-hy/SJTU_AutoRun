"""Offline finish checks: long-press coordinates, result verification, and failures."""
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import cv2
import numpy as np

from sjtuautorun.constants.custom_exceptions import CriticalErr
from sjtuautorun.constants.data_roots import DATA_ROOT
from sjtuautorun.constants.image_templates import IMG
from sjtuautorun.controller.android_controller import AndroidController
from sjtuautorun.mygo import RunPlan
from sjtuautorun.utils.api_image import locateCenterOnImage
from sjtuautorun.utils.run_result import is_run_result, read_result_screen


def main():
    controller = AndroidController.__new__(AndroidController)
    controller.resolution = (1080, 1920)
    controller.config = SimpleNamespace(SHOW_ANDROID_INPUT=False)
    controller.ShellCmd = Mock()
    controller.long_tap(480, 450, duration=3.5, delay=0)
    controller.ShellCmd.assert_called_once_with("input swipe 540 1600 540 1600 3500")
    actual = "实际跑步\n4.01公里\n计入成绩\n4.00公里\n时长\n00:20:31\n平均配速\n5′07″/公里"
    assert is_run_result(actual)
    assert not is_run_result("跑步\n4.00公里\n暂停\n长按结束")
    assert not is_run_result("运动健康\n总公里\n13.94")
    assert not is_run_result("用于记录运动数据\n好的")
    with patch("sjtuautorun.utils.run_result.subprocess.run", return_value=SimpleNamespace(stdout='["实际 跑步","4.01 公里"]')):
        assert read_result_screen("test.png") == "实际跑步\n4.01公里"

    for case in ("success", "already_paused", "no_button", "still_running", "ocr_failure", "unknown_result", "short_test", "short_blocked"):
        clock = [0.0]
        def exists(template, *args):
            if template is IMG.auto_finish_image["short_run_warning"]:
                return case.startswith("short_") and clock[0] < 2
            if template is IMG.run_image[1]:
                return case == "short_test" and clock[0] >= 2
            return case == "still_running"
        timer = SimpleNamespace(
            config=SimpleNamespace(PLAN_ROOT=str(Path(DATA_ROOT) / "plans"), plan="default", log_dir="test-log"),
            update_screen=Mock(), screen=np.zeros((1920, 1080, 3), dtype=np.uint8), logger=Mock(),
            Android=SimpleNamespace(click=Mock(), long_tap=Mock()), log_screen=Mock(),
            get_image_position=Mock(return_value=None if case == "already_paused" else (480, 450)),
            wait_image=Mock(return_value=False if case == "no_button" else (480, 450)),
            image_exist=Mock(side_effect=exists))
        plan = RunPlan(timer)
        actions = Mock()
        actions.attach_mock(timer.Android.click, "pause")
        actions.attach_mock(timer.Android.long_tap, "hold_end")
        with patch("sjtuautorun.mygo.run_plan.time.monotonic", side_effect=lambda: clock[0]), \
                patch("sjtuautorun.mygo.run_plan.time.sleep", side_effect=lambda t: clock.__setitem__(0, clock[0] + t)), \
                patch("sjtuautorun.mygo.run_plan.read_result_screen", return_value=actual if case != "unknown_result" else "运动健康",
                      side_effect=subprocess.TimeoutExpired("OCR", 2) if case == "ocr_failure" else None) as ocr:
            try:
                result = plan.finish_run(timeout=3, allow_short_test=case == "short_test")
            except CriticalErr:
                assert case == "no_button"
                timer.Android.long_tap.assert_not_called()
                timer.log_screen.assert_called_once()
            else:
                assert result["confirmed"] == (case in ("success", "already_paused", "short_test")), case
                timer.Android.long_tap.assert_called_once_with(480, 450, duration=3.5)
                assert [action[0] for action in actions.mock_calls] == (
                    ["hold_end"] if case == "already_paused" else
                    ["pause", "hold_end", "pause"] if case == "short_test" else ["pause", "hold_end"])
                if case in ("still_running", "short_test", "short_blocked"):
                    ocr.assert_not_called()
                if case == "short_test":
                    assert result["discarded"]
                if case == "already_paused":
                    timer.Android.click.assert_not_called()

    source = cv2.imread(str(Path(DATA_ROOT) / "images/auto_finish_image/end_screen.png"))
    frame = np.full((960, 540, 3), 255, dtype=np.uint8)
    frame[700:700 + source.shape[0], 200:200 + source.shape[1]] = source
    assert locateCenterOnImage(frame, IMG.auto_finish_image["end_button"], 0.9) is not None
    source = cv2.imread(str(Path(DATA_ROOT) / "images/auto_finish_image/pause_screen.png"))
    frame[:] = 255
    frame[700:700 + source.shape[0], 200:200 + source.shape[1]] = source
    pause = locateCenterOnImage(frame, IMG.auto_finish_image["pause_button"], 0.9)
    assert pause and abs(pause[0] - 275) < 3 and abs(pause[1] - 766) < 3
    from sjtuautorun.mygo.run_plan import PAUSE_IMAGES
    timer = SimpleNamespace(config=SimpleNamespace(PLAN_ROOT=str(Path(DATA_ROOT) / "plans"), plan="default"),
                            change_location=Mock(), update_screen=Mock(), logger=Mock(),
                            image_exist=lambda images, *args: images is PAUSE_IMAGES,
                            get_image_position=Mock(return_value=None))
    plan = RunPlan(timer)
    plan.run = Mock()
    plan.start_run(run_route=False)
    timer.change_location.assert_not_called()
    plan.run.assert_not_called()
    print("PASS: 3.5-second hold, native coordinates, result-only summary, failure paths, and end template.")


if __name__ == "__main__":
    main()

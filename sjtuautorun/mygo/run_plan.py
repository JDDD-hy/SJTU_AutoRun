import os
import random
import subprocess
import time
import numpy as np

from sjtuautorun.constants.custom_exceptions import CriticalErr, ImageNotFoundErr
from sjtuautorun.constants.data_roots import DATA_ROOT
from sjtuautorun.controller.run_timer import Timer
from sjtuautorun.utils.io import yaml_to_dict, recursive_dict_update
from sjtuautorun.utils.math_functions import calculate_geo_distance
from sjtuautorun.constants.image_templates import IMG
from sjtuautorun.utils.run_result import read_result_screen, is_run_result, is_sports_home

PAUSE_IMAGES = [IMG.run_image[2], IMG.auto_finish_image["pause_button"]]


class RunPlan:
    def __init__(self, timer: Timer):
        self.timer = timer
        self.config = timer.config

        plan_args = yaml_to_dict(os.path.join(self.config.PLAN_ROOT, "default.yaml"))
        if self.config.plan is None:
            self.timer.logger.warning(f"No run plan specified, default plan "
                                      f"{os.path.join(self.config.PLAN_ROOT, 'default.yaml')} will be used")
        else:
            user_plan = yaml_to_dict(os.path.join(self.config.PLAN_ROOT, self.config.plan + ".yaml"))
            plan_args = recursive_dict_update(plan_args, user_plan)

        self.plan_args = plan_args
        assert len(plan_args["points"]) >= 2, "请输入两个以上途径点"

    def start_run(self, timeout=60, run_route=True):
        # 初始化位置
        if run_route:
            self.timer.change_location(self.plan_args["points"][0][0], self.plan_args["points"][0][1])

        deadline = time.monotonic() + timeout
        start_clicked = False
        go_clicked = False
        last_click = None
        last_click_time = float("-inf")
        while time.monotonic() < deadline:
            self.timer.update_screen()
            # Permission dialogs take priority over buttons visible behind them.
            pos = None
            state = None
            permission_titles = [IMG.auto_confirm_image["permission_title"],
                                 IMG.auto_confirm_image["permission_title_live"]]
            on_run_page = self.timer.image_exist(IMG.auto_confirm_image["run_page_title"], 0, 0.9)
            if self.timer.image_exist(permission_titles, 0, 0.9):
                pos = self.timer.get_image_position(IMG.auto_confirm_image["permission_ok"], 0, 0.9)
                state = "permission"
            else:
                # Both app confirmations use 好的; require the running-page heading.
                if on_run_page:
                    pos = self.timer.get_image_position(IMG.auto_confirm_image["permission_ok"], 0, 0.9)
                    state = "permission" if pos else None
                # Keep the existing Android permission template; unknown dialogs time out.
                if not pos:
                    pos = self.timer.get_image_position(IMG.confirm_image[3], 0, 0.9)
                    state = "allow" if pos else None
                if not pos and self.timer.image_exist(PAUSE_IMAGES, 0, 0.9):
                    self.timer.logger.info("Running screen detected.")
                    if run_route:
                        self.run()
                    return
                if not pos and not start_clicked:
                    pos = self.timer.get_image_position(IMG.run_image[1], 0, 0.9)
                    state = "start" if pos else None
                if not pos and not on_run_page and not go_clicked and not start_clicked:
                    pos = self.timer.get_image_position(IMG.start_image[3], 0, 0.9)
                    state = "go_running" if pos else None

            # Debounce slow transitions; identical consecutive dialogs may need another click.
            click = (state, pos) if pos else None
            if click and (click != last_click or time.monotonic() - last_click_time >= 2):
                self.timer.logger.info(f"Auto start: clicking {state} at {pos}")
                self.timer.Android.click(*pos)
                last_click_time = time.monotonic()
                if state == "start":
                    start_clicked = True
                elif state == "go_running":
                    go_clicked = True
            last_click = click
            time.sleep(0.25)

        self.timer.log_screen()
        raise CriticalErr("Auto start timed out: no recognized running screen. Check the saved screenshot.")

    def finish_run(self, hold_seconds=3.5, timeout=30, allow_short_test=False):
        """Pause, hold the detected end button, and verify the app's result page."""
        if not 0.2 < hold_seconds <= 15:
            raise ValueError("End hold must be greater than 0.2 and at most 15 seconds")
        self.timer.update_screen()
        pause = self.timer.get_image_position(PAUSE_IMAGES, 0, 0.9)
        if pause:
            self.timer.Android.click(*pause)
        end = self.timer.wait_image([IMG.run_image[4], IMG.auto_finish_image["end_button"]],
                                    confidence=0.9, timeout=10)
        if not end:
            self.timer.log_screen()
            raise CriticalErr("Cannot recognize end button; finish the recording manually.")
        self.timer.logger.info(f"Auto finish: holding {end} for {hold_seconds} seconds")
        self.timer.Android.long_tap(*end, duration=hold_seconds)
        deadline = time.monotonic() + timeout
        path = os.path.join(self.config.log_dir, "run-result.png")
        result = {"confirmed": False, "discarded": False, "text": "", "screenshot": path, "error": ""}
        short_confirmed = False
        while time.monotonic() < deadline:
            time.sleep(1)
            self.timer.update_screen()
            self.timer.logger.log_image(self.timer.screen, "run-result.png", ignore_existed_image=True)
            if self.timer.image_exist(IMG.auto_finish_image["short_run_warning"], 0, 0.9):
                if not allow_short_test:
                    result["error"] = "应用提示距离过短、不计入成绩，请手动核实是否结束。"
                    return result
                if not short_confirmed:
                    confirm = self.timer.get_image_position(IMG.auto_finish_image["confirm_short_run"], 0, 0.9)
                    if confirm:
                        self.timer.Android.click(*confirm)
                        self.timer.logger.info("Button test: confirmed ending the short, uncredited record.")
                        short_confirmed = True
                continue
            if self.timer.image_exist([*PAUSE_IMAGES, IMG.run_image[4],
                                       IMG.auto_finish_image["end_button"]], 0, 0.9):
                continue
            if short_confirmed and self.timer.image_exist(IMG.run_image[1], 0, 0.9):
                result.update(confirmed=True, discarded=True, text="")
                self.timer.logger.info("Button test finished; returned to the start screen.")
                return result
            try:
                result["text"] = read_result_screen(path, timeout=max(1, min(15, deadline - time.monotonic())))
            except (OSError, ValueError, TimeoutError, subprocess.SubprocessError) as exc:
                result["error"] = str(exc)
                return result
            if is_run_result(result["text"]):
                result["confirmed"] = True
                self.timer.logger.info("Result page detected; recording has ended.")
                return result
            if short_confirmed and is_sports_home(result["text"]):
                result.update(confirmed=True, discarded=True, text="")
                self.timer.logger.info("Button test finished; returned to sports home without a credited result.")
                return result
        result["error"] = "未识别到结果页，请在应用中核实是否已结束。"
        return result

    def run(self):
        time.sleep(self.config.DELAY)

        while True:
            for i in range(len(self.plan_args["points"]) - 1):
                start_longitude = self.plan_args["points"][i][0]
                end_longitude = self.plan_args["points"][i + 1][0]
                start_latitude = self.plan_args["points"][i][1]
                end_latitude = self.plan_args["points"][i + 1][1]

                self.AtoB(start_longitude, end_longitude, start_latitude, end_latitude)

            if self.plan_args["mode"] == 'circular':
                start_longitude = self.plan_args["points"][-1][0]
                end_longitude = self.plan_args["points"][0][0]
                start_latitude = self.plan_args["points"][-1][1]
                end_latitude = self.plan_args["points"][0][1]

                self.AtoB(start_longitude, end_longitude, start_latitude, end_latitude)

            elif self.plan_args["mode"] == 'back-and-forth':
                for i in range(len(self.plan_args["points"]) - 1, 0, -1):
                    start_longitude = self.plan_args["points"][i][0]
                    end_longitude = self.plan_args["points"][i - 1][0]
                    start_latitude = self.plan_args["points"][i][1]
                    end_latitude = self.plan_args["points"][i - 1][1]

                    self.AtoB(start_longitude, end_longitude, start_latitude, end_latitude)

            elif self.plan_args["mode"] == 'single_trip':
                break

            else:
                self.timer.logger.warning("Unknown \"mode\" config in run plan, defaulting to single_trip")
                break

    def AtoB(self, start_longitude, end_longitude, start_latitude, end_latitude):
        self.timer.change_location(start_longitude, start_latitude)

        total_distance = calculate_geo_distance(start_latitude, start_longitude, end_latitude, end_longitude)
        interval = 0.25
        running_pace = random.uniform(self.plan_args["speed"][0], self.plan_args["speed"][1])
        step_distance = 1000 * interval / (60 * running_pace)
        num_steps = round(total_distance / step_distance)

        location_update_index = 0

        for j in range(1, num_steps):
            start_time = time.time()

            rand1 = random.uniform(-0.000001 * self.plan_args["locating_error"],
                                   0.000001 * self.plan_args["locating_error"])
            rand2 = random.uniform(-0.000001 * self.plan_args["locating_error"],
                                   0.000001 * self.plan_args["locating_error"])

            # 计算经纬度的插值
            current_longitude = np.interp(j, [1, num_steps - 1], [start_longitude, end_longitude]) + rand1
            current_latitude = np.interp(j, [1, num_steps - 1], [start_latitude, end_latitude]) + rand2

            # 调用位置变更函数
            if location_update_index >= random.randint(0, 9) or j == num_steps - 1:
                self.timer.change_location(current_longitude, current_latitude)
                self.timer.logger.debug(current_longitude, current_latitude)
                location_update_index = 0
            else:
                location_update_index += 1

            # 等待
            elapsed_time = time.time() - start_time
            time.sleep(max(0.0, interval - elapsed_time))

        self.timer.change_location(end_longitude, end_latitude)

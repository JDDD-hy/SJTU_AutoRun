from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
from sjtuautorun.constants.custom_exceptions import CriticalErr
from sjtuautorun.constants.data_roots import DATA_ROOT
from sjtuautorun.constants.image_templates import IMG
from sjtuautorun.mygo import RunPlan


def check_auto_start():
    """Exercise the real start loop without moving the emulator or recording a run."""
    templates = {
        "title": IMG.auto_confirm_image["permission_title"],
        "title_live": IMG.auto_confirm_image["permission_title_live"],
        "run_page": IMG.auto_confirm_image["run_page_title"],
        "permission": IMG.auto_confirm_image["permission_ok"],
        "allow": IMG.confirm_image[3],
        "start": IMG.run_image[1], "running": IMG.run_image[2],
        "go_running": IMG.start_image[3],
    }
    scenarios = [
        ([{"go_running"}, {"title_live", "permission"}, set(),
          {"run_page", "permission"}, {"start"}, {"running"}],
         ["go_running", "permission", "permission", "start", "run"]),
        ([{"go_running"}, {"start"}, {"running"}], ["go_running", "start", "run"]),
        ([{"permission"}], []),  # Never click 好的 outside the recognized run page.
        ([{"title", "permission", "start"}, {"allow"}, {"start"}, {"running"}],
         ["permission", "allow", "start", "run"]),
        ([{"start"}, {"running"}], ["start", "run"]),
        ([{"running"}], ["run"]),
        ([{"start"}, {"title", "permission"}, {"allow"}, {"running"}],
         ["start", "permission", "allow", "run"]),
        ([{"title", "permission"}] * 3 + [{"running"}], ["permission", "run"]),
        ([{"title", "permission"}] * 10 + [{"running"}], ["permission", "permission", "run"]),
        ([set()], []),
        ([{"title", "running"}], []),  # An incomplete dialog must not fall through.
        ([{"start"}], ["start"]),  # Never click start twice or move before running.
    ]
    for screens, expected in scenarios:
        clock = [0.0]
        events = []
        def find(template, *args):
            if isinstance(template, list):
                return next((pos for item in template if (pos := find(item, *args))), None)
            name = next(name for name, value in templates.items() if value is template)
            frame = screens[min(int(round(clock[0] / 0.25)), len(screens) - 1)]
            return (list(templates).index(name) + 1, 20) if name in frame else None
        def click(x, y):
            events.append(list(templates)[x - 1])
        timer = SimpleNamespace(
            config=SimpleNamespace(PLAN_ROOT=str(Path(DATA_ROOT) / "plans"),
                                   plan="default", DELAY=0),
            logger=Mock(), Android=SimpleNamespace(click=click), change_location=Mock(),
            update_screen=Mock(), get_image_position=find, image_exist=find, log_screen=Mock())
        plan = RunPlan(timer)
        plan.run = lambda: events.append("run")
        with patch("sjtuautorun.mygo.run_plan.time.monotonic", side_effect=lambda: clock[0]), \
                patch("sjtuautorun.mygo.run_plan.time.sleep", side_effect=lambda t: clock.__setitem__(0, clock[0] + t)):
            try:
                plan.start_run(timeout=3)
            except CriticalErr:
                assert "run" not in expected
                timer.log_screen.assert_called_once()
            else:
                assert "run" in expected
                timer.log_screen.assert_not_called()
        assert events == expected, (screens, events, expected)
        timer.change_location.assert_called_once()


if __name__ == "__main__":
    check_auto_start()
    print("PASS: confirmations, skipped dialogs, start order, debounce, and timeout.")

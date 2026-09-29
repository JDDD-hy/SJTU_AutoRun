"""Offline installation check; does not start the emulator or the app."""
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np
import sjtuautorun

from sjtuautorun.constants.data_roots import DATA_ROOT
from sjtuautorun.constants.image_templates import IMG
from sjtuautorun.mygo import RunPlan
from sjtuautorun.scripts.main import get_emulator_path, start_script
from sjtuautorun.utils.io import yaml_to_dict
from sjtuautorun.utils.math_functions import calculate_geo_distance


def main():
    root = Path(DATA_ROOT)
    settings = yaml_to_dict(root / "default_settings.yaml")
    assert settings["emulator"]["emulator_name"] == "emulator-5554"
    for group, count in {"start_image": 3, "setting_image": 4,
                         "confirm_image": 3, "run_image": 4}.items():
        templates = getattr(IMG, group)
        assert len(templates) > count, group
        for template in templates[1:count + 1]:
            assert template is not None, group
            assert template._imread().size > 0, template.filename
    plans = list((root / "plans").glob("*.yaml"))
    for path in plans:
        config = SimpleNamespace(PLAN_ROOT=str(root / "plans"), plan=path.stem)
        plan = RunPlan(SimpleNamespace(config=config))
        assert len(plan.plan_args["points"]) >= 2, path.name
    assert calculate_geo_distance(31, 121, 31, 121) == 0
    assert 110 < calculate_geo_distance(31, 121, 31.001, 121) < 112
    assert cv2.resize(np.zeros((4, 4, 3), dtype=np.uint8), (2, 2)).shape == (2, 2, 3)
    print(f"PASS: sjtuautorun {sjtuautorun.__version__}, imports, OpenCV, images, {len(plans)} plans.")
    print(f"LDPlayer registry path: {get_emulator_path() or 'NOT INSTALLED / NOT REGISTERED'}")
    print("Emulator connection and app operation have NOT been tested.")


if __name__ == "__main__":
    main()

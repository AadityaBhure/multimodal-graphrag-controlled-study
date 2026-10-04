"""Explicit seeding; no implicit torch import or environment mutation."""
import random

import numpy as np


def seed_everything(seed: int, *, torch_module=None) -> dict:
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed < 2**32:
        raise ValueError("Seed must be an integer in [0, 2**32)")
    random.seed(seed)
    np.random.seed(seed)
    seeded = ["python.random", "numpy"]
    if torch_module is not None:
        torch_module.manual_seed(seed)
        if torch_module.cuda.is_available():
            torch_module.cuda.manual_seed_all(seed)
        torch_module.use_deterministic_algorithms(True)
        torch_module.backends.cudnn.benchmark = False
        torch_module.backends.cudnn.deterministic = True
        seeded.append("torch")
    return {"seed": seed, "seeded": seeded,
            "limitations": "Does not change process hash seed or guarantee remote API/hardware determinism."}

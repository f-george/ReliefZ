"""Rebuild demo artifacts from the code in notebooks 01-03, using this Python environment.

These three notebooks contain ordinary Python only. Execute each in a fresh namespace
without a Jupyter server; the notebooks remain the single source of training logic.
Existing generated models/CSVs are replaced. Cached road graphs are left intact.
"""
import json
import os
from pathlib import Path

import matplotlib

ROOT = Path(__file__).resolve().parent.parent
NOTEBOOKS = ("01_synthetic_data.ipynb", "02_model1_risk.ipynb", "03_model2_action.ipynb")


def main():
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    previous_cwd = Path.cwd()
    try:
        os.chdir(ROOT)
        for name in NOTEBOOKS:
            path = ROOT / "notebooks" / name
            notebook = json.loads(path.read_text(encoding="utf-8"))
            namespace = {"__name__": "__main__", "__file__": str(path)}
            print(f"Running {name} ...", flush=True)
            for index, cell in enumerate(notebook["cells"]):
                if cell["cell_type"] == "code":
                    code = "".join(cell["source"])
                    exec(compile(code, f"{name}:cell-{index}", "exec"), namespace)
            plt.close("all")
        print("Demo models ready. Start with: python webui/app.py", flush=True)
    finally:
        os.chdir(previous_cwd)


if __name__ == "__main__":
    main()

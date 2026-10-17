# ReliefSync Z_IBM Z Datathon 2026 Project

**Team:** ReliefSync Z · **Theme:** Real-time AI for critical decisions ·

ReliefSync Z is a hybrid-AI decision-support system for disaster relief convoys, running on IBM LinuxONE. When a
flood, storm or landslide threatens a convoy's route, it:
1. scores the route risk in real time (Model 1);
2. recommends **continue**, **halt**, **reroute** or **divert to a backup hub** (Model 2);
3. computes safer routes on real OpenStreetMap roads;
4. explains the decision in plain language with IBM Granite.

A human dispatcher always makes the final call, and every decision is written to a tamper-evident audit log.

Everything is open source, and no data leaves the LinuxONE machine: no cloud APIs are used, not even for the language
model. See [OPEN_SOURCE.md](OPEN_SOURCE.md) for every library, model and dataset, with links and licences. The full
design is in `ReliefSync_Z_Detailed_Project_Summary-3.docx`.

## How it uses IBM LinuxONE

- **Runs on IBM Z:** everything runs on LinuxONE Community Cloud (s390x, big-endian), inside IBM's official
  Jupyter Lab ML container.
- **Trained there:** both ML models are trained on LinuxONE: scikit-learn Random Forests, benchmarked against XGBoost.
- **Local LLM:** IBM Granite runs on the same machine through llama.cpp. The container's build includes IBM's zDNN
  library, which can use the on-chip AI accelerator (NNPA) on z16 / LinuxONE 4 hardware.
- **Measured at scale:** notebook 06 measures how many convoy updates per second one instance can score.
- **Secure by design:** inference is local, the audit log is hash-chained, and the dispatcher dashboard is reached only
  through an encrypted SSH tunnel.

## What's in the repository

| Path | Contents |
|---|---|
| `notebooks/` | The pipeline as 7 Jupyter notebooks, run in order on LinuxONE (see step 3) |
| `webui/` | Interactive disaster simulator: Flask server + prebuilt React/Tailwind dashboard |
| `data/` | Cached OpenStreetMap road networks for Valencia, Spain and the Noto Peninsula, Japan |
| `OPEN_SOURCE.md` | Open-source credits required by the datathon rules |

Folders created on LinuxONE as you go: `artifacts/` (trained models, benchmark results) and `logs/` (audit log).

---

## Usage guide

You need:
- a **LinuxONE Community Cloud VM**: its public IP and the SSH key you got when registering. The VM user is `linux1`.
- a **laptop** with a terminal and a web browser.

In the commands below, replace `<key.pem>` with the path to your SSH key and `<IP>` with your VM's public IP. Don't
type the angle brackets: in a terminal, `<` and `>` redirect input and output.

### Step 1. Copy the project to LinuxONE

**Option A: clone from GitHub**, on the VM:

```bash
ssh -i <key.pem> linux1@<IP>
mkdir -p /home/linux1/shared && chmod a+w /home/linux1/shared
git clone <repo URL> /home/linux1/shared/ReliefZ
```

**Option B: copy an archive from your laptop.** Run this from the folder that *contains* your `ReliefZ` checkout. It
packs only the files LinuxONE needs (about 2 MB):

```bash
tar -czf ~/reliefz.tar.gz --exclude='node_modules' --exclude='__pycache__' \
  --exclude='.ipynb_checkpoints' --exclude='.pytest_cache' \
  ReliefZ/README.md ReliefZ/OPEN_SOURCE.md ReliefZ/notebooks \
  ReliefZ/data/road_graph.json ReliefZ/data/road_graph_noto.json ReliefZ/webui

scp -i <key.pem> ~/reliefz.tar.gz linux1@<IP>:~
```

The `:~` at the end matters: without the colon, `scp` makes a local copy instead of sending it to the server. Then,
on the VM:

```bash
ssh -i <key.pem> linux1@<IP>
mkdir -p /home/linux1/shared && chmod a+w /home/linux1/shared
tar -xzf ~/reliefz.tar.gz -C /home/linux1/shared
```

**After either option**, still on the VM, let the Jupyter container write into the project. It runs as a different
user from `linux1`:

```bash
chmod -R a+rwX /home/linux1/shared/ReliefZ
```

### Step 2. Start the Jupyter container

Skip this if your container is already running with `/home/linux1/shared` mounted. On the VM:

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker linux1 && newgrp docker
sudo systemctl start docker
docker pull registry.linuxone.cloud.marist.edu/l1cc/jupyterlab-image-s390x:latest
docker run --network host --name notebook -v /home/linux1/shared:/home/ibm-user/shared \
  -d registry.linuxone.cloud.marist.edu/l1cc/jupyterlab-image-s390x:latest
sudo iptables -I INPUT -p tcp --dport 38888 -j ACCEPT
```

If the container doesn't start, add `--security-opt seccomp=unconfined` to `docker run`.

Open **http://\<IP\>:38888** in your browser. The default token is `Your_Token1` unless you changed it. The project is
in `shared/ReliefZ`.

The container already has every library the notebooks need, including scikit-learn, XGBoost, llama.cpp and a Granite
model. There is nothing to install for the notebooks.

### Step 3. Run the notebooks

Run them **in order, 00 → 06**. Training happens here, on LinuxONE: the models must be built with the container's
library versions. The notebooks need no internet access.

- **In the browser** (best for screenshots): open each notebook in `shared/ReliefZ/notebooks/`, then
  **Run → Run All Cells**.
- **Or all at once from a terminal:** in Jupyter, **File → New → Terminal**:

  ```bash
  cd ~/shared/ReliefZ/notebooks
  for nb in 0*.ipynb; do jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=1800 "$nb"; done
  ```

| Notebook | What it does | What you should see |
|---|---|---|
| `00_environment_check` | Platform evidence and a readiness check | `s390x`, byte order `big`, `(matches container)` next to each library, `Running inside a container: True`, a `libggml-zdnn` library. The last cell, *Project readiness*, should have **no FAIL lines**. `nnpa: True` appears only on z16 / LinuxONE 4 hardware. |
| `01_synthetic_data` | Generates the synthetic training data | Risk-score and action-count charts |
| `02_model1_risk` | Trains the risk model (Random Forest) and the XGBoost benchmark | R² ≈ 0.98 (Random Forest) and ≈ 0.99 (XGBoost), plus single-update latency |
| `03_model2_action` | Trains the action model | Accuracy ≈ 0.96 (about 3,835 of 4,000 test decisions correct), confusion matrix, `Recommended: REROUTE` for the worked example |
| `04_routing` | Loads the Valencia road network and tests rerouting around a flood | `19265 nodes, 20301 edges` and a map of the fastest vs safer route |
| `05_live_pipeline_demo` | The live scenario: a flood hits, risk jumps, the system recommends, Granite explains, the decision is logged | Risk jumps from ≈ 0.03 to ≈ 0.98 → **REROUTE**. The explanation source names a Granite **`.gguf` file**, not "template". The audit log shows `OK` and the tampered copy `BROKEN`. |
| `06_scalability_benchmark` | Measures convoys scored per second | A throughput chart titled `... on s390x` and a summary starting `"machine": "s390x"` |

### Step 4. Start the web UI

The web UI is an interactive disaster simulator. Pick **Valencia, Spain** or the **Noto Peninsula, Japan**, place a
flood, storm (typhoon in Japan) or landslide anywhere along the convoy's route, and move the risk-factor sliders. It
shows the decision on a map, compares the options, and can ask Granite for an explanation.

In a Jupyter terminal (inside the container):

```bash
cd ~/shared/ReliefZ
pip install -r webui/requirements.txt    # first time only: Flask + pytest, pure Python
python -m pytest webui/tests -q          # optional check, about 15 s
python webui/app.py
```

Leave this terminal open: closing it stops the web UI. If you ran notebook 05 in the browser, shut down its kernel
first (**Kernel → Shut Down Kernel**), so Granite isn't loaded into memory twice.

### Step 5. Open the web UI from your laptop

The web UI has no login, so it only accepts connections from the VM itself. Reach it through an SSH tunnel, in a new
terminal **on your laptop**:

```bash
ssh -i <key.pem> -L 8050:localhost:8050 linux1@<IP>
```

Keep it open and go to **http://localhost:8050**. The header should say **Running on s390x**.

How to use it:
- **Location** (top): switch between Valencia and Noto. Each has its own fixed route.
- **Disaster** panel: choose the type, then drag *Position along route*. Close to the convoy tends to give HALT or
  DIVERT, mid-route REROUTE, and far ahead CONTINUE.
- **Risk factors** panel: one slider per input to the risk model. Sliders tagged **AUTO** follow the disaster's
  position. Drag one to override it, and click **manual · reset** to undo.
- **Decision** (right): the recommended action, route risk against the 0.75 threshold, the model's confidence, the
  options compared, and what drives the risk.
- **Explain with Granite**: writes a plain-language explanation in 10–30 seconds. The instant template explanation
  is always shown above it.

### Screenshots for the video

For the technical-design score:
- `docker ps` on the VM;
- notebook 00 (`s390x`, `big`);
- notebook 05 (Granite source and audit-log check);
- notebook 06 (throughput on s390x), with `top` or `htop` running alongside;
- the web UI header showing **Running on s390x**.

### Troubleshooting

| Problem | Fix |
|---|---|
| `scp` created a file called `linux1@<IP>` on your laptop | Add `:~` after the address (see step 1) |
| `Permission denied` / `PermissionError` | On the VM: `chmod -R a+rwX /home/linux1/shared/ReliefZ` |
| `Jupyter command jupyter-nbconvert not found` | Run it inside the container (Jupyter's terminal, or `docker exec -it notebook bash`), not in the SSH session |
| Web UI fails with `FileNotFoundError ... artifacts` | Run notebooks 01–03 first |
| `pip install` permission error | `pip install --user -r webui/requirements.txt` |
| The web UI header says `x86_64` | You're seeing a copy running on your laptop. Stop it, then reconnect the SSH tunnel and check there's no `Address already in use` warning. |
| Browser can't connect to localhost:8050 | Check that `python webui/app.py` is still running on LinuxONE and the tunnel terminal is open |
| `Address already in use` when starting the web UI | Use `python webui/app.py --port 8051`, and the tunnel `-L 8051:localhost:8051` |
| Explanation source says "template" | Granite wasn't found or didn't load. Check notebook 00's readiness line, and shut down other kernels to free memory. |
| `(container has …)` next to a library in notebook 00 | A different version was installed over the container's; reinstall it, e.g. `pip install scikit-learn==1.9.0` |

### Updating the project on the server

Copy the new version (step 1), then run `chmod -R a+rwX /home/linux1/shared/ReliefZ` again. Your trained models in
`artifacts/` and the audit log in `logs/` are kept. Re-run any notebooks that changed.

---

## Submission checklist (from the participant guidebook)

- [ ] Project title in the format `ReliefSync Z_IBM Z Datathon 2026 Project`
- [ ] Event code `SSF2026` in the project description
- [ ] Demo video of **3 minutes or less**: problem, supporting data, solution, how it uses IBM Z (tech stack, the
      LinuxONE instance and the model running)
- [ ] GitHub repo link
- [ ] Links to the open-source resources used ([OPEN_SOURCE.md](OPEN_SOURCE.md))
- [ ] Both mandatory AI/ML labs completed (Predictive AI hybrid multi-model; Predictive AI + Generative AI)
- [ ] Optional: architecture flowchart (Figure 1 in the project summary), prototype

## Data and limitations

All training data is synthetic, generated in notebook 01 from documented, domain-informed rules. The risk threshold
(0.75) is a prototype choice. Real deployment would require validation against real operational outcomes. Road
networks are © OpenStreetMap contributors (ODbL).

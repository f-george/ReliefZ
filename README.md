# ReliefSync Z_IBM Z Datathon 2026 Project

**Team:** ReliefSync Z · **Theme:** Real-time AI for critical decisions ·

Hybrid-AI disaster logistics decision-support prototype designed to run on IBM LinuxONE. The demo takes simulated convoy telemetry,
estimates route risk (Model 1), recommends an action (Model 2), computes reroutes on an OpenStreetMap road graph,
and explains the decision in plain language with IBM Granite running locally in llama.cpp. Notebook 05 simulates a
dispatcher accepting or rejecting the first intervention and records it in a hash-chained audit log. The web UI
explores recommendations; it does not implement dispatcher approval or persistent auditing.
See `ReliefSync_Z_Detailed_Project_Summary-3.docx` for the full design.

Inference runs locally with open-source libraries and models. The browser requests background map tiles from
OpenStreetMap; cached road overlays and routing work without those tiles. See [OPEN_SOURCE.md](OPEN_SOURCE.md) for
the libraries, model and data used, with links and licences. See [SUBMISSION_REVIEW.md](SUBMISSION_REVIEW.md) for the
readiness review and the evidence still needed before submission.

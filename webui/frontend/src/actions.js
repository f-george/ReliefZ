// Full class strings (not built dynamically) so Tailwind can find them
export const ACTIONS = {
  CONTINUE_MONITORING: {
    label: "CONTINUE",
    detail: "Keep driving and keep monitoring",
    badge: "bg-emerald-600",
    bar: "bg-emerald-500",
  },
  HOLD_POSITION: {
    label: "HALT",
    detail: "Stop and wait for the hazard to clear",
    badge: "bg-amber-500",
    bar: "bg-amber-500",
  },
  REROUTE: {
    label: "REROUTE",
    detail: "Take the safer alternative route",
    badge: "bg-sky-600",
    bar: "bg-sky-500",
  },
  DIVERT_TO_BACKUP_HUB: {
    label: "DIVERT TO HUB",
    detail: "Deliver to the backup hub instead",
    badge: "bg-violet-600",
    bar: "bg-violet-500",
  },
};

export const ACTION_ORDER = ["CONTINUE_MONITORING", "HOLD_POSITION", "REROUTE", "DIVERT_TO_BACKUP_HUB"];

export const RISK_BAR = { LOW: "bg-emerald-500", MEDIUM: "bg-amber-500", HIGH: "bg-red-600" };

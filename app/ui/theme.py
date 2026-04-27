"""vSphere-style theme for the NiceGUI UI."""
from __future__ import annotations

from nicegui import ui

# ── vSphere-style palette ──────────────────────
PRIMARY = "#0079ad"         # vSphere blue
PRIMARY_H = "#006696"
ACCENT = "#00a7e1"          # brighter blue
TOPBAR = "#1e2e3a"          # navy
TOPBAR_H = "#2a3d4d"
BG = "#f4f5f5"              # page background
BG_ALT = "#e9ebed"          # inventory background
CARD = "#ffffff"
BORDER = "#d1d1d1"
BORDER_2 = "#b3b3b3"
TEXT = "#313131"
TEXT_2 = "#565656"
TEXT_3 = "#737373"
OK = "#1d7c4a"
WARN = "#ad7100"
BAD = "#c92100"
ISSUE_BG = "#fdecea"
ISSUE_BORDER = "#e5b3ad"

GLOBAL_HEAD = f"""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Metropolis:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  :root {{
    --primary: {PRIMARY};
    --primary-h: {PRIMARY_H};
    --accent: {ACCENT};
    --topbar: {TOPBAR};
    --topbar-h: {TOPBAR_H};
    --bg: {BG};
    --bg-alt: {BG_ALT};
    --card: {CARD};
    --border: {BORDER};
    --border2: {BORDER_2};
    --text: {TEXT};
    --text2: {TEXT_2};
    --text3: {TEXT_3};
    --ok: {OK};
    --warn: {WARN};
    --bad: {BAD};
    --issue-bg: {ISSUE_BG};
    --issue-border: {ISSUE_BORDER};
    --font-ui: 'Metropolis', 'Segoe UI', -apple-system, system-ui, 'Helvetica Neue', sans-serif;
    --font-mono: 'JetBrains Mono', ui-monospace, 'Cascadia Code', 'Segoe UI Mono', monospace;
  }}
  html, body, .nicegui-content, .q-page {{
    font-family: var(--font-ui) !important;
    color: var(--text);
    background: var(--bg) !important;
  }}
  /* Top bar — vSphere navy */
  .vc-topbar {{
    background: var(--topbar);
    color: #fff;
    height: 44px;
    min-height: 44px;
    display: flex; align-items: center; padding: 0 12px;
    border-bottom: 1px solid #000;
  }}
  .vc-topbar a, .vc-topbar .q-btn__content {{ color: #fff; }}
  .vc-topbar .q-btn {{ color: #fff !important; }}
  .vc-brand {{ font-size: 15px; font-weight: 600; letter-spacing: .2px; }}
  .vc-brand .accent {{ color: var(--accent); }}
  .vc-search {{
    background: rgba(255,255,255,0.08);
    border: 1px solid rgba(255,255,255,0.15);
    border-radius: 3px; color: #fff;
    padding: 4px 8px; font-size: 12px; min-width: 240px;
  }}
  .vc-search::placeholder {{ color: rgba(255,255,255,0.55); }}

  /* Inventory left panel */
  .vc-inv {{
    background: #fff;
    border-right: 1px solid var(--border);
    width: 300px; min-width: 300px; max-width: 300px;
    display: flex; flex-direction: column;
  }}
  .vc-inv-tabs {{
    display: flex; border-bottom: 1px solid var(--border);
    background: var(--bg-alt);
  }}
  .vc-inv-tab {{
    flex: 1; padding: 10px 0; text-align: center; cursor: pointer;
    color: var(--text3); border-right: 1px solid var(--border); font-size: 11px;
  }}
  .vc-inv-tab:last-child {{ border-right: none; }}
  .vc-inv-tab.active {{ background: #fff; color: var(--primary); border-bottom: 2px solid var(--primary); }}
  .vc-inv-tab:hover {{ color: var(--primary); }}

  /* Tabs bar (content) */
  .vc-tabs {{
    background: #fff; border-bottom: 1px solid var(--border);
    display: flex; gap: 4px; padding: 0 12px; overflow-x: auto;
  }}
  .vc-tab {{
    padding: 12px 14px; font-size: 13px; color: var(--text2); cursor: pointer;
    border-bottom: 2px solid transparent; white-space: nowrap;
  }}
  .vc-tab:hover {{ color: var(--primary); }}
  .vc-tab.active {{ color: var(--primary); border-bottom-color: var(--primary); font-weight: 500; }}

  /* Entity header */
  .vc-ent-hd {{
    background: #fff; padding: 10px 16px; border-bottom: 1px solid var(--border);
    display: flex; align-items: center; gap: 8px;
  }}
  .vc-ent-icon {{
    width: 28px; height: 28px; border-radius: 3px;
    background: var(--primary); color: #fff; font-weight: 700;
    display: flex; align-items: center; justify-content: center; font-size: 14px;
  }}
  .vc-ent-name {{ font-size: 15px; font-weight: 600; color: var(--text); }}
  .vc-ent-sub {{ font-size: 11px; color: var(--text3); }}

  /* Cards */
  .vc-card {{
    background: #fff; border: 1px solid var(--border); border-radius: 2px;
    padding: 14px; margin: 0;
  }}
  .vc-card-title {{ font-size: 13px; font-weight: 600; color: var(--text); margin-bottom: 10px; letter-spacing: .2px; }}

  /* KV list like Summary */
  .vc-kv {{ display: grid; grid-template-columns: 160px 1fr; gap: 6px 16px; font-size: 13px; }}
  .vc-kv dt {{ color: var(--text3); }}
  .vc-kv dd {{ color: var(--text); margin: 0; }}

  /* Gauges (CPU/Mem/Storage) */
  .vc-gauge {{ margin-bottom: 10px; }}
  .vc-gauge .lbl {{ display:flex; justify-content:space-between; font-size: 11px; color: var(--text2); margin-bottom:3px; }}
  .vc-gauge .bar {{ height: 10px; background: #e4e6e8; border-radius: 2px; overflow: hidden; position: relative; }}
  .vc-gauge .bar > .fill {{ height: 100%; background: var(--primary); }}
  .vc-gauge .bar.warn > .fill {{ background: var(--warn); }}
  .vc-gauge .bar.bad > .fill {{ background: var(--bad); }}

  /* Issues panel */
  .vc-issues {{ background: var(--issue-bg); border: 1px solid var(--issue-border); border-radius: 2px; padding: 10px; }}
  .vc-issues .row {{ display:flex; align-items:center; gap:6px; padding: 4px 0; font-size: 13px; }}
  .vc-issues .dot {{ width:10px;height:10px;border-radius:50%;background: var(--bad); flex-shrink:0; }}
  .vc-issues a {{ color: var(--primary); text-decoration: none; font-size: 12px; }}

  /* Bottom tasks drawer */
  .vc-tasks {{
    background: #fff; border-top: 1px solid var(--border);
    max-height: 220px; overflow: auto;
  }}
  .vc-tasks .hd {{
    padding: 6px 12px; font-size: 12px; font-weight: 600; color: var(--text2);
    border-bottom: 1px solid var(--border); background: var(--bg-alt);
    display:flex; align-items:center; gap: 12px;
  }}
  .vc-tasks table {{ width: 100%; font-size: 12px; border-collapse: collapse; }}
  .vc-tasks th, .vc-tasks td {{ padding: 4px 10px; border-bottom: 1px solid #eee; text-align: left; color: var(--text); }}
  .vc-tasks th {{ color: var(--text3); font-weight: 500; background: #fafafa; position: sticky; top: 0; }}

  /* Tool chip */
  .tool-chip {{ border-left: 3px solid var(--primary); padding: 4px 8px; background: rgba(0,121,173,0.08); border-radius: 2px; font-size: 12px; }}
  .tool-chip--err {{ border-left-color: var(--bad); background: rgba(201,33,0,0.08); }}
  .tool-chip--run {{ border-left-color: var(--accent); background: rgba(0,167,225,0.10); }}
  .report-card {{ border-left: 4px solid var(--ok); background: #f4faf6; padding: 12px; border-radius: 2px; }}

  /* Pulsing dot */
  .pulse {{ animation: pulse-dot 1.4s ease-in-out infinite; }}
  @keyframes pulse-dot {{ 0%,100% {{ opacity: 1 }} 50% {{ opacity: 0.35 }} }}

  /* Overrides for Quasar defaults to look more enterprise */
  .q-card {{ box-shadow: none !important; border: 1px solid var(--border); border-radius: 2px; }}
  .q-btn {{ border-radius: 2px; font-weight: 500; text-transform: none; letter-spacing: .2px; }}
  .q-field--outlined .q-field__control {{ border-radius: 2px; }}
  .q-tab__label {{ font-size: 13px; }}
  .q-tabs--dense .q-tab {{ min-height: 36px; }}

  /* Scrollbar */
  ::-webkit-scrollbar {{ width: 10px; height: 10px; }}
  ::-webkit-scrollbar-thumb {{ background: #c4c6c8; border-radius: 2px; }}
  ::-webkit-scrollbar-thumb:hover {{ background: #a6a9ac; }}
</style>
"""


def apply_head() -> None:
    ui.add_head_html(GLOBAL_HEAD)


def brand_colors() -> None:
    ui.colors(primary=PRIMARY, secondary=ACCENT, accent=ACCENT, positive=OK, warning=WARN, negative=BAD)

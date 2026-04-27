"""NiceGUI UI layer (not mounted in the default deployment).

Import this module and call `mount(fastapi_app)` if you want to re-enable it.
The production UI is served from [static/dashboard.html](../../static/dashboard.html) via nginx.
"""
from __future__ import annotations

import os
from fastapi import FastAPI
from nicegui import ui

from app.ui.layout import build_app_shell


def mount(app: FastAPI) -> None:
    """Mount the NiceGUI single-page app at '/' on the existing FastAPI instance."""

    @ui.page("/")
    def _index() -> None:
        build_app_shell()

    @ui.page("/copilot")
    def _copilot() -> None:
        build_app_shell(default_tab="agent")

    ui.run_with(
        app,
        mount_path="/",
        storage_secret=os.environ.get("UI_STORAGE_SECRET", "change-me-in-prod"),
        title="vCenter AI Admin",
        favicon="🖥️",
    )

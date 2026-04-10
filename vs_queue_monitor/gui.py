"""Tkinter GUI application (window, graph, settings)."""
from __future__ import annotations
import json
import math
import os
import re
import subprocess
import sys
import time
import traceback
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional, Union
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
try:
    import winsound
except Exception:
    winsound = None
from . import APP_DISPLAY_NAME, APP_TAGLINE, GITHUB_REPO_URL, VERSION
from .core import *
from .engine import QueueMonitorEngine
from .hooks import TkMonitorHooks

_APP_ICON_GIF_B64 = 'R0lGODdhQABAAIQAABEUGxUYIAsLEi3H1i/U5CWYpRItNSByfRMwOB9yfBdHUCB5hB5ocyq2wxpTXSmntBU4QSSGkzLm9AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACwAAAAAQABAAEAI/wADABhIsKDBgwgTKly4MIDAgQ8TChAAYKLFiQMtZrzIkSLDjw4XYtzIsaJHARAGEGhg4OTIgxE/yiw4kuKDAQMeVCxAQGUCjxVnFhTosKjRkABiEhSg4AGDiQZw4mzJU+UBoBBDIk16tKvXohIP9CRQQAACqQOojr26lOvXt3C1ZjSokeLFpRiBUiQat29XoYC5uo2bNalhhA+9IjYqOHHgw0L12u24ke7kx49fdsS6c+zPoJxlMuYrGLLIqFIRCKhKgK1dhkcHa317UECCsWXPpl69Vq/srUQb+wWrdwFus2hVs17gOzHh4VsZhob9G7r154av00Y8VClm7o8dD/+tvbm8eY3eG2aPHlwk3qDwsWqEOP67QpeSYda2H9nyS5qssWUSfzPhVxlFCiiQUYC+EfhRg0uhNhVvVkEImHOD0RdSfhEmR2FrzYFVWGkatgeWUnoxMFYEAkiY1ocCBqXUbF+t91dYx7moXG9tRUfQiXD9hqNKZbmolk+hiciXdowhtJoEDQgkgAMEEOAARg1IUJZ+1V3n1oOVCeUckzU6uFiXZLZn5o9ptukmdD9+yWZ638l1mGOk0WhnVqPRWZ9p9cVEZ2xqduenfREdyqVI5zVKWWAm0icReSS5ZJKBBimaGU015TVgfJet+WBenbY1X5iIAkoXqHfVFsEAT5H3JOp9km22FIOozroqp6eCxtpnver63qWXtgojh5lKaiaHTFWpwES4zrUmnZzVpBtOO1Y4rJiqYtYiWkeC2Bakd8YmJ010GXksaJBhuOS7ZU5al47rzhWpcIlm+KWfNvXUkrrRskkivtpJW5FxRH67W8B7IfUXk6raliO49QpsmpLWoZuRWAnTy3B1aA43JFnISRVujIUF52Wf41bEMckAexbibHymWRuVKjFnQAM4sSQAwlZyNuabItIFwQLPBsUAA6ApsAAESYYMcYHTKUT0jTJpBlKJRLfsnnRS2ywswV0b/Kl8GsMn49WKNTkTe2GzLffcdJMZEAA7'

class QueueMonitorApp(QueueMonitorEngine, tk.Tk):

    def __init__(self, initial_path: str = "", auto_start: bool = True) -> None:
        tk.Tk.__init__(self)
        self.title(f"VS Queue Monitor v{VERSION}")
        self.geometry("960x700")
        self.minsize(880, 580)
        self._app_icon_image: Optional[tk.PhotoImage] = None
        self._apply_window_icon()

        self._tk_hooks = TkMonitorHooks(self)
        QueueMonitorEngine.__init__(self, self._tk_hooks, initial_path, auto_start)

        self._build_ui()
        self._tk_hooks.flush_pending_history()

        self._bind_keyboard_shortcuts()
        self.bind("<Configure>", self._schedule_resize_refresh, add=True)
        self.graph_log_scale_var.trace_add("write", lambda *_: self._update_graph_y_scale_button_text())
        self.show_log_var.trace_add("write", self._on_show_log_write)
        self.show_status_var.trace_add("write", self._on_show_status_write)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        try:
            geometry = self.config.get("window_geometry", "")
            if isinstance(geometry, str) and geometry:
                self.geometry(geometry)
        except Exception:
            pass

    def _show_start_loading(self, show: bool) -> None:
        if self._loading_spinner is None or self.start_stop_button is None:
            return
        if show:
            self.start_stop_button.state(["disabled"])
            if self._settings_btn is not None:
                self._loading_spinner.pack(side="left", padx=(UI_INNER_PAD_Y_SM, UI_INNER_PAD_Y_SM), before=self._settings_btn)
            else:
                self._loading_spinner.pack(side="left", padx=(UI_INNER_PAD_Y_SM, UI_INNER_PAD_Y_SM))
            self._loading_spinner.start(12)
        else:
            self._loading_spinner.stop()
            self._loading_spinner.pack_forget()
            self.start_stop_button.state(["!disabled"])
            self.update_start_stop_button()

    def _apply_window_icon(self) -> None:
        """Load window icon from embedded GIF (no external files)."""
        try:
            self._app_icon_image = tk.PhotoImage(data=_APP_ICON_GIF_B64)
        except tk.TclError:
            self._app_icon_image = None
            return
        self.iconphoto(True, self._app_icon_image)

    def _about_parent_toplevel(self) -> tk.Misc:
        """Prefer Settings as parent when open so About stacks above it."""
        try:
            w = self._settings_win
            if w is not None and w.winfo_exists():
                return w
        except Exception:
            pass
        return self

    def show_about(self) -> None:
        """Modal About: name, short description, version, project link, disclaimer."""
        if self._about_win is not None:
            try:
                if self._about_win.winfo_exists():
                    self._about_win.lift()
                    self._about_win.focus_force()
                    return
            except Exception:
                pass
            self._about_win = None
        parent = self._about_parent_toplevel()
        about = tk.Toplevel(parent)
        self._about_win = about
        about.title(f'About {APP_DISPLAY_NAME}')
        about.configure(bg=UI_BG_CARD)
        try:
            about.transient(parent)
        except Exception:
            pass
        about.resizable(False, False)
        if self._app_icon_image is not None:
            try:
                about.iconphoto(True, self._app_icon_image)
            except tk.TclError:
                pass
        outer = tk.Frame(about, bg=UI_BG_CARD, padx=22, pady=20)
        outer.pack(fill='both', expand=True)
        header = tk.Frame(outer, bg=UI_BG_CARD)
        header.pack(fill='x', anchor='w')
        if self._app_icon_image is not None:
            icon_lbl = tk.Label(header, image=self._app_icon_image, bg=UI_BG_CARD)
            icon_lbl.pack(side='left', padx=(0, 14))
        text_col = tk.Frame(header, bg=UI_BG_CARD)
        text_col.pack(side='left', fill='y')
        tk.Label(text_col, text=APP_DISPLAY_NAME, bg=UI_BG_CARD, fg=UI_TEXT_PRIMARY, font=('Segoe UI', 14, 'bold') if sys.platform.startswith('win') else ('TkDefaultFont', 14, 'bold'), anchor='w').pack(anchor='w')
        tk.Label(text_col, text=APP_TAGLINE, bg=UI_BG_CARD, fg=UI_TEXT_MUTED, font=('Segoe UI', 10) if sys.platform.startswith('win') else ('TkDefaultFont', 10), anchor='w').pack(anchor='w', pady=(2, 0))
        tk.Label(outer, text=f'Version {VERSION}', bg=UI_BG_CARD, fg=UI_TEXT_MUTED, font=('Segoe UI', 10) if sys.platform.startswith('win') else ('TkDefaultFont', 10), anchor='w', justify='left').pack(anchor='w', pady=(14, 0))
        link_wrap = tk.Frame(outer, bg=UI_BG_CARD)
        link_wrap.pack(anchor='w', pady=(12, 0))
        tk.Label(link_wrap, text='Website: ', bg=UI_BG_CARD, fg=UI_TEXT_PRIMARY, anchor='w').pack(side='left')
        link_lbl = tk.Label(link_wrap, text='GitHub project page', bg=UI_BG_CARD, fg=UI_LINK, cursor='hand2', font=('Segoe UI', 10, 'underline') if sys.platform.startswith('win') else ('TkDefaultFont', 10, 'underline'))
        link_lbl.pack(side='left')

        def open_repo(_evt: object=None) -> None:
            try:
                webbrowser.open(GITHUB_REPO_URL)
            except Exception:
                pass
        link_lbl.bind('<Button-1>', open_repo)
        tk.Label(outer, text='Not affiliated with Vintage Story or its developers.', bg=UI_BG_CARD, fg=UI_TEXT_MUTED, wraplength=400, justify='left', anchor='w', font=('Segoe UI', 9) if sys.platform.startswith('win') else ('TkDefaultFont', 9)).pack(anchor='w', pady=(12, 0))
        btn_row = ttk.Frame(outer, style='Card.TFrame')
        btn_row.pack(fill='x', pady=(18, 0))

        def close_about() -> None:
            self._about_win = None
            try:
                about.grab_release()
            except Exception:
                pass
            try:
                about.destroy()
            except Exception:
                pass
            try:
                sw = self._settings_win
                if sw is not None and sw.winfo_exists() and (parent is sw):
                    sw.grab_set()
            except Exception:
                pass
        ttk.Button(btn_row, text='OK', width=10, command=close_about).pack(side='right')
        about.protocol('WM_DELETE_WINDOW', close_about)
        about.bind('<Escape>', lambda _e: close_about())
        about.bind('<Return>', lambda _e: close_about())
        try:
            about.grab_set()
        except Exception:
            pass
        about.update_idletasks()
        try:
            parent.update_idletasks()
            w = int(about.winfo_reqwidth())
            h = int(about.winfo_reqheight())
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            x = px + max(0, (pw - w) // 2)
            y = py + max(0, (ph - h) // 2)
            about.geometry(f'+{x}+{y}')
        except Exception:
            pass
        try:
            about.focus_force()
        except Exception:
            pass

    def _configure_ttk_theme(self, style: ttk.Style) -> None:
        """Apply app-wide background and text colors (clam, Grafana-style dark)."""
        _bd = UI_SEPARATOR
        _card = UI_BG_CARD
        self.configure(bg=UI_BG_APP)
        style.configure('App.TFrame', background=UI_BG_APP)
        style.configure('TFrame', background=_card, borderwidth=0)
        style.configure('Card.TFrame', background=_card)
        style.configure('HistoryTabStrip.TFrame', background=UI_BG_CARD)
        style.configure('HistoryTab.TButton', padding=(4, 4), background=_card, foreground=UI_TEXT_PRIMARY, bordercolor=_bd, darkcolor=_card, lightcolor=UI_BUTTON_BG_ACTIVE, focuscolor=_card, borderwidth=1, relief='flat', font=('TkDefaultFont', 10, 'bold'))
        style.map('HistoryTab.TButton', background=[('active', UI_BUTTON_BG_ACTIVE), ('pressed', UI_BUTTON_BG_ACTIVE)], darkcolor=[('pressed', UI_BUTTON_BG_ACTIVE)], lightcolor=[('pressed', UI_BUTTON_BG_ACTIVE)])
        style.configure('TLabel', background=_card, foreground=UI_TEXT_PRIMARY)
        style.configure('TLabelframe', background=_card, foreground=UI_TEXT_PRIMARY, bordercolor=_bd, darkcolor=_bd, lightcolor=_bd, relief='flat', borderwidth=1)
        style.configure('TLabelframe.Label', background=_card, foreground=UI_TEXT_MUTED)
        style.configure('Pane.TLabelframe', background=_card, foreground=UI_TEXT_PRIMARY, bordercolor=_bd, darkcolor=_bd, lightcolor=_bd, relief='flat', borderwidth=1, labelmargins=UI_PANE_LABELFRAME_LABEL_MARGINS)
        style.configure('Pane.TLabelframe.Label', background=_card, foreground=UI_TEXT_MUTED)
        style.configure('GraphPane.TFrame', background=_card, bordercolor=_bd, darkcolor=_bd, lightcolor=_bd, relief='flat', borderwidth=1)
        style.configure('TCheckbutton', background=_card, foreground=UI_TEXT_PRIMARY, focuscolor=_card)
        style.map('TCheckbutton', background=[('active', _card)])
        style.configure('TButton', padding=(10, 4), background=UI_BUTTON_BG, foreground=UI_TEXT_PRIMARY, bordercolor=_bd, darkcolor=UI_BUTTON_BG, lightcolor=UI_BUTTON_BG_ACTIVE, focuscolor=UI_BUTTON_BG)
        style.map('TButton', background=[('active', UI_BUTTON_BG_ACTIVE), ('pressed', UI_BUTTON_BG_ACTIVE)], darkcolor=[('pressed', UI_BUTTON_BG_ACTIVE)], lightcolor=[('pressed', UI_BUTTON_BG_ACTIVE)])
        style.configure('GraphYScale.TButton', padding=(10, 6), background=UI_BUTTON_BG, foreground=UI_TEXT_PRIMARY, bordercolor=_bd, darkcolor=UI_BUTTON_BG, lightcolor=UI_BUTTON_BG_ACTIVE, focuscolor=UI_BUTTON_BG)
        style.map('GraphYScale.TButton', background=[('active', UI_BUTTON_BG_ACTIVE), ('pressed', UI_BUTTON_BG_ACTIVE)], darkcolor=[('pressed', UI_BUTTON_BG_ACTIVE)], lightcolor=[('pressed', UI_BUTTON_BG_ACTIVE)])
        style.configure('PlayStopPlay.TButton', padding=(10, 4), background=UI_PLAY_BTN_BG, foreground='#ffffff', bordercolor=_bd, darkcolor=UI_PLAY_BTN_BG, lightcolor=UI_PLAY_BTN_ACTIVE, focuscolor=UI_PLAY_BTN_BG)
        style.map('PlayStopPlay.TButton', background=[('disabled', UI_PLAY_BTN_BG), ('active', UI_PLAY_BTN_ACTIVE), ('pressed', UI_PLAY_BTN_ACTIVE)], foreground=[('disabled', '#ffffff')], darkcolor=[('pressed', UI_PLAY_BTN_ACTIVE)], lightcolor=[('pressed', UI_PLAY_BTN_ACTIVE)])
        style.configure('PlayStopStop.TButton', padding=(10, 4), background=UI_STOP_BTN_BG, foreground='#ffffff', bordercolor=_bd, darkcolor=UI_STOP_BTN_BG, lightcolor=UI_STOP_BTN_ACTIVE, focuscolor=UI_STOP_BTN_BG)
        style.map('PlayStopStop.TButton', background=[('disabled', UI_STOP_BTN_BG), ('active', UI_STOP_BTN_ACTIVE), ('pressed', UI_STOP_BTN_ACTIVE)], foreground=[('disabled', '#ffffff')], darkcolor=[('pressed', UI_STOP_BTN_ACTIVE)], lightcolor=[('pressed', UI_STOP_BTN_ACTIVE)])
        style.configure('TSeparator', background=UI_SEPARATOR)
        style.configure('Horizontal.TProgressbar', troughcolor=UI_PROGRESS_TROUGH, background=UI_ACCENT_POSITION, thickness=8, bordercolor=_bd, darkcolor=UI_PROGRESS_TROUGH, lightcolor=UI_PROGRESS_TROUGH)
        _thin_pb_style = 'Horizontal.Thin.TProgressbar'
        style.layout(_thin_pb_style, style.layout('Horizontal.TProgressbar'))
        style.configure(_thin_pb_style, troughcolor=UI_PROGRESS_TROUGH, background=UI_ACCENT_POSITION, thickness=3, bordercolor=_bd, darkcolor=UI_PROGRESS_TROUGH, lightcolor=UI_PROGRESS_TROUGH)
        style.configure('Vertical.TScrollbar', background=_card, troughcolor=UI_BG_APP, bordercolor=_bd, darkcolor=_bd, lightcolor=_bd, arrowcolor=UI_TEXT_MUTED, arrowsize=12)
        style.map('Vertical.TScrollbar', background=[('active', UI_BUTTON_BG), ('pressed', UI_BUTTON_BG_ACTIVE)], darkcolor=[('active', _bd)], lightcolor=[('active', _bd)])

    @staticmethod
    def _make_dark_entry(parent: tk.Misc, **kwargs: Any) -> tk.Frame:
        """Flat tk.Entry inside a Frame-drawn border (ttk/clam TEntry draws bad corner pixels on Windows).

        Border color is our highlight ring (no theme “dots”). Rounded corners are not supported by stock Tk.
        """
        pad = UI_ENTRY_INNER_PAD
        wrap = tk.Frame(parent, bg=UI_ENTRY_FIELD, bd=0, highlightthickness=1, highlightbackground=UI_ENTRY_BORDER, highlightcolor=UI_ENTRY_BORDER)
        entry = tk.Entry(wrap, bg=UI_ENTRY_FIELD, fg=UI_TEXT_PRIMARY, insertbackground=UI_TEXT_PRIMARY, selectbackground=UI_BUTTON_BG_ACTIVE, selectforeground=UI_TEXT_PRIMARY, relief='flat', borderwidth=0, highlightthickness=0, font=('TkDefaultFont', 10), **kwargs)
        wrap.grid_rowconfigure(0, weight=1)
        wrap.grid_columnconfigure(0, weight=1)
        entry.grid(row=0, column=0, sticky='nsew', padx=pad, pady=pad)

        def _border_focus(_in: bool) -> None:
            c = UI_GRAPH_AXIS if _in else UI_ENTRY_BORDER
            try:
                wrap.configure(highlightbackground=c, highlightcolor=c)
            except tk.TclError:
                pass
        entry.bind('<FocusIn>', lambda _e: _border_focus(True), add=True)
        entry.bind('<FocusOut>', lambda _e: _border_focus(False), add=True)
        return wrap

    def _build_ui(self) -> None:
        try:
            style = ttk.Style()
            if 'clam' in style.theme_names():
                style.theme_use('clam')
            self._configure_ttk_theme(style)
        except Exception:
            pass
        outer = ttk.Frame(self, padding=(12, 12), style='App.TFrame')
        outer.pack(fill='both', expand=True)
        top = ttk.Frame(outer, style='Card.TFrame', padding=(0, 0, 0, UI_INNER_PAD_Y_SM))
        top.pack(fill='x')
        top.columnconfigure(1, weight=1)
        play_wrap = ttk.Frame(top, style='Card.TFrame')
        play_wrap.grid(row=0, column=0, sticky='nw', padx=(0, UI_INNER_PAD_Y_MD), pady=(0, 0))
        self.start_stop_button = ttk.Button(play_wrap, text='▶', style='PlayStopPlay.TButton', command=self.toggle_monitoring, cursor='hand2')
        self.start_stop_button.pack()
        self.update_start_stop_button()
        path_row = ttk.Frame(top, style='Card.TFrame')
        path_row.grid(row=0, column=1, sticky='ew', pady=(0, 0))
        path_row.columnconfigure(0, weight=1)
        path_left = ttk.Frame(path_row, style='Card.TFrame')
        path_left.grid(row=0, column=0, sticky='ew')
        path_left.columnconfigure(1, weight=1)
        self._lbl_log_path = ttk.Label(path_left, text='Logs folder')
        self._lbl_log_path.grid(row=0, column=0, sticky='w', padx=(0, UI_INNER_PAD_Y_SM))
        self._path_entry = self._make_dark_entry(path_left, textvariable=self.source_path_var)
        self._path_entry.grid(row=0, column=1, sticky='ew', padx=(0, UI_INNER_PAD_Y_SM))
        path_actions = ttk.Frame(path_row, style='Card.TFrame')
        path_actions.grid(row=0, column=1, sticky='e')
        self._btn_browse_logs = ttk.Button(path_actions, text='📁  Browse…', command=self.browse_logs_folder)
        self._btn_browse_logs.pack(side='left', padx=(0, 4))
        self._loading_spinner = ttk.Progressbar(path_actions, mode='indeterminate', length=120)
        self._settings_btn = ttk.Button(path_actions, text='⚙  Settings', command=self.open_settings)
        self._settings_btn.pack(side='left', padx=(4, 0))
        panes = tk.PanedWindow(outer, orient=tk.VERTICAL, sashwidth=UI_PANE_SASH_WIDTH, sashrelief=tk.FLAT, sashpad=UI_PANE_SASH_PAD, sashcursor='sb_v_double_arrow', bd=0, proxyrelief=tk.FLAT, proxyborderwidth=0, proxybackground=UI_BG_APP)
        try:
            panes.configure(opaqueresize=True)
        except Exception:
            pass
        try:
            panes.configure(background=UI_BG_APP)
        except Exception:
            pass
        self.panes = panes
        panes.pack(fill='both', expand=True, pady=(UI_INNER_PAD_Y_SM, UI_INNER_PAD_Y_SM))
        panes.bind('<Configure>', self._schedule_pane_fits, add=True)
        panes.bind('<B1-Motion>', self._schedule_pane_drag_thresholds, add=True)
        self._graph_frame = ttk.Frame(panes, style='GraphPane.TFrame', padding=UI_GRAPH_LABELFRAME_PAD)
        graph_frame = self._graph_frame
        graph_frame.columnconfigure(0, weight=1)
        graph_frame.rowconfigure(0, weight=0)
        graph_frame.rowconfigure(1, weight=1)
        summary = tk.Frame(graph_frame, bg=UI_SUMMARY_BG)
        summary.grid(row=0, column=0, sticky='ew', pady=(0, 0))
        for _c in range(8):
            summary.columnconfigure(_c, weight=0)
        summary.columnconfigure(4, weight=1)
        _spx = UI_SUMMARY_INNER_PAD_X
        _spy = UI_SUMMARY_INNER_PAD_Y_TOP
        _hdr_py = (_spy, 4)
        _val_py = (0, UI_SUMMARY_INNER_PAD_Y_BOTTOM)
        _kpi_font_val = KPI_VALUE_FONT
        if sys.platform.startswith('win'):
            _kpi_emoji_font: tuple[str, int, str] = ('Segoe UI Emoji', 14, 'normal')
        elif sys.platform == 'darwin':
            _kpi_emoji_font = ('Apple Color Emoji', 14, 'normal')
        else:
            _kpi_emoji_font = ('TkDefaultFont', 14, 'normal')
        self._lbl_kpi_position = tk.Label(summary, text='POSITION', bg=UI_SUMMARY_BG, fg=UI_ACCENT_POSITION, font=('TkDefaultFont', 9, 'bold'), anchor='w')
        self._lbl_kpi_position.grid(row=0, column=0, sticky='w', padx=(_spx, UI_INNER_PAD_Y_SM), pady=_hdr_py)
        self._lbl_kpi_status = tk.Label(summary, text='STATUS', bg=UI_SUMMARY_BG, fg=UI_ACCENT_STATUS, font=('TkDefaultFont', 9, 'bold'), anchor='w')
        self._lbl_kpi_status.grid(row=0, column=1, sticky='w', padx=(UI_INNER_PAD_Y_SM, UI_INNER_PAD_Y_SM), pady=_hdr_py)
        self._lbl_kpi_rate = tk.Label(summary, text='RATE', bg=UI_SUMMARY_BG, fg=UI_ACCENT_RATE, font=('TkDefaultFont', 9, 'bold'), anchor='w')
        self._lbl_kpi_rate.grid(row=0, column=2, sticky='w', padx=(UI_INNER_PAD_Y_SM, UI_INNER_PAD_Y_SM), pady=_hdr_py)
        self._refresh_kpi_rate_header()
        self._lbl_kpi_warnings = tk.Label(summary, text='WARNINGS', bg=UI_SUMMARY_BG, fg=UI_ACCENT_WARNINGS, font=('TkDefaultFont', 9, 'bold'), anchor='w')
        self._lbl_kpi_warnings.grid(row=0, column=3, sticky='w', padx=(UI_INNER_PAD_Y_SM, UI_INNER_PAD_Y_SM), pady=_hdr_py)
        _summary_mid_spacer = tk.Frame(summary, bg=UI_SUMMARY_BG)
        _summary_mid_spacer.grid(row=0, column=4, rowspan=2, sticky='nsew')
        self._lbl_elapsed_header = tk.Label(summary, text='ELAPSED', bg=UI_SUMMARY_BG, fg=UI_ACCENT_ELAPSED, font=('TkDefaultFont', 9, 'bold'), anchor='w')
        self._lbl_elapsed_header.grid(row=0, column=5, sticky='w', padx=(UI_INNER_PAD_Y_MD, 4), pady=_hdr_py)
        self._lbl_remaining_header = tk.Label(summary, text='EST. REMAINING', bg=UI_SUMMARY_BG, fg=UI_ACCENT_REMAINING, font=('TkDefaultFont', 9, 'bold'), anchor='w')
        self._lbl_remaining_header.grid(row=0, column=6, sticky='w', padx=(UI_INNER_PAD_Y_MD, 0), pady=_hdr_py)
        self._lbl_progress_header = tk.Label(summary, text='PROGRESS', bg=UI_SUMMARY_BG, fg=UI_ACCENT_PROGRESS, font=('TkDefaultFont', 9, 'bold'), anchor='w')
        self._lbl_progress_header.grid(row=0, column=7, sticky='w', padx=(UI_INNER_PAD_Y_MD, _spx), pady=_hdr_py)
        _pos_cell = tk.Frame(summary, bg=UI_SUMMARY_BG)
        _pos_cell.grid(row=1, column=0, sticky='w', padx=(_spx, UI_INNER_PAD_Y_SM), pady=_val_py)
        self._position_value_label = tk.Label(_pos_cell, textvariable=self.position_var, bg=UI_SUMMARY_BG, fg=UI_SUMMARY_VALUE, font=_kpi_font_val, anchor='w')
        self._position_value_label.pack(side='left')
        self._position_emoji_label = tk.Label(_pos_cell, text='', bg=UI_SUMMARY_BG, fg=UI_SUMMARY_VALUE, font=_kpi_emoji_font, anchor='w')
        self._position_emoji_label.pack(side='left', padx=(3, 0))
        self._status_value_label = tk.Label(summary, textvariable=self.status_var, bg=UI_SUMMARY_BG, fg=UI_SUMMARY_VALUE, font=_kpi_font_val, anchor='w')
        self._status_value_label.grid(row=1, column=1, sticky='w', padx=(UI_INNER_PAD_Y_SM, UI_INNER_PAD_Y_SM), pady=_val_py)
        self._queue_rate_value_label = tk.Label(summary, textvariable=self.queue_rate_var, bg=UI_SUMMARY_BG, fg=UI_SUMMARY_VALUE, font=_kpi_font_val, anchor='w')
        self._queue_rate_value_label.grid(row=1, column=2, sticky='w', padx=(UI_INNER_PAD_Y_SM, UI_INNER_PAD_Y_SM), pady=_val_py)
        self._warnings_kpi_frame = tk.Frame(summary, bg=UI_SUMMARY_BG)
        self._warnings_kpi_frame.grid(row=1, column=3, sticky='w', padx=(UI_INNER_PAD_Y_SM, UI_INNER_PAD_Y_SM), pady=_val_py)
        self._elapsed_value_label = tk.Label(summary, textvariable=self.elapsed_var, bg=UI_SUMMARY_BG, fg=UI_SUMMARY_VALUE, font=_kpi_font_val, anchor='e')
        self._elapsed_value_label.grid(row=1, column=5, sticky='ew', padx=(UI_INNER_PAD_Y_MD, 4), pady=_val_py)
        self._remaining_value_label = tk.Label(summary, textvariable=self.predicted_remaining_var, bg=UI_SUMMARY_BG, fg=UI_SUMMARY_VALUE, font=_kpi_font_val, anchor='e')
        self._remaining_value_label.grid(row=1, column=6, sticky='ew', padx=(UI_INNER_PAD_Y_MD, 0), pady=_val_py)
        _prog_cell = tk.Frame(summary, bg=UI_SUMMARY_BG)
        _prog_cell.grid(row=1, column=7, sticky='e', padx=(UI_INNER_PAD_Y_MD, _spx), pady=_val_py)
        self._queue_progress = ttk.Progressbar(_prog_cell, style='Thin.TProgressbar', mode='determinate', maximum=100.0, length=96)
        self._queue_progress.pack(anchor='e', pady=(0, 0))
        self._bind_static_tooltip(self._lbl_progress_header, self._progress_tooltip_text)
        self._bind_static_tooltip(self._queue_progress, self._progress_tooltip_text)
        _gsp_l, _gsp_t, _gsp_r, _gsp_b = UI_GRAPH_STACK_PAD
        self._graph_stack_frame = tk.Frame(graph_frame, bg=UI_GRAPH_BG, bd=0, highlightthickness=0)
        graph_stack = self._graph_stack_frame
        graph_stack.grid(row=1, column=0, sticky='nsew', padx=(_gsp_l, _gsp_r), pady=(_gsp_t, _gsp_b))
        graph_stack.rowconfigure(0, weight=1)
        graph_stack.columnconfigure(0, weight=1)
        self.graph_canvas = tk.Canvas(graph_stack, height=200, highlightthickness=0, background=UI_GRAPH_BG, bd=0, highlightbackground=UI_GRAPH_BG)
        _gdp_l, _gdp_t, _gdp_r, _gdp_b = UI_GRAPH_DARK_INNER_PAD
        self.graph_canvas.grid(row=0, column=0, sticky='nsew', padx=(_gdp_l, _gdp_r), pady=(_gdp_t, _gdp_b))
        self._graph_y_scale_btn = ttk.Button(self.graph_canvas, text='Y → log', style='GraphYScale.TButton', command=self._toggle_graph_y_scale)
        self._graph_y_scale_btn.lift()
        self._update_graph_y_scale_button_text()
        self._bind_static_tooltip(self._graph_y_scale_btn, 'Linear: even spacing by position. Log: zoom the lower numbers on the chart.')
        self.graph_canvas.bind('<Configure>', self._on_graph_canvas_configure)
        self.graph_canvas.bind('<Motion>', self.on_graph_motion)
        self.graph_canvas.bind('<Leave>', lambda _evt: self.hide_graph_tooltip())
        self.status_frame = ttk.Frame(panes, style='HistoryTabStrip.TFrame', padding=UI_HISTORY_FRAME_PAD_EXPANDED)
        self.status_frame.columnconfigure(0, weight=1)
        self.status_frame.rowconfigure(2, weight=1)
        self._status_tab_strip = ttk.Frame(self.status_frame, style='HistoryTabStrip.TFrame')
        self._status_tab_strip.grid(row=0, column=0, sticky='ew')
        self._status_tab_btn = ttk.Button(self._status_tab_strip, text='▼', width=3, style='HistoryTab.TButton', command=self._toggle_status_panel)
        self._status_tab_btn.pack(side='left', padx=(0, UI_INNER_PAD_Y_SM), pady=(0, 0))
        self._lbl_status_section_title = ttk.Label(self._status_tab_strip, text='Info', style='Pane.TLabelframe.Label')
        self._lbl_status_section_title.pack(side='left', padx=(0, 0), pady=(0, 0))
        self._status_sep = ttk.Separator(self.status_frame, orient=tk.HORIZONTAL)
        self._status_sep.grid(row=1, column=0, sticky='ew', pady=(UI_INNER_PAD_Y_SM, UI_INNER_PAD_Y_SM))
        self._status_body_wrap = ttk.Frame(self.status_frame, style='Card.TFrame')
        self._status_body_wrap.grid(row=2, column=0, sticky='nsew')
        self._status_body_wrap.columnconfigure(0, weight=1)
        status_body = ttk.Frame(self._status_body_wrap, style='Card.TFrame', padding=(0, UI_STATUS_BODY_PAD_TOP, 0, 0))
        status_body.grid(row=0, column=0, sticky='nsew')
        status_body.columnconfigure(0, weight=1)
        self.history_frame = ttk.Frame(panes, style='HistoryTabStrip.TFrame', padding=UI_HISTORY_FRAME_PAD_EXPANDED)
        self.history_frame.columnconfigure(0, weight=1)
        self.history_frame.rowconfigure(2, weight=1)
        self._history_tab_strip = ttk.Frame(self.history_frame, style='HistoryTabStrip.TFrame')
        self._history_tab_strip.grid(row=0, column=0, sticky='ew')
        self._history_tab_btn = ttk.Button(self._history_tab_strip, text='▼', width=3, style='HistoryTab.TButton', command=self._toggle_history_panel)
        self._history_tab_btn.pack(side='left', padx=(0, UI_INNER_PAD_Y_SM), pady=(0, 0))
        self._lbl_history_section_title = ttk.Label(self._history_tab_strip, text='History', style='Pane.TLabelframe.Label')
        self._lbl_history_section_title.pack(side='left', padx=(0, 0), pady=(0, 0))
        self._wire_collapsible_header(self._status_tab_strip, self._lbl_status_section_title, self._toggle_status_panel)
        self._wire_collapsible_hand_cursor(self._status_tab_btn)
        self._wire_collapsible_header(self._history_tab_strip, self._lbl_history_section_title, self._toggle_history_panel)
        self._wire_collapsible_hand_cursor(self._history_tab_btn)
        self._history_sep = ttk.Separator(self.history_frame, orient=tk.HORIZONTAL)
        self._history_sep.grid(row=1, column=0, sticky='ew', pady=(UI_INNER_PAD_Y_SM, UI_INNER_PAD_Y_SM))
        self._history_body = tk.Frame(self.history_frame, bg=UI_SUMMARY_BG, bd=0, highlightthickness=0)
        self._history_body.rowconfigure(0, weight=1)
        self._history_body.columnconfigure(0, weight=1)
        panes.add(graph_frame, minsize=120, stretch='always')
        panes.add(self.status_frame, minsize=UI_STATUS_PANE_MIN_EXPANDED, stretch='never')
        panes.add(self.history_frame, minsize=UI_HISTORY_PANE_MIN_EXPANDED, stretch='always')
        details = ttk.Frame(status_body, padding=(UI_SUMMARY_INNER_PAD_X, UI_INNER_PAD_Y_MD, UI_SUMMARY_INNER_PAD_X, UI_INNER_PAD_Y_MD), style='Card.TFrame')
        details.grid(row=0, column=0, sticky='ew', pady=(0, 0))
        details.columnconfigure(1, weight=1)
        details.columnconfigure(3, weight=0)
        wrap = 420
        _dpy = (UI_INNER_PAD_Y_SM, UI_INNER_PAD_Y_SM)
        _g = 6
        self._lbl_det_last_change = ttk.Label(details, text='Last change')
        self._lbl_det_last_change.grid(row=0, column=0, sticky='nw', padx=(0, _g), pady=_dpy)
        self._lbl_det_last_change_val = ttk.Label(details, textvariable=self.last_change_var, wraplength=wrap)
        self._lbl_det_last_change_val.grid(row=0, column=1, sticky='nw', padx=(0, UI_INNER_PAD_Y_MD), pady=_dpy)
        self._lbl_det_alert = ttk.Label(details, text='Last threshold alert')
        self._lbl_det_alert.grid(row=0, column=2, sticky='nw', padx=(UI_INNER_PAD_Y_MD, _g), pady=_dpy)
        self._lbl_det_alert_val = ttk.Label(details, textvariable=self.last_alert_var, wraplength=wrap)
        self._lbl_det_alert_val.grid(row=0, column=3, sticky='nw', padx=(0, 0), pady=_dpy)
        self._lbl_det_path = ttk.Label(details, text='Resolved log path')
        self._lbl_det_path.grid(row=1, column=0, sticky='nw', padx=(0, _g), pady=_dpy)
        self._lbl_det_path_val = ttk.Label(details, textvariable=self.resolved_path_var, wraplength=wrap * 2)
        self._lbl_det_path_val.grid(row=1, column=1, columnspan=3, sticky='nw', padx=(0, UI_INNER_PAD_Y_SM), pady=_dpy)
        self._lbl_det_global_rate = ttk.Label(details, text='Global Rate')
        self._lbl_det_global_rate.grid(row=2, column=0, sticky='nw', padx=(0, _g), pady=_dpy)
        self._lbl_det_global_rate_val = ttk.Label(details, textvariable=self.global_rate_var, wraplength=wrap * 2)
        self._lbl_det_global_rate_val.grid(row=2, column=1, columnspan=3, sticky='nw', padx=(0, UI_INNER_PAD_Y_SM), pady=_dpy)
        self.history_text = tk.Text(self._history_body, height=18, wrap='word', state='disabled', font=('Segoe UI', 9) if sys.platform.startswith('win') else ('TkDefaultFont', 10), padx=UI_HISTORY_TEXT_PAD, pady=UI_HISTORY_TEXT_PAD, bg=UI_SUMMARY_BG, fg=UI_SUMMARY_VALUE, insertbackground=UI_SUMMARY_VALUE, highlightthickness=0, borderwidth=0)
        self.history_text.grid(row=0, column=0, sticky='nsew', padx=(0, UI_INNER_PAD_Y_SM), pady=(0, 0))
        self._history_scrollbar = ttk.Scrollbar(self._history_body, orient='vertical', command=self.history_text.yview)
        self._history_scrollbar.grid(row=0, column=1, sticky='ns')
        self.history_text.configure(yscrollcommand=self._history_scrollbar.set)
        self._bind_main_tooltips()
        self._on_show_log_write()
        self._on_show_status_write()
        self.update_start_stop_button()
        self.after_idle(self._sync_collapsible_panes_after_map)
        self.after_idle(self._refresh_warnings_kpi)

    def _sync_collapsible_panes_after_map(self) -> None:
        try:
            self._on_show_log_write()
            self._on_show_status_write()
        except (tk.TclError, RuntimeError):
            pass

    def open_settings(self) -> None:
        """Polling, Warning Alerts, Completion Alerts, History, estimation — gear entry."""
        if self._settings_win is not None:
            try:
                if self._settings_win.winfo_exists():
                    self._settings_win.lift()
                    self._settings_win.focus_force()
                    return
            except Exception:
                pass
            self._settings_win = None
        win = tk.Toplevel(self)
        self._settings_win = win
        win.title('Settings')
        win.configure(bg=UI_BG_CARD)
        try:
            win.transient(self)
        except Exception:
            pass
        win.minsize(440, 1)
        outer = ttk.Frame(win, padding=(16, 14), style='Card.TFrame')
        outer.pack(fill='x')
        poll_fr = ttk.LabelFrame(outer, text='Polling', padding=(10, 8))
        poll_fr.pack(fill='x', pady=(0, 8))
        _poll_lbl = ttk.Label(poll_fr, text='Poll (s)')
        _poll_lbl.grid(row=0, column=0, sticky='w', padx=(0, 8))
        _poll_entry = self._make_dark_entry(poll_fr, width=6, textvariable=self.poll_sec_var)
        _poll_entry.grid(row=0, column=1, sticky='w')
        self._bind_static_tooltip(_poll_lbl, 'How often the log is read.')
        self._bind_static_tooltip(_poll_entry, 'How often the log is read.')
        warn_fr = ttk.LabelFrame(outer, text='Warning Alerts', padding=(10, 8))
        warn_fr.pack(fill='x', pady=(0, 8))
        warn_fr.columnconfigure(0, weight=1)
        thr_row = ttk.Frame(warn_fr, style='Card.TFrame')
        thr_row.grid(row=0, column=0, sticky='ew')
        thr_row.columnconfigure(1, weight=1)
        _thr_lbl = ttk.Label(thr_row, text='Thresholds (comma-separated)')
        _thr_lbl.grid(row=0, column=0, sticky='e', padx=(0, 8))
        _thr_entry = self._make_dark_entry(thr_row, textvariable=self.alert_thresholds_var, width=36)
        _thr_entry.grid(row=0, column=1, sticky='ew', padx=(0, 12))
        self._bind_static_tooltip(_thr_lbl, 'Alert when your position drops past each number (e.g. 10, 5, 1).')
        self._bind_static_tooltip(_thr_entry, 'Alert when your position drops past each number (e.g. 10, 5, 1).')
        checks1 = ttk.Frame(warn_fr, style='Card.TFrame')
        checks1.grid(row=1, column=0, sticky='w', pady=(10, 0))
        _cb_warn_pop = ttk.Checkbutton(checks1, text='Warning popup', variable=self.popup_enabled_var)
        _cb_warn_pop.pack(side='left', padx=(0, 14))
        self._bind_static_tooltip(_cb_warn_pop, 'Popup when a threshold is crossed.')
        _cb_warn_snd = ttk.Checkbutton(checks1, text='Warning sound', variable=self.sound_enabled_var)
        _cb_warn_snd.pack(side='left', padx=(0, 14))
        self._bind_static_tooltip(_cb_warn_snd, 'Sound when a threshold is crossed.')
        sound_row = ttk.Frame(warn_fr, style='Card.TFrame')
        sound_row.grid(row=2, column=0, sticky='ew', pady=(10, 0))
        sound_row.columnconfigure(1, weight=1)
        _lbl_warn_sound = ttk.Label(sound_row, text='Warning sound file')
        _lbl_warn_sound.grid(row=0, column=0, sticky='w', padx=(0, 8))
        self._bind_static_tooltip(_lbl_warn_sound, 'Optional file; default sound if empty.')
        _sound_entry = self._make_dark_entry(sound_row, textvariable=self.alert_sound_path_var)
        _sound_entry.grid(row=0, column=1, sticky='ew', padx=(0, 8))
        _sound_actions = ttk.Frame(sound_row, style='Card.TFrame')
        _sound_actions.grid(row=0, column=2, sticky='e')
        _sound_browse = ttk.Button(_sound_actions, text='Browse…', command=self.browse_alert_sound, width=8)
        _sound_browse.pack(side='left', padx=(0, 6))
        _sound_preview = ttk.Button(_sound_actions, text='Preview', command=self.preview_alert_sound, width=8)
        _sound_preview.pack(side='left')
        self._bind_static_tooltip(_sound_entry, 'Optional file; default sound if empty.')
        self._bind_static_tooltip(_sound_browse, 'Choose a sound file.')
        self._bind_static_tooltip(_sound_preview, 'Play the warning sound once.')
        comp_fr = ttk.LabelFrame(outer, text='Completion Alerts', padding=(10, 8))
        comp_fr.pack(fill='x', pady=(0, 8))
        comp_fr.columnconfigure(0, weight=1)
        _comp_intro = ttk.Label(comp_fr, text='Fires once when the log shows you are past queue wait (e.g. loading mods, download — lines after the last position line). Not threshold-based — only on/off below (and optional sound file).', wraplength=440)
        _comp_intro.grid(row=0, column=0, sticky='w', pady=(0, 8))
        self._bind_static_tooltip(_comp_intro, 'Uses patterns on lines after your last queue position line so position 1 alone does not trigger.')
        checks2 = ttk.Frame(comp_fr, style='Card.TFrame')
        checks2.grid(row=1, column=0, sticky='w', pady=(0, 0))
        _cb_comp_pop = ttk.Checkbutton(checks2, text='Completion popup', variable=self.completion_popup_enabled_var)
        _cb_comp_pop.pack(side='left', padx=(0, 14))
        self._bind_static_tooltip(_cb_comp_pop, 'Popup when the log shows past-queue-wait activity after the queue.')
        _cb_comp_snd = ttk.Checkbutton(checks2, text='Completion sound', variable=self.completion_sound_enabled_var)
        _cb_comp_snd.pack(side='left', padx=(0, 0))
        self._bind_static_tooltip(_cb_comp_snd, 'Sound when the log shows past-queue-wait activity after the queue.')
        comp_sound_row = ttk.Frame(comp_fr, style='Card.TFrame')
        comp_sound_row.grid(row=2, column=0, sticky='ew', pady=(10, 0))
        comp_sound_row.columnconfigure(1, weight=1)
        _lbl_comp_sound = ttk.Label(comp_sound_row, text='Completion sound file')
        _lbl_comp_sound.grid(row=0, column=0, sticky='w', padx=(0, 8))
        self._bind_static_tooltip(_lbl_comp_sound, 'Optional file; default sound if empty.')
        _comp_entry = self._make_dark_entry(comp_sound_row, textvariable=self.completion_sound_path_var)
        _comp_entry.grid(row=0, column=1, sticky='ew', padx=(0, 8))
        _comp_actions = ttk.Frame(comp_sound_row, style='Card.TFrame')
        _comp_actions.grid(row=0, column=2, sticky='e')
        _comp_browse = ttk.Button(_comp_actions, text='Browse…', command=self.browse_completion_sound, width=8)
        _comp_browse.pack(side='left', padx=(0, 6))
        _comp_preview = ttk.Button(_comp_actions, text='Preview', command=self.preview_completion_sound, width=8)
        _comp_preview.pack(side='left')
        self._bind_static_tooltip(_comp_entry, 'Optional file; default sound if empty.')
        self._bind_static_tooltip(_comp_browse, 'Choose a sound file.')
        self._bind_static_tooltip(_comp_preview, 'Play the completion sound once.')
        history_fr = ttk.LabelFrame(outer, text='History', padding=(10, 8))
        history_fr.pack(fill='x', pady=(0, 8))
        _cb_log_every = ttk.Checkbutton(history_fr, text='Log every position change', variable=self.show_every_change_var)
        _cb_log_every.pack(anchor='w')
        self._bind_static_tooltip(_cb_log_every, 'When on, append a History line each time your queue position changes. When off, skip those (alerts, completion, errors, and monitoring start still log).')
        display_fr = ttk.LabelFrame(outer, text='Estimation', padding=(10, 8))
        display_fr.pack(fill='x', pady=(0, 10))
        _win_lbl = ttk.Label(display_fr, text='Rolling window (points)')
        _win_lbl.grid(row=0, column=0, sticky='w', padx=(0, 8))
        _win_entry = self._make_dark_entry(display_fr, width=8, textvariable=self.avg_window_var)
        _win_entry.grid(row=0, column=1, sticky='w')
        _avg_tip = 'How many recent queue steps to use for rolling rate and ETA (larger = smoother, less reactive).'
        self._bind_static_tooltip(_win_lbl, _avg_tip)
        self._bind_static_tooltip(_win_entry, _avg_tip)
        bottom = ttk.Frame(outer, style='Card.TFrame')
        bottom.pack(fill='x', pady=(8, 0))
        _btn_reset = ttk.Button(bottom, text='Reset defaults', command=self.reset_defaults)
        _btn_reset.pack(side='left')
        self._bind_static_tooltip(_btn_reset, 'Reset all settings here to defaults.')
        _btn_about = ttk.Button(bottom, text='About…', command=self.show_about)
        _btn_about.pack(side='left', padx=(10, 0))
        self._bind_static_tooltip(_btn_about, 'Version and project website.')

        def close_settings() -> None:
            try:
                win.grab_release()
            except Exception:
                pass
            self._settings_win = None
            try:
                win.destroy()
            except Exception:
                pass
            self.persist_config()
            self._on_show_log_write()
            self._on_show_status_write()
            self.redraw_graph()
            self._refresh_warnings_kpi()
        _btn_close = ttk.Button(bottom, text='Close', command=close_settings)
        _btn_close.pack(side='right')
        self._bind_static_tooltip(_btn_close, 'Save and close.')
        win.protocol('WM_DELETE_WINDOW', close_settings)
        win.bind('<Escape>', lambda _e: close_settings())
        try:
            win.grab_set()
        except Exception:
            pass
        win.update_idletasks()
        try:
            self.update_idletasks()
            w = max(380, int(win.winfo_reqwidth()))
            h = int(win.winfo_reqheight())
            px = self.winfo_rootx()
            py = self.winfo_rooty()
            pw = self.winfo_width()
            ph = self.winfo_height()
            x = px + max(0, (pw - w) // 2)
            y = py + max(0, (ph - h) // 2)
            win.geometry(f'{w}x{h}+{x}+{y}')
        except Exception:
            pass

    def update_start_stop_button(self) -> None:
        if self.start_stop_button is None:
            return
        if self.running:
            self.start_stop_button.configure(text='■', style='PlayStopStop.TButton')
        else:
            self.start_stop_button.configure(text='▶', style='PlayStopPlay.TButton')

    def _update_history_tab_button_text(self) -> None:
        btn = self._history_tab_btn
        if btn is None:
            return
        if self.show_log_var.get():
            btn.configure(text='▼')
        else:
            btn.configure(text='▲')

    def _update_status_tab_button_text(self) -> None:
        btn = self._status_tab_btn
        if btn is None:
            return
        if self.show_status_var.get():
            btn.configure(text='▼')
        else:
            btn.configure(text='▲')

    def _schedule_pane_fits(self, _event: object=None) -> None:
        """Window/pane resize: refit collapsed History and Status so empty bands don’t linger."""
        self._schedule_fit_history_collapsed(_event)
        self._schedule_fit_status_collapsed(_event)
        self._schedule_pane_drag_thresholds()

    def _schedule_pane_drag_thresholds(self, _event: object=None) -> None:
        """Debounced: apply sash open/close thresholds during drag (Configure + B1-Motion), not only on release."""
        if self._pane_drag_threshold_job is not None:
            try:
                self.after_cancel(self._pane_drag_threshold_job)
            except Exception:
                pass
        self._pane_drag_threshold_job = self.after_idle(self._run_pane_drag_thresholds)

    def _run_pane_drag_thresholds(self) -> None:
        self._pane_drag_threshold_job = None
        self._apply_pane_drag_thresholds()

    def _apply_pane_drag_thresholds(self) -> None:
        """Stretch past header + margin opens a collapsed pane; squeeze past max height collapses expanded."""
        if self.panes is None:
            return
        try:
            self.update_idletasks()
        except tk.TclError:
            return
        sf = self.status_frame
        hf = self.history_frame
        if sf is not None:
            try:
                h = int(sf.winfo_height())
            except (tk.TclError, ValueError):
                h = 0
            if self.show_status_var.get():
                if h <= UI_STATUS_DRAG_AUTO_COLLAPSE_MAX_H:
                    self.show_status_var.set(False)
            else:
                try:
                    need = self._collapsed_status_pane_minsize()
                except Exception:
                    need = UI_COLLAPSED_PANE_HEADER_MIN_FALLBACK
                open_min = max(need + PANE_DRAG_OPEN_EXTRA_PX, UI_STATUS_PANE_MIN_EXPANDED + 24)
                if h >= open_min:
                    self.show_status_var.set(True)
        if hf is not None:
            try:
                h = int(hf.winfo_height())
            except (tk.TclError, ValueError):
                h = 0
            if self.show_log_var.get():
                if h <= UI_HISTORY_DRAG_AUTO_COLLAPSE_MAX_H:
                    self.show_log_var.set(False)
            else:
                try:
                    need = self._collapsed_history_pane_minsize()
                except Exception:
                    need = UI_COLLAPSED_PANE_HEADER_MIN_FALLBACK
                open_min = max(need + PANE_DRAG_OPEN_EXTRA_PX, UI_HISTORY_PANE_MIN_EXPANDED + 24)
                if h >= open_min:
                    self.show_log_var.set(True)

    def _collapsed_status_pane_minsize(self) -> int:
        """Minimum PanedWindow height for Status when details are hidden (clickable header only)."""
        if self.status_frame is None:
            return UI_COLLAPSED_PANE_HEADER_MIN_FALLBACK
        try:
            self.update_idletasks()
            self.status_frame.update_idletasks()
            h = int(self.status_frame.winfo_reqheight())
            return max(UI_COLLAPSED_PANE_HEADER_MIN_FALLBACK, h)
        except (tk.TclError, ValueError, TypeError):
            return UI_COLLAPSED_PANE_HEADER_MIN_FALLBACK

    def _collapsed_history_pane_minsize(self) -> int:
        """Minimum PanedWindow height for History when log body is hidden (clickable header only)."""
        if self.history_frame is None:
            return UI_COLLAPSED_PANE_HEADER_MIN_FALLBACK
        try:
            self.update_idletasks()
            self.history_frame.update_idletasks()
            h = int(self.history_frame.winfo_reqheight())
            return max(UI_COLLAPSED_PANE_HEADER_MIN_FALLBACK, h)
        except (tk.TclError, ValueError, TypeError):
            return UI_COLLAPSED_PANE_HEADER_MIN_FALLBACK

    def _status_pane_min_for_layout(self) -> int:
        """Reserved height for Status pane when positioning sashes (expanded min or header-only)."""
        if self.status_frame is None:
            return UI_STATUS_PANE_MIN_EXPANDED
        try:
            self.update_idletasks()
            self.status_frame.update_idletasks()
            h = int(self.status_frame.winfo_reqheight())
            if self.show_status_var.get():
                return max(UI_STATUS_PANE_MIN_EXPANDED, h)
            return max(UI_COLLAPSED_PANE_HEADER_MIN_FALLBACK, h)
        except (tk.TclError, ValueError, TypeError):
            return UI_STATUS_PANE_MIN_EXPANDED if self.show_status_var.get() else UI_COLLAPSED_PANE_HEADER_MIN_FALLBACK

    def _wire_collapsible_header(self, strip: tk.Misc, title: tk.Misc, toggle: Callable[[], None]) -> None:
        """Whole header bar + title toggle; chevron keeps its own command (no double toggle).

        Pack an expanding tk.Frame after the chevron + title so the full row receives clicks
        (ttk strip alone often only sizes to its packed children).
        """

        def on_click(_evt: object) -> None:
            toggle()
        filler = tk.Frame(strip, bg=UI_BG_CARD, cursor='hand2', highlightthickness=0, bd=0)
        filler.pack(side='left', fill=tk.BOTH, expand=True)
        for w in (strip, title, filler):
            try:
                w.configure(cursor='hand2')
            except tk.TclError:
                pass
            w.bind('<Button-1>', on_click, add=True)

    @staticmethod
    def _wire_collapsible_hand_cursor(widget: tk.Misc) -> None:
        try:
            widget.configure(cursor='hand2')
        except tk.TclError:
            pass

    def _toggle_history_panel(self) -> None:
        self.show_log_var.set(not self.show_log_var.get())

    def _toggle_status_panel(self) -> None:
        self.show_status_var.set(not self.show_status_var.get())

    def _on_show_log_write(self, *_args: object) -> None:
        self.update_log_visibility()
        self._update_history_tab_button_text()

    def _on_show_status_write(self, *_args: object) -> None:
        self.update_status_visibility()
        self._update_status_tab_button_text()

    def update_status_visibility(self) -> None:
        """Show or hide Status details; header + chevron stay like History."""
        if self.status_frame is None or self.panes is None or self._status_body_wrap is None:
            return
        panes = self.panes
        sf = self.status_frame
        body = self._status_body_wrap
        sep = self._status_sep
        if self.show_status_var.get():
            sf.configure(padding=UI_HISTORY_FRAME_PAD_EXPANDED)
            body.grid(row=2, column=0, sticky='new')
            if sep is not None:
                sep.grid(row=1, column=0, sticky='ew', pady=(UI_INNER_PAD_Y_SM, UI_INNER_PAD_Y_SM))
            sf.rowconfigure(2, weight=0)
            try:
                panes.paneconfigure(sf, minsize=UI_STATUS_PANE_MIN_EXPANDED, stretch='never')
            except Exception:
                pass
            self.after(1, self._fit_status_pane_expanded)
            self.after(50, self._fit_status_pane_expanded)
            self.after(200, self._fit_status_pane_expanded)
        else:
            sf.configure(padding=UI_HISTORY_FRAME_PAD_COLLAPSED)
            body.grid_remove()
            if sep is not None:
                sep.grid_remove()
            sf.rowconfigure(2, weight=0)
            try:
                self.update_idletasks()
                need = self._collapsed_status_pane_minsize()
                panes.paneconfigure(sf, minsize=need, stretch='never')
                panes.paneconfigure(sf, height=need)
            except Exception:
                pass
            self._schedule_fit_status_collapsed()
            self.after(50, self._fit_status_pane_collapsed)
            self.after(200, self._fit_status_pane_collapsed)

    def _schedule_fit_status_collapsed(self, _event: object=None) -> None:
        if self.show_status_var.get():
            return
        if self._fit_status_collapsed_job is not None:
            try:
                self.after_cancel(self._fit_status_collapsed_job)
            except Exception:
                pass
        self._fit_status_collapsed_job = self.after(50, self._fit_status_collapsed_run)

    def _fit_status_collapsed_run(self) -> None:
        self._fit_status_collapsed_job = None
        self._fit_status_pane_collapsed()

    def _fit_status_pane_expanded(self) -> None:
        """Set the Status pane height to fit all visible content (no clipping, no wasted band)."""
        if self.panes is None or self.status_frame is None or (not self.show_status_var.get()):
            return
        try:
            self.update_idletasks()
            sf = self.status_frame
            need = max(UI_STATUS_PANE_MIN_EXPANDED, int(sf.winfo_reqheight()))
            self.panes.paneconfigure(sf, height=need)
        except (tk.TclError, ValueError, AttributeError, TypeError):
            pass

    def _fit_status_pane_collapsed(self) -> None:
        """Shrink the middle pane so only the Status tab row shows when content is hidden."""
        if self.panes is None or self.status_frame is None or self.show_status_var.get():
            return
        try:
            self.update_idletasks()
            pw = self.panes
            sf = self.status_frame
            sf.update_idletasks()
            need = self._collapsed_status_pane_minsize()
            try:
                ah = int(sf.winfo_height())
                open_min = max(need + PANE_DRAG_OPEN_EXTRA_PX, UI_STATUS_PANE_MIN_EXPANDED + 24)
                if ah >= open_min:
                    self.show_status_var.set(True)
                    return
            except (tk.TclError, ValueError):
                pass
            try:
                pw.paneconfigure(sf, minsize=need, stretch='never')
                pw.paneconfigure(sf, height=need)
            except (tk.TclError, ValueError):
                pass
            ph = max(1, pw.winfo_height())
            sash_w = UI_PANE_SASH_WIDTH
            sashpad = UI_PANE_SASH_PAD
            try:
                sp1 = int(float(pw.sashpos(1)))
            except (tk.TclError, ValueError):
                sp1 = max(200, ph * 2 // 3)
            target0 = sp1 - need - sash_w - 2 * sashpad
            graph_min = 120
            target0 = max(target0, graph_min)
            hist_min = UI_HISTORY_PANE_MIN_EXPANDED if self.show_log_var.get() else self._collapsed_history_pane_minsize()
            target0 = min(target0, sp1 - hist_min - sash_w - 2 * sashpad)
            pw.sashpos(0, target0)
        except (tk.TclError, ValueError, AttributeError, TypeError):
            pass

    def update_log_visibility(self) -> None:
        """Show or hide history *content*; header bar stays between Status and the text area."""
        if self.history_frame is None or self.panes is None or self._history_body is None:
            return
        panes = self.panes
        history = self.history_frame
        body = self._history_body
        sep = self._history_sep
        if self.show_log_var.get():
            history.configure(padding=UI_HISTORY_FRAME_PAD_EXPANDED)
            body.grid(row=2, column=0, sticky='nsew')
            if sep is not None:
                sep.grid(row=1, column=0, sticky='ew', pady=(UI_INNER_PAD_Y_SM, UI_INNER_PAD_Y_SM))
            history.rowconfigure(2, weight=1)
            try:
                panes.paneconfigure(history, minsize=UI_HISTORY_PANE_MIN_EXPANDED, stretch='always')
            except Exception:
                pass
            try:
                panes.paneconfigure(history, height='')
            except Exception:
                pass
        else:
            history.configure(padding=UI_HISTORY_FRAME_PAD_COLLAPSED)
            body.grid_remove()
            if sep is not None:
                sep.grid_remove()
            history.rowconfigure(2, weight=0)
            try:
                self.update_idletasks()
                need = self._collapsed_history_pane_minsize()
                panes.paneconfigure(history, minsize=need, stretch='never')
                panes.paneconfigure(history, height=need)
            except Exception:
                pass
            self._schedule_fit_history_collapsed()
            self.after(50, self._fit_history_pane_collapsed)
            self.after(200, self._fit_history_pane_collapsed)

    def _schedule_fit_history_collapsed(self, _event: object=None) -> None:
        """Debounced: keep bottom pane minimal when History content is hidden (also on window resize)."""
        if self.show_log_var.get():
            return
        if self._fit_history_collapsed_job is not None:
            try:
                self.after_cancel(self._fit_history_collapsed_job)
            except Exception:
                pass
        self._fit_history_collapsed_job = self.after(50, self._fit_history_collapsed_run)

    def _fit_history_collapsed_run(self) -> None:
        self._fit_history_collapsed_job = None
        self._fit_history_pane_collapsed()

    def _fit_history_pane_collapsed(self) -> None:
        """Shrink the bottom PanedWindow pane so only the History tab row shows (no empty band)."""
        if self.panes is None or self.history_frame is None or self.show_log_var.get():
            return
        try:
            self.update_idletasks()
            pw = self.panes
            hf = self.history_frame
            hf.update_idletasks()
            need = self._collapsed_history_pane_minsize()
            try:
                ah = int(hf.winfo_height())
                open_min = max(need + PANE_DRAG_OPEN_EXTRA_PX, UI_HISTORY_PANE_MIN_EXPANDED + 24)
                if ah >= open_min:
                    self.show_log_var.set(True)
                    return
            except (tk.TclError, ValueError):
                pass
            try:
                pw.paneconfigure(hf, minsize=need, stretch='never')
                pw.paneconfigure(hf, height=need)
            except (tk.TclError, ValueError):
                pass
            ph = max(1, pw.winfo_height())
            sash_w = UI_PANE_SASH_WIDTH
            sashpad = UI_PANE_SASH_PAD
            status_min = self._status_pane_min_for_layout()
            target = ph - need - sash_w - 2 * sashpad - 1
            s0 = int(float(pw.sashpos(0)))
            lo = s0 + sash_w + 2 * sashpad + status_min
            target = max(int(target), lo)
            target = min(target, ph - 4)
            pw.sashpos(1, target)
        except (tk.TclError, ValueError, AttributeError, TypeError):
            pass

    def browse_logs_folder(self) -> None:
        """Pick the Vintage Story data or Logs folder; the app resolves client-main.log (etc.) inside."""
        initialdir = browse_initialdir_from_path(self.source_path_var.get())
        selected = filedialog.askdirectory(parent=self, title='Select Logs folder (Vintage Story data directory)', initialdir=initialdir)
        if selected:
            self._apply_browsed_log_path(selected)

    def browse_alert_sound(self) -> None:
        parent = self._settings_win
        try:
            if parent is None or not parent.winfo_exists():
                parent = self
        except Exception:
            parent = self
        initialdir = browse_initialdir_from_path(self.alert_sound_path_var.get())
        selected = filedialog.askopenfilename(parent=parent, title='Select warning sound file', initialdir=initialdir, filetypes=[('Audio', '*.wav *.mp3 *.aiff *.aif *.flac *.ogg'), ('WAV', '*.wav'), ('All files', '*.*')])
        if selected:
            self.alert_sound_path_var.set(selected)

    def browse_completion_sound(self) -> None:
        parent = self._settings_win
        try:
            if parent is None or not parent.winfo_exists():
                parent = self
        except Exception:
            parent = self
        initialdir = browse_initialdir_from_path(self.completion_sound_path_var.get())
        selected = filedialog.askopenfilename(parent=parent, title='Select completion sound file', initialdir=initialdir, filetypes=[('Audio', '*.wav *.mp3 *.aiff *.aif *.flac *.ogg'), ('WAV', '*.wav'), ('All files', '*.*')])
        if selected:
            self.completion_sound_path_var.set(selected)

    def preview_alert_sound(self) -> None:
        """Play the configured warning sound once (for Settings); ignores the Warning sound checkbox."""
        self.play_sound()

    def preview_completion_sound(self) -> None:
        """Play the configured completion sound once; ignores the Completion sound checkbox."""
        self.play_completion_sound()

    def _schedule_resize_refresh(self, evt: Optional[tk.Event]=None) -> None:
        if evt is not None and getattr(evt, 'widget', None) is not self:
            return
        if self._configure_resize_job is not None:
            try:
                self.after_cancel(self._configure_resize_job)
            except Exception:
                pass
        self._configure_resize_job = self.after(150, self._on_resize_refresh_done)

    def _on_resize_refresh_done(self) -> None:
        self._configure_resize_job = None
        self.update_time_estimates()

    def _progress_tooltip_text(self) -> str:
        """Progress bar hover: percent of estimated wait so far."""
        p = 0.0
        if self._queue_progress is not None:
            try:
                p = float(self._queue_progress['value'])
            except (tk.TclError, TypeError, ValueError):
                pass
        return f'Estimated wait so far: {p:.0f}%.'

    def _clamp_tooltip_in_host(self, host: tk.Misc, tip: tk.Toplevel, x_left: int, y_top: int, margin: int=6) -> tuple[int, int]:
        """Keep overrideredirect tooltip top-left inside the host toplevel (main or Settings)."""
        try:
            host.update_idletasks()
            tip.update_idletasks()
            tw = int(tip.winfo_reqwidth())
            th = int(tip.winfo_reqheight())
            rx = int(host.winfo_rootx())
            ry = int(host.winfo_rooty())
            rw = int(host.winfo_width())
            rh = int(host.winfo_height())
            if rw < 40 or rh < 40:
                return (x_left, y_top)
            x_left = max(rx + margin, min(x_left, rx + rw - tw - margin))
            y_top = max(ry + margin, min(y_top, ry + rh - th - margin))
        except (tk.TclError, ValueError):
            pass
        return (x_left, y_top)

    def _bind_static_tooltip(self, widget: tk.Misc, text: Union[str, Callable[[], str]]) -> None:
        state: dict[str, Optional[object]] = {'win': None, 'job': None}

        def hide(_evt: object=None) -> None:
            jid = state['job']
            if jid is not None:
                try:
                    self.after_cancel(jid)
                except Exception:
                    pass
                state['job'] = None
            tw = state['win']
            if tw is not None:
                try:
                    if isinstance(tw, tk.Toplevel) and tw.winfo_exists():
                        tw.destroy()
                except Exception:
                    pass
                state['win'] = None

        def show_delayed(_evt: object) -> None:
            hide()

            def show() -> None:
                state['job'] = None
                try:
                    if not widget.winfo_exists():
                        return
                except Exception:
                    return
                resolved = text() if callable(text) else text
                x = int(widget.winfo_rootx() + widget.winfo_width() // 2)
                y = int(widget.winfo_rooty() + widget.winfo_height() + 6)
                try:
                    host = widget.winfo_toplevel()
                except tk.TclError:
                    host = self
                tip = tk.Toplevel(host)
                tip.wm_overrideredirect(True)
                try:
                    tip.attributes('-topmost', True)
                except Exception:
                    pass
                tk.Label(tip, text=resolved, justify='left', background=UI_TOOLTIP_BG, foreground=UI_TOOLTIP_FG, padx=10, pady=8, wraplength=340).pack()
                state['win'] = tip
                tip.update_idletasks()
                tw = tip.winfo_reqwidth()
                x_left = int(x - tw // 2)
                y_top = int(y)
                x_left, y_top = self._clamp_tooltip_in_host(host, tip, x_left, y_top)
                tip.geometry(f'+{x_left}+{y_top}')
            state['job'] = self.after(420, show)
        widget.bind('<Enter>', show_delayed, add=True)
        widget.bind('<Leave>', hide, add=True)

    def _bind_main_tooltips(self) -> None:
        """Hover help for the main window (uses the same delayed toplevel as _bind_static_tooltip)."""
        bt = self._bind_static_tooltip
        bt(self.start_stop_button, 'Start or stop monitoring.')
        bt(self._lbl_log_path, 'Folder to search (not a .log file). The app opens client-main.log when present, then other client log names.')
        bt(self._path_entry, 'VintagestoryData or Logs folder path. Resolution prefers client-main.log under common layouts.')
        bt(self._btn_browse_logs, 'Pick a folder only. The app resolves client-main.log (or another matching client log) inside.')
        bt(self._settings_btn, 'Settings')
        bt(self._loading_spinner, 'Loading…')
        bt(self._graph_frame, 'Queue position over time.')
        bt(self._position_value_label, 'Smaller number = closer to the front.')
        bt(self._status_value_label, 'What the app is doing.')
        bt(self._lbl_kpi_rate, 'Rolling N = last N queue steps used for this rate (N = Rolling window under Estimation in Settings). Same idea as a “last N” or rolling average.')
        bt(self._queue_rate_value_label, 'Minutes per position for that window. Full-graph average is under Info → Global Rate. At position 0 (completed), fixed from the graph — no drift.')
        bt(self._lbl_kpi_warnings, 'Warning thresholds from Settings; muted when your position is at or below that number (or already alerted).')
        bt(self._warnings_kpi_frame, 'Same: a value grays out once your queue position is ≤ that threshold, or after that alert fired.')
        bt(self._elapsed_value_label, 'Time in queue this run: from the first connect-phase log line in this session when found, else from the first queue position line; at the front, frozen using log times (not when you opened the app).')
        bt(self._remaining_value_label, 'Estimated wait left (hidden at the front).')
        bt(self._graph_stack_frame, 'Drag edges to resize panels. Y: chart scale.')
        bt(self.graph_canvas, 'Move the mouse for time and position.')
        bt(self._status_tab_strip, 'Show or hide Info panel.')
        bt(self._lbl_status_section_title, 'Show or hide Info panel.')
        bt(self._status_tab_btn, 'Show or hide Info panel.')
        bt(self._lbl_det_global_rate, 'Average minutes per position over every queue advance in the graph (full session).')
        bt(self._lbl_det_global_rate_val, 'Mean over all downward steps in the graph; KPI Rate uses the rolling window (Estimation in Settings).')
        bt(self._lbl_det_last_change_val, 'When your position last changed.')
        bt(self._lbl_det_alert_val, 'Last threshold alert.')
        bt(self._lbl_det_path_val, 'Log file in use.')
        bt(self._history_tab_strip, 'Show or hide History.')
        bt(self._lbl_history_section_title, 'Show or hide History.')
        bt(self._history_tab_btn, 'Show or hide History.')
        bt(self.history_text, 'Session log.')

    def _bind_keyboard_shortcuts(self) -> None:
        self.bind('<Control-m>', self._shortcut_toggle_monitoring)
        self.bind('<Control-M>', self._shortcut_toggle_monitoring)

        def on_space(evt: tk.Event) -> str | None:
            w = self.focus_get()
            if w is not None:
                cls = getattr(w, 'winfo_class', lambda: '')()
                if cls in ('Text', 'TEntry', 'Entry', 'TCombobox', 'Spinbox', 'TSpinbox'):
                    return None
            self.toggle_monitoring()
            return 'break'
        self.bind('<space>', on_space)

    def _shortcut_toggle_monitoring(self, _evt: tk.Event) -> str:
        self.toggle_monitoring()
        return 'break'

    def _update_graph_y_scale_button_text(self) -> None:
        btn = self._graph_y_scale_btn
        if btn is None:
            return
        if self.graph_log_scale_var.get():
            btn.configure(text='Y → log')
        else:
            btn.configure(text='Y → linear')

    def _toggle_graph_y_scale(self) -> None:
        self.graph_log_scale_var.set(not self.graph_log_scale_var.get())
        self.redraw_graph()

    def _position_graph_y_scale_button(self, _evt: object | None=None) -> None:
        """Place Y-scale control at top-right inside the plot area (not canvas corner — avoids top margin clip)."""
        canvas = self.graph_canvas
        btn = self._graph_y_scale_btn
        if canvas is None or btn is None:
            return
        try:
            w = int(canvas.winfo_width())
        except tk.TclError:
            return
        if w <= 10:
            return
        x_right = w - GRAPH_CANVAS_PAD_RIGHT - GRAPH_Y_SCALE_BTN_INSET_X
        y_top = GRAPH_CANVAS_PAD_TOP + GRAPH_Y_SCALE_BTN_INSET_Y
        btn.place_configure(x=x_right, y=y_top, anchor='ne')

    def _on_graph_canvas_configure(self, _evt: object) -> None:
        self._position_graph_y_scale_button()
        self.redraw_graph()

    def redraw_graph(self) -> None:
        canvas = self.graph_canvas
        if canvas is None:
            return
        canvas.delete('all')
        width = int(canvas.winfo_width())
        height = int(canvas.winfo_height())
        if width <= 10 or height <= 10:
            return
        pad_left = GRAPH_CANVAS_PAD_LEFT
        pad_right = GRAPH_CANVAS_PAD_RIGHT
        pad_top = GRAPH_CANVAS_PAD_TOP
        pad_bottom = GRAPH_CANVAS_PAD_BOTTOM
        plot_w = max(1, width - pad_left - pad_right)
        plot_h = max(1, height - pad_top - pad_bottom)
        x0 = pad_left
        y0 = pad_top
        x1 = pad_left + plot_w
        y1 = pad_top + plot_h
        canvas.create_rectangle(x0, y0, x1, y1, fill=UI_GRAPH_PLOT, outline='')
        points = list(self.graph_points)
        if len(points) > MAX_DRAW_POINTS:
            step = max(1, len(points) // MAX_DRAW_POINTS)
            points = points[::step]
        self.graph_points_drawn = points
        if len(points) == 0:
            self._graph_hover_point = None
            canvas.create_text(x0 + 6, y0 + 6, anchor='nw', text='No data yet', fill=UI_GRAPH_EMPTY)
            return
        if len(points) == 1:
            t_mid = float(points[0][0])
            half = SINGLE_POINT_GRAPH_SPAN_SEC / 2.0
            t0 = t_mid - half
            t1 = t_mid + half
        else:
            t0 = float(points[0][0])
            t1 = float(points[-1][0])
            if t1 <= t0:
                t1 = t0 + 1e-06
        vals = [p for _t, p in points]
        vmin = min(vals)
        vmax = max(vals)
        if vmax == vmin:
            vmax = vmin + 1
        vmin = max(0, vmin)

        def x_of(t: float) -> float:
            return pad_left + (t - t0) / (t1 - t0) * plot_w

        def y_of(v: int) -> float:
            vv = max(vmin, min(vmax, v))
            if not self.graph_log_scale_var.get():
                frac = (vmax - vv) / max(1, vmax - vmin)
                return pad_top + frac * plot_h
            lvmin = math.log(vmin + 1.0)
            lvmax = math.log(vmax + 1.0)
            lv = math.log(vv + 1.0)
            if lvmax <= lvmin:
                frac = 0.0
            else:
                frac = (lvmax - lv) / (lvmax - lvmin)
            frac = max(0.0, min(1.0, frac))
            frac = frac ** GRAPH_LOG_GAMMA
            return pad_top + frac * plot_h
        axis_color = UI_GRAPH_AXIS
        text_color = UI_GRAPH_TEXT
        canvas.create_line(x0, y0, x0, y1, fill=axis_color)
        canvas.create_line(x0, y1, x1, y1, fill=axis_color)
        tick_step = 5
        tick_vals: list[int] = []
        start = vmin // tick_step * tick_step
        end = (vmax + tick_step - 1) // tick_step * tick_step
        for val in range(start, end + 1, tick_step):
            if vmin <= val <= vmax:
                if val == 0 and vmin > 0:
                    continue
                tick_vals.append(val)
        if vmin <= 5 <= vmax:
            tick_vals.extend([1, 2, 3, 4, 5])
        tick_vals.extend([vmin, vmax])
        tick_vals = sorted(set(tick_vals), reverse=True)
        last_y_label: Optional[float] = None
        min_label_dy = 16
        for idx, val in enumerate(tick_vals):
            y = y_of(val)
            canvas.create_line(x0 - 4, y, x0, y, fill=axis_color)
            if last_y_label is None or abs(y - last_y_label) >= min_label_dy:
                canvas.create_text(x0 - 6, y, anchor='e', text=str(val), fill=text_color)
                last_y_label = y
            if 0 < idx < len(tick_vals) - 1:
                canvas.create_line(x0, y, x1, y, fill=UI_GRAPH_GRID)
        span = t1 - t0
        if span <= 0:
            span = 1.0
        candidates = [5, 10, 15, 30, 60, 5 * 60, 10 * 60, 15 * 60, 30 * 60, 60 * 60, 2 * 60 * 60, 6 * 60 * 60]
        target_ticks = 6
        interval = candidates[-1]
        for c in candidates:
            if span / c <= target_ticks:
                interval = c
                break
        fmt = '%H:%M:%S' if interval < 60 * 60 else '%H:%M'
        first_tick = math.ceil(t0 / interval) * interval
        last_tick = math.floor(t1 / interval) * interval
        tick_times: list[float] = []
        t = first_tick
        while t <= last_tick + 1e-06:
            tick_times.append(t)
            t += interval
        if not tick_times or tick_times[0] - t0 > interval * 0.4:
            tick_times.insert(0, t0)
        if tick_times[-1] < t1 - interval * 0.4:
            tick_times.append(t1)
        _dedup: list[float] = []
        for tv in sorted(tick_times):
            xv = x_of(tv)
            if not _dedup or abs(xv - x_of(_dedup[-1])) > 2.0:
                _dedup.append(tv)
        tick_times = _dedup
        min_label_dx = max(76.0, min(130.0, plot_w / 7.5))
        last_x_label: Optional[float] = None
        for idx, t in enumerate(tick_times):
            x = x_of(t)
            label = datetime.fromtimestamp(t).strftime(fmt)
            canvas.create_line(x, y1, x, y1 + 4, fill=axis_color)
            if last_x_label is None or abs(x - last_x_label) >= min_label_dx:
                canvas.create_text(x, y1 + 14, anchor='n', text=label, fill=text_color)
                last_x_label = x
            if 0 < idx < len(tick_times) - 1:
                canvas.create_line(x, y0, x, y1, fill=UI_GRAPH_GRID)
        span_sec = t1 - t0
        if span_sec > 1e-06:
            major_xs = [x_of(float(tv)) for tv in tick_times]
            minor_candidates = (60, 120, 300, 600, 900, 1800, 3600, 7200)
            minor_step_sec = 60.0
            for step in minor_candidates:
                minor_step_sec = float(step)
                n_divs = span_sec / minor_step_sec
                if n_divs < 1.5:
                    continue
                px_per_div = plot_w / n_divs
                if px_per_div >= 5.0:
                    break
            else:
                minor_step_sec = max(60.0, span_sec / max(1.0, plot_w / 5.0))
            major_clear_px = 6.0

            def _too_close_to_major(xm: float) -> bool:
                for xa in major_xs:
                    if abs(xm - xa) <= major_clear_px:
                        return True
                return False
            m_start = math.ceil(t0 / minor_step_sec) * minor_step_sec
            m = m_start
            last_minor_x: Optional[float] = None
            while m <= t1 + 1e-06:
                xm = x_of(m)
                if x0 <= xm <= x1 and (not _too_close_to_major(xm)):
                    if last_minor_x is None or abs(xm - last_minor_x) >= 4.0:
                        canvas.create_line(xm, y1, xm, y1 + 3, fill=UI_GRAPH_MINOR_TICK, width=1)
                        last_minor_x = xm
                m += minor_step_sec
        canvas.create_text(x0 + 6, y0 + 6, anchor='nw', text=f'min {vmin}  max {vmax}', fill=text_color)
        step_vertices: list[tuple[float, int]] = []
        for i, (t, p) in enumerate(points):
            t_f = float(t)
            p_i = int(p)
            if i == 0:
                step_vertices.append((t_f, p_i))
                continue
            t_prev = float(points[i - 1][0])
            p_prev = int(points[i - 1][1])
            if t_f <= t_prev:
                continue
            if p_i != p_prev:
                step_vertices.append((t_f, p_prev))
            step_vertices.append((t_f, p_i))
        line: list[float] = []
        for t, v in step_vertices:
            line.extend([x_of(t), y_of(v)])
        if len(line) >= 4:
            canvas.create_line(*line, fill=UI_GRAPH_LINE, width=2, smooth=False)
        elif len(points) == 1 and step_vertices:
            _ts, _pv = step_vertices[0]
            _lx = x_of(_ts)
            _ly = y_of(_pv)
            canvas.create_line(x0, _ly, _lx, _ly, fill=UI_GRAPH_LINE, width=2, smooth=False)
        marker = self.current_point or points[-1]
        last_t, last_v = marker
        lx = x_of(last_t)
        ly = y_of(last_v)
        canvas.create_oval(lx - 4, ly - 4, lx + 4, ly + 4, outline='', fill=UI_GRAPH_MARKER)
        canvas.create_text(lx + 10, ly, anchor='w', text=str(last_v), fill=UI_GRAPH_TEXT)
        hp = self._graph_hover_point
        if hp is not None:
            ht, hv = hp
            hx = x_of(ht)
            hy = y_of(hv)
            canvas.create_line(hx, y0, hx, y1, fill=UI_GRAPH_HOVER_CURSOR, width=1)
            canvas.create_oval(hx - 5, hy - 5, hx + 5, hy + 5, outline=UI_GRAPH_LINE, width=2, fill=UI_GRAPH_PLOT)

    def on_graph_motion(self, evt: tk.Event) -> None:
        points = self.graph_points_drawn
        canvas = self.graph_canvas
        if canvas is None or len(points) < 1:
            return
        width = int(canvas.winfo_width())
        height = int(canvas.winfo_height())
        if width <= 10 or height <= 10:
            return
        pad_left = GRAPH_CANVAS_PAD_LEFT
        pad_right = GRAPH_CANVAS_PAD_RIGHT
        plot_w = max(1, width - pad_left - pad_right)
        x = max(pad_left, min(pad_left + plot_w, evt.x))
        t0 = float(points[0][0])
        t1 = float(points[-1][0])
        if len(points) == 1:
            half = SINGLE_POINT_GRAPH_SPAN_SEC / 2.0
            t0 = t0 - half
            t1 = t1 + half
        elif t1 <= t0:
            t1 = t0 + 1e-06
        target_t = t0 + (x - pad_left) / plot_w * (t1 - t0)
        best = points[0]
        best_dt = abs(best[0] - target_t)
        for pt in points[1:]:
            dt = abs(pt[0] - target_t)
            if dt < best_dt:
                best = pt
                best_dt = dt
        t, pos = best
        hover = (float(t), int(pos))
        if self._graph_hover_point != hover:
            self._graph_hover_point = hover
            self.redraw_graph()
        ts = datetime.fromtimestamp(t).strftime('%Y-%m-%d %H:%M:%S')
        self.show_graph_tooltip(evt.x_root, evt.y_root, f'{ts}\npos {pos}')

    def show_graph_tooltip(self, x_root: int, y_root: int, text: str) -> None:
        if self.graph_tooltip is None or not self.graph_tooltip.winfo_exists():
            tip = tk.Toplevel(self)
            tip.wm_overrideredirect(True)
            tip.attributes('-topmost', True)
            label = tk.Label(tip, text=text, justify='left', background=UI_TOOLTIP_BG, foreground=UI_TOOLTIP_FG, padx=10, pady=8)
            label.pack()
            self.graph_tooltip = tip
        else:
            label = self.graph_tooltip.winfo_children()[0]
            if isinstance(label, tk.Label):
                label.configure(text=text)
        tip = self.graph_tooltip
        tip.update_idletasks()
        x = int(x_root + 12)
        y = int(y_root + 12)
        x, y = self._clamp_tooltip_in_host(self, tip, x, y)
        tip.geometry(f'+{x}+{y}')

    def hide_graph_tooltip(self) -> None:
        if self.graph_tooltip is not None and self.graph_tooltip.winfo_exists():
            try:
                self.graph_tooltip.destroy()
            except Exception:
                pass
        self.graph_tooltip = None
        if self._graph_hover_point is not None:
            self._graph_hover_point = None
            self.redraw_graph()

    def show_popup(self, position: int, eta_display: str) -> None:
        """Warning threshold popup: position + ETA only (details stay in the session log)."""
        if self.active_popup is not None and self.active_popup.winfo_exists():
            try:
                self.active_popup.destroy()
            except Exception:
                pass
        popup = tk.Toplevel(self)
        self.active_popup = popup
        popup.title(f'{ALERT_POPUP_EMOJI_THRESHOLD} Queue alert')
        popup.attributes('-topmost', True)
        popup.resizable(False, False)
        popup.configure(padx=18, pady=18, bg=UI_BG_CARD)
        try:
            popup.transient(self)
        except Exception:
            pass
        row = tk.Frame(popup, bg=UI_BG_CARD)
        row.pack(fill='x', pady=(0, 4))
        tk.Label(row, text=ALERT_POPUP_EMOJI_THRESHOLD, font=_alert_popup_emoji_font(42), bg=UI_BG_CARD, fg=UI_TEXT_PRIMARY).pack(side='left', anchor='nw', padx=(0, 12))
        txt = tk.Frame(row, bg=UI_BG_CARD)
        txt.pack(side='left', fill='x', expand=True)
        tk.Label(txt, text=f'Position {position}', font=('TkDefaultFont', 15, 'bold'), bg=UI_BG_CARD, fg=UI_TEXT_PRIMARY).pack(anchor='w', pady=(0, 8))
        tk.Label(txt, text=f'Est. left: {eta_display}', justify='left', wraplength=360, bg=UI_BG_CARD, fg=UI_ACCENT_REMAINING, font=('TkDefaultFont', 11, 'bold')).pack(anchor='w', pady=(0, 12))
        ttk.Button(popup, text='Dismiss', command=popup.destroy).pack(anchor='e')
        popup.update_idletasks()
        width = popup.winfo_width()
        height = popup.winfo_height()
        screen_w = popup.winfo_screenwidth()
        screen_h = popup.winfo_screenheight()
        x = max(40, screen_w - width - 50)
        y = max(40, screen_h - height - 90)
        popup.geometry(f'+{x}+{y}')
        popup.after(POPUP_TIMEOUT_MS, lambda: popup.winfo_exists() and popup.destroy())

    def show_completion_popup(self) -> None:
        """Past queue wait (position 0) — visually distinct from the threshold warning popup."""
        if self.active_completion_popup is not None and self.active_completion_popup.winfo_exists():
            try:
                self.active_completion_popup.destroy()
            except Exception:
                pass
        popup = tk.Toplevel(self)
        self.active_completion_popup = popup
        popup.title(f'{ALERT_POPUP_EMOJI_COMPLETION} Past queue')
        popup.attributes('-topmost', True)
        popup.resizable(False, False)
        popup.configure(padx=18, pady=18, bg=UI_BG_CARD)
        try:
            popup.transient(self)
        except Exception:
            pass
        row = tk.Frame(popup, bg=UI_BG_CARD)
        row.pack(fill='x', pady=(0, 4))
        tk.Label(row, text=ALERT_POPUP_EMOJI_COMPLETION, font=_alert_popup_emoji_font(46), bg=UI_BG_CARD, fg=UI_TEXT_PRIMARY).pack(side='left', anchor='nw', padx=(0, 12))
        txt = tk.Frame(row, bg=UI_BG_CARD)
        txt.pack(side='left', fill='x', expand=True)
        tk.Label(txt, text='Not waiting in queue', font=('TkDefaultFont', 15, 'bold'), bg=UI_BG_CARD, fg=UI_ACCENT_STATUS).pack(anchor='w', pady=(0, 8))
        tk.Label(txt, text='Position 0 — connecting (e.g. loading mods). Get ready to join!', justify='left', wraplength=360, bg=UI_BG_CARD, fg=UI_TEXT_PRIMARY).pack(anchor='w', pady=(0, 12))
        ttk.Button(popup, text='Dismiss', command=popup.destroy).pack(anchor='e')
        popup.update_idletasks()
        width = popup.winfo_width()
        height = popup.winfo_height()
        screen_w = popup.winfo_screenwidth()
        screen_h = popup.winfo_screenheight()
        x = max(40, screen_w - width - 50)
        y = max(40, screen_h - height - 140)
        popup.geometry(f'+{x}+{y}')
        popup.after(POPUP_COMPLETION_TIMEOUT_MS, lambda: popup.winfo_exists() and popup.destroy())

    def on_close(self) -> None:
        if self._about_win is not None:
            try:
                self._about_win.grab_release()
            except Exception:
                pass
            try:
                self._about_win.destroy()
            except Exception:
                pass
            self._about_win = None
        if self._settings_win is not None:
            try:
                self._settings_win.grab_release()
            except Exception:
                pass
            try:
                self._settings_win.destroy()
            except Exception:
                pass
            self._settings_win = None
        if self.active_popup is not None:
            try:
                self.active_popup.destroy()
            except Exception:
                pass
            self.active_popup = None
        if self.active_completion_popup is not None:
            try:
                self.active_completion_popup.destroy()
            except Exception:
                pass
            self.active_completion_popup = None
        self.persist_config()
        self.stop_monitoring()
        self.stop_timer()
        self.destroy()

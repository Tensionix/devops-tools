from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
import atexit
import argparse
import ctypes
import html
import importlib
import json
import logging
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from ctypes import wintypes

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from nicegui import app as nicegui_app, run, ui  # type: ignore
from nicegui.elements.tooltip import Tooltip  # type: ignore

AUDION_CANONICAL_TOOLTIP_DELAY_MS = 1500
AUDION_CANONICAL_TOOLTIP_HIDE_DELAY_MS = 100
AUDION_CANONICAL_TOOLTIP_TRANSITION_MS = 100


def install_audion_canonical_tooltip_defaults() -> None:
    try:
        from nicegui.elements.tooltip import Tooltip as NiceGuiTooltip  # type: ignore
    except Exception:
        return
    if getattr(NiceGuiTooltip, "_audion_canonical_tooltip_defaults", False):
        return
    original_init = NiceGuiTooltip.__init__

    def audion_tooltip_init(self: Any, text: str = "") -> None:
        original_init(self, text)
        self.props["delay"] = AUDION_CANONICAL_TOOLTIP_DELAY_MS
        self.props["hide-delay"] = AUDION_CANONICAL_TOOLTIP_HIDE_DELAY_MS
        self.props["transition-duration"] = AUDION_CANONICAL_TOOLTIP_TRANSITION_MS
        self.classes("audion-tooltip")

    NiceGuiTooltip.__init__ = audion_tooltip_init  # type: ignore[method-assign]
    NiceGuiTooltip._audion_canonical_tooltip_defaults = True  # type: ignore[attr-defined]


install_audion_canonical_tooltip_defaults()


AUDION_CANONICAL_UI_CSS = """
<style id="audion-canonical-tooltip-icon-style">
  html body .q-tooltip,
  html body .audion-tooltip {
    background: rgb(23, 33, 43) !important;
    background-color: rgb(23, 33, 43) !important;
    color: #f4f8fb !important;
    border: 1px solid rgba(88, 166, 255, 0.24) !important;
    border-radius: 8px !important;
    box-shadow: 0 12px 28px rgba(0, 0, 0, 0.34) !important;
  }
  html body .q-icon.material-icons,
  html body .q-icon.material-symbols-outlined,
  html body .q-icon.material-symbols-rounded,
  html body i.material-icons,
  html body i.material-symbols-outlined,
  html body i.material-symbols-rounded,
  html body .q-btn .q-icon,
  html body .q-btn .material-icons,
  html body .q-btn .material-symbols-outlined,
  html body .q-btn .material-symbols-rounded,
  html body .q-field .q-field__append .q-icon,
  html body .q-field .q-field__prepend .q-icon,
  html body .q-item .q-icon,
  html body .q-menu .q-icon,
  html body .audion-label-icon,
  html body .audion-path-option-pin,
  html body .audion-select-option-pin {
    font-size: 14px !important;
    width: 14px !important;
    min-width: 14px !important;
    height: 14px !important;
    line-height: 14px !important;
  }
  html body .material-icons,
  html body .q-icon.material-icons {
    font-family: "Material Icons" !important;
  }
  html body .material-symbols-outlined,
  html body .q-icon.material-symbols-outlined {
    font-family: "Material Symbols Outlined" !important;
  }
  html body .material-symbols-rounded,
  html body .q-icon.material-symbols-rounded {
    font-family: "Material Symbols Rounded" !important;
  }
</style>
"""


def add_audion_canonical_ui_styles() -> None:
    ui.add_head_html(AUDION_CANONICAL_UI_CSS)



def audion_tooltip_path_text(path_value: Any) -> str:
    raw = str(path_value or "").strip()
    if not raw:
        return ""
    try:
        path = Path(raw).expanduser()
        if not path.is_absolute():
            path = ROOT / path
        return str(path)
    except Exception:
        return raw


def audion_folder_button_tooltip(folder_id: str, path_value: Any) -> str:
    key = str(folder_id or "folder").strip().lower()
    path_text = audion_tooltip_path_text(path_value)
    if getattr(settings, "language", "ru") == "ru":
        descriptions = {
            "logs": "папку логов запусков и вывода терминала",
            "report": "папку отчётов и результатов операций",
            "reports": "папку отчётов и результатов операций",
            "config": "папку конфигурации проекта: manifest, GUI-настройки и кэши",
            "state": "папку рабочего состояния GUI",
            "project": "корневую папку проекта",
            "root": "корневую папку проекта",
            "data": "папку данных проекта",
            "pipeline": "папку pipeline-артефактов и промежуточных результатов",
            "github": "папку GitHub-артефактов проекта",
            "install": "папку install/runtime-артефактов проекта",
        }
        description = descriptions.get(key, f"папку {folder_id}")
        return f"Открыть {description}: {path_text}" if path_text else f"Открыть {description}."
    descriptions = {
        "logs": "the logs folder with run and terminal output",
        "report": "the reports/results folder",
        "reports": "the reports/results folder",
        "config": "the project config folder with manifest, GUI settings, and caches",
        "state": "the GUI state folder",
        "project": "the project root folder",
        "root": "the project root folder",
        "data": "the project data folder",
        "pipeline": "the pipeline artifacts and intermediate results folder",
        "github": "the project GitHub artifacts folder",
        "install": "the project install/runtime artifacts folder",
    }
    description = descriptions.get(key, f"the {folder_id} folder")
    return f"Open {description}: {path_text}" if path_text else f"Open {description}."


def audion_terminal_action_tooltip(action: str) -> str:
    key = str(action or "").strip().lower()
    if getattr(settings, "language", "ru") == "ru":
        tips = {
            "clear_terminal_window": "Очистить только видимое окно терминала. Файлы логов, отчёты и результаты операций не удаляются.",
            "expand": "Открыть терминал в большом окне, чтобы читать длинный вывод без тесной панели.",
            "expand_log": "Открыть терминал в большом окне, чтобы читать длинный вывод без тесной панели.",
            "pin_command": "Закрепить текущую команду в истории терминала для быстрого повторного запуска.",
            "unpin_command": "Открепить текущую команду от верхней части истории терминала.",
            "clear_history": "Очистить историю команд терминала. Закреплённые команды и файлы логов не удаляются.",
            "terminal_shell": "Выбрать оболочку, в которой будут запускаться команды терминала.",
            "terminal_history": "Выбрать ранее сохранённую или закреплённую команду терминала.",
            "terminal_command": "Команда, которая будет выполнена из выбранной рабочей папки.",
            "terminal_cwd": "Рабочая папка терминала. Команда будет запущена именно отсюда.",
            "pick_folder": "Выбрать рабочую папку терминала через системный диалог.",
            "terminal_run": "Запустить введённую команду в выбранной оболочке и рабочей папке.",
            "latest_report": "Открыть последний созданный отчёт, если он уже есть.",
            "command_preview": "Показать команду, которая будет запущена с текущими параметрами, без выполнения операции.",
            "report_view": "Открыть встроенный список отчётов без перехода в проводник.",
            "close": "Закрыть большое окно терминала и вернуться к основной панели.",
        }
    else:
        tips = {
            "clear_terminal_window": "Clear only the visible terminal window. Log files, reports, and operation results are not deleted.",
            "expand": "Open the terminal in a large window for reading long output comfortably.",
            "expand_log": "Open the terminal in a large window for reading long output comfortably.",
            "pin_command": "Pin the current terminal command for quick reuse.",
            "unpin_command": "Remove the current command from the pinned command list.",
            "clear_history": "Clear terminal command history. Pinned commands and log files are not deleted.",
            "terminal_shell": "Choose the shell used to run terminal commands.",
            "terminal_history": "Pick a saved or pinned terminal command.",
            "terminal_command": "Command to run from the selected working folder.",
            "terminal_cwd": "Terminal working folder. Commands are started from here.",
            "pick_folder": "Choose the terminal working folder with the system dialog.",
            "terminal_run": "Run the entered command in the selected shell and working folder.",
            "latest_report": "Open the latest generated report, if one exists.",
            "command_preview": "Show the command that would run with the current settings, without executing it.",
            "report_view": "Open the built-in reports list without switching to the file explorer.",
            "close": "Close the large terminal window and return to the main panel.",
        }
    return tips.get(key, key.replace("_", " ").strip())


from system_core.core.ansi import terminal_lines_html
from system_core.core.config import load_yaml_or_json
from system_core.core.jobs import execute_operation
from system_core.core.manifest import CommandNode, Operation, load_manifest, operation_requires_confirmation
from system_core.core.paths import ensure_project_dirs, get_project_paths, open_folder
from system_core.core.ui_theme_catalog import DEFAULT_THEME_ID, normalize_theme_id
from system_core.core.ui_settings import load_ui_settings
from system_core.ui_nicegui.workbench import (
    WORKBENCH_FEEDBACK_CSS,
    WORKBENCH_LAYOUT_CSS,
    WORKBENCH_OVERRIDE_CSS,
    WorkbenchAdapter,
    WorkbenchConfig,
    WorkbenchHandlers,
    WorkbenchRenderer,
    WorkbenchRole,
    canonical_role,
)


paths = get_project_paths(ROOT)
ensure_project_dirs(paths)
manifest = load_manifest(paths.config / "tool_manifest.yaml")
settings_path = paths.config / "gui_settings.yaml"
settings = load_ui_settings(settings_path)
tool_info: dict[str, Any] = manifest.raw.get("tool", {})
ui_info: dict[str, Any] = manifest.raw.get("ui", {})


def _workspace_history_file() -> Path:
    return paths.config / "path_history.json"


def _startup_workspace_path(role: str, configured: str, legacy: str, default_path: Path) -> str:
    return str(default_path)


def load_workspace_route_settings() -> tuple[str, str]:
    return (
        _startup_workspace_path("source", "", "", paths.input),
        _startup_workspace_path("target", "", "", paths.output),
    )


def _yaml_string(value: Any) -> str:
    return "'" + str(value or "").replace("'", "''") + "'"


def _workspace_setting_for_disk(role: str, path_value: Any, default_path: Path) -> str:
    return ""


def display_path(path_value: Any) -> str:
    text = str(path_value or "").strip()
    if not text:
        return ""
    path = Path(text).expanduser()
    if not path.is_absolute():
        path = ROOT / path
    try:
        resolved = path.resolve()
        relative = resolved.relative_to(ROOT)
    except (OSError, ValueError):
        return str(path)
    return str(relative) or "."

def save_app_settings() -> None:
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    source_path = _workspace_setting_for_disk("source", getattr(settings, "source_path", ""), paths.input)
    destination_path = _workspace_setting_for_disk("target", getattr(settings, "destination_path", ""), paths.output)
    text = (
        "gui:\n"
        "  # Change to \"en\" for public GitHub builds.\n"
        f"  language: \"{settings.language if settings.language in {'en', 'ru'} else 'ru'}\"\n"
        f"  theme: \"{normalize_theme_id(settings.theme)}\"\n"
        f"  emoji: {str(bool(getattr(settings, 'emoji', False))).lower()}\n"
        f"  allow_runtime_switching: {str(bool(getattr(settings, 'allow_runtime_switching', True))).lower()}\n"
        f"  advanced_open: {str(bool(getattr(settings, 'advanced_open', False))).lower()}\n"
        f"  source_path: {_yaml_string(source_path)}\n"
        f"  destination_path: {_yaml_string(destination_path)}\n"
    )
    settings_path.write_text(text, encoding="utf-8", newline="\n")

settings.source_path, settings.destination_path = load_workspace_route_settings()


def _string_map(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {str(key).strip(): str(item).strip() for key, item in value.items() if str(key).strip()}


BUILTIN_THEMES: dict[str, dict[str, Any]] = {
    "code_dark": {
        "label": "Code Dark",
        "label_ru": "Code Темная",
        "mode": "dark",
        "tokens": {
            "color-background-primary": "#141413",
            "color-background-secondary": "#1f1e1a",
            "color-background-tertiary": "#0f0f0e",
            "color-text-primary": "#faf9f5",
            "color-text-secondary": "#e8e6dc",
            "color-text-tertiary": "#b0aea5",
            "color-border-tertiary": "rgba(250, 249, 245, 0.15)",
            "color-border-secondary": "rgba(250, 249, 245, 0.3)",
            "color-border-primary": "rgba(250, 249, 245, 0.4)",
            "color-accent-primary": "#d97757",
            "color-accent-secondary": "#6a9bcc",
            "color-accent-tertiary": "#788c5d",
        },
    },
    "code_graphite": {
        "label": "Code Graphite",
        "label_ru": "Code графит",
        "mode": "dark",
        "tokens": {
            "color-background-primary": "#2c2c2a",
            "color-background-secondary": "#34332f",
            "color-background-tertiary": "#141413",
            "color-text-primary": "#faf9f5",
            "color-text-secondary": "#e8e6dc",
            "color-text-tertiary": "#b0aea5",
            "color-border-tertiary": "rgba(250, 249, 245, 0.15)",
            "color-border-secondary": "rgba(250, 249, 245, 0.3)",
            "color-border-primary": "rgba(250, 249, 245, 0.4)",
            "color-accent-primary": "#d97757",
            "color-accent-secondary": "#6a9bcc",
            "color-accent-tertiary": "#788c5d",
        },
    },
    "code_light": {
        "label": "Code Light",
        "label_ru": "Code светлая",
        "mode": "light",
        "tokens": {
            "color-background-primary": "#faf9f5",
            "color-background-secondary": "#fffdf8",
            "color-background-tertiary": "#f1efe8",
            "color-text-primary": "#141413",
            "color-text-secondary": "#5f5e5a",
            "color-text-tertiary": "#888780",
            "color-border-tertiary": "rgba(20, 20, 19, 0.15)",
            "color-border-secondary": "rgba(20, 20, 19, 0.3)",
            "color-border-primary": "rgba(20, 20, 19, 0.4)",
            "color-accent-primary": "#d97757",
            "color-accent-secondary": "#6a9bcc",
            "color-accent-tertiary": "#788c5d",
        },
    },
    "code_warm": {
        "label": "Code Warm",
        "label_ru": "Code теплая",
        "mode": "light",
        "tokens": {
            "color-background-primary": "#fffdf8",
            "color-background-secondary": "#faf9f5",
            "color-background-tertiary": "#e8e6dc",
            "color-text-primary": "#141413",
            "color-text-secondary": "#444441",
            "color-text-tertiary": "#888780",
            "color-border-tertiary": "rgba(20, 20, 19, 0.15)",
            "color-border-secondary": "rgba(20, 20, 19, 0.3)",
            "color-border-primary": "rgba(20, 20, 19, 0.4)",
            "color-accent-primary": "#d97757",
            "color-accent-secondary": "#6a9bcc",
            "color-accent-tertiary": "#788c5d",
        },
    },
    "audion_light": {
        "label": "Audion Light",
        "label_ru": "Audion светлая",
        "mode": "light",
        "tokens": {
            "color-background-primary": "#f7fbff",
            "color-background-secondary": "#ffffff",
            "color-background-tertiary": "#e6f1fb",
            "color-text-primary": "#102033",
            "color-text-secondary": "#36546f",
            "color-text-tertiary": "#6f879c",
            "color-border-tertiary": "rgba(4, 44, 83, 0.15)",
            "color-border-secondary": "rgba(4, 44, 83, 0.3)",
            "color-border-primary": "rgba(4, 44, 83, 0.4)",
            "color-accent-primary": "#378ADD",
            "color-accent-secondary": "#1D9E75",
            "color-accent-tertiary": "#534AB7",
        },
    },
    "audion_dark": {
        "label": "Audion Dark",
        "label_ru": "Audion Темная",
        "mode": "dark",
        "tokens": {
            "color-background-primary": "#08131f",
            "color-background-secondary": "#102033",
            "color-background-tertiary": "#050b12",
            "color-text-primary": "#f7fbff",
            "color-text-secondary": "#d7e7f6",
            "color-text-tertiary": "#9bb7cf",
            "color-border-tertiary": "rgba(247, 251, 255, 0.15)",
            "color-border-secondary": "rgba(247, 251, 255, 0.3)",
            "color-border-primary": "rgba(247, 251, 255, 0.4)",
            "color-accent-primary": "#6a9bcc",
            "color-accent-secondary": "#5DCAA5",
            "color-accent-tertiary": "#7F77DD",
        },
    },
    "asar_dark": {
        "label": "Asar Dark",
        "label_ru": "Asar Темная",
        "mode": "dark",
        "tokens": {
            "color-background-primary": "#181a1f",
            "color-background-secondary": "#20242b",
            "color-background-tertiary": "#0f1115",
            "color-text-primary": "#f4f7fb",
            "color-text-secondary": "#d6dde7",
            "color-text-tertiary": "#9aa7b8",
            "color-border-tertiary": "rgba(244, 247, 251, 0.15)",
            "color-border-secondary": "rgba(244, 247, 251, 0.3)",
            "color-border-primary": "rgba(244, 247, 251, 0.4)",
            "color-accent-primary": "#85B7EB",
            "color-accent-secondary": "#9FE1CB",
            "color-accent-tertiary": "#CECBF6",
        },
    },
}


def _normalize_theme(theme_id: str, theme_data: dict[str, Any]) -> dict[str, Any]:
    return {
        "label": str(theme_data.get("label") or theme_id).strip(),
        "label_ru": str(theme_data.get("label_ru") or theme_data.get("label") or theme_id).strip(),
        "mode": "dark" if str(theme_data.get("mode", "dark")).lower() == "dark" else "light",
        "tokens": _string_map(theme_data.get("tokens", {})),
    }


def builtin_themes() -> dict[str, dict[str, Any]]:
    return {
        theme_id: _normalize_theme(theme_id, theme_data)
        for theme_id, theme_data in BUILTIN_THEMES.items()
    }


def load_ui_colors(path: Path) -> dict[str, Any]:
    data = load_yaml_or_json(path) if path.exists() else {}
    if not isinstance(data, dict):
        data = {}
    themes: dict[str, dict[str, Any]] = builtin_themes()
    themes_raw = data.get("themes", {})
    if not isinstance(themes_raw, dict):
        themes_raw = {}
    for theme_id, theme_data in themes_raw.items():
        if not isinstance(theme_data, dict):
            continue
        normalized_id = normalize_theme_id(theme_id, default="")
        if not normalized_id:
            continue
        normalized = _normalize_theme(normalized_id, theme_data)
        if normalized_id in themes:
            base = themes[normalized_id]
            normalized["tokens"] = {**_string_map(base.get("tokens", {})), **normalized["tokens"]}
        themes[normalized_id] = normalized
    return {
        "ramps": data.get("ramps", {}) if isinstance(data.get("ramps", {}), dict) else {},
        "tokens": _string_map(data.get("tokens", {})),
        "themes": themes,
    }


ui_colors = load_ui_colors(paths.config / "ui_colors.yaml")


def tolerate_missing_process_pool() -> None:
    """Keep NiceGUI alive when multiprocessing is blocked by the environment.

    NiceGUI initializes a process pool even when the GUI only uses thread/io-bound
    jobs. Some portable, sandboxed, or enterprise Windows environments reject the
    underlying multiprocessing handles, but the shell can still work without CPU
    pool tasks.
    """
    try:
        import nicegui.run as nicegui_run  # type: ignore
    except Exception:
        return

    original_setup = getattr(nicegui_run, "setup", None)
    if not callable(original_setup):
        return

    def safe_setup() -> None:
        try:
            original_setup()
        except (OSError, PermissionError) as exc:
            logging.warning("NiceGUI process pool disabled: %s", exc)
            nicegui_run.process_pool = None

    nicegui_run.setup = safe_setup


tolerate_missing_process_pool()

LABELS = {
    "ru": {
        "workspace": "Рабочие папки",
        "operations": "Операции",
        "maintenance": "Обслуживание",
        "surface_os": "Инструменты ОС",
        "surface_device": "Устройства",
        "surface_os_tooltip": "Инструменты Windows: PowerShell/runtime, сетевые подключения, WSL, политики, рабочая область и очистка.",
        "surface_device_tooltip": "Устройства Windows: сетевые адаптеры, Wi-Fi-профили, диагностика, драйверы, аудиоустройства и накопители.",
        "surface_os_settings": "Настройки ОС",
        "surface_os_settings_tooltip": "Перенос и настройка того, что не возвращается после переустановки Windows: ключи, сертификаты, шрифты, оболочка и доступы из конфигурации, плюс обслуживание и очистка.",
        "command_section_os_maintenance": "Обслуживание",
        "command_section_os_core": "Ядро Windows",
        "command_section_os_network": "Сеть",
        "command_section_os_browsers": "Браузеры",
        "command_section_os_platforms": "WSL и виртуализация",
        "command_section_os_policy": "Политики Windows",
        "command_section_os_personal": "Ключи, шрифты и настройки Windows",
        "command_section_os_personal_tooltip": "Импорт и экспорт того, что не возвращается само после переустановки: ключи SSH, сертификаты, файлы доступов из конфигурации, шрифты пользователя и настройки оболочки. Для переезда в другую систему.",
        "command_section_os_workspace": "Рабочая область",
        "command_section_os_general": "Инструменты ОС",
        "command_section_device_network": "Сетевые устройства",
        "command_section_device_diagnostics": "Диагностика устройств",
        "command_section_device_drivers": "Драйверы",
        "command_section_device_audio": "Аудиоустройства",
        "command_section_device_storage": "Накопители",
        "command_section_device_general": "Устройства",
        "status": "Статус",
        "log": "Журнал операции",
        "idle": "Ожидание",
        "running": "Выполняется",
        "done": "Готово",
        "error": "Ошибка",
        "cancel": "Отменить",
        "another_running": "Другая операция уже выполняется.",
        "confirm_title": "Подтвердите действие",
        "confirm_note": "Действие может изменить систему или рабочую область; при необходимости появится UAC-запрос.",
        "confirm_impact_title": "Что произойдёт",
        "confirm_irreversible_note": "Если это разрушительная операция, откат возможен только из backup или вручную.",
        "confirm_parameters_note": "Перед запуском проверьте выбранные поля и путь назначения.",
        "confirm_run_dangerous": "Понимаю, запустить",
        "run": "Запустить",
        "back": "Назад",
        "selected_operation": "Выбрана команда",
        "open_menu": "Открыть",
        "parameters": "Параметры",
        "advanced": "Дополнительно",
        "actions": "Команды",
        "command_meta_confirm": "Требует подтверждение",
        "command_meta_dangerous": "Перед запуском появится предохранительная плашка; операция может изменить систему или управляемые файлы.",
        "command_meta_opens_form": "Откроется форма параметров",
        "command_meta_uses_parameters": "Использует параметры выше",
        "section_account": "Учётка",
        "section_action": "Что сделать",
        "section_advanced": "Дополнительно",
        "section_apps": "Приложения",
        "section_backup": "Резервные копии",
        "section_distro": "Дистрибутив",
        "section_encoding": "Кодирование",
        "section_format": "Формат",
        "section_network": "Сеть",
        "section_options": "Опции",
        "section_output": "Результат",
        "section_packages": "Пакеты",
        "section_parameters": "Параметры",
        "section_preset": "Профиль",
        "section_profile": "Профиль",
        "section_run": "Запуск",
        "section_security": "Безопасность",
        "section_source": "Источник",
        "section_target": "Назначение",
        "close": "Закрыть",
        "logs": "Журналы",
        "report": "Отчёт",
        "config": "CONFIG",
        "expand": "Развернуть",
        "copy_terminal_log": "Копировать журнал",
        "terminal_log_copied": "Журнал скопирован: {count} строк.",
        "terminal_log_empty": "Журнал пуст.",
        "terminal_log_copy_failed": "Не удалось скопировать журнал.",
        "clear_terminal_window": "Очистить окно терминала",
        "add_files": "Добавить файлы...",
        "add_folder": "Добавить папку...",
        "file_list": "Список файлов",
        "file_list_button": "Список",
        "file_list_empty": "В INPUT нет файлов.",
        "file_list_missing": "INPUT не найден: {path}",
        "file_list_ready": "Список файлов создан: {count}.",
        "stage_files": "Добавление файлов в input",
        "stage_folder": "Добавление папки в input",
        "picker_cancelled": "Выбор отменен.",
        "operation_done": "Операция завершена.",
        "operation_failed": "Операция завершилась с кодом {code}.",
        "select_required": "Выберите хотя бы один пункт: {field}",
        "refresh_options": "Обновить список",
        "browse": "Выбрать...",
        "empty_section": "В этом разделе пока нет команд.",
        "terminal_command": "Команда",
        "terminal_history": "История команд",
        "terminal_history_empty": "Нет сохранённых команд",
        "terminal_cwd": "CWD",
        "terminal_location": "Локация",
        "terminal_shell": "Оболочка",
        "terminal_run": "ВЫПОЛНИТЬ",
        "terminal_file": "Файл",
        "terminal_folder": "Папка",
        "pick_folder": "Папка",
        "pick_file": "Файл",
        "pin_command": "Закрепить",
        "unpin_command": "Открепить",
        "clear_history": "Очистить",
        "clear_command_cache": "Кэш",
        "history_cleared": "История команд очищена; закреплённые команды сохранены.",
        "command_cache_cleared": "Кэш команд очищен.",
        "command_required": "Введите команду.",
        "source_folder": "Источник",
        "target_folder": "Назначение",
        "source_selected": "Источник выбран.",
        "target_selected": "Назначение выбрано.",
        "source_folder_missing": "Источник не найден: {path}",
        "add_file_short": "Добавить файл...",
        "clear_io_short": "Сбросить",
        "delete_io_short": "Удалить",
        "path_pinned": "Путь закреплен.",
        "path_unpinned": "Закрепление снято.",
        "path_required": "Выберите путь.",
        "theme": "Тема",
        "theme_saved": "Тема сохранена. Перезагружаю интерфейс.",
        "lang_switch": "EN",
    },
    "en": {
        "workspace": "Workspace folders",
        "operations": "Operations",
        "maintenance": "Maintenance",
        "surface_os": "OS Tools",
        "surface_device": "Device Tools",
        "surface_os_tooltip": "Windows software tools: runtime, network stack, WSL, policy, workspace and cleanup.",
        "surface_device_tooltip": "Device tools: adapters, Wi-Fi profiles, diagnostics, drivers, audio and storage.",
        "surface_os_settings": "OS Settings",
        "surface_os_settings_tooltip": "Move and configure what a Windows reinstall does not bring back: keys, certificates, fonts, shell and configured access, plus maintenance and cleanup.",
        "command_section_os_maintenance": "Maintenance",
        "command_section_os_core": "Windows Core",
        "command_section_os_network": "Network Stack",
        "command_section_os_browsers": "Browsers",
        "command_section_os_platforms": "WSL and Virtualization",
        "command_section_os_policy": "Windows Policy",
        "command_section_os_personal": "Keys, Fonts and Windows Settings",
        "command_section_os_personal_tooltip": "Import and export of what a reinstall does not bring back: SSH keys, certificates, the files named by ssh and rclone configuration, user fonts and shell settings. For moving to another system.",
        "command_section_os_workspace": "Workspace Tools",
        "command_section_os_general": "OS Tools",
        "command_section_device_network": "Network Devices",
        "command_section_device_diagnostics": "Device Diagnostics",
        "command_section_device_drivers": "Drivers",
        "command_section_device_audio": "Audio Devices",
        "command_section_device_storage": "Storage",
        "command_section_device_general": "Device Tools",
        "status": "Status",
        "log": "Operation log",
        "idle": "Idle",
        "running": "Running",
        "done": "Done",
        "error": "Error",
        "cancel": "Cancel",
        "another_running": "Another operation is already running.",
        "confirm_title": "Confirm action",
        "confirm_note": "This action may change the system or workspace; a UAC prompt may appear when needed.",
        "confirm_impact_title": "What will happen",
        "confirm_irreversible_note": "If this is a destructive operation, rollback is only possible from backup or manually.",
        "confirm_parameters_note": "Review selected fields and destination paths before starting.",
        "confirm_run_dangerous": "I understand, run",
        "run": "Run",
        "back": "Back",
        "selected_operation": "Selected command",
        "open_menu": "Open",
        "parameters": "Parameters",
        "advanced": "Advanced",
        "actions": "Commands",
        "command_meta_confirm": "Confirmation required",
        "command_meta_dangerous": "A safety confirmation appears before running; this command can change the system or managed files.",
        "command_meta_opens_form": "Opens parameter form",
        "command_meta_uses_parameters": "Uses parameters above",
        "section_account": "Account",
        "section_action": "What to do",
        "section_advanced": "Advanced",
        "section_apps": "Applications",
        "section_backup": "Backups",
        "section_distro": "Distribution",
        "section_encoding": "Encoding",
        "section_format": "Format",
        "section_network": "Network",
        "section_options": "Options",
        "section_output": "Output",
        "section_packages": "Packages",
        "section_parameters": "Parameters",
        "section_preset": "Profile",
        "section_profile": "Profile",
        "section_run": "Run",
        "section_security": "Security",
        "section_source": "Source",
        "section_target": "Target",
        "close": "Close",
        "logs": "Logs",
        "report": "Report",
        "config": "CONFIG",
        "expand": "Expand",
        "copy_terminal_log": "Copy log",
        "terminal_log_copied": "Log copied: {count} lines.",
        "terminal_log_empty": "Log is empty.",
        "terminal_log_copy_failed": "Could not copy log.",
        "clear_terminal_window": "Clear terminal window",
        "add_files": "Add files...",
        "add_folder": "Add folder...",
        "file_list": "File List",
        "file_list_button": "List",
        "file_list_empty": "INPUT has no files.",
        "file_list_missing": "INPUT was not found: {path}",
        "file_list_ready": "File list generated: {count}.",
        "stage_files": "Adding files to input",
        "stage_folder": "Adding folder to input",
        "picker_cancelled": "Selection cancelled.",
        "operation_done": "Operation finished.",
        "operation_failed": "Operation finished with exit code {code}.",
        "select_required": "Select at least one item: {field}",
        "refresh_options": "Refresh list",
        "browse": "Browse...",
        "empty_section": "This section does not have commands yet.",
        "terminal_command": "Command",
        "terminal_history": "Command history",
        "terminal_history_empty": "No saved commands",
        "terminal_cwd": "CWD",
        "terminal_location": "Location",
        "terminal_shell": "Shell",
        "terminal_run": "RUN",
        "terminal_file": "File",
        "terminal_folder": "Folder",
        "pick_folder": "Folder",
        "pick_file": "File",
        "pin_command": "Pin",
        "unpin_command": "Unpin",
        "clear_history": "History",
        "clear_command_cache": "Cache",
        "history_cleared": "Command history cleared; pinned commands were kept.",
        "command_cache_cleared": "Command cache cleared.",
        "command_required": "Enter a command.",
        "source_folder": "Source",
        "target_folder": "Target",
        "source_selected": "Source selected.",
        "target_selected": "Target selected.",
        "source_folder_missing": "Source was not found: {path}",
        "add_file_short": "Add file...",
        "clear_io_short": "Reset",
        "delete_io_short": "Delete",
        "path_pinned": "Path pinned.",
        "path_unpinned": "Path unpinned.",
        "path_required": "Choose a path.",
        "theme": "Theme",
        "theme_saved": "Theme saved. Reloading UI.",
        "lang_switch": "RU",
    },
}

PICKER_BOOTSTRAP = r"""
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
try {
  Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public static class AudionDpiAwareness {
  [DllImport("user32.dll")]
  public static extern bool SetProcessDpiAwarenessContext(IntPtr dpiContext);
  [DllImport("shcore.dll")]
  public static extern int SetProcessDpiAwareness(int value);
}
"@
  try { [AudionDpiAwareness]::SetProcessDpiAwarenessContext([IntPtr](-4)) | Out-Null }
  catch { [AudionDpiAwareness]::SetProcessDpiAwareness(2) | Out-Null }
} catch {}
Add-Type -AssemblyName System.Windows.Forms
[System.Windows.Forms.Application]::EnableVisualStyles()
"""

TERMINAL_HISTORY_PATH = paths.config / "terminal_commands.json"
TERMINAL_HISTORY_LIMIT = 200
TERMINAL_MAX_LINES = 1500
TOOLTIP_SHOW_DELAY_MS = 1500
TOOLTIP_HIDE_DELAY_MS = 100
VISIBLE_DESCRIPTION_MAX_CHARS = 150
PATH_HISTORY_LIMIT = 100


def clean_terminal_commands(items: Any) -> list[str]:
    result: list[str] = []
    if not isinstance(items, list):
        return result
    for item in items:
        text = str(item).strip()
        if text and text not in result:
            result.append(text)
    return result[:TERMINAL_HISTORY_LIMIT]


def resolved_terminal_cwd(value: Any) -> str:
    """Absolute terminal CWD, falling back to the project root.

    The project is portable, so a cached folder can outlive the copy that produced it.
    A relative value is read against the current ROOT, and anything that is no longer a
    directory resets to the start state instead of failing on the first command.
    """
    text = str(value or "").strip()
    if not text:
        return str(ROOT)
    candidate = Path(os.path.expandvars(text)).expanduser()
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    try:
        candidate = candidate.resolve()
    except OSError:
        return str(ROOT)
    return str(candidate) if candidate.is_dir() else str(ROOT)


def stored_terminal_cwd(value: Any) -> str:
    """Terminal CWD as written to disk: project-local folders stay relative to ROOT."""
    resolved = Path(resolved_terminal_cwd(value))
    try:
        return str(resolved.relative_to(Path(ROOT).resolve()))
    except ValueError:
        return str(resolved)


def load_terminal_cache() -> dict[str, Any]:
    default = {"history": [], "pinned": [], "last": "", "shell": "pwsh", "cwd": str(ROOT)}
    if not TERMINAL_HISTORY_PATH.exists():
        return default
    try:
        raw = json.loads(TERMINAL_HISTORY_PATH.read_text(encoding="utf-8"))
    except Exception:
        return default
    if not isinstance(raw, dict):
        return default
    shell = str(raw.get("shell") or default["shell"]).strip().lower()
    if shell not in {"pwsh", "cmd"}:
        shell = "pwsh"
    cwd = resolved_terminal_cwd(raw.get("cwd"))
    return {
        "history": clean_terminal_commands(raw.get("history", [])),
        "pinned": clean_terminal_commands(raw.get("pinned", [])),
        "last": str(raw.get("last") or "").strip(),
        "shell": shell,
        "cwd": cwd,
    }


initial_terminal_cache = load_terminal_cache()

state: dict[str, Any] = {
    "running": False,
    "cancel": False,
    "progress": 0.0,
    "status": "",
    "lines": [],
    "log_version": 0,
    "terminal_generation": 0,
    "terminal_line_total": 0,
    "exit_code": None,
    "command_path": [],
    "pending_command": None,
    "command_switchers": {},
    "command_surface": "os",
    "browser_bookmarks_action": "status",
    "browser_bookmarks_selected": ["chrome"],
    "browser_bookmarks_single": "chrome",
    "browser_bookmarks_import_kind": "html",
    "browser_bookmarks_location_mode": "system",
    "browser_bookmarks_backup_path": "",
    "browser_bookmarks_html_path": "",
    "browser_bookmarks_create_rollback": True,
    "browser_bookmarks_unc_source_server": "",
    "browser_bookmarks_unc_source_share": "",
    "browser_bookmarks_unc_source_subpath": "",
    "browser_bookmarks_unc_target_server": "",
    "browser_bookmarks_unc_target_share": "",
    "browser_bookmarks_unc_target_subpath": "",
    "field_values": {},
    "terminal_cache": initial_terminal_cache,
    "terminal_command": "",
    "terminal_shell": str(initial_terminal_cache.get("shell") or "pwsh"),
    "terminal_cwd": str(initial_terminal_cache.get("cwd") or ROOT),
    "source_path": str(getattr(settings, "source_path", "") or ""),
    "destination_path": str(getattr(settings, "destination_path", "") or ""),
    "workspace_feedback": {},
}

dynamic_option_cache: dict[str, tuple[float, list[Any]]] = {}
SMB_LOGIN_CACHE_PATH = paths.config / "smb_network_logins.json"
SMB_PAIR_SEPARATOR = "\t"
SMB_LOGIN_CACHE_LIMIT = 100


def smb_clean_computer(value: Any) -> str:
    return str(value or "").strip().strip("\\/")


def smb_clean_user(value: Any) -> str:
    return str(value or "").strip()


def smb_record_key(computer: Any, user: Any) -> str:
    return f"{smb_clean_computer(computer)}{SMB_PAIR_SEPARATOR}{smb_clean_user(user)}"


def smb_record_identity(record: dict[str, str]) -> str:
    return (
        smb_clean_computer(record.get("computer", "")).casefold()
        + SMB_PAIR_SEPARATOR
        + smb_clean_user(record.get("user", "")).casefold()
    )


def smb_record_from_key(key: Any) -> dict[str, str] | None:
    text = str(key or "")
    if SMB_PAIR_SEPARATOR not in text:
        return None
    computer, user = text.split(SMB_PAIR_SEPARATOR, 1)
    computer = smb_clean_computer(computer)
    user = smb_clean_user(user)
    if not computer or not user:
        return None
    return {"computer": computer, "user": user}


def load_smb_login_records() -> list[dict[str, str]]:
    if not SMB_LOGIN_CACHE_PATH.exists():
        return []
    try:
        raw = json.loads(SMB_LOGIN_CACHE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    records_raw = raw.get("records", raw) if isinstance(raw, dict) else raw
    if not isinstance(records_raw, list):
        return []
    records: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in records_raw:
        if not isinstance(item, dict):
            continue
        record = {
            "computer": smb_clean_computer(item.get("computer")),
            "user": smb_clean_user(item.get("user")),
        }
        if not record["computer"] or not record["user"]:
            continue
        identity = smb_record_identity(record)
        if identity in seen:
            continue
        seen.add(identity)
        records.append(record)
        if len(records) >= SMB_LOGIN_CACHE_LIMIT:
            break
    return records


def save_smb_login_records(records: list[dict[str, str]]) -> None:
    clean_records: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in records:
        record = {
            "computer": smb_clean_computer(item.get("computer")),
            "user": smb_clean_user(item.get("user")),
        }
        if not record["computer"] or not record["user"]:
            continue
        identity = smb_record_identity(record)
        if identity in seen:
            continue
        seen.add(identity)
        clean_records.append(record)
        if len(clean_records) >= SMB_LOGIN_CACHE_LIMIT:
            break
    if not clean_records:
        try:
            SMB_LOGIN_CACHE_PATH.unlink()
        except FileNotFoundError:
            pass
        except OSError:
            SMB_LOGIN_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            SMB_LOGIN_CACHE_PATH.write_text(
                json.dumps({"records": []}, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        return
    SMB_LOGIN_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    SMB_LOGIN_CACHE_PATH.write_text(
        json.dumps({"records": clean_records}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def upsert_smb_login_record(computer: Any, user: Any) -> str:
    record = {"computer": smb_clean_computer(computer), "user": smb_clean_user(user)}
    if not record["computer"] or not record["user"]:
        return ""
    identity = smb_record_identity(record)
    records = [item for item in load_smb_login_records() if smb_record_identity(item) != identity]
    save_smb_login_records([record, *records])
    return smb_record_key(record["computer"], record["user"])


def delete_smb_login_record(record_key: Any) -> bool:
    record = smb_record_from_key(record_key)
    if not record:
        return False
    identity = smb_record_identity(record)
    current = load_smb_login_records()
    records = [item for item in current if smb_record_identity(item) != identity]
    if len(records) == len(current):
        return False
    save_smb_login_records(records)
    return True


def clear_smb_login_records() -> None:
    save_smb_login_records([])


def tr(key: str, **kwargs: Any) -> str:
    lang = settings.language if settings.language in LABELS else "en"
    text = LABELS.get(lang, LABELS["en"]).get(key, key)
    return text.format(**kwargs) if kwargs else text


RISK_LEVEL_LABELS = {
    "readonly": {
        "ru": "Уровень риска: только чтение/диагностика.",
        "en": "Risk level: read-only diagnostics.",
    },
    "project_write": {
        "ru": "Уровень риска: запись в папку проекта.",
        "en": "Risk level: writes inside the project folder.",
    },
    "user_write": {
        "ru": "Уровень риска: изменение профиля пользователя.",
        "en": "Risk level: changes the user profile.",
    },
    "system_change": {
        "ru": "Уровень риска: изменение системного состояния Windows (политики, компоненты, гипервизор и т.п.).",
        "en": "Risk level: changes Windows system state (policies, features, hypervisor, etc.).",
    },
    "destructive": {
        "ru": "Уровень риска: destructive-действие с удалением, unregister или перезаписью.",
        "en": "Risk level: destructive delete, unregister, or overwrite action.",
    },
    "secret_export": {
        "ru": "Уровень риска: экспорт чувствительных данных.",
        "en": "Risk level: exports sensitive data.",
    },
}


def risk_level_text(risk_level: str) -> str:
    value = str(risk_level or "").strip()
    if not value:
        return ""
    language = settings.language if settings.language in LABELS else "en"
    labels = RISK_LEVEL_LABELS.get(value)
    if labels:
        return labels.get(language, labels["en"])
    return f"Risk level: {value}"


def normalize_visible_text(text: str) -> str:
    return " ".join(str(text or "").split())


def compact_visible_description(text: str) -> str:
    value = normalize_visible_text(text)
    if len(value) <= VISIBLE_DESCRIPTION_MAX_CHARS:
        return value

    min_break = 48
    for separator in (". ", "! ", "? ", "; ", ": ", ", "):
        position = value.find(separator)
        if min_break <= position + len(separator) <= VISIBLE_DESCRIPTION_MAX_CHARS:
            return value[: position + 1].strip()

    cut = value[:VISIBLE_DESCRIPTION_MAX_CHARS].rstrip()
    last_space = cut.rfind(" ")
    if last_space >= min_break:
        cut = cut[:last_space]
    return cut.rstrip(" ,;:") + "..."


def description_tooltip_text(description: str, meta_lines: list[str] | None = None) -> str:
    lines: list[str] = []
    full_description = normalize_visible_text(description)
    if full_description:
        lines.append(full_description)
    for line in meta_lines or []:
        normalized = normalize_visible_text(line)
        if normalized and normalized not in lines:
            lines.append(normalized)
    return "\n".join(lines)


def em(key: str) -> str:
    if not bool(getattr(settings, "emoji", False)):
        return ""
    return {
        "workspace": "📁 ",
        "operations": "⚙ ",
        "maintenance": "🧰 ",
        "status": "● ",
        "log": "🖥 ",
    }.get(key, "")


def app_title() -> str:
    return str(ui_info.get("title") or tool_info.get("name") or "Audion GUI Tool")


def active_theme() -> str:
    theme_id = normalize_theme_id(settings.theme)
    themes = ui_colors["themes"]
    if theme_id in themes:
        return theme_id
    return DEFAULT_THEME_ID if DEFAULT_THEME_ID in themes else next(iter(themes))


def active_theme_data() -> dict[str, Any]:
    return dict(ui_colors["themes"][active_theme()])


def active_theme_mode() -> str:
    return str(active_theme_data().get("mode", "dark"))


def theme_label(theme_id: str) -> str:
    theme_data = ui_colors["themes"].get(theme_id, {})
    label_key = "label_ru" if settings.language == "ru" else "label"
    return str(theme_data.get(label_key) or theme_data.get("label") or theme_id)


def theme_options() -> dict[str, str]:
    return {theme_id: theme_label(theme_id) for theme_id in ui_colors["themes"]}


def set_theme(theme_id: Any) -> None:
    selected = normalize_theme_id(theme_id)
    if selected not in ui_colors["themes"]:
        return
    settings.theme = selected
    save_app_settings()
    safe_notify(tr("theme_saved"), "positive")
    reload_ui()


def theme_change_handler(event: Any) -> None:
    set_theme(getattr(event, "value", None))

def reload_ui() -> None:
    ui.run_javascript(
        """
        (() => {
          try {
            if ('scrollRestoration' in window.history) {
              window.history.scrollRestoration = 'manual';
            }
            window.sessionStorage.setItem('audion_force_scroll_top', '1');
            window.scrollTo(0, 0);
            document.documentElement.scrollTop = 0;
            document.body.scrollTop = 0;
          } catch (error) {}
          window.location.reload();
        })();
        """
    )

def theme_variables() -> dict[str, str]:
    variables: dict[str, str] = {}
    for ramp_name, stops in ui_colors["ramps"].items():
        if not isinstance(stops, dict):
            continue
        for stop, color in stops.items():
            variables[f"color-{ramp_name}-{stop}"] = str(color).strip()
    variables.update(ui_colors["tokens"])
    variables.update(_string_map(active_theme_data().get("tokens", {})))
    variables.setdefault("color-background-primary", "#141413")
    variables.setdefault("color-background-secondary", "#1f1e1a")
    variables.setdefault("color-background-tertiary", "#0f0f0e")
    variables.setdefault("color-text-primary", "#faf9f5")
    variables.setdefault("color-text-secondary", "#e8e6dc")
    variables.setdefault("color-text-tertiary", "#b0aea5")
    variables.setdefault("color-border-tertiary", "rgba(250, 249, 245, 0.15)")
    variables.setdefault("color-border-secondary", "rgba(250, 249, 245, 0.3)")
    variables.setdefault("color-border-primary", "rgba(250, 249, 245, 0.4)")
    variables.setdefault("color-accent-primary", "#d97757")
    variables.setdefault("font-sans", "Inter, Segoe UI, Arial, sans-serif")
    variables.setdefault("font-mono", "Cascadia Mono, Consolas, monospace")
    variables.setdefault("border-radius-md", "8px")
    return variables


def add_log(message: str) -> None:
    if not str(message).strip():
        return
    state["lines"].append(str(message).rstrip())
    state["lines"] = state["lines"][-TERMINAL_MAX_LINES:]
    state["terminal_line_total"] = int(state.get("terminal_line_total", 0)) + 1
    state["log_version"] = int(state["log_version"]) + 1


def reset_terminal_fields() -> dict[str, Any]:
    return {
        "lines": [],
        "terminal_generation": int(state.get("terminal_generation", 0)) + 1,
        "terminal_line_total": 0,
        "log_version": int(state["log_version"]) + 1,
    }


def clear_terminal_window() -> None:
    state.update(reset_terminal_fields())


def terminal_log_text() -> str:
    return "\n".join(str(line).rstrip() for line in state.get("lines", [])).rstrip()


def copy_terminal_log_to_clipboard() -> None:
    text = terminal_log_text()
    if not text.strip():
        safe_notify(tr("terminal_log_empty"), "warning")
        return
    script = "$ErrorActionPreference = 'Stop'; $value = [Console]::In.ReadToEnd(); Set-Clipboard -Value $value"
    try:
        result = subprocess.run(
            [*resolve_dialog_powershell(), script],
            input=text,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            creationflags=hidden_subprocess_flags(),
            startupinfo=hidden_subprocess_startupinfo(),
        )
        if result.returncode != 0:
            message = (result.stderr or result.stdout or f"exit code {result.returncode}").strip()
            raise RuntimeError(message)
    except Exception as exc:
        add_log(f"ERROR: Clipboard copy failed: {exc}")
        safe_notify(tr("terminal_log_copy_failed"), "negative")
        return
    safe_notify(tr("terminal_log_copied", count=len(text.splitlines())), "positive")


def progress_text() -> str:
    return f"{round(max(0.0, min(1.0, float(state['progress']))) * 100):.0f}%"


def safe_notify(message: str, kind: str = "info", **notify_kwargs: Any) -> None:
    notify_type = str(notify_kwargs.pop("type", kind))
    options = {"message": str(message), "type": notify_type, **notify_kwargs}
    delivered = False
    for client in list(nicegui_app.clients()):
        if getattr(client, "_deleted", False) or not client.has_socket_connection:
            continue
        try:
            client.outbox.enqueue_message("notify", options, client.id)
            delivered = True
        except Exception as exc:
            logging.warning("NiceGUI notification delivery failed for client %s: %s", getattr(client, "id", "?"), exc)
    if delivered:
        return

    try:
        ui.notify(message, type=notify_type, **notify_kwargs)
    except RuntimeError as exc:
        message_text = str(exc)
        if "slot belongs to has been deleted" not in message_text and "current slot cannot be determined" not in message_text:
            raise
        logging.warning("NiceGUI notification skipped because no live client slot was available: %s", message)


def operation_skip_warning_message(data: dict[str, Any]) -> str:
    skipped = data.get("skipped")
    if not isinstance(skipped, list) or not skipped:
        return ""
    labels: list[str] = []
    for item in skipped:
        if not isinstance(item, dict):
            continue
        label = str(item.get("browser_label") or item.get("browser") or "").strip()
        if label:
            labels.append(label)
    if not labels:
        labels.append(str(len(skipped)))
    preview = ", ".join(labels[:4])
    if len(labels) > 4:
        preview += f" +{len(labels) - 4}"
    if settings.language == "ru":
        return f"Пропущены отсутствующие профили: {preview}. Остальные выбранные браузеры обработаны."
    return f"Missing profiles skipped: {preview}. Remaining selected browsers were processed."


def dangerous_operation_notes(operation: Operation) -> list[str]:
    op_id = operation.id.lower()
    text = " ".join(
        [
            op_id,
            operation.title.lower(),
            operation.title_ru.lower(),
            operation.description.lower(),
            operation.description_ru.lower(),
        ]
    )
    language = settings.language if settings.language in LABELS else "en"
    ru = language == "ru"
    notes: list[str] = []

    def add(ru_text: str, en_text: str) -> None:
        note = ru_text if ru else en_text
        if note not in notes:
            notes.append(note)

    if any(token in text for token in ("format", "diskpart", "ssd", "nvme", "winre", "partition", "раздел", "формат")):
        add(
            "Может изменить разметку диска, WinRE или состояние накопителя; ошибка выбора диска может привести к потере данных.",
            "May change disk layout, WinRE, or drive state; choosing the wrong disk can cause data loss.",
        )
        add(
            "Интерактивные storage-wizard действия продолжают требовать собственные текстовые подтверждения.",
            "Interactive storage wizard actions still require their own typed confirmations.",
        )

    if "network_nuclear" in op_id or "nuclear" in text or "тоталь" in text:
        add(
            "Будут глубоко сброшены сетевые стеки и маршруты; сеть может временно пропасть до переподключения или reboot.",
            "Network stacks and routes will be deeply reset; connectivity can disappear until reconnect or reboot.",
        )
    elif "network_standard" in op_id:
        add(
            "Будут сброшены Winsock, TCP/IP, WinHTTP proxy, DNS и ARP; активные соединения могут оборваться.",
            "Winsock, TCP/IP, WinHTTP proxy, DNS, and ARP will be reset; active connections can drop.",
        )

    if "network_restore" in op_id:
        add(
            "Текущее сетевое состояние будет заменено данными из выбранного backup-снимка.",
            "Current network state will be replaced with data from the selected backup snapshot.",
        )
    if "proxy" in op_id:
        add(
            "Будут изменены proxy-настройки Windows; приложения могут потерять доступ к сети через корпоративный или ручной proxy.",
            "Windows proxy settings will be changed; apps may lose network access through corporate or manual proxy.",
        )
    if "adapter" in op_id or "lan_wifi" in op_id:
        add(
            "Сетевые адаптеры могут быть выключены или перезапущены; текущие подключения могут оборваться.",
            "Network adapters may be disabled or restarted; current connections may drop.",
        )
    if "wifi_import" in op_id:
        add(
            "Wi-Fi XML будет добавлен в Windows как сохранённый профиль; существующий профиль с тем же именем может быть заменён Windows.",
            "The Wi-Fi XML will be added to Windows as a saved profile; Windows may replace an existing profile with the same name.",
        )
    if "wifi_export" in op_id or "wifi_keys" in op_id:
        add(
            "Wi-Fi ключи могут быть сохранены открытым текстом, если включён соответствующий параметр.",
            "Wi-Fi keys may be saved as clear text if the matching option is enabled.",
        )

    if "wsl_delete" in op_id or "unregister" in text:
        add(
            "WSL unregister удалит выбранный дистрибутив и его Linux-файловую систему из Windows.",
            "WSL unregister will remove the selected distribution and its Linux filesystem from Windows.",
        )
    if "wsl_move" in op_id:
        add(
            "Дистрибутив будет перенесён через export/import; при сбое нужен backup/export для восстановления.",
            "The distribution will be moved through export/import; recovery after failure requires a backup/export.",
        )
    if "wsl_restore" in op_id or "wsl_import" in op_id or "wsl_install" in op_id:
        add(
            "Будет создана или зарегистрирована WSL-инстанция из выбранного образа; проверьте имя и папку установки.",
            "A WSL instance will be created or registered from the selected image; verify name and install folder.",
        )
    if "wsl_register_all" in op_id:
        add(
            "Пакетная регистрация может добавить несколько VHDX как WSL-дистрибутивы; если dry-run снят, изменения будут реальными.",
            "Batch registration can add multiple VHDX files as WSL distributions; if dry-run is off, changes are real.",
        )
    if "wsl_shutdown" in op_id or "wsl_terminate" in op_id:
        add(
            "Запущенные Linux-процессы в выбранном WSL-контексте будут остановлены.",
            "Running Linux processes in the selected WSL context will be stopped.",
        )
    if "wsl_enable" in op_id:
        add(
            "Будут включены Windows optional features для WSL2/Virtual Machine Platform; может потребоваться reboot.",
            "Windows optional features for WSL2/Virtual Machine Platform will be enabled; reboot may be required.",
        )
    if "wsl_linux" in op_id or "neovim" in op_id:
        add(
            "Команда изменит выбранный Linux-дистрибутив: пакеты, пользователя, пароль, sudo/wheel или конфиги.",
            "The command will modify the selected Linux distribution: packages, user, password, sudo/wheel, or configs.",
        )

    if "hosts" in text or "bitrix" in op_id:
        add(
            "Будет изменён файл Windows hosts; DNS-резолвинг для выбранных имён может поменяться сразу.",
            "The Windows hosts file will be changed; DNS resolution for selected names may change immediately.",
        )
    if "python_nuke" in op_id:
        add(
            "Будут удаляться Python installs/launchers/cache и PATH-записи; часть Python-инструментов перестанет запускаться.",
            "Python installs/launchers/cache and PATH entries will be removed; some Python tools may stop launching.",
        )
    if "codex_nuke" in op_id:
        add(
            "Codex Desktop, sandbox-пользователи, firewall rules, cache/state и registry-артефакты могут быть удалены; для CLI state выбирай вариант keep CLI state.",
            "Codex Desktop, sandbox users, firewall rules, cache/state, and registry artifacts may be removed; choose keep CLI state to preserve CLI state.",
        )
    if "cleanup_input_output" in op_id:
        add(
            "Содержимое управляемых папок input и output будет удалено; сами папки останутся.",
            "Contents of managed input and output folders will be deleted; the folders stay.",
        )
    if "cleanup_workspace" in op_id:
        add(
            "Содержимое управляемой папки workspace будет удалено; внешние исторические инструменты не трогаются.",
            "Contents of the managed workspace folder will be deleted; external historical tools are not touched.",
        )

    add(tr("confirm_parameters_note"), tr("confirm_parameters_note"))
    add(tr("confirm_irreversible_note"), tr("confirm_irreversible_note"))
    return notes


def terminal_cache() -> dict[str, Any]:
    cache = state.setdefault("terminal_cache", {"history": [], "pinned": [], "last": "", "shell": "pwsh", "cwd": str(ROOT)})
    if not isinstance(cache, dict):
        cache = {"history": [], "pinned": [], "last": "", "shell": "pwsh", "cwd": str(ROOT)}
        state["terminal_cache"] = cache
    cache["history"] = clean_terminal_commands(cache.get("history", []))
    cache["pinned"] = clean_terminal_commands(cache.get("pinned", []))
    return cache


def save_terminal_cache() -> None:
    cache = terminal_cache()
    cache["last"] = str(state.get("terminal_command") or "").strip()
    shell = str(state.get("terminal_shell") or "pwsh").strip().lower()
    cache["shell"] = shell if shell in {"pwsh", "cmd"} else "pwsh"
    cache["cwd"] = stored_terminal_cwd(state.get("terminal_cwd"))
    TERMINAL_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    TERMINAL_HISTORY_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def remember_terminal_command(command: str) -> None:
    command = command.strip()
    if not command:
        return
    cache = terminal_cache()
    history = [command, *[item for item in cache["history"] if item != command]]
    cache["history"] = history[:TERMINAL_HISTORY_LIMIT]
    state["terminal_command"] = command
    save_terminal_cache()


def terminal_command_options() -> dict[str, str]:
    cache = terminal_cache()
    pinned = clean_terminal_commands(cache.get("pinned", []))
    history = [item for item in clean_terminal_commands(cache.get("history", [])) if item not in pinned]
    last = str(cache.get("last") or "").strip()
    current = str(state.get("terminal_command") or "").strip()
    ordered = [*pinned]
    for command in (current, last, *history):
        if command and command not in ordered:
            ordered.append(command)
    options: dict[str, str] = {}
    for command in ordered[:TERMINAL_HISTORY_LIMIT]:
        options[command] = terminal_command_option_label(command, command in pinned)
    if not options:
        options[""] = tr("terminal_history_empty")
    return options


def terminal_command_option_label(command: str, pinned: bool = False) -> str:
    text = " ".join(str(command or "").split())
    if len(text) > 120:
        text = f"{text[:117]}..."
    return f"PIN {text}" if pinned else text


def terminal_history_value() -> str | None:
    options = terminal_command_options()
    current = str(state.get("terminal_command") or "").strip()
    last = str(terminal_cache().get("last") or "").strip()
    for command in (current, last):
        if command and command in options:
            return command
    if "" in options:
        return ""
    return None


def terminal_command_is_pinned() -> bool:
    command = str(state.get("terminal_command") or "").strip()
    return bool(command and command in terminal_cache().get("pinned", []))


def event_value(event: Any) -> Any:
    if hasattr(event, "value"):
        return event.value
    args = getattr(event, "args", None)
    if isinstance(args, list) and args:
        return args[0]
    if isinstance(args, dict):
        return args.get("value") or args.get("inputValue") or args.get("input")
    return args


def set_terminal_command(value: Any) -> None:
    state["terminal_command"] = str(value or "").strip()
    save_terminal_cache()


def resolve_terminal_history_value(value: Any) -> str:
    value = event_value(value)
    if isinstance(value, dict):
        value = value.get("value") or value.get("label") or value.get("name") or ""
    if isinstance(value, list) and value:
        value = value[0]
    text = str(value or "").strip()
    options = terminal_command_options()
    if text in options:
        return text
    for command, label in options.items():
        if text == str(label).strip():
            return command
    return text


def select_terminal_history(value: Any) -> None:
    set_terminal_command(resolve_terminal_history_value(value))
    terminal_command_bar.refresh()


def set_terminal_shell(value: Any) -> None:
    shell = str(value or "pwsh").strip().lower()
    state["terminal_shell"] = shell if shell in {"pwsh", "cmd"} else "pwsh"
    save_terminal_cache()


def set_terminal_cwd(value: Any) -> None:
    state["terminal_cwd"] = str(value or "").strip() or str(ROOT)
    save_terminal_cache()


def append_terminal_argument(value: Path | str) -> None:
    text = str(value)
    quoted = f'"{text}"' if any(char.isspace() for char in text) else text
    current = str(state.get("terminal_command") or "").rstrip()
    state["terminal_command"] = f"{current} {quoted}".strip() if current else quoted
    save_terminal_cache()
    terminal_command_bar.refresh()


def pin_terminal_command() -> None:
    command = str(state.get("terminal_command") or "").strip()
    if not command:
        safe_notify(tr("command_required"), "warning")
        return
    cache = terminal_cache()
    pinned = [command, *[item for item in cache["pinned"] if item != command]]
    cache["pinned"] = pinned[:TERMINAL_HISTORY_LIMIT]
    remember_terminal_command(command)
    terminal_command_bar.refresh()


def unpin_terminal_command() -> None:
    command = str(state.get("terminal_command") or "").strip()
    if not command:
        safe_notify(tr("command_required"), "warning")
        return
    cache = terminal_cache()
    cache["pinned"] = [item for item in cache["pinned"] if item != command]
    remember_terminal_command(command)
    terminal_command_bar.refresh()


def clear_terminal_history() -> None:
    cache = terminal_cache()
    cache["history"] = [item for item in cache["history"] if item in cache["pinned"]]
    cache["last"] = ""
    state["terminal_command"] = ""
    save_terminal_cache()
    safe_notify(tr("history_cleared"), "positive")
    terminal_command_bar.refresh()


def clear_terminal_command_cache() -> None:
    cache = terminal_cache()
    cache["history"] = []
    cache["pinned"] = []
    cache["last"] = ""
    state["terminal_command"] = ""
    save_terminal_cache()
    safe_notify(tr("command_cache_cleared"), "positive")
    terminal_command_bar.refresh()


RUN_STATE_LABELS = {
    "idle": ("idle", "audion-status-idle"),
    "running": ("running", "audion-status-running"),
    "done": ("done", "audion-status-done"),
    "error": ("error", "audion-status-error"),
}


def run_state() -> str:
    """Which of the four states the panel is showing.

    Colour carries this everywhere it appears, so it is decided once.
    """
    if bool(state["running"]):
        return "running"
    exit_code = state.get("exit_code")
    if exit_code is None:
        return "idle"
    return "done" if int(exit_code or 0) == 0 else "error"


def status_row_classes() -> str:
    return f"audion-status-row {RUN_STATE_LABELS[run_state()][1]}"


def status_state_text() -> str:
    return tr(RUN_STATE_LABELS[run_state()][0]).upper()


def elapsed_text(seconds: float | None) -> str:
    """A run's own clock, mm:ss, or an em dash before anything has run.

    The start is noticed by the refresh timer rather than written by the code that
    starts a run: there are several such places, and none of them has to know
    about the panel.
    """
    if seconds is None:
        return "—"
    total = max(0, int(seconds))
    return f"{total // 60:02d}:{total % 60:02d}"


def status_dot_classes() -> str:
    base = "audion-status-dot text-lg leading-none"
    if bool(state["running"]):
        return f"{base} text-sky-400 animate-pulse"
    if state.get("exit_code") is None:
        return f"{base} text-gray-500"
    if int(state.get("exit_code") or 0) == 0:
        return f"{base} text-green-400"
    return f"{base} text-red-400"


def set_progress(value: float) -> None:
    state["progress"] = max(0.0, min(1.0, float(value)))


def cancel_requested() -> bool:
    return bool(state["cancel"])


def hidden_subprocess_flags() -> int:
    if os.name == "nt" and hasattr(subprocess, "CREATE_NO_WINDOW"):
        return int(subprocess.CREATE_NO_WINDOW)
    return 0


def hidden_subprocess_startupinfo() -> subprocess.STARTUPINFO | None:
    if os.name != "nt" or not hasattr(subprocess, "STARTUPINFO"):
        return None
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = 0
    return startupinfo


def resolve_dialog_powershell() -> list[str]:
    candidates = [
        [str(paths.system_core / "powershell" / "pwsh.exe"), "-NoLogo", "-NoProfile", "-STA", "-Command"],
        ["pwsh.exe", "-NoLogo", "-NoProfile", "-STA", "-Command"],
        ["powershell.exe", "-NoProfile", "-STA", "-ExecutionPolicy", "Bypass", "-Command"],
    ]
    for candidate in candidates:
        exe = candidate[0]
        if Path(exe).exists() or shutil.which(exe):
            return candidate
    raise RuntimeError("PowerShell was not found for Windows picker.")


_PICKER_RUN_LOCK = threading.Lock()
_PICKER_JOB_LOCK = threading.Lock()
_PICKER_JOB_HANDLE: int | None = None


class _JobObjectBasicLimitInformation(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_int64),
        ("PerJobUserTimeLimit", ctypes.c_int64),
        ("LimitFlags", wintypes.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", wintypes.DWORD),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", wintypes.DWORD),
        ("SchedulingClass", wintypes.DWORD),
    ]


class _IoCounters(ctypes.Structure):
    _fields_ = [
        ("ReadOperationCount", ctypes.c_uint64),
        ("WriteOperationCount", ctypes.c_uint64),
        ("OtherOperationCount", ctypes.c_uint64),
        ("ReadTransferCount", ctypes.c_uint64),
        ("WriteTransferCount", ctypes.c_uint64),
        ("OtherTransferCount", ctypes.c_uint64),
    ]


class _JobObjectExtendedLimitInformation(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", _JobObjectBasicLimitInformation),
        ("IoInfo", _IoCounters),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


def close_picker_job() -> None:
    global _PICKER_JOB_HANDLE
    with _PICKER_JOB_LOCK:
        handle = _PICKER_JOB_HANDLE
        _PICKER_JOB_HANDLE = None
    if os.name == "nt" and handle:
        ctypes.WinDLL("kernel32", use_last_error=True).CloseHandle(wintypes.HANDLE(handle))


def _picker_job_handle() -> int | None:
    global _PICKER_JOB_HANDLE
    if os.name != "nt":
        return None
    with _PICKER_JOB_LOCK:
        if _PICKER_JOB_HANDLE:
            return _PICKER_JOB_HANDLE
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateJobObjectW.restype = wintypes.HANDLE
        job = kernel32.CreateJobObjectW(None, None)
        if not job:
            logging.warning("Could not create the Windows picker job: %s", ctypes.get_last_error())
            return None
        info = _JobObjectExtendedLimitInformation()
        info.BasicLimitInformation.LimitFlags = 0x00002000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        configured = kernel32.SetInformationJobObject(
            wintypes.HANDLE(job),
            9,  # JobObjectExtendedLimitInformation
            ctypes.byref(info),
            ctypes.sizeof(info),
        )
        if not configured:
            error = ctypes.get_last_error()
            kernel32.CloseHandle(wintypes.HANDLE(job))
            logging.warning("Could not configure the Windows picker job: %s", error)
            return None
        _PICKER_JOB_HANDLE = int(job)
        return _PICKER_JOB_HANDLE


def _assign_picker_to_job(process: subprocess.Popen[str]) -> None:
    handle = _picker_job_handle()
    if os.name != "nt" or not handle:
        return
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    assigned = kernel32.AssignProcessToJobObject(
        wintypes.HANDLE(handle),
        wintypes.HANDLE(int(process._handle)),  # type: ignore[attr-defined]
    )
    if not assigned:
        logging.warning("Could not attach picker PID %s to its Windows job: %s", process.pid, ctypes.get_last_error())


def run_picker_script(script: str, failure_message: str) -> str:
    if not _PICKER_RUN_LOCK.acquire(blocking=False):
        raise RuntimeError("A Windows picker is already open.")
    process: subprocess.Popen[str] | None = None
    try:
        process = subprocess.Popen(
            [*resolve_dialog_powershell(), script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=hidden_subprocess_flags(),
            startupinfo=hidden_subprocess_startupinfo(),
        )
        _assign_picker_to_job(process)
        try:
            stdout, stderr = process.communicate(timeout=3600)
        except subprocess.TimeoutExpired as exc:
            process.kill()
            process.communicate()
            raise RuntimeError("Windows picker timed out.") from exc
        if process.returncode != 0:
            raise RuntimeError(stderr.strip() or failure_message)
        return stdout
    finally:
        if process is not None and process.poll() is None:
            process.kill()
        _PICKER_RUN_LOCK.release()


atexit.register(close_picker_job)
nicegui_app.on_shutdown(close_picker_job)


def parse_picker_paths(text: str) -> list[Path]:
    import json

    payload = text.strip()
    if not payload:
        return []
    data = json.loads(payload)
    if isinstance(data, str):
        data = [data]
    return [Path(str(item)).resolve() for item in data if str(item).strip()]


def ps_single_quoted(text: str) -> str:
    return "'" + str(text).replace("'", "''") + "'"


def picker_initial_directory_script(initial_dir: Path | None, *, property_name: str) -> str:
    if initial_dir is None:
        return ""
    return f"""
$initialDirectory = {ps_single_quoted(str(initial_dir))}
if (Test-Path -LiteralPath $initialDirectory -PathType Container) {{
  $dialog.{property_name} = $initialDirectory
}}
"""


def nearest_existing_directory(path: Path) -> Path | None:
    current = path.expanduser()
    if current.exists() and current.is_file():
        current = current.parent
    while not current.exists():
        parent = current.parent
        if parent == current:
            return None
        current = parent
    return current if current.is_dir() else current.parent


def resolve_picker_initial_directory(field: dict[str, Any], key: str, kind: str) -> Path | None:
    raw = state.setdefault("field_values", {}).get(key, field_default(field))
    text = os.path.expandvars(str(raw or "").strip())
    if not text:
        return ROOT
    path = Path(text).expanduser()
    if not path.is_absolute():
        path = ROOT / path
    if kind == "file":
        path = path.parent
    return nearest_existing_directory(path) or ROOT


def pick_files(title: str = "Choose files", initial_dir: Path | None = None) -> list[Path]:
    script = PICKER_BOOTSTRAP + f"""
$dialog = New-Object System.Windows.Forms.OpenFileDialog
$dialog.Title = {ps_single_quoted(title)}
$dialog.Multiselect = $true
$dialog.Filter = 'All supported files|*.*|All files|*.*'
{picker_initial_directory_script(initial_dir, property_name="InitialDirectory")}
if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {{
  $dialog.FileNames | ConvertTo-Json -Compress
}}
"""
    return parse_picker_paths(run_picker_script(script, "File picker failed."))


def pick_single_file(title: str = "Choose one source file", initial_dir: Path | None = None) -> list[Path]:
    script = PICKER_BOOTSTRAP + f"""
$dialog = New-Object System.Windows.Forms.OpenFileDialog
$dialog.Title = {ps_single_quoted(title)}
$dialog.Multiselect = $false
$dialog.Filter = 'All supported files|*.*|All files|*.*'
{picker_initial_directory_script(initial_dir, property_name="InitialDirectory")}
if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {{
  $dialog.FileName | ConvertTo-Json -Compress
}}
"""
    return parse_picker_paths(run_picker_script(script, "File picker failed."))


def pick_folder(title: str = "Choose folder", initial_dir: Path | None = None) -> list[Path]:
    script = PICKER_BOOTSTRAP + f"""
$dialog = New-Object System.Windows.Forms.FolderBrowserDialog
$dialog.Description = {ps_single_quoted(title)}
$dialog.ShowNewFolderButton = $false
{picker_initial_directory_script(initial_dir, property_name="SelectedPath")}
if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {{
  @($dialog.SelectedPath) | ConvertTo-Json -Compress
}}
"""
    return parse_picker_paths(run_picker_script(script, "Folder picker failed."))


async def pick_path_into_field(field: dict[str, Any], key: str, kind: str) -> None:
    try:
        initial_dir = resolve_picker_initial_directory(field, key, kind)
        if kind == "folder":
            sources = await run.io_bound(pick_folder, tr("pick_folder"), initial_dir)
        else:
            sources = await run.io_bound(pick_files, tr("pick_file"), initial_dir)
    except Exception as exc:
        safe_notify(f"{exc.__class__.__name__}: {exc}", "negative")
        return
    if not sources:
        safe_notify(tr("picker_cancelled"), "warning")
        return
    set_field_value(key, str(sources[0]))
    command_tree.refresh()


def path_picker_click_handler(field: dict[str, Any], key: str, kind: str):
    async def handler() -> None:
        await pick_path_into_field(field, key, kind)

    return handler


def input_file_list_lines(source: Path) -> list[str]:
    if not source.exists():
        return [tr("file_list_missing", path=source)]
    if source.is_file():
        names = [source.name]
    elif source.is_dir():
        names = sorted((path.name for path in source.rglob("*") if path.is_file()), key=lambda item: item.casefold())
    else:
        return [f"Unsupported INPUT path: {source}"]
    if not names:
        return [tr("file_list_empty")]

    number_width = max(3, len(str(len(names))))
    lines = [
        f"{'No.':>{number_width}}  List",
        f"{'-' * number_width}  ----",
    ]
    lines.extend(f"{index:0{number_width}d}. {name}" for index, name in enumerate(names, start=1))
    return lines


async def show_input_file_list() -> None:
    if state["running"]:
        safe_notify(tr("another_running"), "warning")
        return

    title = tr("file_list")
    state.update(
        {
            "running": True,
            "cancel": False,
            "progress": 0.02,
            "status": f"{tr('running')}: {title}",
            **reset_terminal_fields(),
            "exit_code": None,
        }
    )
    try:
        lines = await run.io_bound(input_file_list_lines, current_source_path())
        for line in lines:
            add_log(line)
        count = max(0, len(lines) - 2)
        state["exit_code"] = 0
        state["progress"] = 1.0
        state["status"] = f"{tr('done')}: {title} [{count}]"
        safe_notify(tr("file_list_ready", count=count), "positive")
    except Exception as exc:
        state["exit_code"] = 1
        state["progress"] = max(float(state["progress"]), 0.98)
        state["status"] = f"{tr('error')}: {exc}"
        add_log(f"ERROR: {exc.__class__.__name__}: {exc}")
        safe_notify(str(exc), "negative")
    finally:
        state["running"] = False


async def start_operation(operation: Operation) -> None:
    if state["running"]:
        safe_notify(tr("another_running"), "warning")
        return

    if operation_requires_confirmation(operation):
        with ui.dialog() as dialog, ui.card().classes("audion-dialog audion-confirm-card rounded-lg p-4"):
            ui.label(tr("confirm_title")).classes("audion-confirm-title text-base font-semibold")
            ui.label(operation.display_title(settings.language)).classes("audion-confirm-operation text-sm font-semibold")
            ui.label(operation.display_description(settings.language)).classes("audion-confirm-description text-sm")
            risk_text = risk_level_text(getattr(operation, "risk_level", ""))
            if risk_text:
                ui.label(risk_text).classes("audion-confirm-risk text-xs")
            with ui.element("div").classes("audion-confirm-impact"):
                ui.label(tr("confirm_impact_title")).classes("audion-confirm-impact-title")
                with ui.element("ul").classes("audion-confirm-list"):
                    for note in dangerous_operation_notes(operation):
                        with ui.element("li").classes("audion-confirm-list-item"):
                            ui.label(note).classes("audion-confirm-list-text")
            ui.label(tr("confirm_note")).classes("audion-confirm-note text-xs")
            with ui.row().classes("w-full justify-end gap-2"):
                ui.button(tr("cancel"), on_click=dialog.close).props("dense flat").classes("audion-action rounded-lg")
                ui.button(tr("confirm_run_dangerous"), on_click=lambda: dialog.submit(True)).props("dense flat").classes("audion-action rounded-lg")
        confirmed = await dialog
        if not confirmed:
            return

    state.update(
        {
            "running": True,
            "cancel": False,
            "progress": 0.02,
            "status": f"{tr('running')}: {operation.display_title(settings.language)}",
            **reset_terminal_fields(),
            "exit_code": None,
        }
    )
    started = time.perf_counter()
    try:
        result = await run.io_bound(
            execute_operation,
            paths,
            operation,
            add_log,
            set_progress,
            cancel_requested,
        )
        elapsed = time.perf_counter() - started
        apply_operation_field_updates(result.data)
        state["exit_code"] = 0 if result.ok else 1
        state["progress"] = 1.0
        state["status"] = f"{tr('done') if result.ok else tr('error')}: {operation.display_title(settings.language)} [{state['exit_code']}] {elapsed:.1f}s"
        skip_warning = operation_skip_warning_message(result.data) if result.ok else ""
        safe_notify(skip_warning or result.message, "warning" if skip_warning else ("positive" if result.ok else "negative"))
    except Exception as exc:
        state["exit_code"] = 1
        state["progress"] = max(float(state["progress"]), 0.98)
        state["status"] = f"{tr('error')}: {exc}"
        add_log(f"ERROR: {exc.__class__.__name__}: {exc}")
        safe_notify(str(exc), "negative")
    finally:
        state["running"] = False


async def pick_terminal_location(kind: str) -> None:
    try:
        if kind == "folder":
            sources = await run.io_bound(pick_folder, tr("terminal_location"))
        else:
            sources = await run.io_bound(pick_files, tr("pick_file"))
    except Exception as exc:
        safe_notify(f"{exc.__class__.__name__}: {exc}", "negative")
        return
    if not sources:
        safe_notify(tr("picker_cancelled"), "warning")
        return
    chosen = sources[0]
    location = chosen if chosen.is_dir() else chosen.parent
    set_terminal_cwd(str(location))
    if kind == "file" and chosen.is_file():
        append_terminal_argument(chosen)
    terminal_command_bar.refresh()


def terminal_location_click_handler(kind: str):
    async def handler() -> None:
        await pick_terminal_location(kind)

    return handler


async def start_terminal_command() -> None:
    command = str(state.get("terminal_command") or "").strip()
    if not command:
        safe_notify(tr("command_required"), "warning")
        return
    remember_terminal_command(command)
    terminal_command_bar.refresh()
    shell = str(state.get("terminal_shell") or "pwsh").strip().lower()
    cwd = str(state.get("terminal_cwd") or ROOT).strip()
    title = "Terminal command"
    title_ru = "Команда терминала"
    operation = Operation(
        id="terminal_command",
        title=title,
        title_ru=title_ru,
        description=command,
        description_ru=command,
        service="system_core.services.devops_tools:terminal_command",
        kind="safe",
        parameters={"command": command, "shell": shell, "cwd": cwd},
    )
    await start_operation(operation)


async def terminal_enter_handler(_event: Any = None) -> None:
    await start_terminal_command()


def toggle_language() -> None:
    settings.language = "en" if settings.language == "ru" else "ru"
    save_app_settings()
    reload_ui()


def save_advanced_open(event: Any) -> None:
    settings.advanced_open = bool(getattr(event, "value", False))
    save_app_settings()


def current_source_path() -> Path:
    return Path(str(state.get("source_path") or getattr(settings, "source_path", "") or paths.input)).expanduser()


def current_target_path() -> Path:
    return Path(str(state.get("destination_path") or getattr(settings, "destination_path", "") or paths.output)).expanduser()


def save_workspace_path(kind: str, value: Any) -> None:
    text = str(value or "").strip()
    if kind == "source":
        settings.source_path = text
        state["source_path"] = text
    elif kind == "destination":
        settings.destination_path = text
        state["destination_path"] = text
    else:
        raise RuntimeError(f"Unsupported workspace path kind: {kind}")
    save_app_settings()


def open_workspace_folder(role: str) -> None:
    folder = current_target_path() if role == "target" else current_source_path()
    if role != "target" and not folder.exists():
        raise FileNotFoundError(tr("source_folder_missing", path=folder))
    if folder.is_file():
        if os.name == "nt":
            subprocess.Popen(["explorer.exe", f"/select,{folder}"])
        else:
            open_folder(folder.parent)
        return
    open_folder(folder)


def mark_workspace_feedback(role: str, action: str) -> None:
    state["workspace_feedback"] = {"role": canonical_role(role), "action": str(action or "path")}


def _save_workspace_adapter_path(role: WorkbenchRole, value: Any) -> None:
    save_workspace_path("destination" if role == "target" else "source", value)


def _workspace_feedback() -> dict[str, str]:
    value = state.get("workspace_feedback")
    return dict(value) if isinstance(value, dict) else {}


def _clear_workspace_feedback() -> None:
    state["workspace_feedback"] = {}


def absolute_project_path(path_value: Any) -> Path:
    path = Path(str(path_value or "")).expanduser()
    if not path.is_absolute():
        path = ROOT / path
    return path


def normalized_absolute_path(path_value: Any) -> Path:
    return absolute_project_path(path_value).resolve(strict=False)


def paths_equal(left: Any, right: Any) -> bool:
    return os.path.normcase(str(normalized_absolute_path(left))) == os.path.normcase(str(normalized_absolute_path(right)))


def remove_path_tree(path: Path) -> int:
    is_junction = bool(getattr(os.path, "isjunction", lambda _path: False)(path))
    if path.is_symlink() or is_junction:
        if path.is_dir():
            path.rmdir()
        else:
            path.unlink()
        return 1
    if path.is_file():
        path.unlink()
        return 1
    if path.is_dir():
        shutil.rmtree(path)
        return 1
    return 0


def clear_directory_contents(folder: Path) -> int:
    removed = 0
    if not folder.exists():
        return removed
    for child in sorted(folder.iterdir(), key=lambda item: item.name.casefold()):
        # .gitkeep is not spared: input and output must be genuinely empty after
        # a clear, so nobody has to wonder what the leftover file is or whether it
        # is safe to delete. The folders come from install/init_folders.cmd.
        removed += remove_path_tree(child)
    return removed


def validate_workspace_delete_target(path_value: Any) -> Path:
    target = normalized_absolute_path(path_value)
    if target.parent == target:
        raise RuntimeError(f"Refusing to delete a filesystem root: {target}")
    if paths_equal(target, ROOT):
        raise RuntimeError(f"Refusing to delete the project root: {target}")
    return target


def delete_workspace_path_contents(path_value: Any) -> dict[str, Any]:
    target = validate_workspace_delete_target(path_value)
    if not target.exists() and not target.is_symlink():
        return {"path": str(target), "kind": "missing", "removed": 0}
    is_junction = bool(getattr(os.path, "isjunction", lambda _path: False)(target))
    if target.is_file() or target.is_symlink() or is_junction:
        return {"path": str(target), "kind": "file", "removed": remove_path_tree(target)}
    if not target.is_dir():
        raise RuntimeError(f"Unsupported workspace path: {target}")
    return {"path": str(target), "kind": "folder", "removed": clear_directory_contents(target)}


def delete_workspace_io_contents(source: Path, target: Path) -> dict[str, Any]:
    source_result = delete_workspace_path_contents(source)
    if paths_equal(source, target):
        target_result = {"path": str(normalized_absolute_path(target)), "kind": "same", "removed": 0}
    else:
        target_result = delete_workspace_path_contents(target)
    return {"source": source_result, "target": target_result}


WORKBENCH_CONFIG = WorkbenchConfig(
    root=ROOT,
    input_path=paths.input,
    output_path=paths.output,
    history_path=_workspace_history_file(),
    history_limit=PATH_HISTORY_LIMIT,
)
WORKBENCH_ADAPTER = WorkbenchAdapter(
    config=WORKBENCH_CONFIG,
    current_path_callback=lambda role: current_target_path() if role == "target" else current_source_path(),
    save_path_callback=_save_workspace_adapter_path,
    language_callback=lambda: settings.language,
    translate_callback=tr,
    log_callback=add_log,
    notify_callback=safe_notify,
    reload_callback=lambda _delay=0: reload_ui(),
    busy_callback=lambda: bool(state.get("running")),
    feedback_callback=_workspace_feedback,
    set_feedback_callback=mark_workspace_feedback,
    clear_feedback_callback=_clear_workspace_feedback,
)
WORKBENCH_ADAPTER.validate()
WORKBENCH_ADAPTER.ensure_initial_history()


def workspace_pin_click_handler(role: str, pinned: bool):
    async def handler() -> None:
        path_value = str(current_target_path() if role == "target" else current_source_path())
        if not path_value:
            safe_notify(tr("path_required"), "warning")
            return
        try:
            await run.io_bound(WORKBENCH_ADAPTER.set_path_pinned, role, path_value, pinned)
            mark_workspace_feedback(role, "pin" if pinned else "unpin")
            add_log(f"{'Pinned' if pinned else 'Unpinned'} {role} path: {path_value}")
            reload_ui()
        except Exception as exc:
            add_log(f"ERROR: {exc.__class__.__name__}: {exc}")
            safe_notify(str(exc), "negative")

    return handler


def workspace_delete_path_click_handler(role: str):
    async def handler() -> None:
        if state["running"]:
            safe_notify(tr("another_running"), "warning")
            return
        path = current_target_path() if role == "target" else current_source_path()
        path_value = str(path)
        if not path_value:
            safe_notify(tr("path_required"), "warning")
            return
        external_source = role != "target" and not paths_equal(path, paths.input)
        if external_source:
            is_file = path.is_file()
            with ui.dialog() as dialog, ui.card().classes("audion-dialog rounded-lg"):
                title = "Удалить исходный файл?" if is_file else "Очистить внешний ИСТОЧНИК?"
                if settings.language != "ru":
                    title = "Delete the source file?" if is_file else "Clear the external SOURCE?"
                ui.label(title).classes("text-base font-semibold")
                warning = (
                    "Будет удалён исходный файл. Другой копии может не существовать."
                    if is_file
                    else "Будут безвозвратно удалены все файлы и вложенные папки."
                )
                if settings.language != "ru":
                    warning = (
                        "The source file will be deleted. Another copy may not exist."
                        if is_file
                        else "All files and nested folders will be permanently deleted."
                    )
                ui.label(warning).classes("text-sm text-gray-300")
                ui.label(str(normalized_absolute_path(path))).classes("max-w-3xl break-all font-mono text-xs text-gray-400")
                with ui.row().classes("gap-2"):
                    ui.button(tr("cancel"), on_click=dialog.close).props("dense flat")
                    ui.button(tr("delete_io_short"), on_click=lambda: dialog.submit(True)).props("dense color=negative")
            if not await dialog:
                return
        try:
            result = await run.io_bound(delete_workspace_path_contents, path)
            if result.get("kind") == "file":
                await run.io_bound(WORKBENCH_ADAPTER.delete_path_history, role, path_value)
                save_workspace_path("destination" if role == "target" else "source", "")
            mark_workspace_feedback(role, "delete")
            add_log(
                f"Cleared {'TARGET' if role == 'target' else 'SOURCE'}: {result.get('path')} "
                f"[kind={result.get('kind')}, removed={result.get('removed', 0)}]"
            )
            reload_ui()
        except Exception as exc:
            add_log(f"ERROR: {exc.__class__.__name__}: {exc}")
            safe_notify(str(exc), "negative")

    return handler


def workspace_single_file_click_handler():
    async def handler() -> None:
        if state["running"]:
            safe_notify(tr("another_running"), "warning")
            return
        initial = nearest_existing_directory(current_source_path()) or ROOT
        try:
            selected = await run.io_bound(pick_single_file, tr("add_file_short"), initial)
        except Exception as exc:
            add_log(f"ERROR: {exc.__class__.__name__}: {exc}")
            safe_notify(str(exc), "negative")
            return
        if not selected:
            add_log(tr("picker_cancelled"))
            return
        path_value = str(selected[0])
        save_workspace_path("source", path_value)
        await run.io_bound(WORKBENCH_ADAPTER.remember_path, "source", path_value)
        mark_workspace_feedback("source", "path")
        add_log(f"SOURCE FILE -> {path_value}")
        reload_ui()

    return handler


def workspace_open_click_handler(role: str):
    async def handler() -> None:
        try:
            await run.io_bound(open_workspace_folder, role)
            current = current_target_path() if role == "target" else current_source_path()
            add_log(f"Opened {'target' if role == 'target' else 'source'} folder: {current}")
        except Exception as exc:
            add_log(f"ERROR: {exc.__class__.__name__}: {exc}")
            safe_notify(str(exc), "negative")

    return handler


def reset_workspace_paths_click_handler():
    async def handler() -> None:
        if state["running"]:
            safe_notify(tr("another_running"), "warning")
            return
        result = await run.io_bound(WORKBENCH_ADAPTER.clear_path_history_cache_keep_pins)
        save_workspace_path("source", "")
        save_workspace_path("destination", "")
        add_log(f"Workspace route reset: SOURCE -> {paths.input}")
        add_log(f"Workspace route reset: TARGET -> {paths.output}")
        add_log(
            "Workspace path cache cleared: "
            f"sources={result.get('removed_sources', 0)}, targets={result.get('removed_targets', 0)}, "
            f"pins kept={result.get('kept_pins', 0)}"
        )
        safe_notify(tr("operation_done"), "positive")
        reload_ui()

    return handler


def workspace_path_select_handler(role: str):
    async def handler(event: Any) -> None:
        path_value = str(getattr(event, "value", "") or "").strip()
        if not path_value:
            return
        save_workspace_path("destination" if role == "target" else "source", path_value)
        await run.io_bound(WORKBENCH_ADAPTER.remember_path, role, path_value)
        mark_workspace_feedback(role, "path")
        add_log(f"{'TARGET' if role == 'target' else 'SOURCE'} -> {path_value}")
        reload_ui()

    return handler


def workspace_delete_both_click_handler():
    async def handler() -> None:
        if state["running"]:
            safe_notify(tr("another_running"), "warning")
            return
        source = current_source_path()
        target = current_target_path()
        source_external = not paths_equal(source, paths.input)
        with ui.dialog() as dialog, ui.card().classes("audion-dialog rounded-lg"):
            ui.label("Удалить содержимое I/O?" if settings.language == "ru" else "Delete I/O contents?").classes("text-base font-semibold")
            warning = (
                "Будут удалены файлы ИСТОЧНИКА и НАЗНАЧЕНИЯ. Внешний ИСТОЧНИК может быть единственным экземпляром."
                if source_external
                else "Будут удалены файлы ИСТОЧНИКА и НАЗНАЧЕНИЯ."
            )
            if settings.language != "ru":
                warning = (
                    "SOURCE and TARGET files will be deleted. The external SOURCE may be the only copy."
                    if source_external
                    else "SOURCE and TARGET files will be deleted."
                )
            ui.label(warning).classes("text-sm text-gray-300")
            ui.label(f"SOURCE: {normalized_absolute_path(source)}").classes("max-w-3xl break-all font-mono text-xs text-gray-400")
            ui.label(f"TARGET: {normalized_absolute_path(target)}").classes("max-w-3xl break-all font-mono text-xs text-gray-400")
            with ui.row().classes("gap-2"):
                ui.button(tr("cancel"), on_click=dialog.close).props("dense flat")
                ui.button(tr("delete_io_short"), on_click=lambda: dialog.submit(True)).props("dense color=negative")
        if not await dialog:
            return
        state["running"] = True
        try:
            result = await run.io_bound(delete_workspace_io_contents, source, target)
            source_result = result.get("source", {})
            target_result = result.get("target", {})
            if source_result.get("kind") == "file":
                await run.io_bound(WORKBENCH_ADAPTER.delete_path_history, "source", str(source))
                save_workspace_path("source", "")
            if target_result.get("kind") == "file":
                await run.io_bound(WORKBENCH_ADAPTER.delete_path_history, "target", str(target))
                save_workspace_path("destination", "")
            add_log(
                f"Cleared SOURCE: {source_result.get('path')} "
                f"[kind={source_result.get('kind')}, removed={source_result.get('removed', 0)}]"
            )
            add_log(
                f"Cleared TARGET: {target_result.get('path')} "
                f"[kind={target_result.get('kind')}, removed={target_result.get('removed', 0)}]"
            )
            mark_workspace_feedback("source", "delete")
            reload_ui()
        except Exception as exc:
            add_log(f"ERROR: {exc.__class__.__name__}: {exc}")
            safe_notify(str(exc), "negative")
        finally:
            state["running"] = False

    return handler


def workspace_pick_click_handler(role: str):
    async def handler() -> None:
        if state["running"]:
            safe_notify(tr("another_running"), "warning")
            return
        current = current_target_path() if role == "target" else current_source_path()
        initial = nearest_existing_directory(current) or ROOT
        try:
            selected = await run.io_bound(pick_folder, tr("pick_folder"), initial)
        except Exception as exc:
            add_log(f"ERROR: {exc.__class__.__name__}: {exc}")
            safe_notify(str(exc), "negative")
            return
        if not selected:
            add_log(tr("picker_cancelled"))
            return
        path_value = str(selected[0])
        save_workspace_path("destination" if role == "target" else "source", path_value)
        await run.io_bound(WORKBENCH_ADAPTER.remember_path, role, path_value)
        mark_workspace_feedback(role, "path")
        add_log(f"{'TARGET' if role == 'target' else 'SOURCE'} -> {path_value}")
        reload_ui()

    return handler


WORKBENCH_RENDERER = WorkbenchRenderer(
    adapter=WORKBENCH_ADAPTER,
    handlers=WorkbenchHandlers(
        delete_path=workspace_delete_path_click_handler,
        pin_path=workspace_pin_click_handler,
        select_path=workspace_path_select_handler,
        pick_path=workspace_pick_click_handler,
        open_path=workspace_open_click_handler,
        add_file=workspace_single_file_click_handler,
        reset_paths=reset_workspace_paths_click_handler,
        delete_io=workspace_delete_both_click_handler,
        list_files=show_input_file_list,
    ),
    display_path_callback=display_path,
)


def operation_button(operation: Operation) -> None:
    row_classes = ["audion-operation-row", "audion-operation-row-leaf", "audion-operation-row-direct"]
    button_classes = ["audion-action", "audion-operation-button", "audion-operation-button-direct", "rounded-lg"]
    if str(operation.kind).strip().lower() == "dangerous":
        row_classes.append("audion-operation-row-dangerous")
        button_classes.append("audion-operation-button-direct-dangerous")
    description = operation.display_description(settings.language)
    risk_text = risk_level_text(getattr(operation, "risk_level", ""))
    tooltip = description_tooltip_text(description, [risk_text] if risk_text else [])
    with ui.element("div").classes(" ".join(row_classes)):
        button = ui.button(
            operation.display_title(settings.language),
            on_click=operation_click_handler(operation),
        ).props("dense flat").classes(" ".join(button_classes))
        if tooltip:
            soft_tooltip(button, tooltip)
        if description:
            description_label = ui.label(compact_visible_description(description)).classes("audion-operation-description audion-operation-description-compact")
            if tooltip:
                soft_tooltip(description_label, tooltip)
        if risk_text:
            ui.label(risk_text).classes("audion-operation-meta")


def operation_click_handler(operation: Operation):
    async def handler() -> None:
        await start_operation(operation)

    return handler


def operation_to_command_node(operation: Operation) -> CommandNode:
    return CommandNode(
        id=operation.id,
        title=operation.title,
        description=operation.description,
        service=operation.service,
        kind=operation.kind,
        risk_level=operation.risk_level,
        ui_layout="",
        surface="os",
        section="os_workspace",
        title_ru=operation.title_ru,
        description_ru=operation.description_ru,
        parameters=dict(operation.parameters),
        fields=operation.fields,
    )


COMMAND_SURFACES = ("os", "os_settings", "device")


def normalize_command_surface(value: Any) -> str:
    text = str(value or "").strip().lower()
    return text if text in COMMAND_SURFACES else "os"


def command_node_surface(node: CommandNode) -> str:
    return normalize_command_surface(getattr(node, "surface", ""))


def command_node_section(node: CommandNode) -> str:
    section = str(getattr(node, "section", "") or "").strip().lower()
    if section:
        return section
    return "device_general" if command_node_surface(node) == "device" else "os_general"


def is_flattened_root_node(node: CommandNode) -> bool:
    layout = str(getattr(node, "ui_layout", "") or "").strip().lower()
    return layout in {"flatten", "flatten_children", "root_flatten"}


def root_command_nodes() -> list[CommandNode]:
    nodes = list(manifest.operation_groups) if manifest.operation_groups else [
        operation_to_command_node(operation) for operation in manifest.operations
    ]
    result: list[CommandNode] = []
    for node in nodes:
        if is_flattened_root_node(node):
            result.extend(node.children)
        else:
            result.append(node)
    return result


def current_command_surface() -> str:
    surface = normalize_command_surface(state.get("command_surface"))
    state["command_surface"] = surface
    return surface


def root_nodes_for_current_surface() -> list[CommandNode]:
    surface = current_command_surface()
    return [node for node in root_command_nodes() if command_node_surface(node) == surface]


def current_command_level() -> tuple[list[CommandNode], list[CommandNode]]:
    trail: list[CommandNode] = []
    nodes = root_nodes_for_current_surface()
    for node_id in list(state.get("command_path", [])):
        node = next((candidate for candidate in nodes if candidate.id == node_id), None)
        if node is None:
            state["command_path"] = []
            state["pending_command"] = None
            return [], root_nodes_for_current_surface()
        trail.append(node)
        nodes = list(node.children)
    return trail, nodes


def set_command_surface(surface: str) -> None:
    normalized = normalize_command_surface(surface)
    if state.get("command_surface") != normalized:
        state["command_surface"] = normalized
        state["command_path"] = []
        state["pending_command"] = None
    command_tree.refresh()


def command_surface_click_handler(surface: str):
    def handler() -> None:
        set_command_surface(surface)

    return handler


def enter_command_node(node: CommandNode) -> None:
    state["pending_command"] = None
    state["command_path"] = [*state.get("command_path", []), node.id]
    command_tree.refresh()


def select_command_node(node: CommandNode) -> None:
    state["pending_command"] = node
    command_tree.refresh()


async def activate_command_node(node: CommandNode) -> None:
    if node.children:
        enter_command_node(node)
        return
    if node.fields:
        select_command_node(node)
        return
    state["pending_command"] = None
    await start_operation(node.to_operation(dict(node.parameters)))


def command_click_handler(node: CommandNode):
    async def handler() -> None:
        await activate_command_node(node)

    return handler


def go_back_command() -> None:
    if state.get("pending_command") is not None:
        state["pending_command"] = None
    else:
        path = list(state.get("command_path", []))
        if path:
            path.pop()
        state["command_path"] = path
    command_tree.refresh()


def field_id(field: dict[str, Any]) -> str:
    return str(field.get("id") or field.get("name") or "").strip()


def field_label(field: dict[str, Any]) -> str:
    language = settings.language
    if language == "ru" and field.get("label_ru"):
        return str(field["label_ru"])
    return str(field.get("label") or field.get("title") or field_id(field))


def field_hint(field: dict[str, Any]) -> str:
    language = settings.language
    if language == "ru" and field.get("hint_ru"):
        return str(field["hint_ru"])
    return str(field.get("hint") or "")


def field_refresh_label(field: dict[str, Any]) -> str:
    language = settings.language
    if language == "ru" and field.get("refresh_label_ru"):
        return str(field["refresh_label_ru"])
    return str(field.get("refresh_label") or tr("refresh_options"))


def field_default(field: dict[str, Any]) -> Any:
    if "default" in field:
        return field["default"]
    kind = str(field.get("type", field.get("kind", "text"))).lower()
    options = field.get("options", [])
    if kind in {"checkboxes", "multi_checkbox", "multicheckbox", "multi-select", "multiselect"}:
        if not isinstance(options, list):
            return []
        selected: list[Any] = []
        for option in options:
            if isinstance(option, dict) and option.get("default", False):
                selected.append(option.get("value", option.get("id", option.get("label"))))
        return selected
    if isinstance(options, list) and options:
        first = options[0]
        if isinstance(first, dict):
            return first.get("value", first.get("id", ""))
        return first
    return ""


def current_field_value(field: dict[str, Any]) -> Any:
    key = field_id(field)
    values = state.setdefault("field_values", {})
    if key not in values:
        values[key] = field_default(field)
    return values[key]


def set_field_value(key: str, value: Any) -> None:
    state.setdefault("field_values", {})[key] = value


def apply_operation_field_updates(data: dict[str, Any]) -> None:
    updates = data.get("field_updates") if isinstance(data, dict) else None
    if not isinstance(updates, dict) or not updates:
        return
    field_values = state.setdefault("field_values", {})
    changed: list[str] = []
    for key, value in updates.items():
        key_text = str(key).strip()
        if not key_text:
            continue
        field_values[key_text] = value
        changed.append(key_text)
    if changed:
        add_log("Updated GUI fields: " + ", ".join(changed))
        command_tree.refresh()


def adjusted_number_value(field: dict[str, Any], current: Any, direction: int) -> int | float:
    step_raw = field.get("step", 1)
    try:
        step = float(step_raw)
    except (TypeError, ValueError):
        step = 1.0

    seed = current
    if seed is None or seed == "":
        seed = field_default(field) or 0
    try:
        value = float(seed)
    except (TypeError, ValueError):
        value = 0.0

    value += step * (1 if direction > 0 else -1)
    for bound_key, clamp in (("min", max), ("max", min)):
        bound = field.get(bound_key)
        if bound is None or bound == "":
            continue
        try:
            value = clamp(value, float(bound))
        except (TypeError, ValueError):
            continue

    kind = str(field.get("type", field.get("kind", "number"))).lower()
    integer_like = kind in {"number", "int", "integer"} and float(step).is_integer()
    return int(round(value)) if integer_like else round(value, 6)


def spin_number_field(key: str, field: dict[str, Any], control: Any, direction: int) -> None:
    value = adjusted_number_value(field, state.setdefault("field_values", {}).get(key), direction)
    set_field_value(key, value)
    control.set_value(value)


def dynamic_option_source(field: dict[str, Any]) -> str:
    return str(field.get("options_source") or field.get("source") or "").strip()


def refresh_dynamic_options(field: dict[str, Any]) -> None:
    source = dynamic_option_source(field)
    if source:
        dynamic_option_cache.pop(source, None)
    key = field_id(field)
    if key:
        state.setdefault("field_values", {}).pop(key, None)
    command_tree.refresh()


def refresh_options_click_handler(field: dict[str, Any]):
    def handler() -> None:
        refresh_dynamic_options(field)

    return handler


def apply_preset(preset: dict[str, Any]) -> None:
    values = preset.get("values", {})
    if not isinstance(values, dict):
        return
    field_values = state.setdefault("field_values", {})
    for key, value in values.items():
        field_values[str(key)] = value
    command_tree.refresh()


def preset_label(preset: dict[str, Any]) -> str:
    if settings.language == "ru" and preset.get("label_ru"):
        return str(preset["label_ru"])
    return str(preset.get("label") or preset.get("title") or preset.get("id") or "Preset")


def preset_click_handler(preset: dict[str, Any]):
    def handler() -> None:
        apply_preset(preset)

    return handler


def load_dynamic_options(field: dict[str, Any]) -> list[Any]:
    source = dynamic_option_source(field)
    if not source:
        return []

    cache_seconds = float(field.get("cache_seconds", 45) or 0)
    now = time.monotonic()
    cached = dynamic_option_cache.get(source)
    if cached and cache_seconds > 0 and now - cached[0] < cache_seconds:
        return cached[1]

    try:
        if ":" not in source:
            raise RuntimeError(f"Dynamic option source must use module:function syntax: {source}")
        module_name, function_name = source.split(":", 1)
        module = importlib.import_module(module_name)
        provider = getattr(module, function_name)
        try:
            options = provider(ROOT)
        except TypeError:
            options = provider()
        if not isinstance(options, list):
            raise RuntimeError(f"Dynamic option source returned {type(options).__name__}, expected list.")
    except Exception as exc:
        message = f"Option source failed: {exc.__class__.__name__}: {exc}"
        options = [{"value": "", "label": message, "label_ru": message}]

    dynamic_option_cache[source] = (now, options)
    return options


def field_options(field: dict[str, Any]) -> list[Any]:
    dynamic_options = load_dynamic_options(field)
    if dynamic_options:
        return dynamic_options
    options = field.get("options", [])
    return options if isinstance(options, list) else []


def select_options(field: dict[str, Any]) -> dict[Any, str] | list[Any]:
    options = field_options(field)
    if all(isinstance(option, dict) for option in options):
        result: dict[Any, str] = {}
        for option in options:
            value = option.get("value", option.get("id", ""))
            if settings.language == "ru" and option.get("label_ru"):
                label = str(option["label_ru"])
            else:
                label = str(option.get("label") or option.get("title") or value)
            result[value] = label
        return result
    return options


def option_value(option: Any) -> Any:
    if isinstance(option, dict):
        return option.get("value", option.get("id", option.get("label", "")))
    return option


def select_option_values(field: dict[str, Any]) -> list[Any]:
    return [option_value(option) for option in field_options(field)]


def normalize_choice_value(field: dict[str, Any], value: Any) -> Any:
    values = select_option_values(field)
    if not values:
        return value
    if value in values:
        return value
    return values[0]


def option_label(option: Any) -> str:
    if not isinstance(option, dict):
        return str(option)
    language = settings.language
    if language == "ru" and option.get("label_ru"):
        return str(option["label_ru"])
    return str(option.get("label") or option.get("title") or option_value(option))


def item_hint(item: Any) -> str:
    if not isinstance(item, dict):
        return ""
    if settings.language == "ru" and item.get("hint_ru"):
        return str(item["hint_ru"])
    return str(item.get("hint") or item.get("description") or "")


def item_summary(item: Any) -> str:
    if not isinstance(item, dict):
        return ""
    if settings.language == "ru" and item.get("summary_ru"):
        return str(item["summary_ru"])
    return str(item.get("summary") or "")


def item_icon(item: Any) -> str:
    return ""


def item_pair_label(item: Any) -> str:
    if not isinstance(item, dict):
        return ""
    if settings.language == "ru" and item.get("pair_ru"):
        return str(item["pair_ru"])
    return str(item.get("pair") or "")


def item_tone(item: Any) -> str:
    if not isinstance(item, dict):
        return "medium"
    tone = str(item.get("tone") or item.get("safety") or "").strip().lower()
    aliases = {
        "safe": "friendly",
        "success": "friendly",
        "friendly": "friendly",
        "info": "medium",
        "moderate": "medium",
        "medium": "medium",
        "warning": "danger",
        "danger": "danger",
        "dangerous": "danger",
        "destructive": "danger",
    }
    return aliases.get(tone, "medium")


def info_badge_tone(item: Any) -> str:
    if not isinstance(item, dict):
        return "medium"
    tone = str(item.get("tone") or item.get("safety") or "").strip().lower().replace("_", "-")
    aliases = {
        "safe": "friendly",
        "success": "friendly",
        "friendly": "friendly",
        "info": "medium",
        "moderate": "medium",
        "medium": "medium",
        "warning": "danger",
        "danger": "danger",
        "dangerous": "danger",
        "destructive": "danger",
        "lock": "lock",
        "driver-lock": "lock",
        "generic-lock": "lock",
        "oem": "oem-tail",
        "oem-tail": "oem-tail",
        "rev-tail": "oem-tail",
        "cleanup-tail": "oem-tail",
    }
    return aliases.get(tone, "medium")


def strictest_tone(options: list[Any]) -> str:
    rank = {"friendly": 0, "medium": 1, "danger": 2}
    result = "friendly"
    for option in options:
        tone = item_tone(option)
        if rank.get(tone, 1) > rank[result]:
            result = tone
    return result


def safety_choice_groups(field: dict[str, Any]) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    by_key: dict[str, dict[str, Any]] = {}
    for raw_option in field_options(field):
        option = raw_option if isinstance(raw_option, dict) else {"value": raw_option, "label": str(raw_option)}
        label = item_pair_label(option) or option_label(option)
        key = str(label).strip().lower()
        if key not in by_key:
            group = {"label": label, "options": []}
            by_key[key] = group
            groups.append(group)
        by_key[key]["options"].append(option)
    for group in groups:
        group["tone"] = strictest_tone(group["options"])
    return groups


def checkbox_options(field: dict[str, Any]) -> list[tuple[Any, str]]:
    options = field_options(field)
    return [(option_value(option), option_label(option)) for option in options]


def checkbox_option_items(field: dict[str, Any]) -> list[tuple[Any, str, str]]:
    options = field_options(field)
    return [(option_value(option), option_label(option), item_hint(option)) for option in options]


def option_group_label(option: Any) -> str:
    if not isinstance(option, dict):
        return ""
    if settings.language == "ru" and option.get("group_ru"):
        return str(option["group_ru"]).strip()
    return str(option.get("group") or "").strip()


def checkbox_option_groups(field: dict[str, Any]) -> list[tuple[str, list[tuple[Any, str, str]]]]:
    """Split checkbox options into labelled family blocks; keeps manifest order."""
    groups: list[tuple[str, list[tuple[Any, str, str]]]] = []
    index: dict[str, int] = {}
    for option in field_options(field):
        label = option_group_label(option)
        item = (option_value(option), option_label(option), item_hint(option))
        if label not in index:
            index[label] = len(groups)
            groups.append((label, [item]))
        else:
            groups[index[label]][1].append(item)
    return groups


def checkbox_group_accents(field: dict[str, Any]) -> dict[str, str]:
    """Accent colour per chip family, keyed by the label the family renders with.

    Looked up first in the field's `group_accents` map (keyed by the untranslated
    group name, so the mapping survives a language switch), then on the first
    option of the family that carries an `accent`.
    """
    declared = field.get("group_accents")
    declared = declared if isinstance(declared, dict) else {}
    accents: dict[str, str] = {}
    for option in field_options(field):
        label = option_group_label(option)
        if not label or label in accents:
            continue
        raw = ""
        if isinstance(option, dict):
            raw = str(declared.get(option.get("group") or "") or option.get("accent") or "")
        accent = item_accent({"accent": raw})
        if accent:
            accents[label] = accent
    return accents


def is_chip_checkbox_group(field: dict[str, Any]) -> bool:
    if field_display(field) in {"chips", "chip", "chip_groups", "chip-groups"}:
        return True
    return any(option_group_label(option) for option in field_options(field))


def ordered_checkbox_values(field: dict[str, Any], values: Any) -> list[Any]:
    if not isinstance(values, list):
        return []
    allowed = select_option_values(field)
    if not allowed:
        return values
    selected = set(values)
    return [value for value in allowed if value in selected]


def checkbox_group_presets(field: dict[str, Any]) -> list[dict[str, Any]]:
    presets = field.get("selection_presets", field.get("presets", []))
    if not isinstance(presets, list):
        return []
    return [preset for preset in presets if isinstance(preset, dict)]


def checkbox_group_preset_values(field: dict[str, Any], preset: dict[str, Any]) -> list[Any]:
    mode = str(preset.get("mode") or "").strip().lower()
    if mode in {"all", "select_all"}:
        return select_option_values(field)
    if mode in {"none", "clear", "empty", "select_none"}:
        return []
    if mode in {"default", "defaults"}:
        return ordered_checkbox_values(field, field_default(field))
    return ordered_checkbox_values(field, preset.get("values", []))


def checkbox_group_preset_label(preset: dict[str, Any]) -> str:
    if settings.language == "ru" and preset.get("label_ru"):
        return str(preset["label_ru"])
    return str(preset.get("label") or preset.get("title") or preset.get("id") or "Preset")


def checkbox_group_preset_click_handler(field: dict[str, Any], key: str, preset: dict[str, Any]):
    def handler() -> None:
        set_field_value(key, checkbox_group_preset_values(field, preset))
        command_tree.refresh()

    return handler


def is_checkbox_group(field: dict[str, Any]) -> bool:
    kind = str(field.get("type", field.get("kind", "text"))).lower()
    return kind in {"checkboxes", "multi_checkbox", "multicheckbox", "multi-select", "multiselect"}


def is_workbench_route_field(field: dict[str, Any]) -> bool:
    if "workbench_route" in field and not bool(field.get("workbench_route")):
        # Managed system paths (policy folders, backup roots) keep their own value
        # and must never be replaced by the workbench source/target routes.
        return False
    key = field_id(field).lower()
    kind = str(field.get("type", field.get("kind", ""))).lower()
    label_text = " ".join(
        str(field.get(item) or "").lower()
        for item in ("label", "label_ru", "title", "hint", "hint_ru", "placeholder")
    )
    haystack = f"{key} {label_text}"
    route_markers = (
        "input",
        "output",
        "source",
        "destination",
        "target",
        "src",
        "dst",
        "исход",
        "источник",
        "вход",
        "выход",
        "цель",
        "результ",
        "приём",
        "прием",
    )
    path_markers = ("path", "folder", "directory", "dir", "пап", "каталог", "путь")
    return kind in {"path", "folder", "directory"} or (
        any(marker in haystack for marker in route_markers)
        and any(marker in haystack for marker in path_markers)
    )


def field_display(field: dict[str, Any]) -> str:
    return str(field.get("display") or field.get("ui") or "").strip().lower()


def is_info_badge_field(field: dict[str, Any]) -> bool:
    kind = str(field.get("type", field.get("kind", "text"))).lower()
    return kind in {"info_badges", "info-badges", "static_badges", "static-badges", "badges"}


def command_visible_fields(fields: tuple[dict[str, Any], ...] | list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [field for field in fields if not is_workbench_route_field(field)]


def workbench_value_for_field(field: dict[str, Any]) -> str:
    key = field_id(field).lower()
    label_text = " ".join(
        str(field.get(item) or "").lower()
        for item in ("label", "label_ru", "title", "hint", "hint_ru", "placeholder")
    )
    haystack = f"{key} {label_text}"
    if any(marker in haystack for marker in ("output", "destination", "target", "dst", "выход", "цель", "результ", "приём", "прием")):
        return str(current_target_path())
    return str(current_source_path())


def field_container_classes(field: dict[str, Any]) -> str:
    span = str(field.get("span") or field.get("width") or "").lower()
    kind = str(field.get("type", field.get("kind", "text"))).lower()
    display = field_display(field)
    base = "audion-field"
    if bool(field.get("hide_hint", False)):
        base += " audion-field-hide-hint"
    if display in {"safety_buttons", "safety-buttons", "risk_buttons", "risk-buttons"}:
        return f"{base} audion-field-wide"
    if display in MODE_BUTTON_DISPLAYS:
        return f"{base} audion-field-wide"
    # A checkbox whose explanation runs several sentences takes the full row:
    # inside one narrow grid cell that text turns into a tall ribbon.
    if kind in {"checkbox", "bool", "boolean", "toggle"} and len(field_hint(field)) > 90:
        return f"{base} audion-field-wide"
    if span in {"full", "wide", "100%", "1/-1"}:
        return f"{base} audion-field-wide"
    if kind in {"select", "choice", "format"}:
        return f"{base} audion-field-select"
    if kind in {"textarea", "multiline", "path", "file", "folder"}:
        return f"{base} audion-field-wide"
    if kind in {"preset_buttons", "presets", "profile_buttons", "profiles"}:
        return f"{base} audion-field-wide"
    if is_info_badge_field(field):
        return f"{base} audion-field-wide"
    if kind in {"checkboxes", "multi_checkbox", "multicheckbox", "multi-select", "multiselect"}:
        return f"{base} audion-field-wide"
    if kind in {"smb_login_cache", "smb-login-cache"}:
        return f"{base} audion-field-wide"
    return base


def safety_choice_click_handler(key: str, value: Any):
    def handler(_event: Any = None) -> None:
        set_field_value(key, value)
        command_tree.refresh()

    return handler


def safety_group_classes(group: dict[str, Any]) -> str:
    tone = str(group.get("tone") or "medium")
    classes = ["audion-safety-group", f"audion-safety-group-{tone}"]
    # Three or more cards get a two-column slot, so they spread sideways
    # instead of forming a tall stack next to half-empty neighbours.
    if len(group.get("options") or []) >= 3:
        classes.append("audion-safety-group-wide")
    return " ".join(classes)


def safety_choice_classes(option: Any, selected: bool) -> str:
    classes = ["audion-safety-choice", f"audion-safety-choice-{item_tone(option)}"]
    if not item_icon(option):
        classes.append("audion-safety-choice-no-icon")
    if selected:
        classes.append("audion-safety-choice-selected")
    return " ".join(classes)


MODE_BUTTON_DISPLAYS = {"mode_buttons", "mode-buttons", "toggle_buttons", "toggle-buttons", "toggles"}


def item_accent(item: Any) -> str:
    """Per-option accent colour for mode buttons; empty means the shared default."""
    if not isinstance(item, dict):
        return ""
    raw = str(item.get("accent") or "").strip()
    if not raw.startswith("#") or not 4 <= len(raw) <= 9:
        return ""
    return raw if all(char in "0123456789abcdefABCDEF" for char in raw[1:]) else ""


def mode_button_classes(selected: bool) -> str:
    classes = ["audion-mode-button"]
    if selected:
        classes.append("audion-mode-button-active")
    return " ".join(classes)


def render_mode_buttons_field(field: dict[str, Any], key: str, value: Any, label: str, hint: str) -> None:
    """A choice field drawn as one row of coloured toggles instead of a dropdown."""
    label_element = ui.label(label).classes("audion-field-label")
    soft_tooltip(label_element, hint)
    with ui.element("div").classes("audion-mode-buttons"):
        for option in field_options(field):
            option_key = option_value(option)
            selected = option_key == value
            button = (
                ui.element("button")
                .props(f"type=button aria-pressed={'true' if selected else 'false'}")
                .classes(mode_button_classes(selected))
                .on("click", safety_choice_click_handler(key, option_key))
            )
            accent = item_accent(option)
            if accent:
                button.style(f"--audion-mode-accent: {accent}")
            soft_tooltip(button, item_hint(option))
            with button:
                ui.label(option_label(option)).classes("audion-mode-button-title")
    if hint:
        ui.label(hint).classes("audion-field-hint")


def render_safety_choice_field(field: dict[str, Any], key: str, value: Any, label: str, hint: str) -> None:
    label_element = ui.label(label).classes("audion-field-label")
    soft_tooltip(label_element, hint)
    with ui.element("div").classes("audion-safety-grid"):
        for group in safety_choice_groups(field):
            with ui.element("div").classes(safety_group_classes(group)):
                ui.label(str(group.get("label") or "")).classes("audion-safety-group-title")
                with ui.element("div").classes("audion-safety-group-actions"):
                    for option in group.get("options", []):
                        option_key = option_value(option)
                        selected = option_key == value
                        pressed = "true" if selected else "false"
                        button = (
                            ui.element("button")
                            .props(f"type=button aria-pressed={pressed}")
                            .classes(safety_choice_classes(option, selected))
                            .on("click", safety_choice_click_handler(key, option_key))
                        )
                        soft_tooltip(button, item_hint(option))
                        with button:
                            icon = item_icon(option)
                            if icon:
                                ui.icon(icon).classes("audion-safety-choice-icon")
                            with ui.element("div").classes("audion-safety-choice-text"):
                                ui.label(option_label(option)).classes("audion-safety-choice-title")
                                summary = item_summary(option)
                                if summary:
                                    ui.label(summary).classes("audion-safety-choice-summary")
    if hint:
        ui.label(hint).classes("audion-field-hint")


def smb_login_default(field: dict[str, Any]) -> dict[str, str]:
    default = field_default(field)
    if isinstance(default, dict):
        return {
            "computer": smb_clean_computer(default.get("computer")),
            "user": smb_clean_user(default.get("user")),
        }
    return {"computer": "", "user": ""}


def smb_login_state(field: dict[str, Any]) -> dict[str, str]:
    raw = current_field_value(field)
    default = smb_login_default(field)
    value = raw if isinstance(raw, dict) else {}
    records = load_smb_login_records()
    selected_key = str(value.get("record_key") or "")
    selected = next((record for record in records if smb_record_key(record["computer"], record["user"]) == selected_key), None)
    computer_manual = smb_clean_computer(value.get("computer_manual"))
    user_manual = smb_clean_user(value.get("user_manual"))
    use_default = str(value.get("cleared") or "").lower() != "true"
    computer = smb_clean_computer(value.get("computer")) or (selected["computer"] if selected else "") or (default["computer"] if use_default else "")
    user = smb_clean_user(value.get("user")) or (selected["user"] if selected else "") or (default["user"] if use_default else "")
    if selected is None and selected_key:
        selected_key = ""
    return {
        "record_key": selected_key,
        "computer": computer,
        "user": user,
        "computer_manual": computer_manual,
        "user_manual": user_manual,
        "cleared": "true" if not use_default else "",
    }


def smb_effective_login(value: dict[str, str]) -> tuple[str, str]:
    computer = smb_clean_computer(value.get("computer_manual")) or smb_clean_computer(value.get("computer"))
    user = smb_clean_user(value.get("user_manual")) or smb_clean_user(value.get("user"))
    return computer, user


def smb_cache_options(records: list[dict[str, str]], primary: str) -> dict[str, str]:
    options: dict[str, str] = {}
    for record in records:
        key = smb_record_key(record["computer"], record["user"])
        options[key] = f"{record['computer']} | {record['user']}"
    return options


def smb_select_pair_handler(field: dict[str, Any]):
    def handler(event: Any) -> None:
        selected_key = str(getattr(event, "value", "") or "")
        record = next(
            (
                item
                for item in load_smb_login_records()
                if smb_record_key(item["computer"], item["user"]) == selected_key
            ),
            None,
        )
        if not record:
            return
        set_field_value(
            field_id(field),
            {
                "record_key": selected_key,
                "computer": record["computer"],
                "user": record["user"],
                "computer_manual": "",
                "user_manual": "",
                "cleared": "",
            },
        )
        command_tree.refresh()

    return handler


def smb_manual_change_handler(field: dict[str, Any], part: str):
    def handler(event: Any) -> None:
        value = smb_login_state(field)
        value[f"{part}_manual"] = smb_clean_computer(event.value) if part == "computer" else smb_clean_user(event.value)
        set_field_value(field_id(field), value)

    return handler


def smb_open_select_popup(control: Any) -> None:
    try:
        control.run_method("showPopup")
    except Exception:
        pass


def smb_save_pair_handler(field: dict[str, Any]):
    def handler() -> None:
        value = smb_login_state(field)
        computer, user = smb_effective_login(value)
        if not computer or not user:
            safe_notify("SMB: заполните имя компьютера и пользователя.", "warning")
            return
        record_key = upsert_smb_login_record(computer, user)
        set_field_value(
            field_id(field),
            {
                "record_key": record_key,
                "computer": computer,
                "user": user,
                "computer_manual": "",
                "user_manual": "",
                "cleared": "",
            },
        )
        safe_notify("SMB: запись сохранена.", "positive")
        command_tree.refresh()

    return handler


def smb_delete_pair_handler(field: dict[str, Any]):
    def handler() -> None:
        value = smb_login_state(field)
        record_key = value.get("record_key") or smb_record_key(*smb_effective_login(value))
        deleted = delete_smb_login_record(record_key)
        if not deleted:
            safe_notify("SMB: запись не найдена в кэше.", "warning")
            return
        computer, user = smb_effective_login(value)
        set_field_value(
            field_id(field),
            {
                "record_key": "",
                "computer": computer,
                "user": user,
                "computer_manual": value.get("computer_manual", ""),
                "user_manual": value.get("user_manual", ""),
                "cleared": value.get("cleared", ""),
            },
        )
        safe_notify("SMB: запись удалена.", "positive")
        command_tree.refresh()

    return handler


def smb_clear_pairs_handler(field: dict[str, Any]):
    def handler() -> None:
        clear_smb_login_records()
        set_field_value(
            field_id(field),
            {
                "record_key": "",
                "computer": "",
                "user": "",
                "computer_manual": "",
                "user_manual": "",
                "cleared": "true",
            },
        )
        safe_notify("SMB: кэш очищен.", "positive")
        command_tree.refresh()

    return handler


def render_smb_cache_button(icon: str, tooltip: str, handler: Any) -> None:
    button = ui.button(icon=icon, on_click=handler).props("dense flat round").classes("audion-action audion-smb-cache-icon-button")
    soft_tooltip(button, tooltip)


def render_smb_login_cache_field(field: dict[str, Any], key: str, label: str, hint: str) -> None:
    value = smb_login_state(field)
    set_field_value(key, value)
    records = load_smb_login_records()
    options_by_computer = smb_cache_options(records, "computer")
    options_by_user = smb_cache_options(records, "user")
    selected_key = value.get("record_key") if value.get("record_key") in options_by_computer else None
    effective_computer, effective_user = smb_effective_login(value)

    label_element = ui.label(label).classes("audion-field-label")
    soft_tooltip(label_element, hint)
    with ui.element("div").classes("audion-smb-cache"):
        with ui.element("div").classes("audion-smb-cache-grid"):
            with ui.element("div").classes("audion-smb-cache-column"):
                computer_select = ui.select(
                    options=options_by_computer,
                    label="Computer cache" if settings.language != "ru" else "Кэш компьютеров",
                    value=selected_key,
                    on_change=smb_select_pair_handler(field),
                ).props("dense outlined options-dense popup-content-class=audion-select-popup").classes("audion-select audion-smb-cache-select")
                computer_select.on("click", lambda _event, control=computer_select: smb_open_select_popup(control))
                computer_select.on("focus", lambda _event, control=computer_select: smb_open_select_popup(control))
                with ui.row().classes("audion-smb-cache-button-row"):
                    render_smb_cache_button("delete", "Удалить выбранную SMB-запись", smb_delete_pair_handler(field))
                    render_smb_cache_button("delete_sweep", "Очистить весь SMB-кэш", smb_clear_pairs_handler(field))
                ui.input(
                    label="New computer" if settings.language != "ru" else "Новый компьютер",
                    value=value.get("computer_manual", ""),
                    placeholder=str(field.get("computer_placeholder") or "COMPUTER-NAME"),
                    on_change=smb_manual_change_handler(field, "computer"),
                ).props("dense outlined").classes("audion-smb-manual-input w-full")

            with ui.element("div").classes("audion-smb-cache-column"):
                user_select = ui.select(
                    options=options_by_user,
                    label="User cache" if settings.language != "ru" else "Кэш пользователей",
                    value=selected_key,
                    on_change=smb_select_pair_handler(field),
                ).props("dense outlined options-dense popup-content-class=audion-select-popup").classes("audion-select audion-smb-cache-select")
                user_select.on("click", lambda _event, control=user_select: smb_open_select_popup(control))
                user_select.on("focus", lambda _event, control=user_select: smb_open_select_popup(control))
                with ui.row().classes("audion-smb-cache-button-row"):
                    render_smb_cache_button("delete", "Удалить выбранную SMB-запись", smb_delete_pair_handler(field))
                    render_smb_cache_button("delete_sweep", "Очистить весь SMB-кэш", smb_clear_pairs_handler(field))
                ui.input(
                    label="New user" if settings.language != "ru" else "Новый пользователь",
                    value=value.get("user_manual", ""),
                    placeholder=str(field.get("user_placeholder") or "User Name"),
                    on_change=smb_manual_change_handler(field, "user"),
                ).props("dense outlined").classes("audion-smb-manual-input w-full")

        with ui.row().classes("audion-smb-current-row items-center gap-2"):
            current_text = f"{effective_computer or '...'} | {effective_user or '...'}"
            ui.label(current_text).classes("audion-smb-current")
            ui.space()
            render_smb_cache_button("add", "Сохранить текущую SMB-пару", smb_save_pair_handler(field))
    if hint:
        ui.label(hint).classes("audion-field-hint")


def render_info_badge_field(field: dict[str, Any], label: str, hint: str) -> None:
    if dynamic_option_source(field):
        items = field_options(field)
    else:
        items = field.get("items", field.get("options", []))
    if not isinstance(items, list):
        items = []

    label_element = ui.label(label).classes("audion-field-label")
    soft_tooltip(label_element, hint)
    if dynamic_option_source(field) and bool(field.get("show_refresh", True)):
        refresh_button = ui.button(
            field_refresh_label(field),
            on_click=refresh_options_click_handler(field),
        ).props("dense flat no-wrap").classes("audion-action mb-1 rounded-lg")
        soft_tooltip(refresh_button, hint)
    with ui.element("div").classes("audion-info-badge-row"):
        for item in items:
            if not isinstance(item, dict):
                item = {"label": str(item)}
            badge = ui.element("div").classes(f"audion-info-badge audion-info-badge-{info_badge_tone(item)}")
            soft_tooltip(badge, item_hint(item))
            with badge:
                pair = item_pair_label(item)
                if pair:
                    ui.label(pair).classes("audion-info-badge-pair")
                ui.label(option_label(item)).classes("audion-info-badge-title")
                summary = item_summary(item)
                if summary:
                    ui.label(summary).classes("audion-info-badge-summary")
    if hint:
        ui.label(hint).classes("audion-field-hint")


def render_field(field: dict[str, Any]) -> None:
    key = field_id(field)
    if not key:
        return
    kind = str(field.get("type", field.get("kind", "text"))).lower()
    label = field_label(field)
    value = current_field_value(field)
    hint = field_hint(field)

    with ui.element("div").classes(field_container_classes(field)):
        if is_info_badge_field(field):
            render_info_badge_field(field, label, hint)
            return

        if kind in {"smb_login_cache", "smb-login-cache"}:
            render_smb_login_cache_field(field, key, label, hint)
            return

        if kind in {"preset_buttons", "presets", "profile_buttons", "profiles"}:
            presets = field.get("presets", field.get("options", []))
            if not isinstance(presets, list):
                presets = []
            label_element = ui.label(label).classes("audion-field-label")
            soft_tooltip(label_element, hint)
            with ui.row().classes("audion-choice-row"):
                for preset in presets:
                    if not isinstance(preset, dict):
                        continue
                    preset_button = ui.button(
                        preset_label(preset),
                        on_click=preset_click_handler(preset),
                    ).props("dense flat no-wrap").classes("audion-action rounded-lg")
                    soft_tooltip(preset_button, item_hint(preset))
            if hint:
                ui.label(hint).classes("audion-field-hint")
            return

        if kind in {"select", "choice", "format"}:
            value = normalize_choice_value(field, value)
            set_field_value(key, value)
            if field_display(field) in MODE_BUTTON_DISPLAYS:
                render_mode_buttons_field(field, key, value, label, hint)
                return
            select = ui.select(
                options=select_options(field),
                label=label,
                value=value,
                on_change=lambda event, item_key=key: set_field_value(item_key, event.value),
            )
            props = "dense outlined popup-content-class=audion-select-popup"
            if bool(field.get("searchable", field.get("with_input", False))):
                props += " use-input input-debounce=0"
            select.props(props).classes("audion-select w-full")
            soft_tooltip(select, hint)
            if dynamic_option_source(field) and bool(field.get("show_refresh", True)):
                refresh_button = ui.button(
                    field_refresh_label(field),
                    on_click=refresh_options_click_handler(field),
                ).props("dense flat no-wrap").classes("audion-action mt-1 rounded-lg")
                soft_tooltip(refresh_button, hint)
            if hint:
                ui.label(hint).classes("audion-field-hint")
            return

        if kind in {"radio", "radiobuttons", "radio-buttons"}:
            value = normalize_choice_value(field, value)
            set_field_value(key, value)
            if field_display(field) in {"safety_buttons", "safety-buttons", "risk_buttons", "risk-buttons"}:
                render_safety_choice_field(field, key, value, label, hint)
                return
            if field_display(field) in MODE_BUTTON_DISPLAYS:
                render_mode_buttons_field(field, key, value, label, hint)
                return
            label_element = ui.label(label).classes("audion-field-label")
            soft_tooltip(label_element, hint)
            radio = ui.radio(
                options=select_options(field),
                value=value,
                on_change=lambda event, item_key=key: set_field_value(item_key, event.value),
            ).props("dense").classes("audion-choice-grid")
            soft_tooltip(radio, hint)
            if dynamic_option_source(field) and bool(field.get("show_refresh", True)):
                refresh_button = ui.button(
                    field_refresh_label(field),
                    on_click=refresh_options_click_handler(field),
                ).props("dense flat no-wrap").classes("audion-action mt-1 rounded-lg")
                soft_tooltip(refresh_button, hint)
            if hint:
                ui.label(hint).classes("audion-field-hint")
            return

        if kind in {"number", "int", "integer", "float"}:
            number_input = ui.number(
                label=label,
                value=value if value != "" else None,
                min=field.get("min"),
                max=field.get("max"),
                step=field.get("step", 1),
                on_change=lambda event, item_key=key: set_field_value(item_key, event.value),
            ).props("dense outlined").classes("audion-number w-full")
            soft_tooltip(number_input, hint)
            with number_input.add_slot("append"):
                with ui.element("div").classes("audion-number-spinner"):
                    ui.button(
                        icon="keyboard_arrow_up",
                        on_click=lambda item_key=key, item_field=field, control=number_input: spin_number_field(item_key, item_field, control, 1),
                    ).props("dense flat round tabindex=-1").classes("audion-number-spin-button")
                    ui.button(
                        icon="keyboard_arrow_down",
                        on_click=lambda item_key=key, item_field=field, control=number_input: spin_number_field(item_key, item_field, control, -1),
                    ).props("dense flat round tabindex=-1").classes("audion-number-spin-button")
            if hint:
                ui.label(hint).classes("audion-field-hint")
            return

        if kind in {"password", "secret"}:
            input_control = ui.input(
                label=label,
                value=str(value) if value is not None else "",
                placeholder=str(field.get("placeholder", "")),
                password=True,
                password_toggle_button=True,
                on_change=lambda event, item_key=key: set_field_value(item_key, event.value),
            ).props("dense outlined").classes("w-full")
            soft_tooltip(input_control, hint)
            if hint:
                ui.label(hint).classes("audion-field-hint")
            return

        if kind in {"textarea", "multiline"}:
            textarea_control = ui.textarea(
                label=label,
                value=str(value) if value is not None else "",
                placeholder=str(field.get("placeholder", "")),
                on_change=lambda event, item_key=key: set_field_value(item_key, event.value),
            ).props("dense outlined autogrow").classes("w-full")
            soft_tooltip(textarea_control, hint)
            if hint:
                ui.label(hint).classes("audion-field-hint")
            return

        if kind in {"checkbox", "bool", "boolean", "toggle"}:
            checkbox_control = ui.checkbox(
                label,
                value=bool(value),
                on_change=lambda event, item_key=key: set_field_value(item_key, bool(event.value)),
            ).props("dense").classes("audion-single-checkbox")
            soft_tooltip(checkbox_control, hint)
            if hint:
                ui.label(hint).classes("audion-field-hint")
            return

        if is_checkbox_group(field):
            selected = set(value if isinstance(value, list) else [])
            controls: dict[Any, Any] = {}

            def sync_checkboxes(item_key: str = key) -> None:
                set_field_value(
                    item_key,
                    [option_key for option_key, checkbox in controls.items() if bool(checkbox.value)],
                )

            label_element = ui.label(label).classes("audion-field-label")
            soft_tooltip(label_element, hint)
            if dynamic_option_source(field) and bool(field.get("show_refresh", True)):
                refresh_button = ui.button(
                    field_refresh_label(field),
                    on_click=refresh_options_click_handler(field),
                ).props("dense flat no-wrap").classes("audion-action mb-1 rounded-lg")
                soft_tooltip(refresh_button, hint)
            presets = checkbox_group_presets(field)
            if presets:
                with ui.row().classes("audion-checkbox-preset-row"):
                    for preset in presets:
                        preset_button = ui.button(
                            checkbox_group_preset_label(preset),
                            on_click=checkbox_group_preset_click_handler(field, key, preset),
                        ).props("dense flat no-wrap").classes("audion-action audion-checkbox-preset-button rounded-lg")
                        soft_tooltip(preset_button, item_hint(preset))
            if is_chip_checkbox_group(field):
                family_accents = checkbox_group_accents(field)
                for family_label, family_items in checkbox_option_groups(field):
                    family = ui.element("div").classes("audion-chip-family")
                    family_accent = family_accents.get(family_label, "")
                    if family_accent:
                        family.style(f"--audion-chip-accent: {family_accent}")
                    with family:
                        if family_label:
                            ui.label(family_label).classes("audion-chip-family-title")
                        with ui.element("div").classes("audion-chip-checkboxes"):
                            for option_key, option_text, option_hint in family_items:
                                checkbox = ui.checkbox(
                                    option_text,
                                    value=option_key in selected,
                                    on_change=lambda _event: sync_checkboxes(),
                                ).props("dense").classes("audion-chip-checkbox")
                                soft_tooltip(checkbox, option_hint)
                                controls[option_key] = checkbox
            else:
                with ui.element("div").classes("audion-checkbox-grid"):
                    for option_key, option_text, option_hint in checkbox_option_items(field):
                        checkbox = ui.checkbox(
                            option_text,
                            value=option_key in selected,
                            on_change=lambda _event: sync_checkboxes(),
                        ).props("dense").classes("audion-grid-checkbox")
                        soft_tooltip(checkbox, option_hint)
                        controls[option_key] = checkbox
            if hint:
                ui.label(hint).classes("audion-field-hint")
            sync_checkboxes()
            return

        if kind in {"path", "file", "folder"}:
            picker_kind = "folder" if kind in {"folder", "path"} else "file"
            with ui.row().classes("audion-path-field w-full items-start gap-2"):
                input_control = ui.input(
                    label=label,
                    value=str(value) if value is not None else "",
                    placeholder=str(field.get("placeholder", "")),
                    on_change=lambda event, item_key=key: set_field_value(item_key, event.value),
                ).props("dense outlined").classes("flex-1")
                soft_tooltip(input_control, hint)
                picker_button = ui.button(
                    tr("browse"),
                    on_click=path_picker_click_handler(field, key, picker_kind),
                ).props("dense flat no-wrap").classes("audion-action audion-picker-button rounded-lg")
                soft_tooltip(picker_button, hint)
            if hint:
                ui.label(hint).classes("audion-field-hint")
            return

        input_control = ui.input(
            label=label,
            value=str(value) if value is not None else "",
            placeholder=str(field.get("placeholder", "")),
            on_change=lambda event, item_key=key: set_field_value(item_key, event.value),
        ).props("dense outlined").classes("w-full")
        soft_tooltip(input_control, hint)
        if hint:
            ui.label(hint).classes("audion-field-hint")


def operation_from_pending_command(node: CommandNode) -> Operation:
    parameters = dict(node.parameters)
    values = state.setdefault("field_values", {})
    for field in node.fields:
        key = field_id(field)
        if not key:
            continue
        if is_info_badge_field(field):
            continue
        kind = str(field.get("type", field.get("kind", "text"))).lower()
        if kind in {"smb_login_cache", "smb-login-cache"}:
            login = smb_login_state(field)
            computer, user = smb_effective_login(login)
            if computer and user:
                login["record_key"] = upsert_smb_login_record(computer, user)
                login["computer"] = computer
                login["user"] = user
                login["computer_manual"] = ""
                login["user_manual"] = ""
                login["cleared"] = ""
                set_field_value(key, login)
            parameters[key] = login
            parameters["smb_computer"] = computer
            parameters["smb_user"] = user
            continue
        if is_workbench_route_field(field):
            parameters[key] = workbench_value_for_field(field)
        else:
            parameters[key] = values.get(key, field_default(field))
    return node.to_operation(parameters)


def validate_pending_fields(node: CommandNode) -> bool:
    values = state.setdefault("field_values", {})
    for field in command_visible_fields(node.fields):
        kind = str(field.get("type", field.get("kind", "text"))).lower()
        if kind in {"smb_login_cache", "smb-login-cache"}:
            computer, user = smb_effective_login(smb_login_state(field))
            if not computer or not user:
                safe_notify("SMB: заполните имя компьютера и пользователя.", "warning")
                return False
            continue
        if not is_checkbox_group(field):
            continue
        min_selected = int(field.get("min_selected", 0) or 0)
        if min_selected <= 0:
            continue
        key = field_id(field)
        selected = values.get(key, field_default(field))
        if not isinstance(selected, list) or len(selected) < min_selected:
            safe_notify(tr("select_required", field=field_label(field)), "warning")
            return False
    return True


async def run_pending_command(node: CommandNode) -> None:
    if validate_pending_fields(node):
        await start_operation(operation_from_pending_command(node))


def run_pending_click_handler(node: CommandNode):
    async def handler() -> None:
        await run_pending_command(node)

    return handler


def field_signature(fields: tuple[dict[str, Any], ...]) -> tuple[str, ...]:
    return tuple(field_id(field) for field in fields if field_id(field))


def has_only_leaf_children(children: list[CommandNode]) -> bool:
    return bool(children) and all(not child.children for child in children)


def node_ui_layout(node: CommandNode | None) -> str:
    return str(getattr(node, "ui_layout", "") or "").strip().lower()


def should_render_command_switcher(node: CommandNode | None) -> bool:
    return node_ui_layout(node) in {"switcher", "action_switcher", "inline_switcher"}


def command_switcher_key(parent: CommandNode) -> str:
    path = [str(item) for item in state.get("command_path", []) if str(item)]
    if path and path[-1] == parent.id:
        return "/".join(path)
    return parent.id


def is_direct_run_node(node: CommandNode) -> bool:
    return not node.children and not command_visible_fields(node.fields)


def is_direct_switcher_action(node: CommandNode) -> bool:
    return is_direct_run_node(node)


def selected_switcher_node(parent: CommandNode, nodes: list[CommandNode]) -> CommandNode | None:
    if not nodes:
        return None
    panel_nodes = [node for node in nodes if not is_direct_switcher_action(node)]
    if not panel_nodes:
        panel_nodes = nodes
    switchers = state.setdefault("command_switchers", {})
    key = command_switcher_key(parent)
    selected_id = str(switchers.get(key) or "")
    selected = next((node for node in panel_nodes if node.id == selected_id), None)
    if selected is None:
        selected = panel_nodes[0]
        switchers[key] = selected.id
    return selected


def switcher_select_handler(parent: CommandNode, node: CommandNode):
    async def handler() -> None:
        state["pending_command"] = None
        if is_direct_switcher_action(node):
            await start_operation(node.to_operation(dict(node.parameters)))
            return
        state.setdefault("command_switchers", {})[command_switcher_key(parent)] = node.id
        command_tree.refresh()

    return handler


def common_inline_fields(children: list[CommandNode]) -> tuple[dict[str, Any], ...]:
    if not has_only_leaf_children(children):
        return ()
    first = tuple(command_visible_fields(children[0].fields))
    if not first:
        return ()
    result: list[dict[str, Any]] = []
    for index, field in enumerate(first):
        key = field_id(field)
        if not key:
            break
        if all(
            index < len(command_visible_fields(child.fields))
            and field_id(command_visible_fields(child.fields)[index]) == key
            for child in children
        ):
            result.append(field)
            continue
        break
    return tuple(result)


def is_dangerous_node(node: CommandNode) -> bool:
    return str(node.kind).lower() == "dangerous"


def node_action_group_label(node: CommandNode) -> str:
    if settings.language == "ru" and getattr(node, "action_group_ru", ""):
        return str(getattr(node, "action_group_ru", ""))
    return str(getattr(node, "action_group", "") or "")


def node_risk_tone(node: CommandNode) -> str:
    risk = str(getattr(node, "risk_level", "") or "").strip().lower()
    if risk in {"destructive", "secret_export"}:
        return "danger"
    if risk in {"project_write", "user_write", "system_change"}:
        return "medium"
    if risk == "readonly":
        return "friendly"
    if is_dangerous_node(node):
        return "danger"
    if str(getattr(node, "kind", "") or "").strip().lower() == "safe":
        return "friendly"
    return "neutral"


def node_action_group_tone(node: CommandNode) -> str:
    explicit = str(getattr(node, "action_group_tone", "") or "").strip().lower()
    aliases = {
        "none": "neutral",
        "neutral": "neutral",
        "pipeline": "neutral",
        "safe": "friendly",
        "success": "friendly",
        "friendly": "friendly",
        "info": "medium",
        "moderate": "medium",
        "medium": "medium",
        "warning": "danger",
        "danger": "danger",
        "dangerous": "danger",
        "destructive": "danger",
    }
    if explicit in aliases:
        return aliases[explicit]
    tone = node_risk_tone(node)
    return "friendly" if tone == "neutral" else tone


def node_action_tone(node: CommandNode) -> str:
    explicit = str(getattr(node, "action_tone", "") or "").strip().lower()
    aliases = {
        "none": "neutral",
        "neutral": "neutral",
        "safe": "friendly",
        "soft": "friendly",
        "status": "friendly",
        "restore": "friendly",
        "success": "friendly",
        "friendly": "friendly",
        "info": "medium",
        "normal": "medium",
        "moderate": "medium",
        "medium": "medium",
        "warning": "danger",
        "strong": "danger",
        "danger": "danger",
        "dangerous": "danger",
        "destructive": "danger",
        "sensitive": "danger",
    }
    if explicit in aliases:
        return aliases[explicit]
    return node_risk_tone(node)


def strictest_node_group_tone(nodes: list[CommandNode]) -> str:
    rank = {"neutral": 0, "friendly": 1, "medium": 2, "danger": 3}
    result = "neutral"
    for node in nodes:
        tone = node_action_group_tone(node)
        if rank.get(tone, 1) > rank[result]:
            result = tone
    return result


def command_node_action_groups(nodes: list[CommandNode]) -> list[tuple[str, str, list[CommandNode]]]:
    groups: list[tuple[str, str, list[CommandNode]]] = []
    index_by_label: dict[str, int] = {}
    for node in nodes:
        label = node_action_group_label(node)
        if not label:
            label = tr("actions")
        key = label.casefold()
        if key not in index_by_label:
            index_by_label[key] = len(groups)
            groups.append((label, node_action_group_tone(node), [node]))
            continue
        group_index = index_by_label[key]
        current_label, _current_tone, group_nodes = groups[group_index]
        group_nodes.append(node)
        groups[group_index] = (current_label, strictest_node_group_tone(group_nodes), group_nodes)
    return groups


def operation_row_classes(node: CommandNode, *, direct_launch: bool | None = None) -> str:
    classes = ["audion-operation-row"]
    if direct_launch is None:
        direct_launch = is_direct_run_node(node)
    if node.children:
        classes.append("audion-operation-row-branch")
    else:
        classes.append("audion-operation-row-leaf")
    if command_visible_fields(node.fields):
        classes.append("audion-operation-row-form")
    if direct_launch:
        classes.append("audion-operation-row-direct")
    if is_dangerous_node(node):
        classes.append("audion-operation-row-dangerous")
    return " ".join(classes)


def action_button_classes(node: CommandNode, *, direct_launch: bool | None = None) -> str:
    if direct_launch is None:
        direct_launch = is_direct_run_node(node)
    classes = ["audion-action", "audion-operation-button", "rounded-lg"]
    if not node.children:
        action_tone = node_action_tone(node)
        if action_tone != "neutral":
            classes.append(f"audion-operation-button-tone-{action_tone}")
    if direct_launch:
        classes.append("audion-operation-button-direct")
        if is_dangerous_node(node):
            classes.append("audion-operation-button-direct-dangerous")
    return " ".join(classes)


def command_run_button_classes(node: CommandNode) -> str:
    classes = ["audion-action", "audion-command-run-button", "rounded-lg"]
    if node.id.startswith("browser_bookmarks_"):
        classes.append("audion-browser-run-button")
    action_tone = node_action_tone(node)
    if action_tone != "neutral":
        classes.append(f"audion-operation-button-tone-{action_tone}")
    return " ".join(classes)


def operation_description_classes(node: CommandNode, extra: str = "") -> str:
    classes = "audion-operation-description"
    if extra:
        classes += f" {extra}"
    return classes


def operation_meta_lines(node: CommandNode, *, can_run_from_shared_fields: bool = False) -> list[str]:
    lines: list[str] = []
    risk_text = risk_level_text(getattr(node, "risk_level", ""))
    if risk_text:
        lines.append(risk_text)
    if is_dangerous_node(node):
        if not risk_text:
            lines.append(tr("command_meta_confirm"))
    elif command_visible_fields(node.fields) and not can_run_from_shared_fields:
        lines.append(tr("command_meta_opens_form"))
    return lines


def render_operation_copy(
    node: CommandNode,
    *,
    can_run_from_shared_fields: bool = False,
    show_title: bool = False,
    fallback_description: str = "",
) -> None:
    description = node.display_description(settings.language) or fallback_description
    meta_lines = operation_meta_lines(node, can_run_from_shared_fields=can_run_from_shared_fields)
    tooltip = description_tooltip_text(description, meta_lines)
    with ui.element("div").classes("audion-operation-copy"):
        if show_title:
            title_label = ui.label(node.display_title(settings.language)).classes("audion-operation-copy-title")
            if tooltip:
                soft_tooltip(title_label, tooltip)
        if description:
            description_label = ui.label(compact_visible_description(description)).classes(operation_description_classes(node, "audion-operation-description-compact"))
            if tooltip:
                soft_tooltip(description_label, tooltip)
        for line in meta_lines:
            ui.label(line).classes("audion-operation-meta")


def render_inline_child_action(node: CommandNode, *, shared_fields: tuple[dict[str, Any], ...] = ()) -> None:
    shared_signature = field_signature(shared_fields)
    node_signature = field_signature(tuple(command_visible_fields(node.fields)))
    can_run_from_shared_fields = bool(shared_signature) and node_signature == shared_signature
    handler = run_pending_click_handler(node) if can_run_from_shared_fields else command_click_handler(node)
    direct_launch = can_run_from_shared_fields or is_direct_run_node(node)

    with ui.element("div").classes(operation_row_classes(node, direct_launch=direct_launch)):
        button = ui.button(
            node.display_title(settings.language),
            on_click=handler,
        ).props("dense flat").classes(action_button_classes(node, direct_launch=direct_launch))
        tooltip = description_tooltip_text(
            node.display_description(settings.language),
            operation_meta_lines(node, can_run_from_shared_fields=can_run_from_shared_fields),
        )
        if tooltip:
            soft_tooltip(button, tooltip)
        render_operation_copy(node, can_run_from_shared_fields=can_run_from_shared_fields)


def render_leaf_action_group(nodes: list[CommandNode]) -> None:
    inline_fields = common_inline_fields(nodes)
    primary_fields, advanced_fields = split_primary_advanced_fields(inline_fields)
    if primary_fields:
        ui.label(tr("parameters")).classes("text-sm font-semibold text-gray-300")
        render_field_grid(primary_fields)
    groups = command_node_action_groups(nodes)
    grouped = any(node_action_group_label(node) for node in nodes)
    if not grouped:
        with ui.element("div").classes("audion-action-group-grid"):
            with ui.element("section").classes("audion-action-group audion-action-group-neutral"):
                ui.label(tr("actions")).classes("audion-action-group-title")
                with ui.column().classes("audion-action-group-list w-full gap-0"):
                    for node in nodes:
                        render_inline_child_action(node, shared_fields=inline_fields)
    else:
        with ui.element("div").classes("audion-action-group-grid"):
            for label, tone, group_nodes in groups:
                with ui.element("section").classes(f"audion-action-group audion-action-group-{tone}"):
                    ui.label(label).classes("audion-action-group-title")
                    with ui.column().classes("audion-action-group-list w-full gap-0"):
                        for node in group_nodes:
                            render_inline_child_action(node, shared_fields=inline_fields)
    if advanced_fields:
        render_advanced_fields(advanced_fields)


def render_command_node_group(nodes: list[CommandNode]) -> None:
    grouped = any(node_action_group_label(node) for node in nodes)
    if not grouped:
        with ui.element("div").classes("audion-action-group-grid"):
            with ui.element("section").classes("audion-action-group audion-action-group-neutral"):
                ui.label(tr("actions")).classes("audion-action-group-title")
                with ui.column().classes("audion-action-group-list w-full gap-0"):
                    for node in nodes:
                        command_node_button(node)
        return

    with ui.element("div").classes("audion-action-group-grid"):
        for label, tone, group_nodes in command_node_action_groups(nodes):
            with ui.element("section").classes(f"audion-action-group audion-action-group-{tone}"):
                ui.label(label).classes("audion-action-group-title")
                with ui.column().classes("audion-action-group-list w-full gap-0"):
                    for node in group_nodes:
                        command_node_button(node)


def render_single_switcher_leaf(node: CommandNode) -> None:
    visible_fields = command_visible_fields(node.fields)
    if visible_fields:
        primary_fields, advanced_fields = split_primary_advanced_fields(tuple(visible_fields))
        if primary_fields:
            ui.label(tr("parameters")).classes("text-sm font-semibold text-gray-300")
            render_field_grid(primary_fields)
        # Run lives in the nav row next to Back; see command_nav_row().
        if advanced_fields:
            render_advanced_fields(advanced_fields)
        return

    with ui.column().classes("audion-command-list w-full gap-0"):
        render_inline_child_action(node)


def command_switcher_tooltip(node: CommandNode) -> str:
    lines: list[str] = []
    description = node.display_description(settings.language)
    if description:
        lines.append(description)
    for line in operation_meta_lines(node):
        if line and line not in lines:
            lines.append(line)
    return "\n".join(lines)


def tooltip_title_value(text: str) -> str:
    lines = [line.strip() for line in str(text or "").splitlines() if line.strip()]
    return html.escape(" | ".join(lines), quote=True)


def soft_tooltip(element: Any, text: str) -> Any:
    lines = [line.strip() for line in str(text or "").splitlines() if line.strip()]
    if not lines:
        return element
    tooltip_text = "\n".join(lines)
    element.props["aria-description"] = " | ".join(lines)
    tooltip = Tooltip(tooltip_text)
    tooltip.props["target"] = f"#{element.html_id}"
    tooltip.props["delay"] = TOOLTIP_SHOW_DELAY_MS
    tooltip.props["hide-delay"] = TOOLTIP_HIDE_DELAY_MS
    tooltip.classes("audion-tooltip")
    return element


def render_command_switcher(parent: CommandNode, nodes: list[CommandNode]) -> None:
    selected = selected_switcher_node(parent, nodes)
    if selected is None:
        ui.label(tr("empty_section")).classes("audion-empty-section")
        return

    with ui.row().classes("audion-command-switcher w-full"):
        for node in nodes:
            classes = "audion-action audion-switcher-button rounded-lg"
            if is_direct_switcher_action(node):
                classes += " audion-switcher-button-direct"
            elif node.id == selected.id:
                classes += " audion-switcher-button-active"
            button = ui.button(
                node.display_title(settings.language),
                on_click=switcher_select_handler(parent, node),
            ).props("dense flat no-wrap").classes(classes)
            tooltip = command_switcher_tooltip(node)
            if tooltip:
                soft_tooltip(button, tooltip)

    with ui.element("div").classes("audion-switcher-panel"):
        children = list(selected.children)
        if children:
            if has_only_leaf_children(children):
                render_leaf_action_group(children)
            else:
                render_command_node_group(children)
            return

        render_single_switcher_leaf(selected)


def browser_bookmarks_route_title(role: str) -> str:
    if role == "target":
        return "TARGET" if settings.language == "ru" else "TARGET"
    return "SOURCE" if settings.language == "ru" else "SOURCE"


def browser_bookmarks_route_hint(role: str) -> str:
    if role == "target":
        return (
            "TARGET используется для Export. UNC-синтаксис: \\\\SERVER\\Share\\Folder."
            if settings.language == "ru"
            else "TARGET is used for Export. UNC syntax: \\\\SERVER\\Share\\Folder."
        )
    return (
        "SOURCE используется для Import и Status. UNC-синтаксис: \\\\SERVER\\Share\\Folder."
        if settings.language == "ru"
        else "SOURCE is used for Import and Status. UNC syntax: \\\\SERVER\\Share\\Folder."
    )


def browser_bookmarks_current_route(role: str) -> Path:
    return current_target_path() if role == "target" else current_source_path()


def browser_bookmarks_unc_state_key(role: str, part: str) -> str:
    role_key = "target" if role == "target" else "source"
    return f"browser_bookmarks_unc_{role_key}_{part}"


def sync_browser_bookmarks_route_state(role: str) -> None:
    current_text = str(browser_bookmarks_current_route(role))
    current_key = browser_bookmarks_unc_state_key(role, "current")
    if str(state.get(current_key) or "") == current_text:
        return
    server, share, subpath = split_unc_path(current_text)
    state[browser_bookmarks_unc_state_key(role, "server")] = server
    state[browser_bookmarks_unc_state_key(role, "share")] = share
    state[browser_bookmarks_unc_state_key(role, "subpath")] = subpath
    state[current_key] = current_text


def split_unc_path(path_value: Any) -> tuple[str, str, str]:
    text = str(path_value or "").strip().replace("/", "\\")
    if not text.startswith("\\\\"):
        return "", "", ""
    parts = [part for part in text.lstrip("\\").split("\\") if part]
    if not parts:
        return "", "", ""
    server = parts[0]
    share = parts[1] if len(parts) > 1 else ""
    subpath = "\\".join(parts[2:]) if len(parts) > 2 else ""
    return server, share, subpath


def compose_unc_path(server: Any, share: Any, subpath: Any = "") -> str:
    server_text = str(server or "").strip().strip("\\/")
    share_text = str(share or "").strip().replace("/", "\\").strip("\\")
    subpath_text = str(subpath or "").strip().replace("/", "\\").strip("\\")
    if not server_text:
        raise RuntimeError("Укажи имя сервера/компьютера." if settings.language == "ru" else "Enter the server/computer name.")
    if not share_text:
        raise RuntimeError("Укажи имя общей папки Share." if settings.language == "ru" else "Enter the shared folder name.")
    return f"\\\\{server_text}\\{share_text}" + (f"\\{subpath_text}" if subpath_text else "")


def browser_bookmarks_unc_value(role: str, part: str) -> str:
    key = browser_bookmarks_unc_state_key(role, part)
    value = str(state.get(key) or "").strip()
    if value:
        return value
    server, share, subpath = split_unc_path(browser_bookmarks_current_route(role))
    state[browser_bookmarks_unc_state_key(role, "server")] = server
    state[browser_bookmarks_unc_state_key(role, "share")] = share
    state[browser_bookmarks_unc_state_key(role, "subpath")] = subpath
    if part == "server":
        return server
    if part == "share":
        return share
    return subpath


def browser_bookmarks_unc_change_handler(role: str, part: str):
    def handler(event: Any) -> None:
        state[browser_bookmarks_unc_state_key(role, part)] = str(getattr(event, "value", "") or "").strip()

    return handler


def browser_bookmarks_apply_unc_handler(role: str):
    async def handler() -> None:
        try:
            path_value = compose_unc_path(
                state.get(browser_bookmarks_unc_state_key(role, "server")),
                state.get(browser_bookmarks_unc_state_key(role, "share")),
                state.get(browser_bookmarks_unc_state_key(role, "subpath")),
            )
            save_workspace_path("destination" if role == "target" else "source", path_value)
            await run.io_bound(remember_path, role, path_value)
            add_log(f"{browser_bookmarks_route_title(role)} -> {path_value}")
            safe_notify(f"{browser_bookmarks_route_title(role)}: {path_value}", "positive")
            reload_ui()
        except Exception as exc:
            safe_notify(str(exc), "warning")

    return handler


def browser_bookmarks_reload_unc_from_current_handler(role: str):
    def handler() -> None:
        server, share, subpath = split_unc_path(browser_bookmarks_current_route(role))
        state[browser_bookmarks_unc_state_key(role, "server")] = server
        state[browser_bookmarks_unc_state_key(role, "share")] = share
        state[browser_bookmarks_unc_state_key(role, "subpath")] = subpath
        state[browser_bookmarks_unc_state_key(role, "current")] = str(browser_bookmarks_current_route(role))
        command_tree.refresh()

    return handler


def render_browser_bookmarks_route_card(role: str) -> None:
    sync_browser_bookmarks_route_state(role)
    title = browser_bookmarks_route_title(role)
    current_path = browser_bookmarks_current_route(role)
    hint = browser_bookmarks_route_hint(role)
    server_value = browser_bookmarks_unc_value(role, "server")
    share_value = browser_bookmarks_unc_value(role, "share")
    subpath_value = browser_bookmarks_unc_value(role, "subpath")

    with ui.element("section").classes("audion-browser-route-card"):
        with ui.row().classes("audion-browser-route-head w-full items-center gap-2"):
            title_label = ui.label(title).classes("audion-section-title")
            soft_tooltip(title_label, hint)
            ui.space()
            open_button = ui.button(icon="folder_open", on_click=workspace_open_click_handler(role)).props("dense flat round").classes("audion-action audion-folder-icon-button")
            soft_tooltip(open_button, "Открыть текущий путь." if settings.language == "ru" else "Open the current path.")
            pick_button = ui.button(icon="drive_file_move", on_click=workspace_pick_click_handler(role)).props("dense flat round").classes("audion-action audion-folder-icon-button")
            soft_tooltip(pick_button, "Выбрать локальную или сетевую папку через диалог." if settings.language == "ru" else "Pick a local or network folder with a dialog.")
            reload_button = ui.button(icon="sync", on_click=browser_bookmarks_reload_unc_from_current_handler(role)).props("dense flat round").classes("audion-action audion-folder-icon-button")
            soft_tooltip(reload_button, "Разобрать текущий UNC-путь обратно в поля." if settings.language == "ru" else "Parse the current UNC path back into the fields.")
        route_input = ui.input(
            label=f"Текущий Workbench {title}" if settings.language == "ru" else f"Current Workbench {title}",
            value=str(current_path),
        ).props("dense outlined readonly").classes("audion-browser-route-path")
        soft_tooltip(route_input, hint)
        with ui.row().classes("audion-browser-unc-row w-full items-start gap-1"):
            ui.label(r"\\").classes("audion-unc-static")
            server_input = ui.input(
                label="Имя сервера/компьютера" if settings.language == "ru" else "Server/computer",
                value=server_value,
                placeholder="SERVER",
                on_change=browser_bookmarks_unc_change_handler(role, "server"),
            ).props("dense outlined").classes("audion-unc-server")
            soft_tooltip(server_input, "Например: NAS, OFFICE-PC, 192.168.1.10." if settings.language == "ru" else "Example: NAS, OFFICE-PC, 192.168.1.10.")
            ui.label("\\").classes("audion-unc-static")
            share_input = ui.input(
                label="Share" if settings.language == "ru" else "Share",
                value=share_value,
                placeholder="Share",
                on_change=browser_bookmarks_unc_change_handler(role, "share"),
            ).props("dense outlined").classes("audion-unc-share")
            soft_tooltip(share_input, "Имя общей папки, опубликованной на сервере. Например: Share или Backups." if settings.language == "ru" else "Name of the shared folder published on the server. Example: Share or Backups.")
            ui.label("\\").classes("audion-unc-static")
            subpath_input = ui.input(
                label="Папка внутри Share" if settings.language == "ru" else "Folder inside Share",
                value=subpath_value,
                placeholder=r"BrowserBackups",
                on_change=browser_bookmarks_unc_change_handler(role, "subpath"),
            ).props("dense outlined").classes("audion-unc-subpath")
            soft_tooltip(subpath_input, r"Необязательно. Например: BrowserBackups или Tools\Bookmarks." if settings.language == "ru" else r"Optional. Example: BrowserBackups or Tools\Bookmarks.")
            apply_button = ui.button(title, on_click=browser_bookmarks_apply_unc_handler(role)).props("dense flat no-wrap").classes("audion-action audion-route-apply-button rounded-lg")
            soft_tooltip(apply_button, hint)


def render_browser_bookmarks_routes(action: str) -> None:
    if action == "browser_bookmarks_transfer_master":
        note = ui.label(
            "Transfer не использует SOURCE/TARGET: перенос идёт через локальный backup\\browser_bookmarks."
            if settings.language == "ru"
            else "Transfer does not use SOURCE/TARGET: it routes through local backup\\browser_bookmarks."
        ).classes("audion-field-hint")
        soft_tooltip(note, "Сетевой путь нужен только для Import/Export." if settings.language == "ru" else "Network paths are only needed for Import/Export.")
        return

    roles = ["source", "target"]
    if action == "browser_bookmarks_import_master":
        roles = ["source"]
    elif action == "browser_bookmarks_export_master":
        roles = ["target"]

    header = ui.label("Маршруты backup" if settings.language == "ru" else "Backup routes").classes("audion-section-title")
    soft_tooltip(header, "SOURCE/TARGET здесь сохраняют общие Workbench-пути, но с подсказкой UNC-синтаксиса." if settings.language == "ru" else "SOURCE/TARGET here save the shared Workbench routes, with UNC syntax help.")
    with ui.element("div").classes("audion-browser-route-grid"):
        for role in roles:
            render_browser_bookmarks_route_card(role)


BROWSER_BOOKMARKS_ACTIONS = (
    "browser_bookmarks_status",
    "browser_bookmarks_import_master",
    "browser_bookmarks_export_master",
    "browser_bookmarks_transfer_master",
)


def browser_bookmarks_action_label(node_id: str) -> str:
    labels = {
        "browser_bookmarks_status": ("Status", "Статус"),
        "browser_bookmarks_import_master": ("Import", "Импорт"),
        "browser_bookmarks_export_master": ("Export", "Экспорт"),
        "browser_bookmarks_transfer_master": ("Transfer", "Перенос"),
    }
    en, ru = labels.get(node_id, (node_id, node_id))
    return ru if settings.language == "ru" else en


def browser_bookmarks_action_hint(node_id: str) -> str:
    hints = {
        "browser_bookmarks_status": (
            "Read status for one or several selected Chromium profiles.",
            "Показать статус одного или нескольких выбранных Chromium-профилей.",
        ),
        "browser_bookmarks_import_master": (
            "Import the Workbench SOURCE master into one selected browser. Favicons cleanup is always done first.",
            "Импортировать эталон из Workbench SOURCE в один выбранный браузер. Очистка Favicons всегда выполняется перед импортом.",
        ),
        "browser_bookmarks_export_master": (
            "Export master backups from selected browsers into Workbench TARGET.",
            "Экспортировать эталонные backup-папки выбранных браузеров в Workbench TARGET.",
        ),
        "browser_bookmarks_transfer_master": (
            "Transfer one source browser into selected target browsers through a project-local backup.",
            "Перенести один браузер-источник в выбранные браузеры-приёмники через project-local backup.",
        ),
    }
    en, ru = hints.get(node_id, ("", ""))
    return ru if settings.language == "ru" else en


def browser_bookmarks_action_tone_class(node_id: str) -> str:
    return "audion-browser-toggle-process"


def browser_bookmarks_selector_hint(action: str) -> str:
    hints = {
        "browser_bookmarks_status": (
            "Select one or several browsers for a read-only status check.",
            "Выбери один или несколько браузеров для read-only проверки статуса.",
        ),
        "browser_bookmarks_import_master": (
            "Select one or several system browsers. Portable mode uses one exact profile selected by radio.",
            "Выбери один или несколько системных браузеров. Portable-режим использует один точный профиль с выбором radio.",
        ),
        "browser_bookmarks_export_master": (
            "Select one or several source browsers to export into Workbench TARGET.",
            "Выбери один или несколько браузеров-источников для экспорта в Workbench TARGET.",
        ),
        "browser_bookmarks_transfer_master": (
            "Select one source browser and one or several different target browsers.",
            "Выбери один браузер-источник и один или несколько других браузеров-приёмников.",
        ),
    }
    en, ru = hints.get(action, ("", ""))
    return ru if settings.language == "ru" else en


def browser_bookmarks_browser_hint(action: str, label: str) -> str:
    hints = {
        "browser_bookmarks_status": (
            f"Include {label} in the read-only status report.",
            f"Включить {label} в read-only отчёт Status.",
        ),
        "browser_bookmarks_import_master": (
            f"Use {label} as the one target browser for import.",
            f"Использовать {label} как единственный браузер назначения для import.",
        ),
        "browser_bookmarks_export_master": (
            f"Export {label} native Bookmarks/Favicons files into Workbench TARGET.",
            f"Экспортировать штатные Bookmarks/Favicons файлы {label} в Workbench TARGET.",
        ),
        "browser_bookmarks_transfer_master": (
            f"Receive native Bookmarks/Favicons files from the selected source into {label}.",
            f"Загрузить штатные Bookmarks/Favicons файлы выбранного источника в {label}.",
        ),
    }
    en, ru = hints.get(action, ("", ""))
    return ru if settings.language == "ru" else en


def browser_bookmarks_child(nodes: list[CommandNode], node_id: str) -> CommandNode | None:
    return next((node for node in nodes if node.id == node_id), None)


def browser_bookmarks_field(parent: CommandNode, key: str) -> dict[str, Any] | None:
    return next((field for field in parent.fields if field_id(field) == key), None)


def browser_bookmarks_options(parent: CommandNode) -> dict[Any, str]:
    field = browser_bookmarks_field(parent, "browser_profile")
    if not field:
        return {"chrome": "Google Chrome"}
    options = select_options(field)
    if isinstance(options, dict) and options:
        return options
    return {"chrome": "Google Chrome"}


def normalize_browser_bookmarks_state(parent: CommandNode) -> tuple[str, dict[Any, str], list[Any], Any]:
    options = browser_bookmarks_options(parent)
    option_values = list(options.keys())
    fallback = "chrome" if "chrome" in option_values else option_values[0]
    action = str(state.get("browser_bookmarks_action") or "browser_bookmarks_status")
    if action in {"status", "browser_bookmarks_status"}:
        action = "browser_bookmarks_status"
    elif action in {"import", "browser_bookmarks_import_master"}:
        action = "browser_bookmarks_import_master"
    elif action in {"export", "browser_bookmarks_export_master"}:
        action = "browser_bookmarks_export_master"
    elif action in {"transfer", "browser_bookmarks_transfer_master"}:
        action = "browser_bookmarks_transfer_master"
    else:
        action = "browser_bookmarks_status"
    state["browser_bookmarks_action"] = action

    selected_raw = state.get("browser_bookmarks_selected")
    selected = selected_raw if isinstance(selected_raw, list) else []
    selected = [value for value in selected if value in option_values]
    single = state.get("browser_bookmarks_single")
    if single not in option_values:
        single = selected[0] if selected else fallback

    if action == "browser_bookmarks_import_master" and str(state.get("browser_bookmarks_location_mode") or "system") == "portable":
        selected = [single]
    elif action == "browser_bookmarks_transfer_master":
        selected = [value for value in selected if value != single]
    elif not selected:
        selected = [single if single in option_values else fallback]
    state["browser_bookmarks_selected"] = selected
    state["browser_bookmarks_single"] = single
    return action, options, selected, single


def set_browser_bookmarks_action(parent: CommandNode, action: str) -> None:
    previous = str(state.get("browser_bookmarks_action") or "")
    state["browser_bookmarks_action"] = action
    if action != previous:
        state["browser_bookmarks_selected"] = ["chrome"]
        state["browser_bookmarks_single"] = "chrome"
    normalize_browser_bookmarks_state(parent)
    command_tree.refresh()


def browser_bookmarks_action_click_handler(parent: CommandNode, action: str):
    def handler() -> None:
        set_browser_bookmarks_action(parent, action)

    return handler


def browser_bookmarks_checkbox_handler(parent: CommandNode, browser_key: Any, checked: bool):
    def handler(_event: Any = None) -> None:
        action, _options, selected, _single = normalize_browser_bookmarks_state(parent)
        next_selected = list(selected)
        if checked:
            if browser_key not in next_selected:
                next_selected.append(browser_key)
        else:
            next_selected = [value for value in next_selected if value != browser_key]
            if not next_selected:
                safe_notify("Выберите хотя бы один браузер." if settings.language == "ru" else "Select at least one browser.", "warning")
                command_tree.refresh()
                return
        state["browser_bookmarks_selected"] = next_selected
        if next_selected and action != "browser_bookmarks_transfer_master":
            state["browser_bookmarks_single"] = next_selected[0]
        command_tree.refresh()

    return handler


def browser_bookmarks_radio_handler(parent: CommandNode):
    def handler(event: Any) -> None:
        value = getattr(event, "value", None)
        if value is None:
            return
        state["browser_bookmarks_single"] = value
        normalize_browser_bookmarks_state(parent)
        command_tree.refresh()

    return handler


def browser_bookmarks_fields_for_action(parent: CommandNode, action: str, selected_count: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    keys_by_action = {
        "browser_bookmarks_status": [],
        "browser_bookmarks_import_master": ["backup_version", "close_browser_process"],
        "browser_bookmarks_export_master": ["backup_label", "backup_version", "close_browser_process"],
        "browser_bookmarks_transfer_master": ["backup_label", "backup_version", "close_browser_process"],
    }
    primary: list[dict[str, Any]] = []
    advanced: list[dict[str, Any]] = []
    for field in parent.fields:
        key = field_id(field)
        if key in {"browser_profile", "backup_source_path", "backup_target_path"}:
            continue
        if key == "browser_profile_path":
            continue
        if key not in keys_by_action.get(action, []):
            continue
        (advanced if is_advanced_field(field) else primary).append(field)
    return primary, advanced


def browser_bookmarks_operation(parent: CommandNode, node: CommandNode, selected: list[Any]) -> Operation:
    selected_values = [str(value) for value in selected if str(value)]
    if not selected_values:
        raise RuntimeError("No browser selected.")
    parameters = dict(node.parameters)
    values = state.setdefault("field_values", {})
    for field in parent.fields:
        key = field_id(field)
        if not key or key == "browser_profile":
            continue
        if key == "browser_profile_path" and len(selected_values) != 1:
            continue
        if is_info_badge_field(field):
            continue
        if is_workbench_route_field(field):
            parameters[key] = workbench_value_for_field(field)
        else:
            parameters[key] = values.get(key, field_default(field))
    parameters["browser_profile"] = selected_values[0]
    parameters["browser_profiles"] = selected_values
    parameters["create_rollback_backup"] = bool(state.get("browser_bookmarks_create_rollback", True))
    location_mode = str(state.get("browser_bookmarks_location_mode") or "system")
    parameters["browser_location_mode"] = location_mode
    if location_mode == "portable":
        if len(selected_values) != 1:
            raise RuntimeError("В portable-режиме выберите ровно один браузер.")
        profile_path = str(state.setdefault("field_values", {}).get("browser_profile_path") or "").strip()
        if not profile_path:
            raise RuntimeError("Выберите папку профиля portable-браузера с файлом Bookmarks.")
        parameters["browser_profile_path"] = profile_path
    if node.id == "browser_bookmarks_import_master":
        parameters["clear_favicons_before_import"] = False
        parameters["bookmark_import_kind"] = str(state.get("browser_bookmarks_import_kind") or "html")
        parameters["bookmark_backup_path"] = str(state.get("browser_bookmarks_backup_path") or "")
        parameters["bookmark_html_path"] = str(state.get("browser_bookmarks_html_path") or "")
    if node.id == "browser_bookmarks_transfer_master":
        source = str(state.get("browser_bookmarks_single") or "").strip()
        if not source:
            raise RuntimeError("No source browser selected.")
        if source in selected_values:
            raise RuntimeError("Source browser cannot also be a transfer target.")
        parameters["browser_profile"] = source
        parameters["source_browser_profile"] = source
        parameters["target_browser_profiles"] = selected_values
        parameters["browser_profiles"] = selected_values
        parameters["clear_favicons_before_import"] = True
    return node.to_operation(parameters)


def browser_bookmarks_native_backups() -> list[Path]:
    source = current_source_path()
    if not source.exists() or not source.is_dir():
        return []
    required = ("Bookmarks", "Favicons")
    found: list[Path] = []
    if all((source / name).is_file() for name in required):
        found.append(source)
    found.extend(
        path for path in source.iterdir()
        if path.is_dir() and all((path / name).is_file() for name in required)
    )
    return sorted(set(found), key=lambda path: path.stat().st_mtime, reverse=True)


def browser_bookmarks_import_kind_handler(event: Any) -> None:
    state["browser_bookmarks_import_kind"] = str(getattr(event, "value", "native") or "native")
    command_tree.refresh()


def browser_bookmarks_location_mode_handler(event: Any) -> None:
    state["browser_bookmarks_location_mode"] = str(getattr(event, "value", "system") or "system")
    command_tree.refresh()


def browser_bookmarks_location_mode_click(mode: str):
    def handler() -> None:
        state["browser_bookmarks_location_mode"] = mode
        command_tree.refresh()
    return handler


def browser_bookmarks_import_kind_click(kind: str):
    def handler() -> None:
        state["browser_bookmarks_import_kind"] = kind
        command_tree.refresh()
    return handler


def render_browser_bookmarks_location(parent: CommandNode, selected_count: int) -> None:
    mode = str(state.get("browser_bookmarks_location_mode") or "system")
    title = ui.label("Расположение браузера" if settings.language == "ru" else "Browser location").classes("audion-section-title")
    soft_tooltip(title, "Системный режим находит стандартный профиль автоматически. Portable требует точную папку профиля, а не папку с EXE." if settings.language == "ru" else "System mode detects the standard profile. Portable requires the exact profile folder, not merely the EXE folder.")
    labels = {"system": "СИСТЕМНЫЙ", "portable": "PORTABLE"} if settings.language == "ru" else {"system": "SYSTEM", "portable": "PORTABLE"}
    with ui.element("div").classes("audion-browser-mode-buttons audion-browser-location-mode"):
        for value, label in labels.items():
            classes = "audion-browser-mode-button"
            if value == mode:
                classes += " audion-browser-mode-button-active"
            button = ui.button(label, on_click=browser_bookmarks_location_mode_click(value)).props("dense flat no-wrap").classes(classes)
            soft_tooltip(button, "Штатный профиль установленного браузера." if value == "system" and settings.language == "ru" else "Точная папка профиля portable-браузера." if settings.language == "ru" else "Standard installed browser profile." if value == "system" else "Exact portable browser profile folder.")
    if mode == "portable":
        field = browser_bookmarks_field(parent, "browser_profile_path")
        if field is not None:
            render_field(field)
        if selected_count != 1:
            ui.label("Для portable-профиля запускай операцию по одному браузеру." if settings.language == "ru" else "Run portable profile operations for one browser at a time.").classes("audion-field-hint")


def browser_bookmarks_backup_handler(event: Any) -> None:
    state["browser_bookmarks_backup_path"] = str(getattr(event, "value", "") or "")


def browser_bookmarks_rollback_handler(event: Any) -> None:
    state["browser_bookmarks_create_rollback"] = bool(getattr(event, "value", True))


async def browser_bookmarks_pick_html() -> None:
    try:
        files = await run.io_bound(pick_files, "Выберите HTML-файл закладок", current_source_path())
    except Exception as exc:
        safe_notify(str(exc), "warning")
        return
    if not files:
        return
    selected = files[0]
    if selected.suffix.lower() not in {".html", ".htm"}:
        safe_notify("Нужен файл .html или .htm.", "warning")
        return
    state["browser_bookmarks_html_path"] = str(selected)
    state["browser_bookmarks_import_kind"] = "html"
    command_tree.refresh()


def render_browser_bookmarks_import_source() -> None:
    kind = str(state.get("browser_bookmarks_import_kind") or "html")
    title = ui.label("Источник закладок" if settings.language == "ru" else "Bookmark source").classes("audion-section-title")
    soft_tooltip(title, "HTML-бэкап — основной clean-import Bookmarks и встроенных ICON. Backup профиля программы — аварийный путь восстановления." if settings.language == "ru" else "HTML backup is the primary clean import for Bookmarks and embedded ICON data. Program profile backup is the emergency recovery path.")
    source_modes = {"html": "HTML-БЭКАП", "native": "BACKUP ПРОФИЛЯ"} if settings.language == "ru" else {"html": "HTML BACKUP", "native": "PROFILE BACKUP"}
    with ui.element("div").classes("audion-browser-mode-buttons audion-browser-import-kind"):
        for value, label in source_modes.items():
            classes = "audion-browser-mode-button"
            if value == kind:
                classes += " audion-browser-mode-button-active audion-browser-mode-button-source"
            button = ui.button(label, on_click=browser_bookmarks_import_kind_click(value)).props("dense flat no-wrap").classes(classes)
            soft_tooltip(button, "Основной clean-import Bookmarks и встроенных ICON." if value == "html" and settings.language == "ru" else "Аварийное восстановление из backup профиля." if settings.language == "ru" else "Primary clean import of Bookmarks and embedded ICON data." if value == "html" else "Emergency restore from a profile backup.")
    if kind == "native":
        backups = browser_bookmarks_native_backups()
        options = {str(path): path.name if path != current_source_path() else f"{path.name} (SOURCE)" for path in backups}
        selected = str(state.get("browser_bookmarks_backup_path") or "")
        if selected not in options and backups:
            selected = str(backups[0])
            state["browser_bookmarks_backup_path"] = selected
        if options:
            radio = ui.radio(options=options, value=selected, on_change=browser_bookmarks_backup_handler).props("dense").classes("audion-choice-grid audion-browser-backup-radio")
            soft_tooltip(radio, "Выбери конкретную папку backup. Автоматического скрытого выбора последней папки больше нет." if settings.language == "ru" else "Choose the exact backup folder. The newest folder is no longer selected invisibly.")
        else:
            ui.label("В SOURCE нет папок с файлами Bookmarks + Favicons." if settings.language == "ru" else "SOURCE contains no folders with Bookmarks + Favicons.").classes("audion-field-hint")
    else:
        html_path = str(state.get("browser_bookmarks_html_path") or "")
        if not html_path and current_source_path().is_dir():
            candidates = sorted(
                [*current_source_path().glob("*.html"), *current_source_path().glob("*.htm")],
                key=lambda path: path.stat().st_mtime,
                reverse=True,
            )
            if candidates:
                html_path = str(candidates[0])
                state["browser_bookmarks_html_path"] = html_path
        with ui.row().classes("w-full items-center gap-2"):
            button = ui.button("ВЫБРАТЬ HTML", icon="folder_open", on_click=browser_bookmarks_pick_html).props("dense flat no-wrap").classes("audion-action audion-route-apply-button rounded-lg")
            soft_tooltip(button, "Выбрать экспорт закладок .html/.htm. Перед импортом будет создан локальный rollback backup." if settings.language == "ru" else "Choose a .html/.htm bookmark export. A local rollback backup is created before import.")
            ui.label(html_path or ("Файл не выбран" if settings.language == "ru" else "No file selected")).classes("audion-browser-html-path")


def browser_bookmarks_direct_run_handler(node: CommandNode):
    async def handler() -> None:
        await start_operation(node.to_operation(dict(node.parameters)))

    return handler


def browser_bookmarks_run_handler(parent: CommandNode, node: CommandNode, selected: list[Any]):
    async def handler() -> None:
        try:
            operation = browser_bookmarks_operation(parent, node, selected)
        except Exception as exc:
            safe_notify(str(exc), "warning")
            return
        await start_operation(operation)

    return handler


def render_browser_bookmarks_selector(parent: CommandNode, action: str, options: dict[Any, str], selected: list[Any], single: Any) -> None:
    title = "Браузеры" if settings.language == "ru" else "Browsers"
    if action == "browser_bookmarks_import_master":
        title = "Браузер назначения" if settings.language == "ru" else "Target browser"
    elif action == "browser_bookmarks_export_master":
        title = "Браузеры для экспорта в TARGET" if settings.language == "ru" else "Browsers to export into TARGET"
    elif action == "browser_bookmarks_transfer_master":
        title = "Перенос между браузерами" if settings.language == "ru" else "Browser transfer"
    selector_hint = browser_bookmarks_selector_hint(action)
    title_label = ui.label(title).classes("audion-section-title")
    soft_tooltip(title_label, selector_hint)

    portable_import = action == "browser_bookmarks_import_master" and str(state.get("browser_bookmarks_location_mode") or "system") == "portable"
    if portable_import or action == "browser_bookmarks_transfer_master":
        if action == "browser_bookmarks_transfer_master":
            source_label = "Браузер-источник" if settings.language == "ru" else "Source browser"
            source_hint = "Из этого браузера будет снят промежуточный эталонный backup." if settings.language == "ru" else "The intermediate master backup will be exported from this browser."
            source_title = ui.label(source_label).classes("audion-section-title audion-browser-bookmarks-subtitle")
            soft_tooltip(source_title, source_hint)
        radio = ui.radio(
            options=options,
            value=single,
            on_change=browser_bookmarks_radio_handler(parent),
        ).props("dense").classes("audion-choice-grid audion-browser-bookmarks-radio")
        soft_tooltip(radio, selector_hint if portable_import else source_hint)
        if portable_import:
            with ui.row().classes("w-full items-center gap-2 pt-1"):
                checkbox = ui.checkbox(
                    "Сохранить текущие Favicons" if settings.language == "ru" else "Keep current Favicons",
                    value=True,
                ).props("dense disable").classes("audion-single-checkbox")
                soft_tooltip(checkbox, "HTML не содержит полноценную favicon-базу. Очистка вынесена в отдельную команду с rollback." if settings.language == "ru" else "HTML has no complete favicon database. Cleanup is a separate command with rollback.")
            return

        target_label = "Браузеры-приёмники" if settings.language == "ru" else "Target browsers"
        target_hint = "Источник скрыт из списка приёмников; выбранные браузеры будут перезаписаны через промежуточный backup." if settings.language == "ru" else "The source browser is hidden from targets; selected browsers will be overwritten through the intermediate backup."
        target_title = ui.label(target_label).classes("audion-section-title audion-browser-bookmarks-subtitle")
        soft_tooltip(target_title, target_hint)
        selected_set = set(selected)
        with ui.element("div").classes("audion-checkbox-grid audion-browser-bookmarks-checkboxes"):
            for browser_key, label in options.items():
                if browser_key == single:
                    continue
                checkbox = ui.checkbox(
                    label,
                    value=browser_key in selected_set,
                    on_change=lambda event, key=browser_key: browser_bookmarks_checkbox_handler(parent, key, bool(event.value))(),
                ).props("dense").classes("audion-grid-checkbox")
                soft_tooltip(checkbox, browser_bookmarks_browser_hint(action, str(label)))
        with ui.row().classes("w-full items-center gap-2 pt-1"):
            checkbox = ui.checkbox(
                "Выгрузить во временный backup и загрузить в приёмники" if settings.language == "ru" else "Export to intermediate backup and import into targets",
                value=True,
            ).props("dense disable").classes("audion-single-checkbox")
            soft_tooltip(checkbox, "Служебный двухэтапный маршрут: source -> backup -> targets. Перед импортом у приёмников очищается Favicons cache." if settings.language == "ru" else "Service two-stage route: source -> backup -> targets. Target Favicons cache is cleared before import.")
        return

    selected_set = set(selected)
    with ui.element("div").classes("audion-checkbox-grid audion-browser-bookmarks-checkboxes"):
        for browser_key, label in options.items():
            checkbox = ui.checkbox(
                label,
                value=browser_key in selected_set,
                on_change=lambda event, key=browser_key: browser_bookmarks_checkbox_handler(parent, key, bool(event.value))(),
            ).props("dense").classes("audion-grid-checkbox")
            soft_tooltip(checkbox, browser_bookmarks_browser_hint(action, str(label)))
    if action == "browser_bookmarks_import_master":
        note = ui.label("HTML: чистый импорт Bookmarks + восстановление встроенных ICON." if settings.language == "ru" else "HTML: clean Bookmarks import + embedded ICON recovery.").classes("audion-field-hint")
        soft_tooltip(note, "Для каждого браузера сначала сохраняется полный rollback. Старая favicon-база очищается и заполняется иконками из HTML." if settings.language == "ru" else "A full rollback is saved for every browser first. The old favicon database is cleared and repopulated from HTML icons.")


def render_browser_bookmarks_favicon_action(parent: CommandNode, nodes: list[CommandNode], selected: list[Any]) -> None:
    clear_node = browser_bookmarks_child(nodes, "browser_bookmarks_clear_favicons")
    if clear_node is None:
        return
    open_node = browser_bookmarks_child(nodes, "browser_bookmarks_open_local_backup")
    with ui.row().classes("audion-browser-service-row w-full justify-end items-center gap-3 pt-1"):
        if open_node is not None:
            open_button = ui.button(
                "ОТКРЫТЬ BACKUP" if settings.language == "ru" else "OPEN BACKUP",
                icon="folder_open",
                on_click=browser_bookmarks_direct_run_handler(open_node),
            ).props("dense flat no-wrap").classes("audion-action audion-browser-open-backup rounded-lg")
            soft_tooltip(open_button, "Открыть project-local папку rollback-копий. Кнопка ничего не создаёт и не изменяет." if settings.language == "ru" else "Open the project-local rollback folder. This button creates and changes nothing.")
        rollback = ui.checkbox(
            "СОЗДАТЬ ROLLBACK" if settings.language == "ru" else "CREATE ROLLBACK",
            value=bool(state.get("browser_bookmarks_create_rollback", True)),
            on_change=browser_bookmarks_rollback_handler,
        ).props("dense").classes("audion-single-checkbox")
        soft_tooltip(rollback, "Сохранить текущие Bookmarks и Favicons перед импортом или очисткой. Сними флажок, если повреждённую favicon-базу сохранять не нужно." if settings.language == "ru" else "Save current Bookmarks and Favicons before import or cleanup. Disable when the damaged favicon database is not worth keeping.")
        button = ui.button(
            "ОЧИСТИТЬ FAVICONS" if settings.language == "ru" else "CLEAR FAVICONS",
            icon="delete_sweep",
            on_click=browser_bookmarks_run_handler(parent, clear_node, selected),
        ).props("dense flat no-wrap").classes("audion-action audion-browser-favicons-button rounded-lg")
        soft_tooltip(button, "Очистить Favicons/Favicons-journal во ВСЕХ отмеченных выше системных браузерах либо в одном выбранном portable-профиле. Закладки не меняются. Rollback зависит от соседнего чекбокса." if settings.language == "ru" else "Clear Favicons/Favicons-journal in ALL checked system browsers above, or in one selected portable profile. Bookmarks stay intact. Rollback follows the adjacent checkbox.")


def render_browser_bookmarks_master(parent: CommandNode, nodes: list[CommandNode]) -> None:
    action, options, selected, single = normalize_browser_bookmarks_state(parent)
    action_node = browser_bookmarks_child(nodes, action)
    if action_node is None:
        ui.label(tr("empty_section")).classes("audion-empty-section")
        return

    with ui.row().classes("audion-command-switcher w-full"):
        for action_id in BROWSER_BOOKMARKS_ACTIONS:
            node = browser_bookmarks_child(nodes, action_id)
            if node is None:
                continue
            classes = f"audion-action audion-switcher-button {browser_bookmarks_action_tone_class(action_id)} rounded-lg"
            if action_id == action:
                classes += " audion-switcher-button-active"
            button = ui.button(
                browser_bookmarks_action_label(action_id),
                on_click=browser_bookmarks_action_click_handler(parent, action_id),
            ).props("dense flat no-wrap").classes(classes)
            soft_tooltip(button, browser_bookmarks_action_hint(action_id))

    with ui.element("div").classes("audion-switcher-panel audion-browser-bookmarks-panel"):
        with ui.element("section").classes("audion-browser-block audion-browser-block-location"):
            render_browser_bookmarks_location(parent, len(selected))
        if action == "browser_bookmarks_import_master":
            with ui.element("section").classes("audion-browser-block audion-browser-block-source"):
                render_browser_bookmarks_import_source()
        with ui.element("section").classes("audion-browser-block audion-browser-block-browsers"):
            render_browser_bookmarks_selector(parent, action, options, selected, single)
            render_browser_bookmarks_favicon_action(parent, nodes, selected)
        with ui.element("section").classes("audion-browser-block audion-browser-block-routes"):
            render_browser_bookmarks_routes(action)
        primary_fields, advanced_fields = browser_bookmarks_fields_for_action(parent, action, len(selected))
        with ui.element("section").classes("audion-browser-block audion-browser-block-details"):
            if primary_fields:
                ui.label(tr("parameters")).classes("text-sm font-semibold text-gray-300 pt-2")
                render_field_grid(primary_fields)
            if advanced_fields:
                render_advanced_fields(advanced_fields)
            render_operation_copy(action_node, show_title=True)


ADVANCED_FIELD_SUFFIXES = (
    "_model_override",
    "_chunk_tokens",
    "_overlap_tokens",
    "_min_chunks",
    "_max_retries",
    "_max_output_tokens",
    "_timeout_sec",
    "_resume",
)


def is_advanced_field(field: dict[str, Any]) -> bool:
    if bool(field.get("advanced", False)):
        return True
    priority = str(field.get("priority") or field.get("section") or "").strip().lower()
    if priority in {"advanced", "expert", "rare"}:
        return True
    key = field_id(field)
    return any(key.endswith(suffix) for suffix in ADVANCED_FIELD_SUFFIXES)


def split_primary_advanced_fields(fields: tuple[dict[str, Any], ...]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    primary: list[dict[str, Any]] = []
    advanced: list[dict[str, Any]] = []
    for field in fields:
        if is_advanced_field(field):
            advanced.append(field)
        else:
            primary.append(field)
    return primary, advanced


def field_section_id(field: dict[str, Any]) -> str:
    key = field_id(field)
    kind = str(field.get("type", field.get("kind", "text"))).lower()
    section = str(field.get("section") or "").strip().lower()
    explicit = str(field.get("group") or field.get("ui_group") or field.get("section_group") or "").strip().lower()
    if not explicit and section and section not in {"advanced", "expert", "rare"}:
        explicit = section
    if explicit:
        return explicit
    if kind in {"profile_select", "profile-select", "preset_select", "preset-select", "preset_buttons", "presets", "profile_buttons", "profiles"}:
        return "preset"
    if key in {"dry_run", "no_launch", "overwrite"} or key.endswith(("_dry_run", "_overwrite")):
        return "run"
    if any(part in key for part in ("selinux", "sudo", "wheel")):
        return "security"
    if key.startswith("linux_") or any(part in key for part in ("username", "password", "default_user")):
        return "account"
    if "package" in key or key in {"wsl_apt_update_first", "wsl_install_recommends", "wsl_flatpak_flathub"}:
        return "packages"
    if any(part in key for part in ("distro", "wsl_name")) or key in {"install_name", "new_name"}:
        return "distro"
    if any(part in key for part in ("profile", "preset", "skin")):
        return "profile"
    if any(part in key for part in ("adapter", "wifi", "lan", "network")):
        return "network"
    if key in {"target_folder", "install_location", "location", "backup_dir"} or key.endswith(("_location", "_dir")):
        return "target"
    if any(part in key for part in ("source", "input", "url", "file", "folder", "path", "root")):
        return "source"
    if any(part in key for part in ("format", "container", "quality", "dpi", "bitrate", "resolution")):
        return "format"
    if any(part in key for part in ("output", "report", "export", "release")):
        return "output"
    if any(part in key for part in ("codec", "encode", "model", "engine")):
        return "encoding"
    if kind in {"checkbox", "bool", "boolean", "toggle", "radio", "checkboxes", "multi_checkbox", "multicheckbox", "multi-select", "multiselect"}:
        return "options"
    return "parameters"


def field_section_label(section_id: str) -> str:
    key = f"section_{section_id}"
    label = tr(key)
    if label != key:
        return label
    return section_id.replace("_", " ").title()


def group_fields_by_section(fields: list[dict[str, Any]]) -> list[tuple[str, list[dict[str, Any]]]]:
    groups: list[tuple[str, list[dict[str, Any]]]] = []
    group_index: dict[str, int] = {}
    for field in fields:
        section_id = field_section_id(field)
        if section_id not in group_index:
            group_index[section_id] = len(groups)
            groups.append((section_id, [field]))
        else:
            groups[group_index[section_id]][1].append(field)
    return groups


def render_field_grid(fields: list[dict[str, Any]]) -> None:
    if not fields:
        return
    with ui.element("div").classes("audion-fields-grid"):
        for section_id, section_fields in group_fields_by_section(fields):
            with ui.element("section").classes(f"audion-field-section audion-field-section-{section_id}"):
                ui.label(field_section_label(section_id)).classes("audion-section-title")
                with ui.element("div").classes("audion-section-fields"):
                    for field in section_fields:
                        try:
                            render_field(field)
                        except Exception as exc:
                            ui.label(f"{field_label(field)}: {exc.__class__.__name__}: {exc}").classes("audion-field-error")


def render_advanced_fields(fields: list[dict[str, Any]]) -> None:
    if not fields:
        return
    with ui.expansion(
        tr("advanced"),
        value=bool(getattr(settings, "advanced_open", False)),
        on_value_change=save_advanced_open,
    ).classes("audion-advanced-expansion w-full") as expansion:
        expansion.props("dense switch-toggle-side")
        render_field_grid(fields)


def command_node_button(node: CommandNode) -> None:
    has_children = bool(node.children)
    direct_launch = is_direct_run_node(node)
    label = node.display_title(settings.language)
    description = node.display_description(settings.language)
    if has_children and not description:
        description = tr("open_menu")

    with ui.element("div").classes(operation_row_classes(node, direct_launch=direct_launch)):
        button = ui.button(
            label,
            on_click=command_click_handler(node),
        ).props("dense flat").classes(action_button_classes(node, direct_launch=direct_launch))
        tooltip = description_tooltip_text(description, operation_meta_lines(node))
        if tooltip:
            soft_tooltip(button, tooltip)
        render_operation_copy(node, show_title=False, fallback_description=description)


def command_surface_toggle() -> None:
    active = current_command_surface()
    with ui.row().classes("audion-command-surface-toggle w-full"):
        for surface in COMMAND_SURFACES:
            classes = "audion-action audion-surface-button rounded-lg"
            if surface == active:
                classes += " audion-surface-button-active"
            button = ui.button(
                tr(f"surface_{surface}"),
                on_click=command_surface_click_handler(surface),
            ).props("dense flat no-wrap").classes(classes)
            tooltip = tr(f"surface_{surface}_tooltip")
            if tooltip != f"surface_{surface}_tooltip":
                soft_tooltip(button, tooltip)


def command_section_label(section_id: str) -> str:
    key = f"command_section_{section_id}"
    label = tr(key)
    if label != key:
        return label
    return section_id.replace("_", " ").title()


def group_command_nodes_by_section(nodes: list[CommandNode]) -> list[tuple[str, list[CommandNode]]]:
    groups: list[tuple[str, list[CommandNode]]] = []
    group_index: dict[str, int] = {}
    for node in nodes:
        section = command_node_section(node)
        if section not in group_index:
            group_index[section] = len(groups)
            groups.append((section, [node]))
        else:
            groups[group_index[section]][1].append(node)
    return groups


def command_section_tooltip(section_id: str) -> str:
    """A section may explain itself; most do not need to."""
    key = f"command_section_{section_id}_tooltip"
    text = tr(key)
    return "" if text == key else text


def render_root_command_sections(nodes: list[CommandNode]) -> None:
    with ui.element("div").classes("audion-command-sections"):
        for section_id, section_nodes in group_command_nodes_by_section(nodes):
            with ui.element("section").classes(f"audion-command-section audion-command-section-{section_id}"):
                section_title = ui.label(command_section_label(section_id)).classes("audion-command-section-title")
                hint = command_section_tooltip(section_id)
                if hint:
                    soft_tooltip(section_title, hint)
                with ui.column().classes("audion-command-section-list w-full gap-0"):
                    for node in section_nodes:
                        command_node_button(node)


def render_browser_bookmarks_nav_run(parent: CommandNode, nodes: list[CommandNode]) -> None:
    action, _options, selected, _single = normalize_browser_bookmarks_state(parent)
    action_node = browser_bookmarks_child(nodes, action)
    if action_node is None:
        return
    run_button = ui.button(
        tr("run"),
        on_click=browser_bookmarks_run_handler(parent, action_node, selected),
    ).props("dense flat no-wrap").classes(command_run_button_classes(action_node))
    tooltip = description_tooltip_text(
        browser_bookmarks_action_hint(action),
        operation_meta_lines(action_node),
    )
    if tooltip:
        soft_tooltip(run_button, tooltip)


def command_nav_row(trail: list[CommandNode], pending: CommandNode | None, nodes: list[CommandNode] | None = None) -> None:
    can_go_back = pending is not None or bool(trail)
    if pending is not None:
        title = pending.display_title(settings.language)
    elif trail:
        title = " / ".join(node.display_title(settings.language) for node in trail)
    else:
        title = ""

    with ui.row().classes("audion-command-nav w-full items-center gap-2"):
        if can_go_back:
            back_button = ui.button(
                tr("back"),
                on_click=go_back_command,
            ).props("dense flat no-wrap").classes("audion-action w-28 rounded-lg")
            soft_tooltip(back_button, "Вернуться на уровень выше" if settings.language == "ru" else "Go back one level")
        ui.label(title).classes("min-w-0 flex-1 truncate text-sm text-gray-400")
        if pending is not None:
            run_button = ui.button(
                tr("run"),
                on_click=run_pending_click_handler(pending),
            ).props("dense flat no-wrap").classes(command_run_button_classes(pending))
            tooltip = command_switcher_tooltip(pending)
            if tooltip:
                soft_tooltip(run_button, tooltip)
        elif trail and trail[-1].id == "browser_bookmarks_master" and nodes is not None:
            render_browser_bookmarks_nav_run(trail[-1], nodes)
        elif trail and nodes is not None and should_render_command_switcher(trail[-1]):
            # A switcher tab runs from this row too, so Run always sits next to
            # Back instead of drifting to the bottom of a long form.
            selected = selected_switcher_node(trail[-1], nodes)
            if selected is not None and not selected.children and command_visible_fields(selected.fields):
                run_button = ui.button(
                    tr("run"),
                    on_click=run_pending_click_handler(selected),
                ).props("dense flat no-wrap").classes(command_run_button_classes(selected))
                tooltip = command_switcher_tooltip(selected)
                if tooltip:
                    soft_tooltip(run_button, tooltip)


@ui.refreshable
def command_tree() -> None:
    trail, nodes = current_command_level()
    pending = state.get("pending_command")
    command_surface_toggle()
    command_nav_row(trail, pending, nodes)

    if pending is not None:
        ui.label(tr("selected_operation")).classes("text-sm font-semibold text-gray-300")
        visible_fields = command_visible_fields(pending.fields)
        if visible_fields:
            primary_fields, advanced_fields = split_primary_advanced_fields(tuple(visible_fields))
            if primary_fields:
                ui.label(tr("parameters")).classes("text-sm font-semibold text-gray-300")
                render_field_grid(primary_fields)
        else:
            advanced_fields = []
        with ui.element("div").classes("audion-selected-operation-summary"):
            render_operation_copy(pending, show_title=True)
        if advanced_fields:
            render_advanced_fields(advanced_fields)
        return

    current_parent = trail[-1] if trail else None
    if current_parent is None:
        if nodes:
            render_root_command_sections(nodes)
        else:
            ui.label(tr("empty_section")).classes("audion-empty-section")
        return

    if current_parent.id == "browser_bookmarks_master":
        render_browser_bookmarks_master(current_parent, nodes)
        return

    with ui.element("div").classes("audion-child-command-surface w-full"):
        if should_render_command_switcher(current_parent):
            render_command_switcher(current_parent, nodes)
            return

        if has_only_leaf_children(nodes):
            render_leaf_action_group(nodes)
            return

        if not nodes:
            ui.label(tr("empty_section")).classes("audion-empty-section")
            return

        render_command_node_group(nodes)


@ui.refreshable
def terminal_command_bar() -> None:
    shell_options = {"pwsh": "PowerShell", "cmd": "CMD"} if os.name == "nt" else {"sh": "Shell"}
    with ui.column().classes("audion-terminal-command w-full gap-1"):
        with ui.row().classes("audion-terminal-command-row w-full items-center"):
            shell_select = ui.select(
                options=shell_options,
                label=tr("terminal_shell"),
                value=str(state.get("terminal_shell") or next(iter(shell_options))),
                on_change=lambda event: set_terminal_shell(event.value),
            )
            shell_select.props("dense outlined popup-content-class=audion-select-popup").classes("audion-terminal-shell")

            history_select = ui.select(
                options=terminal_command_options(),
                label=tr("terminal_history"),
                value=terminal_history_value(),
                on_change=lambda event: select_terminal_history(event),
            )
            history_select.props("dense outlined popup-content-class=audion-select-popup").classes("audion-terminal-history min-w-0 flex-1")

            pin_button = ui.button(
                icon="push_pin",
                on_click=pin_terminal_command,
            ).props("dense flat round").classes("audion-action audion-terminal-icon-button audion-terminal-pin")
            soft_tooltip(pin_button, audion_terminal_action_tooltip("pin_command"))
            unpin_button = ui.button(
                icon="block",
                on_click=unpin_terminal_command,
            ).props("dense flat round").classes("audion-action audion-terminal-icon-button audion-terminal-unpin")
            soft_tooltip(unpin_button, audion_terminal_action_tooltip("unpin_command"))
            clear_button = ui.button(
                icon="delete",
                on_click=clear_terminal_history,
            ).props("dense flat round").classes("audion-action audion-terminal-icon-button audion-terminal-clear")
            soft_tooltip(clear_button, audion_terminal_action_tooltip("clear_history"))
            ui.button(
                tr("terminal_run"),
                on_click=start_terminal_command,
            ).props("dense flat no-wrap").classes("audion-action audion-terminal-run rounded-lg")

        command_area = ui.textarea(
            label=tr("terminal_command"),
            value=str(state.get("terminal_command") or ""),
            on_change=lambda event: set_terminal_command(event.value),
        )
        command_area.props("dense outlined autogrow rows=3").classes("audion-terminal-command-text w-full")
        command_area.on("keydown.ctrl.enter", terminal_enter_handler)

        with ui.row().classes("w-full items-center gap-2"):
            ui.input(
                label=tr("terminal_cwd"),
                value=str(state.get("terminal_cwd") or ROOT),
                on_change=lambda event: set_terminal_cwd(event.value),
            ).props("dense outlined").classes("audion-terminal-cwd min-w-0 flex-1")
            ui.button(
                tr("terminal_folder"),
                on_click=terminal_location_click_handler("folder"),
            ).props("dense flat no-wrap").classes("audion-action audion-terminal-picker rounded-lg")
            ui.button(
                tr("terminal_file"),
                on_click=terminal_location_click_handler("file"),
            ).props("dense flat no-wrap").classes("audion-action audion-terminal-picker rounded-lg")


APPLICATION_CSS_PATH = Path(__file__).resolve().with_name("theme.css")
_application_css_cache = ""


def application_css() -> str:
    """The application stylesheet lives next to this module, not inside it."""
    global _application_css_cache
    if not _application_css_cache:
        _application_css_cache = APPLICATION_CSS_PATH.read_text(encoding="utf-8")
    return _application_css_cache


def add_styles() -> None:
    add_audion_canonical_ui_styles()
    variables_css = "\n".join(
        f"            --{key}: {value};"
        for key, value in sorted(theme_variables().items())
    )
    ui.add_head_html(
        "<style>\n"
        ":root {\n"
        f"{variables_css}\n"
        "}\n"
        + application_css()
        + "\n</style>\n"
    )


def build_ui() -> None:
    ensure_project_dirs(paths)
    if not state["status"]:
        state["status"] = tr("idle")
    if active_theme_mode() == "dark":
        ui.dark_mode().enable()
    else:
        ui.dark_mode().disable()
    add_styles()
    ui.add_head_html(f"<style>{WORKBENCH_LAYOUT_CSS}\n{WORKBENCH_OVERRIDE_CSS}</style>")
    ui.add_head_html(WORKBENCH_FEEDBACK_CSS)

    with ui.header().classes("audion-header h-[42px] items-center justify-between px-4"):
        with ui.row().classes("audion-header-brand items-baseline gap-2"):
            ui.label(app_title()).classes("audion-header-title text-lg font-bold")
        with ui.row().classes("audion-header-controls items-center gap-2"):
            ui.icon("palette").classes("text-lg")
            ui.select(
                options=theme_options(),
                value=active_theme(),
                on_change=theme_change_handler,
            ).props("dense outlined options-dense").classes("audion-theme-select")
            ui.button(tr("lang_switch"), on_click=toggle_language).props("dense flat").classes("audion-action rounded-lg")
            cancel_button = ui.button(tr("cancel"), on_click=lambda: state.update({"cancel": True})).props("dense flat color=negative")
            cancel_button.visible = False

    with ui.element("div").classes("audion-shell"):
        with ui.column().classes("audion-pane audion-scroll gap-2"):
            with ui.column().classes("audion-panel audion-workspace-panel w-full gap-2 p-2"):
                WORKBENCH_RENDERER.render_address_rows()
                WORKBENCH_RENDERER.render_action_bar()

            ui.label(f"{em('operations')}{tr('operations')}").classes("text-lg font-bold")
            command_tree()

            visible_maintenance_operations = [
                operation for operation in manifest.maintenance_operations if operation.id != "cleanup_input_output"
            ]
            if visible_maintenance_operations:
                ui.label(f"{em('maintenance')}{tr('maintenance')}").classes("text-lg font-bold pt-2")
                for operation in visible_maintenance_operations:
                    operation_button(operation)

        ui.element("div").classes("audion-splitter").props('title="Resize panels"')

        with ui.element("div").classes("audion-pane audion-right gap-2 pt-3"):
            with ui.column().classes("audion-panel w-full gap-2 p-3"):
                        with ui.element("div").classes(status_row_classes()) as status_row:
                            status_dot_main = ui.element("span").classes("audion-status-dot-mark")
                            status_state_label = ui.label(status_state_text()).classes("audion-status-state")
                            status_label = ui.label(str(state["status"])).classes("audion-status-message")
                            status_clock = ui.label(elapsed_text(None)).classes("audion-status-clock")
                            with ui.element("div").classes("audion-status-bar"):
                                status_bar_fill = ui.element("i").style("width: 0%")
                            status_percent = ui.label(progress_text()).classes("audion-status-percent")

            with ui.column().classes("audion-terminal-panel w-full gap-2 p-3"):
                with ui.row().classes("audion-log-toolbar w-full items-center gap-2"):
                    ui.label(f"{em('log')}{tr('log')}").classes("text-base font-semibold")
                    ui.space()
                    ui.button("ROOT", on_click=lambda: open_folder(paths.root)).props("dense flat").classes("audion-action rounded-lg")
                    ui.button("INPUT", on_click=lambda: open_folder(paths.input)).props("dense flat").classes("audion-action rounded-lg")
                    ui.button("OUTPUT", on_click=lambda: open_folder(paths.output)).props("dense flat").classes("audion-action rounded-lg")
                    ui.button("BACKUP", on_click=lambda: open_folder(paths.backup)).props("dense flat").classes("audion-action rounded-lg")
                    ui.button("WORK", on_click=lambda: open_folder(paths.workspace)).props("dense flat").classes("audion-action rounded-lg")
                    ui.button(tr("logs"), on_click=lambda: open_folder(paths.logs)).props("dense flat").classes("audion-action rounded-lg").tooltip(audion_folder_button_tooltip("logs", paths.logs))
                    ui.button(tr("report"), on_click=lambda: open_folder(paths.report)).props("dense flat").classes("audion-action rounded-lg").tooltip(audion_folder_button_tooltip("report", paths.report))
                    ui.button(tr("config"), on_click=lambda: open_folder(paths.config)).props("dense flat").classes("audion-action rounded-lg").tooltip(audion_folder_button_tooltip("config", paths.config))
                    copy_log_button = ui.button(icon="content_copy", on_click=copy_terminal_log_to_clipboard).props("dense flat round").classes("audion-action audion-log-icon-button")
                    soft_tooltip(copy_log_button, tr("copy_terminal_log"))
                    clear_log_button = ui.button(icon="delete_sweep", on_click=clear_terminal_window).props("dense flat round").classes("audion-action audion-log-icon-button")
                    soft_tooltip(clear_log_button, audion_terminal_action_tooltip("clear_terminal_window"))
                    expand_log_button = ui.button(icon="open_in_full", on_click=lambda: log_dialog.open()).props("dense flat round").classes("audion-action audion-log-icon-button")
                    soft_tooltip(expand_log_button, audion_terminal_action_tooltip("expand"))
                log_view = ui.html("", sanitize=False, tag="pre").classes("audion-terminal w-full min-h-[72vh]")
                terminal_command_bar()
                with ui.row().classes("audion-terminal-footer w-full items-center gap-2 px-1 pt-1"):
                    status_dot = ui.label("●").classes(status_dot_classes())
                    terminal_status_label = ui.label(str(state["status"])).classes("min-w-0 flex-1 truncate text-xs")

    with ui.dialog() as log_dialog:
        with ui.card().classes("audion-dialog h-[92vh] w-[92vw] rounded-lg p-3"):
            with ui.row().classes("w-full items-center gap-2"):
                ui.label(f"{em('log')}{tr('log')}").classes("text-base font-semibold")
                ui.space()
                copy_dialog_log_button = ui.button(icon="content_copy", on_click=copy_terminal_log_to_clipboard).props("dense flat round").classes("audion-action audion-log-icon-button")
                soft_tooltip(copy_dialog_log_button, tr("copy_terminal_log"))
                clear_dialog_log_button = ui.button(icon="delete_sweep", on_click=clear_terminal_window).props("dense flat round").classes("audion-action audion-log-icon-button")
                soft_tooltip(clear_dialog_log_button, tr("clear_terminal_window"))
                ui.button(tr("config"), on_click=lambda: open_folder(paths.config)).props("dense flat").classes("audion-action rounded-lg").tooltip(audion_folder_button_tooltip("config", paths.config))
                ui.button(tr("close"), on_click=log_dialog.close).props("dense flat").classes("audion-action rounded-lg").tooltip(audion_terminal_action_tooltip("close"))
            expanded_log_view = ui.html("", sanitize=False, tag="pre").classes("audion-terminal audion-terminal-expanded w-full")

    ui.run_javascript(
        """
        (() => {
          const storageKey = 'audion_devops_tools_terminal_width_ratio_v2';
          const legacyRatioStorageKey = 'audion_devops_tools_terminal_width_ratio';
          const oldPixelStorageKey = 'audion_devops_tools_terminal_width_px';
          const defaultRatio = 0.34;
          const minLeft = 430;
          const minRight = 480;

          const clamp = (value, min, max) => Math.max(min, Math.min(max, value));

          const ratioToWidth = (ratio, shellWidth) => shellWidth * clamp(Number(ratio) || defaultRatio, 0.25, 0.62);

          const applyWidth = (width, persist = true) => {
            const shell = document.querySelector('.audion-shell');
            if (!shell) return;
            const rect = shell.getBoundingClientRect();
            const maxRight = Math.max(minRight, rect.width - minLeft - 40);
            const next = clamp(Number(width) || ratioToWidth(defaultRatio, rect.width), minRight, maxRight);
            shell.style.setProperty('--audion-terminal-width', `${Math.round(next)}px`);
            if (persist) {
              localStorage.setItem(storageKey, String(clamp(next / rect.width, 0.25, 0.62)));
            }
          };

          const applyStoredRatio = () => {
            const shell = document.querySelector('.audion-shell');
            if (!shell) return;
            localStorage.removeItem(legacyRatioStorageKey);
            localStorage.removeItem(oldPixelStorageKey);
            const rect = shell.getBoundingClientRect();
            applyWidth(ratioToWidth(localStorage.getItem(storageKey) || defaultRatio, rect.width), false);
          };

          const setup = () => {
            const shell = document.querySelector('.audion-shell');
            const splitter = document.querySelector('.audion-splitter');
            if (!shell || !splitter) {
              setTimeout(setup, 80);
              return;
            }
            if (splitter.dataset.audionReady === '1') return;
            splitter.dataset.audionReady = '1';

            applyStoredRatio();

            let dragging = false;
            const updateFromEvent = (event) => {
              if (!dragging) return;
              const rect = shell.getBoundingClientRect();
              const rightWidth = rect.right - event.clientX - 10;
              applyWidth(rightWidth);
            };

            splitter.addEventListener('pointerdown', (event) => {
              dragging = true;
              splitter.setPointerCapture?.(event.pointerId);
              document.body.classList.add('audion-resizing');
              event.preventDefault();
            });
            splitter.addEventListener('pointermove', updateFromEvent);
            splitter.addEventListener('pointerup', (event) => {
              dragging = false;
              splitter.releasePointerCapture?.(event.pointerId);
              document.body.classList.remove('audion-resizing');
            });
            splitter.addEventListener('pointercancel', () => {
              dragging = false;
              document.body.classList.remove('audion-resizing');
            });
            window.addEventListener('resize', applyStoredRatio);
          };

          setup();
        })();
        """
    )

    # Terminal text is element content, not a JavaScript side effect: NiceGUI owns the DOM,
    # so the log is written through `ui.html.content` and survives reconnects and re-renders.
    # The only thing left to JavaScript is scrolling, which the DOM model cannot express.
    ui.run_javascript(
        """
        (() => {
          const stickToBottom = new WeakMap();
          const isAtBottom = (el) => Math.abs(el.scrollHeight - el.scrollTop - el.clientHeight) <= 6;
          const hasSelection = (el) => {
            const selection = window.getSelection?.();
            if (!selection || selection.isCollapsed) return false;
            return el.contains(selection.anchorNode) || el.contains(selection.focusNode);
          };
          const attach = (el) => {
            if (stickToBottom.has(el)) return;
            stickToBottom.set(el, true);
            el.scrollTop = el.scrollHeight;
            el.addEventListener('scroll', () => stickToBottom.set(el, isAtBottom(el)));
            new MutationObserver(() => {
              if (stickToBottom.get(el) && !hasSelection(el)) {
                el.scrollTop = el.scrollHeight;
              }
            }).observe(el, { childList: true, subtree: true, characterData: true });
          };
          let scanScheduled = false;
          const scan = () => {
            scanScheduled = false;
            document.querySelectorAll('.audion-terminal').forEach(attach);
          };
          scan();
          new MutationObserver(() => {
            if (scanScheduled) return;
            scanScheduled = true;
            setTimeout(scan, 0);
          }).observe(document.body, { childList: true, subtree: true });
        })();
        """
    )

    last_log_version = {"value": -1}

    refresh_timer: Any | None = None

    # Every one of these used to be written twice a second whether or not it had
    # changed, so an idle window still sent ten element updates a second. Holding
    # the last value makes an idle panel cost nothing and pays for the clock.
    shown = {"status": None, "state": None, "row": None, "clock": None, "percent": None, "fill": None}
    run_clock: dict[str, float | None] = {"started": None, "frozen": None}

    def refresh() -> None:
        nonlocal refresh_timer
        try:
            running = bool(state["running"])
            if running and run_clock["started"] is None:
                run_clock["started"] = time.monotonic()
                run_clock["frozen"] = None
            elif not running and run_clock["started"] is not None:
                run_clock["frozen"] = time.monotonic() - run_clock["started"]
                run_clock["started"] = None
            seconds = (
                time.monotonic() - run_clock["started"]
                if run_clock["started"] is not None
                else run_clock["frozen"]
            )

            def show(key: str, value: Any, assign: Any) -> None:
                if shown[key] != value:
                    shown[key] = value
                    assign(value)

            message = str(state["status"])
            show("status", message, lambda value: (
                setattr(status_label, "text", value),
                setattr(terminal_status_label, "text", value),
            ))
            show("state", status_state_text(), lambda value: setattr(status_state_label, "text", value))
            show("row", status_row_classes(), lambda value: (
                status_row.classes(replace=value),
                status_dot.classes(replace=status_dot_classes()),
            ))
            show("clock", elapsed_text(seconds), lambda value: setattr(status_clock, "text", value))
            show("percent", progress_text(), lambda value: setattr(status_percent, "text", value))
            show("fill", f"{float(state['progress']) * 100:.1f}%",
                lambda value: status_bar_fill.style(f"width: {value}"))
            log_version = int(state["log_version"])
            if log_version != last_log_version["value"]:
                last_log_version["value"] = log_version
                # `state["lines"]` is already capped at TERMINAL_MAX_LINES, so a full
                # re-render stays bounded and keeps ANSI colour runs correct across lines.
                log_html = terminal_lines_html(list(state["lines"]))
                log_view.content = log_html
                expanded_log_view.content = log_html
            cancel_button.visible = bool(state["running"])
        except RuntimeError as exc:
            message = str(exc)
            if "slot belongs to has been deleted" not in message and "current slot cannot be determined" not in message:
                raise
            logging.warning("NiceGUI refresh timer stopped because the client slot was deleted.")
            if refresh_timer is not None:
                refresh_timer.deactivate()

    refresh_timer = ui.timer(0.5, refresh)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audion NiceGUI shell.")
    parser.add_argument("--host", default=str(ui_info.get("host", "127.0.0.1")))
    parser.add_argument("--port", type=int, default=int(ui_info.get("port", 8080)))
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--smoke", action="store_true")
    return parser.parse_args()


def port_is_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.3)
        return sock.connect_ex((host, port)) == 0


def build_ui_once() -> dict[str, int]:
    """Build the whole page once, headlessly, and report what came of it.

    `--smoke` used to print a line and return, so an app could ship a `build_ui`
    that raised on its first statement and still pass — twice in this fleet it did.
    Here the page is actually built: no browser and no HTTP request, so whatever
    the app defers until a client attaches is skipped, but every widget is
    constructed and the stylesheet has to arrive.
    """
    import asyncio
    import logging
    import re

    from nicegui import core
    from nicegui.client import Client
    from nicegui.page import page as page_definition

    async def build() -> tuple[int, str]:
        core.loop = asyncio.get_running_loop()
        # Work deferred to a connected browser fails here and says nothing about
        # the build. An exception raised by build_ui itself still propagates.
        core.loop.set_exception_handler(lambda _loop, _context: None)
        logging.getLogger("nicegui").setLevel(logging.CRITICAL)
        client = Client(page_definition("/__smoke__"))
        with client:
            build_ui()
        report = len(client.elements), client.shared_head_html + client.head_html
        # The page starts work that waits for a browser to attach. Nothing will
        # attach, so stop it deliberately instead of letting the loop close on it.
        pending = asyncio.all_tasks(core.loop) - {asyncio.current_task()}
        for task in pending:
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
        return report

    element_count, head = asyncio.run(build())
    if element_count < 2:
        raise RuntimeError("build_ui produced no widgets")
    # Token prefixes differ between apps, so look for any custom property rather
    # than for one project's naming.
    if not re.search(r"--[\w-]+\s*:", head):
        raise RuntimeError("the stylesheet never reached the page")
    return {"elements": element_count, "stylesheet_bytes": len(head)}


def main() -> int:
    args = parse_args()
    ensure_project_dirs(paths)
    if args.smoke:
        try:
            report = build_ui_once()
        except Exception as error:  # noqa: BLE001
            print(f"FAIL nicegui shell: {ROOT}: {error}")
            return 1
        print(
            f"OK nicegui shell: {ROOT}"
            f" | widgets={report['elements']}"
            f" | stylesheet={report['stylesheet_bytes']} bytes"
        )
        return 0

    if port_is_open(args.host, args.port):
        url = f"http://{args.host}:{args.port}/"
        print(f"GUI already appears to be running: {url}")
        if not args.no_browser:
            webbrowser.open(url)
        return 0

    ui.run(
        root=build_ui,
        title=app_title(),
        host=args.host,
        port=args.port,
        reload=False,
        native=False,
        show=not args.no_browser,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

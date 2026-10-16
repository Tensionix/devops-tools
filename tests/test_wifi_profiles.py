"""The list of Wi-Fi profiles puts the one connected now first, says so, and chooses nothing.

    runtime\\python.exe tests\\test_wifi_profiles.py

netsh is not asked: its answers of a Russian and an English Windows are given as they print them.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from system_core.services import devops_tools  # noqa: E402

PROFILES_RU = """
Профили интерфейса Беспроводная сеть:

Профили групповой политики (только чтение)
------------------------------------------
    <Отсутствует>

Профили пользователей
---------------------
    Все профили пользователей     : BASE_Master
    Все профили пользователей     : BASE_Master_TTK
    Все профили пользователей     : ItpGrad-5.0G
"""
CONNECTED_RU = """
В системе 1 интерфейс:

    Имя:                                Беспроводная сеть
    Описание:                       Intel(R) Wi-Fi 6E AX211 160MHz
    Состояние:                     подключено
    SSID                   : BASE_Master_TTK
    AP BSSID               : 12:34:56:78:9a:bc
    Тип сети             : Инфраструктура
    Профиль                : BASE_Master_TTK
"""
DISCONNECTED_RU = """
В системе 1 интерфейс:

    Имя:                                Беспроводная сеть
    Состояние:                     отключено
"""
CONNECTED_EN = """
There is 1 interface on the system:

    Name                   : Wi-Fi
    State                  : connected
    SSID                   : ItpGrad-5.0G
    BSSID                  : 12:34:56:78:9a:bc
    Profile                : ItpGrad-5.0G
"""


class WifiProfiles(unittest.TestCase):
    def options(self, interfaces: str) -> list[dict]:
        answers = {"profiles": PROFILES_RU, "interfaces": interfaces}
        saved = devops_tools._run_capture
        devops_tools._run_capture = lambda command, **_: answers[command[3]]
        try:
            return devops_tools.wifi_profile_options(ROOT)
        finally:
            devops_tools._run_capture = saved

    def test_the_connected_profile_stands_first_and_says_so(self) -> None:
        options = self.options(CONNECTED_RU)
        self.assertEqual([option["value"] for option in options], ["BASE_Master_TTK", "BASE_Master", "ItpGrad-5.0G"])
        self.assertEqual(options[0]["label_ru"], "BASE_Master_TTK — подключён сейчас")
        self.assertEqual(options[0]["label"], "BASE_Master_TTK - connected now")
        self.assertEqual(options[1]["label_ru"], "BASE_Master")

    def test_nothing_is_chosen_for_the_field(self) -> None:
        self.assertFalse(any(option.get("default") for option in self.options(CONNECTED_RU)))

    def test_an_english_windows_is_read_too(self) -> None:
        self.assertEqual(self.options(CONNECTED_EN)[0]["value"], "ItpGrad-5.0G")

    def test_without_a_connection_the_list_is_as_before(self) -> None:
        options = self.options(DISCONNECTED_RU)
        self.assertEqual([option["value"] for option in options], ["BASE_Master", "BASE_Master_TTK", "ItpGrad-5.0G"])
        self.assertEqual([option["label_ru"] for option in options], ["BASE_Master", "BASE_Master_TTK", "ItpGrad-5.0G"])

    def test_a_network_without_its_profile_line_is_found_by_its_ssid(self) -> None:
        only_ssid = CONNECTED_RU.replace("    Профиль                : BASE_Master_TTK\n", "")
        self.assertEqual(self.options(only_ssid)[0]["value"], "BASE_Master_TTK")


if __name__ == "__main__":
    unittest.main(verbosity=1)

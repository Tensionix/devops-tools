# README — Wi-Fi Segments Switch (Keenetic + Windows)

## 1) Что это

Набор BAT/CMD-кнопок для быстрого переключения ПК между:

* **HOME Wi-Fi сегментом** (SSID `BASE_Master`)
* **TTK Wi-Fi сегментом** (SSID `BASE_Master_TTK_Wi-Fi`)
  и управления проводным интерфейсом **Ethernet** (вкл/выкл), чтобы Windows не “упорно” выбирала провод.

---

## 2) Файлы-кнопки и что они делают

### WiFi-HOME.cmd

Подключает Wi-Fi к HOME SSID и делает “липко”:

* HOME = автоподключение
* TTK = вручную

### WiFi-TTK.cmd

Подключает Wi-Fi к TTK SSID и делает “липко”:

* TTK = автоподключение
* HOME = вручную

### WiFi-STATUS.cmd

Показывает:

* текущий SSID
* базовые строки из `ipconfig` (IPv4, Gateway, DNS)

### Wired-OFF.cmd

Отключает сетевой интерфейс **Ethernet** (требует админ-права / UAC).

### Wired-ON.cmd

Включает сетевой интерфейс **Ethernet** (требует админ-права / UAC).

### Go-TTK.cmd

Цепочка:

1. Wired-OFF
2. WiFi-TTK

### Go-HOME.cmd

Цепочка:

1. WiFi-HOME
2. Wired-ON

### Go-HOME-WiFi-Only.cmd

Цепочка:

1. Wired-OFF
2. WiFi-HOME

### Go-WIRED-ONLY.cmd

Цепочка:

1. Wired-ON
2. Wi-Fi disconnect

---

## 3) Команды netsh, которые используются

### 3.1 Список Wi-Fi профилей (известных сетей)

```bat
netsh wlan show profiles
```

Показывает названия Wi-Fi профилей, которые нужно указывать в `netsh wlan connect name="..."`.

### 3.2 Подключиться к Wi-Fi профилю

```bat
netsh wlan connect name="BASE_Master"
```

Подключает к сохранённой сети.

### 3.3 Отключить Wi-Fi соединение (не адаптер)

```bat
netsh wlan disconnect
```

Разрывает соединение, Wi-Fi адаптер остаётся включён.

### 3.4 Показать текущий SSID и статус Wi-Fi

```bat
netsh wlan show interfaces
```

Проверка “я реально в HOME или TTK?”.

### 3.5 Управлять автоподключением к профилю (sticky mode)

Авто:

```bat
netsh wlan set profileparameter name="BASE_Master" connectionmode=auto
```

Только вручную:

```bat
netsh wlan set profileparameter name="BASE_Master_TTK_Wi-Fi" connectionmode=manual
```

### 3.6 Показать список сетевых интерфейсов

```bat
netsh interface show interface
```

Имена интерфейсов должны совпадать с тем, что указано в скриптах (например `Ethernet`).

### 3.7 Включить / выключить Ethernet как интерфейс

Выключить:

```bat
netsh interface set interface name="Ethernet" admin=disabled
```

Включить:

```bat
netsh interface set interface name="Ethernet" admin=enabled
```

---

## 4) Быстрые проверки после переключения

### Проверка SSID

```bat
netsh wlan show interfaces
```

### Проверка IP / Gateway / DNS

```bat
ipconfig
```

Ожидаемо:

* HOME: обычно `192.168.1.x`
* TTK: обычно `192.168.2.x`

---

## 5) Типовые проблемы и решения

### 5.1 “Переключаю Wi-Fi, а интернет будто не меняется”

Почти всегда виноват **Ethernet**, который остаётся подключён.
Решение: использовать `Wired-OFF.cmd` перед Wi-Fi.

### 5.2 “Нужно Admin для Wired-ON/OFF”

Это нормально: включение/выключение интерфейса требует прав администратора.

### 5.3 “Wi-Fi профиль не находится”

Проверь точное имя:

```bat
netsh wlan show profiles
```

И сравни со строкой в батнике `netsh wlan connect name="..."`.

### 5.4 “Новый IP (192.168.2.x) и не открывается роутер”

Это нормально для VLAN/Segment.
Нужно разрешить доступ к сервисам роутера из сегмента (в Keenetic):
включить опцию типа **Access the applications running on your device** для этого сегмента.

---

## 6) Где менять параметры (если переименуешь SSID/интерфейс)

* SSID меняются в `WiFi-HOME.cmd` / `WiFi-TTK.cmd` в строках `name="..."`.
* Имя проводного интерфейса меняется в `Wired-ON.cmd` / `Wired-OFF.cmd` в строке:

```bat
set "WIRED_IF=Ethernet"
```

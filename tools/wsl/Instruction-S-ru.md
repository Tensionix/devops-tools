# Instruction-S — WSL дома (`S:\WSL`)

## 1. Что где делается

### Только в Windows

Здесь мы ставим и обслуживаем **WSL for Windows**.

Это делается из **CMD** или **PowerShell** **от имени администратора**.

Команды этого слоя начинаются с `wsl ...`.

Именно здесь включается WSL, скачивается Linux-дистрибутив и задаётся папка установки через `--location`.

### Уже внутри Ubuntu в WSL

Это уже не Windows, а сама Linux-среда Ubuntu.

Сначала Ubuntu должна быть установлена через `wsl --install ...`.

Потом в неё входят командой `wsl -d ...`, и только после этого выполняют Linux-команды:

- `apt`
- `do-release-upgrade`
- `.sh` bootstrap-скрипты

### На обычных Linux Desktop

Те же `.sh` bootstrap-скрипты можно запускать и на обычных Ubuntu Desktop / Fedora Desktop.

Это **отдельный сценарий**, не обязательный для WSL.

То есть:

- `wsl ...` — только Windows
- `apt ...`, `do-release-upgrade`, `./bootstrap_*.sh` — внутри Linux

---

## 2. Целевая структура дома

```text
S:\WSL\
├─ Backup\
├─ Docs\
├─ Logs\
├─ Toolkit\
└─ VHDX\
```

Основная папка для Ubuntu в WSL:

```text
S:\WSL\VHDX\Ubuntu
```

Важно: папку лучше называть просто **`Ubuntu`**, а не `Ubuntu-24.04`.

Причина простая: версия LTS меняется, а рабочий путь лучше оставить стабильным.

---

## 3. Команды Windows — WSL-host layer

Запускать из **CMD** или **PowerShell** **от имени администратора**.

### 3.1. Проверка состояния WSL

Показывает общее состояние WSL в Windows.

```cmd
wsl --status
```

Показывает версию WSL и связанные компоненты.

```cmd
wsl --version
```

Показывает список доступных к установке дистрибутивов.

```cmd
wsl --list --online
```

### 3.2. Варианты установки WSL и Ubuntu

Это базовая установка WSL с дистрибутивом по умолчанию.

```cmd
wsl --install
```

Это явная установка обычного Ubuntu.

```cmd
wsl --install -d Ubuntu
```

Это явная установка Ubuntu 24.04 LTS как опция.

```cmd
wsl --install -d Ubuntu-24.04
```

Это установка Ubuntu в нужную рабочую папку на диске `S:`.

```cmd
wsl --install -d Ubuntu --location "S:\WSL\VHDX\Ubuntu"
```

Это установка именно Ubuntu 24.04 LTS в ту же стабильную папку `Ubuntu`.

```cmd
wsl --install -d Ubuntu-24.04 --location "S:\WSL\VHDX\Ubuntu"
```

Важно:

Запускают **только один** подходящий вариант установки.

Не нужно выполнять все команды установки подряд.

Если ты хочешь строго указать актуальный LTS-релиз при установке, используй вариант с `Ubuntu-24.04`.

Если тебе важнее более нейтральное имя, используй вариант с `Ubuntu`.

### 3.3. Команды после установки

Обновляет сам слой WSL в Windows.

```cmd
wsl --update
```

Полностью останавливает все WSL-дистрибутивы.

```cmd
wsl --shutdown
```

Показывает установленные дистрибутивы и версию WSL для каждого.

```cmd
wsl -l -v
```

### 3.4. Вход в Ubuntu

Вход в дистрибутив с именем `Ubuntu`.

```cmd
wsl -d Ubuntu
```

Вход в дистрибутив с именем `Ubuntu-24.04`.

```cmd
wsl -d Ubuntu-24.04
```

Важно:

Входить нужно в то имя дистрибутива, которое реально зарегистрировано в WSL.

Имя дистрибутива в WSL и имя папки на диске могут не совпадать.

Например, дистрибутив может называться `Ubuntu-24.04`, а лежать в папке:

```text
S:\WSL\VHDX\Ubuntu
```

---

## 4. Команды уже внутри Ubuntu в WSL

Эти команды выполняются **после входа** в Ubuntu.

### 4.1. Проверка версии Ubuntu

Показывает версию дистрибутива в удобном виде.

```bash
lsb_release -a
```

Показывает системную информацию из `os-release`.

```bash
cat /etc/os-release
```

### 4.2. Обычное обновление текущего LTS

Обновляет индекс пакетов.

```bash
sudo apt update
```

Устанавливает обычные обновления пакетов.

```bash
sudo apt upgrade -y
```

Устанавливает более полное обновление с учётом изменений зависимостей.

```bash
sudo apt full-upgrade -y
```

Удаляет больше не нужные пакеты и их остатки.

```bash
sudo apt autoremove --purge -y
```

Очищает локальный кэш пакетов.

```bash
sudo apt autoclean
```

### 4.3. Переход на следующий LTS

Команда перехода на следующий релиз Ubuntu.

```bash
sudo do-release-upgrade
```

Важно:

Это уже не обычное обновление пакетов, а upgrade самого релиза Ubuntu.

Для LTS используется последовательный путь:

- с одного LTS на следующий LTS
- без перепрыгивания через релизы

На WSL перед крупным upgrade разумно сначала закрыть сессию Ubuntu и затем из Windows выполнить:

```cmd
wsl --shutdown
```

После этого снова запустить Ubuntu и продолжить работу.

---

## 5. Bootstrap-скрипты Linux

Это уже **Linux-скрипты**, не Windows-скрипты.

Их можно использовать:

- внутри Ubuntu в WSL
- на обычном Ubuntu Desktop
- на обычном Fedora Desktop

### 5.1. Если bootstrap лежит на Windows-диске `S:`

Например, архив bootstrap распакован сюда:

```text
S:\Audion-Linux-Bootstrap
```

Тогда внутри Ubuntu в WSL путь будет таким:

```text
/mnt/s/Audion-Linux-Bootstrap
```

### 5.2. Пример запуска Ubuntu bootstrap внутри WSL

Дать право на запуск базовому Ubuntu-скрипту.

```bash
chmod +x /mnt/s/Audion-Linux-Bootstrap/Ubuntu-Desktop/bootstrap_ubuntu_minimal.sh
```

Запустить базовый Ubuntu-скрипт.

```bash
/mnt/s/Audion-Linux-Bootstrap/Ubuntu-Desktop/bootstrap_ubuntu_minimal.sh
```

Дать право на запуск расширенному Ubuntu-скрипту.

```bash
chmod +x /mnt/s/Audion-Linux-Bootstrap/Ubuntu-Desktop/bootstrap_ubuntu_power.sh
```

Запустить расширенный Ubuntu-скрипт.

```bash
/mnt/s/Audion-Linux-Bootstrap/Ubuntu-Desktop/bootstrap_ubuntu_power.sh
```

### 5.3. Пример запуска Fedora bootstrap на обычном Fedora Desktop

Дать право на запуск базовому Fedora-скрипту.

```bash
chmod +x ./Fedora-Desktop/bootstrap_fedora_minimal.sh
```

Запустить базовый Fedora-скрипт.

```bash
./Fedora-Desktop/bootstrap_fedora_minimal.sh
```

Дать право на запуск расширенному Fedora-скрипту.

```bash
chmod +x ./Fedora-Desktop/bootstrap_fedora_power.sh
```

Запустить расширенный Fedora-скрипт.

```bash
./Fedora-Desktop/bootstrap_fedora_power.sh
```

---

## 6. Практический рекомендуемый сценарий для домашнего ПК

### Шаг 1. Распаковать WSL-блок

Распаковать архив WSL-блока так, чтобы получился корень:

```text
S:\WSL
```

### Шаг 2. Распаковать Linux bootstrap отдельно

Рекомендуемое место:

```text
S:\Audion-Linux-Bootstrap
```

### Шаг 3. В Windows установить Ubuntu в нужную папку

Базовый рекомендуемый вариант:

```cmd
wsl --install -d Ubuntu --location "S:\WSL\VHDX\Ubuntu"
```

Альтернативный вариант, если хочешь явно зафиксировать текущий LTS:

```cmd
wsl --install -d Ubuntu-24.04 --location "S:\WSL\VHDX\Ubuntu"
```

### Шаг 4. После установки обновить WSL и проверить список дистрибутивов

```cmd
wsl --update
```

```cmd
wsl -l -v
```

### Шаг 5. Войти в Ubuntu

Если установлен дистрибутив `Ubuntu`:

```cmd
wsl -d Ubuntu
```

Если установлен дистрибутив `Ubuntu-24.04`:

```cmd
wsl -d Ubuntu-24.04
```

### Шаг 6. Внутри Ubuntu обновить пакеты

```bash
sudo apt update
```

```bash
sudo apt upgrade -y
```

```bash
sudo apt full-upgrade -y
```

```bash
sudo apt autoremove --purge -y
```

```bash
sudo apt autoclean
```

### Шаг 7. При необходимости запустить bootstrap

Базовый профиль Ubuntu:

```bash
/mnt/s/Audion-Linux-Bootstrap/Ubuntu-Desktop/bootstrap_ubuntu_minimal.sh
```

Расширенный профиль Ubuntu:

```bash
/mnt/s/Audion-Linux-Bootstrap/Ubuntu-Desktop/bootstrap_ubuntu_power.sh
```

---

## 7. Короткая логика без путаницы

### Только Windows

```cmd
wsl --install -d Ubuntu --location "S:\WSL\VHDX\Ubuntu"
```

```cmd
wsl --install -d Ubuntu-24.04 --location "S:\WSL\VHDX\Ubuntu"
```

```cmd
wsl --update
```

```cmd
wsl -l -v
```

```cmd
wsl -d Ubuntu
```

```cmd
wsl -d Ubuntu-24.04
```

### Уже внутри Ubuntu в WSL

```bash
sudo apt update
```

```bash
sudo apt upgrade -y
```

```bash
sudo apt full-upgrade -y
```

```bash
sudo apt autoremove --purge -y
```

```bash
sudo apt autoclean
```

```bash
sudo do-release-upgrade
```

### На обычных Linux Desktop

```bash
./Ubuntu-Desktop/bootstrap_ubuntu_minimal.sh
```

```bash
./Ubuntu-Desktop/bootstrap_ubuntu_power.sh
```

```bash
./Fedora-Desktop/bootstrap_fedora_minimal.sh
```

```bash
./Fedora-Desktop/bootstrap_fedora_power.sh
```

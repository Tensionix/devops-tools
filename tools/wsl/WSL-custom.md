## Микрогайд: установка Ubuntu 26.04 WSL из `.wsl` файла

Официальный Ubuntu WSL image — это root filesystem для установки через WSL; Ubuntu прямо описывает установку `.wsl` файла двойным кликом или командой `wsl --install --from-file <image>.wsl`. ([Ubuntu Documentation][1])
Microsoft также документирует базовые команды WSL: `wsl --version`, `wsl --update`, `wsl -l -v`, `wsl --set-default-version 2`, `--location`. ([Microsoft Learn][2])

### 1. Подготовка WSL

PowerShell от обычного пользователя обычно достаточно, но если WSL ещё не установлен — лучше открыть **PowerShell от администратора**.

```powershell
wsl --version

wsl --update

wsl --status

wsl --set-default-version 2
```

Если WSL вообще не включён:

```powershell
wsl --install --no-distribution
```

После этого — перезагрузка.

---

### 2. Проверка скачанного файла

Допустим, файл лежит тут:

```text
E:\Downloads\ubuntu-26.04-wsl-amd64.wsl
```

Проверяем хэш:

```powershell
Get-FileHash "E:\Downloads\ubuntu-26.04-wsl-amd64.wsl" -Algorithm SHA256
```

И сравниваем с официальным `SHA256SUMS` на странице релиза Ubuntu 26.04. Это особенно важно, если файл скачан не из Microsoft Store, а напрямую из архива/зеркала Ubuntu.

---

### 3. Установка в выбранную папку

Я бы ставил не в `%LOCALAPPDATA%`, а в нормальное место, например:

```powershell
New-Item -ItemType Directory -Force "E:\WSL\Ubuntu-26.04"
```

Потом:

```powershell
wsl --install --from-file "E:\Downloads\ubuntu-26.04-wsl-amd64.wsl" --location "E:\WSL\Ubuntu-26.04"
```

Если твоя версия WSL не примет `--location` вместе с `--from-file`, сначала обнови WSL:

```powershell
wsl --update
```

Потом повтори команду.

---

### 4. Проверка установки

```powershell
wsl -l -v
```

Должно появиться что-то вроде Ubuntu/Ubuntu-26.04 со статусом WSL 2.

Запуск:

```powershell
wsl -d Ubuntu-26.04
```

Название может отличаться. Смотри точное имя через:

```powershell
wsl -l -v
```

---

### 5. Первый запуск внутри Ubuntu

Внутри WSL:

```bash
sudo apt update

sudo apt full-upgrade

sudo apt install -y build-essential curl wget git ca-certificates gnupg lsb-release unzip zip nano mc htop
```

Создание нормального пользователя обычно предложит сам Ubuntu-первый запуск. Если вдруг ты попал под root, можно сделать вручную:

```bash
adduser audion

usermod -aG sudo audion
```

Потом в Windows создать/проверить файл:

```powershell
notepad "$env:USERPROFILE\.wslconfig"
```

Базовый спокойный вариант:

```ini
[wsl2]
memory=16GB
processors=8
swap=8GB
localhostForwarding=true
```

После изменения:

```powershell
wsl --shutdown
```

---

### 6. Сделать Ubuntu 26.04 WSL дистрибутивом по умолчанию

```powershell
wsl --set-default Ubuntu-26.04
```

И запускать просто:

```powershell
wsl
```

---

### 7. Где лежат файлы

Из Windows:

```text
\\wsl$\Ubuntu-26.04\
```

Лучше правило такое:

**Linux-проекты держать внутри WSL**:

```bash
/home/audion/projects
```

А не на `C:\` / `E:\`, потому что скорость и права файлов в Linux-папке обычно лучше.

---

### 8. Удаление, если что-то пошло не так

Посмотреть имя:

```powershell
wsl -l -v
```

Остановить:

```powershell
wsl --terminate Ubuntu-26.04
```

Удалить дистрибутив:

```powershell
wsl --unregister Ubuntu-26.04
```

Важно: `--unregister` удаляет Linux-систему и её данные.

---

### 9. Мини-бэкап перед экспериментами

Экспорт:

```powershell
wsl --export Ubuntu-26.04 "E:\WSL_Backups\Ubuntu-26.04-clean.tar"
```

Восстановление в новую папку:

```powershell
wsl --import Ubuntu-26.04-Restore "E:\WSL\Ubuntu-26.04-Restore" "E:\WSL_Backups\Ubuntu-26.04-clean.tar" --version 2
```

---

Мой практический вариант для тебя:

```text
E:\WSL\Ubuntu-26.04\
E:\WSL_Backups\
E:\Downloads\ubuntu-26.04-wsl-amd64.wsl
```

И сразу после чистой установки сделать экспорт `Ubuntu-26.04-clean.tar`. Это будет твоя “машина времени” для WSL.

2026-04-29 07:19:48

[1]: https://documentation.ubuntu.com/wsl/latest/howto/install-ubuntu-wsl2/?utm_source=chatgpt.com "Install Ubuntu on WSL 2"
[2]: https://learn.microsoft.com/en-us/windows/wsl/install?utm_source=chatgpt.com "How to install Linux on Windows with WSL"

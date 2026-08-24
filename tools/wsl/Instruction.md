Да, давай сделаем **нормально и по слоям**.

Тут есть **два разных типа обновления**:

1. **WSL в Windows** — обновляется командами `wsl ...` из **CMD / PowerShell от администратора**. Команды WSL в таком виде официально поддерживаются и в Command Prompt, и в PowerShell. Новые установки через `wsl --install` идут как WSL 2 по умолчанию. ([Microsoft Learn][1])

2. **Ubuntu внутри WSL** — обновляется уже **внутри Linux** через `apt` и, для перехода между релизами Ubuntu, через `do-release-upgrade`. Canonical отдельно различает обычные обновления пакетов и upgrade самого релиза. ([Ubuntu][2])

## 1) Команды Windows CMD / PowerShell (WSL-host)

Запускать **от имени администратора**.

### Проверка, что доступно

```cmd
wsl --status

wsl --version

wsl --list --online
```

`wsl --list --online` показывает точные имена доступных дистрибутивов для установки, и Ubuntu в своей документации прямо использует имя `Ubuntu-24.04` для установки Ubuntu 24.04 LTS. ([Microsoft Learn][1])

### Варианты установки

**Вариант A — дефолтная установка**

```cmd
wsl --install
```

**Вариант B — явная установка Ubuntu**

```cmd
wsl --install -d Ubuntu
```

**Вариант C — явная установка Ubuntu 24.04 LTS**

```cmd
wsl --install -d Ubuntu-24.04
```

**Вариант D — работа, установка Ubuntu в нужную папку**

```cmd
wsl --install -d Ubuntu --location "E:\WSL\VHDX\Ubuntu"
```

**Вариант E — дом, установка Ubuntu в нужную папку**

```cmd
wsl --install -d Ubuntu --location "S:\WSL\VHDX\Ubuntu"
```

**Вариант F — работа, установка именно Ubuntu 24.04 LTS в нужную папку**

```cmd
wsl --install -d Ubuntu-24.04 --location "E:\WSL\VHDX\Ubuntu-24.04"
```

**Вариант G — дом, установка именно Ubuntu 24.04 LTS в нужную папку**

```cmd
wsl --install -d Ubuntu-24.04 --location "S:\WSL\VHDX\Ubuntu-24.04"
```

Поддержка `--location` есть у `wsl --install`, а Ubuntu 24.04 LTS документирована Canonical как устанавливаемая через `wsl --install Ubuntu-24.04`; у Microsoft стандартная форма с выбором дистрибутива — `wsl --install -d <Distro>`. ([Microsoft Learn][1])

### После установки

```cmd
wsl --update

wsl --shutdown

wsl -l -v
```

`wsl --update` обновляет сам WSL, а `wsl -l -v` позволяет проверить, что дистрибутив установлен и работает на WSL 2. Microsoft также рекомендует Store-версию WSL для более быстрых обновлений. ([Microsoft Learn][1])

## 2) Команды уже внутри Ubuntu в WSL

Сначала входишь в Ubuntu:

```cmd
wsl -d Ubuntu
```

или, если ставил именно 24.04:

```cmd
wsl -d Ubuntu-24.04
```

А дальше уже **внутри Linux**:

### Обычное обновление пакетов в рамках текущего LTS

```bash
sudo apt update

sudo apt upgrade -y

sudo apt full-upgrade -y

sudo apt autoremove --purge -y

sudo apt autoclean
```

Это обычное обслуживание текущего релиза Ubuntu: обновление индексов пакетов, установка доступных обновлений и очистка лишнего. Canonical отдельно объясняет работу `apt upgrade` и phased updates. ([Ubuntu][3])

### Проверка версии Ubuntu

```bash
lsb_release -a
```

или:

```bash
cat /etc/os-release
```

## 3) Upgrade именно LTS → следующий LTS

Вот это уже **не просто update пакетов**, а **переход на новый релиз Ubuntu**.

### Перед release upgrade

```bash
sudo apt update

sudo apt full-upgrade -y

sudo reboot
```

### Сам переход на следующий LTS

```bash
sudo do-release-upgrade
```

Canonical рекомендует `do-release-upgrade` именно для перехода между релизами Ubuntu. Для LTS-ветки апгрейд на следующий LTS становится доступен после выхода point release нового LTS; сейчас Ubuntu 24.04.4 LTS уже существует, но следующий LTS — 26.04 — по дорожной карте выходит только 23 апреля 2026, так что на 15 марта 2026 прямого LTS→LTS апгрейда с 24.04 ещё нет. ([Ubuntu][2])

## 4) Практичная схема для тебя

### Работа, `E:\WSL`

**Windows CMD / Admin**

```cmd
wsl --list --online

wsl --install -d Ubuntu-24.04 --location "E:\WSL\VHDX\Ubuntu-24.04"

wsl --update

wsl -l -v
```

**Потом внутри Ubuntu**

```bash
sudo apt update

sudo apt upgrade -y

sudo apt full-upgrade -y

sudo apt autoremove --purge -y
```

### Дом, `S:\WSL`

**Windows CMD / Admin**

```cmd
wsl --list --online

wsl --install -d Ubuntu-24.04 --location "S:\WSL\VHDX\Ubuntu-24.04"

wsl --update

wsl -l -v
```

**Потом внутри Ubuntu**

```bash
sudo apt update

sudo apt upgrade -y

sudo apt full-upgrade -y

sudo apt autoremove --purge -y
```

## 5) Самое важное различие

**В Windows:**

```cmd
wsl --install ...
wsl --update
wsl -l -v
```

**Внутри Ubuntu:**

```bash
sudo apt update
sudo apt upgrade -y
sudo apt full-upgrade -y
sudo do-release-upgrade
```

То есть:

* `wsl ...` — это **установка и обслуживание слоя WSL в Windows**
* `apt ...` и `do-release-upgrade` — это **обслуживание самой Ubuntu внутри WSL**

Если хочешь, я сейчас сразу соберу это в **новые русские `Instruction-E.md` и `Instruction-S.md`**, уже без путаницы и с отдельными блоками **“CMD в Windows”** и **“команды внутри Ubuntu”**.

[1]: https://learn.microsoft.com/en-us/windows/wsl/basic-commands?utm_source=chatgpt.com "Basic commands for WSL"
[2]: https://ubuntu.com/server/docs/how-to/software/upgrade-your-release/?utm_source=chatgpt.com "How to upgrade your Ubuntu release"
[3]: https://ubuntu.com/server/docs/explanation/software/about-apt-upgrade-and-phased-updates/?utm_source=chatgpt.com "About apt upgrade and phased updates"

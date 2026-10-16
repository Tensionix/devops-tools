Cache Cleaner / Очистка кэшей (Windows)

EN
Frees the system drive from caches their programs refill on demand. No admin rights:
everything belongs to the current user, but the Windows Temp - it needs them and is
skipped without them.

Included:
- Invoke-CacheCleaner.ps1
- Clean.cmd (menu: audit / clean / clean + NuGet packages / Chrome model / Chrome model back /
  Temp / Premiere)

Targets:
- pip    %LOCALAPPDATA%\pip\cache
- npm    %LOCALAPPDATA%\npm-cache\_cacache
- nuget  NuGet v3-cache, http-cache, plugins-cache, %TEMP%\NuGetScratch;
         ~\.nuget\packages only with -NuGetPackages
- temp    %TEMP% entries untouched for 24 h (-TempAgeHours); files in use stay
- wintemp %SystemRoot%\Temp entries untouched for 24 h; needs administrator rights
- claude  %TEMP%\claude, the scratch of Claude Code: a session folder nothing was
          written in for 24 h; a session at work stays
- adobe  %APPDATA%\Adobe\Common\Media Cache Files, Media Cache, Peak Files, and the
         same folders where Premiere Pro moved them (HKCU\Software\Adobe\Common
         <version>\Media Cache: FolderPath, DatabasePath) - never the place they stand in;
         skipped while Premiere Pro, After Effects, Media Encoder or Audition runs
- chrome Chrome on-device AI model (User Data\OptGuideOnDeviceModel), only when named.
         Clean also sets the user policy HKCU\Software\Policies\Google\Chrome
         GenAILocalFoundationalModelSettings = 1, otherwise Chrome downloads it again.
         Chrome then shows "Managed by your organization". Undo: -ChromePolicyUndo.

Examples:
  Invoke-CacheCleaner.ps1                      measure only
  Invoke-CacheCleaner.ps1 -Mode Clean
  Invoke-CacheCleaner.ps1 -Mode Clean -Targets chrome
  Invoke-CacheCleaner.ps1 -Mode Clean -Targets temp,wintemp,claude
  Invoke-CacheCleaner.ps1 -Mode Clean -Targets adobe

Exit code: 0 done, 1 some files were in use and stayed, 2 unknown target.
GUI: OS Settings > Maintenance & Cleanup > Cache Cleaner.

RU
Освобождает системный диск от кэшей, которые программы сами наполнят снова. Права
администратора не нужны: всё принадлежит текущему пользователю, кроме Temp Windows -
без прав она пропускается.

Что чистится:
- pip, npm, http-кэш NuGet; папка пакетов ~\.nuget\packages — только с -NuGetPackages
  (следующая сборка скачает их заново);
- Temp пользователя и Temp Windows — записи старше суток, занятые файлы остаются;
- сессии Claude Code в %TEMP%\claude, в которых ничего не менялось сутки; рабочая
  сессия остаётся;
- медиакэш Adobe — в обычном месте и там, куда его перенесли в настройках Premiere;
  чистятся только папки самих кэшей; пропускается, пока открыты Premiere Pro,
  After Effects, Media Encoder или Audition;
- ИИ-модель Chrome — только по отдельной кнопке; ставит пользовательскую политику
  Chrome, чтобы модель не скачалась снова (Chrome покажет «Управляется вашей
  организацией»). Вернуть — -ChromePolicyUndo.

Без -Mode Clean ничего не меняется: только замер.
В окне: OS Settings > Обслуживание и очистка > Очистка кэшей.

Cache Cleaner / Очистка кэшей (Windows)

EN
Frees the system drive from caches their programs refill on demand. No admin rights:
everything belongs to the current user.

Included:
- Invoke-CacheCleaner.ps1
- Clean.cmd (menu: audit / clean / clean + NuGet packages / Chrome model / Chrome model back)

Targets:
- pip    %LOCALAPPDATA%\pip\cache
- npm    %LOCALAPPDATA%\npm-cache\_cacache
- nuget  NuGet v3-cache, http-cache, plugins-cache, %TEMP%\NuGetScratch;
         ~\.nuget\packages only with -NuGetPackages
- temp   %TEMP% entries untouched for 24 h (-TempAgeHours); files in use stay
- adobe  %APPDATA%\Adobe\Common\Media Cache Files, Media Cache, Peak Files;
         skipped while Premiere Pro, After Effects, Media Encoder or Audition runs
- chrome Chrome on-device AI model (User Data\OptGuideOnDeviceModel), only when named.
         Clean also sets the user policy HKCU\Software\Policies\Google\Chrome
         GenAILocalFoundationalModelSettings = 1, otherwise Chrome downloads it again.
         Chrome then shows "Managed by your organization". Undo: -ChromePolicyUndo.

Examples:
  Invoke-CacheCleaner.ps1                      measure only
  Invoke-CacheCleaner.ps1 -Mode Clean
  Invoke-CacheCleaner.ps1 -Mode Clean -Targets chrome

Exit code: 0 done, 1 some files were in use and stayed, 2 unknown target.
GUI: OS Settings > Maintenance & Cleanup > Cache Cleaner.

RU
Освобождает системный диск от кэшей, которые программы сами наполнят снова. Права
администратора не нужны: всё принадлежит текущему пользователю.

Что чистится:
- pip, npm, http-кэш NuGet; папка пакетов ~\.nuget\packages — только с -NuGetPackages
  (следующая сборка скачает их заново);
- Temp — записи старше суток, занятые файлы остаются;
- медиакэш Adobe — пропускается, пока открыты Premiere Pro, After Effects,
  Media Encoder или Audition;
- ИИ-модель Chrome — только по отдельной кнопке; ставит пользовательскую политику
  Chrome, чтобы модель не скачалась снова (Chrome покажет «Управляется вашей
  организацией»). Вернуть — -ChromePolicyUndo.

Без -Mode Clean ничего не меняется: только замер.
В окне: OS Settings > Обслуживание и очистка > Очистка кэшей.

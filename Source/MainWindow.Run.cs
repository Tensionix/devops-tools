using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using Avalonia.Controls;
using Avalonia.Media.Imaging;
using Avalonia.Threading;
using AudionDevOpsTools.Core;
using AudionDevOpsTools.Views;
using Page = AudionDevOpsTools.Core.Page;

namespace AudionDevOpsTools;

/// <summary>
/// A run: one operation at a time, started through the console command with what the form holds at
/// the moment of the press. A dangerous one is asked about first, in the words the console command
/// gives (`check` - the rules of the former window). Its course is read from the service lines of the
/// command. STOP asks the operation to stop - it stops itself where nothing is left half done; only an
/// operation that does not answer is ended.
/// </summary>
public partial class MainWindow
{
    string _runName = "";
    DateTime _started;
    readonly DispatcherTimer _clock = new() { Interval = TimeSpan.FromSeconds(1) };
    DoorEvent? _finish;
    bool _stopAsked, _stopAgain, _asking;
    DispatcherTimer? _killTimer, _againTimer;
    /// <summary>The operation that runs, and the page whose switches and lists it may have changed.</summary>
    Node? _running;
    PageView? _runningOn;
#if DEBUG
    static readonly int StopWaitSeconds = int.TryParse(Environment.GetEnvironmentVariable("AUDION_STOP_WAIT"), out var seconds) && seconds > 0 ? seconds : 60;
#else
    const int StopWaitSeconds = 60;
#endif

    /// <summary>One thing at a time: while it goes, nothing else starts.</summary>
    void ApplyBusy()
    {
        bool free = !_runner.Running && !_asking && _told is not null && Door.Ready;
        if (_view is { } view)
        {
            foreach (var button in view.RunButtons) button.IsEnabled = free;
            foreach (var button in view.SwitchButtons) button.IsEnabled = free;
        }
        foreach (var child in ServiceRow.Children.Concat(FolderTools.Children)) if (child is Button button) button.IsEnabled = free;
        StopButton.IsVisible = _runner.Running;
        StopButton.IsEnabled = _runner.Running && (!_stopAsked || _stopAgain);
    }

    /// <summary>The name of an operation with its place: "СЕТЬ → Ремонт → Обычный ремонт". Names repeat across pages.</summary>
    static string PathName(Node node) =>
        node.Page is { Section: { } section } page ? $"{section.Name} → {page.Name} → {node.Name}" : node.Name;

    /// <summary>The fields of an operation that hold a secret: their values are written as stars wherever the window shows them.</summary>
    static HashSet<string> SecretsOf(Node node) => node.Fields.Where(field => field.Password).Select(field => field.Id).ToHashSet();

    /// <summary>
    /// A press of a button that runs an operation. Everything the run needs is taken from the window
    /// here, before any question: the answer may come a minute later, and what is started is what was
    /// asked about.
    /// </summary>
    async void Press(Node node)
    {
        if (!node.Runs || _asking) return;
        if (_runner.Running) { SetStatus("Идёт другая операция."); return; }
        if (_told is null || !Door.Ready) return;
        // A value being typed is taken first: its box gives up the focus.
        Shell.Focus();

        // An operation of the working folders of the program is named no source and no target: it acts
        // on `input` and `output` of the program itself, whatever folders the rows show.
        bool own = _told.Layout.Folders.Contains(node);
        var target = own ? "" : _target;
        var source = own ? "" : _source;
        var held = _store.Of(node.Page);
        var values = held.ForDoor(node);
        var changed = held.ChangedOf(node);
        if (held.TooFew(node, field => _view?.Form.InSight(field) ?? true) is { } few)
        {
            SetStatus(Lang.F("«{0}»: отметьте не меньше {1}.", Form.NameOf(few), few.MinSelected));
            return;
        }
        if (!await MayRun(node, values, source, target, own ? FolderLines() : "")) return;
        Begin(node, target, values, changed, source: source);
    }

    /// <summary>
    /// What stands between a press and a run. A dangerous operation is checked by the console command
    /// first: whether the form may run as it stands - no browser ticked, no SMB pair - and, when the
    /// rules of the former window ask so, the question with what will happen. True - it may run now.
    /// </summary>
    async Task<bool> MayRun(Node node, string values, string source, string target, string more = "")
    {
        if (!node.Dangerous) return !_runner.Running && IsVisible;
        _asking = true;
        ApplyBusy();
        try
        {
            SetStatus("Проверяю форму…");
            var said = await Door.Check(node.Id, values, source, target);
            if (!said.Ok)
            {
                SetStatus(Lang.F("{0}: не запущено - {1}", node.Name, said.Error));
                await AskDialog.Ok(this, PathName(node), said.Error);
                return false;
            }
            if (said.Ask)
            {
                var lines = new List<string>();
                if (said.Description.Length > 0) lines.Add(said.Description);
                if (said.Risk.Length > 0) lines.Add(said.Risk);
                if (said.Notes.Count > 0)
                {
                    lines.Add("");
                    lines.Add(said.ImpactTitle);
                    lines.AddRange(said.Notes.Select(note => "• " + note));
                }
                if (more.Length > 0) { lines.Add(""); lines.Add(more); }
                if (node.Secret) { lines.Add(""); lines.Add(Lang.T("Экспорт содержит секреты: храните его как ключ.")); }
                if (said.Note.Length > 0) { lines.Add(""); lines.Add(said.Note); }
                var tone = node.Look == "burn" || node.RiskLevel == "destructive" ? "burn" : "";
                if (!await AskDialog.YesNo(this, Lang.F("Выполнить «{0}»?", PathName(node)), string.Join("\n", lines), tone)) { SetStatus("Отменено."); return false; }
            }
            SetStatus("Готово.");
            return !_runner.Running && IsVisible;
        }
        finally
        {
            _asking = false;
            ApplyBusy();
        }
    }

    /// <summary>The run that goes is a command of the terminal; whether its own words have begun, and whether they are over.</summary>
    bool _commandRun, _commandSaid, _commandOver;

    /// <summary>Of a command of the terminal only what the command itself said is shown; the frame of the engine stays in its log file.</summary>
    List<string> OnlyTheCommand(List<string> lines)
    {
        var said = new List<string>(lines.Count);
        foreach (var line in lines)
        {
            var text = System.Text.RegularExpressions.Regex.Replace(line, "\\x1b\\[[0-9;]*m", "");
            if (!_commandSaid)
            {
                if (text.StartsWith("[CMD] ", StringComparison.Ordinal) || text.StartsWith("── ", StringComparison.Ordinal)) _commandSaid = true;
                continue;
            }
            if (text.StartsWith("Traceback (most recent call last):", StringComparison.Ordinal)) _commandOver = true;
            if (_commandOver || text.StartsWith("[EXIT", StringComparison.Ordinal) || text.StartsWith("Finished operation:", StringComparison.Ordinal)) continue;
            said.Add(line);
        }
        return said;
    }

    void Begin(Node node, string target, string values, Dictionary<string, string> changed, string? name = null, string source = "", bool command = false)
    {
        _commandRun = command;
        _commandSaid = false;
        _commandOver = false;
        if (_sheet.Length > 0) ToggleSheet(_sheet);
        _runName = name ?? PathName(node);
        _started = DateTime.Now;
        _finish = null;
        _stopAsked = false;
        _stopAgain = false;
        _running = node;
        _runningOn = node.Page is { } page && _views.TryGetValue(KeyOf(page), out var view) ? view : null;
        _ansi.Reset();

        AppendLines(new[] { "", $"===== {_runName} =====" });
        // The same run as a person would type it; a password is stars - it goes by the file of the values.
        if (!command) AppendLines(new[] { Lang.T("[окно] ") + Door.RunLine(node.Id, source, target, changed, SecretsOf(node)) });
        if (Door.Prepare(values) is { Length: > 0 } trouble)
        {
            AppendLines(new[] { "[ERR] " + Lang.F("запуск не подготовлен: {0}", trouble) });
            SetStatus("Не запустилось: причина в терминале.");
            return;
        }
        if (_runner.Start(Door.Run(node.Id, source, target)) is { } failed)
        {
            Door.ForgetParams();
            AppendLines(new[] { "[ERR] " + Lang.F("не запустилось: {0}", failed) });
            SetStatus("Не запустилось: причина в терминале.");
            return;
        }

        RunNameText.Text = Upper(name ?? node.Name);
        RunNameText.Classes.Set("idle", false);
        OutcomeText.Text = Upper(Lang.T("идёт"));
        SetTone(OutcomeText, "quiet");
        SetStatus(_runName);
        ProgressBar.IsVisible = true;
        ProgressBar.IsIndeterminate = true;
        ShowClock();
        _clock.Start();
        ShowActivity("");
        ApplyBusy();
    }

    string _activity = "";

    void ShowActivity(string text, bool? shown = null)
    {
        _activity = text.Trim();
        bool runs = shown ?? _runner.Running;
        if (runs)
        {
            if (_activity.Length > 0) LiveLine.Paint(ActivityText, _activity);
            else LiveLine.Quiet(ActivityText, _runName + "…");
        }
        ActivityDot.Classes.Set("pulse", runs);
        ActivityRow.IsVisible = runs;
    }

    static void SetTone(TextBlock number, string tone)
    {
        foreach (var name in new[] { "idle", "good", "bad", "warn", "quiet" }) number.Classes.Set(name, name == tone);
    }

    // ------------------------------------------------------------ the course

    void OnOutput(IReadOnlyList<string> lines)
    {
        var plain = new List<string>(lines.Count);
        foreach (var line in lines)
        {
            if (Door.Read(line) is not { } said) { plain.Add(line); continue; }
            switch (said.Kind)
            {
                case "started":
                    // The values are in the hands of the command now: a password typed for the run is in no file from here on.
                    Door.ForgetParams();
                    break;
                case "progress":
                    ProgressBar.IsIndeterminate = said.Progress <= 0;
                    if (said.Progress > 0) ProgressBar.Value = Math.Max(2, Math.Min(100, said.Progress * 100));
                    break;
                case "activity":
                    ShowActivity(said.Activity);
                    break;
                case "finished":
                    _finish = said;
                    break;
            }
        }
        AppendLines(_commandRun ? OnlyTheCommand(plain) : plain, told: true);
    }

    void ShowClock()
    {
        var span = DateTime.Now - _started;
        ClockText.Text = span.TotalHours >= 1 ? span.ToString(@"h\:mm\:ss") : span.ToString(@"mm\:ss");
        ClockText.Classes.Set("idle", false);
    }

    // ------------------------------------------------------------ STOP

    void StopRun()
    {
        if (!_runner.Running) return;
        if (_stopAsked)
        {
            if (!_stopAgain) return;
            _stopAgain = false;
            _killTimer?.Stop();
            ApplyBusy();
            AppendLines(new[] { Lang.T("[окно] ") + Lang.T("СТОП нажат повторно: операция завершена принудительно") });
            _runner.Stop();
            return;
        }
        _stopAsked = true;
        ApplyBusy();
        AppendLines(new[] { Lang.T("[окно] ") + Lang.T("остановлено кнопкой СТОП: операция останавливается сама") });
        SetStatus(Lang.F("{0}: останавливается…", _runName));
        if (Door.AskToStop() is { Length: > 0 } trouble)
        {
            AppendLines(new[] { Lang.T("[окно] ") + Lang.F("сигнал остановки не записан ({0}): операция завершена принудительно", trouble) });
            _runner.Stop();
            return;
        }
        _killTimer = new DispatcherTimer { Interval = TimeSpan.FromSeconds(StopWaitSeconds) };
        _killTimer.Tick += (_, _) =>
        {
            _killTimer?.Stop();
            if (!_runner.Running) return;
            AppendLines(new[] { Lang.T("[окно] ") + Lang.F("операция не остановилась за {0} с: завершена принудительно", StopWaitSeconds) });
            _runner.Stop();
        };
        _killTimer.Start();
        _againTimer = new DispatcherTimer { Interval = TimeSpan.FromSeconds(3) };
        _againTimer.Tick += (_, _) =>
        {
            _againTimer?.Stop();
            if (!_runner.Running || !_stopAsked) return;
            _stopAgain = true;
            ApplyBusy();
        };
        _againTimer.Start();
    }

    // ------------------------------------------------------------ the end of a run

    void OnFinished(int code, bool stopped)
    {
        _clock.Stop();
        _killTimer?.Stop();
        _againTimer?.Stop();
        ShowClock();
        Door.ForgetParams();
        string outcome = stopped ? "stopped"
            : _finish is { Outcome.Length: > 0 } said ? said.Outcome
            : code == Door.ExitStopped ? "stopped"
            : code == Door.ExitUsage ? "refused"
            : code == Door.ExitDone ? "done" : "failed";
        var (word, tone) = outcome switch
        {
            "done" => ("готово", "good"),
            "stopped" => ("остановлено", "warn"),
            "refused" => ("отказ", "bad"),
            _ => ("ошибка", "bad"),
        };
        _ansi.Reset();
        AppendLines(new[] { $"===== {(outcome == "done" ? "OK" : outcome == "stopped" ? "STOPPED" : "FAILED")}: {_runName} · {ClockText.Text} =====" });
        if (_finish?.Message is { Length: > 0 } message && outcome is "failed" or "refused")
        {
            var exitCode = _commandRun ? System.Text.RegularExpressions.Regex.Match(message, @"exit code (-?\d+)") : System.Text.RegularExpressions.Match.Empty;
            AppendLines(new[] { "[ERR] " + (exitCode.Success ? Lang.F("код выхода {0}", exitCode.Groups[1].Value) : message) });
        }

        OutcomeText.Text = Upper(Lang.T(word));
        SetTone(OutcomeText, tone);
        ProgressBar.IsVisible = false;
        ShowActivity("", false);
        ShowDrives();
        SetStatus(outcome switch
        {
            "done" => Lang.F("Готово: {0}", _runName),
            "stopped" => Lang.F("Остановлено: {0}", _runName),
            "refused" => Lang.F("{0}: отказ до начала - причина в терминале.", _runName),
            _ => Lang.F("{0}: ошибка - подробности в терминале.", _runName),
        });

        // What the operation handed back to its form: a password stored is cleared from the field.
        if (_running is { } ran && Door.FieldUpdates() is { Count: > 0 } updates)
        {
            var held = _store.Of(ran.Page);
            foreach (var (id, value) in updates)
                if (ran.Fields.FirstOrDefault(field => field.Id == id) is { } field) held.Set(field, Values.TextOf(value));
        }
        // The machine may be in another state now, and a list about it another list: the switches of
        // the page are read again, its lists asked anew when it is next in sight.
        foreach (var view in _views.Values)
        {
            if (!view.Form.DropListsAfterRun()) continue;
            view.Stale = true;
            if (ReferenceEquals(view, _view)) RebuildSoon();
        }
        if (_runningOn is { Page.State: true } changedPage && ReferenceEquals(changedPage, _view)) AskState(changedPage);
        else if (_runningOn is { Page.State: true } other) other.State = null;
        _running = null;
        _runningOn = null;
        ApplyBusy();
        if (_closeAfterRun) Close();
        else NextCommand();
    }

    // ------------------------------------------------------------ the rights of the window

    void RestartElevated()
    {
        if (_runner.Running || _asking) { SetStatus("Идёт операция: перезапустить окно с правами можно, когда она закончится."); return; }
        if (SystemInfo.ElevatedStart() is not { } start) return;
        SaveWindow();
        OneWindow.Release();
        try
        {
            using var successor = System.Diagnostics.Process.Start(start);
        }
        catch (Exception)
        {
            OneWindow.Retake();
            SetStatus("Окно осталось с обычными правами.");
            return;
        }
        Close();
    }

    // ------------------------------------------------------------ the end of the window

    bool _closeAfterRun, _closeAsking;

    void OnClosing(object? sender, WindowClosingEventArgs e)
    {
        if (_runner.Running && e.CloseReason == WindowCloseReason.WindowClosing)
        {
            e.Cancel = true;
            if (!_closeAfterRun) AskToClose();
            return;
        }
        if (_runner.Running)
        {
            Door.AskToStop();
            _runner.StopForClose();
        }
        SaveWindow();
        KeepCommand();
        if (!_runner.Running) Paths.DropSession();
    }

    async void AskToClose()
    {
        if (_closeAsking) return;
        _closeAsking = true;
        try
        {
            var go = await AskDialog.YesNo(this, "Закрыть окно и остановить операцию?",
                Lang.F("Идёт «{0}».", _runName) + "\n" + Lang.T("Операция остановится сама в ближайшей безопасной точке. Окно закроется, когда она остановится."), "burn");
            if (!go) return;
            if (!_runner.Running) { Close(); return; }
            _closeAfterRun = true;
            StopRun();
        }
        finally { _closeAsking = false; }
    }

#if DEBUG
    // ------------------------------------------------------------ a check without a mouse

    /// <summary>
    /// The pictures of the window, page by page, into a folder: what a person is shown before any
    /// button is pressed. Nothing is run; the lists and the states a page asks for are waited for.
    /// </summary>
    async Task TakeShots(string folder)
    {
        Directory.CreateDirectory(folder);
        if (_told is null) { Save(Path.Combine(folder, "00-no-door.png")); Close(); return; }
        int number = 0;
        bool pages = Environment.GetEnvironmentVariable("AUDION_SHOT_PAGES") != "0";
        File.WriteAllLines(Path.Combine(folder, "badges.txt"), MachineRow.Children.OfType<Border>().Where(badge => badge.IsVisible)
            .Select(badge => "[" + ((badge.Child as TextBlock)?.Text ?? "") + "]" + (badge.Classes.Contains("warn") ? " (warn)" : "") + "\n    "
                + (ToolTip.GetTip(badge)?.ToString() ?? "").Replace("\n", "\n    ")));
        var only = (Environment.GetEnvironmentVariable("AUDION_SHOT_ONLY") ?? "").Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);
        int pause = Environment.GetEnvironmentVariable("AUDION_SHOT_WAIT") is { } wait && int.TryParse(wait, out var ms) ? ms : 1500;
        var timing = new List<string>();
        foreach (var section in _told.Layout.Sections)
            foreach (var page in section.Pages)
            {
                if (!pages) break;
                number++;
                if (only.Length > 0 && !only.Contains(page.Id) && !only.Contains(section.Id + "/" + page.Id)) continue;
                SelectSection(section);
                SelectPage(page);
                timing.Add($"{section.Id}/{page.Id}: built in {_builtIn:0} ms");
                await Task.Delay(pause);
                // A page waits for what the machine was found in and for the lists it asked for.
                for (int i = 0; i < 100 && _view is { } shown && (shown.StateAsking || shown.Form.Asking || _rebuildPosted); i++) await Task.Delay(200);
                await Task.Delay(200);
                Save(Path.Combine(folder, $"{number:00}-{section.Id}-{page.Id}.png"));
                // AUDION_SHOT_FULL=1: the whole page too, not only what the window shows of it - a check of a long page.
                if (Environment.GetEnvironmentVariable("AUDION_SHOT_FULL") == "1" && _view is { } whole) SaveWhole(whole.Cards, Path.Combine(folder, $"{number:00}-{section.Id}-{page.Id}-full.png"));
            }
        File.WriteAllLines(Path.Combine(folder, "timing.txt"), timing);
        if (Environment.GetEnvironmentVariable("AUDION_SHOT_STEPS") is { Length: > 0 } steps) await WalkSteps(folder, steps);
        if (Environment.GetEnvironmentVariable("AUDION_SHOT_LIVE") is { Length: > 0 } live)
        {
            AppendLines(SelfTest.ColouredLines, told: true);
            ShowActivity(live, true);
            await Task.Delay(350);
            Save(Path.Combine(folder, "91-live.png"));
            ShowActivity("", false);
        }
        if (Environment.GetEnvironmentVariable("AUDION_SHOT_SHEETS") == "1")
        {
            ToggleSheet("settings");
            await Task.Delay(700);
            Save(Path.Combine(folder, "95-settings.png"));
            ToggleSheet("about");
            await Task.Delay(700);
            Save(Path.Combine(folder, "96-about.png"));
            ToggleSheet("about");
        }
        Close();
    }

    void Save(string file) => Save(this, file);

    /// <summary>A control as it is laid out, whole - the cards of a page past the bottom of the window - on the ground of the window.</summary>
    void SaveWhole(Control control, string file)
    {
        double scale = RenderScaling;
        var size = new Avalonia.PixelSize((int)(control.Bounds.Width * scale), (int)(control.Bounds.Height * scale));
        if (size.Width <= 0 || size.Height <= 0) return;
        var ground = (control as Panel)?.Background;
        if (control is Panel panel && this.TryFindResource("AppBg", ActualThemeVariant, out var bg) && bg is Avalonia.Media.IBrush brush) panel.Background = brush;
        try
        {
            using var bitmap = new RenderTargetBitmap(size, new Avalonia.Vector(96 * scale, 96 * scale));
            bitmap.Render(control);
            using var picture = File.Create(file);
            bitmap.Save(picture, new PngBitmapEncoderOptions());
        }
        finally
        {
            if (control is Panel back) back.Background = ground;
        }
    }

    static void Save(Window window, string file)
    {
        double scale = window.RenderScaling;
        var size = new Avalonia.PixelSize((int)(window.Bounds.Width * scale), (int)(window.Bounds.Height * scale));
        using var bitmap = new RenderTargetBitmap(size, new Avalonia.Vector(96 * scale, 96 * scale));
        bitmap.Render(window);
        using var picture = File.Create(file);
        bitmap.Save(picture, new PngBitmapEncoderOptions());
    }
#endif
}

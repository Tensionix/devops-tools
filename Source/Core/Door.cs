using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;

namespace AudionDevOpsTools.Core;

/// <summary>What a short call of the console command answered.</summary>
public sealed record Reply(int Code, string Out, string Err)
{
    public bool Ok => Code == 0;
}

/// <summary>A service line of a run ("::devops::{...}"): the start, how far the work is, the one live line, the end.</summary>
public sealed class DoorEvent
{
    /// <summary>started, progress, activity or finished; "" for a line of a kind this window does not know.</summary>
    public string Kind { get; init; } = "";
    /// <summary>The share of the work done, 0..1.</summary>
    public double Progress { get; init; } = -1;
    /// <summary>The live line under the journal: what goes on right now; "" clears it.</summary>
    public string Activity { get; init; } = "";
    /// <summary>done, failed or stopped.</summary>
    public string Outcome { get; init; } = "";
    public string Message { get; init; } = "";
}

/// <summary>
/// The console command of the engine. A button of the window does nothing a console cannot: it runs
/// devops_cli.cmd with the words a person would type, and that line is written into the journal.
/// The window starts the Python of the project itself, the way the wrapper does - so a path is
/// quoted once, by the system, and not a second time by the rules of cmd. Which fields an operation
/// has, what their defaults are, which parameters a service gets, whether a question is asked first
/// - the console command alone knows (system_core\cli.py).
/// </summary>
public static class Door
{
    public const string Control = "::devops::";
    public const int ExitDone = 0, ExitFailed = 1, ExitUsage = 2, ExitStopped = 130;

    /// <summary>Why the command cannot be called, in the words of the window; "" when it can.</summary>
    public static string Trouble =>
        !File.Exists(Paths.DoorScript) ? Lang.F("нет файла: {0}", Paths.DoorScript)
        : Paths.Python.Length == 0 ? Lang.F("нет Python программы ({0}): сначала соберите окружение - builder_main.cmd", Path.Combine(Paths.Root, @"runtime\python.exe"))
        : "";

    public static bool Ready => Trouble.Length == 0;

    // What devops_cli.cmd does before it calls Python: UTF-8 everywhere (-X utf8 is PYTHONUTF8=1),
    // lines at once (-u), the command started as a file.
    static IEnumerable<string> Head => new[] { "-X", "utf8", "-u", Paths.DoorScript, "--language", Lang.Code == "ru" ? "ru" : "en" };

    public static string ParamsFile => Path.Combine(Paths.Session, "params.json");
    public static string ResultFile => Path.Combine(Paths.Session, "result.json");
    /// <summary>The stop signal: the file appears - the operation stops at its next safe point.</summary>
    public static string StopFile => Path.Combine(Paths.Session, "stop.flag");

    static string Quote(string value)
    {
        if (value.Length > 0 && value.IndexOfAny(new[] { ' ', '\t', '"', '&', '(', ')', '^', '=', ';', ',', '%', '!', '<', '>', '|' }) < 0) return value;
        var text = new StringBuilder("\"");
        int slashes = 0;
        foreach (var ch in value)
        {
            if (ch == '\\') { slashes++; continue; }
            if (ch == '"') text.Append('\\', slashes * 2 + 1).Append('"');
            else text.Append('\\', slashes).Append(ch);
            slashes = 0;
        }
        return text.Append('\\', slashes * 2).Append('"').ToString();
    }

    /// <summary>
    /// The same run as a person would type it: written into the journal at every start. A value
    /// that is a secret - a password - is written as stars: it went to the command by a file.
    /// </summary>
    public static string RunLine(string operation, string source, string target, IReadOnlyDictionary<string, string> changed, ISet<string>? secrets = null)
    {
        var words = new List<string> { Paths.DoorName, "run", "--operation", operation };
        if (source.Length > 0) { words.Add("--source"); words.Add(Paths.Short(source)); }
        if (target.Length > 0) { words.Add("--target"); words.Add(Paths.Short(target)); }
        foreach (var (name, value) in changed)
        {
            words.Add("--set");
            words.Add(name + "=" + (secrets is not null && secrets.Contains(name) && value.Length > 0 ? "***" : value));
        }
        return string.Join(" ", words.Select(Quote));
    }

    /// <summary>A run: the values of the fields go by a file - a text with quotes or a password is not for a command line.</summary>
    public static Launch Run(string operation, string source, string target)
    {
        var args = Head.Concat(new[] { "run", "--operation", operation }).ToList();
        args.AddRange(Folders(source, target));
        // The colours the services write their lines in come as they are: the terminal shows them (Core\Ansi.cs).
        args.AddRange(new[] { "--params", ParamsFile, "--result", ResultFile, "--cancel-file", StopFile, "--colours" });
        return new Launch { Exe = Paths.Python, Args = args };
    }

    /// <summary>The files of the last run are cleared away and the values of the new one written; the reason when that did not work.</summary>
    public static string Prepare(string valuesJson)
    {
        try
        {
            foreach (var file in new[] { ResultFile, StopFile })
                if (File.Exists(file)) File.Delete(file);
            File.WriteAllText(ParamsFile, valuesJson, new UTF8Encoding(false));
            return "";
        }
        catch (Exception ex) { return ex.Message; }
    }

    /// <summary>The values of the run leave the disk once it has begun: a password typed for it is in no file after.</summary>
    public static void ForgetParams()
    {
        try { if (File.Exists(ParamsFile)) File.Delete(ParamsFile); } catch { }
    }

    /// <summary>What the operation handed back to the form (`field_updates` of its outcome): a password cleared after it was stored.</summary>
    public static Dictionary<string, JsonElement> FieldUpdates()
    {
        try
        {
            if (!File.Exists(ResultFile)) return new();
            using var doc = JsonDocument.Parse(File.ReadAllText(ResultFile));
            if (doc.RootElement.TryGetProperty("data", out var data) && data.ValueKind == JsonValueKind.Object
                && data.TryGetProperty("field_updates", out var updates) && updates.ValueKind == JsonValueKind.Object)
                return updates.EnumerateObject().ToDictionary(item => item.Name, item => item.Value.Clone());
        }
        catch { }
        return new();
    }

    /// <summary>Asks the running operation to stop. "" when the signal is written; the reason when it could not be.</summary>
    public static string AskToStop()
    {
        try { File.WriteAllText(StopFile, DateTime.Now.ToString("O")); return ""; }
        catch (Exception ex) { return ex.Message.Length > 0 ? ex.Message : ex.GetType().Name; }
    }

    /// <summary>The service line of a run read; null when the line is an ordinary one.</summary>
    public static DoorEvent? Read(string line)
    {
        if (!line.StartsWith(Control, StringComparison.Ordinal)) return null;
        try
        {
            using var doc = JsonDocument.Parse(line[Control.Length..]);
            var root = doc.RootElement;
            static string Text(JsonElement owner, string name) => owner.TryGetProperty(name, out var v) && v.ValueKind == JsonValueKind.String ? v.GetString() ?? "" : "";
            if (root.TryGetProperty("started", out _)) return new DoorEvent { Kind = "started" };
            if (root.TryGetProperty("finished", out var finished))
                return new DoorEvent { Kind = "finished", Outcome = Text(finished, "outcome"), Message = Text(finished, "message") };
            if (root.TryGetProperty("progress", out var share) && share.ValueKind == JsonValueKind.Number)
                return new DoorEvent { Kind = "progress", Progress = share.GetDouble() };
            if (root.TryGetProperty("activity", out var activity) && activity.ValueKind == JsonValueKind.String)
                return new DoorEvent { Kind = "activity", Activity = activity.GetString() ?? "" };
            return new DoorEvent { Kind = "" };
        }
        catch { return new DoorEvent { Kind = "" }; }
    }

    static IEnumerable<string> Folders(string source, string target)
    {
        if (source.Length > 0) { yield return "--source"; yield return source; }
        if (target.Length > 0) { yield return "--target"; yield return target; }
    }

    // ------------------------------------------------------------ short calls

    /// <summary>
    /// A call that answers and ends - the description, a list of options, a check, a state: the
    /// command is run and its output read whole. Never throws: a command that could not be started
    /// answers with the code -1 and the reason.
    /// </summary>
    public static async Task<Reply> Call(IEnumerable<string> words, int timeoutMs = 180_000)
    {
        if (!Ready) return new Reply(-1, "", Trouble);
        var info = new ProcessStartInfo(Paths.Python)
        {
            UseShellExecute = false,
            CreateNoWindow = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            RedirectStandardInput = true,
            StandardOutputEncoding = Encoding.UTF8,
            StandardErrorEncoding = Encoding.UTF8,
            WorkingDirectory = Paths.Root,
        };
        foreach (var word in Head.Concat(words)) info.ArgumentList.Add(word);
        try
        {
            using var process = Process.Start(info) ?? throw new InvalidOperationException("the process was not created");
            try { process.StandardInput.Close(); } catch { }
            var output = process.StandardOutput.ReadToEndAsync();
            var errors = process.StandardError.ReadToEndAsync();
            var exited = process.WaitForExitAsync();
            if (await Task.WhenAny(exited, Task.Delay(timeoutMs)) != exited)
            {
                try { process.Kill(entireProcessTree: true); } catch { }
                return new Reply(-1, "", Lang.F("консольная команда не ответила за {0} с", timeoutMs / 1000));
            }
            var said = Task.WhenAll(output, errors);
            if (await Task.WhenAny(said, Task.Delay(5_000)) != said)
                return new Reply(process.ExitCode, output.IsCompletedSuccessfully ? output.Result : "", errors.IsCompletedSuccessfully ? errors.Result : "");
            return new Reply(process.ExitCode, await output, await errors);
        }
        catch (Exception ex) { return new Reply(-1, "", ex.Message); }
    }

    static string Lines(string text) => string.Join(" ", text.Split('\n').Select(line => line.Trim()).Where(line => line.Length > 0));

    /// <summary>The last line of an answer that is JSON: the command prints one, and a service may have printed before it.</summary>
    static string LastJson(string output) =>
        output.Split('\n').Select(line => line.Trim()).LastOrDefault(line => line.StartsWith('{')) ?? "";

    /// <summary>What the program is made of, or the reason it could not be told.</summary>
    public static async Task<(Described? Told, string Trouble)> Describe()
    {
        var reply = await Call(new[] { "describe" });
        if (!reply.Ok) return (null, Lines(reply.Err.Length > 0 ? reply.Err : reply.Out));
        try { return (Described.Parse(LastJson(reply.Out)), ""); }
        catch (Exception ex) { return (null, ex.Message); }
    }

    static int _asked;

    static string ValuesFile(string kind, string valuesJson)
    {
        var file = Path.Combine(Paths.Session, $"{kind}-{System.Threading.Interlocked.Increment(ref _asked)}.json");
        File.WriteAllText(file, valuesJson, new UTF8Encoding(false));
        return file;
    }

    /// <summary>The list of a field, asked of its provider with the values of the form and the working folders; the reason when there is no list.</summary>
    public static async Task<(List<Option> Options, string Trouble)> Options(string node, string field, string valuesJson, string source = "", string target = "", bool refresh = false)
    {
        string file = "";
        try
        {
            if (refresh && System.Text.Json.Nodes.JsonNode.Parse(valuesJson) is System.Text.Json.Nodes.JsonObject fresh)
            {
                fresh["_refresh_options"] = true;
                valuesJson = fresh.ToJsonString();
            }
            file = ValuesFile("options", valuesJson);
            var reply = await Call(new[] { "options", "--operation", node, "--field", field }.Concat(Folders(source, target)).Concat(new[] { "--params", file }));
            var json = LastJson(reply.Out);
            if (json.Length == 0) return (new List<Option>(), Lines(reply.Err.Length > 0 ? reply.Err : Lang.T("консольная команда не ответила")));
            using var doc = JsonDocument.Parse(json);
            var trouble = doc.RootElement.TryGetProperty("error", out var error) ? error.GetString() ?? "" : "";
            var options = doc.RootElement.TryGetProperty("options", out var list) ? Described.ParseOptions(list) : new List<Option>();
            return (options, trouble);
        }
        catch (Exception ex) { return (new List<Option>(), ex.Message); }
        finally { try { if (file.Length > 0) File.Delete(file); } catch { } }
    }

    /// <summary>
    /// Whether the form may run as it stands, and the question asked before it (`check`): the same
    /// rules the run applies, and the words the former window asked with.
    /// </summary>
    public static async Task<Checked> Check(string node, string valuesJson, string source, string target)
    {
        string file = "";
        try
        {
            file = ValuesFile("check", valuesJson);
            var reply = await Call(new[] { "check", "--operation", node }.Concat(Folders(source, target)).Concat(new[] { "--params", file }), 60_000);
            var json = LastJson(reply.Out);
            if (json.Length == 0) return new Checked { Ok = false, Error = Lines(reply.Err.Length > 0 ? reply.Err : Lang.T("консольная команда не ответила")) };
            return Described.Read<Checked>(json) ?? new Checked { Ok = false, Error = Lang.T("консольная команда не ответила") };
        }
        catch (Exception ex) { return new Checked { Ok = false, Error = ex.Message }; }
        finally { try { if (file.Length > 0) File.Delete(file); } catch { } }
    }

    /// <summary>The state of the machine for the switches of a page.</summary>
    public static async Task<PageState> State(string page)
    {
        var reply = await Call(new[] { "state", "--page", page }, 60_000);
        try
        {
            var json = LastJson(reply.Out);
            if (json.Length == 0) return new PageState { Page = page, Error = Lines(reply.Err.Length > 0 ? reply.Err : Lang.T("консольная команда не ответила")) };
            return Described.Read<PageState>(json) ?? new PageState { Page = page };
        }
        catch (Exception ex) { return new PageState { Page = page, Error = ex.Message }; }
    }

    /// <summary>The program pins no option of a list (no field names `pins`): a pin is refused in words.</summary>
    public static Task<string> Pin(string node, string field, string value, bool on) => Task.FromResult(Lang.T("закрепление не поддерживается"));

    /// <summary>The remembered SMB pairs: "save" with "computer|user", "forget" with a key, "clear". The pairs after it, or the reason.</summary>
    public static async Task<(List<Option> Records, string Trouble)> Smb(string verb, string value = "")
    {
        var words = new List<string> { "smb" };
        if (verb == "save") { words.Add("--save"); words.Add(value); }
        else if (verb == "forget") { words.Add("--forget"); words.Add(value); }
        else if (verb == "clear") words.Add("--clear");
        var reply = await Call(words, 30_000);
        try
        {
            using var doc = JsonDocument.Parse(LastJson(reply.Out));
            var records = doc.RootElement.TryGetProperty("records", out var list) ? Described.ParseOptions(list) : new List<Option>();
            bool ok = doc.RootElement.TryGetProperty("ok", out var done) && done.ValueKind == JsonValueKind.True;
            return (records, ok ? "" : Lang.T("запись не найдена"));
        }
        catch { return (new List<Option>(), reply.Err.Trim().Length > 0 ? reply.Err.Trim() : Lang.T("консольная команда не ответила")); }
    }
}

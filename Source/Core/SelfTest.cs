using System;
using System.Collections.Generic;
using System.Linq;
using System.Runtime.InteropServices;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Threading.Tasks;

namespace AudionDevOpsTools.Core;

/// <summary>
/// What --self-test checks once the window has been put together: the parts of the window that need
/// no screen - what the console command says of the program, the cards and the switches of its pages,
/// what the window hands the command for every operation, the line a run is written with, the colours
/// of the terminal. Each check answers with a line; one that failed is named on the error stream, and
/// the program ends with 2.
///
/// With --values-to "file" the window writes what it would hand the command for every operation with
/// its form untouched: tests\test_window_values.py builds the parameters of the services from it with
/// the model of the command and compares them with the record of the former window.
/// </summary>
public static class SelfTest
{
    /// <summary>Lines in the colours their writer gave them; a picture of the terminal is taken with the same lines.</summary>
    public static readonly string[] ColouredLines =
    {
        "\u001b[33m[WARN] yellow by its writer\u001b[0m and plain after it",
        "\u001b[1;36m── process 2 · AudionPs.exe · Audion_Network_Cleaner.ps1 -Mode Status ──\u001b[0m",
        "\u001b[32m[EXIT 0]\u001b[0m",
        "\u001b[31mred \u001b[32mgreen \u001b[34mblue \u001b[35mmagenta \u001b[90mgrey \u001b[97mwhite",
        "still white: the colour was left open\u001b[0m",
        "[OK] a line nobody coloured",
    };

    sealed class Report
    {
        public readonly List<string> Passed = new();
        public readonly List<string> Failed = new();

        public void Check(string name, bool good, string found = "")
        {
            if (good) Passed.Add(name);
            else Failed.Add(found.Length > 0 ? name + ": " + found : name);
        }
    }

    public static string ReportFile { get; set; } = "";
    public static string ValuesFile { get; set; } = "";
    public static bool JustBuilt { get; set; }

    public static bool Run()
    {
        var report = new Report();
        foreach (var check in new (string Name, Action<Report> Body)[]
        {
            ("version", Number),
            ("rights", Rights),
            ("describe", Describe),
            ("sections", Sections),
            ("cards", Cards),
            ("fields", Fields),
            ("values", ValuesSent),
            ("terminal", Terminal),
            ("run line", RunLine),
            ("colours", Colours),
            ("error stream", ErrorStream),
        })
        {
            try { check.Body(report); }
            catch (Exception error) { report.Failed.Add($"{check.Name}: {error.GetType().Name}: {error.Message}"); }
        }
        foreach (var line in report.Passed) try { Console.Out.WriteLine("ok   " + line); } catch { }
        foreach (var line in report.Failed) try { Console.Error.WriteLine("FAIL " + line); } catch { }
        if (ReportFile.Length > 0)
            try
            {
                System.IO.File.WriteAllLines(ReportFile, report.Passed.Select(line => "ok   " + line).Concat(report.Failed.Select(line => "FAIL " + line)), new System.Text.UTF8Encoding(false));
            }
            catch { }
        return report.Failed.Count == 0;
    }

    static void Number(Report report)
    {
        if (!JustBuilt) return;
        var built = typeof(SelfTest).Assembly.GetName().Version;
        var wanted = Paths.Version;
        var carried = built is null ? "" : $"{built.Major}.{built.Minor}.{built.Build}";
        report.Check("version: the executable carries the number of config\\version.json", wanted is not null && carried == wanted.Split('-', '+')[0], $"the executable {carried}, the file {wanted ?? "(unreadable)"}");
    }

    static void Rights(Report report)
    {
        var start = SystemInfo.ElevatedStart();
        report.Check("rights: the window starts itself again with the rights - the same program, from the folder of the project",
            start is not null && start.Verb == "runas" && start.UseShellExecute
            && string.Equals(start.FileName, Environment.ProcessPath, StringComparison.OrdinalIgnoreCase)
            && string.Equals(start.WorkingDirectory, Paths.Root, StringComparison.OrdinalIgnoreCase),
            start is null ? "no start" : $"{start.FileName} | {start.Verb} | {start.WorkingDirectory}");
    }

    static Described? _told;

    static void Describe(Report report)
    {
        var (told, trouble) = Task.Run(Door.Describe).GetAwaiter().GetResult();
        report.Check("describe: the console command answered and the answer reads", told is not null, trouble);
        if (told is null) return;
        _told = told;
        var places = told.Operations().ToList();
        var nameless = places.Where(node => node.Id.Length == 0 || node.Title.Length == 0).Select(node => node.Id.Length > 0 ? node.Id : "(no id)").ToList();
        report.Check($"describe: each of the {places.Count} places of operations has a node and a name", places.Count > 0 && nameless.Count == 0, string.Join(", ", nameless));
        var twice = places.GroupBy(node => node.Id).Where(group => group.Count() > 1).Select(group => group.Key).ToList();
        report.Check("describe: no operation stands in the window twice", twice.Count == 0, string.Join(", ", twice));
        var formless = places.Where(node => node.Form.Length > 0 && node.Fields.Count == 0).Select(node => node.Id).ToList();
        report.Check($"describe: the {told.Forms.Count} forms told once are put together", told.Forms.Count > 0 && formless.Count == 0, string.Join(", ", formless));
        var homeless = told.Layout.Sections.SelectMany(section => section.Pages).SelectMany(page => page.Operations())
            .Where(node => node.Page?.Section is null || node.Card is null).Select(node => node.Id).ToList();
        report.Check("describe: every operation of a page knows its page, its section and its card", homeless.Count == 0, string.Join(", ", homeless));
    }

    /// <summary>The rule of the owner, 15.10.2026: every section has its line under its name and pages inside it.</summary>
    static void Sections(Report report)
    {
        if (_told is not { } told) return;
        var ids = string.Join(",", told.Layout.Sections.Select(section => section.Id));
        report.Check("sections: six sections by the subject of the work", ids == "network,wsl,drivers,defaults,transfer,system", ids);
        foreach (var language in new[] { "ru", "en" })
        {
            Lang.Set(language);
            var bare = told.Layout.Sections.Where(section => section.Name.Length == 0 || section.Line.Length == 0 || section.Pages.Count < 2).Select(section => section.Id).ToList();
            report.Check($"sections: every section has a name, a line under it and at least two pages [{language}]", bare.Count == 0, string.Join(", ", bare));
            var nameless = told.Layout.Sections.SelectMany(section => section.Pages).Where(page => page.Name.Length == 0).Select(ValueStore.KeyOf).ToList();
            report.Check($"sections: every page has a name [{language}]", nameless.Count == 0, string.Join(", ", nameless));
        }
        Lang.Set("ru");
    }

    static void Cards(Report report)
    {
        if (_told is not { } told) return;
        var cards = told.Layout.Sections.SelectMany(section => section.Pages).SelectMany(page => page.Cards).ToList();
        var odd = cards.Where(card => card.Kind is not ("op" or "switch" or "pick")).Select(card => card.Id).ToList();
        report.Check($"cards: each of the {cards.Count} cards is an operation, a switch or a pick", odd.Count == 0, string.Join(", ", odd));
        var switches = cards.Where(card => card.Kind == "switch").ToList();
        var badStates = switches.Where(card => card.State.Length == 0 || card.Operations.Count < 2 || card.Operations.Any(node => node.Is.Length == 0)
            || card.Operations.Select(node => node.Is).Distinct().Count() != card.Operations.Count).Select(card => card.Id).ToList();
        report.Check($"cards: each of the {switches.Count} switches names its states, one per operation", switches.Count > 0 && badStates.Count == 0, string.Join(", ", badStates));
        var noState = told.Layout.Sections.SelectMany(section => section.Pages).Where(page => page.Cards.Any(card => card.Kind == "switch") && !page.State).Select(ValueStore.KeyOf).ToList();
        report.Check("cards: a page with switches asks for the state of the machine", noState.Count == 0, string.Join(", ", noState));
        var picks = cards.Where(card => card.Kind == "pick").ToList();
        report.Check($"cards: each of the {picks.Count} picks opens on its first operation", picks.Count > 0 && picks.All(card => card.Chosen == card.Operations[0].Id && card.FormOf == card.Operations[0]),
            string.Join(", ", picks.Select(card => card.Id + "=" + card.Chosen)));
        // The answer of `state` reads into what lights the switches.
        var said = Described.Read<PageState>("{\"page\": \"dns\", \"switches\": {\"resolver\": {\"is\": \"cloudflare\", \"detail\": \"Wi-Fi · 1.1.1.1\", \"pending\": \"\", \"note\": \"\"}}}");
        report.Check("cards: the answer of the state reads", said?.Switches["resolver"].Is == "cloudflare" && said.Switches["resolver"].Detail.StartsWith("Wi-Fi"), said?.Page ?? "nothing");
    }

    static void Fields(Report report)
    {
        if (_told is not { } told) return;
        var fields = told.Operations().SelectMany(node => node.Fields).GroupBy(field => field.Id).Select(group => group.First()).ToList();
        var unknown = fields.Where(field => field.Drawn && !FieldKinds.Known.Contains(field.Kind)).Select(field => field.Id + ":" + field.Kind).ToList();
        report.Check($"fields: each of the {fields.Count} fields is of a kind the window draws", unknown.Count == 0, string.Join(", ", unknown));
        var routed = fields.Where(field => field.Routed).ToList();
        report.Check($"fields: {routed.Count} folders of the workbench are filled by the command, not drawn", routed.Count > 0 && routed.All(field => field.Route is "source" or "target" && !field.Drawn),
            string.Join(", ", routed.Where(field => field.Route is not ("source" or "target")).Select(field => field.Id)));
        var secrets = fields.Where(field => field.Password).Select(field => field.Id).OrderBy(id => id, StringComparer.Ordinal).ToList();
        report.Check("fields: the four passwords are fields of a secret", string.Join(",", secrets) == "linux_password,pfx_password,wifi_main_password,wifi_second_password", string.Join(",", secrets));
        var bookmarks = told.Operations().FirstOrDefault(node => node.Id == "browser_bookmarks_transfer_master");
        report.Check("fields: the form of the bookmarks carries the values the former window kept beside the manifest",
            bookmarks is not null && bookmarks.Fields.Any(field => field.Id == "bookmark_source") && bookmarks.Fields.Any(field => field.Id == "bookmark_browsers")
            && bookmarks.Fields.All(field => field.Id != "browser_profile"),
            bookmarks is null ? "no such operation" : string.Join(",", bookmarks.Fields.Select(field => field.Id)));
    }

    /// <summary>
    /// What the window hands the command for every operation, the form untouched: JSON of the fields by
    /// their ids, no folder of the workbench in it, the SMB login an object. Written to --values-to.
    /// </summary>
    static void ValuesSent(Report report)
    {
        if (_told is not { } told) return;
        var store = new ValueStore(told.Layout.Shared);
        var all = new JsonObject();
        var bad = new List<string>();
        foreach (var page in told.Layout.Sections.SelectMany(section => section.Pages))
        {
            var values = store.Open(page);
            foreach (var node in page.Operations())
            {
                var json = values.ForDoor(node);
                JsonNode? read;
                try { read = JsonNode.Parse(json); }
                catch (Exception error) { bad.Add($"{node.Id}: {error.Message}"); continue; }
                if (read is not JsonObject sent) { bad.Add(node.Id + ": not an object"); continue; }
                foreach (var field in node.Fields.Where(field => field.Routed))
                    if (sent.ContainsKey(field.Id)) bad.Add($"{node.Id}: hands the folder {field.Id}");
                foreach (var field in node.Fields.Where(field => field.Kind == "smb_login_cache"))
                    if (sent[field.Id] is not JsonObject) bad.Add($"{node.Id}: the SMB login is no object");
                all[node.Id] = sent.DeepClone();
            }
        }
        foreach (var node in told.Layout.Folders.Concat(told.Layout.Service))
            all[node.Id] = JsonNode.Parse(store.Window.ForDoor(node));
        report.Check($"values: what the window hands the command reads for each of the {all.Count} operations", bad.Count == 0, string.Join("; ", bad.Take(8)));
        if (ValuesFile.Length > 0)
            System.IO.File.WriteAllText(ValuesFile, all.ToJsonString(new JsonSerializerOptions { WriteIndented = true, Encoder = System.Text.Encodings.Web.JavaScriptEncoder.UnsafeRelaxedJsonEscaping }), new System.Text.UTF8Encoding(false));
    }

    static void Terminal(Report report)
    {
        var memory = new TerminalMemory();
        foreach (var command in new[] { "one", "two", "three", "two" }) memory.Used(command);
        report.Check("terminal: a command that was run stands first in the history, once", string.Join(",", memory.History) == "two,three,one", string.Join(",", memory.History));
        var operation = _told?.CardOperations.FirstOrDefault(node => node.Id == "terminal_command");
        report.Check("terminal: the program describes the operation a command runs by - a shell, a command, a folder",
            operation is not null && operation.Runs && string.Join(",", operation.Fields.Select(field => field.Id)) == "shell,command,cwd",
            operation is null ? "no such operation" : string.Join(",", operation.Fields.Select(field => field.Id)));
    }

    [DllImport("shell32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    static extern IntPtr CommandLineToArgvW(string line, out int count);

    [DllImport("kernel32.dll")]
    static extern IntPtr LocalFree(IntPtr memory);

    static List<string> Words(string line)
    {
        var words = new List<string>();
        var raw = CommandLineToArgvW(line, out int count);
        if (raw == IntPtr.Zero) return words;
        try
        {
            for (int i = 0; i < count; i++) words.Add(Marshal.PtrToStringUni(Marshal.ReadIntPtr(raw, i * IntPtr.Size)) ?? "");
        }
        finally { LocalFree(raw); }
        return words;
    }

    static void RunLine(Report report)
    {
        var values = new Dictionary<string, string>
        {
            ["plain"] = "word",
            ["space"] = "two words",
            ["quote"] = "say \"yes\" twice",
            ["slash_end"] = @"C:\Some Folder\",
            ["empty"] = "",
            ["signs"] = "a&b|c<d>e^f",
            ["wifi_main_password"] = "never shown",
        };
        var target = @"D:\Out Put\";
        var source = @"E:\Some Source\";
        var line = Door.RunLine("network_backup", source, target, values, new HashSet<string> { "wifi_main_password" });
        var expected = new List<string> { Paths.DoorName, "run", "--operation", "network_backup", "--source", Paths.Short(source), "--target", Paths.Short(target) };
        foreach (var (name, value) in values) { expected.Add("--set"); expected.Add(name + "=" + (name == "wifi_main_password" ? "***" : value)); }
        var read = Words(line);
        var wrong = Enumerable.Range(0, Math.Max(expected.Count, read.Count))
            .Where(i => i >= expected.Count || i >= read.Count || expected[i] != read[i])
            .Select(i => $"word {i}: wanted <{(i < expected.Count ? expected[i] : "")}> read <{(i < read.Count ? read[i] : "")}>").ToList();
        report.Check("run line: read back word for word - a space, a quote, a backslash at the end; a password is stars", wrong.Count == 0 && !line.Contains("never shown"), string.Join("; ", wrong) + " | " + line);
        var launch = Door.Run("network_backup", source, target);
        report.Check("run line: the values go to the command by a file, never as words of its line", launch.Args.Contains("--params") && !launch.Args.Any(word => word.Contains("never shown")), string.Join(" ", launch.Args));
    }

    static void ErrorStream(Report report)
    {
        var read = new[] { "a plain word", "[ERR] named an error by its writer", "", "[ERROR] another word of the writer" }.Select(Runner.ErrorLine).ToArray();
        var expected = new[] { "[ERR] a plain word", "[ERR] named an error by its writer", "[ERR] ", "[ERR] [ERROR] another word of the writer" };
        report.Check("error stream: a line is marked [ERR] once", read.SequenceEqual(expected), string.Join(" ~ ", read));
    }

    static void Colours(Report report)
    {
        static string Piece((string Text, Hue Hue) part) =>
            part.Text + "|" + (part.Hue.Own is { } own ? $"#{own.R:x2}{own.G:x2}{own.B:x2}" + (own.A < 255 ? "/" + own.A : "") : part.Hue.Key)
            + (part.Hue.Bold ? "|bold" : "") + (part.Hue.Underline ? "|underline" : "");
        var ansi = new Ansi();
        var frame = ansi.Read(ColouredLines[1], out var frameText).Select(Piece).ToArray();
        report.Check("colours: the frame of a process is one bold line in its colour", frame.Length == 1 && frame[0].EndsWith("|bold") && frameText.StartsWith("── process 2"), string.Join(" ~ ", frame));
        var exit = ansi.Read(ColouredLines[2], out var exitText).Select(Piece).ToArray();
        report.Check("colours: the exit code of a process is in the colour of how it ended", exit.Length == 1 && !exit[0].EndsWith("LogPlain") && exitText == "[EXIT 0]", string.Join(" ~ ", exit));
        var warn = ansi.Read(ColouredLines[0], out var warnText).Select(Piece).ToArray();
        report.Check("colours: a line keeps the colour its writer gave it and no other", warn.Length == 2 && warn[1] == " and plain after it|LogPlain" && warnText == "[WARN] yellow by its writer and plain after it", string.Join(" ~ ", warn));
        ansi.Read("\u001b[31mopen", out _);
        ansi.Reset();
        var after = ansi.Read("next run", out _).Select(Piece).ToArray();
        report.Check("colours: a colour left open does not outlive the run", after.SequenceEqual(new[] { "next run|LogPlain" }), string.Join(" ~ ", after));
    }
}

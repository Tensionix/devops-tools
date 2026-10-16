using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace AudionDevOpsTools.Core;

/// <summary>
/// What the console command tells of the program (devops_cli.cmd describe): the sections of the
/// window, their pages, the cards of every page with their operations and fields. The window draws
/// by it and knows no section and no operation by its name: what stands where is
/// config\window_layout.yaml, what an operation is - config\tool_manifest.yaml.
/// </summary>
public sealed class Described
{
    public string Version { get; set; } = "";
    public ProjectPaths Paths { get; set; } = new();
    public Layout Layout { get; set; } = new();
    /// <summary>The operations no page carries: the command line of the terminal.</summary>
    public List<Node> CardOperations { get; set; } = new();
    /// <summary>The forms, each told once: a name and its fields (operation_model.share_forms); put together in Parse.</summary>
    public Dictionary<string, List<Field>> Forms { get; set; } = new();

    static readonly JsonSerializerOptions Json = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
        PropertyNameCaseInsensitive = true,
        NumberHandling = JsonNumberHandling.AllowReadingFromString,
    };

    /// <summary>The answer of "describe" read; an answer that is no description throws.</summary>
    public static Described Parse(string json)
    {
        var told = JsonSerializer.Deserialize<Described>(json, Json) ?? throw new JsonException("the console command gave no description");
        foreach (var section in told.Layout.Sections)
            foreach (var page in section.Pages)
            {
                page.Section = section;
                foreach (var card in page.Cards)
                {
                    card.Page = page;
                    if (card.Kind == "pick" && card.Operations.Count > 0) card.Chosen = card.Operations[0].Id;
                    foreach (var node in card.Operations.Concat(card.Guests))
                    {
                        node.Page = page;
                        node.Card = card;
                    }
                }
            }
        // The fields of an operation: those of the form it names. The fields are the same objects
        // wherever the form stands; the list is the operation's own.
        foreach (var node in told.Operations().Concat(told.CardOperations))
        {
            if (node.Fields.Count > 0 || node.Form.Length == 0) continue;
            if (!told.Forms.TryGetValue(node.Form, out var form)) throw new JsonException($"the operation {node.Id} names a form the description does not have: {node.Form}");
            node.Fields = form.ToList();
        }
        return told;
    }

    public static List<Option> ParseOptions(JsonElement list) =>
        JsonSerializer.Deserialize<List<Option>>(list.GetRawText(), Json) ?? new List<Option>();

    public static T? Read<T>(string json) => JsonSerializer.Deserialize<T>(json, Json);

    /// <summary>Everything that has a button: the operations of the pages, then those of the header, then those beside the working folders.</summary>
    public IEnumerable<Node> Operations() =>
        Layout.Sections.SelectMany(section => section.Pages).SelectMany(page => page.Operations()).Concat(Layout.Service).Concat(Layout.Folders);
}

/// <summary>The folders of the project, as the console command resolves them.</summary>
public sealed class ProjectPaths
{
    public string Root { get; set; } = "";
    public string Input { get; set; } = "";
    public string Output { get; set; } = "";
    public string Backup { get; set; } = "";
    public string Logs { get; set; } = "";
    public string Report { get; set; } = "";
    public string Config { get; set; } = "";
    public string Workspace { get; set; } = "";
}

public sealed class Layout
{
    public List<Section> Sections { get; set; } = new();
    /// <summary>The operations of the program itself: small buttons of the header.</summary>
    public List<Node> Service { get; set; } = new();
    /// <summary>
    /// The operations of the working folders of the program: beside the rows SOURCE and TARGET.
    /// They run on `input` and `output` of the program itself, and the question before one names both.
    /// </summary>
    public List<Node> Folders { get; set; } = new();
    /// <summary>The fields whose value is one for the whole window; every other field belongs to its page.</summary>
    public List<string> Shared { get; set; } = new();
}

/// <summary>A section of the window: a large button of the row under the header.</summary>
public sealed class Section
{
    public string Id { get; set; } = "";
    public string Title { get; set; } = "";
    public string TitleRu { get; set; } = "";
    public string Icon { get; set; } = "";
    public string About { get; set; } = "";
    public string AboutRu { get; set; } = "";
    public List<Page> Pages { get; set; } = new();

    [JsonIgnore] public string Name => Words.Pick(TitleRu, Title);
    [JsonIgnore] public string Line => Words.Pick(AboutRu, About);
}

/// <summary>A page of a section: one of the row under the sections, with its cards.</summary>
public sealed class Page
{
    public string Id { get; set; } = "";
    public string Title { get; set; } = "";
    public string TitleRu { get; set; } = "";
    public string Icon { get; set; } = "";
    public string About { get; set; } = "";
    public string AboutRu { get; set; } = "";
    /// <summary>The operations of the page read a file or a folder of SOURCE.</summary>
    public bool Source { get; set; }
    /// <summary>The page has switches of the state of the machine: the console command is asked (`state --page`).</summary>
    public bool State { get; set; }
    /// <summary>Fields of the whole window its operations read but another page sets: not drawn here (the Wi-Fi adapter - on WI-FI).</summary>
    public List<string> Away { get; set; } = new();
    public List<Card> Cards { get; set; } = new();

    [JsonIgnore] public Section? Section { get; set; }
    [JsonIgnore] public string Name => Words.Pick(TitleRu, Title);
    [JsonIgnore] public string Line => Words.Pick(AboutRu, About);

    public IEnumerable<Node> Operations() => Cards.SelectMany(card => card.Operations.Concat(card.Guests));
}

/// <summary>
/// A card of a page. `op` - an operation with its form and the buttons of its guests; `switch` - a
/// row of operations, each bringing the machine into one state, the one in force lit; `pick` - a
/// row choosing the operation the one run button of the card starts.
/// </summary>
public sealed class Card
{
    public string Kind { get; set; } = "op";
    public string Id { get; set; } = "";
    /// <summary>What the state of the switch is read as (the key of `state --page`).</summary>
    public string State { get; set; } = "";
    public string Block { get; set; } = "";
    public string BlockRu { get; set; } = "";
    public string Icon { get; set; } = "";
    public string Tone { get; set; } = "";
    public string Title { get; set; } = "";
    public string TitleRu { get; set; } = "";
    public string About { get; set; } = "";
    public string AboutRu { get; set; } = "";
    /// <summary>The host of an `op` card; the row of a switch or a pick.</summary>
    public List<Node> Operations { get; set; } = new();
    public List<Node> Guests { get; set; } = new();

    [JsonIgnore] public Page? Page { get; set; }
    /// <summary>The operation of a pick that is on.</summary>
    [JsonIgnore] public string Chosen { get; set; } = "";
    [JsonIgnore] public string BlockName => Words.Pick(BlockRu, Block);
    [JsonIgnore] public string Name => Words.Pick(TitleRu, Title);

    /// <summary>The operation whose form the card draws: the host, the first of a switch, the chosen one of a pick.</summary>
    [JsonIgnore]
    public Node? FormOf => Kind == "pick" ? Operations.FirstOrDefault(node => node.Id == Chosen) ?? Operations.FirstOrDefault() : Operations.FirstOrDefault();
}

/// <summary>An operation as it stands on a page: what a button runs.</summary>
public sealed class Node
{
    public string Id { get; set; } = "";
    public string Title { get; set; } = "";
    public string TitleRu { get; set; } = "";
    public string Description { get; set; } = "";
    public string DescriptionRu { get; set; } = "";
    public string Tooltip { get; set; } = "";
    public string TooltipRu { get; set; } = "";
    /// <summary>"safe" or "dangerous": a dangerous one is asked about (the question is the console command's: `check`).</summary>
    public string Kind { get; set; } = "";
    public string RiskLevel { get; set; } = "";
    public string ActionTone { get; set; } = "";
    public string Icon { get; set; } = "";
    public string Tone { get; set; } = "";
    /// <summary>What the layout gives the place of the operation: its name, sign and tone there.</summary>
    public string PlaceTitle { get; set; } = "";
    public string PlaceTitleRu { get; set; } = "";
    public string PlaceIcon { get; set; } = "";
    public string PlaceTone { get; set; } = "";
    /// <summary>The state of the machine the operation brings it to, in a switch.</summary>
    public string Is { get; set; } = "";
    public bool Runs { get; set; }
    /// <summary>Runs and has no field to draw: a button is all it needs.</summary>
    public bool Direct { get; set; }
    public Dictionary<string, JsonElement> Parameters { get; set; } = new();
    public string Form { get; set; } = "";
    public List<Field> Fields { get; set; } = new();

    [JsonIgnore] public Page? Page { get; set; }
    [JsonIgnore] public Card? Card { get; set; }
    [JsonIgnore] public string Name => Words.Pick(PlaceTitleRu, PlaceTitle) is { Length: > 0 } placed ? placed : Words.Pick(TitleRu, Title);
    /// <summary>The name of the operation as the manifest gives it, whatever its place calls it.</summary>
    [JsonIgnore] public string OwnName => Words.Pick(TitleRu, Title);
    [JsonIgnore] public string About => Words.Pick(DescriptionRu, Description);
    [JsonIgnore] public string Tip => Words.Pick(TooltipRu, Tooltip);
    [JsonIgnore] public string Sign => PlaceIcon.Length > 0 ? PlaceIcon : Icon;
    [JsonIgnore] public string Look => PlaceTone.Length > 0 ? PlaceTone : Tone;
    [JsonIgnore] public bool Dangerous => Kind == "dangerous";
    /// <summary>It hands a secret out: keys, passwords, a bundle of access.</summary>
    [JsonIgnore] public bool Secret => RiskLevel == "secret_export";
}

public sealed class Field
{
    public string Id { get; set; } = "";
    /// <summary>The kind as the manifest names it: `type` of the manifest, told as `kind`.</summary>
    public string Kind { get; set; } = "";
    public string Display { get; set; } = "";
    public JsonElement Default { get; set; }
    /// <summary>The block of the form the field stands in: `group` of the manifest.</summary>
    public string Group { get; set; } = "";
    public bool Advanced { get; set; }
    /// <summary>A list of ticks laid out by the groups of its options, a block under each name (`group_blocks`): the apps of Microsoft by what they take.</summary>
    public bool GroupBlocks { get; set; }
    /// <summary>"source" or "target": the field is filled from the working folder of that name and is not drawn.</summary>
    public string Route { get; set; } = "";
    public string Label { get; set; } = "";
    public string LabelRu { get; set; } = "";
    public string Hint { get; set; } = "";
    public string HintRu { get; set; } = "";
    public string Tooltip { get; set; } = "";
    public string TooltipRu { get; set; } = "";
    public string Placeholder { get; set; } = "";
    /// <summary>The placeholder in Russian; the Russian window showed the English one (the review of 16.10.2026).</summary>
    public string PlaceholderRu { get; set; } = "";
    [JsonIgnore] public string Prompt => Words.Pick(PlaceholderRu, Placeholder);
    public double? Min { get; set; }
    public double? Max { get; set; }
    public double? Step { get; set; }
    public int MinSelected { get; set; }
    public int Rows { get; set; }
    public bool Hidden { get; set; }
    public Dictionary<string, JsonElement>? VisibleWhen { get; set; }
    public Dictionary<string, JsonElement>? HiddenWhen { get; set; }
    public List<Option> Options { get; set; } = new();
    public string OptionsSource { get; set; } = "";
    public List<string> DependsOn { get; set; } = new();
    /// <summary>"dropdown" - a choice of many is a field that opens its list under itself.</summary>
    public string View { get; set; } = "";
    public bool Searchable { get; set; }
    public bool Filter { get; set; }
    public double CacheSeconds { get; set; }
    public List<Preset> Presets { get; set; } = new();
    public string Target { get; set; } = "";
    /// <summary>The kinds of file a file field takes, ".html" and the like.</summary>
    public List<string> Extensions { get; set; } = new();
    public string Pins { get; set; } = "";
    public string CardActions { get; set; } = "";

    [JsonIgnore] public string Name => Words.Pick(LabelRu, Label);
    [JsonIgnore] public string Note => Words.Pick(HintRu, Hint);
    [JsonIgnore] public bool Dynamic => OptionsSource.Length > 0;
    [JsonIgnore] public bool Routed => Route.Length > 0;
    [JsonIgnore] public bool Badges => Kind is "info_badges" or "info-badges" or "static_badges" or "badges";
    [JsonIgnore] public bool Password => Kind == "password";
    /// <summary>A field the window draws: neither filled from a working folder nor kept out of sight.</summary>
    [JsonIgnore] public bool Drawn => !Routed && !Hidden;

    [JsonIgnore]
    public string Tip
    {
        get
        {
            var more = Words.Pick(TooltipRu, Tooltip);
            return Note.Length > 0 && more.Length > 0 ? Note + "\n\n" + more : Note.Length > 0 ? Note : more;
        }
    }

    [JsonIgnore] public JsonElement DefaultInUse => Default;
}

public sealed class Option
{
    public JsonElement Value { get; set; }
    public string Label { get; set; } = "";
    public string LabelRu { get; set; } = "";
    public string Tooltip { get; set; } = "";
    public string TooltipRu { get; set; } = "";
    public string Hint { get; set; } = "";
    public string HintRu { get; set; } = "";
    public string Summary { get; set; } = "";
    public string SummaryRu { get; set; } = "";
    public string Group { get; set; } = "";
    public string GroupRu { get; set; } = "";
    public bool Header { get; set; }
    public bool Note { get; set; }
    public bool Default { get; set; }
    public bool Beta { get; set; }
    public string Tone { get; set; } = "";
    /// <summary>The colour of a button of a row of choices (`accent` of the manifest).</summary>
    public string Accent { get; set; } = "";
    public List<string> Apps { get; set; } = new();
    public bool Installer { get; set; }
    public bool Archive { get; set; }
    public bool Page { get; set; }
    public string InstallerId { get; set; } = "";
    public string PortableId { get; set; } = "";
    public string Running { get; set; } = "";
    public string Newest { get; set; } = "";
    public bool Behind { get; set; }
    public bool Pinned { get; set; }

    [JsonIgnore] public string Name => Words.Pick(LabelRu, Label);
    [JsonIgnore] public string Tip => Words.Pick(TooltipRu, Tooltip) is { Length: > 0 } tip ? tip : Words.Pick(HintRu, Hint);
    [JsonIgnore] public string Said => Words.Pick(SummaryRu, Summary);
    [JsonIgnore] public string Key => FieldKinds.Text(Value);
    /// <summary>The group of a choice in the language of the window: the physical adapters and the virtual ones.</summary>
    [JsonIgnore] public string GroupName => Words.Pick(GroupRu, Group);
}

/// <summary>A button of a row of sets: at a press it puts values into fields.</summary>
public sealed class Preset
{
    public string Id { get; set; } = "";
    public string Label { get; set; } = "";
    public string LabelRu { get; set; } = "";
    public string Tooltip { get; set; } = "";
    public string TooltipRu { get; set; } = "";
    public string Hint { get; set; } = "";
    public string HintRu { get; set; } = "";
    public Dictionary<string, JsonElement> Values { get; set; } = new();
    public Dictionary<string, string> Pick { get; set; } = new();
    public Dictionary<string, JsonElement> Toggle { get; set; } = new();
    public Dictionary<string, JsonElement>? VisibleWhen { get; set; }

    [JsonIgnore] public string Name => Words.Pick(LabelRu, Label);
    [JsonIgnore] public string Tip => Words.Pick(TooltipRu, Tooltip) is { Length: > 0 } tip ? tip : Words.Pick(HintRu, Hint);
}

/// <summary>What `check` answered: whether the form may run, and the question asked before it.</summary>
public sealed class Checked
{
    public bool Ok { get; set; }
    public string Error { get; set; } = "";
    public bool Ask { get; set; }
    public string Title { get; set; } = "";
    public string Operation { get; set; } = "";
    public string Description { get; set; } = "";
    public string Risk { get; set; } = "";
    public string ImpactTitle { get; set; } = "";
    public List<string> Notes { get; set; } = new();
    public string Note { get; set; } = "";
    public string Run { get; set; } = "";
}

/// <summary>What `state --page` answered for one switch: the state in force, what was seen, the state after a restart, a word of trouble.</summary>
public sealed class Standing
{
    public string Is { get; set; } = "";
    public string Detail { get; set; } = "";
    public string Pending { get; set; } = "";
    public string Note { get; set; } = "";
}

public sealed class PageState
{
    public string Page { get; set; } = "";
    public string Error { get; set; } = "";
    public Dictionary<string, Standing> Switches { get; set; } = new();
}

public static class Words
{
    /// <summary>The Russian text in the Russian window; the English one otherwise, and wherever the Russian is missing.</summary>
    public static string Pick(string ru, string en) => Lang.Code == "ru" && ru.Length > 0 ? ru : en;
}

public static class FieldKinds
{
    /// <summary>The kinds of field the window can draw. Anything else is said in the journal, not left as an empty place.</summary>
    public static readonly string[] Known =
    {
        "checkbox", "checkboxes", "multiselect", "radio", "tabs", "select", "number", "text", "textarea", "markdown_editor",
        "profile_buttons", "toggle_buttons", "password", "folder", "file", "path", "smb_login_cache", "info_badges",
    };

    public static string Text(JsonElement value) => value.ValueKind switch
    {
        JsonValueKind.String => value.GetString() ?? "",
        JsonValueKind.Number => value.GetDouble().ToString("0.############", CultureInfo.InvariantCulture),
        JsonValueKind.True => "true",
        JsonValueKind.False => "false",
        JsonValueKind.Null or JsonValueKind.Undefined => "",
        _ => value.GetRawText(),
    };

    public static bool Matches(Dictionary<string, JsonElement>? condition, Func<string, string> valueOf)
    {
        if (condition is null || condition.Count == 0) return false;
        foreach (var (key, wanted) in condition)
        {
            var current = valueOf(key);
            bool any = wanted.ValueKind == JsonValueKind.Array
                ? wanted.EnumerateArray().Any(item => Text(item) == current)
                : Text(wanted) == current;
            if (!any) return false;
        }
        return true;
    }
}

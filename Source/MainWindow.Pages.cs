using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using Avalonia;
using Avalonia.Controls;
using Avalonia.Controls.Primitives;
using Avalonia.Layout;
using Avalonia.Media;
using Avalonia.Threading;
using AudionDevOpsTools.Core;
using AudionDevOpsTools.Views;
using Page = AudionDevOpsTools.Core.Page;

namespace AudionDevOpsTools;

/// <summary>
/// The pages of the window. A page is built when it is first opened and then stays in the window,
/// hidden while another is in sight: to show what is already there takes nothing. A page whose form
/// has to change - a field its shape depends on was set, a list it holds is to be asked anew - is
/// built again when it is next in sight, not before.
///
/// A page is blocks of cards. The fields two cards of a page share - the adapters of the network, the
/// distribution of WSL - stand once, over all the blocks; each card draws only its own. A card is an
/// operation with its form, a switch of the state of the machine, or a choice of the operation its one
/// run button starts (Core\Manifest.cs, Card).
/// </summary>
public partial class MainWindow
{
    sealed class PageView
    {
        public required Page Page;
        public required Form Form;
        public required ScrollViewer Root;
        public required StackPanel Cards;
        /// <summary>The buttons of the page that run something, the buttons of its switches among them.</summary>
        public readonly List<Button> RunButtons = new();
        public readonly List<ToggleButton> SwitchButtons = new();
        /// <summary>A page with one form keeps its name, its buttons and "back to the defaults" in the bar over the cards.</summary>
        public bool HasBar;
        public string BarTitle = "";
        public readonly List<Button> BarButtons = new();
        public List<Field> ResetFields = new();
        public Control? Bands;
        /// <summary>The page is to be built before it is shown: never built yet, or what it shows is out of date.</summary>
        public bool Stale = true;
        /// <summary>The switches of the page: by the key of the state, the button of each state and the line of what was seen.</summary>
        public readonly Dictionary<string, (List<(ToggleButton Button, Node Node)> States, TextBlock Seen)> Switches = new();
        /// <summary>What the machine was found in, last time the page asked; null - not asked yet.</summary>
        public PageState? State;
        public bool StateAsking;
    }

    readonly Dictionary<string, PageView> _views = new();
    PageView? _view;

    static string KeyOf(Page page) => ValueStore.KeyOf(page);

    PageView ViewOf(Page page)
    {
        if (_views.TryGetValue(KeyOf(page), out var known)) return known;
        var cards = new StackPanel { Margin = new Thickness(10, 10, 10, 4), Spacing = 10 };
        var root = new ScrollViewer
        {
            Content = cards, IsVisible = false,
            HorizontalScrollBarVisibility = ScrollBarVisibility.Disabled, VerticalScrollBarVisibility = ScrollBarVisibility.Auto,
        };
        PageView? view = null;
        var form = new Form(_store.Of(page), () => Outdated(view!))
        {
            Grown = CentreWords,
            Folders = () => (_source, _target),
        };
        view = new PageView { Page = page, Form = form, Root = root, Cards = cards };
        PageHost.Children.Add(root);
        return _views[KeyOf(page)] = view;
    }

    void Outdated(PageView view)
    {
        view.Stale = true;
        if (ReferenceEquals(view, _view)) RebuildSoon();
    }

    void SelectPage(Page page)
    {
        _page = page;
        if (page.Section is { } section) _lastPage[section.Id] = page.Id;
        foreach (var child in PageRow.Children)
            if (child is ToggleButton tab) tab.IsChecked = (string?)tab.Tag == page.Id;
        var view = ViewOf(page);
        _view = view;
        _store.Open(page);
        if (view.Form.DropExpiredLists()) view.Stale = true;
        if (view.Stale) Build(view, whole: false);
        Show(view);
        // The state of the machine is asked every time its page comes into sight: it changes from outside too.
        if (page.State) AskState(view);
    }

    void Show(PageView view)
    {
        CardsNote.IsVisible = false;
        foreach (var other in _views.Values) other.Root.IsVisible = ReferenceEquals(other, view);
        ActionButtons.Children.Clear();
        foreach (var button in view.BarButtons) ActionButtons.Children.Add(button);
        ActionTitle.Text = view.BarTitle;
        ActionReset.IsVisible = view.ResetFields.Count > 0;
        ActionBar.IsVisible = view.HasBar;
        BandHost.Content = view.Bands;
        BandHost.IsVisible = view.Bands is not null;
        PageBar.IsVisible = PageRow.IsVisible || BandHost.IsVisible;
        ApplyBusy();
        CentreWords();
    }

    bool _rebuildPosted;

    void RebuildSoon()
    {
        if (_rebuildPosted) return;
        _rebuildPosted = true;
        Dispatcher.UIThread.Post(() =>
        {
            _rebuildPosted = false;
            if (_view is not { } view) return;
            var offset = view.Root.Offset;
            Build(view, whole: offset.Y >= 1);
            Show(view);
            Dispatcher.UIThread.Post(() => view.Root.Offset = offset, DispatcherPriority.Loaded);
        });
    }

    void ResetFields(PageView view, List<Field> fields)
    {
        _store.Of(view.Page).Reset(fields);
        Outdated(view);
    }

    void OutdateAll(bool lists)
    {
        foreach (var view in _views.Values)
        {
            if (lists) view.Form.DropLists();
            view.Stale = true;
        }
        if (_view is not null) RebuildSoon();
    }

    void ForgetPages()
    {
        foreach (var view in _views.Values) view.Form.Detach();
        _views.Clear();
        _view = null;
        PageHost.Children.Clear();
        ActionButtons.Children.Clear();
    }

    double _builtIn;

    // ------------------------------------------------------------ the cards of a page

    /// <summary>
    /// The fields a card draws of its own: those of its form, and for a pick - of every operation it may start.
    /// A field the page puts away (`away`) is set on another page and is not drawn here.
    /// </summary>
    static IEnumerable<Field> FieldsOf(Card card, Page page)
    {
        var nodes = card.Kind == "pick" ? card.Operations : card.FormOf is { } form ? new List<Node> { form } : new List<Node>();
        return nodes.SelectMany(node => node.Fields).Where(field => field.Drawn && !page.Away.Contains(field.Id))
            .GroupBy(field => field.Id).Select(group => group.First());
    }

    /// <summary>
    /// The fields two cards of a page share: they stand once, over all the blocks - the adapters of a
    /// page of the network, the distribution of a page of WSL. A row of badges stays with its card.
    /// </summary>
    static List<Field> Common(Page page, IReadOnlyList<Card> cards)
    {
        if (cards.Count < 2) return new List<Field>();
        var counts = new Dictionary<string, (Field Field, int Cards)>();
        foreach (var card in cards)
            foreach (var field in FieldsOf(card, page))
            {
                if (field.Badges) continue;
                counts[field.Id] = counts.TryGetValue(field.Id, out var seen) ? (seen.Field, seen.Cards + 1) : (field, 1);
            }
        return counts.Values.Where(item => item.Cards > 1).Select(item => item.Field).ToList();
    }

    void Build(PageView view, bool whole)
    {
        var clock = System.Diagnostics.Stopwatch.StartNew();
        var page = view.Page;
        var visibleCards = page.Cards.Where(card => card.WhenPicked.Length == 0 || page.Cards.Any(choice => choice.Kind == "pick" && choice.Chosen == card.WhenPicked)).ToList();
        view.Form.Forget();
        view.Form.Lazy = !whole;
        view.Cards.Children.Clear();
        view.RunButtons.Clear();
        view.SwitchButtons.Clear();
        view.Switches.Clear();
        view.BarButtons.Clear();
        view.ResetFields = new List<Field>();
        view.HasBar = false;
        view.BarTitle = "";
        view.Bands = null;

        var common = Common(page, visibleCards);
        var shared = common.Select(field => field.Id).ToHashSet();
        if (common.Count > 0)
        {
            // The form over all the blocks: drawn for the first operation that has these fields.
            var owner = visibleCards.SelectMany(card => card.Operations).First(node => node.Fields.Any(field => shared.Contains(field.Id)));
            var fields = owner.Fields.Where(field => shared.Contains(field.Id)).ToList();
            foreach (var other in page.Operations())
                foreach (var field in other.Fields.Where(field => shared.Contains(field.Id) && fields.All(known => known.Id != field.Id)))
                    fields.Add(field);
            var form = view.Form.Build(owner, fields, out _);
            view.ResetFields.AddRange(fields);
            var head = new TextBlock { Classes = { "blockname" }, Text = Lang.T("Общие поля страницы"), Margin = new Thickness(0, 0, 0, 7) };
            ToolTip.SetTip(head, Lang.T("Поля, которые читают несколько блоков этой страницы: задаются один раз."));
            view.Cards.Children.Add(new Border { Classes = { "card" }, Padding = new Thickness(10, 8, 8, 6), Child = new StackPanel { Children = { head, form } } });
        }

        // A page of one operation with a form - the pages of DEFAULT APPS: its name and its button stand in the bar over the form.
        // A card with operations beside its own is a card like any other: the bar holds one button, not a row of them.
        if (page.Cards.Count == 1 && page.Cards[0] is { Kind: "op", Guests.Count: 0 } alone && alone.FormOf is { } single && FieldsOf(alone, page).Any())
        {
            view.HasBar = true;
            view.BarTitle = Upper(page.Name);
            var buttons = alone.Guests.Append(single).Select(node => RunButton(view, node)).OrderBy(button => button.Classes.Contains("fill") ? 1 : 0).ToList();
            view.BarButtons.AddRange(buttons);
            var drawn = FieldsOf(alone, page).ToList();
            view.ResetFields.AddRange(drawn);
            WatchLabel(view, single);
            view.Cards.Children.Add(view.Form.Build(single, drawn, out var bands));
            view.Bands = bands;
            Finish(view, clock);
            return;
        }

        // Cards of one block stand together, in one frame under the name of the block.
        var blocks = new List<(string Name, List<Card> Cards)>();
        foreach (var card in visibleCards)
        {
            var name = card.BlockName.Length > 0 ? card.BlockName : page.Name;
            if (blocks.Count > 0 && blocks[^1].Name == name) blocks[^1].Cards.Add(card);
            else blocks.Add((name, new List<Card> { card }));
        }
        foreach (var (name, cards) in blocks) view.Cards.Children.Add(Block(view, name, cards, shared));
        Finish(view, clock);
    }

    void Finish(PageView view, System.Diagnostics.Stopwatch clock)
    {
        if (view.Form.Unknown.Count > 0)
        {
            AppendLines(new[] { Lang.F("[окно] поля неизвестного вида не показаны: {0}", string.Join("; ", view.Form.Unknown)) });
            view.Form.Unknown.Clear();
        }
        if (Lang.Code != "ru") Lang.Walk(view.Cards);
        view.Stale = false;
        view.Form.Lazy = true;
        _builtIn = clock.Elapsed.TotalMilliseconds;
        if (view.State is not null) Light(view);
    }

    void CentreWords() => Dispatcher.UIThread.Post(() => PixelGrid.Adopt(this), DispatcherPriority.Loaded);

    /// <summary>
    /// A block: its name, then its cards one under another. Cards that are nothing but buttons put
    /// them in one row; a card with a form or a title is a part of its own, its buttons at its right.
    /// The first card of a block that has no title of its own puts its buttons on the line of the
    /// name, at its right: one line, not a name over a row of buttons.
    /// </summary>
    Control Block(PageView view, string name, List<Card> cards, HashSet<string> shared)
    {
        var body = new StackPanel { Spacing = 10 };
        var top = new Grid { ColumnDefinitions = new ColumnDefinitions("Auto,*") };
        top.Children.Add(new TextBlock { Classes = { "blockname" }, Text = name, VerticalAlignment = VerticalAlignment.Center, Margin = new Thickness(0, 0, 10, 1) });
        body.Children.Add(top);
        WrapPanel? plain = null;
        bool first = true;
        foreach (var card in cards)
        {
            var into = first ? top : null;
            first = false;
            var own = FieldsOf(card, view.Page).Where(field => !shared.Contains(field.Id)).ToList();
            if (card.Kind == "op" && own.Count == 0 && card.Name.Length == 0)
            {
                // Nothing to fill: the buttons of such cards stand side by side at the right, as every row of buttons
                // does - on the line of the name when they come first, on a row of their own after a part (the review
                // of 16.10.2026: "move" of WSL stood alone at the left under the field of "clone").
                if (plain is null)
                {
                    plain = new WrapPanel { Orientation = Orientation.Horizontal, HorizontalAlignment = HorizontalAlignment.Right,
                        LineSpacing = 6, ItemsAlignment = WrapPanelItemsAlignment.End };
                    if (into is null) body.Children.Add(plain);
                    else
                    {
                        plain.VerticalAlignment = VerticalAlignment.Center;
                        Grid.SetColumn(plain, 1);
                        top.Children.Add(plain);
                    }
                }
                foreach (var node in card.Operations.Concat(card.Guests))
                {
                    var button = RunButton(view, node);
                    button.Margin = new Thickness(4, 0, 0, 0);
                    plain.Children.Add(button);
                }
                continue;
            }
            plain = null;
            body.Children.Add(card.Kind switch
            {
                "switch" => Switch(view, card, own, into),
                "pick" => Pick(view, card, own, into),
                _ => Part(view, card, own, into),
            });
        }
        return new Border { Classes = { "card" }, Padding = new Thickness(12, 10, 10, 10), Child = body };
    }

    /// <summary>
    /// A line of a card: its title at the left (when the layout names one), its buttons at the right, the main one last.
    /// A title that already says the name the layout gave an operation leaves its button the operation's own name.
    /// A line with no title goes to the line of the name of the block when it is given one (`into`): null is returned then.
    /// </summary>
    Control? Head(PageView view, string title, IEnumerable<Node> nodes, Action<List<Button>>? more = null, Grid? into = null)
    {
        var buttons = nodes.Select(node => RunButton(view, node, heading: title)).ToList();
        more?.Invoke(buttons);
        // A line that wraps keeps a gap from the one over it and stands at the right as the first does (the owner,
        // 15.10.2026: "the buttons must be parted" - a wrapped button sat glued under its row).
        var row = new WrapPanel { Orientation = Orientation.Horizontal, HorizontalAlignment = HorizontalAlignment.Right, VerticalAlignment = VerticalAlignment.Center,
            LineSpacing = 6, ItemsAlignment = WrapPanelItemsAlignment.End };
        foreach (var button in buttons.OrderBy(button => button.Classes.Contains("fill") ? 1 : 0)) row.Children.Add(button);
        Grid.SetColumn(row, 1);
        if (title.Length == 0 && into is not null)
        {
            into.Children.Add(row);
            return null;
        }
        if (title.Length == 0 && buttons.Count == 0) return null;
        var head = new Grid { ColumnDefinitions = new ColumnDefinitions("Auto,*") };
        if (title.Length > 0) head.Children.Add(new TextBlock { Classes = { "cardtitle" }, Text = title, VerticalAlignment = VerticalAlignment.Center, Margin = new Thickness(0, 0, 10, 0) });
        head.Children.Add(row);
        return head;
    }

    /// <summary>An operation with its form: its title and buttons, its own fields under them.</summary>
    Control Part(PageView view, Card card, List<Field> own, Grid? top = null)
    {
        var host = card.Operations.FirstOrDefault();
        var part = new StackPanel { Spacing = 8 };
        if (host is null) return part;
        WatchLabel(view, host);
        if (Head(view, card.Name.Length > 0 ? card.Name : host.Name != host.OwnName ? host.Name : "", card.Guests.Prepend(host), into: top) is { } head)
            part.Children.Add(head);
        if (own.Count > 0) part.Children.Add(view.Form.Build(host, own, out _));
        return part;
    }

    /// <summary>
    /// A switch of the state of the machine: a row of states, the one the machine is in lit. A press
    /// on another state runs the operation that brings the machine there; on the one in force -
    /// nothing. Over the row - what was seen; at its right - the operations of the card that only look.
    /// </summary>
    Control Switch(PageView view, Card card, List<Field> own, Grid? top = null)
    {
        var part = new StackPanel { Spacing = 8 };
        if (Head(view, card.Name, card.Guests, into: top) is { } head) part.Children.Add(head);
        var seen = new TextBlock { Classes = { "note" }, Text = Lang.T("Сейчас: читаю…"), TextWrapping = TextWrapping.Wrap };
        part.Children.Add(seen);
        var row = new WrapPanel { Orientation = Orientation.Horizontal };
        var states = new List<(ToggleButton, Node)>();
        foreach (var node in card.Operations)
        {
            var face = new StackPanel { Orientation = Orientation.Horizontal, Spacing = 7 };
            if (Icons.Glyph(node.Sign) is not null) face.Children.Add(Icons.Sign(node.Sign));
            face.Children.Add(new TextBlock { Text = Upper(node.Name), VerticalAlignment = VerticalAlignment.Center });
            var button = new ToggleButton { Classes = { "switch", "state" }, Content = face, Margin = new Thickness(0, 0, 6, 4), MinHeight = 32, Tag = node };
            Avalonia.Automation.AutomationProperties.SetAutomationId(button, "state_" + node.Id);
            ToolTip.SetTip(button, TipOf(node));
            button.Click += (_, _) =>
            {
                // The button shows the machine, not the press: it is lit again by what is read, never by the click.
                bool lit = IsInForce(view, card, node);
                button.IsChecked = lit;
                if (lit) { SetStatus(Lang.F("«{0}»: машина уже в этом состоянии.", node.Name)); return; }
                Press(node);
            };
            states.Add((button, node));
            view.SwitchButtons.Add(button);
            row.Children.Add(button);
        }
        part.Children.Add(row);
        view.Switches[card.State] = (states, seen);
        if (own.Count > 0 && card.Operations.FirstOrDefault() is { } first) part.Children.Add(view.Form.Build(first, own, out _));
        return part;
    }

    static bool IsInForce(PageView view, Card card, Node node) =>
        view.State?.Switches.TryGetValue(card.State, out var standing) == true && standing.Is.Length > 0 && standing.Is == node.Is;

    /// <summary>
    /// A choice of the operation: a row over the form - the form follows the operation chosen - and
    /// the one run button of the card, named as the choice is.
    /// </summary>
    Control Pick(PageView view, Card card, List<Field> own, Grid? top = null)
    {
        var part = new StackPanel { Spacing = 8 };
        bool tabbed = card.View == "tabs";
        Panel band = tabbed ? new Grid() : new WrapPanel { Orientation = Orientation.Horizontal };
        foreach (var node in card.Operations)
        {
            var face = new StackPanel { Orientation = Orientation.Horizontal, Spacing = 7 };
            if (Icons.Glyph(node.Sign) is not null) face.Children.Add(Icons.Sign(node.Sign));
            face.Children.Add(new TextBlock { Text = Upper(node.Name), VerticalAlignment = VerticalAlignment.Center });
            var button = new ToggleButton { Classes = { "switch" }, Content = face, Margin = new Thickness(0, 0, 6, 4), IsChecked = node.Id == card.Chosen };
            if (tabbed)
            {
                button.Classes.Add("section");
                button.HorizontalAlignment = HorizontalAlignment.Stretch;
                button.HorizontalContentAlignment = HorizontalAlignment.Center;
                button.Margin = new Thickness(band.Children.Count == 0 ? 0 : 3, 0, band.Children.Count == card.Operations.Count - 1 ? 0 : 3, 0);
                ((Grid)band).ColumnDefinitions.Add(new ColumnDefinition(GridLength.Star));
                Grid.SetColumn(button, band.Children.Count);
            }
            Avalonia.Automation.AutomationProperties.SetAutomationId(button, "pick_" + node.Id);
            ToolTip.SetTip(button, TipOf(node));
            var id = node.Id;
            button.Click += (_, _) =>
            {
                if (card.Chosen == id) { button.IsChecked = true; return; }
                card.Chosen = id;
                if (tabbed) view.Root.Offset = default;
                Outdated(view);
            };
            band.Children.Add(button);
        }
        if (tabbed) view.Bands = band;
        else part.Children.Add(band);
        if (card.FormOf is { } chosen)
        {
            var drawn = chosen.Fields.Where(field => own.Any(mine => mine.Id == field.Id)).ToList();
            if (drawn.Count > 0) part.Children.Add(view.Form.Build(chosen, drawn, out _));
            if (tabbed)
            {
                view.HasBar = true;
                view.BarTitle = Upper(chosen.OwnName);
                view.ResetFields.AddRange(drawn);
                WatchLabel(view, chosen);
                view.BarButtons.AddRange(card.Guests.Select(node => RunButton(view, node)));
                view.BarButtons.Add(RunButton(view, chosen, card.Tone.Length > 0 ? card.Tone : null));
                return part;
            }
            // First in its block, the run button stands at the right of the name of the block, over the choice.
            if (Head(view, "", card.Guests, buttons =>
            {
                // The run button of the card: the operation chosen, filled - Burn Orange where the choice removes.
                // The row above already says the choice in short; the button says the whole action.
                var run = RunButton(view, chosen, card.Tone.Length > 0 && chosen.PlaceTone.Length == 0 ? card.Tone : null, heading: chosen.Name);
                buttons.Add(run);
            }, top) is { } head) part.Children.Add(head);
        }
        return part;
    }

    /// <summary>
    /// The button that runs an operation: its sign and its name, nothing more - what it does is in its
    /// tooltip. The main action of a block is filled with the accent; what removes - with Burn Orange.
    /// An operation whose form begins with "what to do" is named by the choice made there.
    /// </summary>
    Button RunButton(PageView view, Node node, string? tone = null, string heading = "")
    {
        var look = tone ?? node.Look;
        var label = LabelOf(view, node);
        if (heading.Length > 0 && label == node.Name && node.OwnName.Length > 0 && string.Equals(heading, node.Name, StringComparison.OrdinalIgnoreCase)) label = node.OwnName;
        var face = new StackPanel { Orientation = Orientation.Horizontal, Spacing = 6, HorizontalAlignment = HorizontalAlignment.Center, VerticalAlignment = VerticalAlignment.Center };
        if (Icons.Glyph(node.Sign) is not null) face.Children.Add(Icons.Sign(node.Sign));
        if (node.Secret) face.Children.Add(Icons.Sign("lock"));
        face.Children.Add(new TextBlock { Text = Upper(label) });
        var button = new Button
        {
            Tag = node, Classes = { "step" }, Content = face, Height = 30, MinHeight = 30,
            Margin = new Thickness(4, 0, 0, 0),
        };
        button.Classes.Set("fill", look is "run" or "burn");
        button.Classes.Set("burn", look == "burn");
        Avalonia.Automation.AutomationProperties.SetAutomationId(button, "run_" + node.Id);
        ToolTip.SetTip(button, TipOf(node) + (node.Secret ? "\n" + Lang.T("Экспорт содержит секреты: храните его как ключ.") : ""));
        button.Click += (_, _) => Press(node);
        view.RunButtons.Add(button);
        return button;
    }

    /// <summary>The field "what to do" of an operation (`display: safety_buttons`): the choice names its run button.</summary>
    static Field? ActionField(Node node) => node.Fields.FirstOrDefault(field => field.Display == "safety_buttons" && field.Kind is "radio" or "select");

    string LabelOf(PageView view, Node node)
    {
        if (ActionField(node) is not { } action) return node.Name;
        var key = _store.Of(view.Page).Get(action);
        return action.Options.FirstOrDefault(option => option.Key == key)?.Name is { Length: > 0 } chosen ? chosen : node.Name;
    }

    /// <summary>A change of "what to do" renames the run button: the page is built again.</summary>
    void WatchLabel(PageView view, Node node)
    {
        if (ActionField(node) is { } action) view.Form.Shapes(new[] { action.Id });
    }

    // ------------------------------------------------------------ the state of the machine

    /// <summary>The state of the switches of a page asked of the console command; the switches are lit by the answer.</summary>
    async void AskState(PageView view)
    {
        if (view.StateAsking || !Door.Ready) return;
        view.StateAsking = true;
        try
        {
            var told = await Door.State(view.Page.Id);
            view.State = told;
            Light(view);
        }
        finally { view.StateAsking = false; }
    }

    /// <summary>
    /// The switches lit by what the machine was found in. A state that comes after a restart is shown
    /// as such: its button is marked, and the line says so. What could not be read lights nothing.
    /// </summary>
    void Light(PageView view)
    {
        if (view.State is not { } state) return;
        foreach (var (key, (states, seen)) in view.Switches)
        {
            state.Switches.TryGetValue(key, out var standing);
            foreach (var (button, node) in states)
            {
                button.IsChecked = standing is not null && standing.Is.Length > 0 && standing.Is == node.Is;
                button.Classes.Set("pending", standing is not null && standing.Pending.Length > 0 && standing.Pending == node.Is && standing.Pending != standing.Is);
            }
            seen.Text = Seen(state, standing, states);
            seen.Classes.Set("warn", standing is null || standing.Is.Length == 0);
        }
    }

    static string Seen(PageState state, Standing? standing, List<(ToggleButton Button, Node Node)> states)
    {
        if (state.Error.Length > 0) return Lang.F("Сейчас: не прочитано - {0}", state.Error);
        if (standing is null) return Lang.T("Сейчас: не прочитано.");
        var lit = states.FirstOrDefault(item => item.Node.Is == standing.Is).Node;
        var parts = new List<string>();
        // Nothing read for a reason (rights, no network) is unknown; read but none of the buttons is something else.
        parts.Add(lit is not null ? lit.Name : standing.Is.Length > 0 ? standing.Is : standing.Note.Length > 0 ? Lang.T("не определено") : Lang.T("другое"));
        if (standing.Detail.Length > 0) parts.Add(standing.Detail);
        if (standing.Pending.Length > 0 && standing.Pending != standing.Is)
            parts.Add(Lang.F("после перезагрузки: {0}", states.FirstOrDefault(item => item.Node.Is == standing.Pending).Node?.Name ?? standing.Pending));
        var note = standing.Note switch
        {
            "" => "",
            "rights" => Lang.T("нужны права администратора"),
            "offline" => Lang.T("нет выхода в сеть"),
            "no_device" => Lang.T("устройства нет"),
            "absent" => Lang.T("компонента нет в этой редакции Windows"),
            var other => other,
        };
        if (note.Length > 0) parts.Add(note);
        return Lang.T("Сейчас:") + " " + string.Join(" · ", parts);
    }
}

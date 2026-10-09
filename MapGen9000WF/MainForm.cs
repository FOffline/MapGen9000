using System.Drawing.Imaging;
using System.Globalization;
using System.Runtime.InteropServices;
using System.Text.Json;

namespace MapGen9000;

public sealed class MainForm : Form
{
    // ------------------------------------------------------------ slider description
    sealed class Slider
    {
        public string Key = "", Title = "";
        public double Lo, Hi, Step;
        public bool Percent, RangePercent;
        public TrackBar Bar = null;
        public Label ValueLabel = null;

        public double Display => Lo + Bar.Value * Step;               // value as shown (percent units for Percent)
        public void SetDisplay(double v)
        {
            int pos = (int)Math.Round((v - Lo) / Step);
            Bar.Value = Math.Max(Bar.Minimum, Math.Min(Bar.Maximum, pos));
            ShowValue();
        }
        public void ShowValue()
        {
            double v = Display;
            ValueLabel.Text =
                Percent ? v.ToString("F1", CultureInfo.InvariantCulture) + "%" :
                RangePercent ? (v * 100).ToString("F0", CultureInfo.InvariantCulture) + "%" :
                Key == "size" || Key == "seed" || Key == "octaves" ? ((int)Math.Round(v)).ToString(CultureInfo.InvariantCulture) :
                Key == "patch_grass" ? v.ToString("F1", CultureInfo.InvariantCulture) + "x" :
                v.ToString("F2", CultureInfo.InvariantCulture);
        }
    }

    readonly List<Slider> sliders = new();
    readonly CheckBox chkDelete = new() { Text = "Delete outside", Checked = true, Width = 200 };
    readonly CheckBox chkBlockers = new() { Text = "Scroll blockers", Checked = true, Width = 200 };
    readonly PictureBox pic = new() { Dock = DockStyle.Fill, BackColor = Color.FromArgb(34, 34, 34), SizeMode = PictureBoxSizeMode.CenterImage };
    readonly System.Windows.Forms.Timer timer = new() { Interval = 150 };
    readonly Random uiRng = new();
    Protos protos = new();
    int version;

    public MainForm()
    {
        Text = "MapGen9000";
        Icon = System.Drawing.Icon.ExtractAssociatedIcon(Application.ExecutablePath);
        AutoScaleMode = AutoScaleMode.Dpi;
        ClientSize = new Size(1280, 720);
        MinimumSize = new Size(900, 500);
        StartPosition = FormStartPosition.CenterScreen;

        var side = new Panel { Dock = DockStyle.Left, Width = 470, AutoScroll = true };
        var flow = new FlowLayoutPanel
        {
            Dock = DockStyle.Top, AutoSize = true, AutoSizeMode = AutoSizeMode.GrowAndShrink,
            FlowDirection = FlowDirection.LeftToRight, WrapContents = true, Width = 446, Padding = new Padding(6),
        };
        side.Controls.Add(flow);
        Controls.Add(pic);          // fill first, then the dock-left panel
        Controls.Add(side);

        // key, title, min, max, step, percent, range-percent
        
		var spec = new (string, string, double, double, double, bool, bool)[]
		{
			("size", "Size", 20, 400, 2, false, false),
			("seed", "Seed", 0, 99999, 1, false, false),
			("octaves", "Noise octaves", 1, 8, 1, false, false),
			("persistence", "Noise persistence", 0.05, 0.9, 0.01, false, false),

			("density", "Main ground density", 0, 100, 0.1, true, false),

			("corn", "Corn", 0, 100, 0.1, true, false),
			("dry_trees", "Dry trees", 0, 100, 0.1, true, false),
			("trees", "Trees", 0, 100, 0.1, true, false),
			("rocks", "Rocks", 0, 100, 0.1, true, false),
			("cactuses", "Cactuses", 0, 100, 0.1, true, false),
			("grass", "Grass", 0, 100, 0.1, true, false),
			("misc", "Misc", 0, 100, 0.1, true, false),
			("barrels", "Barrels", 0, 100, 0.1, true, false),

			("patch_grass", "Grass patch multiplier", 1, 6, 0.1, false, false),

			("grass_min", "Grass minimum", 0, 1, 0.01, false, true),
			("grass_max", "Grass maximum", 0, 1, 0.01, false, true),
			("trees_min", "Trees minimum", 0, 1, 0.01, false, true),
			("trees_max", "Trees maximum", 0, 1, 0.01, false, true),
		};
        var defaults = new GenParams();
        foreach (var (key, title, lo, hi, step, pct, rng) in spec)
        {
            var s = new Slider { Key = key, Title = title, Lo = lo, Hi = hi, Step = step, Percent = pct, RangePercent = rng };
            var cell = new Panel { Width = 205, Height = 58, Margin = new Padding(2) };
            var name = new Label { Text = title, Location = new Point(2, 0), AutoSize = true };
            s.ValueLabel = new Label { Location = new Point(135, 0), Size = new Size(68, 16), TextAlign = ContentAlignment.TopRight };
            s.Bar = new TrackBar
            {
                Location = new Point(0, 18), Width = 202, Height = 38, AutoSize = false, TickStyle = TickStyle.None,
                Minimum = 0, Maximum = (int)Math.Round((hi - lo) / step), SmallChange = 1, LargeChange = Math.Max(1, (int)Math.Round((hi - lo) / step / 20)),
            };
            double initial = GetValue(defaults, key) * (pct ? 100 : 1);
            s.SetDisplay(initial);
            s.Bar.ValueChanged += (_, _) => { s.ShowValue(); Schedule(); };
            cell.Controls.Add(name);
            cell.Controls.Add(s.ValueLabel);
            cell.Controls.Add(s.Bar);
            flow.Controls.Add(cell);
            sliders.Add(s);
        }

        chkDelete.CheckedChanged += (_, _) => Schedule();
        chkBlockers.CheckedChanged += (_, _) => Schedule();
        flow.Controls.Add(chkDelete);
        flow.Controls.Add(chkBlockers);

        var btnRandom = MakeButton("Random Desert", 416, RandomDesert);
        flow.Controls.Add(btnRandom);
        flow.SetFlowBreak(btnRandom, true);
        flow.Controls.Add(MakeButton("Save Preset", 204, SavePreset));
        flow.Controls.Add(MakeButton("Load Preset", 204, LoadPreset));
        var btnSave = MakeButton("Save .fomap", 416, SaveMap);
        btnSave.Font = new Font(Font, FontStyle.Bold);
        flow.Controls.Add(btnSave);

        timer.Tick += (_, _) => { timer.Stop(); StartUpdate(); };
        pic.SizeChanged += (_, _) => Schedule();
        Load += (_, _) => Schedule();
    }

    static Button MakeButton(string text, int width, Action click)
    {
        var b = new Button { Text = text, Width = width, Height = 28, Margin = new Padding(2, 4, 2, 2) };
        b.Click += (_, _) => click();
        return b;
    }

    // ------------------------------------------------------------ parameters <-> controls
    static double GetValue(GenParams p, string k) => k switch
    {
        "size" => p.Size, "seed" => p.Seed, "octaves" => p.Octaves, "persistence" => p.Persistence, "density" => p.Density,
        "corn" => p.Corn, "dry_trees" => p.DryTrees, "trees" => p.Trees, "rocks" => p.Rocks, "cactuses" => p.Cactuses,
        "grass" => p.Grass, "misc" => p.Misc, "barrels" => p.Barrels, "patch_grass" => p.PatchGrass,
        "grass_min" => p.GrassMin, "grass_max" => p.GrassMax, "trees_min" => p.TreesMin, "trees_max" => p.TreesMax,
        _ => 0,
    };

    static void SetValue(GenParams p, string k, double v)
    {
        switch (k)
        {
            case "size": p.Size = (int)Math.Round(v); break;
            case "seed": p.Seed = (int)Math.Round(v); break;
            case "octaves": p.Octaves = (int)Math.Round(v); break;
            case "persistence": p.Persistence = v; break;
            case "density": p.Density = v; break;
            case "corn": p.Corn = v; break;
            case "dry_trees": p.DryTrees = v; break;
            case "trees": p.Trees = v; break;
            case "rocks": p.Rocks = v; break;
            case "cactuses": p.Cactuses = v; break;
            case "grass": p.Grass = v; break;
            case "misc": p.Misc = v; break;
            case "barrels": p.Barrels = v; break;
            case "patch_grass": p.PatchGrass = v; break;
            case "grass_min": p.GrassMin = v; break;
            case "grass_max": p.GrassMax = v; break;
            case "trees_min": p.TreesMin = v; break;
            case "trees_max": p.TreesMax = v; break;
        }
    }

    GenParams GetParams()
    {
        var p = new GenParams { DeleteOutside = chkDelete.Checked, ScrollBlockers = chkBlockers.Checked, Protos = protos };
        foreach (var s in sliders) SetValue(p, s.Key, s.Percent ? s.Display / 100.0 : s.Display);
        return p;
    }

    void Schedule()
    {
        timer.Stop();
        timer.Start();
    }

    // ------------------------------------------------------------ preview
    static Bitmap ToBitmap(byte[] rgb, int w, int h)
    {
        var bmp = new Bitmap(w, h, PixelFormat.Format24bppRgb);
        var bd = bmp.LockBits(new Rectangle(0, 0, w, h), ImageLockMode.WriteOnly, PixelFormat.Format24bppRgb);
        try
        {
            int stride = Math.Abs(bd.Stride);
            var buf = new byte[stride * h];
            for (int y = 0; y < h; y++)
                for (int x = 0; x < w; x++)
                {
                    int s = (y * w + x) * 3, d = y * stride + x * 3;
                    buf[d] = rgb[s + 2]; buf[d + 1] = rgb[s + 1]; buf[d + 2] = rgb[s];
                }
            Marshal.Copy(buf, 0, bd.Scan0, buf.Length);
        }
        finally { bmp.UnlockBits(bd); }
        return bmp;
    }

    void StartUpdate()
    {
        var p = GetParams();
        int vw = pic.ClientSize.Width, vh = pic.ClientSize.Height;
        int w = vw > 100 ? Math.Max(120, (int)Math.Min(vw, vh * 1.38) - 12) : 450;
        int my = ++version;
        Task.Run(() =>
        {
            try
            {
                var m = Generator.Generate(p);
                var (rgb, rw, rh) = Generator.Render(m, w);
                var bmp = ToBitmap(rgb, rw, rh);
                BeginInvoke(new Action(() =>
                {
                    if (my != version || IsDisposed) { bmp.Dispose(); return; }
                    var old = pic.Image;
                    pic.Image = bmp;
                    old?.Dispose();
                    Text = $"MapGen9000 - {m.TileCount} tiles, {m.Objects.Count} objects";
                }));
            }
            catch (Exception ex)
            {
                try { BeginInvoke(new Action(() => Text = "MapGen9000 - " + ex.Message)); } catch { }
            }
        });
    }

    // ------------------------------------------------------------ buttons
    void SaveMap()
    {
        using var dlg = new SaveFileDialog { Filter = "FOnline map (*.fomap)|*.fomap", DefaultExt = "fomap", FileName = "map.fomap" };
        if (dlg.ShowDialog(this) != DialogResult.OK) return;
        var oldCursor = Cursor;
        Cursor = Cursors.WaitCursor;
        try
        {
            var m = Generator.Generate(GetParams());
            Generator.WriteFomap(m, dlg.FileName);
            MessageBox.Show(this, "Saved " + dlg.FileName, "MapGen9000");
        }
        catch (Exception ex) { MessageBox.Show(this, ex.Message, "MapGen9000", MessageBoxButtons.OK, MessageBoxIcon.Error); }
        finally { Cursor = oldCursor; }
    }

    void RandomDesert()
    {
        Slider S(string k) => sliders.First(s => s.Key == k);
        double U(double a, double b) => a + uiRng.NextDouble() * (b - a);
        S("seed").SetDisplay(uiRng.Next(0, 100000));
        foreach (var k in new[] { "corn", "dry_trees", "trees", "barrels" }) S(k).SetDisplay(0);
        S("cactuses").SetDisplay(U(2.5, 5.0));
        S("rocks").SetDisplay(U(0.5, 1.5));
        S("grass").SetDisplay(U(0.2, 1.0));
        S("misc").SetDisplay(U(0.5, 1.5));
        Schedule();
    }

    void SavePreset()
    {
        using var dlg = new SaveFileDialog { Filter = "MapGen9000 preset (*.json)|*.json", DefaultExt = "json" };
        if (dlg.ShowDialog(this) != DialogResult.OK) return;
        var d = new Dictionary<string, object>();
        foreach (var s in sliders)
        {
            double v = s.Percent ? s.Display / 100.0 : s.Display;
            if (s.Key == "size" || s.Key == "seed" || s.Key == "octaves") d[s.Key] = (int)Math.Round(v);
            else d[s.Key] = Math.Round(v, 6);
        }
        d["delete_outside"] = chkDelete.Checked;
        d["scroll_blockers"] = chkBlockers.Checked;
        var pr = new Dictionary<string, object> { ["blocker"] = protos.Blocker };
        foreach (var kv in protos.Lists) pr[kv.Key] = kv.Value;
        d["protos"] = pr;
        File.WriteAllText(dlg.FileName, JsonSerializer.Serialize(d, new JsonSerializerOptions { WriteIndented = true }));
    }

    void LoadPreset()
    {
        using var dlg = new OpenFileDialog { Filter = "MapGen9000 preset (*.json)|*.json" };
        if (dlg.ShowDialog(this) != DialogResult.OK) return;
        try
        {
            using var doc = JsonDocument.Parse(File.ReadAllText(dlg.FileName));
            var root = doc.RootElement;
            foreach (var s in sliders)
                if (root.TryGetProperty(s.Key, out var el) && el.ValueKind == JsonValueKind.Number)
                    s.SetDisplay(s.Percent ? el.GetDouble() * 100.0 : el.GetDouble());
            if (root.TryGetProperty("delete_outside", out var a) && (a.ValueKind == JsonValueKind.True || a.ValueKind == JsonValueKind.False)) chkDelete.Checked = a.GetBoolean();
            if (root.TryGetProperty("scroll_blockers", out var b) && (b.ValueKind == JsonValueKind.True || b.ValueKind == JsonValueKind.False)) chkBlockers.Checked = b.GetBoolean();
            if (root.TryGetProperty("protos", out var pr) && pr.ValueKind == JsonValueKind.Object)
            {
                var np = new Protos();
                if (pr.TryGetProperty("blocker", out var bl) && bl.ValueKind == JsonValueKind.Number) np.Blocker = bl.GetInt32();
                foreach (var key in np.Lists.Keys.ToList())
                    if (pr.TryGetProperty(key, out var arr) && arr.ValueKind == JsonValueKind.Array)
                    {
                        var ids = arr.EnumerateArray().Where(e => e.ValueKind == JsonValueKind.Number).Select(e => e.GetInt32()).ToArray();
                        if (ids.Length > 0) np.Lists[key] = ids;
                    }
                protos = np;
            }
            Schedule();
        }
        catch (Exception ex) { MessageBox.Show(this, ex.Message, "MapGen9000", MessageBoxButtons.OK, MessageBoxIcon.Error); }
    }
}

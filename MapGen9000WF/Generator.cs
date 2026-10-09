using System.Globalization;
using System.Numerics;
using System.Text;

namespace MapGen9000;

/// <summary>All generator settings. Percent-style values are stored as fractions (0.04 = 4 %).</summary>
public sealed class GenParams
{
    public int Size = 200, Seed = 2967, Octaves = 3;
    public double Persistence = 0.30, Density = 0.6;
    public double Corn = 0.04, DryTrees = 0.03, Trees = 0.12, Rocks = 0.025, Cactuses = 0.025,
                  Grass = 0.14, Misc = 0.02, Barrels = 0.01;
    public double GrassMin = 0.0, GrassMax = 0.75, TreesMin = 0.4, TreesMax = 1.0, PatchGrass = 1.5;
    public bool DeleteOutside = true, ScrollBlockers = true;
    public Protos Protos = new();
}

/// <summary>Scenery prototype ids per category.</summary>
public sealed class Protos
{
    public int Blocker = 4012;
    public Dictionary<string, int[]> Lists = new()
    {
        ["corn"] = new[] { 2369, 2370, 2371 },
        ["dry_trees"] = new[] { 2316, 2317, 2318, 2319, 2320, 2321 },
        ["trees"] = new[] { 2066, 2943, 2944, 2945, 2946, 2947 },
        ["rocks"] = new[] { 2090, 2091, 2092, 2093 },
        ["cactuses"] = new[] { 2064, 2065 },
        ["grass"] = new[] { 2102, 2103, 2104, 2105, 2127 },
        ["misc"] = new[] { 2101, 2106, 2107, 2108, 2109, 2110, 2116, 2117, 2118, 2121, 2122, 2123, 2124,
                           2082, 2083, 2084, 2085, 2086, 2063, 2434, 2431 },
        ["barrels"] = new[] { 2005, 2006, 2001, 2396, 2397, 2398, 2399, 2551, 2552 },
    };
}

public sealed class MapData
{
    public int N, M;                       // N = hex size, M = N / 2 = tile grid size
    public GenParams P = new();
    public double[] Noise = Array.Empty<double>();   // [y * N + x]
    public bool[] GroundA = Array.Empty<bool>();     // true = main ground (edg5xxx), false = rough patch
    public bool[] Ins = Array.Empty<bool>();         // playable hexes
    public bool[] TileCells = Array.Empty<bool>();   // [ty * M + tx]
    public int TileCount;
    public List<(int proto, int x, int y)> Objects = new();
    public List<(int x, int y, int tile)> Tiles;
}

public static class Generator
{
    // ------------------------------------------------------------------ noise
    public static double[] FractalNoise(int n, int seed, int octaves, double persistence)
    {
        var rng = new Random(seed);
        var outp = new double[n * n];
        double amp = 1.0, total = 0.0;
        for (int o = 0; o < Math.Max(1, octaves); o++)
        {
            int cells = 4 * (1 << o);
            int gs = cells + 2;
            var g = new double[gs * gs];
            for (int i = 0; i < g.Length; i++) g[i] = rng.NextDouble();
            var idx = new int[n];
            var f = new double[n];
            for (int i = 0; i < n; i++)
            {
                double t = (double)i * cells / n;
                idx[i] = (int)t;
                double fr = t - idx[i];
                f[i] = fr * fr * (3 - 2 * fr);
            }
            for (int y = 0; y < n; y++)
            {
                int iy = idx[y]; double fy = f[y];
                for (int x = 0; x < n; x++)
                {
                    int ix = idx[x]; double fx = f[x];
                    double a = g[iy * gs + ix], b = g[iy * gs + ix + 1];
                    double c = g[(iy + 1) * gs + ix], d = g[(iy + 1) * gs + ix + 1];
                    outp[y * n + x] += ((a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy) * amp;
                }
            }
            total += amp;
            amp *= persistence < 0.25 ? persistence * 4 : persistence;
        }
        double mn = double.MaxValue, mx = double.MinValue;
        for (int i = 0; i < outp.Length; i++) { outp[i] /= total; mn = Math.Min(mn, outp[i]); mx = Math.Max(mx, outp[i]); }
        for (int i = 0; i < outp.Length; i++) outp[i] = (outp[i] - mn) / (mx - mn + 1e-9);
        return outp;
    }

    // ------------------------------------------------------------------ playable area
    static (double a, double b, double c, double d) Bounds(int n)
    {
        double umin = Math.Floor(0.25 * n + 0.25);
        double vmin = Math.Ceiling(-0.75 * n + 0.25);
        return (umin, umin + n - 0.5, vmin, vmin + n - 0.5);
    }

    static bool Inside(int x, int y, int n)
    {
        var (a, b, c, d) = Bounds(n);
        double u = y + x / 2.0, v = y - 1.5 * x;
        return u >= a && u <= b && v >= c && v <= d;
    }

    static bool InsideTiles(int x, int y, int n)
    {
        var (a, b, c, d) = Bounds(n);
        double u = y + x / 2.0, v = y - 1.5 * x;
        return u >= a - 2 && u <= b + 0.5 && v >= c - 1 && v <= d + 2.5;
    }

    static readonly (int dx, int dy)[] BlockEven = { (-1, 0), (-1, 1), (0, 1), (1, 0) };
    static readonly (int dx, int dy)[] BlockOdd = { (-1, -1), (-1, 0), (0, 1), (1, -1) };

    // ------------------------------------------------------------------ generate
    public static MapData Generate(GenParams p)
    {
        int n = p.Size / 2 * 2;
        if (n < 10) throw new ArgumentException("Can't be less than ten.");
        int m = n / 2;
        var rng = new Random(p.Seed + 1);
        var noise = FractalNoise(n, p.Seed, p.Octaves, p.Persistence);
        bool dele = p.DeleteOutside;

        var ins = new bool[n * n];
        var tins = new bool[n * n];
        for (int y = 0; y < n; y++)
            for (int x = 0; x < n; x++)
            {
                ins[y * n + x] = !dele || Inside(x, y, n);
                tins[y * n + x] = !dele || InsideTiles(x, y, n);
            }

        var groundA = GroundMask(n, p.Seed, p.Density);

        var tileCells = new bool[m * m];
        int tileCount = 0;
        for (int ty = 0; ty < m; ty++)
            for (int tx = 0; tx < m; tx++)
            {
                int x = tx * 2, y = ty * 2;
                if (tins[y * n + x] && (!dele || ins[y * n + x])) { tileCells[ty * m + tx] = true; tileCount++; }
            }

        var taken = new HashSet<int>();
        var objs = new List<(int, int, int)>();
        bool Put(int proto, int x, int y)
        {
            if (x < 0 || y < 0 || x >= n || y >= n) return false;
            if (taken.Contains(y * n + x)) return false;
            if (dele && !ins[y * n + x]) return false;
            taken.Add(y * n + x);
            objs.Add((proto, x, y));
            return true;
        }
        int Pick(string key)
        {
            var l = p.Protos.Lists[key];
            return l[rng.Next(l.Length)];
        }

        if (p.ScrollBlockers)       // one-hex line along the border (reproduces dgen exactly)
        {
            bool Ins(int x, int y) => x >= 0 && y >= 0 && x < n && y < n && ins[y * n + x];
            for (int y = 0; y < n; y++)
                for (int x = 0; x < n; x++)
                {
                    if (!ins[y * n + x]) continue;
                    var nb = x % 2 == 0 ? BlockEven : BlockOdd;
                    bool edge = false;
                    foreach (var (dx, dy) in nb) if (!Ins(x + dx, y + dy)) { edge = true; break; }
                    if (edge) Put(p.Protos.Blocker, x, y);
                }
        }

        var r = new double[n * n];
        for (int i = 0; i < r.Length; i++) r[i] = rng.NextDouble();
        var clumpN = FractalNoise(n, p.Seed + 7, 3, 0.5);

        for (int y = 0; y < n; y++)
            for (int x = 0; x < n; x++)
            {
                int i = y * n + x;
                if (!ins[i]) continue;
                double v = noise[i];
                double clump = Math.Clamp(clumpN[i] * clumpN[i] * 4.0, 0, 1);
                double rr = r[i];
                double rc = rr / Math.Max(clump, 1e-3);
                double rg = rc / (groundA[i] ? 1.0 : Math.Max(p.PatchGrass, 1e-3));

                if (rr < p.Corn && v >= 0.20 && v <= 0.75) Put(Pick("corn"), x, y);
                else if (rc < p.DryTrees && v < 0.40) Put(Pick("dry_trees"), x, y);
                else if (v >= p.TreesMin && v <= p.TreesMax && rc < p.Trees) Put(Pick("trees"), x, y);
                else if (rc < p.Rocks) Put(Pick("rocks"), x, y);
                else if (rc < p.Cactuses && v < 0.75) Put(Pick("cactuses"), x, y);
                else if (v >= p.GrassMin && v <= p.GrassMax && rg < p.Grass) Put(Pick("grass"), x, y);
                else if (rc < p.Misc) Put(Pick("misc"), x, y);
                else if (rr < p.Barrels) Put(Pick("barrels"), x, y);
            }

        return new MapData
        {
            N = n, M = m, P = p, Noise = noise, GroundA = groundA, Ins = ins,
            TileCells = tileCells, TileCount = tileCount, Objects = objs,
        };
    }

    // ------------------------------------------------------------------ rough patch layout
    static readonly Dictionary<(int, int, long), bool[]> MaskCache = new();

   
/// <summary>
/// n x n at hex resolution.
/// true = main/light ground (edg5xxx).
/// Density 0 = all dark ground; 1 = all light ground.
/// Intermediate values retain organic blob patches.
/// </summary>
public static bool[] GroundMask(int n, int seed, double density)
{
    density = Math.Clamp(density, 0.0, 1.0);

    var key = (n, seed, (long)Math.Round(density * 1000));

    lock (MaskCache)
    {
        if (MaskCache.TryGetValue(key, out var hit))
            return hit;

        if (MaskCache.Count > 8)
            MaskCache.Clear();

        var g = new bool[n * n];

        // 0%: all dark ground.
        if (density <= 0.0)
        {
            MaskCache[key] = g;
            return g;
        }

        // 100%: all light/main ground.
        if (density >= 1.0)
        {
            Array.Fill(g, true);
            MaskCache[key] = g;
            return g;
        }

        // Intermediate values: preserve the existing blob pattern.
        int m = n / 2;
        var patch = BlobMask(m, seed, 1.0 - density);

        for (int y = 0; y < n; y++)
        {
            for (int x = 0; x < n; x++)
            {
                g[y * n + x] = !patch[(y / 2) * m + x / 2];
            }
        }

        MaskCache[key] = g;
        return g;
    }
}

    static bool[] Erode(bool[] a, int m)
    {
        var r = new bool[a.Length];
        for (int y = 0; y < m; y++)
            for (int x = 0; x < m; x++)
            {
                bool ok = true;
                for (int dy = -1; dy <= 1 && ok; dy++)
                    for (int dx = -1; dx <= 1; dx++)
                    {
                        int xx = x + dx, yy = y + dy;
                        if (xx < 0 || yy < 0 || xx >= m || yy >= m || !a[yy * m + xx]) { ok = false; break; }
                    }
                r[y * m + x] = ok;
            }
        return r;
    }

    static bool[] Dilate(bool[] a, int w, int h)
    {
        var r = new bool[a.Length];
        for (int y = 0; y < h; y++)
            for (int x = 0; x < w; x++)
            {
                bool any = false;
                for (int dy = -1; dy <= 1 && !any; dy++)
                    for (int dx = -1; dx <= 1; dx++)
                    {
                        int xx = x + dx, yy = y + dy;
                        if (xx >= 0 && yy >= 0 && xx < w && yy < h && a[yy * w + xx]) { any = true; break; }
                    }
                r[y * w + x] = any;
            }
        return r;
    }

    static double Gauss(Random rng)
    {
        double u1 = 1.0 - rng.NextDouble(), u2 = rng.NextDouble();
        return Math.Sqrt(-2.0 * Math.Log(u1)) * Math.Cos(2.0 * Math.PI * u2);
    }

    /// <summary>Separate organic patches (like dgen's maps) covering about `share` of the m x m tile grid.</summary>
    public static bool[] BlobMask(int m, int seed, double share, double median = 36, double sigma = 0.95,
                                  int minSize = 7, int maxSize = 330, int gap = 2)
    {
        var rng = new Random(seed + 99);
        double target = share * m * m * 1.1;
        var occ = new bool[m * m];
        var block = new bool[m * m];
        int total = 0;
        var sizes = new List<int>();
        int sum = 0;
        while (sum < target * 1.3 && sizes.Count < 400)
        {
            int a = (int)Math.Clamp(Math.Exp(Math.Log(median) + sigma * Gauss(rng)), minSize, maxSize);
            sizes.Add(a); sum += a;
        }
        sizes.Sort((x, y) => y.CompareTo(x));
        foreach (int A in sizes)
        {
            if (total >= target) break;
            for (int attempt = 0; attempt < 60; attempt++)
            {
                double cx = rng.NextDouble() * m, cy = rng.NextDouble() * m;
                double aspect = 1.0 + 1.2 * rng.NextDouble();
                double th = Math.PI * rng.NextDouble();
                double b = Math.Sqrt(A / (Math.PI * aspect)), a = aspect * b;
                double ph0 = 2 * Math.PI * rng.NextDouble(), ph1 = 2 * Math.PI * rng.NextDouble(), ph2 = 2 * Math.PI * rng.NextDouble();
                int R = (int)(a * 1.7) + 3;
                int x0 = Math.Max(0, (int)cx - R), x1 = Math.Min(m, (int)cx + R + 1);
                int y0 = Math.Max(0, (int)cy - R), y1 = Math.Min(m, (int)cy + R + 1);
                int w = x1 - x0, h = y1 - y0;
                var blob = new bool[w * h];
                int count = 0; bool clash = false;
                double cs = Math.Cos(th), sn = Math.Sin(th);
                for (int yy = 0; yy < h && !clash; yy++)
                    for (int xx = 0; xx < w; xx++)
                    {
                        double dx = x0 + xx - cx, dy = y0 + yy - cy;
                        double u = (dx * cs + dy * sn) / a, v = (-dx * sn + dy * cs) / b;
                        double phi = Math.Atan2(v, u);
                        double lim = 1 + 0.25 * Math.Sin(2 * phi + ph0) + 0.2 * Math.Sin(3 * phi + ph1) + 0.12 * Math.Sin(5 * phi + ph2);
                        if (Math.Sqrt(u * u + v * v) <= lim)
                        {
                            if (block[(y0 + yy) * m + x0 + xx]) { clash = true; break; }
                            blob[yy * w + xx] = true; count++;
                        }
                    }
                if (clash || count < minSize) continue;
                for (int yy = 0; yy < h; yy++)
                    for (int xx = 0; xx < w; xx++)
                        if (blob[yy * w + xx]) occ[(y0 + yy) * m + x0 + xx] = true;
                total += count;
                int X0 = Math.Max(0, x0 - gap), X1 = Math.Min(m, x1 + gap), Y0 = Math.Max(0, y0 - gap), Y1 = Math.Min(m, y1 + gap);
                int rw = X1 - X0, rh = Y1 - Y0;
                var reg = new bool[rw * rh];
                for (int yy = 0; yy < rh; yy++)
                    for (int xx = 0; xx < rw; xx++) reg[yy * rw + xx] = occ[(Y0 + yy) * m + X0 + xx];
                for (int k = 0; k < gap; k++) reg = Dilate(reg, rw, rh);
                for (int yy = 0; yy < rh; yy++)
                    for (int xx = 0; xx < rw; xx++)
                        if (reg[yy * rw + xx]) block[(Y0 + yy) * m + X0 + xx] = true;
                break;
            }
        }
        return Dilate(Erode(occ, m), m, m);        // drop 1-tile spikes
    }

    // ------------------------------------------------------------------ ground tiles
    const double Hard = 18.0;     // side mismatch above this is a visible seam
    const double Sigma = 6.0;     // smaller = stricter about matching sides
    static readonly ulong BulkMask = MakeMask(true);
    static readonly ulong PatchMask = MakeMask(false);

    static ulong MakeMask(bool bulk)
    {
        ulong r = 0;
        for (int i = 0; i < TileData.Count; i++)
            if ((TileData.Names[i][0] == '5') == bulk) r |= 1UL << i;
        return r;
    }

    static double Art(int d, int a, int b) => TileData.ArtErr[(d * TileData.Count + a) * TileData.Count + b];

    /// <summary>Fill m.Tiles. Rough patches come from m.GroundA; every patch tile is non-edg5xxx and the rest edg5xxx.</summary>
    public static void BuildTiles(MapData md)
    {
        int m = md.M, n = md.N, T = TileData.Count;
        var rng = new Random(md.P.Seed * 7919 + 1);

        // rough patch cells, tiny pieces (< 6 tiles) are dropped so no lonely edge tiles appear
        var patch = new bool[m * m];
        for (int i = 0; i < m * m; i++)
            patch[i] = md.TileCells[i] && !md.GroundA[((i / m) * 2) * n + (i % m) * 2];
        DropSmall(patch, m, 6);

        var dom = new ulong[m * m];
var init = new ulong[m * m];
for (int i = 0; i < m * m; i++) init[i] = dom[i] = patch[i] ? PatchMask : BulkMask;

        var nbr = new int[m * m][];
        for (int i = 0; i < m * m; i++)
        {
            if (!md.TileCells[i]) continue;
            int tx = i % m, ty = i / m;
            var l = new int[8];
            for (int d = 0; d < 8; d++)
            {
                int x = tx + TileData.Dirs[d].dx, y = ty + TileData.Dirs[d].dy;
                l[d] = (x >= 0 && y >= 0 && x < m && y < m && md.TileCells[y * m + x]) ? y * m + x : -1;
            }
            nbr[i] = l;
        }

        var cache = new Dictionary<(int, ulong), ulong>();
        ulong Allowed(int d, ulong dm)
        {
            if (cache.TryGetValue((d, dm), out var r)) return r;
            r = 0; ulong mm = dm;
            while (mm != 0) { int b = BitOperations.TrailingZeroCount(mm); r |= TileData.Adj[d][b]; mm &= mm - 1; }
            cache[(d, dm)] = r; return r;
        }

        var heap = new PriorityQueue<int, (int, double)>();
        void Push(int c) => heap.Enqueue(c, (BitOperations.PopCount(dom[c]), rng.NextDouble()));

        var stack = new Stack<int>();
        void Prop()
        {
            while (stack.Count > 0)
            {
                int c = stack.Pop(); ulong D = dom[c];
                for (int d = 0; d < 8; d++)
                {
                    int nb = nbr[c][d];
                    if (nb < 0) continue;
                    ulong nd = dom[nb] & Allowed(d, D);
                    if (nd != dom[nb] && nd != 0) { dom[nb] = nd; stack.Push(nb); Push(nb); }   // dead end: skipped, repaired below
                }
            }
        }

        var cellList = new List<int>();
        for (int i = 0; i < m * m; i++) if (md.TileCells[i]) cellList.Add(i);
        foreach (int c in cellList) { stack.Push(c); Prop(); }
        foreach (int c in cellList) Push(c);

        var res = new int[m * m];
        Array.Fill(res, -1);

        (int broken, double art) Cost(int c, int t)
        {
            int broken = 0; double art = 0;
            for (int d = 0; d < 8; d++)
            {
                int nb = nbr[c][d];
                if (nb < 0 || res[nb] < 0) continue;
                int o = res[nb];
                if (((TileData.Adj[d][t] >> o) & 1UL) == 0) broken++;
                if (d < 4) art += Art(d, t, o);
            }
            return (broken, art);
        }

        while (heap.TryDequeue(out int c, out var pr))
        {
            if (res[c] >= 0) continue;
            ulong D = dom[c];
            if (BitOperations.PopCount(D) != pr.Item1) { Push(c); continue; }
            if (pr.Item1 > 1)
            {
                var opts = new List<int>(); var w = new List<double>(); double sum = 0;
                for (int t = 0; t < T; t++)
                    if (((D >> t) & 1UL) != 0)
                    {
                        double wt = TileData.Weights[t] * Math.Exp(-Cost(c, t).art / Sigma);
                        opts.Add(t); w.Add(wt); sum += wt;
                    }
                double pick = rng.NextDouble() * sum; int chosen = opts[opts.Count - 1];
                for (int k = 0; k < opts.Count; k++) { pick -= w[k]; if (pick <= 0) { chosen = opts[k]; break; } }
                dom[c] = 1UL << chosen;
            }
            res[c] = BitOperations.TrailingZeroCount(dom[c]);
            stack.Push(c); Prop();
        }

        // local repair: fix broken rules first, then visible seams
        for (int sweep = 0; sweep < 40; sweep++)
        {
            var bad = new List<int>();
            foreach (int c in cellList)
            {
                var (b, a) = Cost(c, res[c]);
                if (b > 0 || a > Hard * 2) bad.Add(c);
            }
            if (bad.Count == 0) break;
            for (int i = bad.Count - 1; i > 0; i--) { int j = rng.Next(i + 1); (bad[i], bad[j]) = (bad[j], bad[i]); }
            foreach (int c in bad)
            {
                var cur = Cost(c, res[c]);
                double curv = cur.broken * 60 + cur.art;
                double bestV = double.MaxValue; int bestT = res[c];
                for (int t = 0; t < T; t++)
                {
                    if (((init[c] >> t) & 1UL) == 0) continue;
                    var (b, a) = Cost(c, t);
                    double v = b * 60 + a + rng.NextDouble() * 1e-6;
                    if (v < bestV) { bestV = v; bestT = t; }
                }
                if (bestV < curv) res[c] = bestT;
            }
        }

        var tiles = new List<(int, int, int)>(cellList.Count);
        foreach (int c in cellList) tiles.Add(((c % m) * 2, (c / m) * 2, res[c]));
        md.Tiles = tiles;
    }

    static void DropSmall(bool[] patch, int m, int minSize)
    {
        var seen = new bool[m * m];
        for (int s = 0; s < m * m; s++)
        {
            if (!patch[s] || seen[s]) continue;
            var comp = new List<int>(); var st = new Stack<int>();
            st.Push(s); seen[s] = true;
            while (st.Count > 0)
            {
                int p = st.Pop(); comp.Add(p);
                int px = p % m, py = p / m;
                for (int dy = -1; dy <= 1; dy++)
                    for (int dx = -1; dx <= 1; dx++)
                    {
                        int x = px + dx, y = py + dy;
                        if (x < 0 || y < 0 || x >= m || y >= m) continue;
                        int q = y * m + x;
                        if (patch[q] && !seen[q]) { seen[q] = true; st.Push(q); }
                    }
            }
            if (comp.Count < minSize) foreach (int c in comp) patch[c] = false;
        }
    }

    // ------------------------------------------------------------------ output
    public static void WriteFomap(MapData md, string path)
    {
        if (md.Tiles == null) BuildTiles(md);
        var sb = new StringBuilder();
        string w = (md.N / 2).ToString(CultureInfo.InvariantCulture), n = md.N.ToString(CultureInfo.InvariantCulture);
        sb.Append("[Header]\r\nVersion\t4\r\nMaxHexX\t").Append(n).Append("\r\nMaxHexY\t").Append(n)
          .Append("\r\nWorkHexX\t").Append(w).Append("\r\nWorkHexY\t").Append(w)
          .Append("\r\nScriptModule\t-\r\nScriptFunc\t-\r\nNoLogOut\t0\r\nTime\t0\r\nDayTime\t300  600  1140 1380\r\n")
          .Append("DayColor0\t18  18  53\r\nDayColor1\t128 128 128\r\nDayColor2\t103 95  86\r\nDayColor3\t51  40  29\r\n\r\n[Tiles]\r\n");
        foreach (var (x, y, t) in md.Tiles)
            sb.Append("tile \t ").Append(x).Append(" \t ").Append(y).Append(" \t art\\tiles\\edg").Append(TileData.Names[t]).Append(".frm\r\n");
        sb.Append("\r\n[Objects]\r\n");
        foreach (var (pr, x, y) in md.Objects)
            sb.Append("MapObjType\t2\r\nProtoId\t").Append(pr).Append("\r\nMapX\t").Append(x).Append("\r\nMapY\t").Append(y).Append("\r\n\r\n");
        File.WriteAllText(path, sb.ToString(), Encoding.Latin1);
    }

    // ------------------------------------------------------------------ preview
    const double Aspect = 1.38;

    /// <summary>Upright landscape preview of the playable area, 24-bit RGB (3 bytes per pixel).</summary>
    public static (byte[] rgb, int w, int h) Render(MapData md, int w)
    {
        int n = md.N, h = (int)(w / Aspect);
        var img = new byte[n * n * 3];
        void Set(int i, int r, int g, int b) { img[i * 3] = (byte)r; img[i * 3 + 1] = (byte)g; img[i * 3 + 2] = (byte)b; }
        for (int i = 0; i < n * n; i++)
        {
            if (!md.Ins[i]) Set(i, 40, 40, 40);
            else if (md.GroundA[i]) Set(i, 146, 108, 80);
            else Set(i, 122, 112, 72);
        }
        var col = new Dictionary<int, (int, int, int)> { [md.P.Protos.Blocker] = (245, 245, 245) };
        var colors = new Dictionary<string, (int, int, int)>
        {
            ["corn"] = (210, 180, 70), ["dry_trees"] = (105, 78, 48), ["trees"] = (28, 62, 36), ["rocks"] = (80, 78, 76),
            ["cactuses"] = (45, 105, 55), ["grass"] = (205, 170, 105), ["misc"] = (105, 82, 58), ["barrels"] = (115, 82, 48),
        };
        foreach (var kv in colors)
            if (md.P.Protos.Lists.TryGetValue(kv.Key, out var ids)) foreach (int id in ids) col[id] = kv.Value;
        foreach (var (pr, x, y) in md.Objects)
        {
            var c = col.TryGetValue(pr, out var cc) ? cc : (255, 0, 255);
            Set(y * n + x, c.Item1, c.Item2, c.Item3);
        }

        var outp = new byte[w * h * 3];
        for (int i = 0; i < outp.Length; i++) outp[i] = 40;
        for (int j = 0; j < h; j++)
        {
            double U = 0.25 * n + (1.25 * n - 0.25 * n) * j / Math.Max(1, h - 1);
            for (int i = 0; i < w; i++)
            {
                double V = -0.75 * n + (0.25 * n + 0.75 * n) * i / Math.Max(1, w - 1);
                int X = (int)Math.Round((U - V) / 2), Y = (int)Math.Round(U - X / 2.0);
                if (X < 0 || X >= n || Y < 0 || Y >= n) continue;
                int s = (Y * n + X) * 3, d = (j * w + i) * 3;
                outp[d] = img[s]; outp[d + 1] = img[s + 1]; outp[d + 2] = img[s + 2];
            }
        }
        return (outp, w, h);
    }
}

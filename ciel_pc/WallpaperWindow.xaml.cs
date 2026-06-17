using System;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Interop;
using System.Windows.Threading;
using SkiaSharp;
using SkiaSharp.Views.Desktop;
using Forms = System.Windows.Forms;

namespace Ciel;

// Levande Ciel-bakgrunn: ein WPF-vindauge teikna BAK skrivebordsikona via
// WorkerW-trikset (Progman 0x052C). Native oppløysing i sanntid → ingen
// transcode-cache eller skalerings-problem. Éin orb per skjerm. Ingen admin.
public partial class WallpaperWindow : Window
{
    const int GWL_EXSTYLE = -20, WS_EX_NOACTIVATE = 0x08000000, WS_EX_TOOLWINDOW = 0x80;

    [DllImport("user32.dll")] static extern IntPtr FindWindow(string cls, string? name);
    [DllImport("user32.dll")] static extern IntPtr FindWindowEx(IntPtr parent, IntPtr after, string cls, string? name);
    [DllImport("user32.dll")] static extern IntPtr SendMessageTimeout(IntPtr hwnd, uint msg, IntPtr w, IntPtr l, uint flags, uint timeout, out IntPtr res);
    [DllImport("user32.dll")] static extern bool EnumWindows(EnumWindowsProc cb, IntPtr l);
    [DllImport("user32.dll")] static extern IntPtr SetParent(IntPtr child, IntPtr parent);
    [DllImport("user32.dll")] static extern int GetWindowLong(IntPtr h, int i);
    [DllImport("user32.dll")] static extern int SetWindowLong(IntPtr h, int i, int v);
    [DllImport("user32.dll")] static extern bool MoveWindow(IntPtr h, int x, int y, int w, int ht, bool repaint);
    delegate bool EnumWindowsProc(IntPtr h, IntPtr l);

    readonly Orb _orb = new();
    readonly Stopwatch _clock = Stopwatch.StartNew();
    DispatcherTimer? _timer;
    SKColor _gold = new(0xEF, 0x9F, 0x27), _targetGold = new(0xEF, 0x9F, 0x27);
    bool _girl = true;
    readonly CielClient _client = new("127.0.0.1:8765");
    const double Fps = 20;   // bakgrunn: lågare fps held CPU nede

    public WallpaperWindow()
    {
        InitializeComponent();
        Loaded += OnLoaded;
        Closed += (_, _) => _timer?.Stop();
    }

    void OnLoaded(object? s, RoutedEventArgs e)
    {
        _timer = new DispatcherTimer(DispatcherPriority.Render)
        { Interval = TimeSpan.FromMilliseconds(1000.0 / Fps) };
        _timer.Tick += (_, _) => { EaseColour(); Skia.InvalidateVisual(); };
        _timer.Start();
        _client.OnColour = hex => { if (TryHex(hex, out var c)) _targetGold = c; };
        _client.Start();
    }

    protected override void OnSourceInitialized(EventArgs e)
    {
        base.OnSourceInitialized(e);
        var hwnd = new WindowInteropHelper(this).Handle;
        int ex = GetWindowLong(hwnd, GWL_EXSTYLE);
        SetWindowLong(hwnd, GWL_EXSTYLE, ex | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW);

        // Be Progman om å lage WorkerW bak ikona
        IntPtr progman = FindWindow("Progman", null);
        SendMessageTimeout(progman, 0x052C, IntPtr.Zero, IntPtr.Zero, 0, 1000, out _);
        IntPtr workerw = FindWorkerW();
        if (workerw == IntPtr.Zero) workerw = progman;   // Win11-fallback

        var vs = Forms.SystemInformation.VirtualScreen;
        SetParent(hwnd, workerw);
        MoveWindow(hwnd, 0, 0, vs.Width, vs.Height, true);   // dekk heile virtuelle skrivebordet
    }

    static IntPtr FindWorkerW()
    {
        IntPtr found = IntPtr.Zero;
        EnumWindows((top, l) =>
        {
            if (FindWindowEx(top, IntPtr.Zero, "SHELLDLL_DefView", null) != IntPtr.Zero)
                found = FindWindowEx(IntPtr.Zero, top, "WorkerW", null);
            return true;
        }, IntPtr.Zero);
        return found;
    }

    void EaseColour()
    {
        const float k = 0.12f;
        byte L(byte a, byte b) => (byte)(a + (b - a) * k);
        _gold = new SKColor(L(_gold.Red, _targetGold.Red), L(_gold.Green, _targetGold.Green), L(_gold.Blue, _targetGold.Blue));
    }

    static bool TryHex(string hex, out SKColor col)
    {
        col = default;
        if (string.IsNullOrEmpty(hex)) return false;
        hex = hex.TrimStart('#');
        if (hex.Length != 6) return false;
        try { col = new SKColor(Convert.ToByte(hex.Substring(0, 2), 16), Convert.ToByte(hex.Substring(2, 2), 16), Convert.ToByte(hex.Substring(4, 2), 16)); return true; }
        catch { return false; }
    }

    void OnPaint(object? s, SKPaintSurfaceEventArgs e)
    {
        var c = e.Surface.Canvas;
        c.Clear(SKColors.Black);
        double t = _clock.Elapsed.TotalSeconds;
        var vs = Forms.SystemInformation.VirtualScreen;
        int sw = e.Info.Width, sh = e.Info.Height;
        // Éin orb sentrert på kvar skjerm (proporsjonalt → DPI-trygt)
        foreach (var scr in Forms.Screen.AllScreens)
        {
            double fx = (scr.Bounds.X - vs.X) / (double)vs.Width;
            double fy = (scr.Bounds.Y - vs.Y) / (double)vs.Height;
            double fw = scr.Bounds.Width / (double)vs.Width;
            double fh = scr.Bounds.Height / (double)vs.Height;
            float cx = (float)((fx + fw / 2) * sw);
            float cy = (float)((fy + fh / 2) * sh);
            float maxR = (float)(Math.Min(fw * sw, fh * sh) * 0.58);
            _orb.RenderAt(c, cx, cy, maxR, t, _gold, _girl);
        }
    }
}

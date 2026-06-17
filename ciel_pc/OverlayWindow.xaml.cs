using System;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Interop;
using System.Windows.Threading;
using SkiaSharp;
using SkiaSharp.Views.Desktop;

namespace Ciel;

public partial class OverlayWindow : Window
{
    // ── Win32: gjer vindauget click-through (mus går RETT GJENNOM til skrivebordet) ──
    const int GWL_EXSTYLE = -20;
    const int WS_EX_TRANSPARENT = 0x00000020;
    const int WS_EX_LAYERED = 0x00080000;
    const int WS_EX_TOOLWINDOW = 0x00000080;   // skjul frå Alt+Tab
    const int WS_EX_NOACTIVATE = 0x08000000;   // stel aldri fokus

    [DllImport("user32.dll")] static extern int GetWindowLong(IntPtr hwnd, int index);
    [DllImport("user32.dll")] static extern int SetWindowLong(IntPtr hwnd, int index, int newStyle);

    readonly Orb _orb = new();
    readonly Stopwatch _clock = Stopwatch.StartNew();
    DispatcherTimer? _timer;

    // Gull standard + girl mode på (som tabletten). Mål-verdiar settast av WS-sync;
    // render-fargen lerp-ar mjukt mot målet kvar frame (same kjensle som tabletten).
    SKColor _gold = new(0xEF, 0x9F, 0x27);
    SKColor _targetGold = new(0xEF, 0x9F, 0x27);
    bool _girl = true;
    bool _targetGirl = true;

    // Etappe B: speglar modus/farge frå hjernen i sanntid (lokal tilkobling).
    readonly CielClient _client = new("127.0.0.1:8765");

    const double IdleFps = 24;       // hjørne-orb: rikeleg for sakte pust, låg CPU
    const double EdgeMargin = 24;        // avstand frå skjermkanten

    public OverlayWindow()
    {
        InitializeComponent();
        Loaded += OnLoaded;
        Closed += (_, _) => _timer?.Stop();
    }

    void OnLoaded(object? sender, RoutedEventArgs e)
    {
        DockBottomRight();
        _timer = new DispatcherTimer(DispatcherPriority.Render)
        {
            Interval = TimeSpan.FromMilliseconds(1000.0 / IdleFps)
        };
        _timer.Tick += (_, _) => { EaseColour(); Skia.InvalidateVisual(); };
        _timer.Start();

        // Mode/farge-sync med tabletten via hjernen
        _client.OnColour = hex => { if (TryHex(hex, out var col)) _targetGold = col; };
        _client.OnGirl = g => _targetGirl = g;
        _client.Start();
    }

    // Lerp gjeldande farge mot målet → mjuk overgang når modus skiftar.
    void EaseColour()
    {
        const float k = 0.12f;
        byte L(byte a, byte b) => (byte)(a + (b - a) * k);
        _gold = new SKColor(L(_gold.Red, _targetGold.Red),
                            L(_gold.Green, _targetGold.Green),
                            L(_gold.Blue, _targetGold.Blue));
        _girl = _targetGirl;
    }

    static bool TryHex(string hex, out SKColor col)
    {
        col = default;
        if (string.IsNullOrEmpty(hex)) return false;
        hex = hex.TrimStart('#');
        if (hex.Length != 6) return false;
        try
        {
            col = new SKColor(
                Convert.ToByte(hex.Substring(0, 2), 16),
                Convert.ToByte(hex.Substring(2, 2), 16),
                Convert.ToByte(hex.Substring(4, 2), 16));
            return true;
        }
        catch { return false; }
    }

    void DockBottomRight()
    {
        var wa = SystemParameters.WorkArea; // i DIP — toler DPI-skalering
        Left = wa.Right - Width - EdgeMargin;
        Top = wa.Bottom - Height - EdgeMargin;
    }

    protected override void OnSourceInitialized(EventArgs e)
    {
        base.OnSourceInitialized(e);
        var hwnd = new WindowInteropHelper(this).Handle;
        int ex = GetWindowLong(hwnd, GWL_EXSTYLE);
        // Click-through + lag + verktøyvindauge + aldri-aktiver
        SetWindowLong(hwnd, GWL_EXSTYLE,
            ex | WS_EX_TRANSPARENT | WS_EX_LAYERED | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE);
    }

    void OnPaint(object? sender, SKPaintSurfaceEventArgs e)
    {
        double t = _clock.Elapsed.TotalSeconds;
        _orb.Render(e.Surface.Canvas, e.Info.Width, e.Info.Height, t, _gold, _girl);
    }
}

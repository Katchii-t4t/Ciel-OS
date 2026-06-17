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

    // Etappe A: gull standard + girl mode på (som tabletten). Etappe B sync-ar dette.
    SKColor _gold = new(0xEF, 0x9F, 0x27);
    bool _girl = true;

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
        _timer.Tick += (_, _) => Skia.InvalidateVisual();
        _timer.Start();
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

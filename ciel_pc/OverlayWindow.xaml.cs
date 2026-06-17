using System;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Input;
using System.Windows.Interop;
using System.Windows.Threading;
using SkiaSharp;
using SkiaSharp.Views.Desktop;

namespace Ciel;

public partial class OverlayWindow : Window
{
    // ── Win32 ─────────────────────────────────────────────────────────────────
    const int GWL_EXSTYLE = -20;
    const int WS_EX_TRANSPARENT = 0x00000020;
    const int WS_EX_LAYERED = 0x00080000;
    const int WS_EX_TOOLWINDOW = 0x00000080;
    const int WS_EX_NOACTIVATE = 0x08000000;

    const int WM_HOTKEY = 0x0312;
    const uint MOD_ALT = 0x0001, MOD_CONTROL = 0x0002, MOD_NOREPEAT = 0x4000;
    const uint VK_SPACE = 0x20;
    const int HOTKEY_ID = 0xC1E1;   // "CIEl"

    [DllImport("user32.dll")] static extern int GetWindowLong(IntPtr hwnd, int index);
    [DllImport("user32.dll")] static extern int SetWindowLong(IntPtr hwnd, int index, int newStyle);
    [DllImport("user32.dll")] static extern bool RegisterHotKey(IntPtr hwnd, int id, uint mod, uint vk);
    [DllImport("user32.dll")] static extern bool UnregisterHotKey(IntPtr hwnd, int id);

    readonly Orb _orb = new();
    readonly Stopwatch _clock = Stopwatch.StartNew();
    DispatcherTimer? _timer;
    IntPtr _hwnd;

    SKColor _gold = new(0xEF, 0x9F, 0x27);
    SKColor _targetGold = new(0xEF, 0x9F, 0x27);
    bool _girl = true;
    readonly CielClient _client = new("127.0.0.1:8765");

    const double IdleFps = 30;       // litt høgare under animert overgang; framleis billeg
    const double EdgeMargin = 24;
    const double CornerSize = 220;

    bool _full;
    double _curL, _curT, _curW, _curH;   // animert (gjeldande) vindaugsboks
    double _tgtL, _tgtT, _tgtW, _tgtH;   // mål

    public OverlayWindow()
    {
        InitializeComponent();
        Loaded += OnLoaded;
        KeyDown += OnKeyDown;
        Closed += (_, _) => { _timer?.Stop(); if (_hwnd != IntPtr.Zero) UnregisterHotKey(_hwnd, HOTKEY_ID); };
    }

    void OnLoaded(object? sender, RoutedEventArgs e)
    {
        SetCornerTarget();
        _curL = _tgtL; _curT = _tgtT; _curW = _tgtW; _curH = _tgtH;
        ApplyBounds();

        _timer = new DispatcherTimer(DispatcherPriority.Render)
        {
            Interval = TimeSpan.FromMilliseconds(1000.0 / IdleFps)
        };
        _timer.Tick += (_, _) => { AnimateBounds(); EaseColour(); Skia.InvalidateVisual(); };
        _timer.Start();

        _client.OnColour = hex => { if (TryHex(hex, out var col)) _targetGold = col; };
        _client.Start();
    }

    // ── Hjørne / full presence ─────────────────────────────────────────────────
    void SetCornerTarget()
    {
        var wa = SystemParameters.WorkArea;
        _tgtW = CornerSize; _tgtH = CornerSize;
        _tgtL = wa.Right - CornerSize - EdgeMargin;
        _tgtT = wa.Bottom - CornerSize - EdgeMargin;
    }

    void SetFullTarget()
    {
        var wa = SystemParameters.WorkArea;
        _tgtL = wa.Left; _tgtT = wa.Top; _tgtW = wa.Width; _tgtH = wa.Height;
    }

    void ToggleFull()
    {
        _full = !_full;
        if (_full)
        {
            SetFullTarget();
            SetClickThrough(false);   // fang input — skriv/snakk til Ciel
            Activate();
            Focus();
        }
        else
        {
            SetCornerTarget();
            SetClickThrough(true);    // tilbake til stille, click-through hjørne
        }
    }

    void AnimateBounds()
    {
        const double k = 0.28;
        _curL += (_tgtL - _curL) * k;
        _curT += (_tgtT - _curT) * k;
        _curW += (_tgtW - _curW) * k;
        _curH += (_tgtH - _curH) * k;
        if (Math.Abs(_curL - _tgtL) < 0.6 && Math.Abs(_curW - _tgtW) < 0.6)
        { _curL = _tgtL; _curT = _tgtT; _curW = _tgtW; _curH = _tgtH; }
        ApplyBounds();
    }

    void ApplyBounds()
    {
        Left = _curL; Top = _curT;
        Width = Math.Max(1, _curW); Height = Math.Max(1, _curH);
    }

    void OnKeyDown(object sender, KeyEventArgs e)
    {
        if (_full && e.Key == Key.Escape) ToggleFull();   // Esc = avvis
    }

    // ── Window styles ───────────────────────────────────────────────────────────
    protected override void OnSourceInitialized(EventArgs e)
    {
        base.OnSourceInitialized(e);
        _hwnd = new WindowInteropHelper(this).Handle;
        SetClickThrough(true);
        // Global hurtigtast: Ctrl+Alt+Space (Win+Space er teken av Windows).
        RegisterHotKey(_hwnd, HOTKEY_ID, MOD_CONTROL | MOD_ALT | MOD_NOREPEAT, VK_SPACE);
        HwndSource.FromHwnd(_hwnd)?.AddHook(WndProc);
    }

    IntPtr WndProc(IntPtr hwnd, int msg, IntPtr wParam, IntPtr lParam, ref bool handled)
    {
        if (msg == WM_HOTKEY && wParam.ToInt32() == HOTKEY_ID)
        {
            ToggleFull();
            handled = true;
        }
        return IntPtr.Zero;
    }

    void SetClickThrough(bool through)
    {
        if (_hwnd == IntPtr.Zero) return;
        int ex = GetWindowLong(_hwnd, GWL_EXSTYLE) | WS_EX_LAYERED | WS_EX_TOOLWINDOW;
        if (through) ex |= WS_EX_TRANSPARENT | WS_EX_NOACTIVATE;
        else ex &= ~(WS_EX_TRANSPARENT | WS_EX_NOACTIVATE);
        SetWindowLong(_hwnd, GWL_EXSTYLE, ex);
    }

    // ── Farge-easing ────────────────────────────────────────────────────────────
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
        try
        {
            col = new SKColor(Convert.ToByte(hex.Substring(0, 2), 16),
                              Convert.ToByte(hex.Substring(2, 2), 16),
                              Convert.ToByte(hex.Substring(4, 2), 16));
            return true;
        }
        catch { return false; }
    }

    void OnPaint(object? sender, SKPaintSurfaceEventArgs e)
    {
        double t = _clock.Elapsed.TotalSeconds;
        _orb.Render(e.Surface.Canvas, e.Info.Width, e.Info.Height, t, _gold, _girl);
    }
}

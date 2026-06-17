using System;
using System.IO;
using System.Runtime.InteropServices;
using SkiaSharp;

namespace Ciel;

// Set Ciel-orben som Windows-skrivebordsbakgrunn (statisk bilete på svart, same
// look som tablet-heimen). Per-brukar, ingen admin, ingen shell-erstatning.
// Brukar IDesktopWallpaper (moderne API) for å setje bakgrunnen på KVAR skjerm
// med Fill — viktig på fleirskjerm-oppsett. Fallback: SystemParametersInfo.
public static class Wallpaper
{
    [DllImport("user32.dll")] static extern int GetSystemMetrics(int n);
    [DllImport("user32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    static extern bool SystemParametersInfo(uint action, uint uParam, string pvParam, uint fWinIni);
    const uint SPI_SETDESKWALLPAPER = 0x0014, SPIF_UPDATEINIFILE = 0x01, SPIF_SENDCHANGE = 0x02;

    [StructLayout(LayoutKind.Sequential)] struct RECT { public int L, T, R, B; }

    [ComImport, Guid("B92B56A9-8B55-4E14-9A89-0199BBB6F93B"),
     InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface IDesktopWallpaper
    {
        void SetWallpaper([MarshalAs(UnmanagedType.LPWStr)] string monitorID,
                          [MarshalAs(UnmanagedType.LPWStr)] string wallpaper);
        [return: MarshalAs(UnmanagedType.LPWStr)] string GetWallpaper([MarshalAs(UnmanagedType.LPWStr)] string monitorID);
        [return: MarshalAs(UnmanagedType.LPWStr)] string GetMonitorDevicePathAt(uint monitorIndex);
        uint GetMonitorDevicePathCount();
        void GetMonitorRECT([MarshalAs(UnmanagedType.LPWStr)] string monitorID, out RECT rect);
        void SetBackgroundColor(uint color);
        uint GetBackgroundColor();
        void SetPosition(int position);   // 4 = Fill
        int GetPosition();
    }

    [ComImport, Guid("C2CF3110-460E-4fc1-B9D0-8A1C0C9CC4BD")] class DesktopWallpaperClass { }

    static readonly string Dir = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Ciel");
    static readonly object Gate = new();

    public static void Set(Orb orb, SKColor gold, bool girl)
    {
      lock (Gate)
      {
        try
        {
            int w = GetSystemMetrics(0), h = GetSystemMetrics(1);
            if (w <= 0 || h <= 0) { w = 1920; h = 1080; }

            using var surface = SKSurface.Create(new SKImageInfo(w, h));
            orb.Render(surface.Canvas, w, h, 0.8, gold, girl, SKColors.Black, 0.70, round: false);

            Directory.CreateDirectory(Dir);
            string outPath = Path.Combine(Dir, $"wallpaper_{DateTime.Now.Ticks}.png");
            using (var img = surface.Snapshot())
            using (var data = img.Encode(SKEncodedImageFormat.Png, 90))
            using (var fs = File.Create(outPath))
                data.SaveTo(fs);

            // Moderne API: set på KVAR skjerm med Fill (fiksar svart 2. skjerm).
            bool ok = false;
            try
            {
                var dw = (IDesktopWallpaper)new DesktopWallpaperClass();
                dw.SetPosition(4); // Fill
                uint n = dw.GetMonitorDevicePathCount();
                for (uint i = 0; i < n; i++)
                {
                    string id = dw.GetMonitorDevicePathAt(i);
                    if (!string.IsNullOrEmpty(id)) dw.SetWallpaper(id, outPath);
                }
                ok = n > 0;
            }
            catch { ok = false; }

            if (!ok)   // fallback
                SystemParametersInfo(SPI_SETDESKWALLPAPER, 0, outPath, SPIF_UPDATEINIFILE | SPIF_SENDCHANGE);

            foreach (var f in Directory.GetFiles(Dir, "wallpaper*.png"))
                if (f != outPath) try { File.Delete(f); } catch { }
        }
        catch { /* bakgrunn er kosmetisk — aldri krasj overlay-en */ }
      }
    }
}

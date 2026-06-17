using System;
using System.IO;
using System.Runtime.InteropServices;
using SkiaSharp;

namespace Ciel;

// Set Ciel-orben som Windows-skrivebordsbakgrunn (statisk bilete på svart, same
// look som tablet-heimen). Per-brukar, ingen admin, ingen shell-erstatning.
// Vert regenerert når modus-fargen skiftar → bakgrunnen held seg i sync.
public static class Wallpaper
{
    [DllImport("user32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    static extern bool SystemParametersInfo(uint action, uint uParam, string pvParam, uint fWinIni);
    [DllImport("user32.dll")] static extern int GetSystemMetrics(int n);

    const uint SPI_SETDESKWALLPAPER = 0x0014;
    const uint SPIF_UPDATEINIFILE = 0x01, SPIF_SENDCHANGE = 0x02;

    static readonly string OutPath = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
        "Ciel", "wallpaper.png");

    public static void Set(Orb orb, SKColor gold, bool girl)
    {
        try
        {
            int w = GetSystemMetrics(0), h = GetSystemMetrics(1);   // primær skjerm i pikslar
            if (w <= 0 || h <= 0) { w = 2560; h = 1440; }

            using var surface = SKSurface.Create(new SKImageInfo(w, h));
            // Orb-renderaren er trygg å kalle frå bakgrunnstråd (les berre faste data).
            orb.Render(surface.Canvas, w, h, 0.8, gold, girl, SKColors.Black);

            Directory.CreateDirectory(Path.GetDirectoryName(OutPath)!);
            using (var img = surface.Snapshot())
            using (var data = img.Encode(SKEncodedImageFormat.Png, 90))
            using (var fs = File.Create(OutPath))
                data.SaveTo(fs);

            SystemParametersInfo(SPI_SETDESKWALLPAPER, 0, OutPath,
                SPIF_UPDATEINIFILE | SPIF_SENDCHANGE);
        }
        catch { /* bakgrunn er kosmetisk — aldri krasj overlay-en for dette */ }
    }
}

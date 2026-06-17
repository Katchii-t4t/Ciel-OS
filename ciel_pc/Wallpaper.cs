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

    static readonly string Dir = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Ciel");
    static readonly object Gate = new();   // serialiser samtidige kall (unngå at opprydding slettar kvarandre)

    public static void Set(Orb orb, SKColor gold, bool girl)
    {
      lock (Gate)
      {
        try
        {
            int w = GetSystemMetrics(0), h = GetSystemMetrics(1);   // primær skjerm i pikslar
            if (w <= 0 || h <= 0) { w = 1920; h = 1080; }

            using var surface = SKSurface.Create(new SKImageInfo(w, h));
            // Orb-renderaren er trygg å kalle frå bakgrunnstråd (les berre faste data).
            // Stor, ambient orb som fyller ramma (ikkje sentrert "ikon" i sirkel).
            orb.Render(surface.Canvas, w, h, 0.8, gold, girl, SKColors.Black, 0.70, round: false);

            Directory.CreateDirectory(Dir);
            // UNIKT filnamn kvar gong: Windows re-transcodar ikkje same sti, så
            // same filnamn ville vist den GAMLE bakgrunnen. Ny sti tvingar oppdatering.
            string outPath = Path.Combine(Dir, $"wallpaper_{DateTime.Now.Ticks}.png");
            using (var img = surface.Snapshot())
            using (var data = img.Encode(SKEncodedImageFormat.Png, 90))
            using (var fs = File.Create(outPath))
                data.SaveTo(fs);

            SystemParametersInfo(SPI_SETDESKWALLPAPER, 0, outPath,
                SPIF_UPDATEINIFILE | SPIF_SENDCHANGE);

            // Rydd gamle bakgrunnsbilete
            foreach (var f in Directory.GetFiles(Dir, "wallpaper*.png"))
                if (f != outPath) try { File.Delete(f); } catch { }
        }
        catch { /* bakgrunn er kosmetisk — aldri krasj overlay-en for dette */ }
      }
    }
}

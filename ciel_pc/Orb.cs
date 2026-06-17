using System;
using SkiaSharp;

namespace Ciel;

// Ciel-orben — trufast port av orb.dart / CielWallpaperService.kt:
// kvit-gull krystallinsk kjerne, 8 lange stråler, partikkelboble som orbiterer
// kjernen, mjuk aura. Gull er standard; girl mode = trans-flagg-band (blå/kvit/rosa).
// Tidsbasert (t i sekund), så fps ikkje endrar fart — berre straumbruk.
public sealed class Orb
{
    const int N = 320;
    static readonly double TwoPi = Math.PI * 2;

    readonly double[] ang0 = new double[N];
    readonly double[] rr = new double[N];
    readonly double[] edge = new double[N];
    readonly double[] spd = new double[N];
    readonly double[] szF = new double[N];   // storleik som brøk av maxR
    readonly int[] band = new int[N];
    readonly double[] opBase = new double[N];
    readonly double[] opFreq = new double[N];
    readonly double[] opPhase = new double[N];

    // trans-flagg + gull
    static readonly byte[] Blue = { 123, 205, 255 };
    static readonly byte[] White = { 255, 255, 255 };
    static readonly byte[] Pink = { 245, 169, 196 };

    public Orb()
    {
        var r = new Random(42); // same seed som tabletten → same partikkelmønster
        for (int i = 0; i < N; i++)
        {
            ang0[i] = r.NextDouble() * TwoPi;
            double rad = 0.20 + r.NextDouble() * 1.65;     // heilt ut til kantane
            rr[i] = rad;
            edge[i] = 1 - ((rad - 0.20) / 1.65) * 0.40;     // ytre litt dimmare (djupn)
            spd[i] = (0.05 + r.NextDouble() * 0.22) / (0.6 + rad); // ytre orbiterer seinare
            szF[i] = (2.0 + r.NextDouble() * 3.6) / 165.0;  // ~px ved maxR≈165, skalert
            band[i] = i % 3;
            opBase[i] = (0.55 + r.NextDouble() * 0.42) * edge[i];
            opFreq[i] = 0.3 + r.NextDouble() * 1.2;
            opPhase[i] = r.NextDouble() * TwoPi;
        }
    }

    static SKColor Band(int b, bool girl, SKColor gold, double a)
    {
        byte[] c = !girl ? new[] { gold.Red, gold.Green, gold.Blue }
                         : (b == 0 ? Blue : b == 1 ? White : Pink);
        return new SKColor(c[0], c[1], c[2], (byte)(Math.Clamp(a, 0, 1) * 255));
    }

    // t = sekund sidan start. gold = gjeldande modus-farge (standard #EF9F27).
    public void Render(SKCanvas canvas, int w, int h, double t, SKColor gold, bool girl)
    {
        canvas.Clear(SKColors.Transparent);
        float cx = w / 2f, cy = h / 2f;
        float maxR = Math.Min(w, h) * 0.46f;
        var ctr = new SKPoint(cx, cy);

        using var paint = new SKPaint { IsAntialias = true };

        // Aura — mjuk glød (gull, eller rosa i girl mode)
        byte[] ac = !girl ? new[] { gold.Red, gold.Green, gold.Blue } : Pink;
        paint.Style = SKPaintStyle.Fill;
        paint.Shader = SKShader.CreateRadialGradient(ctr, maxR * 1.7f,
            new[] { new SKColor(ac[0], ac[1], ac[2], 56), new SKColor(0, 0, 0, 0) },
            new float[] { 0f, 1f }, SKShaderTileMode.Clamp);
        canvas.DrawCircle(cx, cy, maxR * 1.7f, paint);
        paint.Shader = null;

        // Partiklar — orbiterer kjernen
        for (int i = 0; i < N; i++)
        {
            double a = ang0[i] + spd[i] * 0.96 * t;
            float rad = maxR * (float)rr[i];
            float px = cx + (float)Math.Cos(a) * rad;
            float py = cy + (float)Math.Sin(a) * rad * 0.92f;
            double op = opBase[i] * (0.5 + 0.5 * Math.Sin(t * opFreq[i] + opPhase[i]));
            paint.Color = Band(band[i], girl, gold, op);
            canvas.DrawCircle(px, py, (float)(szF[i] * maxR * edge[i]), paint);
        }

        // 8 stråler — sakte rotasjon
        double rot = t * 0.08;
        paint.Style = SKPaintStyle.Stroke;
        paint.StrokeWidth = Math.Max(1.5f, maxR * 0.018f);
        for (int i = 0; i < 8; i++)
        {
            double a = rot + i / 8.0 * TwoPi;
            float len = maxR * (0.72f + 0.08f * (float)Math.Sin(t * 0.6 + i));
            var tip = new SKPoint(cx + (float)Math.Cos(a) * len, cy + (float)Math.Sin(a) * len);
            int third = (int)(((a % TwoPi + TwoPi) % TwoPi) / (TwoPi / 3));
            paint.Shader = SKShader.CreateLinearGradient(ctr, tip,
                new[] { Band(third, girl, gold, 0.45), new SKColor(0, 0, 0, 0) },
                new float[] { 0f, 1f }, SKShaderTileMode.Clamp);
            canvas.DrawLine(ctr, tip, paint);
        }
        paint.Shader = null;

        // Kjerne — alltid kvit-lys
        float coreR = maxR * 0.15f;
        byte[] cc = !girl ? new[] { gold.Red, gold.Green, gold.Blue } : White;
        paint.Style = SKPaintStyle.Fill;
        paint.Shader = SKShader.CreateRadialGradient(ctr, coreR,
            new[] { new SKColor(255, 255, 255, 255), new SKColor(cc[0], cc[1], cc[2], 235), new SKColor(0, 0, 0, 0) },
            new float[] { 0f, 0.38f, 1f }, SKShaderTileMode.Clamp);
        canvas.DrawCircle(cx, cy, coreR, paint);
        paint.Shader = null;
        paint.Color = new SKColor(255, 255, 255, 252);
        canvas.DrawCircle(cx, cy, maxR * 0.02f, paint);
    }
}

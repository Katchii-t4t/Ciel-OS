using System;
using SkiaSharp;

namespace Ciel;

// Ciel-orben — tett, lysande krystallinsk bubble (ikkje spreidd stjernefelt).
// Tre lag: tett skal-ring (bubla), indre dis, sparsame ytre wisps. Kvit kjerne,
// 8 stråler, mjuk aura. Trans-flagg-band (blå/kvit/rosa) når girl=true (standard).
// Tidsbasert (t i sekund) → fps endrar ikkje fart, berre straumbruk.
public sealed class Orb
{
    const int NShell = 340, NInner = 150, NOuter = 90;
    const int N = NShell + NInner + NOuter;
    static readonly double TwoPi = Math.PI * 2;

    readonly double[] ang0 = new double[N];
    readonly double[] rFrac = new double[N];   // radius som brøk av maxR
    readonly double[] spd = new double[N];
    readonly double[] szF = new double[N];      // storleik som brøk av maxR
    readonly double[] opBase = new double[N];
    readonly double[] opFreq = new double[N];
    readonly double[] opPhase = new double[N];
    readonly double[] breathe = new double[N];
    readonly int[] band = new int[N];

    static readonly byte[] Blue = { 123, 205, 255 };
    static readonly byte[] White = { 255, 255, 255 };
    static readonly byte[] Pink = { 245, 169, 196 };

    public Orb()
    {
        var r = new Random(42);
        for (int i = 0; i < N; i++)
        {
            ang0[i] = r.NextDouble() * TwoPi;
            band[i] = i % 3;
            opFreq[i] = 0.3 + r.NextDouble() * 1.2;
            opPhase[i] = r.NextDouble() * TwoPi;

            if (i < NShell)                       // tett skal-ring = sjølve bubla
            {
                rFrac[i] = 0.56 + r.NextDouble() * 0.30;     // 0.56–0.86
                opBase[i] = 0.48 + r.NextDouble() * 0.42;    // lysare
                szF[i] = (1.6 + r.NextDouble() * 2.8) / 165.0;
                breathe[i] = 0.02 + r.NextDouble() * 0.04;
            }
            else if (i < NShell + NInner)         // indre dis (djupn mot kjernen)
            {
                rFrac[i] = 0.16 + r.NextDouble() * 0.42;
                opBase[i] = 0.26 + r.NextDouble() * 0.34;
                szF[i] = (1.0 + r.NextDouble() * 2.0) / 165.0;
                breathe[i] = 0.01 + r.NextDouble() * 0.03;
            }
            else                                  // sparsame ytre wisps
            {
                rFrac[i] = 0.90 + r.NextDouble() * 0.55;
                opBase[i] = 0.10 + r.NextDouble() * 0.22;
                szF[i] = (1.0 + r.NextDouble() * 2.4) / 165.0;
                breathe[i] = 0.02 + r.NextDouble() * 0.05;
            }
            spd[i] = (0.05 + r.NextDouble() * 0.20) / (0.5 + rFrac[i]); // ytre seinare
        }
    }

    static SKColor Band(int b, bool girl, SKColor gold, double a)
    {
        byte[] c = !girl ? new[] { gold.Red, gold.Green, gold.Blue }
                         : (b == 0 ? Blue : b == 1 ? White : Pink);
        return new SKColor(c[0], c[1], c[2], (byte)(Math.Clamp(a, 0, 1) * 255));
    }

    // gold = modus-farge (tintar glød + stråler). girl = trans-flagg-band.
    // bg = null → gjennomsiktig (overlay); svart → skrivebordsbakgrunn.
    // maxRFactor = orb-storleik som brøk av minste dimensjon.
    // round = true → klipp til mjuk sirkel (overlay-hjørnet). false → fyll ramma
    // ambient (skrivebordsbakgrunn), berre mjuk vignett mot kantane.
    public void Render(SKCanvas canvas, int w, int h, double t, SKColor gold, bool girl,
                       SKColor? bg = null, double maxRFactor = 0.40, bool round = true)
    {
        canvas.Clear(bg ?? SKColors.Transparent);
        float minDim = Math.Min(w, h);
        float maxR = (float)(minDim * maxRFactor);
        if (round)
        {
            canvas.SaveLayer(null);
            RenderAt(canvas, w / 2f, h / 2f, maxR, t, gold, girl);
            using var mask = new SKPaint { BlendMode = SKBlendMode.DstIn };
            mask.Shader = SKShader.CreateRadialGradient(new SKPoint(w / 2f, h / 2f), minDim * 0.5f,
                new[] { new SKColor(255, 255, 255, 255), new SKColor(255, 255, 255, 255), new SKColor(255, 255, 255, 0) },
                new float[] { 0f, 0.66f, 1f }, SKShaderTileMode.Clamp);
            canvas.DrawRect(0, 0, w, h, mask);
            canvas.Restore();
        }
        else
        {
            RenderAt(canvas, w / 2f, h / 2f, maxR, t, gold, girl);
        }
    }

    // Teikn éin orb sentrert på (cx,cy) med radius maxR. Klarar IKKJE lerretet —
    // brukt for fleire orbar på same lerret (t.d. ein per skjerm på bakgrunnen).
    public void RenderAt(SKCanvas canvas, float cx, float cy, float maxR, double t, SKColor gold, bool girl)
    {
        var ctr = new SKPoint(cx, cy);
        using var paint = new SKPaint { IsAntialias = true };

        // Aura — mjuk glød i modus-fargen
        paint.Style = SKPaintStyle.Fill;
        paint.Shader = SKShader.CreateRadialGradient(ctr, maxR * 1.25f,
            new[] { new SKColor(gold.Red, gold.Green, gold.Blue, 80), new SKColor(0, 0, 0, 0) },
            new float[] { 0f, 1f }, SKShaderTileMode.Clamp);
        canvas.DrawCircle(cx, cy, maxR * 1.25f, paint);
        paint.Shader = null;

        // Partiklar — tett bubble som pustar + orbiterer
        for (int i = 0; i < N; i++)
        {
            double a = ang0[i] + spd[i] * 0.96 * t;
            double rf = rFrac[i] + breathe[i] * Math.Sin(t * 0.6 + opPhase[i]);
            float rad = maxR * (float)rf;
            float px = cx + (float)Math.Cos(a) * rad;
            float py = cy + (float)Math.Sin(a) * rad * 0.92f;
            double op = opBase[i] * (0.55 + 0.45 * Math.Sin(t * opFreq[i] + opPhase[i]));
            paint.Color = Band(band[i], girl, gold, op);
            canvas.DrawCircle(px, py, (float)(szF[i] * maxR), paint);
        }

        // 8 stråler — sakte rotasjon, tinta av modus-fargen
        double rot = t * 0.08;
        paint.Style = SKPaintStyle.Stroke;
        paint.StrokeWidth = Math.Max(1.5f, maxR * 0.016f);
        for (int i = 0; i < 8; i++)
        {
            double a = rot + i / 8.0 * TwoPi;
            float len = maxR * (0.78f + 0.08f * (float)Math.Sin(t * 0.6 + i));
            var tip = new SKPoint(cx + (float)Math.Cos(a) * len, cy + (float)Math.Sin(a) * len);
            paint.Shader = SKShader.CreateLinearGradient(ctr, tip,
                new[] { new SKColor(gold.Red, gold.Green, gold.Blue, 130), new SKColor(0, 0, 0, 0) },
                new float[] { 0f, 1f }, SKShaderTileMode.Clamp);
            canvas.DrawLine(ctr, tip, paint);
        }
        paint.Shader = null;

        // Kjerne — kvit-lys, litt større glød
        float coreR = maxR * 0.17f;
        byte[] cc = !girl ? new[] { gold.Red, gold.Green, gold.Blue } : White;
        paint.Style = SKPaintStyle.Fill;
        paint.Shader = SKShader.CreateRadialGradient(ctr, coreR,
            new[] { new SKColor(255, 255, 255, 255), new SKColor(cc[0], cc[1], cc[2], 240), new SKColor(0, 0, 0, 0) },
            new float[] { 0f, 0.40f, 1f }, SKShaderTileMode.Clamp);
        canvas.DrawCircle(cx, cy, coreR, paint);
        paint.Shader = null;
        paint.Color = new SKColor(255, 255, 255, 255);
        canvas.DrawCircle(cx, cy, maxR * 0.025f, paint);
    }
}

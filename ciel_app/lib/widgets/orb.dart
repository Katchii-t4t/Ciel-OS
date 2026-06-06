import 'dart:math' as math;
import 'dart:typed_data';
import 'dart:ui' as ui;
import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart' show Ticker;

/// Renderar ein STILL-ramme av orben til PNG — for låsskjerm-bakgrunn o.l.
/// (statisk, ingen animasjon/pulsing).
Future<Uint8List?> renderOrbPng({
  required int width,
  required int height,
  Color color = const Color(0xFFFFC850),
  bool girl = false,
  double brightness = 1.35,
  double t = 0.7,
}) async {
  final recorder = ui.PictureRecorder();
  final canvas = Canvas(recorder);
  final w = width.toDouble(), h = height.toDouble();
  canvas.drawRect(Rect.fromLTWH(0, 0, w, h), Paint()..color = const Color(0xFF000000));
  final orbD = w * 0.82;
  canvas.save();
  canvas.translate((w - orbD) / 2, (h - orbD) / 2);
  _OrbPainter(
    t: t,
    girlMix: girl ? 1.0 : 0.0,
    base: color,
    model: _OrbModel(math.Random(42)),
    transparentBg: true,
    brightness: brightness,
  ).paint(canvas, Size(orbD, orbD));
  canvas.restore();
  final img = await recorder.endRecording().toImage(width, height);
  final data = await img.toByteData(format: ui.ImageByteFormat.png);
  return data?.buffer.asUint8List();
}

/// Ciel-orben — port av ciel_orb_v3.html til Flutter CustomPainter.
/// Krystallinsk kjerne, partikkelboble, 8 stråler. Gull er heim; girl mode
/// samlar partiklane i trans-flagg-band (1/3 blå · 1/3 kvit · 1/3 rosa).
class CielOrb extends StatefulWidget {
  final Color modeColor; // gjeldande modus-farge (gull som standard)
  final bool girlMode;
  final double size;
  final bool transparentBg; // true = ingen svart fyll (for hjørne-overlay)
  final double brightness;  // >1 = sterkare/meir synleg (for overlay)

  const CielOrb({
    super.key,
    this.modeColor = const Color(0xFFFFC850), // ~ [255,200,80]
    this.girlMode = false,
    this.size = 320,
    this.transparentBg = false,
    this.brightness = 1.0,
  });

  @override
  State<CielOrb> createState() => _CielOrbState();
}

class _CielOrbState extends State<CielOrb> with SingleTickerProviderStateMixin {
  late final Ticker _ticker;
  final ValueNotifier<double> _t = ValueNotifier(0);
  double _girlMix = 0;
  Duration _last = Duration.zero;
  late final _OrbModel _model;

  @override
  void initState() {
    super.initState();
    _model = _OrbModel(math.Random(42));
    _girlMix = widget.girlMode ? 1 : 0;
    _ticker = createTicker(_onTick)..start();
  }

  void _onTick(Duration elapsed) {
    final dt = (elapsed - _last).inMicroseconds / 1e6;
    _last = elapsed;
    final target = widget.girlMode ? 1.0 : 0.0;
    _girlMix += (target - _girlMix) * math.min(1.0, dt * 2.7);
    _t.value = elapsed.inMicroseconds / 1e6 * 0.42; // matchar JS-tempoet
  }

  @override
  void dispose() {
    _ticker.dispose();
    _t.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: widget.size,
      height: widget.size,
      child: AnimatedBuilder(
        animation: _t,
        builder: (_, __) => CustomPaint(
          painter: _OrbPainter(
            t: _t.value,
            girlMix: _girlMix,
            base: widget.modeColor,
            model: _model,
            transparentBg: widget.transparentBg,
            brightness: widget.brightness,
          ),
        ),
      ),
    );
  }
}

// ── Partikkel-modell (seeda éin gong) ────────────────────────────────────────
class _Shell {
  final double baseAngle, angleOff, radiusBase, radiusNoise, noiseFreq,
      noisePhase, size, opacity, opFreq, opPhase, distortAmp, distortFreq, distortPhase;
  final int band;
  _Shell(math.Random r, int i, int n)
      : baseAngle = i / n * math.pi * 2,
        band = i % 3,
        angleOff = (r.nextDouble() - .5) * .16,
        radiusBase = 62 + r.nextDouble() * 16,
        radiusNoise = 9 + r.nextDouble() * 20,
        noiseFreq = .4 + r.nextDouble() * 1.2,
        noisePhase = r.nextDouble() * math.pi * 2,
        size = .5 + r.nextDouble() * 1.5,
        opacity = .28 + r.nextDouble() * .5,
        opFreq = .3 + r.nextDouble() * .8,
        opPhase = r.nextDouble() * math.pi * 2,
        distortAmp = 7 + r.nextDouble() * 22,
        distortFreq = .2 + r.nextDouble() * .6,
        distortPhase = r.nextDouble() * math.pi * 2;
}

class _Drift {
  double angle;
  final double r, speed, size, opacity, opFreq, opPhase, wander;
  final int band;
  _Drift(math.Random r0, int i, double rMin, double rSpan, double spd, double opBase, double opSpan)
      : band = i % 3,
        angle = r0.nextDouble() * math.pi * 2,
        r = rMin + r0.nextDouble() * rSpan,
        speed = (r0.nextDouble() - .5) * spd,
        size = .3 + r0.nextDouble() * 1.1,
        opacity = opBase + r0.nextDouble() * opSpan,
        opFreq = .2 + r0.nextDouble() * 1.3,
        opPhase = r0.nextDouble() * math.pi * 2,
        wander = (r0.nextDouble() - .5) * .003;
}

class _OrbModel {
  final List<_Shell> shell;
  final List<_Drift> inner;
  final List<_Drift> outer;
  _OrbModel(math.Random r)
      : shell = List.generate(160, (i) => _Shell(r, i, 160)),
        inner = List.generate(90, (i) => _Drift(r, i, 24, 40, .004, .16, .35)),
        outer = List.generate(55, (i) => _Drift(r, i, 85, 70, .002, .06, .18));
}

// ── Painter ──────────────────────────────────────────────────────────────────
class _OrbPainter extends CustomPainter {
  final double t, girlMix;
  final Color base;
  final _OrbModel model;
  final bool transparentBg;
  final double brightness;
  _OrbPainter({required this.t, required this.girlMix, required this.base, required this.model, this.transparentBg = false, this.brightness = 1.0});

  // Trans-flagg-fargar
  static const List<double> _blue = [123, 205, 255];
  static const List<double> _white = [255, 255, 255];
  static const List<double> _pink = [245, 169, 196];

  double _lerp(double a, double b, double x) => a + (b - a) * x;

  List<double> _baseRgb() => [base.r * 255, base.g * 255, base.b * 255];

  /// Farge for ein partikkel: blandar frå modus-fargen mot band-fargen med girlMix.
  Color _bandColor(int band, double alpha) {
    final tc = band == 0 ? _blue : band == 1 ? _white : _pink;
    final bb = _baseRgb();
    int mix(int i) => _lerp(bb[i], tc[i], girlMix).round();
    return Color.fromRGBO(mix(0), mix(1), mix(2), alpha.clamp(0.0, 1.0));
  }

  void _drawRay(Canvas c, Offset ctr, double angle, double length, double width,
      Color col, double alpha) {
    final tip = ctr + Offset(math.cos(angle) * length, math.sin(angle) * length);
    final px = math.sin(angle) * width, py = -math.cos(angle) * width;
    final p = Path()
      ..moveTo(ctr.dx + px, ctr.dy + py)
      ..lineTo(tip.dx, tip.dy)
      ..lineTo(ctr.dx - px, ctr.dy - py)
      ..close();
    final shader = ui.Gradient.linear(ctr, tip, [
      col.withValues(alpha:alpha.clamp(0.0, 1.0)),
      col.withValues(alpha:(alpha * .45).clamp(0.0, 1.0)),
      col.withValues(alpha:0.0),
    ], [
      0.0,
      0.38,
      1.0
    ]);
    c.drawPath(p, Paint()..shader = shader);
  }

  @override
  void paint(Canvas c, Size size) {
    final s = size.shortestSide;
    final k = s / 350.0; // v3 var teikna for 350 px høgd
    final ctr = Offset(size.width / 2, size.height / 2);
    final b = _baseRgb();
    final baseCol = Color.fromRGBO(b[0].round(), b[1].round(), b[2].round(), 1);

    // Svart bakgrunn (AMOLED off) — hopp over for gjennomsiktig hjørne-overlay
    if (!transparentBg) {
      c.drawRect(Offset.zero & size, Paint()..color = Colors.black);
    }

    // Aura
    final auraR = 150 * k;
    final auraPaint = Paint()
      ..shader = ui.Gradient.radial(ctr, auraR, [
        baseCol.withValues(alpha:((.10 + .03 * math.sin(t * .5)) * brightness).clamp(0.0, 1.0)),
        baseCol.withValues(alpha:(.04 * brightness).clamp(0.0, 1.0)),
        baseCol.withValues(alpha:0.0),
      ], [0.0, 0.5, 1.0]);
    c.drawCircle(ctr, auraR, auraPaint);

    final dot = Paint();

    // Ytre wisps
    for (final p in model.outer) {
      p.angle += p.speed + math.sin(t * .3 + p.angle) * p.wander;
      final r = p.r + 18 * math.sin(t * .4 + p.angle * 3);
      final pos = ctr + Offset(math.cos(p.angle) * r * k, math.sin(p.angle) * r * .78 * k);
      final op = p.opacity * (.4 + .6 * math.sin(t * p.opFreq + p.opPhase));
      dot.color = _bandColor(p.band, math.max(0.0, op) * brightness);
      c.drawCircle(pos, p.size * k, dot);
    }

    // Boble-skal — i girl mode dyttast partiklane inn i band (tredjedelar)
    for (final p in model.shell) {
      final bandCenter = p.band * (math.pi * 2 / 3);
      final spread = _lerp(math.pi * 2, math.pi * 2 / 3 * .92, girlMix);
      final localAngle = p.baseAngle % (math.pi * 2);
      final banded = bandCenter + (localAngle / (math.pi * 2) - .5) * spread;
      final angle = _lerp(p.baseAngle, banded, girlMix) + p.angleOff + t * .012;
      final distort = p.distortAmp * math.sin(t * p.distortFreq + p.distortPhase + angle * 3);
      final r = p.radiusBase + p.radiusNoise * math.sin(t * p.noiseFreq + p.noisePhase) + distort;
      final pos = ctr + Offset(math.cos(angle) * r * k, math.sin(angle) * r * .88 * k);
      final op = p.opacity * (.5 + .5 * math.sin(t * p.opFreq + p.opPhase));
      dot.color = _bandColor(p.band, math.max(0.0, op) * brightness);
      c.drawCircle(pos, p.size * k, dot);
    }

    // Indre dis
    for (final p in model.inner) {
      p.angle += p.speed;
      final warp = 9 * math.sin(t * .6 + p.angle * 4);
      final pos = ctr +
          Offset(math.cos(p.angle) * (p.r + warp) * k, math.sin(p.angle) * (p.r + warp) * .9 * k);
      final op = p.opacity * (.4 + .6 * math.sin(t * p.opFreq + p.opPhase).abs());
      dot.color = _bandColor(p.band, math.max(0.0, op) * brightness);
      c.drawCircle(pos, p.size * k, dot);
    }

    final breath = .93 + .07 * math.sin(t * .5);
    final rot = t * .035;
    const lens = [140.0, 70, 108, 60, 132, 64, 100, 58];
    const wids = [1.1, .5, .8, .45, 1.0, .5, .7, .45];

    // 8 hovudstråler — farga etter kva tredjedel dei peikar i (girl mode)
    for (int i = 0; i < 8; i++) {
      final a = rot + i / 8 * math.pi * 2;
      final third = ((((a % (math.pi * 2)) + math.pi * 2) % (math.pi * 2)) / (math.pi * 2 / 3)).floor();
      _drawRay(c, ctr, a, lens[i] * breath * k, wids[i] * k, _bandColor(third, 1),
          (.5 + .12 * math.sin(t * .6 + i)) * breath * brightness);
    }
    // 14 mindre stråler
    for (int i = 0; i < 14; i++) {
      final a = rot * .6 + i / 14 * math.pi * 2 + .22;
      final third = ((((a % (math.pi * 2)) + math.pi * 2) % (math.pi * 2)) / (math.pi * 2 / 3)).floor();
      _drawRay(c, ctr, a, (26 + 9 * math.sin(t * .9 + i)) * breath * k, .28 * k,
          _bandColor(third, 1), (.10 + .05 * math.sin(t + i)) * brightness);
    }

    // Ringar
    final ring = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = .5 * k
      ..color = baseCol.withValues(alpha:.08 + .03 * math.sin(t * 1.1));
    c.drawCircle(ctr, 68 * breath * k, ring);
    c.drawCircle(ctr, 17 * breath * k,
        Paint()..style = PaintingStyle.stroke..strokeWidth = .5 * k
          ..color = baseCol.withValues(alpha:.18 + .06 * math.sin(t)));

    // Kjerne — alltid kvit-lys
    final coreR = 11 * breath * k;
    final coreHalo = girlMix < .5
        ? baseCol
        : Color.fromRGBO(
            _lerp(b[0], 245, girlMix).round(),
            _lerp(b[1], 200, girlMix).round(),
            _lerp(b[2], 220, girlMix).round(),
            1);
    final corePaint = Paint()
      ..shader = ui.Gradient.radial(ctr, coreR, [
        Colors.white.withValues(alpha:.97),
        coreHalo.withValues(alpha:.88),
        coreHalo.withValues(alpha:.3),
        coreHalo.withValues(alpha:0.0),
      ], [0.0, 0.2, 0.65, 1.0]);
    c.drawCircle(ctr, coreR, corePaint);
    c.drawCircle(ctr, 1.8 * k, Paint()..color = Colors.white.withValues(alpha:.99));
  }

  @override
  bool shouldRepaint(covariant _OrbPainter old) =>
      old.t != t || old.girlMix != girlMix || old.base != base;
}

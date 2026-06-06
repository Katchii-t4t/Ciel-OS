import 'dart:async';
import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';

/// Fangar S Pen-strok over orben, teiknar dei glødande, og kallar [onComplete]
/// etter ein kort pause. Berre stylus teiknar — fingertrykk går vidare som vanleg.
class InkLayer extends StatefulWidget {
  final Color color;
  final void Function(List<List<Offset>> strokes) onComplete;
  final Widget child;

  const InkLayer({
    super.key,
    required this.color,
    required this.onComplete,
    required this.child,
  });

  @override
  State<InkLayer> createState() => _InkLayerState();
}

class _InkLayerState extends State<InkLayer> {
  final List<List<Offset>> _strokes = [];
  List<Offset>? _current;
  Timer? _debounce;
  bool _capturing = false;

  void _down(PointerDownEvent e) {
    if (e.kind != PointerDeviceKind.stylus) return;
    _debounce?.cancel();
    _capturing = true;
    setState(() => _current = [e.localPosition]);
  }

  void _move(PointerMoveEvent e) {
    if (!_capturing || _current == null || e.kind != PointerDeviceKind.stylus) return;
    setState(() => _current!.add(e.localPosition));
  }

  void _up(PointerUpEvent e) {
    if (!_capturing) return;
    if (_current != null && _current!.length > 1) _strokes.add(_current!);
    _current = null;
    _capturing = false;
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 900), _finish);
    setState(() {});
  }

  void _finish() {
    if (_strokes.isEmpty) return;
    final s = List<List<Offset>>.from(_strokes);
    _strokes.clear();
    setState(() {});
    widget.onComplete(s);
  }

  @override
  void dispose() {
    _debounce?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Listener(
      behavior: HitTestBehavior.translucent,
      onPointerDown: _down,
      onPointerMove: _move,
      onPointerUp: _up,
      child: Stack(children: [
        widget.child,
        Positioned.fill(
          child: IgnorePointer(
            child: CustomPaint(painter: _InkPainter(_strokes, _current, widget.color)),
          ),
        ),
      ]),
    );
  }
}

class _InkPainter extends CustomPainter {
  final List<List<Offset>> strokes;
  final List<Offset>? current;
  final Color color;
  _InkPainter(this.strokes, this.current, this.color);

  @override
  void paint(Canvas c, Size s) {
    final glow = Paint()
      ..color = color.withValues(alpha: .28)
      ..strokeWidth = 11
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 8);
    final line = Paint()
      ..color = color
      ..strokeWidth = 4
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round;

    void draw(List<Offset> pts) {
      if (pts.length < 2) return;
      final path = Path()..moveTo(pts.first.dx, pts.first.dy);
      for (final p in pts.skip(1)) {
        path.lineTo(p.dx, p.dy);
      }
      c.drawPath(path, glow);
      c.drawPath(path, line);
    }

    for (final st in strokes) {
      draw(st);
    }
    if (current != null) draw(current!);
  }

  @override
  bool shouldRepaint(_InkPainter old) => true;
}

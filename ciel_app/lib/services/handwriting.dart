import 'dart:ui';
import 'package:google_mlkit_digital_ink_recognition/google_mlkit_digital_ink_recognition.dart';

/// Lokal handskrift-attkjenning (ML Kit Digital Ink). Ingen data forlèt eininga.
class Handwriting {
  final String lang;
  final _modelManager = DigitalInkRecognizerModelManager();
  DigitalInkRecognizer? _recognizer;

  Handwriting({this.lang = 'en'});

  Future<void> _ensure() async {
    if (!await _modelManager.isModelDownloaded(lang)) {
      await _modelManager.downloadModel(lang); // ~ nokre MB, éin gong
    }
    _recognizer ??= DigitalInkRecognizer(languageCode: lang);
  }

  /// Topp-tolkingar av strok (handskrift er uskarp — vi prøver fleire).
  Future<List<String>> recognizeCandidates(List<List<Offset>> strokes, {int max = 6}) async {
    final valid = strokes.where((s) => s.isNotEmpty).toList();
    if (valid.isEmpty) return [];
    await _ensure();

    final ink = Ink();
    var t = 0;
    ink.strokes = valid.map((s) {
      final stroke = Stroke();
      stroke.points = s.map((p) {
        t += 16; // syntetiske, monotone tidsstempel
        return StrokePoint(x: p.dx, y: p.dy, t: t);
      }).toList();
      return stroke;
    }).toList();

    final candidates = await _recognizer!.recognize(ink);
    return candidates
        .take(max)
        .map((c) => c.text.trim())
        .where((s) => s.isNotEmpty)
        .toList();
  }

  /// Beste enkelt-tolking.
  Future<String?> recognize(List<List<Offset>> strokes) async {
    final c = await recognizeCandidates(strokes, max: 1);
    return c.isEmpty ? null : c.first;
  }

  void dispose() => _recognizer?.close();
}

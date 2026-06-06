import 'package:flutter_tts/flutter_tts.dart';

/// Ciel si stemme (lokal TTS). Les svar høgt — roleg, deliberat tempo.
/// Nynorsk-stemme (nb-NO) så uttalen av svara blir rett. ElevenLabs kjem i 3.2.
class Voice {
  final FlutterTts _tts = FlutterTts();
  bool ready = false;

  Future<void> init() async {
    try {
      await _tts.setLanguage('nb-NO');
      await _tts.setSpeechRate(0.45); // under normalt tempo — "never hurried"
      await _tts.setPitch(1.0);
      await _tts.awaitSpeakCompletion(true);
      ready = true;
    } catch (_) {
      ready = false;
    }
  }

  Future<void> speak(String text) async {
    final t = text.trim();
    if (t.isEmpty) return;
    try {
      await _tts.stop();
      await _tts.speak(t);
    } catch (_) {}
  }

  Future<void> stop() async {
    try {
      await _tts.stop();
    } catch (_) {}
  }
}

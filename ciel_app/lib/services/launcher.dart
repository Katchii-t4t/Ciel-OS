import 'package:flutter/services.dart';

/// Bru til Android: opnar ekte appar etter namn (PackageManager-side i Kotlin).
class Launcher {
  static const _ch = MethodChannel('ciel/launcher');

  /// Returnerer etiketten til appen som vart opna, eller null om ingen match.
  static Future<String?> launchApp(String query) async {
    try {
      return await _ch.invokeMethod<String>('launchApp', {'query': query});
    } on PlatformException {
      return null;
    }
  }

  static Future<List<String>> listApps() async {
    try {
      final res = await _ch.invokeMethod<List<dynamic>>('listApps');
      return (res ?? []).map((e) => e.toString()).toList();
    } on PlatformException {
      return [];
    }
  }
}

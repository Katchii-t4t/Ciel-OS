import 'package:flutter/services.dart';

/// Bru til Android: opnar ekte appar etter namn (PackageManager-side i Kotlin).
class Launcher {
  static const _ch = MethodChannel('ciel/launcher');

  /// Set eit PNG som låsskjerm-bakgrunn (Samsung sin låsskjerm ligg oppå).
  static Future<bool> setLockWallpaper(Uint8List bytes) async {
    try {
      return await _ch.invokeMethod<bool>('setLockWallpaper', {'bytes': bytes}) ?? false;
    } on PlatformException {
      return false;
    }
  }

  /// Returnerer etiketten til appen som vart opna, eller null om ingen match.
  static Future<String?> launchApp(String query) async {
    try {
      return await _ch.invokeMethod<String>('launchApp', {'query': query});
    } on PlatformException {
      return null;
    }
  }

  /// Opnar system-førehandsvisninga for det levande Ciel-bakgrunnet.
  static Future<void> openLiveWallpaper() async {
    try {
      await _ch.invokeMethod('openLiveWallpaper');
    } on PlatformException {
      // ignorer
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

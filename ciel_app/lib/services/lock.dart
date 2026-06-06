import 'dart:convert';
import 'package:crypto/crypto.dart';
import 'package:local_auth/local_auth.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Ciel-velkomstporten (SPEC §5) — eit OPPLEVINGSLAG, ikkje ekte einings-tryggleik.
/// Tre vegar inn: pennord (lokal hash), fingeravtrykk, fjes (best-effort).
class Lock {
  static const _kEnabled = 'lock_enabled';
  static const _kHash = 'lock_pass_hash';
  final _auth = LocalAuthentication();

  Future<SharedPreferences> get _p => SharedPreferences.getInstance();

  Future<bool> isEnabled() async => (await _p).getBool(_kEnabled) ?? false;
  Future<void> setEnabled(bool v) async => (await _p).setBool(_kEnabled, v);

  String _hash(String word) =>
      sha256.convert(utf8.encode(word.toLowerCase().trim())).toString();

  Future<void> setPassphrase(String word) async =>
      (await _p).setString(_kHash, _hash(word));

  Future<bool> hasPassphrase() async => (await _p).getString(_kHash) != null;

  Future<bool> checkPassphrase(String word) async {
    final stored = (await _p).getString(_kHash);
    return stored != null && stored == _hash(word);
  }

  // ── Biometri ──────────────────────────────────────────────────────────────
  Future<List<BiometricType>> available() async {
    try {
      if (!await _auth.isDeviceSupported()) return [];
      return await _auth.getAvailableBiometrics();
    } catch (_) {
      return [];
    }
  }

  Future<bool> authBiometric() async {
    try {
      return await _auth.authenticate(
        localizedReason: 'Lås opp Ciel',
        biometricOnly: true,
      );
    } catch (_) {
      return false;
    }
  }
}

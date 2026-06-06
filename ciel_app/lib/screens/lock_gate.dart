import 'package:flutter/material.dart';
import 'package:local_auth/local_auth.dart';
import '../services/lock.dart';
import '../services/handwriting.dart';
import '../widgets/orb.dart';
import '../widgets/ink_layer.dart';

const _lockColor = Color(0xFF85B7EB); // iskald blå — låst / JARVIS-aktiv (§6.3)

/// Ciel-velkomstporten over låsskjermen. Tre vegar inn: pennord, fingeravtrykk, fjes.
class LockGate extends StatefulWidget {
  final VoidCallback onUnlocked;
  const LockGate({super.key, required this.onUnlocked});

  @override
  State<LockGate> createState() => _LockGateState();
}

class _LockGateState extends State<LockGate> {
  final _lock = Lock();
  final _hand = Handwriting();
  String _status = 'Velkommen attende, Dr. Katchi';
  List<BiometricType> _bio = [];
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _prep();
  }

  Future<void> _prep() async {
    _bio = await _lock.available();
    if (mounted) setState(() {});
    // Auto-trigger biometri ved oppstart — JARVIS-augneblinken
    if (_bio.isNotEmpty) _bioAuth();
  }

  Future<void> _bioAuth() async {
    if (_busy) return;
    setState(() => _busy = true);
    final ok = await _lock.authBiometric();
    if (!mounted) return;
    setState(() => _busy = false);
    if (ok) {
      widget.onUnlocked();
    } else {
      setState(() => _status = 'Prøv igjen — eller skriv ordet ditt på orben');
    }
  }

  Future<void> _onInk(List<List<Offset>> strokes) async {
    final cands = await _hand.recognizeCandidates(strokes);
    if (!mounted || cands.isEmpty) return;
    for (final c in cands) {
      if (await _lock.checkPassphrase(c)) {
        widget.onUnlocked();
        return;
      }
    }
    if (mounted) setState(() => _status = 'Feil ord. Prøv igjen.');
  }

  @override
  void dispose() {
    _hand.dispose();
    super.dispose();
  }

  bool get _hasFace => _bio.contains(BiometricType.face);
  bool get _hasFinger =>
      _bio.contains(BiometricType.fingerprint) || _bio.contains(BiometricType.strong);

  @override
  Widget build(BuildContext context) {
    final orbSize = MediaQuery.of(context).size.shortestSide * .7;
    return Scaffold(
      backgroundColor: Colors.black,
      body: SafeArea(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Spacer(),
            // Skriv pennordet rett på orben
            InkLayer(
              color: _lockColor,
              onComplete: _onInk,
              child: CielOrb(modeColor: _lockColor, size: orbSize),
            ),
            const SizedBox(height: 28),
            Text(
              _status,
              textAlign: TextAlign.center,
              style: const TextStyle(color: Colors.white70, fontSize: 15, letterSpacing: .3),
            ),
            const SizedBox(height: 6),
            const Text(
              'Skriv ordet ditt med pennen',
              style: TextStyle(color: Colors.white30, fontSize: 12),
            ),
            const Spacer(),
            // Biometriske vegar
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                if (_hasFinger)
                  _GateButton(
                    icon: Icons.fingerprint,
                    label: 'Fingeravtrykk',
                    onTap: _bioAuth,
                  ),
                if (_hasFace) ...[
                  const SizedBox(width: 28),
                  _GateButton(
                    icon: Icons.face_retouching_natural,
                    label: 'Fjes',
                    onTap: _bioAuth,
                  ),
                ],
              ],
            ),
            const SizedBox(height: 36),
          ],
        ),
      ),
    );
  }
}

class _GateButton extends StatelessWidget {
  final IconData icon;
  final String label;
  final VoidCallback onTap;
  const _GateButton({required this.icon, required this.label, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(16),
      child: Padding(
        padding: const EdgeInsets.all(10),
        child: Column(children: [
          Icon(icon, color: _lockColor, size: 38),
          const SizedBox(height: 4),
          Text(label, style: const TextStyle(color: Colors.white54, fontSize: 11)),
        ]),
      ),
    );
  }
}

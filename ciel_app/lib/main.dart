import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_overlay_window/flutter_overlay_window.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'screens/home.dart';
import 'screens/lock_gate.dart';
import 'services/lock.dart';
import 'services/launcher.dart';
import 'services/ciel_api.dart';
import 'widgets/orb.dart';

// Standard hjerne-URL (PC sin Tailscale-IP) om ingen er lagra enno.
const _brainFallback = 'http://100.121.52.97:8765';
// Lar oss vise SnackBar frå kor som helst (t.d. når ei delt fil kjem inn).
final GlobalKey<ScaffoldMessengerState> cielMessenger = GlobalKey<ScaffoldMessengerState>();

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  // Kant-til-kant: svart AMOLED bak gjennomsiktige systemfelt (launcher-kjensle)
  SystemChrome.setEnabledSystemUIMode(SystemUiMode.edgeToEdge);
  SystemChrome.setSystemUIOverlayStyle(const SystemUiOverlayStyle(
    statusBarColor: Colors.transparent,
    systemNavigationBarColor: Colors.transparent,
    statusBarIconBrightness: Brightness.light,
    systemNavigationBarIconBrightness: Brightness.light,
  ));
  runApp(const CielApp());
}

class CielApp extends StatelessWidget {
  const CielApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Ciel',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        brightness: Brightness.dark,
        scaffoldBackgroundColor: Colors.black,
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFFEF9F27),
          brightness: Brightness.dark,
        ),
        useMaterial3: true,
      ),
      scaffoldMessengerKey: cielMessenger,
      home: const CielRoot(),
    );
  }
}

/// Avgjer om velkomstporten skal visast (berre om lås er på OG vi ikkje låser ut).
class CielRoot extends StatefulWidget {
  const CielRoot({super.key});
  @override
  State<CielRoot> createState() => _CielRootState();
}

class _CielRootState extends State<CielRoot> {
  final _lock = Lock();
  bool _unlocked = false;
  bool? _enabled;

  @override
  void initState() {
    super.initState();
    _check();
    _initShare();
  }

  // Del → Ciel: ta imot delte filer (GoodNotes-eksport) og send til hjernen.
  // Native sida (MainActivity) legg filene i kø; her hentar vi dei.
  void _initShare() {
    Launcher.onSharedFiles(_pullShared);   // varm start (medan appen køyrer)
    _pullShared();                         // kald start (delt før app opna)
  }

  Future<void> _pullShared() async {
    final paths = await Launcher.consumeSharedFiles();
    if (paths.isEmpty) return;
    cielMessenger.currentState?.showSnackBar(
      const SnackBar(content: Text('Sender til Ciel …')),
    );
    final prefs = await SharedPreferences.getInstance();
    final api = CielApi(prefs.getString('serverUrl') ?? _brainFallback);
    var ok = 0;
    for (final p in paths) {
      try {
        final bytes = await File(p).readAsBytes();
        final name = p.split(RegExp(r'[\\/]')).last;
        if (await api.uploadGoodNotes(bytes, name) != null) ok++;
      } catch (_) {}
    }
    cielMessenger.currentState?.showSnackBar(SnackBar(
      content: Text(ok > 0
          ? 'Ciel mottok $ok fil(er) → lagar Obsidian-notat …'
          : 'Fekk ikkje kontakt med hjernen — prøv igjen'),
    ));
  }

  Future<void> _check() async {
    var en = await _lock.isEnabled();
    if (en) {
      // Tryggleiksventil: ikkje lås ut om verken pennord eller biometri finst
      final hasPass = await _lock.hasPassphrase();
      final bio = await _lock.available();
      if (!hasPass && bio.isEmpty) en = false;
    }
    if (mounted) setState(() => _enabled = en);
  }

  @override
  Widget build(BuildContext context) {
    if (_enabled == null) {
      return const Scaffold(backgroundColor: Colors.black, body: SizedBox.shrink());
    }
    if (!_enabled! || _unlocked) return const HomeScreen();
    return LockGate(onUnlocked: () => setState(() => _unlocked = true));
  }
}

/// Eigen inngang for hjørne-overlayet (Ciel oppi andre appar).
/// Køyrer i eit eige isolat — berre ein liten, gjennomsiktig, pustande orb.
@pragma("vm:entry-point")
void overlayMain() {
  runApp(const _CielOverlayApp());
}

class _CielOverlayApp extends StatefulWidget {
  const _CielOverlayApp();
  @override
  State<_CielOverlayApp> createState() => _CielOverlayAppState();
}

class _CielOverlayAppState extends State<_CielOverlayApp> {
  Color _color = const Color(0xFFEF9F27);
  bool _girl = true;

  @override
  void initState() {
    super.initState();
    // Tek imot gjeldande farge/modus frå hovudappen så hjørne-orben matchar heim
    FlutterOverlayWindow.overlayListener.listen((event) {
      try {
        if (event is String && event.startsWith('{')) {
          final m = jsonDecode(event) as Map<String, dynamic>;
          setState(() {
            if (m['c'] != null) _color = Color(m['c'] as int);
            if (m['g'] != null) _girl = m['g'] as bool;
          });
        }
      } catch (_) {}
    });
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      home: GestureDetector(
        // Trykk kvar som helst på hjørne-orben → hovudappen kjem fram igjen
        behavior: HitTestBehavior.opaque,
        onTap: () => FlutterOverlayWindow.shareData('open'),
        child: Center(
          child: Container(
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              gradient: RadialGradient(colors: [
                Colors.black.withValues(alpha: .55),
                Colors.black.withValues(alpha: .0),
              ]),
            ),
            child: CielOrb(
              modeColor: _color,
              girlMode: _girl,
              size: 165,
              transparentBg: true,
              brightness: 2.1,
              fps: 20, // over andre appar: 20 fps er rikeleg, sparar mest batteri
            ),
          ),
        ),
      ),
    );
  }
}

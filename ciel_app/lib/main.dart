import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_overlay_window/flutter_overlay_window.dart';
import 'screens/home.dart';
import 'screens/lock_gate.dart';
import 'services/lock.dart';
import 'widgets/orb.dart';

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
            ),
          ),
        ),
      ),
    );
  }
}

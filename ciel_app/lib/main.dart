import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_overlay_window/flutter_overlay_window.dart';
import 'screens/home.dart';
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
      home: const HomeScreen(),
    );
  }
}

/// Eigen inngang for hjørne-overlayet (Ciel oppi andre appar).
/// Køyrer i eit eige isolat — berre ein liten, gjennomsiktig, pustande orb.
@pragma("vm:entry-point")
void overlayMain() {
  runApp(const _CielOverlayApp());
}

class _CielOverlayApp extends StatelessWidget {
  const _CielOverlayApp();

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
            child: const CielOrb(size: 165, transparentBg: true, brightness: 2.1),
          ),
        ),
      ),
    );
  }
}

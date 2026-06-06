import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:io';
import 'package:flutter_overlay_window/flutter_overlay_window.dart';
import 'package:record/record.dart';
import 'package:path_provider/path_provider.dart';
import '../services/ciel_api.dart';
import '../services/launcher.dart';
import '../services/handwriting.dart';
import '../services/lock.dart';
import '../services/voice.dart';
import '../widgets/orb.dart';
import '../widgets/ink_layer.dart';

const _defaultUrl = 'http://192.168.10.194:8765';

const Map<String, Color> kModeColors = {
  'ambient': Color(0xFFEF9F27),
  'solo': Color(0xFF85B7EB),
  'social': Color(0xFF97C459),
  'lecture': Color(0xFFAFA9EC),
  'wind-down': Color(0xFFF09595),
};

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});
  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> with WidgetsBindingObserver {
  CielApi _api = CielApi(_defaultUrl);
  final _input = TextEditingController();
  final _answerScroll = ScrollController();
  final Handwriting _hand = Handwriting();
  final Lock _lock = Lock();
  final Voice _voice = Voice();
  final AudioRecorder _rec = AudioRecorder();
  bool _recording = false;
  bool _overlayPerm = false;
  bool _lockEnabled = false;
  bool _girlPermanent = true; // vis girl mode alltid (kan slåast av i innstillingar)
  bool _showGreeting = false;
  bool _voiceOn = true; // les svar høgt

  String _mode = 'ambient';
  bool _girlMode = false;
  bool _deep = false;
  bool _online = false;
  bool _busy = false;
  String _answer = '';
  StreamSubscription? _events;
  StreamSubscription? _askSub;

  Color get _modeColor => kModeColors[_mode] ?? kModeColors['ambient']!;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _boot();
    _initOverlay();
    _greet();
    WidgetsBinding.instance.addPostFrameCallback((_) => _ensureWallpaper());
  }

  // Self-heal: set Ciel-orben som bakgrunn (heim + lås) éin gong, så låsskjermen
  // alltid har orben sjølv om noko nullstilte han.
  static const _wpVer = 4; // auk for å tvinge re-set av wallpaper-designet
  Future<void> _ensureWallpaper() async {
    final prefs = await SharedPreferences.getInstance();
    if ((prefs.getInt('wp_ver') ?? 0) >= _wpVer) return;
    if (!mounted) return;
    try {
      final sz = MediaQuery.of(context).size;
      final dpr = MediaQuery.of(context).devicePixelRatio;
      final png = await renderOrbPng(
        width: (sz.width * dpr).round(),
        height: (sz.height * dpr).round(),
        color: _modeColor,
        girl: _girlPermanent || _girlMode,
      );
      if (png != null) {
        await Launcher.setLockWallpaper(png);
        await prefs.setInt('wp_ver', _wpVer);
      }
    } catch (_) {}
  }

  Future<void> _boot() async {
    final prefs = await SharedPreferences.getInstance();
    _lockEnabled = await _lock.isEnabled();
    _girlPermanent = prefs.getBool('girl_permanent') ?? true;
    _voiceOn = prefs.getBool('voice_on') ?? true;
    await _voice.init();
    if (_voiceOn) _voice.speak(_greetingText()); // talt velkomst ved oppstart
    final saved = prefs.getString('serverUrl');
    // Auto-oppdag hjernen: prøv lagra/LAN-URL, fall så tilbake til localhost
    // (fungerer over adb reverse / framtidig på-eining). Graceful degradation.
    final candidates = <String>[
      if (saved != null) saved,
      _defaultUrl,
      'http://localhost:8765',
      'http://127.0.0.1:8765',
    ];
    String chosen = saved ?? _defaultUrl;
    for (final c in candidates) {
      if (await CielApi(c).ping()) { chosen = c; break; }
    }
    _api = CielApi(chosen);
    await prefs.setString('serverUrl', chosen);
    await _refreshState();
    _listenEvents();
  }

  Future<void> _refreshState() async {
    final ok = await _api.ping();
    if (!mounted) return;
    setState(() => _online = ok);
    if (!ok) return;
    try {
      final st = await _api.getState();
      if (!mounted) return;
      setState(() {
        _mode = (st['mode'] ?? 'ambient').toString();
        _girlMode = st['girl_mode'] == true;
      });
    } catch (_) {}
  }

  void _listenEvents() {
    _events?.cancel();
    _events = _api.events().listen((e) {
      if (!mounted) return;
      switch (e['type']) {
        case 'state':
          setState(() {
            _mode = (e['mode'] ?? _mode).toString();
            _girlMode = e['girl_mode'] == true;
            _online = true;
          });
          break;
        case 'mode':
          setState(() => _mode = (e['mode'] ?? _mode).toString());
          break;
        case 'girl_mode':
          setState(() => _girlMode = e['on'] == true);
          break;
      }
    }, onError: (_) {
      if (mounted) setState(() => _online = false);
    });
  }

  Future<void> _ask() async {
    final q = _input.text.trim();
    if (q.isEmpty || _busy) return;
    setState(() {
      _busy = true;
      _answer = '';
    });
    _input.clear();
    _voice.stop(); // stopp evt. tidlegare tale
    _askSub = _api.askStream(q, deep: _deep).listen((tok) {
      if (!mounted) return;
      setState(() => _answer += tok);
      _answerScroll.animateTo(_answerScroll.position.maxScrollExtent,
          duration: const Duration(milliseconds: 120), curve: Curves.easeOut);
    }, onError: (e) {
      if (mounted) setState(() => _answer += '\n\n[feil: $e]');
    }, onDone: () {
      if (mounted) setState(() => _busy = false);
      if (_voiceOn && _answer.trim().isNotEmpty) _voice.speak(_answer); // Ciel les svaret høgt
    });
  }

  // ── Stemme inn: opptak → NB-Whisper → spør ──────────────────────────────
  Future<void> _toggleRecord() async {
    if (_recording) {
      final path = await _rec.stop();
      if (mounted) setState(() => _recording = false);
      if (path == null) return;
      if (mounted) setState(() => _busy = true);
      final bytes = await File(path).readAsBytes();
      final text = await _api.transcribe(bytes);
      if (!mounted) return;
      setState(() => _busy = false);
      if (text != null && text.trim().isNotEmpty) {
        _input.text = text;
        _ask();
      } else {
        _flash('Høyrde ikkje noko — prøv igjen');
      }
    } else {
      if (!await _rec.hasPermission()) {
        _flash('Mikrofon-løyve trengst');
        return;
      }
      final dir = await getTemporaryDirectory();
      await _rec.start(
        const RecordConfig(encoder: AudioEncoder.wav, sampleRate: 16000, numChannels: 1),
        path: '${dir.path}/ciel_rec.wav',
      );
      if (mounted) setState(() => _recording = true);
    }
  }

  // ── Velkomst-helsing (JARVIS-augneblinken etter opplåsing) ───────────────
  String _greetingText() {
    final h = DateTime.now().hour;
    final part = h < 5
        ? 'Good evening'
        : h < 12
            ? 'Good morning'
            : h < 18
                ? 'Good afternoon'
                : 'Good evening';
    return '$part, Dr. Katchi';
  }

  void _greet() {
    if (!mounted) return;
    setState(() => _showGreeting = true);
    Future.delayed(const Duration(milliseconds: 4500), () {
      if (mounted) setState(() => _showGreeting = false);
    });
  }

  // ── S Pen: skriv på orben → handling (Module D) ──────────────────────────
  void _flash(String msg) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: Text(msg),
      duration: const Duration(seconds: 2),
      behavior: SnackBarBehavior.floating,
      backgroundColor: Colors.white.withValues(alpha: .08),
    ));
  }

  // v1-scener: eitt ord → ein konfigurert tilstand (utvidast seinare)
  static const _scenes = {'lsb', 'forelesing', 'studie', 'sjakk'};
  static const _sceneMode = {
    'lsb': 'lecture', 'forelesing': 'lecture', 'studie': 'solo', 'sjakk': 'ambient',
  };

  Future<void> _onInk(List<List<Offset>> strokes) async {
    setState(() => _busy = true);
    List<String> cands = [];
    try {
      cands = await _hand.recognizeCandidates(strokes);
    } catch (e) {
      _flash('Handskrift feila: $e');
    }
    if (!mounted) return;
    if (cands.isEmpty) {
      setState(() => _busy = false);
      return;
    }
    final text = cands.first;
    _flash('✍ $text');

    // 1) App-namn → opne ekte app. Prøv ALLE tolkingar (handskrift er uskarp).
    // Vis hjørne-orben FØR vi opnar, medan Ciel er i framgrunn.
    await _showCornerOrb();
    for (final c in cands) {
      final launched = await Launcher.launchApp(c);
      if (launched != null) {
        if (mounted) {
          _flash('Opnar $launched');
          setState(() => _busy = false);
        }
        return;
      }
    }
    // ingen app → lukk hjørne-orben vi førehandsviste
    try { await FlutterOverlayWindow.closeOverlay(); } catch (_) {}

    // 2) Scene-ord → konfigurert tilstand
    for (final c in cands) {
      final key = c.toLowerCase().trim();
      if (_scenes.contains(key)) {
        final mode = _sceneMode[key] ?? 'ambient';
        await _api.command('set_mode', {'mode': mode});
        if (mounted) {
          setState(() { _mode = mode; _busy = false; });
          _flash('Scene: $key');
        }
        return;
      }
    }

    // 3) Elles → spørsmål til Ciel
    setState(() => _busy = false);
    _input.text = text;
    _ask();
  }

  // ── Ciel-på-sida: hjørne-overlay oppi andre appar (Module D) ──────────────
  Future<void> _initOverlay() async {
    try {
      _overlayPerm = await FlutterOverlayWindow.isPermissionGranted();
      if (!_overlayPerm) {
        _overlayPerm = await FlutterOverlayWindow.requestPermission() ?? false;
      }
      FlutterOverlayWindow.overlayListener.listen((data) async {
        if (data == 'open') {
          await FlutterOverlayWindow.closeOverlay();
          await Launcher.launchApp('Ciel'); // hent hovudappen fram igjen
        }
      });
    } catch (_) {}
  }

  // Vis hjørne-orben (foreground-service-overlay). Må kallast medan Ciel er i
  // framgrunn — då overlever overlayet at Samsung frys hovudprosessen.
  Future<void> _showCornerOrb() async {
    if (!_overlayPerm) return;
    try {
      if (!await FlutterOverlayWindow.isActive()) {
        await FlutterOverlayWindow.showOverlay(
          height: 460,
          width: 460,
          alignment: OverlayAlignment.topRight,
          flag: OverlayFlag.defaultFlag,
          enableDrag: true,
          overlayTitle: 'Ciel',
        );
      }
      // send gjeldande farge/modus til hjørne-orben så han matchar heim
      await Future.delayed(const Duration(milliseconds: 250));
      await FlutterOverlayWindow.shareData(jsonEncode({
        'c': _modeColor.toARGB32(),
        'g': _girlPermanent || _girlMode,
      }));
    } catch (_) {}
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) async {
    if (state == AppLifecycleState.resumed) _greet(); // "God morgon, Dr. Katchi" etter opplåsing
    if (!_overlayPerm) return;
    try {
      if (state == AppLifecycleState.paused) {
        await _showCornerOrb(); // best-effort (kan vere fryst på Samsung)
      } else if (state == AppLifecycleState.resumed) {
        if (await FlutterOverlayWindow.isActive()) {
          await FlutterOverlayWindow.closeOverlay();
        }
      }
    } catch (_) {}
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _events?.cancel();
    _askSub?.cancel();
    _input.dispose();
    _answerScroll.dispose();
    _hand.dispose();
    _voice.stop();
    _rec.dispose();
    super.dispose();
  }

  // ── Innstillingar (lang-trykk på orben) ──────────────────────────────────
  void _openSettings() {
    final urlCtrl = TextEditingController(text: _api.baseUrl);
    final passCtrl = TextEditingController();
    showModalBottomSheet(
      context: context,
      backgroundColor: const Color(0xFF0A0A0F),
      isScrollControlled: true,
      builder: (ctx) => Padding(
        padding: EdgeInsets.only(
            left: 20, right: 20, top: 20,
            bottom: 20 + MediaQuery.of(ctx).viewInsets.bottom),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          TextField(
            controller: urlCtrl,
            style: const TextStyle(color: Colors.white),
            decoration: const InputDecoration(
                labelText: 'Server-URL', labelStyle: TextStyle(color: Colors.white54)),
          ),
          const SizedBox(height: 16),
          Wrap(spacing: 8, children: [
            for (final m in kModeColors.keys)
              ChoiceChip(
                label: Text(m),
                selected: _mode == m,
                selectedColor: kModeColors[m],
                onSelected: (_) async {
                  await _api.command('set_mode', {'mode': m});
                  if (mounted) setState(() => _mode = m);
                },
              ),
          ]),
          const SizedBox(height: 8),
          SwitchListTile(
            title: const Text('Girl mode ♀ (alltid på)', style: TextStyle(color: Colors.white)),
            subtitle: const Text('trans-flagg som standard — av = gull + auto etter tema',
                style: TextStyle(color: Colors.white38, fontSize: 11)),
            value: _girlPermanent,
            onChanged: (v) async {
              final p = await SharedPreferences.getInstance();
              await p.setBool('girl_permanent', v);
              if (mounted) setState(() => _girlPermanent = v);
            },
          ),
          SwitchListTile(
            title: const Text('Stemme — les svar høgt', style: TextStyle(color: Colors.white)),
            value: _voiceOn,
            onChanged: (v) async {
              final p = await SharedPreferences.getInstance();
              await p.setBool('voice_on', v);
              if (!v) _voice.stop();
              if (mounted) setState(() => _voiceOn = v);
            },
          ),
          const Divider(color: Colors.white12, height: 24),
          StatefulBuilder(
            builder: (c, setSheet) => SwitchListTile(
              title: const Text('Lås Ciel (velkomstport)', style: TextStyle(color: Colors.white)),
              subtitle: const Text('opplevingslag — ikkje einings-tryggleik',
                  style: TextStyle(color: Colors.white38, fontSize: 11)),
              value: _lockEnabled,
              onChanged: (v) async {
                await _lock.setEnabled(v);
                setSheet(() {});
                setState(() => _lockEnabled = v);
              },
            ),
          ),
          Row(children: [
            Expanded(
              child: TextField(
                controller: passCtrl,
                obscureText: true,
                style: const TextStyle(color: Colors.white),
                decoration: const InputDecoration(
                    labelText: 'Set pennord', labelStyle: TextStyle(color: Colors.white54)),
              ),
            ),
            const SizedBox(width: 8),
            TextButton(
              onPressed: () async {
                final w = passCtrl.text.trim();
                if (w.isNotEmpty) {
                  await _lock.setPassphrase(w);
                  passCtrl.clear();
                  _flash('Pennord lagra 🤫');
                }
              },
              child: const Text('Lagre'),
            ),
          ]),
          const SizedBox(height: 8),
          OutlinedButton.icon(
            onPressed: () async {
              final dpr = MediaQuery.of(ctx).devicePixelRatio;
              final s = MediaQuery.of(ctx).size;
              final png = await renderOrbPng(
                width: (s.width * dpr).round(),
                height: (s.height * dpr).round(),
                color: _modeColor,
                girl: _girlPermanent || _girlMode,
              );
              if (png != null) {
                final ok = await Launcher.setLockWallpaper(png);
                _flash(ok ? 'Ciel sett som låsskjerm-bakgrunn 🌙' : 'Klarte ikkje setje låsskjerm');
              }
            },
            icon: const Icon(Icons.wallpaper),
            label: const Text('Sett Ciel-orb (heim + lås, stille)'),
          ),
          const SizedBox(height: 8),
          OutlinedButton.icon(
            onPressed: () => Launcher.openLiveWallpaper(),
            icon: const Icon(Icons.auto_awesome_motion),
            label: const Text('Sett LEVANDE Ciel-bakgrunn (orbit)'),
          ),
          const SizedBox(height: 8),
          FilledButton(
            onPressed: () async {
              final prefs = await SharedPreferences.getInstance();
              await prefs.setString('serverUrl', urlCtrl.text.trim());
              setState(() => _api = CielApi(urlCtrl.text.trim()));
              await _refreshState();
              _listenEvents();
              if (ctx.mounted) Navigator.pop(ctx);
            },
            child: const Text('Lagre & kople til'),
          ),
        ]),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final screen = MediaQuery.of(context).size;
    final orbSize = screen.shortestSide * .82;
    return Scaffold(
      backgroundColor: Colors.black,
      body: SafeArea(
        child: Stack(children: [
          Column(children: [
          // Diskret status (ikkje chrome — berre ein liten prikk)
          Padding(
            padding: const EdgeInsets.only(top: 8, right: 14),
            child: Align(
              alignment: Alignment.topRight,
              child: Icon(Icons.circle,
                  size: 8, color: _online ? _modeColor : Colors.white24),
            ),
          ),
          // Orben — trykk for å fokusere, lang-trykk for innstillingar
          Expanded(
            child: Center(
              child: GestureDetector(
                onTap: () => FocusScope.of(context).requestFocus(FocusNode()),
                onLongPress: _openSettings,
                child: InkLayer(
                  color: _modeColor,
                  onComplete: _onInk,
                  child: CielOrb(
                    modeColor: _modeColor,
                    girlMode: _girlPermanent || _girlMode,
                    brightness: (_girlPermanent || _girlMode) ? 1.45 : 1.0,
                    size: orbSize,
                  ),
                ),
              ),
            ),
          ),
          // Svar
          if (_answer.isNotEmpty)
            Container(
              constraints: BoxConstraints(maxHeight: screen.height * .3),
              margin: const EdgeInsets.symmetric(horizontal: 16),
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha:.04),
                borderRadius: BorderRadius.circular(14),
              ),
              child: SingleChildScrollView(
                controller: _answerScroll,
                child: Text(_answer,
                    style: const TextStyle(color: Colors.white, height: 1.5, fontSize: 15)),
              ),
            ),
          // Spør-felt
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
            child: Row(children: [
              IconButton(
                tooltip: 'Snakk til Ciel',
                icon: Icon(_recording ? Icons.stop_circle : Icons.mic,
                    color: _recording ? Colors.redAccent : _modeColor),
                onPressed: (_busy && !_recording) ? null : _toggleRecord,
              ),
              IconButton(
                tooltip: 'Djupt svar (SNL + Wikipedia + PubMed)',
                icon: Icon(Icons.auto_awesome,
                    color: _deep ? _modeColor : Colors.white38),
                onPressed: () => setState(() => _deep = !_deep),
              ),
              Expanded(
                child: TextField(
                  controller: _input,
                  style: const TextStyle(color: Colors.white),
                  textInputAction: TextInputAction.send,
                  onSubmitted: (_) => _ask(),
                  decoration: InputDecoration(
                    hintText: _online ? 'Spør Ciel…' : 'Ingen kontakt med hjernen',
                    hintStyle: const TextStyle(color: Colors.white30),
                    filled: true,
                    fillColor: Colors.white.withValues(alpha:.05),
                    border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(24), borderSide: BorderSide.none),
                    contentPadding: const EdgeInsets.symmetric(horizontal: 18, vertical: 12),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              _busy
                  ? const Padding(
                      padding: EdgeInsets.all(10),
                      child: SizedBox(
                          width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2)))
                  : IconButton(
                      icon: Icon(Icons.arrow_upward, color: _modeColor),
                      onPressed: _ask,
                    ),
            ]),
          ),
          ]),
          // Velkomst-helsing — tonar inn etter opplåsing, så ut igjen
          Positioned(
            top: 64,
            left: 0,
            right: 0,
            child: IgnorePointer(
              child: Center(
                child: AnimatedOpacity(
                  opacity: _showGreeting ? 1 : 0,
                  duration: const Duration(milliseconds: 900),
                  child: Text(
                    _greetingText(),
                    style: TextStyle(
                      color: _modeColor,
                      fontSize: 20,
                      letterSpacing: .5,
                      shadows: const [Shadow(blurRadius: 14, color: Colors.black)],
                    ),
                  ),
                ),
              ),
            ),
          ),
        ]),
      ),
    );
  }
}

import 'dart:async';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../services/ciel_api.dart';
import '../widgets/orb.dart';

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

class _HomeScreenState extends State<HomeScreen> {
  CielApi _api = CielApi(_defaultUrl);
  final _input = TextEditingController();
  final _answerScroll = ScrollController();

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
    _boot();
  }

  Future<void> _boot() async {
    final prefs = await SharedPreferences.getInstance();
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
    _askSub = _api.askStream(q, deep: _deep).listen((tok) {
      if (!mounted) return;
      setState(() => _answer += tok);
      _answerScroll.animateTo(_answerScroll.position.maxScrollExtent,
          duration: const Duration(milliseconds: 120), curve: Curves.easeOut);
    }, onError: (e) {
      if (mounted) setState(() => _answer += '\n\n[feil: $e]');
    }, onDone: () {
      if (mounted) setState(() => _busy = false);
    });
  }

  @override
  void dispose() {
    _events?.cancel();
    _askSub?.cancel();
    _input.dispose();
    _answerScroll.dispose();
    super.dispose();
  }

  // ── Innstillingar (lang-trykk på orben) ──────────────────────────────────
  void _openSettings() {
    final urlCtrl = TextEditingController(text: _api.baseUrl);
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
            title: const Text('Girl mode ♀', style: TextStyle(color: Colors.white)),
            value: _girlMode,
            onChanged: (v) async {
              await _api.command('set_girl_mode', {'on': v});
              if (mounted) setState(() => _girlMode = v);
            },
          ),
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
        child: Column(children: [
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
                child: CielOrb(
                  modeColor: _modeColor,
                  girlMode: _girlMode,
                  size: orbSize,
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
      ),
    );
  }
}

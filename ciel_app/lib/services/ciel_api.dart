import 'dart:async';
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:web_socket_channel/web_socket_channel.dart';

/// Klient mot Ciel-serveren (ciel_server.py). PC-en gjer alt arbeidet;
/// denne klienten renderer berre og strøymer svar.
class CielApi {
  String baseUrl; // t.d. http://192.168.10.194:8765

  CielApi(this.baseUrl);

  String get _wsBase =>
      baseUrl.replaceFirst('https://', 'wss://').replaceFirst('http://', 'ws://');

  Uri _u(String path) => Uri.parse('$baseUrl$path');

  // ── REST ────────────────────────────────────────────────────────────────
  Future<Map<String, dynamic>> getState() async {
    final r = await http.get(_u('/api/state')).timeout(const Duration(seconds: 6));
    return jsonDecode(utf8.decode(r.bodyBytes)) as Map<String, dynamic>;
  }

  Future<List<dynamic>> getNotes({int limit = 30}) async {
    final r = await http
        .get(_u('/api/vault/notes?limit=$limit'))
        .timeout(const Duration(seconds: 8));
    return (jsonDecode(utf8.decode(r.bodyBytes))['notes'] as List<dynamic>);
  }

  Future<Map<String, dynamic>> getNote(String path) async {
    final r = await http
        .get(_u('/api/vault/note?path=${Uri.encodeQueryComponent(path)}'))
        .timeout(const Duration(seconds: 8));
    return jsonDecode(utf8.decode(r.bodyBytes)) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> command(String name, [Map<String, dynamic> args = const {}]) async {
    final r = await http
        .post(_u('/api/command'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({'command': name, 'args': args}))
        .timeout(const Duration(seconds: 8));
    return jsonDecode(utf8.decode(r.bodyBytes)) as Map<String, dynamic>;
  }

  /// Send WAV-lyd → NB-Whisper på PC → transkribert tekst.
  Future<String?> transcribe(List<int> wavBytes) async {
    try {
      final req = http.MultipartRequest('POST', _u('/api/transcribe'));
      req.files.add(http.MultipartFile.fromBytes('file', wavBytes, filename: 'rec.wav'));
      final streamed = await req.send().timeout(const Duration(seconds: 120));
      final body = await streamed.stream.bytesToString();
      if (streamed.statusCode != 200) return null;
      return jsonDecode(body)['text'] as String?;
    } catch (_) {
      return null;
    }
  }

  /// Send ei delt GoodNotes-fil (PDF/bilete) → hjernen legg den i inn/ og
  /// stc_goodnotes lagar eit Obsidian-notat. Returnerer serveren sitt namn.
  Future<String?> uploadGoodNotes(List<int> bytes, String filename) async {
    try {
      final req = http.MultipartRequest('POST', _u('/api/goodnotes'));
      req.files.add(http.MultipartFile.fromBytes('file', bytes, filename: filename));
      final streamed = await req.send().timeout(const Duration(seconds: 120));
      final body = await streamed.stream.bytesToString();
      if (streamed.statusCode != 200) return null;
      return jsonDecode(body)['saved'] as String?;
    } catch (_) {
      return null;
    }
  }

  Future<bool> ping() async {
    try {
      final r = await http.get(_u('/health')).timeout(const Duration(seconds: 4));
      return r.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  // ── WebSocket: typewriter-svar ────────────────────────────────────────────
  /// Strøymer svaret token-for-token. Kastar [CielError] ved feil frå serveren.
  Stream<String> askStream(String question, {bool deep = false, String context = ''}) {
    final ch = WebSocketChannel.connect(Uri.parse('$_wsBase/ws/stream'));
    final ctrl = StreamController<String>();

    ch.sink.add(jsonEncode({'question': question, 'deep': deep, 'context': context}));

    final sub = ch.stream.listen((raw) {
      try {
        final d = jsonDecode(raw as String) as Map<String, dynamic>;
        if (d.containsKey('token')) ctrl.add(d['token'] as String);
        if (d.containsKey('error')) ctrl.addError(CielError(d['error'].toString()));
        if (d['done'] == true) {
          ctrl.close();
          ch.sink.close();
        }
      } catch (_) {/* ignorer ikkje-JSON */}
    }, onError: (e) {
      ctrl.addError(CielError(e.toString()));
      ctrl.close();
    }, onDone: () {
      if (!ctrl.isClosed) ctrl.close();
    });

    ctrl.onCancel = () async {
      await sub.cancel();
      await ch.sink.close();
    };
    return ctrl.stream;
  }

  // ── WebSocket: push-hendingar (modusbyte m.m.) ────────────────────────────
  Stream<Map<String, dynamic>> events() {
    final ch = WebSocketChannel.connect(Uri.parse('$_wsBase/ws/events'));
    return ch.stream.map((raw) {
      try {
        return jsonDecode(raw as String) as Map<String, dynamic>;
      } catch (_) {
        return <String, dynamic>{};
      }
    });
  }
}

class CielError implements Exception {
  final String message;
  CielError(this.message);
  @override
  String toString() => message;
}

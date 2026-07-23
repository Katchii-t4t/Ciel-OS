using System;
using System.Net.WebSockets;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;

namespace Ciel;

// Tynn klient mot hjernen (ciel_server.py) — same rolle som Flutter-appen.
// Lyttar på /ws/events og speglar modus/farge i sanntid (PC = klient, hjerne = sanning).
public sealed class CielClient
{
    readonly string _host;
    public Action<string>? OnColour;   // hex, t.d. "#AFA9EC"
    public Action<bool>? OnGirl;

    public CielClient(string host) => _host = host;   // t.d. 127.0.0.1:8765

    public void Start() => _ = Task.Run(EventLoop);

    async Task EventLoop()
    {
        var uri = new Uri($"ws://{_host}/ws/events");
        var buf = new byte[16384];
        while (true)
        {
            try
            {
                using var ws = new ClientWebSocket();
                await ws.ConnectAsync(uri, CancellationToken.None);
                while (ws.State == WebSocketState.Open)
                {
                    var sb = new StringBuilder();
                    WebSocketReceiveResult res;
                    do
                    {
                        res = await ws.ReceiveAsync(new ArraySegment<byte>(buf), CancellationToken.None);
                        if (res.MessageType == WebSocketMessageType.Close) break;
                        sb.Append(Encoding.UTF8.GetString(buf, 0, res.Count));
                    } while (!res.EndOfMessage);
                    if (sb.Length > 0) Handle(sb.ToString());
                }
            }
            catch { /* hjernen nede / nett-glipp — prøv igjen */ }
            await Task.Delay(3000); // reconnect-backoff
        }
    }

    void Handle(string json)
    {
        try
        {
            using var doc = JsonDocument.Parse(json);
            var root = doc.RootElement;
            var type = root.TryGetProperty("type", out var t) ? t.GetString() : null;
            switch (type)
            {
                case "mode":
                case "state":
                    if (root.TryGetProperty("colour", out var c)) OnColour?.Invoke(c.GetString() ?? "");
                    if (root.TryGetProperty("girl_mode", out var g) &&
                        (g.ValueKind == JsonValueKind.True || g.ValueKind == JsonValueKind.False))
                        OnGirl?.Invoke(g.GetBoolean());
                    break;
                case "girl_mode":
                    if (root.TryGetProperty("on", out var on)) OnGirl?.Invoke(on.GetBoolean());
                    break;
            }
        }
        catch { }
    }
}

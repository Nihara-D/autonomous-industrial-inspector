using System.Net.WebSockets;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace InspectorApi;

/// <summary>
/// Talks to rosbridge_server over a WebSocket: reads robot status, detections and the camera
/// image, and publishes operator commands. Reconnects by itself when the robot side restarts.
/// </summary>
public sealed class RosBridgeClient : BackgroundService
{
    private const string CommandTopic = "/inspector/command";

    private readonly RobotState state;
    private readonly RunHistory history;
    private readonly ILogger<RosBridgeClient> log;
    private readonly Uri url;
    private readonly SemaphoreSlim sendLock = new(1, 1);
    private ClientWebSocket? socket;

    public RosBridgeClient(RobotState state, RunHistory history, IConfiguration config,
                           ILogger<RosBridgeClient> log)
    {
        this.state = state;
        this.history = history;
        this.log = log;
        url = new Uri(config["Ros:BridgeUrl"] ?? "ws://localhost:9090");
    }

    protected override async Task ExecuteAsync(CancellationToken stop)
    {
        while (!stop.IsCancellationRequested)
        {
            try
            {
                await RunSession(stop);
            }
            catch (OperationCanceledException) when (stop.IsCancellationRequested)
            {
                break;
            }
            catch (Exception ex)
            {
                log.LogWarning("rosbridge not available ({Message}), retrying", ex.Message);
            }

            socket = null;
            state.SetBridge(false);
            try { await Task.Delay(TimeSpan.FromSeconds(2), stop); }
            catch (OperationCanceledException) { break; }
        }
    }

    public async Task<bool> PublishCommand(object command, CancellationToken ct)
    {
        var ws = socket;
        if (ws is not { State: WebSocketState.Open })
            return false;

        var data = JsonSerializer.Serialize(command);
        await Send(ws, new { op = "publish", topic = CommandTopic, msg = new { data } }, ct);
        return true;
    }

    private async Task RunSession(CancellationToken stop)
    {
        using var ws = new ClientWebSocket();
        using (var timeout = CancellationTokenSource.CreateLinkedTokenSource(stop))
        {
            timeout.CancelAfter(TimeSpan.FromSeconds(5));
            await ws.ConnectAsync(url, timeout.Token);
        }

        socket = ws;
        state.SetBridge(true);
        log.LogInformation("connected to rosbridge at {Url}", url);

        await Send(ws, new { op = "subscribe", topic = "/inspector/status",
                             type = "std_msgs/msg/String", queue_length = 1 }, stop);
        await Send(ws, new { op = "subscribe", topic = "/inspector/detections",
                             type = "std_msgs/msg/String", throttle_rate = 300, queue_length = 1 }, stop);
        await Send(ws, new { op = "subscribe", topic = "/camera/detections_image/compressed",
                             type = "sensor_msgs/msg/CompressedImage", throttle_rate = 200, queue_length = 1 }, stop);
        await Send(ws, new { op = "advertise", topic = CommandTopic,
                             type = "std_msgs/msg/String" }, stop);

        await ReceiveLoop(ws, stop);
    }

    private async Task ReceiveLoop(ClientWebSocket ws, CancellationToken stop)
    {
        var buffer = new byte[64 * 1024];
        using var message = new MemoryStream();

        while (ws.State == WebSocketState.Open && !stop.IsCancellationRequested)
        {
            message.SetLength(0);
            ValueWebSocketReceiveResult result;
            do
            {
                result = await ws.ReceiveAsync(buffer.AsMemory(), stop);
                if (result.MessageType == WebSocketMessageType.Close)
                    return;
                message.Write(buffer, 0, result.Count);
            } while (!result.EndOfMessage);

            message.Position = 0;
            Handle(message);
        }
    }

    private void Handle(Stream json)
    {
        JsonNode? root;
        try { root = JsonNode.Parse(json); }
        catch (JsonException) { return; }

        if (root?["op"]?.GetValue<string>() != "publish")
            return;

        var msg = root["msg"];
        switch (root["topic"]?.GetValue<string>())
        {
            case "/inspector/status":
                if (Embedded(msg) is { } status)
                {
                    state.SetStatus(status);
                    history.Observe(status);
                }
                break;

            case "/inspector/detections":
                if (Embedded(msg) is { } detections)
                    state.SetDetections(detections);
                break;

            case "/camera/detections_image/compressed":
                var b64 = msg?["data"]?.GetValue<string>();
                if (!string.IsNullOrEmpty(b64))
                    state.SetJpeg(Convert.FromBase64String(b64));
                break;
        }
    }

    // The robot sends JSON text inside a std_msgs/String.
    private static JsonNode? Embedded(JsonNode? msg)
    {
        var text = msg?["data"]?.GetValue<string>();
        if (text is null) return null;
        try { return JsonNode.Parse(text); }
        catch (JsonException) { return null; }
    }

    private async Task Send(ClientWebSocket ws, object payload, CancellationToken ct)
    {
        var bytes = JsonSerializer.SerializeToUtf8Bytes(payload);
        await sendLock.WaitAsync(ct);
        try { await ws.SendAsync(new ReadOnlyMemory<byte>(bytes), WebSocketMessageType.Text, true, ct); }
        finally { sendLock.Release(); }
    }
}

using System.Text.Json.Nodes;

namespace InspectorApi;

/// <summary>Latest data received from the robot. Written by the bridge client, read by the API.</summary>
public sealed class RobotState
{
    private readonly object gate = new();
    private bool bridgeConnected;
    private JsonNode? status;
    private JsonNode? detections;
    private DateTime statusAt = DateTime.MinValue;
    private byte[]? jpeg;
    private DateTime jpegAt = DateTime.MinValue;

    public void SetBridge(bool connected)
    {
        lock (gate)
        {
            bridgeConnected = connected;
            if (!connected)
            {
                status = null;
                detections = null;
                jpeg = null;
            }
        }
    }

    public void SetStatus(JsonNode node)
    {
        lock (gate) { status = node; statusAt = DateTime.UtcNow; }
    }

    public void SetDetections(JsonNode node)
    {
        lock (gate) { detections = node; }
    }

    public void SetJpeg(byte[] data)
    {
        lock (gate) { jpeg = data; jpegAt = DateTime.UtcNow; }
    }

    public byte[]? Jpeg()
    {
        lock (gate) { return jpeg; }
    }

    public string? RobotPhase()
    {
        lock (gate) { return status?["state"]?.GetValue<string>(); }
    }

    public object Snapshot()
    {
        lock (gate)
        {
            var online = bridgeConnected && (DateTime.UtcNow - statusAt).TotalSeconds < 5;
            return new
            {
                bridge = bridgeConnected,
                robotOnline = online,
                status = online ? status?.DeepClone() : null,
                detections = online ? detections?.DeepClone() : null,
                cameraAgeSeconds = jpeg is null ? (double?)null : (DateTime.UtcNow - jpegAt).TotalSeconds
            };
        }
    }
}

using System.Text.Json;
using System.Text.Json.Nodes;

namespace InspectorApi;

public sealed record RunRecord(
    int Id,
    DateTime StartedAt,
    DateTime FinishedAt,
    string[] Sorted,
    string[] Failed,
    string[] Skipped);

/// <summary>Keeps a short list of finished sorting runs in a JSON file next to the app.</summary>
public sealed class RunHistory
{
    private const int MaxRuns = 50;
    private readonly object gate = new();
    private readonly string path;
    private readonly List<RunRecord> runs = new();
    private string lastPhase = "";
    private DateTime startedAt;

    public RunHistory(IHostEnvironment env)
    {
        var dir = Path.Combine(env.ContentRootPath, "data");
        Directory.CreateDirectory(dir);
        path = Path.Combine(dir, "runs.json");
        try
        {
            if (File.Exists(path))
                runs = JsonSerializer.Deserialize<List<RunRecord>>(File.ReadAllText(path)) ?? new();
        }
        catch (JsonException)
        {
            runs = new();   // damaged file, start fresh
        }
    }

    public IReadOnlyList<RunRecord> All()
    {
        lock (gate) { return runs.OrderByDescending(r => r.Id).ToList(); }
    }

    /// <summary>Called for every status message; records a run when the robot goes running -> ready.</summary>
    public void Observe(JsonNode status)
    {
        var phase = status["state"]?.GetValue<string>() ?? "";
        lock (gate)
        {
            if (phase == "running" && lastPhase != "running")
                startedAt = DateTime.UtcNow;

            if (lastPhase == "running" && phase == "ready")
            {
                var record = new RunRecord(
                    runs.Count == 0 ? 1 : runs.Max(r => r.Id) + 1,
                    startedAt == default ? DateTime.UtcNow : startedAt,
                    DateTime.UtcNow,
                    Strings(status["done"]),
                    Strings(status["failed"]),
                    Strings(status["skipped"]));
                runs.Add(record);
                if (runs.Count > MaxRuns)
                    runs.RemoveRange(0, runs.Count - MaxRuns);
                Save();
            }
            lastPhase = phase;
        }
    }

    private static string[] Strings(JsonNode? array) =>
        array is JsonArray a
            ? a.Select(x => x?.GetValue<string>() ?? "").Where(s => s.Length > 0).ToArray()
            : Array.Empty<string>();

    private void Save()
    {
        File.WriteAllText(path, JsonSerializer.Serialize(runs, new JsonSerializerOptions { WriteIndented = true }));
    }
}

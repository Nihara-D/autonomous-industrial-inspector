using InspectorApi;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddSingleton<RobotState>();
builder.Services.AddSingleton<RunHistory>();
builder.Services.AddSingleton<RosBridgeClient>();
builder.Services.AddHostedService(sp => sp.GetRequiredService<RosBridgeClient>());

var app = builder.Build();

var knownColours = new[] { "red", "green", "blue" };

app.UseDefaultFiles();
app.UseStaticFiles();

app.MapGet("/api/status", (RobotState robot) => Results.Json(robot.Snapshot()));

app.MapGet("/api/camera.jpg", (RobotState robot, HttpResponse response) =>
{
    var jpeg = robot.Jpeg();
    if (jpeg is null)
        return Results.NotFound();
    response.Headers.CacheControl = "no-store";
    return Results.File(jpeg, "image/jpeg");
});

app.MapGet("/api/runs", (RunHistory history) => Results.Json(history.All()));

app.MapPost("/api/start", async (StartRequest body, RobotState robot, RosBridgeClient ros,
                                 CancellationToken ct) =>
{
    var colours = (body.Colors ?? Array.Empty<string>())
        .Select(c => c.Trim().ToLowerInvariant())
        .Where(c => knownColours.Contains(c))
        .Distinct()
        .ToArray();

    if (colours.Length == 0)
        return Results.BadRequest(new { message = "Select at least one colour." });

    var phase = robot.RobotPhase();
    if (phase != "ready")
        return Results.Conflict(new
        {
            message = phase is null ? "The robot is offline." : $"The robot is {phase}; wait until it is ready."
        });

    return await Forward(ros, new { action = "start", colors = colours }, ct);
});

app.MapPost("/api/stop", async (RobotState robot, RosBridgeClient ros, CancellationToken ct) =>
{
    if (robot.RobotPhase() != "running")
        return Results.Conflict(new { message = "Nothing is running." });
    return await Forward(ros, new { action = "stop" }, ct);
});

app.MapPost("/api/reset-slots", async (RobotState robot, RosBridgeClient ros, CancellationToken ct) =>
{
    if (robot.RobotPhase() != "ready")
        return Results.Conflict(new { message = "The robot has to be idle to reset the pedestal." });
    return await Forward(ros, new { action = "reset_slots" }, ct);
});

app.MapFallbackToFile("index.html");

app.Run();

static async Task<IResult> Forward(RosBridgeClient ros, object command, CancellationToken ct)
{
    var sent = await ros.PublishCommand(command, ct);
    return sent
        ? Results.Json(new { ok = true }, statusCode: 202)
        : Results.Json(new { message = "Not connected to the robot." }, statusCode: 503);
}

record StartRequest(string[]? Colors);

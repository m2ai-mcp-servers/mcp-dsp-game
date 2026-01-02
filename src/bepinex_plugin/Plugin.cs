using BepInEx;
using BepInEx.Configuration;
using BepInEx.Logging;
using HarmonyLib;
using UnityEngine;
using System.Reflection;

namespace DysonMCP
{
    /// <summary>
    /// Main plugin entry point for DysonMCP.
    /// Provides real-time factory metrics to MCP server via WebSocket.
    /// </summary>
    [BepInPlugin(PluginGuid, PluginName, PluginVersion)]
    public class DysonMCPPlugin : BaseUnityPlugin
    {
        public const string PluginGuid = "com.memyselfai.dysonmcp";
        public const string PluginName = "DysonMCP";
        public const string PluginVersion = "1.0.0";

        // Static references for patches to access
        public static DysonMCPPlugin Instance { get; private set; }
        public static ManualLogSource Log { get; private set; }

        private Harmony _harmony;
        private WebSocketServer _wsServer;
        private MetricsCollector _collector;
        private int _frameCounter;

        // Configuration entries
        public static ConfigEntry<int> WebSocketPort { get; private set; }
        public static ConfigEntry<int> MetricsUpdateFrequency { get; private set; }
        public static ConfigEntry<bool> EnableRealTimeStreaming { get; private set; }
        public static ConfigEntry<bool> EnableDetailedLogging { get; private set; }

        /// <summary>
        /// Plugin initialization - called when BepInEx loads the plugin.
        /// </summary>
        void Awake()
        {
            Instance = this;
            Log = Logger;

            // Load configuration
            LoadConfiguration();

            // Log API diagnostics first
            LogApiDiagnostics();

            // Initialize Harmony patches
            try
            {
                _harmony = new Harmony(PluginGuid);
                _harmony.PatchAll();
                Logger.LogInfo("Harmony patches applied successfully");
            }
            catch (System.Exception ex)
            {
                Logger.LogWarning($"Some Harmony patches failed (plugin will continue): {ex.Message}");
                // Continue without patches - WebSocket server can still work for manual data collection
            }

            // Initialize metrics collector
            _collector = new MetricsCollector(MetricsUpdateFrequency.Value);
            MetricsCollector.Instance = _collector;

            // Initialize WebSocket server if streaming enabled
            if (EnableRealTimeStreaming.Value)
            {
                try
                {
                    _wsServer = new WebSocketServer(WebSocketPort.Value);
                    _wsServer.Start();
                    Logger.LogInfo($"WebSocket server started on port {WebSocketPort.Value}");
                }
                catch (System.Exception ex)
                {
                    Logger.LogError($"Failed to start WebSocket server: {ex.Message}");
                }
            }

            Logger.LogInfo($"{PluginName} v{PluginVersion} loaded successfully");
        }

        /// <summary>
        /// Load plugin configuration from BepInEx config file.
        /// </summary>
        private void LoadConfiguration()
        {
            WebSocketPort = Config.Bind(
                "Network",
                "Port",
                8470,
                "WebSocket server port for MCP communication (1024-65535)"
            );

            MetricsUpdateFrequency = Config.Bind(
                "Performance",
                "UpdateFrequency",
                1,
                new ConfigDescription(
                    "Metrics collection frequency in Hz (1-60). Higher values = more CPU usage.",
                    new AcceptableValueRange<int>(1, 60)
                )
            );

            EnableRealTimeStreaming = Config.Bind(
                "Features",
                "RealTimeStreaming",
                true,
                "Enable real-time metric streaming via WebSocket"
            );

            EnableDetailedLogging = Config.Bind(
                "Debug",
                "DetailedLogging",
                false,
                "Enable detailed debug logging (may impact performance)"
            );
        }

        /// <summary>
        /// Called every frame by Unity.
        /// </summary>
        void Update()
        {
            if (_collector == null) return;

            _frameCounter++;

            // Collect and broadcast metrics at configured frequency
            // Assuming 60 FPS, divide by frequency to get frame interval
            int frameInterval = Mathf.Max(1, 60 / MetricsUpdateFrequency.Value);

            if (_frameCounter % frameInterval == 0)
            {
                try
                {
                    // Collect current metrics
                    var metrics = _collector.CollectMetrics();

                    // Broadcast to connected clients
                    if (_wsServer != null && _wsServer.HasClients && metrics != null)
                    {
                        _wsServer.BroadcastMetrics(metrics);
                    }
                }
                catch (System.Exception ex)
                {
                    if (EnableDetailedLogging.Value)
                    {
                        Logger.LogWarning($"Error collecting/broadcasting metrics: {ex.Message}");
                    }
                }
            }
        }

        /// <summary>
        /// Log API diagnostics to help debug Harmony patches.
        /// </summary>
        private void LogApiDiagnostics()
        {
            try
            {
                // Check AssemblerComponent methods
                var assemblerType = typeof(AssemblerComponent);
                Logger.LogInfo($"=== AssemblerComponent Methods ===");
                foreach (var method in assemblerType.GetMethods(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance))
                {
                    if (method.Name.Contains("Update") || method.Name.Contains("Internal"))
                    {
                        var parameters = string.Join(", ", System.Array.ConvertAll(method.GetParameters(), p => $"{p.ParameterType.Name} {p.Name}"));
                        Logger.LogInfo($"  {method.Name}({parameters})");
                    }
                }

                // Check PowerSystem methods
                var powerType = typeof(PowerSystem);
                Logger.LogInfo($"=== PowerSystem Methods ===");
                foreach (var method in powerType.GetMethods(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance))
                {
                    if (method.Name.Contains("Update") || method.Name.Contains("GameTick"))
                    {
                        var parameters = string.Join(", ", System.Array.ConvertAll(method.GetParameters(), p => $"{p.ParameterType.Name} {p.Name}"));
                        Logger.LogInfo($"  {method.Name}({parameters})");
                    }
                }

                // Check CargoTraffic methods
                var cargoType = typeof(CargoTraffic);
                Logger.LogInfo($"=== CargoTraffic Methods ===");
                foreach (var method in cargoType.GetMethods(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance))
                {
                    if (method.Name.Contains("Update") || method.Name.Contains("GameTick"))
                    {
                        var parameters = string.Join(", ", System.Array.ConvertAll(method.GetParameters(), p => $"{p.ParameterType.Name} {p.Name}"));
                        Logger.LogInfo($"  {method.Name}({parameters})");
                    }
                }
            }
            catch (System.Exception ex)
            {
                Logger.LogWarning($"API diagnostics failed: {ex.Message}");
            }
        }

        /// <summary>
        /// Plugin cleanup - called when plugin is unloaded.
        /// </summary>
        void OnDestroy()
        {
            Logger.LogInfo("Shutting down DysonMCP...");

            // Stop WebSocket server
            try
            {
                _wsServer?.Stop();
            }
            catch (System.Exception ex)
            {
                Logger.LogWarning($"Error stopping WebSocket server: {ex.Message}");
            }

            // Remove Harmony patches
            try
            {
                _harmony?.UnpatchSelf();
            }
            catch (System.Exception ex)
            {
                Logger.LogWarning($"Error removing Harmony patches: {ex.Message}");
            }

            // Clear collector
            _collector = null;
            MetricsCollector.Instance = null;

            Logger.LogInfo("DysonMCP shutdown complete");
        }
    }
}

using HarmonyLib;
using System;

namespace DysonMCP.Patches
{
    /// <summary>
    /// Harmony patches for tracking belt/logistics throughput.
    /// Hooks into CargoTraffic.GameTick to capture belt data.
    /// </summary>
    [HarmonyPatch]
    public static class LogisticsPatch
    {
        private static int _tickCounter = 0;
        private static readonly int SampleInterval = 30; // Sample every 0.5 seconds (30 ticks)

        // Belt tier max throughput (items per second)
        private const float BELT_MK1_THROUGHPUT = 6f;
        private const float BELT_MK2_THROUGHPUT = 12f;
        private const float BELT_MK3_THROUGHPUT = 30f;

        /// <summary>
        /// Patch target: CargoTraffic.GameTickBeforePower
        /// This method manages all belt/path movement each tick.
        /// </summary>
        [HarmonyPatch(typeof(CargoTraffic), "GameTickBeforePower")]
        [HarmonyPostfix]
        public static void CargoTrafficGameTick_Postfix(
            ref CargoTraffic __instance,
            long time)
        {
            try
            {
                if (MetricsCollector.Instance == null) return;

                // Only sample periodically to reduce overhead
                _tickCounter++;
                if (_tickCounter % SampleInterval != 0) return;

                // Get planet ID
                int planetId = __instance.factory?.planetId ?? 0;
                if (planetId <= 0) return;

                // Sample belt data
                if (__instance.beltPool != null)
                {
                    // Sample a subset of belts to minimize performance impact
                    int sampleStep = Math.Max(1, __instance.beltCursor / 100); // Sample ~100 belts max

                    for (int i = 1; i < __instance.beltCursor; i += sampleStep)
                    {
                        var belt = __instance.beltPool[i];
                        if (belt.id != i || belt.id <= 0) continue;

                        // Get belt segment info
                        int itemType = 0;
                        int itemCount = 0;

                        // Check cargo path for items
                        if (__instance.pathPool != null && belt.segPathId > 0 &&
                            belt.segPathId < __instance.pathPool.Length)
                        {
                            var path = __instance.pathPool[belt.segPathId];
                            if (path != null && path.id > 0)
                            {
                                // Count items in this belt segment
                                itemCount = CountItemsInSegment(__instance, belt, path, out itemType);
                            }
                        }

                        // Determine belt tier and max throughput
                        float maxThroughput = GetBeltMaxThroughput(belt.speed);
                        int bufferLength = belt.segLength;

                        MetricsCollector.RecordBeltThroughput(
                            planetId: planetId,
                            beltId: belt.id,
                            itemType: itemType,
                            itemCount: itemCount,
                            bufferLength: bufferLength,
                            maxThroughput: maxThroughput,
                            gameTick: time
                        );
                    }
                }
            }
            catch (Exception ex)
            {
                if (DysonMCPPlugin.EnableDetailedLogging?.Value == true)
                {
                    DysonMCPPlugin.Log?.LogWarning($"LogisticsPatch error: {ex.Message}");
                }
            }
        }

        /// <summary>
        /// Count items in a belt segment.
        /// </summary>
        private static int CountItemsInSegment(
            CargoTraffic traffic,
            BeltComponent belt,
            CargoPath path,
            out int primaryItemType)
        {
            primaryItemType = 0;
            int count = 0;

            try
            {
                if (path.buffer == null) return 0;

                // Count items in the path buffer for this segment
                int segStart = belt.segIndex;
                int segEnd = segStart + belt.segLength;

                // Scan cargo buffer for items
                // DSP uses a byte buffer where items are stored with their IDs
                for (int i = 0; i < path.buffer.Length; i += 4)
                {
                    if (i + 3 < path.buffer.Length)
                    {
                        // Item ID is stored in the buffer (implementation varies by DSP version)
                        int itemId = path.buffer[i];
                        if (itemId > 0)
                        {
                            count++;
                            if (primaryItemType == 0)
                            {
                                primaryItemType = itemId;
                            }
                        }
                    }
                }
            }
            catch
            {
                // Fallback for buffer access errors
            }

            return count;
        }

        /// <summary>
        /// Get max throughput based on belt speed.
        /// </summary>
        private static float GetBeltMaxThroughput(int beltSpeed)
        {
            // DSP belt speeds:
            // MK1: 1, MK2: 2, MK3: 5
            // Actual throughput: MK1: 6/s, MK2: 12/s, MK3: 30/s
            switch (beltSpeed)
            {
                case 1:
                    return BELT_MK1_THROUGHPUT;
                case 2:
                    return BELT_MK2_THROUGHPUT;
                case 5:
                    return BELT_MK3_THROUGHPUT;
                default:
                    // Estimate based on speed ratio
                    return beltSpeed * 6f;
            }
        }

        // InserterComponent patch removed - not implemented and has API compatibility issues
    }
}

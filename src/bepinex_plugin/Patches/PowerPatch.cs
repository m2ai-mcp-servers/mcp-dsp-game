using HarmonyLib;
using System;

namespace DysonMCP.Patches
{
    /// <summary>
    /// Harmony patches for tracking power grid state.
    /// Hooks into PowerSystem.GameTick to capture power generation and consumption.
    /// </summary>
    [HarmonyPatch]
    public static class PowerPatch
    {
        private static int _tickCounter = 0;
        private static readonly int SampleInterval = 60; // Sample once per second (60 ticks)

        /// <summary>
        /// Patch target: PowerSystem.GameTick
        /// This method is called every tick for each planet's power system.
        /// </summary>
        [HarmonyPatch(typeof(PowerSystem), "GameTick")]
        [HarmonyPostfix]
        public static void PowerSystemGameTick_Postfix(
            ref PowerSystem __instance,
            long time,
            bool isActive,
            bool multithreaded,
            int threadOrdinal)
        {
            try
            {
                if (MetricsCollector.Instance == null) return;
                if (!isActive) return;

                // Only sample periodically to reduce overhead
                _tickCounter++;
                if (_tickCounter % SampleInterval != 0) return;

                int planetId = __instance.planet?.id ?? 0;
                if (planetId <= 0) return;

                // Calculate total generation
                long totalGeneration = 0;
                int generatorCount = 0;

                if (__instance.genPool != null)
                {
                    for (int i = 1; i < __instance.genCursor; i++)
                    {
                        var gen = __instance.genPool[i];
                        if (gen.id == i && gen.id > 0)
                        {
                            totalGeneration += gen.genEnergyPerTick;
                            generatorCount++;
                        }
                    }
                }

                // Calculate total consumption
                long totalConsumption = 0;
                int consumerCount = 0;

                if (__instance.consumerPool != null)
                {
                    for (int i = 1; i < __instance.consumerCursor; i++)
                    {
                        var consumer = __instance.consumerPool[i];
                        if (consumer.id == i && consumer.id > 0)
                        {
                            totalConsumption += consumer.workEnergyPerTick;
                            consumerCount++;
                        }
                    }
                }

                // Calculate accumulator state
                long accumulatorCurrent = 0;
                long accumulatorMax = 0;
                int accumulatorCount = 0;

                if (__instance.accPool != null)
                {
                    for (int i = 1; i < __instance.accCursor; i++)
                    {
                        var acc = __instance.accPool[i];
                        if (acc.id == i && acc.id > 0)
                        {
                            accumulatorCurrent += acc.curEnergy;
                            accumulatorMax += acc.maxEnergy;
                            accumulatorCount++;
                        }
                    }
                }

                // Also include exchanger contributions (energy exchangers)
                if (__instance.excPool != null)
                {
                    for (int i = 1; i < __instance.excCursor; i++)
                    {
                        var exc = __instance.excPool[i];
                        if (exc.id == i && exc.id > 0)
                        {
                            // Exchangers can both generate and consume
                            if (exc.currEnergyPerTick > 0)
                            {
                                totalGeneration += exc.currEnergyPerTick;
                            }
                            else if (exc.currEnergyPerTick < 0)
                            {
                                totalConsumption += -exc.currEnergyPerTick;
                            }
                        }
                    }
                }

                MetricsCollector.RecordPower(
                    planetId: planetId,
                    generationEnergyPerTick: totalGeneration,
                    consumptionEnergyPerTick: totalConsumption,
                    accumulatorCurrent: accumulatorCurrent,
                    accumulatorMax: accumulatorMax,
                    generatorCount: generatorCount,
                    consumerCount: consumerCount,
                    accumulatorCount: accumulatorCount,
                    gameTick: time
                );
            }
            catch (Exception ex)
            {
                if (DysonMCPPlugin.EnableDetailedLogging?.Value == true)
                {
                    DysonMCPPlugin.Log?.LogWarning($"PowerPatch error: {ex.Message}");
                }
            }
        }

        // PlanetFactory.GameTick patch removed - method doesn't exist in current DSP version
    }
}

using HarmonyLib;
using System;

namespace DysonMCP.Patches
{
    /// <summary>
    /// Harmony patches for tracking assembler and smelter production.
    /// Hooks into AssemblerComponent.InternalUpdate to capture output events.
    /// </summary>
    [HarmonyPatch]
    public static class ProductionPatch
    {
        /// <summary>
        /// Patch target: AssemblerComponent.InternalUpdate
        /// This method is called every tick for each active assembler/smelter.
        /// </summary>
        [HarmonyPatch(typeof(AssemblerComponent), "InternalUpdate")]
        [HarmonyPostfix]
        public static void AssemblerInternalUpdate_Postfix(
            ref AssemblerComponent __instance,
            float power,
            int[] productRegister,
            int[] consumeRegister)
        {
            try
            {
                // Skip if no collector or instance is idle
                if (MetricsCollector.Instance == null) return;
                if (__instance.recipeId <= 0) return;

                // Get factory reference to find planet ID
                int planetId = GetPlanetId(__instance);
                if (planetId <= 0) return;

                // Check production state
                bool inputStarved = IsInputStarved(__instance);
                bool outputBlocked = IsOutputBlocked(__instance);

                // Calculate items produced this tick
                // Products are placed in produced[] array slots
                int itemsProduced = 0;
                if (__instance.produced != null && __instance.produced.Length > 0)
                {
                    // Check if products were just added (production completed)
                    // The productCounts array shows how many of each product per craft
                    if (__instance.time >= __instance.timeSpend && __instance.replicating)
                    {
                        // A craft just completed
                        for (int i = 0; i < __instance.productCounts.Length; i++)
                        {
                            itemsProduced += __instance.productCounts[i];
                        }
                    }
                }

                // Only record if there was production or state needs update
                if (itemsProduced > 0 || inputStarved || outputBlocked)
                {
                    long gameTick = GetGameTick();

                    MetricsCollector.RecordProduction(
                        planetId: planetId,
                        assemblerId: __instance.id,
                        recipeId: __instance.recipeId,
                        protoId: __instance.products != null && __instance.products.Length > 0
                            ? __instance.products[0] : 0,
                        itemsProduced: itemsProduced,
                        gameTick: gameTick,
                        inputStarved: inputStarved,
                        outputBlocked: outputBlocked,
                        powerLevel: power
                    );
                }
            }
            catch (Exception ex)
            {
                if (DysonMCPPlugin.EnableDetailedLogging?.Value == true)
                {
                    DysonMCPPlugin.Log?.LogWarning($"ProductionPatch error: {ex.Message}");
                }
            }
        }

        /// <summary>
        /// Check if assembler is starved for input materials.
        /// </summary>
        private static bool IsInputStarved(AssemblerComponent assembler)
        {
            if (assembler.requires == null) return false;

            for (int i = 0; i < assembler.requires.Length; i++)
            {
                if (assembler.served != null && i < assembler.served.Length)
                {
                    // If served count is less than required for next craft
                    if (assembler.served[i] < assembler.requireCounts[i])
                    {
                        return true;
                    }
                }
            }
            return false;
        }

        /// <summary>
        /// Check if assembler output slots are full.
        /// </summary>
        private static bool IsOutputBlocked(AssemblerComponent assembler)
        {
            if (assembler.produced == null || assembler.productCounts == null) return false;

            for (int i = 0; i < assembler.produced.Length; i++)
            {
                if (i < assembler.productCounts.Length)
                {
                    // Check if produced buffer is near capacity
                    // Assemblers typically have 4-slot output buffers (4 * stack size)
                    int maxBuffer = 4 * GetStackSize(assembler.products[i]);
                    if (assembler.produced[i] >= maxBuffer - assembler.productCounts[i])
                    {
                        return true;
                    }
                }
            }
            return false;
        }

        /// <summary>
        /// Get the planet ID for an assembler instance.
        /// </summary>
        private static int GetPlanetId(AssemblerComponent assembler)
        {
            try
            {
                // Access through GameMain.localPlanet or find factory by entityId
                var gameMainType = Type.GetType("GameMain, Assembly-CSharp");
                if (gameMainType != null)
                {
                    var localPlanetField = gameMainType.GetProperty("localPlanet",
                        System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Static);
                    if (localPlanetField != null)
                    {
                        var planet = localPlanetField.GetValue(null);
                        if (planet != null)
                        {
                            var idProp = planet.GetType().GetProperty("id");
                            if (idProp != null)
                            {
                                return (int)idProp.GetValue(planet);
                            }
                        }
                    }
                }
            }
            catch
            {
                // Fallback
            }
            return 1; // Default to planet 1
        }

        /// <summary>
        /// Get item stack size.
        /// </summary>
        private static int GetStackSize(int itemId)
        {
            try
            {
                var ldbType = Type.GetType("LDB, Assembly-CSharp");
                if (ldbType != null)
                {
                    var itemsField = ldbType.GetProperty("items",
                        System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Static);
                    if (itemsField != null)
                    {
                        var items = itemsField.GetValue(null);
                        if (items != null)
                        {
                            var selectMethod = items.GetType().GetMethod("Select");
                            if (selectMethod != null)
                            {
                                var item = selectMethod.Invoke(items, new object[] { itemId });
                                if (item != null)
                                {
                                    var stackSizeProp = item.GetType().GetProperty("StackSize");
                                    if (stackSizeProp != null)
                                    {
                                        return (int)stackSizeProp.GetValue(item);
                                    }
                                }
                            }
                        }
                    }
                }
            }
            catch
            {
                // Fallback
            }
            return 100; // Default stack size
        }

        /// <summary>
        /// Get current game tick.
        /// </summary>
        private static long GetGameTick()
        {
            try
            {
                var gameMainType = Type.GetType("GameMain, Assembly-CSharp");
                if (gameMainType != null)
                {
                    var gameTickField = gameMainType.GetField("gameTick",
                        System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Static);
                    if (gameTickField != null)
                    {
                        return (long)gameTickField.GetValue(null);
                    }
                }
            }
            catch
            {
                // Fallback
            }
            return DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();
        }
    }
}

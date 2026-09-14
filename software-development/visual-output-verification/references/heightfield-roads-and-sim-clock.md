# Heightfield roads + sim clock (Charter / Three.js)

Session 2026-08-17. User: Halt did nothing; speeds felt unwired; roads sat flat on hills like stairs.

## Sim clock vs render loop

Visible time (sky, sun, fog, cars, HUD clock) must follow `simulation.speed` and `simulation.cityTime`.

- Do **not** increment a `frame` counter every `requestAnimationFrame` and use that for day/night.
- `Halt` (`speed === PAUSED`) must freeze: `simulate()` return, day/night, cars, HUD date. Verify by reading the date label twice ~1.5s apart.
- Slow / Day / Rush must change `cityTime` rate (tick interval **and** `cityTime += 1|2|4`), not just a React button class.
- Do **not** put `speed` or `currentTool` in the `useEffect` that constructs `CityView`. Remounting the WebGL view on every Halt click is a bug. Keep tool in a ref.

HUD stats: update the clock every frame (or you will miss pause). Heavier census can stay periodic.

## Seat authored tiles on a heightfield

Kenney (or any) road mesh at `(x, landHeight(x,z), z)` with identity rotation is a **flat slab**. Grass vertices move; the road does not → stair steps / hovering edges.

1. `sampleHeight` bilinearly.
2. Wrap the fitted piece in a group. Pitch/roll: `atan2(Δh, span)` from samples ±0.45 on X and Z.
3. Smooth the **terrain mesh** under pavement (average raw neighbor heights) so the grass ramps with the street.
4. Fit GLB to 1 tile **first**, then wrap, then yaw. Never `rotation.y =` on the same node you just recentered — pieces miss at intersections.
5. Kenney City Kit Roads look like parking stalls; `road-bridge.glb` is a highway. Per-tile streets: straight/bend/tee/cross/end only. Water: custom narrow deck.

## Verify

- Halt: clock string unchanged after 1.5s; sky does not keep cycling.
- Orbit a hillside road: deck lies on the grass, not a hovering rectangle.

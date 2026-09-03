# TPG MAGURA Weapon-USV POC

This branch is an isolated proof of concept for making the existing MAGURA W6 / Sea Dragon hull render as a **weapon object** rather than relying on DCS naval-unit collision behavior.

## What this first pass tests

1. Can DCS instantiate a ~1000 kg custom self-homing weapon at **very low speed**?
2. Can an intentionally huge virtual lifting area keep it controllable around **20-25 m/s (39-49 kt)**?
3. Can it retain an assigned moving naval target?
4. Can it reach physical impact without the naval-AI avoidance turn?
5. How low can its reference point run before water/terrain collision or autopilot instability occurs?

## Deliberate cheats

The visible EDM is the existing `MAGURA_W6_SeaDragon_R73` hull. The FM is deliberately unrelated to the visible body:

- 22 m² virtual lifting/reference area
- high low-speed lift
- 10 m/s nominal `v_min`
- 22 m/s nominal `v_mid`
- low 2 g turn limit
- long, weak motor
- active-radar/MMW-style self-homing surrogate

This is not meant to be physically honest aerodynamics. It is meant to discover whether DCS will permit a guided weapon to behave like a surface attack craft.

## Dependency

The existing MAGURA W6 / Sea Dragon mod must remain installed because this POC references its already-mounted:

`MAGURA_W6_SeaDragon_R73.edm`

No working production MAGURA unit is modified by this branch.

## Important current limitation

This commit declares the weapon object only. DCS still requires a launcher object/task to create a weapon instance. The next test harness should attach this weapon to an isolated surface launcher (or duplicate an existing MAGURA test launcher) so AI can assign a moving ship target.

## First test matrix once launcher hookup is in place

| Test | Target | Launch distance | Desired result |
|---|---|---:|---|
| A1 | stationary ship | 1 km | weapon object spawns |
| A2 | stationary ship | 3 km | holds near sea level |
| B1 | ship 10 kt | 3 km | sustained target tracking |
| B2 | ship 20 kt | 3 km | sustained target tracking |
| B3 | ship 20 kt turning | 3 km | lateral correction without large pitch excursion |
| C1 | same target | 3 km | physical impact / hit event |

Record DCS log, debrief log, and Tacview for every run.

## Parameters to sweep after first successful spawn

- virtual area: 12 / 22 / 32 m²
- `dCydA`: 1.0 / 1.65 / 2.4
- desired speed: 18 / 22 / 26 / 30 m/s
- g limit: 1.5 / 2 / 3
- reference altitude / launch connector height
- vertical damping/autopilot gain family

Do not tune warhead or visuals until the weapon is proven to track and hit.

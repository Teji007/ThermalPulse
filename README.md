# ThermalPulse

**Lightweight, open-source WMI thermal, fan, and power control center for Windows laptops (tested and verified on Acer Nitro V15 `ANV15-51`).**

[![License: MIT](https://img.shields.io/badge/License-MIT-ef4444.svg)](LICENSE)
[![Platform: Windows 10/11 x64](https://img.shields.io/badge/Platform-Windows%2010%2F11%20x64-0ea5e9.svg)](#installation)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776ab.svg)](#installation)

ThermalPulse communicates directly with standard Windows power APIs, GPU telemetry libraries (`nvml.dll` / `atiadlxx.dll`), and firmware-exposed WMI thermal interfaces (`AcerGamingFunction`) to provide profile switching on AC and battery, custom fan curves, live diagnostics, and hardware safety guardrailsâ€”without kernel drivers or heavy background suites.

---

## Disclaimer & Non-Affiliation

> **Independent Project Notice:** ThermalPulse is an independent, community-developed open-source utility and is **not affiliated with, endorsed by, or sponsored by Acer Inc., NVIDIA Corporation, AMD, or Intel**. "Acer", "Nitro", and "NitroSense" are registered trademarks of Acer Inc. and are referenced solely to describe hardware compatibility.
>
> **Hardware & Warranty Notice:** This software modifies Windows power plans, fan curves, and firmware-exposed thermal profiles. While built-in guardrails (Thermal Fail-Safe, Battery Safety Cutoff, and automatic fan reset on exit) are enabled by default, operating laptops at high wattage on battery accelerates cell wear, and OEMs may decline warranty claims if hardware damage results from manual overrides. Use at your own risk under the [MIT License](LICENSE).

---

## Key Features

- **AC & Battery Thermal Profile Control:** Direct WMI switching across `Eco`, `Quiet`, `Balanced`, and `Performance` with an optional battery profile watchdog and Windows DC boost/cooling/PCIe tuning.
- **Built-In Hardware Safety Guardrails:**
  - **Battery Safety Cutoff (20-60%, default 30%):** Automatically drops to Balanced on low charge to prevent voltage-sag shutdowns.
  - **Thermal Fail-Safe:** Automatically switches fans to Max if CPU hits 92 C or GPU hits 86 C in Manual/Curve mode.
  - **Clean Exit Reset:** Automatically restores EC fan control to `Auto` and unlocks GPU clock caps when exiting the app.
- **Animated Hardware Dashboard:** 50 FPS procedural mode animations (automatically paused when minimized to tray), eased circular thermal gauges, rolling 60-sample CPU/GPU temperature and battery wattage sparklines, and live battery wear/ETA diagnostics.
- **Manual Fans, Curves & CoolBoost:** `Auto`, `Max`, `Manual` sliders (25-100%), draggable 5-point `Curve` editor with hysteresis, and one-click **CoolBoost Cooldown** (Max fans until <= 50 C).
- **CPU / GPU Tuning & Optimus Inspector:** Hybrid P-Core/E-Core frequency caps and EPP controls, NVIDIA NVML GPU clock lock (software undervolt), live GPU throttle reason badges, AMD ADL2 telemetry support, and an **Optimus dGPU Wake-Up Inspector** to identify background apps keeping the discrete GPU awake.
- **Automation & Analytics:** Auto refresh-rate switching, per-mode brightness, per-app auto-profiles with EcoQoS guard, global hotkeys (`Ctrl+Alt+1..4`, `Ctrl+Alt+H`), click-through Mini HUD, OSD toast, and local SQLite telemetry recording with CSV export.

---

## Installation

### Option 1: Windows Installer (Recommended)
1. Download `ThermalPulse_Setup_v1.0.0.exe` from the [Releases](https://github.com/Teji007/ThermalPulse/releases) page.
2. Run the setup wizard (Administrator privileges are required for Windows WMI hardware access).
3. Review and accept the MIT License and first-run hardware safety notice.

### Option 2: Run or Build from Source
```powershell
git clone https://github.com/Teji007/ThermalPulse.git
cd ThermalPulse
python -m pip install -r requirements.txt
python src\thermalpulse.py
```

To compile the standalone `.exe` and Inno Setup installer locally:
```powershell
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

---

## Developer & License

Developed by **Tejinder Pal Singh** ([@Teji007](https://github.com/Teji007)).
Licensed under the [MIT License](LICENSE).
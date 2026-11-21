# Changelog

All notable changes to **ThermalPulse** are documented in this file.

## [1.0.0] - 2026-11-21
### Added
- Initial public release of **ThermalPulse** by Tejinder Pal Singh (MIT License).
- Brand-neutral open-source architecture with explicit non-affiliation disclaimer and first-run hardware safety notice.
- Direct WMI thermal profile switching (`Eco`, `Quiet`, `Balanced`, `Performance`) with battery watchdog and Windows DC power tuning.
- Built-in hardware safety guardrails: automatic fan reset to `Auto` and GPU clock unlock on exit, Thermal Fail-Safe (92 C CPU / 86 C GPU), and Battery Safety Cutoff (20-60%, default 30%).
- Animated 50 FPS dashboard, thermal arc gauges, rolling temperature and battery wattage sparklines, and battery health diagnostics.
- Manual fan sliders, interactive 5-point CPU/GPU fan curve editor with hysteresis, and CoolBoost cooldown timer.
- Hybrid P-Core/E-Core CPU frequency/EPP tuning, NVIDIA NVML clock lock, throttle badges, Optimus dGPU Wake-Up Inspector, and AMD ADL2 support.
- Per-app auto-profiles with EcoQoS guard, auto refresh-rate switcher, per-mode brightness, global hotkeys, click-through Mini HUD, SQLite/CSV session recorder, and in-app Help & About tab.
- PyInstaller `--onedir` build and Inno Setup 6 Windows installer with silent upgrade/uninstall handling.
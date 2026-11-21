# Contributing to ThermalPulse

Contributions, bug reports, and WMI hardware compatibility reports are welcome!

## Guidelines
- Keep the project brand-neutral and never commit proprietary OEM binaries, drivers, logos, or copyrighted assets.
- Keep dependencies minimal (Python standard library, `PySide6`, `pywin32`, or OS/GPU DLLs via `ctypes`).
- Include your laptop model, BIOS version, and **Hardware -> Inspect WMI Methods** log output when reporting hardware compatibility issues.
- Verify syntax with `python -m py_compile src\thermalpulse.py` before opening a pull request.
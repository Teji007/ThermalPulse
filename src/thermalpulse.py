import csv
import ctypes
import json
import math
import os
import random
import re
import sqlite3
import subprocess
import sys
import time
from collections import deque
from datetime import datetime

import pywintypes
import win32api
import win32com.client
import win32con
import win32pdh
import win32service
from PySide6.QtNetwork import (
    QLocalServer, 
    QLocalSocket
)
from PySide6.QtCore import (
    Property,
    QAbstractNativeEventFilter,
    QEasingCurve,
    QPointF,
    QPropertyAnimation,
    QRectF,
    Qt,
    QTimer,
    QUrl,
)
from PySide6.QtGui import (
    QAction,
    QColor,
    QDesktopServices,
    QFont,
    QIcon,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QRadialGradient,
)
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSlider,
    QSpinBox,
    QSystemTrayIcon,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

# =============================================================================
# CONSTANTS, PATHS & CONFIG DEFAULTS
# =============================================================================

APP_NAME = "ThermalPulse"
APP_VERSION = "1.0.0"
APP_ID = "Teji007.ThermalPulse.ControlCenter.1"
APP_DEVELOPER = "Tejinder Pal Singh"
APP_REPO_URL = "https://github.com/Teji007/ThermalPulse"
APP_LICENSE = "MIT License"

EXE_DIR = os.path.dirname(sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__))
if os.path.exists(os.path.join(EXE_DIR, "portable.flag")):
    DATA_DIR = EXE_DIR
else:
    DATA_DIR = os.path.join(os.environ.get("LOCALAPPDATA", EXE_DIR), APP_NAME)
    os.makedirs(DATA_DIR, exist_ok=True)

CONFIG_PATH = os.path.join(DATA_DIR, "config.json")
TELEMETRY_DB_PATH = os.path.join(DATA_DIR, "telemetry.db")
_RES_ROOT = getattr(sys, "_MEIPASS", os.path.dirname(EXE_DIR))
ICON_PATH = os.path.join(_RES_ROOT, "assets", "app.ico")

PROFILES = {
    "Eco": (0x06, 0x060B),
    "Quiet": (0x00, 0x000B),
    "Balanced": (0x01, 0x010B),
    "Performance": (0x04, 0x040B),
}
MODE_ORDER = ["Eco", "Quiet", "Balanced", "Performance"]
ID_TO_NAME = {v[0]: k for k, v in PROFILES.items()}

MODE_THEME = {
    "Eco": {
        "color": QColor("#10b981"),
        "secondary": QColor("#34d399"),
        "tagline": "Maximum Battery Efficiency • Low Acoustic Floor",
    },
    "Quiet": {
        "color": QColor("#38bdf8"),
        "secondary": QColor("#7dd3fc"),
        "tagline": "Whisper-Quiet Acoustics • Soft Thermal Curve",
    },
    "Balanced": {
        "color": QColor("#818cf8"),
        "secondary": QColor("#a5b4fc"),
        "tagline": "Adaptive Power & Thermals • Everyday Equilibrium",
    },
    "Performance": {
        "color": QColor("#ef4444"),
        "secondary": QColor("#f97316"),
        "tagline": "Unrestricted DC Boost • Active Cooling Override",
    },
}

FAN_BEHAVIOR = {
    "Auto": 0x410009,
    "Max": 0x820009,
    "Custom": 0xC30009,
}
FAN_ID_CPU = 0x01
FAN_ID_GPU = 0x04

SYSINFO_CPU_TEMP = 0x0101
SYSINFO_CPU_RPM = 0x0201
SYSINFO_GPU_RPM = 0x0601
SYSINFO_GPU_TEMP = 0x0A01

MISC_KB_TIMEOUT = 0x02
MISC_USB_CHARGE = 0x03
MISC_LCD_OVERDRIVE = 0x05

SUB_PROC = "54533251-82be-4824-96c1-47b60b740d00"
SUB_PCIE = "501a4d13-42af-4429-9fd1-a8218c268e20"
GUID_PERFBOOSTMODE = "be337238-0d82-4146-a960-4f3749d470c7"
GUID_PROCTHROTTLEMAX = "bc5038f7-23e0-4960-96da-33abaf5935ec"
GUID_SYSCOOLPOL = "94d3a615-a899-4ac5-ae2b-e4d8f634367f"
GUID_PROCFREQMAX = "75b0ae3f-bce0-45a7-8c89-c9611c25e100"
GUID_PROCFREQMAX1 = "75b0ae3f-bce0-45a7-8c89-c9611c25e101"
GUID_PERFEPP = "36687f9e-e3a5-4dbf-b1dc-15eb381c6863"
GUID_PERFEPP1 = "36687f9e-e3a5-4dbf-b1dc-15eb381c6864"
GUID_ASPM = "ee12f906-d277-404b-b6da-e5fa1a576df5"

THERMAL_FAILSAFE_CPU_C = 92
THERMAL_FAILSAFE_GPU_C = 86
COOLBOOST_TARGET_C = 50
COOLBOOST_MAX_SECS = 180

DEFAULT_CONFIG = {
    "dc_lock": True,
    "win_dc_tuning": True,
    "poll_gpu_api": True,
    "safety_cutoff_pct": 30,
    "fan_mode": "Auto",
    "manual_cpu_fan": 60,
    "manual_gpu_fan": 60,
    "curve_hysteresis": 3,
    "thermal_failsafe": True,
    "cpu_curve": [[40, 25], [55, 42], [70, 65], [82, 85], [90, 100]],
    "gpu_curve": [[40, 25], [55, 40], [68, 62], [78, 84], [85, 100]],
    "auto_refresh_rate": False,
    "hotkeys_enabled": True,
    "osd_toast_enabled": True,
    "hud_visible": False,
    "hud_corner": "Top-Right",
    "app_profiles_enabled": False,
    "app_profile_target_mode": "Performance",
    "app_profile_target_fan": "Curve",
    "ecoqos_guard_enabled": True,
    "watched_apps": ["cyberpunk2077.exe", "eldenring.exe", "blender.exe"],
    "cpu_pcore_cap_mhz": 0,
    "cpu_ecore_cap_mhz": 0,
    "cpu_epp_pcore": 20,
    "cpu_epp_ecore": 45,
    "gpu_clock_cap_mhz": 0,
    "brightness_auto": False,
    "mode_brightness": {"Eco": 45, "Quiet": 55, "Balanced": 70, "Performance": 90},
    "nitro_key_hijack": False,
    "nitro_key_vk": 255,
    "nitro_key_scan": 117,
    "acer_service_guard": False,
    "restore_acer_services_on_exit": True,
    "disclaimer_accepted": False,
}


# =============================================================================
# WIN32 STRUCTURES & LOW-LEVEL APIs
# =============================================================================

class SYSTEM_POWER_STATUS(ctypes.Structure):
    _fields_ = [
        ("ACLineStatus", ctypes.c_ubyte),
        ("BatteryFlag", ctypes.c_ubyte),
        ("BatteryLifePercent", ctypes.c_ubyte),
        ("SystemStatusFlag", ctypes.c_ubyte),
        ("BatteryLifeTime", ctypes.c_ulong),
        ("BatteryFullLifeTime", ctypes.c_ulong),
    ]


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class WIN32_MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", ctypes.c_void_p),
        ("message", ctypes.c_uint),
        ("wParam", ctypes.c_size_t),
        ("lParam", ctypes.c_ssize_t),
        ("time", ctypes.c_uint32),
        ("pt", POINT),
    ]


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", ctypes.c_uint32),
        ("cntUsage", ctypes.c_uint32),
        ("th32ProcessID", ctypes.c_uint32),
        ("th32DefaultHeapID", ctypes.c_size_t),
        ("th32ModuleID", ctypes.c_uint32),
        ("cntThreads", ctypes.c_uint32),
        ("th32ParentProcessID", ctypes.c_uint32),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", ctypes.c_uint32),
        ("szExeFile", ctypes.c_wchar * 260),
    ]


class PROCESS_POWER_THROTTLING_STATE(ctypes.Structure):
    _fields_ = [
        ("Version", ctypes.c_uint32),
        ("ControlMask", ctypes.c_uint32),
        ("StateMask", ctypes.c_uint32),
    ]


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", ctypes.c_uint32),
        ("scanCode", ctypes.c_uint32),
        ("flags", ctypes.c_uint32),
        ("time", ctypes.c_uint32),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


kernel32 = ctypes.windll.kernel32
kernel32.CreateToolhelp32Snapshot.argtypes = [ctypes.c_uint32, ctypes.c_uint32]
kernel32.CreateToolhelp32Snapshot.restype = ctypes.c_void_p
kernel32.Process32FirstW.argtypes = [ctypes.c_void_p, ctypes.POINTER(PROCESSENTRY32W)]
kernel32.Process32FirstW.restype = ctypes.c_int
kernel32.Process32NextW.argtypes = [ctypes.c_void_p, ctypes.POINTER(PROCESSENTRY32W)]
kernel32.Process32NextW.restype = ctypes.c_int
kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
kernel32.CloseHandle.restype = ctypes.c_int
kernel32.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
kernel32.OpenProcess.restype = ctypes.c_void_p
kernel32.TerminateProcess.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
kernel32.TerminateProcess.restype = ctypes.c_int
kernel32.SetPriorityClass.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
kernel32.SetPriorityClass.restype = ctypes.c_int
kernel32.SetProcessInformation.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32]
kernel32.SetProcessInformation.restype = ctypes.c_int

user32 = ctypes.windll.user32
user32.RegisterHotKey.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_uint, ctypes.c_uint]
user32.RegisterHotKey.restype = ctypes.c_int
user32.UnregisterHotKey.argtypes = [ctypes.c_void_p, ctypes.c_int]
user32.UnregisterHotKey.restype = ctypes.c_int

HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, ctypes.c_int, ctypes.c_size_t, ctypes.c_ssize_t)
user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, ctypes.c_void_p, ctypes.c_uint32]
user32.SetWindowsHookExW.restype = ctypes.c_void_p
user32.CallNextHookEx.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_size_t, ctypes.c_ssize_t]
user32.CallNextHookEx.restype = ctypes.c_ssize_t
user32.UnhookWindowsHookEx.argtypes = [ctypes.c_void_p]
user32.UnhookWindowsHookEx.restype = ctypes.c_int


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def relaunch_as_admin():
    params = " ".join(f'"{arg}"' for arg in sys.argv)
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
    sys.exit(0)


def get_power_status() -> tuple[bool, int]:
    status = SYSTEM_POWER_STATUS()
    if kernel32.GetSystemPowerStatus(ctypes.byref(status)):
        on_ac = status.ACLineStatus == 1
        pct = status.BatteryLifePercent if status.BatteryLifePercent <= 100 else 100
        return on_ac, pct
    return True, 100


def get_process_map() -> dict[int, str]:
    pmap: dict[int, str] = {}
    snap = kernel32.CreateToolhelp32Snapshot(0x00000002, 0)
    if not snap or snap == ctypes.c_void_p(-1).value:
        return pmap
    try:
        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
        if kernel32.Process32FirstW(snap, ctypes.byref(entry)):
            while True:
                pmap[int(entry.th32ProcessID)] = entry.szExeFile.lower()
                if not kernel32.Process32NextW(snap, ctypes.byref(entry)):
                    break
    finally:
        kernel32.CloseHandle(snap)
    return pmap


def terminate_pid(pid: int) -> bool:
    h = kernel32.OpenProcess(0x0001, 0, int(pid))
    if not h:
        return False
    try:
        return bool(kernel32.TerminateProcess(h, 1))
    finally:
        kernel32.CloseHandle(h)


def boost_process_priority_no_ecoqos(pid: int) -> bool:
    h = kernel32.OpenProcess(0x0200, 0, int(pid))
    if not h:
        return False
    try:
        ok1 = bool(kernel32.SetPriorityClass(h, 0x00000080))
        state = PROCESS_POWER_THROTTLING_STATE(Version=1, ControlMask=0x1, StateMask=0)
        ok2 = bool(kernel32.SetProcessInformation(h, 4, ctypes.byref(state), ctypes.sizeof(state)))
        return ok1 or ok2
    finally:
        kernel32.CloseHandle(h)


def lerp_color(c1: QColor, c2: QColor, t: float) -> QColor:
    return QColor(
        int(c1.red() + (c2.red() - c1.red()) * t),
        int(c1.green() + (c2.green() - c1.green()) * t),
        int(c1.blue() + (c2.blue() - c1.blue()) * t),
        int(c1.alpha() + (c2.alpha() - c1.alpha()) * t),
    )


def temp_to_color(temp_c: float | None) -> QColor:
    if temp_c is None:
        return QColor("#64748b")
    if temp_c >= 84:
        return QColor("#ef4444")
    if temp_c >= 70:
        return QColor("#f59e0b")
    return QColor("#10b981")


def eval_fan_curve(points: list[list[int]], temp_c: float) -> int:
    pts = sorted(points, key=lambda item: item[0])
    if not pts:
        return 50
    if temp_c <= pts[0][0]:
        return int(pts[0][1])
    if temp_c >= pts[-1][0]:
        return int(pts[-1][1])
    for i in range(len(pts) - 1):
        t0, s0 = pts[i]
        t1, s1 = pts[i + 1]
        if t0 <= temp_c <= t1:
            if t1 == t0:
                return int(s1)
            return int(round(s0 + ((temp_c - t0) / (t1 - t0)) * (s1 - s0)))
    return int(pts[-1][1])


def load_config() -> dict:
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                user_cfg = json.load(f)
            if isinstance(user_cfg, dict):
                # Migrate old poll_nvml key if present
                if "poll_nvml" in user_cfg and "poll_gpu_api" not in user_cfg:
                    user_cfg["poll_gpu_api"] = user_cfg["poll_nvml"]
                for k, v in user_cfg.items():
                    if k == "mode_brightness" and isinstance(v, dict):
                        cfg["mode_brightness"].update(v)
                    else:
                        cfg[k] = v
        except Exception:
            pass
    return cfg


def save_config(cfg: dict):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass


# =============================================================================
# UNIVERSAL CPU & GPU BACKENDS
# =============================================================================

class UniversalCPUMonitor:
    def __init__(self):
        self.raw_name = "Unknown CPU"
        self.short_name = "CPU"
        self.vendor = "Unknown"
        self.family_tag = "Standard"
        self.is_hybrid = False
        self.cores = os.cpu_count() or 8
        self.base_mhz = 2100.0
        self._detect_cpu()

        self.query = None
        self.c_perf = None
        self.c_util = None
        try:
            self.query = win32pdh.OpenQuery()
            add_fn = getattr(win32pdh, "AddEnglishCounter", win32pdh.AddCounter)
            self.c_perf = add_fn(self.query, r"\Processor Information(_Total)\% Processor Performance")
            self.c_util = add_fn(self.query, r"\Processor Information(_Total)\% Processor Utility")
            win32pdh.CollectQueryData(self.query)
        except Exception:
            self.query = None

    def _detect_cpu(self):
        try:
            cim = win32com.client.GetObject(r"winmgmts:\\.\root\cimv2")
            for cpu in cim.InstancesOf("Win32_Processor"):
                self.raw_name = str(getattr(cpu, "Name", "") or "").strip()
                mfr = str(getattr(cpu, "Manufacturer", "") or "")
                if getattr(cpu, "MaxClockSpeed", None):
                    self.base_mhz = float(cpu.MaxClockSpeed)
                if getattr(cpu, "NumberOfCores", None):
                    self.cores = int(cpu.NumberOfCores)

                low = self.raw_name.lower()
                if "intel" in low or "intel" in mfr.lower():
                    self.vendor = "Intel"
                    if "ultra" in low:
                        self.family_tag = "Intel Core Ultra (Hybrid)"
                        self.is_hybrid = True
                    elif re.search(r"i[3579]-1[234]\d{2,3}", low) or re.search(r"core.*1[234]\d{2}", low):
                        self.family_tag = "Intel 12th-14th Gen (Hybrid P/E)"
                        self.is_hybrid = True
                    else:
                        self.family_tag = "Intel Core"
                        self.is_hybrid = True
                elif "amd" in low or "ryzen" in low or "amd" in mfr.lower():
                    self.vendor = "AMD"
                    if "ryzen ai" in low or re.search(r"ryzen.*\b(8540|8440|7540|7440|3\d{2})\b", low):
                        self.family_tag = "AMD Ryzen AI / Hybrid Zen"
                        self.is_hybrid = True
                    else:
                        self.family_tag = "AMD Ryzen (CPPC)"

                clean = re.sub(r"\(R\)|\(TM\)|CPU|@.*$|with Radeon.*$", "", self.raw_name, flags=re.IGNORECASE)
                clean = re.sub(r"\b\d+(th|st|nd|rd)\s+Gen\b", "", clean, flags=re.IGNORECASE)
                clean = re.sub(r"\s+", " ", clean).strip()
                self.short_name = clean[:28] if clean else "CPU"
                break
        except Exception:
            pass

    def read(self) -> tuple[int | None, int | None]:
        if not self.query:
            return None, None
        try:
            win32pdh.CollectQueryData(self.query)
            _, perf_pct = win32pdh.GetFormattedCounterValue(self.c_perf, win32pdh.PDH_FMT_DOUBLE)
            _, util_pct = win32pdh.GetFormattedCounterValue(self.c_util, win32pdh.PDH_FMT_DOUBLE)
            mhz = int(round(self.base_mhz * (perf_pct / 100.0)))
            util = max(0, min(100, int(round(util_pct))))
            return mhz, util
        except Exception:
            return None, None

    def close(self):
        if self.query:
            try:
                win32pdh.CloseQuery(self.query)
            except Exception:
                pass


class NVMLUtilization(ctypes.Structure):
    _fields_ = [("gpu", ctypes.c_uint), ("memory", ctypes.c_uint)]


class NVMLProcessInfo_v2(ctypes.Structure):
    _fields_ = [
        ("pid", ctypes.c_uint),
        ("usedGpuMemory", ctypes.c_ulonglong),
        ("gpuInstanceId", ctypes.c_uint),
        ("computeInstanceId", ctypes.c_uint),
    ]


class NVMLProcessInfo_v1(ctypes.Structure):
    _fields_ = [("pid", ctypes.c_uint), ("usedGpuMemory", ctypes.c_ulonglong)]


NVML_THROTTLE_BITS = [
    (0x0000000000000001, "Idle"),
    (0x0000000000000002, "Clock Lock"),
    (0x0000000000000004, "SW Power Cap"),
    (0x0000000000000008, "HW Slowdown"),
    (0x0000000000000010, "Sync Boost"),
    (0x0000000000000020, "SW Thermal"),
    (0x0000000000000040, "HW Thermal"),
    (0x0000000000000080, "Power Brake"),
]


class NVMLBackend:
    def __init__(self):
        self.lib = None
        self.handle = ctypes.c_void_p()
        self.available = False
        self.name = "NVIDIA GPU"
        self.vendor = "NVIDIA"
        self._init_nvml()

    def _init_nvml(self):
        candidates = [
            "nvml.dll",
            os.path.join(
                os.environ.get("ProgramFiles", r"C:\Program Files"),
                "NVIDIA Corporation",
                "NVSMI",
                "nvml.dll",
            ),
        ]
        for path in candidates:
            try:
                lib = ctypes.CDLL(path)
                if lib.nvmlInit_v2() == 0:
                    if lib.nvmlDeviceGetHandleByIndex_v2(ctypes.c_uint(0), ctypes.byref(self.handle)) == 0:
                        self.lib = lib
                        self.available = True
                        buf = ctypes.create_string_buffer(96)
                        if lib.nvmlDeviceGetName(self.handle, buf, ctypes.c_uint(96)) == 0:
                            raw = buf.value.decode("utf-8", errors="ignore").strip()
                            raw = raw.replace("NVIDIA GeForce ", "").replace(" Laptop GPU", "")
                            self.name = raw[:28] if raw else "NVIDIA RTX"
                        return
                    lib.nvmlShutdown()
            except Exception:
                continue

    def read(self) -> dict:
        data = {"core_mhz": None, "mem_mhz": None, "temp_c": None, "power_w": None, "util_pct": None, "throttle_reasons": []}
        if not self.available or not self.lib:
            return data

        val = ctypes.c_uint()
        if self.lib.nvmlDeviceGetClockInfo(self.handle, ctypes.c_uint(0), ctypes.byref(val)) == 0:
            data["core_mhz"] = val.value
        if self.lib.nvmlDeviceGetClockInfo(self.handle, ctypes.c_uint(2), ctypes.byref(val)) == 0:
            data["mem_mhz"] = val.value
        if self.lib.nvmlDeviceGetTemperature(self.handle, ctypes.c_uint(0), ctypes.byref(val)) == 0:
            data["temp_c"] = val.value
        if self.lib.nvmlDeviceGetPowerUsage(self.handle, ctypes.byref(val)) == 0:
            data["power_w"] = round(val.value / 1000.0, 1)
        util = NVMLUtilization()
        if self.lib.nvmlDeviceGetUtilizationRates(self.handle, ctypes.byref(util)) == 0:
            data["util_pct"] = util.gpu

        reasons_mask = ctypes.c_ulonglong(0)
        for fn_name in ("nvmlDeviceGetCurrentClocksEventReasons", "nvmlDeviceGetCurrentClocksThrottleReasons"):
            fn = getattr(self.lib, fn_name, None)
            if fn is not None:
                try:
                    if fn(self.handle, ctypes.byref(reasons_mask)) == 0:
                        decoded = [label for bit, label in NVML_THROTTLE_BITS if reasons_mask.value & bit]
                        data["throttle_reasons"] = decoded if decoded else ["Optimal"]
                        break
                except Exception:
                    continue
        return data

    def set_clock_lock(self, max_mhz: int) -> tuple[bool, str]:
        if not self.available or not self.lib:
            return False, "NVML not active"
        try:
            if max_mhz <= 0:
                fn = getattr(self.lib, "nvmlDeviceResetGpuLockedClocks", None)
                if not fn:
                    return False, "ResetGpuLockedClocks unavailable"
                rc = fn(self.handle)
                return rc == 0, f"Unlocked GPU clocks (rc={rc})"
            fn = getattr(self.lib, "nvmlDeviceSetGpuLockedClocks", None)
            if not fn:
                return False, "SetGpuLockedClocks unavailable"
            rc = fn(self.handle, ctypes.c_uint(210), ctypes.c_uint(int(max_mhz)))
            return rc == 0, f"Locked GPU max clock to {max_mhz} MHz (rc={rc})"
        except Exception as exc:
            return False, str(exc)

    def get_running_processes(self) -> list[dict]:
        if not self.available or not self.lib:
            return []
        pmap = get_process_map()
        found: dict[int, dict] = {}
        for base_name, kind in (
            ("nvmlDeviceGetGraphicsRunningProcesses", "Graphics"),
            ("nvmlDeviceGetComputeRunningProcesses", "Compute"),
        ):
            for suffix, struct_cls in (("_v3", NVMLProcessInfo_v2), ("_v2", NVMLProcessInfo_v2), ("", NVMLProcessInfo_v1)):
                fn = getattr(self.lib, base_name + suffix, None)
                if fn is None:
                    continue
                try:
                    count = ctypes.c_uint(64)
                    arr = (struct_cls * 64)()
                    rc = fn(self.handle, ctypes.byref(count), arr)
                    if rc in (0, 7):
                        for i in range(min(count.value, 64)):
                            pid = int(arr[i].pid)
                            mem_b = int(arr[i].usedGpuMemory)
                            mem_mb = round(mem_b / (1024 * 1024), 1) if 0 < mem_b < (1 << 60) else 0.0
                            exe = pmap.get(pid, f"PID {pid}")
                            if pid in found:
                                found[pid]["vram_mb"] = max(found[pid]["vram_mb"], mem_mb)
                                if kind not in found[pid]["type"]:
                                    found[pid]["type"] += f"/{kind}"
                            else:
                                found[pid] = {"pid": pid, "exe": exe, "vram_mb": mem_mb, "type": kind}
                        break
                except Exception:
                    continue
        return sorted(found.values(), key=lambda x: x["vram_mb"], reverse=True)

    def shutdown(self):
        if self.available and self.lib:
            try:
                self.lib.nvmlShutdown()
            except Exception:
                pass
            self.available = False


class ADLAdapterInfo(ctypes.Structure):
    _fields_ = [
        ("iSize", ctypes.c_int), ("iAdapterIndex", ctypes.c_int), ("strUDID", ctypes.c_char * 256),
        ("iBusNumber", ctypes.c_int), ("iDeviceNumber", ctypes.c_int), ("iFunctionNumber", ctypes.c_int),
        ("iVendorID", ctypes.c_int), ("strAdapterName", ctypes.c_char * 256), ("strDisplayName", ctypes.c_char * 256),
        ("iPresent", ctypes.c_int), ("iExist", ctypes.c_int), ("strDriverPath", ctypes.c_char * 256),
        ("strDriverPathExt", ctypes.c_char * 256), ("strPNPString", ctypes.c_char * 256), ("iOSDisplayIndex", ctypes.c_int),
    ]


class ADLSingleSensorData(ctypes.Structure):
    _fields_ = [("supported", ctypes.c_int), ("value", ctypes.c_int)]


class ADLPMLogDataOutput(ctypes.Structure):
    _fields_ = [("size", ctypes.c_int), ("sensors", ADLSingleSensorData * 256)]


ADL_MALLOC_CB = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_int)


class AMDADLBackend:
    def __init__(self):
        self.lib = None
        self.ctx = ctypes.c_void_p()
        self.adapter_idx = -1
        self.available = False
        self.name = "AMD Radeon"
        self.vendor = "AMD"
        self._malloc_ref = None
        self._init_adl()

    def _init_adl(self):
        try:
            lib = ctypes.CDLL("atiadlxx.dll")
            msvcrt = ctypes.CDLL("msvcrt.dll")
            msvcrt.malloc.argtypes = [ctypes.c_size_t]
            msvcrt.malloc.restype = ctypes.c_void_p
            self._malloc_ref = ADL_MALLOC_CB(lambda sz: msvcrt.malloc(max(1, sz)))
            create_fn = getattr(lib, "ADL2_Main_Control_Create", None)
            if not create_fn:
                return
            create_fn.argtypes = [ADL_MALLOC_CB, ctypes.c_int, ctypes.POINTER(ctypes.c_void_p)]
            create_fn.restype = ctypes.c_int
            if create_fn(self._malloc_ref, 1, ctypes.byref(self.ctx)) != 0:
                return
            num = ctypes.c_int(0)
            if lib.ADL2_Adapter_NumberOfAdapters_Get(self.ctx, ctypes.byref(num)) != 0 or num.value <= 0:
                return
            arr = (ADLAdapterInfo * num.value)()
            if lib.ADL2_Adapter_AdapterInfo_Get(self.ctx, arr, ctypes.sizeof(arr)) != 0:
                return
            chosen = None
            for i in range(num.value):
                nm = arr[i].strAdapterName.decode("utf-8", errors="ignore").strip()
                if not nm:
                    continue
                if "rx " in nm.lower() or "radeon pro" in nm.lower():
                    chosen = (arr[i].iAdapterIndex, nm)
                    break
                if chosen is None and "amd" in nm.lower():
                    chosen = (arr[i].iAdapterIndex, nm)
            if chosen:
                self.adapter_idx, raw_name = chosen
                self.name = raw_name.replace("AMD ", "")[:28]
                self.lib = lib
                self.available = True
        except Exception:
            self.available = False

    def read(self) -> dict:
        data = {"core_mhz": None, "mem_mhz": None, "temp_c": None, "power_w": None, "util_pct": None, "throttle_reasons": ["ADL2 Active"]}
        if not self.available or not self.lib:
            return data
        try:
            fn = getattr(self.lib, "ADL2_New_QueryPMLogData_Get", None)
            if not fn:
                return data
            out = ADLPMLogDataOutput()
            out.size = ctypes.sizeof(out)
            if fn(self.ctx, ctypes.c_int(self.adapter_idx), ctypes.byref(out)) == 0:
                s = out.sensors
                if s[1].supported:
                    data["core_mhz"] = int(s[1].value)
                if s[2].supported:
                    data["mem_mhz"] = int(s[2].value)
                if s[8].supported:
                    data["temp_c"] = int(s[8].value)
                if s[19].supported:
                    data["util_pct"] = int(s[19].value)
                if s[73].supported and s[73].value > 0:
                    data["power_w"] = float(s[73].value)
                elif s[23].supported and s[23].value > 0:
                    data["power_w"] = float(s[23].value)
        except Exception:
            pass
        return data

    def set_clock_lock(self, max_mhz: int) -> tuple[bool, str]:
        return False, "Clock lock requires NVIDIA NVML"

    def get_running_processes(self) -> list[dict]:
        return []

    def shutdown(self):
        if self.available and self.lib:
            try:
                self.lib.ADL2_Main_Control_Destroy(self.ctx)
            except Exception:
                pass
            self.available = False


class UniversalGPUMonitor:
    def __init__(self):
        self.nvml = NVMLBackend()
        self.adl = AMDADLBackend()
        self.all_gpus = self._enumerate_wmi_gpus()
        self.active = self.nvml if self.nvml.available else (self.adl if self.adl.available else None)

    @staticmethod
    def _enumerate_wmi_gpus() -> list[str]:
        names = []
        try:
            cim = win32com.client.GetObject(r"winmgmts:\\.\root\cimv2")
            for g in cim.InstancesOf("Win32_VideoController"):
                nm = str(getattr(g, "Name", "") or "").strip()
                if nm and nm not in names:
                    names.append(nm)
        except Exception:
            pass
        return names

    @property
    def name(self) -> str:
        return self.active.name if self.active else (self.all_gpus[0][:28] if self.all_gpus else "Integrated GPU")

    @property
    def vendor(self) -> str:
        return self.active.vendor if self.active else "Generic"

    def read(self) -> dict:
        if self.active:
            return self.active.read()
        return {"core_mhz": None, "mem_mhz": None, "temp_c": None, "power_w": None, "util_pct": None, "throttle_reasons": []}

    def set_clock_lock(self, max_mhz: int) -> tuple[bool, str]:
        return self.active.set_clock_lock(max_mhz) if self.active else (False, "No supported GPU API")

    def get_running_processes(self) -> list[dict]:
        return self.active.get_running_processes() if self.active else []

    def shutdown(self):
        self.nvml.shutdown()
        self.adl.shutdown()


# =============================================================================
# ACER WMI, DISPLAY, BRIGHTNESS, SERVICES, BATTERY & SQLITE RECORDER
# =============================================================================

class AcerWMIController:
    def __init__(self):
        self.wmi_svc = win32com.client.GetObject(r"winmgmts:\\.\root\wmi")
        self.instance = None
        self.available = False
        self.available_methods: list[str] = []
        self._sim_profile_id = 0x04
        try:
            instances = list(self.wmi_svc.InstancesOf("AcerGamingFunction"))
            if instances:
                self.instance = instances[0]
                self.available = True
                self.available_methods = sorted([str(m.Name) for m in self.instance.Methods_])
        except Exception:
            self.available = False

    def _exec(self, method_name: str, payload: int, param_name: str = "gmInput") -> int:
        if not self.available or not self.instance:
            return 0
        method = self.instance.Methods_(method_name)
        in_params = method.InParameters.SpawnInstance_()
        actual_in = param_name
        try:
            props = [p.Name for p in in_params.Properties_]
            if actual_in not in props and props:
                actual_in = props[0]
        except Exception:
            pass
        try:
            setattr(in_params, actual_in, payload)
        except Exception:
            setattr(in_params, actual_in, str(payload))
        out_params = self.instance.ExecMethod_(method_name, in_params)
        for out_name in ("gmOutput", "uOutput", "ReturnValue"):
            if hasattr(out_params, out_name):
                val = getattr(out_params, out_name)
                if val is not None:
                    return int(val)
        for p in out_params.Properties_:
            if p.Value is not None:
                return int(p.Value)
        return 0

    def get_profile_id(self) -> int:
        if not self.available:
            return self._sim_profile_id
        return (self._exec("GetGamingMiscSetting", 11) >> 8) & 0xFF

    def set_profile(self, name: str) -> int:
        pid, payload = PROFILES[name]
        self._sim_profile_id = pid
        return self._exec("SetGamingMiscSetting", payload) if self.available else 0

    def get_misc_setting(self, index: int) -> int | None:
        if not self.available:
            return None
        try:
            raw = self._exec("GetGamingMiscSetting", index)
            return ((raw >> 8) & 0xFF) if (raw & 0xFF) == 0 else None
        except Exception:
            return None

    def set_misc_setting(self, index: int, value: int) -> int:
        return self._exec("SetGamingMiscSetting", ((value & 0xFF) << 8) | (index & 0xFF)) if self.available else -1

    def set_battery_charge_limit(self, enable_80: bool) -> tuple[bool, str]:
        if not self.available:
            return False, "Acer WMI not present"
        if "SetBatteryHealthControl" in self.available_methods:
            try:
                payload = 0x010101 if enable_80 else 0x000101
                st = self._exec("SetBatteryHealthControl", payload, param_name="uInput")
                return (st & 0xFF) == 0, f"SetBatteryHealthControl({hex(payload)}) -> {hex(st)}"
            except Exception as exc:
                return False, str(exc)
        return False, "SetBatteryHealthControl not exposed on AcerGamingFunction"

    def get_battery_charge_limit(self) -> bool | None:
        if self.available and "GetBatteryHealthControl" in self.available_methods:
            try:
                raw = self._exec("GetBatteryHealthControl", 0x01, param_name="uInput")
                if (raw & 0xFF) == 0:
                    return bool((raw >> 8) & 0x01)
            except Exception:
                return None
        return None

    def set_fan_behavior(self, mode: str) -> int:
        return self._exec("SetGamingFanBehavior", FAN_BEHAVIOR[mode]) if self.available else 0

    def set_fan_speed(self, fan_id: int, percent: int) -> int:
        if not self.available:
            return 0
        return self._exec("SetGamingFanSpeed", (max(0, min(100, int(percent))) << 8) | fan_id)

    def _read_acpi_temp_fallback(self) -> int | None:
        try:
            for tz in self.wmi_svc.InstancesOf("MSAcpi_ThermalZoneTemperature"):
                c = int(round((int(getattr(tz, "CurrentTemperature", 0) or 0) / 10.0) - 273.15))
                if 15 <= c <= 115:
                    return c
        except Exception:
            pass
        return None

    def read_ec_sensors(self) -> dict:
        sensors = {"cpu_temp": None, "gpu_temp": None, "cpu_rpm": None, "gpu_rpm": None}
        if not self.available:
            sensors["cpu_temp"] = self._read_acpi_temp_fallback()
            return sensors
        for cmd, key, is_temp in (
            (SYSINFO_CPU_TEMP, "cpu_temp", True),
            (SYSINFO_GPU_TEMP, "gpu_temp", True),
            (SYSINFO_CPU_RPM, "cpu_rpm", False),
            (SYSINFO_GPU_RPM, "gpu_rpm", False),
        ):
            try:
                raw = self._exec("GetGamingSysInfo", cmd)
                if (raw & 0xFF) == 0:
                    if is_temp:
                        t = (raw >> 8) & 0xFF
                        if 10 <= t <= 120:
                            sensors[key] = t
                    else:
                        sensors[key] = (raw >> 8) & 0x1FFF
            except Exception:
                pass
        if sensors["cpu_temp"] is None:
            sensors["cpu_temp"] = self._read_acpi_temp_fallback()
        return sensors


class DisplayRefreshController:
    @staticmethod
    def get_current_and_supported() -> tuple[int, list[int]]:
        try:
            cur = win32api.EnumDisplaySettings(None, win32con.ENUM_CURRENT_SETTINGS)
            cur_hz = int(cur.DisplayFrequency)
            w, h, bpp = cur.PelsWidth, cur.PelsHeight, cur.BitsPerPel
            rates = {cur_hz}
            idx = 0
            while True:
                try:
                    dm = win32api.EnumDisplaySettings(None, idx)
                    if dm.PelsWidth == w and dm.PelsHeight == h and dm.BitsPerPel == bpp and dm.DisplayFrequency >= 40:
                        rates.add(int(dm.DisplayFrequency))
                    idx += 1
                except pywintypes.error:
                    break
            return cur_hz, sorted(rates)
        except Exception:
            return 60, [60]

    @staticmethod
    def set_refresh_rate(target_hz: int) -> tuple[bool, str]:
        try:
            dm = win32api.EnumDisplaySettings(None, win32con.ENUM_CURRENT_SETTINGS)
            if int(dm.DisplayFrequency) == int(target_hz):
                return True, f"Already at {target_hz} Hz"
            dm.DisplayFrequency = int(target_hz)
            dm.Fields = win32con.DM_DISPLAYFREQUENCY
            res = win32api.ChangeDisplaySettings(dm, 0)
            return (res == win32con.DISP_CHANGE_SUCCESSFUL), f"Display -> {target_hz} Hz (rc={res})"
        except Exception as exc:
            return False, str(exc)


class BrightnessController:
    @staticmethod
    def set_brightness(percent: int) -> bool:
        pct = max(5, min(100, int(percent)))
        try:
            wmi_svc = win32com.client.GetObject(r"winmgmts:\\.\root\wmi")
            for m in wmi_svc.InstancesOf("WmiMonitorBrightnessMethods"):
                m.WmiSetBrightness(1, pct)
                return True
        except Exception:
            pass
        return False


class AcerServiceGuard:
    PATTERNS = ("pssvc", "nssvc", "nitrosense", "predatorsense", "acersense", "acergaming")

    def __init__(self):
        self.paused_services: list[str] = []

    def find_acer_services(self) -> list[tuple[str, str]]:
        found = []
        try:
            scm = win32service.OpenSCManager(None, None, win32service.SC_MANAGER_ENUMERATE_SERVICE)
            try:
                for name, disp, status in win32service.EnumServicesStatus(scm):
                    low = f"{name} {disp}".lower()
                    if any(pat in low for pat in self.PATTERNS):
                        found.append((name, "Running" if status[1] == win32service.SERVICE_RUNNING else "Stopped"))
            finally:
                win32service.CloseServiceHandle(scm)
        except Exception:
            pass
        return found

    def stop_conflicting(self) -> list[str]:
        stopped = []
        for name, state in self.find_acer_services():
            if state == "Running":
                try:
                    scm = win32service.OpenSCManager(None, None, win32service.SC_MANAGER_CONNECT)
                    try:
                        hs = win32service.OpenService(scm, name, win32service.SERVICE_STOP | win32service.SERVICE_QUERY_STATUS)
                        try:
                            win32service.ControlService(hs, win32service.SERVICE_CONTROL_STOP)
                            stopped.append(name)
                            if name not in self.paused_services:
                                self.paused_services.append(name)
                        finally:
                            win32service.CloseServiceHandle(hs)
                    finally:
                        win32service.CloseServiceHandle(scm)
                except Exception:
                    pass
        return stopped

    def restore_paused(self) -> list[str]:
        started = []
        for name in list(self.paused_services):
            try:
                scm = win32service.OpenSCManager(None, None, win32service.SC_MANAGER_CONNECT)
                try:
                    hs = win32service.OpenService(scm, name, win32service.SERVICE_START)
                    try:
                        win32service.StartService(hs, None)
                        started.append(name)
                    finally:
                        win32service.CloseServiceHandle(hs)
                finally:
                    win32service.CloseServiceHandle(scm)
            except Exception:
                pass
        self.paused_services.clear()
        return started


class BatteryDiagnostics:
    def __init__(self):
        self.wmi = None
        self.designed_mwh: int | None = None
        self.full_mwh: int | None = None
        try:
            self.wmi = win32com.client.GetObject(r"winmgmts:\\.\root\wmi")
            self.refresh_static_health()
        except Exception:
            self.wmi = None

    def refresh_static_health(self):
        if not self.wmi:
            return
        try:
            for item in self.wmi.InstancesOf("BatteryStaticData"):
                val = int(getattr(item, "DesignedCapacity", 0) or 0)
                if val > 0:
                    self.designed_mwh = val
                    break
        except Exception:
            pass
        try:
            for item in self.wmi.InstancesOf("BatteryFullChargedCapacity"):
                val = int(getattr(item, "FullChargedCapacity", 0) or 0)
                if val > 0:
                    self.full_mwh = val
                    break
        except Exception:
            pass

    def read(self) -> dict:
        out = {
            "watts": None, "state": "Idle", "voltage_v": None, "remaining_mwh": None,
            "designed_mwh": self.designed_mwh, "full_mwh": self.full_mwh, "wear_pct": None, "eta_str": "--",
        }
        if self.designed_mwh and self.full_mwh:
            out["wear_pct"] = round(max(0.0, (1.0 - (self.full_mwh / self.designed_mwh)) * 100.0), 1)
        if not self.wmi:
            return out
        try:
            for st in self.wmi.InstancesOf("BatteryStatus"):
                dis_mw = int(getattr(st, "DischargeRate", 0) or 0)
                chg_mw = int(getattr(st, "ChargeRate", 0) or 0)
                rem_mwh = int(getattr(st, "RemainingCapacity", 0) or 0)
                volt_mv = int(getattr(st, "Voltage", 0) or 0)
                discharging = bool(getattr(st, "Discharging", False))
                charging = bool(getattr(st, "Charging", False))

                if 0 < volt_mv < 0xFFFFFFFF:
                    out["voltage_v"] = round(volt_mv / 1000.0, 2)
                if 0 < rem_mwh < 0xFFFFFFFF:
                    out["remaining_mwh"] = rem_mwh

                if discharging and 0 < dis_mw < 0xFFFFFFFF:
                    out["watts"] = -round(dis_mw / 1000.0, 1)
                    out["state"] = "Discharging"
                    if out["remaining_mwh"]:
                        total_min = int(round((out["remaining_mwh"] / dis_mw) * 60))
                        out["eta_str"] = f"{total_min // 60}h {total_min % 60:02d}m left"
                elif charging and 0 < chg_mw < 0xFFFFFFFF:
                    out["watts"] = round(chg_mw / 1000.0, 1)
                    out["state"] = "Charging"
                    if out["remaining_mwh"] and self.full_mwh and self.full_mwh > out["remaining_mwh"]:
                        total_min = int(round(((self.full_mwh - out["remaining_mwh"]) / chg_mw) * 60))
                        out["eta_str"] = f"{total_min // 60}h {total_min % 60:02d}m to full"
                else:
                    out["watts"] = 0.0
                    out["state"] = "AC Hold" if bool(getattr(st, "PowerOnline", False)) else "Idle"
                break
        except Exception:
            pass
        return out


class TelemetryRecorder:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.recording = False
        self.session_id: str | None = None
        self.start_ts: float = 0.0
        self.sample_count = 0
        self.wh_consumed = 0.0
        self._last_ts: float | None = None
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS samples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL, ts REAL NOT NULL, mode TEXT, on_ac INTEGER,
                batt_pct INTEGER, batt_w REAL, cpu_temp INTEGER, cpu_mhz INTEGER,
                gpu_temp INTEGER, gpu_mhz INTEGER, gpu_w REAL, cpu_rpm INTEGER, gpu_rpm INTEGER
            )
        """)
        self.conn.commit()

    def start_session(self) -> str:
        self.session_id = datetime.now().strftime("session_%Y%m%d_%H%M%S")
        self.start_ts = time.time()
        self._last_ts = self.start_ts
        self.sample_count = 0
        self.wh_consumed = 0.0
        self.recording = True
        return self.session_id

    def stop_session(self) -> dict:
        self.recording = False
        self.conn.commit()
        return self.get_session_summary(self.session_id)

    def record_sample(self, mode, on_ac, batt_pct, batt_w, cpu_temp, cpu_mhz, gpu_temp, gpu_mhz, gpu_w, cpu_rpm, gpu_rpm):
        if not self.recording or not self.session_id:
            return
        now = time.time()
        if self._last_ts is not None and batt_w is not None and batt_w < 0:
            self.wh_consumed += abs(batt_w) * ((now - self._last_ts) / 3600.0)
        self._last_ts = now
        self.sample_count += 1
        self.conn.execute(
            "INSERT INTO samples (session_id, ts, mode, on_ac, batt_pct, batt_w, cpu_temp, cpu_mhz, gpu_temp, gpu_mhz, gpu_w, cpu_rpm, gpu_rpm) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (self.session_id, now, mode, int(on_ac), batt_pct, batt_w, cpu_temp, cpu_mhz, gpu_temp, gpu_mhz, gpu_w, cpu_rpm, gpu_rpm),
        )
        if self.sample_count % 5 == 0:
            self.conn.commit()

    def get_session_summary(self, session_id: str | None) -> dict:
        if not session_id:
            return {}
        row = self.conn.execute(
            """
            SELECT COUNT(*), MIN(ts), MAX(ts), AVG(cpu_temp), MAX(cpu_temp),
                   AVG(gpu_temp), MAX(gpu_temp), AVG(CASE WHEN batt_w < 0 THEN ABS(batt_w) END),
                   SUM(CASE WHEN cpu_temp >= 85 OR gpu_temp >= 83 THEN 1 ELSE 0 END)
            FROM samples WHERE session_id = ?
            """,
            (session_id,),
        ).fetchone()
        if not row or row[0] == 0:
            return {"samples": 0}
        return {
            "session_id": session_id,
            "samples": row[0],
            "duration_s": max(1, int(row[2] - row[1])),
            "avg_cpu_c": round(row[3], 1) if row[3] is not None else None,
            "peak_cpu_c": int(row[4]) if row[4] is not None else None,
            "avg_gpu_c": round(row[5], 1) if row[5] is not None else None,
            "peak_gpu_c": int(row[6]) if row[6] is not None else None,
            "avg_dis_w": round(row[7], 1) if row[7] is not None else None,
            "wh_used": round(self.wh_consumed, 2),
            "hot_samples": int(row[8] or 0),
        }

    def export_csv(self, session_id: str | None, out_path: str) -> int:
        if not session_id:
            return 0
        rows = self.conn.execute(
            "SELECT ts, mode, on_ac, batt_pct, batt_w, cpu_temp, cpu_mhz, gpu_temp, gpu_mhz, gpu_w, cpu_rpm, gpu_rpm "
            "FROM samples WHERE session_id = ? ORDER BY ts ASC",
            (session_id,),
        ).fetchall()
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "mode", "on_ac", "batt_pct", "batt_w", "cpu_temp", "cpu_mhz", "gpu_temp", "gpu_mhz", "gpu_w", "cpu_rpm", "gpu_rpm"])
            for r in rows:
                writer.writerow([datetime.fromtimestamp(r[0]).isoformat(timespec="seconds"), *r[1:]])
        return len(rows)

    def close(self):
        try:
            self.conn.commit()
            self.conn.close()
        except Exception:
            pass


def apply_windows_dc_tuning(performance: bool):
    boost = "2" if performance else "1"
    cool_policy = "1" if performance else "0"
    pcie_aspm = "0" if performance else "2"
    cmds = [
        ["powercfg", "/setdcvalueindex", "SCHEME_CURRENT", SUB_PROC, GUID_PERFBOOSTMODE, boost],
        ["powercfg", "/setdcvalueindex", "SCHEME_CURRENT", SUB_PROC, GUID_PROCTHROTTLEMAX, "100"],
        ["powercfg", "/setdcvalueindex", "SCHEME_CURRENT", SUB_PROC, GUID_SYSCOOLPOL, cool_policy],
        ["powercfg", "/setdcvalueindex", "SCHEME_CURRENT", SUB_PCIE, GUID_ASPM, pcie_aspm],
        ["powercfg", "/setactive", "SCHEME_CURRENT"],
    ]
    for cmd in cmds:
        subprocess.run(cmd, check=False, creationflags=subprocess.CREATE_NO_WINDOW)


def apply_cpu_freq_and_epp(pcore_mhz: int, ecore_mhz: int, epp_pcore: int, epp_ecore: int, is_hybrid: bool):
    cmds = []
    for target in ("/setdcvalueindex", "/setacvalueindex"):
        if is_hybrid:
            cmds.append(["powercfg", target, "SCHEME_CURRENT", SUB_PROC, GUID_PROCFREQMAX1, str(max(0, int(pcore_mhz)))])
            cmds.append(["powercfg", target, "SCHEME_CURRENT", SUB_PROC, GUID_PROCFREQMAX, str(max(0, int(ecore_mhz)))])
            cmds.append(["powercfg", target, "SCHEME_CURRENT", SUB_PROC, GUID_PERFEPP1, str(max(0, min(100, int(epp_pcore))))])
            cmds.append(["powercfg", target, "SCHEME_CURRENT", SUB_PROC, GUID_PERFEPP, str(max(0, min(100, int(epp_ecore))))])
        else:
            cmds.append(["powercfg", target, "SCHEME_CURRENT", SUB_PROC, GUID_PROCFREQMAX, str(max(0, int(pcore_mhz)))])
            cmds.append(["powercfg", target, "SCHEME_CURRENT", SUB_PROC, GUID_PERFEPP, str(max(0, min(100, int(epp_pcore))))])
    cmds.append(["powercfg", "/setactive", "SCHEME_CURRENT"])
    for cmd in cmds:
        subprocess.run(cmd, check=False, creationflags=subprocess.CREATE_NO_WINDOW)


def make_status_icon(color_hex: str) -> QIcon:
    pix = QPixmap(64, 64)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(color_hex))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(8, 8, 48, 48)
    painter.end()
    return QIcon(pix)


# =============================================================================
# GLOBAL HOTKEYS, NITRO KEY HOOK, OSD TOAST & MINI HUD
# =============================================================================

class GlobalHotkeyFilter(QAbstractNativeEventFilter):
    WM_HOTKEY = 0x0312

    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def nativeEventFilter(self, eventType, message):
        if eventType in (b"windows_generic_MSG", "windows_generic_MSG"):
            try:
                msg = WIN32_MSG.from_address(int(message))
                if msg.message == self.WM_HOTKEY:
                    self.callback(int(msg.wParam))
                    return True, 0
            except Exception:
                pass
        return False, 0


class NitroKeyHook:
    WH_KEYBOARD_LL = 13
    WM_KEYDOWN = 0x0100
    WM_SYSKEYDOWN = 0x0104

    def __init__(self, on_trigger, on_learned):
        self.on_trigger = on_trigger
        self.on_learned = on_learned
        self.hook_id = None
        self._proc_ref = None
        self.target_vk = 255
        self.target_scan = 117
        self.learning = False

    def start(self, vk: int, scan: int):
        self.stop()
        self.target_vk = vk
        self.target_scan = scan

        def _cb(nCode, wParam, lParam):
            if nCode >= 0 and wParam in (self.WM_KEYDOWN, self.WM_SYSKEYDOWN):
                kb = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
                if self.learning:
                    self.learning = False
                    self.target_vk = int(kb.vkCode)
                    self.target_scan = int(kb.scanCode)
                    QTimer.singleShot(0, lambda v=self.target_vk, s=self.target_scan: self.on_learned(v, s))
                    return 1
                if int(kb.vkCode) == self.target_vk and int(kb.scanCode) == self.target_scan:
                    QTimer.singleShot(0, self.on_trigger)
                    return 1
            return user32.CallNextHookEx(self.hook_id, nCode, wParam, lParam)

        self._proc_ref = HOOKPROC(_cb)
        self.hook_id = user32.SetWindowsHookExW(self.WH_KEYBOARD_LL, self._proc_ref, None, 0)

    def stop(self):
        if self.hook_id:
            user32.UnhookWindowsHookEx(self.hook_id)
            self.hook_id = None
            self._proc_ref = None


class ModeToastOverlay(QWidget):
    def __init__(self):
        super().__init__(
            None,
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowTransparentForInput,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedSize(300, 62)

        self.title_txt = "PERFORMANCE"
        self.sub_txt = "ThermalPulse Control Center"
        self.accent = QColor("#ef4444")

        self.fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self.fade_anim.setDuration(300)
        self.fade_anim.finished.connect(self._on_fade_done)

        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self._start_fade_out)

    def show_toast(self, title: str, subtitle: str, accent: QColor):
        self.title_txt = title
        self.sub_txt = subtitle
        self.accent = QColor(accent)
        self.update()
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            self.move(geo.x() + (geo.width() - self.width()) // 2, geo.y() + 44)
        self.fade_anim.stop()
        self.setWindowOpacity(0.96)
        self.show()
        self.hide_timer.start(1750)

    def _start_fade_out(self):
        self.fade_anim.stop()
        self.fade_anim.setStartValue(self.windowOpacity())
        self.fade_anim.setEndValue(0.0)
        self.fade_anim.start()

    def _on_fade_done(self):
        if self.windowOpacity() <= 0.05:
            self.hide()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(1.5, 1.5, self.width() - 3, self.height() - 3)
        p.setBrush(QColor(15, 19, 28, 235))
        border = QColor(self.accent)
        border.setAlpha(200)
        p.setPen(QPen(border, 1.6))
        p.drawRoundedRect(rect, 14, 14)

        p.setBrush(self.accent)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(12, 13, 5, self.height() - 26), 2.5, 2.5)

        p.setPen(QColor("#f8fafc"))
        p.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        p.drawText(QRectF(28, 10, self.width() - 38, 22), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self.title_txt)

        p.setPen(QColor("#94a3b8"))
        p.setFont(QFont("Segoe UI", 9))
        p.drawText(QRectF(28, 33, self.width() - 38, 18), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self.sub_txt)
        p.end()


class MiniHudOverlay(QWidget):
    def __init__(self):
        super().__init__(
            None,
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowTransparentForInput,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedSize(485, 44)
        self.text_line1 = "CPU --°C --MHz  |  GPU --°C --MHz --W"
        self.text_line2 = "FAN --/-- RPM  |  BATT --% --W  |  MODE"
        self.accent = QColor("#ef4444")
        self.corner = "Top-Right"

    def set_corner(self, corner: str):
        self.corner = corner
        screen = QApplication.primaryScreen()
        if not screen:
            return
        geo = screen.availableGeometry()
        m = 14
        if corner == "Top-Left":
            self.move(geo.x() + m, geo.y() + m)
        elif corner == "Bottom-Left":
            self.move(geo.x() + m, geo.y() + geo.height() - self.height() - m)
        elif corner == "Bottom-Right":
            self.move(geo.x() + geo.width() - self.width() - m, geo.y() + geo.height() - self.height() - m)
        else:
            self.move(geo.x() + geo.width() - self.width() - m, geo.y() + m)

    def update_metrics(self, line1: str, line2: str, accent: QColor):
        self.text_line1 = line1
        self.text_line2 = line2
        self.accent = QColor(accent)
        if self.isVisible():
            self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(1, 1, self.width() - 2, self.height() - 2)
        p.setBrush(QColor(11, 14, 20, 210))
        border = QColor(self.accent)
        border.setAlpha(185)
        p.setPen(QPen(border, 1.3))
        p.drawRoundedRect(rect, 10, 10)

        p.setBrush(self.accent)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(7, 8, 4, self.height() - 16), 2, 2)

        p.setPen(QColor("#f8fafc"))
        p.setFont(QFont("Consolas", 9.5, QFont.Weight.Bold))
        p.drawText(QRectF(18, 4, self.width() - 24, 18), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self.text_line1)

        p.setPen(QColor("#94a3b8"))
        p.setFont(QFont("Consolas", 8.5))
        p.drawText(QRectF(18, 22, self.width() - 24, 18), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self.text_line2)
        p.end()


# =============================================================================
# ANIMATED CUSTOM UI WIDGETS
# =============================================================================

class ModeHeroBanner(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(118)
        self.mode = "Performance"
        self.power_badge = "BATTERY • --%"
        self.watt_badge = "-- W"
        self.ec_hex = "EC 0x0400"
        self.fan_badge = "FANS: AUTO"
        self.phase = 0.0
        self.cur_primary = QColor(MODE_THEME[self.mode]["color"])
        self.cur_secondary = QColor(MODE_THEME[self.mode]["secondary"])

        rng = random.Random(42)
        self.eco_motes = [
            [rng.uniform(0.05, 0.95), rng.uniform(0.0, 1.0), rng.uniform(0.002, 0.005), rng.uniform(2.0, 5.0)]
            for _ in range(16)
        ]
        self.perf_streaks = [
            [rng.uniform(0.0, 1.0), rng.uniform(0.1, 0.9), rng.uniform(0.015, 0.035), rng.uniform(24, 68)]
            for _ in range(14)
        ]

    def set_mode(self, mode: str, ec_hex: str):
        if mode in MODE_THEME:
            self.mode = mode
        self.ec_hex = ec_hex

    def set_badges(self, power_badge: str, watt_badge: str, fan_badge: str):
        self.power_badge = power_badge
        self.watt_badge = watt_badge
        self.fan_badge = fan_badge

    def advance_frame(self):
        self.cur_primary = lerp_color(self.cur_primary, MODE_THEME[self.mode]["color"], 0.12)
        self.cur_secondary = lerp_color(self.cur_secondary, MODE_THEME[self.mode]["secondary"], 0.12)
        self.phase += {"Eco": 0.035, "Quiet": 0.045, "Balanced": 0.06, "Performance": 0.13}.get(self.mode, 0.05)

        if self.mode == "Eco":
            for m in self.eco_motes:
                m[1] -= m[2]
                if m[1] < -0.1:
                    m[1] = 1.1
        elif self.mode == "Performance":
            for s in self.perf_streaks:
                s[0] += s[2]
                if s[0] > 1.2:
                    s[0] = -0.2
        self.update()

    def paintEvent(self, event):
        w, h = self.width(), self.height()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(1, 1, w - 2, h - 2)
        clip = QPainterPath()
        clip.addRoundedRect(rect, 14, 14)
        p.setClipPath(clip)

        bg = QLinearGradient(0, 0, w, h)
        bg.setColorAt(0.0, QColor("#141821"))
        bg.setColorAt(1.0, QColor("#0d1016"))
        p.fillRect(rect, bg)

        cx, cy = 66.0, h / 2.0
        glow = QRadialGradient(cx, cy, max(w * 0.55, 160.0))
        c_glow = QColor(self.cur_primary)
        c_glow.setAlpha(68 if self.mode == "Performance" else 52)
        glow.setColorAt(0.0, c_glow)
        c_mid = QColor(self.cur_secondary)
        c_mid.setAlpha(18)
        glow.setColorAt(0.45, c_mid)
        glow.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.fillRect(rect, glow)

        if self.mode == "Eco":
            self._paint_eco(p, w, h, cx, cy)
        elif self.mode == "Quiet":
            self._paint_quiet(p, w, h, cx, cy)
        elif self.mode == "Balanced":
            self._paint_balanced(p, w, h, cx, cy)
        else:
            self._paint_performance(p, w, h, cx, cy)

        tx = 128
        p.setPen(QColor("#f8fafc"))
        p.setFont(QFont("Segoe UI", 17, QFont.Weight.Bold))
        p.drawText(QRectF(tx, 12, w - tx - 16, 30), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self.mode.upper())

        p.setPen(QColor("#94a3b8"))
        p.setFont(QFont("Segoe UI", 9.5))
        p.drawText(QRectF(tx, 43, w - tx - 16, 20), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, MODE_THEME[self.mode]["tagline"])

        px = tx
        for text, col in (
            (self.power_badge, self.cur_primary),
            (self.watt_badge, QColor("#f59e0b")),
            (self.ec_hex, QColor("#475569")),
            (self.fan_badge, QColor("#475569")),
        ):
            px += self._draw_pill(p, px, 75, text, col) + 7

        p.setClipping(False)
        border_col = QColor(self.cur_primary)
        border_col.setAlpha(155)
        p.setPen(QPen(border_col, 1.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(rect, 14, 14)
        p.end()

    def _draw_pill(self, p: QPainter, x: int, y: int, text: str, accent: QColor) -> int:
        p.setFont(QFont("Segoe UI", 8.5, QFont.Weight.DemiBold))
        pw = p.fontMetrics().horizontalAdvance(text) + 16
        ph = 23
        pill_rect = QRectF(x, y, pw, ph)
        bg = QColor(accent)
        bg.setAlpha(35)
        border = QColor(accent)
        border.setAlpha(115)
        p.setBrush(bg)
        p.setPen(QPen(border, 1.0))
        p.drawRoundedRect(pill_rect, 11.5, 11.5)
        p.setPen(QColor("#e2e8f0"))
        p.drawText(pill_rect, Qt.AlignmentFlag.AlignCenter, text)
        return pw

    def _paint_eco(self, p: QPainter, w: int, h: int, cx: float, cy: float):
        for mx, my, _, r in self.eco_motes:
            col = QColor(self.cur_secondary)
            col.setAlpha(int(45 + 55 * (1.0 - abs(my - 0.5) * 2)))
            p.setBrush(col)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(mx * w, my * h), r, r)
        for i in range(3):
            prog = (self.phase * 0.25 + i * 0.33) % 1.0
            c = QColor(self.cur_primary)
            c.setAlpha(int((1.0 - prog) * 180))
            p.setPen(QPen(c, 2.0))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPointF(cx, cy), 18 + prog * 34, 18 + prog * 34)
        leaf = QPainterPath()
        leaf.moveTo(cx - 12, cy + 12)
        leaf.cubicTo(cx - 18, cy - 10, cx + 6, cy - 20, cx + 15, cy - 14)
        leaf.cubicTo(cx + 16, cy + 4, cx + 2, cy + 18, cx - 12, cy + 12)
        fill = QColor(self.cur_primary)
        fill.setAlpha(210)
        p.setBrush(fill)
        p.setPen(QPen(self.cur_secondary, 1.5))
        p.drawPath(leaf)

    def _paint_quiet(self, p: QPainter, w: int, h: int, cx: float, cy: float):
        for layer in range(3):
            path = QPainterPath()
            amp = 6.5 + layer * 4.0
            freq = 0.018 - layer * 0.003
            y_base = h * 0.72 + layer * 6
            for x in range(0, w + 8, 8):
                y = y_base + math.sin(x * freq + self.phase + layer * 1.4) * amp
                path.moveTo(x, y) if x == 0 else path.lineTo(x, y)
            col = QColor(self.cur_primary if layer == 0 else self.cur_secondary)
            col.setAlpha(95 - layer * 24)
            p.setPen(QPen(col, 2.0 - layer * 0.3))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(path)
        pulse = 25 + math.sin(self.phase) * 3.0
        c = QColor(self.cur_primary)
        c.setAlpha(150)
        p.setPen(QPen(c, 2.2))
        p.drawEllipse(QPointF(cx, cy), pulse, pulse)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(self.cur_secondary)
        for idx, offset in enumerate((-11, 0, 11)):
            bh = 10 + abs(math.sin(self.phase * 0.8 + idx * 1.1)) * 12
            p.drawRoundedRect(QRectF(cx + offset - 3, cy - bh / 2, 6, bh), 3, 3)

    def _paint_balanced(self, p: QPainter, w: int, h: int, cx: float, cy: float):
        deg1 = (self.phase * 48) % 360
        deg2 = (-self.phase * 34) % 360
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(self.cur_primary, 3.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawArc(QRectF(cx - 33, cy - 33, 66, 66), int(deg1 * 16), 110 * 16)
        p.drawArc(QRectF(cx - 33, cy - 33, 66, 66), int((deg1 + 180) * 16), 110 * 16)
        p.setPen(QPen(self.cur_secondary, 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawArc(QRectF(cx - 21, cy - 21, 42, 42), int(deg2 * 16), 140 * 16)
        rad = math.radians(-deg1)
        p.setBrush(QColor("#e0e7ff"))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(cx + math.cos(rad) * 33, cy + math.sin(rad) * 33), 3.6, 3.6)
        p.setBrush(self.cur_primary)
        p.drawEllipse(QPointF(cx, cy), 8.0, 8.0)

    def _paint_performance(self, p: QPainter, w: int, h: int, cx: float, cy: float):
        for sx, sy, _, length in self.perf_streaks:
            x1, y1 = sx * w, sy * h
            grad = QLinearGradient(x1 - length, y1, x1, y1)
            grad.setColorAt(0.0, QColor(239, 68, 68, 0))
            grad.setColorAt(1.0, QColor(249, 115, 22, 115))
            p.setPen(QPen(grad, 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(QPointF(x1 - length, y1), QPointF(x1, y1))
        deg_fast = (self.phase * 115) % 360
        deg_rev = (-self.phase * 75) % 360
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(self.cur_primary, 3.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        for i in range(3):
            p.drawArc(QRectF(cx - 35, cy - 35, 70, 70), int((deg_fast + i * 120) * 16), 70 * 16)
        p.setPen(QPen(self.cur_secondary, 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        for i in range(2):
            p.drawArc(QRectF(cx - 23, cy - 23, 46, 46), int((deg_rev + i * 180) * 16), 115 * 16)
        pulse = 12 + math.sin(self.phase * 2.2) * 2.4
        core_col = QColor(self.cur_primary)
        core_col.setAlpha(200)
        p.setBrush(core_col)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(cx, cy), pulse, pulse)
        bolt = QPainterPath()
        bolt.moveTo(cx + 2, cy - 10)
        bolt.lineTo(cx - 7, cy + 1)
        bolt.lineTo(cx - 1, cy + 1)
        bolt.lineTo(cx - 3, cy + 10)
        bolt.lineTo(cx + 7, cy - 1)
        bolt.lineTo(cx + 1, cy - 1)
        bolt.closeSubpath()
        p.setBrush(QColor("#fff7ed"))
        p.drawPath(bolt)


class AnimatedModeBar(QWidget):
    def __init__(self, on_select, parent=None):
        super().__init__(parent)
        self.on_select = on_select
        self.active_index = MODE_ORDER.index("Performance")
        self._pill_x = 0.0
        self._pill_color = QColor(MODE_THEME["Performance"]["color"])
        self.setFixedHeight(42)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(0)

        self.buttons: list[QPushButton] = []
        for idx, name in enumerate(MODE_ORDER):
            btn = QPushButton(name)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, i=idx, n=name: self._clicked(i, n))
            layout.addWidget(btn)
            self.buttons.append(btn)

        self.anim = QPropertyAnimation(self, b"pillX")
        self.anim.setDuration(250)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.set_active_mode("Performance", animate=False)

    def get_pill_x(self) -> float:
        return self._pill_x

    def set_pill_x(self, val: float):
        self._pill_x = val
        self.update()

    pillX = Property(float, get_pill_x, set_pill_x)

    def _slot_width(self) -> float:
        return max(1.0, (self.width() - 8) / len(MODE_ORDER))

    def _clicked(self, idx: int, name: str):
        self.set_active_mode(name, animate=True)
        self.on_select(name)

    def set_active_mode(self, name: str, animate: bool = True):
        if name not in MODE_ORDER:
            return
        idx = MODE_ORDER.index(name)
        self.active_index = idx
        self._pill_color = QColor(MODE_THEME[name]["color"])
        target_x = 4.0 + idx * self._slot_width()
        for i, b in enumerate(self.buttons):
            b.setStyleSheet(
                f"QPushButton {{ background: transparent; border: none; color: {'#ffffff' if i == idx else '#94a3b8'}; "
                "font-weight: 700; font-size: 13px; padding: 6px; } QPushButton:hover { color: #ffffff; }"
            )
        if animate and self.width() > 20:
            self.anim.stop()
            self.anim.setStartValue(self._pill_x)
            self.anim.setEndValue(target_x)
            self.anim.start()
        else:
            self._pill_x = target_x
            self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._pill_x = 4.0 + self.active_index * self._slot_width()
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor("#161a23"))
        p.setPen(QPen(QColor("#262d3d"), 1.0))
        p.drawRoundedRect(QRectF(0.5, 0.5, self.width() - 1, self.height() - 1), 12, 12)

        sw = self._slot_width()
        pill_rect = QRectF(self._pill_x, 4, sw, self.height() - 8)
        grad = QLinearGradient(pill_rect.topLeft(), pill_rect.bottomRight())
        c1 = QColor(self._pill_color)
        c1.setAlpha(225)
        c2 = QColor(self._pill_color).darker(125)
        c2.setAlpha(235)
        grad.setColorAt(0.0, c1)
        grad.setColorAt(1.0, c2)
        p.setBrush(grad)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(pill_rect, 9, 9)
        p.end()


class ArcGaugeWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(84, 84)
        self.target_temp: float | None = None
        self.display_temp: float = 0.0

    def set_temp(self, temp_c: int | None):
        self.target_temp = float(temp_c) if temp_c is not None else None

    def tick_ease(self):
        if self.target_temp is not None:
            diff = self.target_temp - self.display_temp
            if abs(diff) > 0.15:
                self.display_temp += diff * 0.15
                self.update()
        else:
            self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(9, 9, self.width() - 18, self.height() - 18)
        p.setPen(QPen(QColor("#252c3b"), 6.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawArc(rect, 210 * 16, -240 * 16)
        if self.target_temp is not None:
            ratio = max(0.0, min(1.0, self.display_temp / 100.0))
            p.setPen(QPen(temp_to_color(self.display_temp), 6.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawArc(rect, 210 * 16, int(-240 * ratio * 16))
            text, col = f"{int(round(self.display_temp))}°", QColor("#f8fafc")
        else:
            text, col = "--°", QColor("#64748b")
        p.setPen(col)
        p.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        p.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
        p.setFont(QFont("Segoe UI", 7.5, QFont.Weight.DemiBold))
        p.setPen(QColor("#64748b"))
        p.drawText(QRectF(0, self.height() - 18, self.width(), 14), Qt.AlignmentFlag.AlignCenter, "TEMP")
        p.end()


class SparklineWidget(QWidget):
    def __init__(self, accent_hex: str, min_val: float = 30.0, max_val: float = 100.0, height: int = 34, parent=None):
        super().__init__(parent)
        self.setFixedHeight(height)
        self.accent = QColor(accent_hex)
        self.min_val = min_val
        self.max_val = max_val
        self.history: deque[float] = deque(maxlen=60)

    def push(self, val: float | None):
        if val is not None:
            self.history.append(float(val))
            self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.setBrush(QColor("#0e121a"))
        p.setPen(QPen(QColor("#1e2636"), 1.0))
        p.drawRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), 6, 6)
        if len(self.history) < 2:
            p.end()
            return
        vals = list(self.history)
        span = max(1.0, self.max_val - self.min_val)
        step_x = (w - 8) / max(1, (self.history.maxlen - 1))
        start_x = (w - 4) - (len(vals) - 1) * step_x
        line_path, fill_path = QPainterPath(), QPainterPath()
        for i, v in enumerate(vals):
            clamped = max(self.min_val, min(self.max_val, v))
            nx = start_x + i * step_x
            ny = (h - 4) - ((clamped - self.min_val) / span) * (h - 8)
            if i == 0:
                line_path.moveTo(nx, ny)
                fill_path.moveTo(nx, h - 3)
                fill_path.lineTo(nx, ny)
            else:
                line_path.lineTo(nx, ny)
                fill_path.lineTo(nx, ny)
        fill_path.lineTo(start_x + (len(vals) - 1) * step_x, h - 3)
        fill_path.closeSubpath()
        grad = QLinearGradient(0, 0, 0, h)
        c_top = QColor(self.accent)
        c_top.setAlpha(75)
        c_bot = QColor(self.accent)
        c_bot.setAlpha(0)
        grad.setColorAt(0.0, c_top)
        grad.setColorAt(1.0, c_bot)
        p.fillPath(fill_path, grad)
        p.setPen(QPen(self.accent, 1.6))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(line_path)
        p.end()


class TelemetryGaugeCard(QFrame):
    def __init__(self, title: str, subtitle: str, spark_color: str, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 9, 10, 9)
        outer.setSpacing(6)

        row = QHBoxLayout()
        row.setSpacing(10)
        self.gauge = ArcGaugeWidget()
        row.addWidget(self.gauge)

        info = QVBoxLayout()
        info.setSpacing(2)
        self.lbl_title = QLabel(f"{title}  •  {subtitle}")
        self.lbl_title.setObjectName("sectionTitle")
        self.lbl_clock = QLabel("-- MHz")
        self.lbl_clock.setStyleSheet("font-size: 17px; font-weight: 700; color: #f8fafc;")
        self.lbl_line1 = QLabel("--")
        self.lbl_line1.setObjectName("metricSub")
        self.lbl_line2 = QLabel("Fan: -- RPM")
        self.lbl_line2.setObjectName("metricSub")
        self.lbl_badge = QLabel("")
        self.lbl_badge.setStyleSheet("font-size: 10.5px; font-weight: 700; color: #fbbf24;")

        info.addWidget(self.lbl_title)
        info.addWidget(self.lbl_clock)
        info.addWidget(self.lbl_line1)
        info.addWidget(self.lbl_line2)
        info.addWidget(self.lbl_badge)
        row.addLayout(info, 1)

        outer.addLayout(row)
        self.spark = SparklineWidget(spark_color, 30.0, 100.0)
        outer.addWidget(self.spark)


class FanCurveEditor(QWidget):
    MIN_T, MAX_T = 30, 100
    MIN_S, MAX_S = 20, 100

    def __init__(self, points: list[list[int]], accent_hex: str, on_change, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(180)
        self.points = [list(pt) for pt in points]
        self.accent = QColor(accent_hex)
        self.on_change = on_change
        self.live_temp: float | None = None
        self.drag_idx: int | None = None
        self.setMouseTracking(True)

    def set_curve(self, points: list[list[int]], accent_hex: str):
        self.points = [list(pt) for pt in points]
        self.accent = QColor(accent_hex)
        self.update()

    def set_live_temp(self, temp_c: float | None):
        self.live_temp = float(temp_c) if temp_c is not None else None
        self.update()

    def _plot_rect(self) -> QRectF:
        return QRectF(42, 14, max(40, self.width() - 58), max(40, self.height() - 40))

    def _data_to_px(self, temp: float, speed: float) -> QPointF:
        r = self._plot_rect()
        tx = (temp - self.MIN_T) / (self.MAX_T - self.MIN_T)
        ty = (speed - self.MIN_S) / (self.MAX_S - self.MIN_S)
        return QPointF(r.left() + tx * r.width(), r.bottom() - ty * r.height())

    def _px_to_data(self, pos: QPointF) -> tuple[int, int]:
        r = self._plot_rect()
        tx = max(0.0, min(1.0, (pos.x() - r.left()) / max(1.0, r.width())))
        ty = max(0.0, min(1.0, (r.bottom() - pos.y()) / max(1.0, r.height())))
        return int(round(self.MIN_T + tx * (self.MAX_T - self.MIN_T))), int(round(self.MIN_S + ty * (self.MAX_S - self.MIN_S)))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position()
            for idx, (t, s) in enumerate(self.points):
                pt = self._data_to_px(t, s)
                if math.hypot(pos.x() - pt.x(), pos.y() - pt.y()) <= 13:
                    self.drag_idx = idx
                    return

    def mouseMoveEvent(self, event):
        if self.drag_idx is None:
            return
        temp, speed = self._px_to_data(event.position())
        min_t = self.MIN_T if self.drag_idx == 0 else self.points[self.drag_idx - 1][0] + 4
        max_t = self.MAX_T if self.drag_idx == len(self.points) - 1 else self.points[self.drag_idx + 1][0] - 4
        self.points[self.drag_idx] = [max(min_t, min(max_t, temp)), max(self.MIN_S, min(self.MAX_S, speed))]
        self.update()

    def mouseReleaseEvent(self, event):
        if self.drag_idx is not None:
            self.drag_idx = None
            self.on_change([list(pt) for pt in self.points])

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self._plot_rect()
        p.setBrush(QColor("#0d1118"))
        p.setPen(QPen(QColor("#232b3b"), 1.0))
        p.drawRoundedRect(QRectF(0.5, 0.5, self.width() - 1, self.height() - 1), 10, 10)

        p.setFont(QFont("Segoe UI", 8))
        for s in (20, 40, 60, 80, 100):
            y = self._data_to_px(self.MIN_T, s).y()
            p.setPen(QPen(QColor("#1e2534"), 1.0, Qt.PenStyle.DashLine))
            p.drawLine(QPointF(r.left(), y), QPointF(r.right(), y))
            p.setPen(QColor("#64748b"))
            p.drawText(QRectF(4, y - 8, 34, 16), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, f"{s}%")
        for t in (30, 50, 70, 90, 100):
            x = self._data_to_px(t, self.MIN_S).x()
            p.setPen(QPen(QColor("#1e2534"), 1.0, Qt.PenStyle.DashLine))
            p.drawLine(QPointF(x, r.top()), QPointF(x, r.bottom()))
            p.setPen(QColor("#64748b"))
            p.drawText(QRectF(x - 16, r.bottom() + 4, 32, 16), Qt.AlignmentFlag.AlignCenter, f"{t}°")

        line, fill = QPainterPath(), QPainterPath()
        first_pt = self._data_to_px(self.MIN_T, self.points[0][1])
        line.moveTo(first_pt)
        fill.moveTo(r.left(), r.bottom())
        fill.lineTo(first_pt)
        for t, s in self.points:
            pt = self._data_to_px(t, s)
            line.lineTo(pt)
            fill.lineTo(pt)
        last_pt = self._data_to_px(self.MAX_T, self.points[-1][1])
        line.lineTo(last_pt)
        fill.lineTo(last_pt)
        fill.lineTo(r.right(), r.bottom())
        fill.closeSubpath()

        grad = QLinearGradient(0, r.top(), 0, r.bottom())
        c1, c2 = QColor(self.accent), QColor(self.accent)
        c1.setAlpha(65)
        c2.setAlpha(0)
        grad.setColorAt(0.0, c1)
        grad.setColorAt(1.0, c2)
        p.fillPath(fill, grad)
        p.setPen(QPen(self.accent, 2.2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(line)

        if self.live_temp is not None:
            lt = max(self.MIN_T, min(self.MAX_T, self.live_temp))
            ls = eval_fan_curve(self.points, lt)
            lpt = self._data_to_px(lt, ls)
            p.setPen(QPen(QColor("#f59e0b"), 1.4, Qt.PenStyle.DotLine))
            p.drawLine(QPointF(lpt.x(), r.top()), QPointF(lpt.x(), r.bottom()))
            p.setBrush(QColor("#f59e0b"))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(lpt, 4.5, 4.5)
            p.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            p.setPen(QColor("#fbbf24"))
            p.drawText(QRectF(lpt.x() - 36, r.top() + 2, 72, 16), Qt.AlignmentFlag.AlignCenter, f"{int(lt)}°→{ls}%")

        for idx, (t, s) in enumerate(self.points):
            pt = self._data_to_px(t, s)
            active = idx == self.drag_idx
            p.setBrush(QColor("#ffffff") if active else self.accent)
            p.setPen(QPen(QColor("#0b0e14"), 2.0))
            p.drawEllipse(pt, 7.0 if active else 5.8, 7.0 if active else 5.8)
            if active:
                p.setPen(QColor("#f8fafc"))
                p.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
                p.drawText(QRectF(pt.x() - 28, pt.y() - 22, 56, 15), Qt.AlignmentFlag.AlignCenter, f"{t}°C / {s}%")
        p.end()


# =============================================================================
# MAIN APPLICATION WINDOW
# =============================================================================

class NitroDCUnlockApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ThermalPulse Control Center")
        self.setMinimumWidth(740)

        self.cfg = load_config()
        self.wmi = AcerWMIController()
        self.cpu_mon = UniversalCPUMonitor()
        self.gpu_mon = UniversalGPUMonitor()
        self.batt_diag = BatteryDiagnostics()
        self.svc_guard = AcerServiceGuard()
        self.recorder = TelemetryRecorder(TELEMETRY_DB_PATH)
        self.cur_hz, self.supported_hz = DisplayRefreshController.get_current_and_supported()

        self.safety_tripped = False
        self.last_dc_tuning_state = None
        self.fan_mode = self.cfg["fan_mode"]
        self.current_mode_name = "Performance"
        self.active_curve_target = "CPU"

        # Hysteresis, CoolBoost & App-Profile state
        self._curve_eval_cpu_t: float | None = None
        self._curve_eval_gpu_t: float | None = None
        self._last_sent_cpu_pct: int | None = None
        self._last_sent_gpu_pct: int | None = None
        self._coolboost_active = False
        self._coolboost_start_ts = 0.0
        self._coolboost_prev_fan_mode = "Auto"
        self._app_override_active = False
        self._pre_app_mode = "Balanced"
        self._pre_app_fan_mode = "Auto"
        self._boosted_pids: set[int] = set()
        self._last_applied_brightness_mode: str | None = None
        self._tick_counter = 0

        self.toast = ModeToastOverlay()
        self.hud = MiniHudOverlay()
        self.hud.set_corner(self.cfg["hud_corner"])
        self.hotkey_filter: GlobalHotkeyFilter | None = None
        self._registered_hotkeys: list[int] = []
        self.nitro_hook = NitroKeyHook(self._on_nitro_key_pressed, self._on_nitro_key_learned)

        self.fan_apply_timer = QTimer(self)
        self.fan_apply_timer.setSingleShot(True)
        self.fan_apply_timer.timeout.connect(self._commit_manual_fan_speeds)

        self._build_ui()
        self._build_tray()
        self._setup_hotkeys()

        if self.cfg["nitro_key_hijack"]:
            self.nitro_hook.start(int(self.cfg["nitro_key_vk"]), int(self.cfg["nitro_key_scan"]))
        if self.cfg["acer_service_guard"]:
            stopped = self.svc_guard.stop_conflicting()
            if stopped:
                self.log(f"Service Guard paused conflicting services: {', '.join(stopped)}")
        if self.cfg["hud_visible"]:
            self.hud.show()

        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._tick_animations)
        self.anim_timer.start(20)

        self.hw_timer = QTimer(self)
        self.hw_timer.timeout.connect(self.tick_watchdog)
        self.hw_timer.start(1500)

        self._apply_saved_startup_fan_mode()
        self.log(f"Detected CPU: {self.cpu_mon.short_name} ({self.cpu_mon.family_tag})")
        self.log(f"Detected GPU: {self.gpu_mon.name} ({self.gpu_mon.vendor}) | Acer WMI: {'Active' if self.wmi.available else 'Fallback'}")
        self.tick_watchdog()

    def _build_ui(self):
        self.setStyleSheet("""
            QMainWindow, QWidget { background-color: #0b0e14; color: #e2e8f0; font-family: 'Segoe UI'; font-size: 13px; }
            QFrame#card { background-color: #131720; border: 1px solid #222938; border-radius: 12px; }
            QLabel#sectionTitle { font-size: 11px; font-weight: 700; color: #94a3b8; letter-spacing: 0.7px; }
            QLabel#metricSub { font-size: 12px; color: #94a3b8; }
            QPushButton { background-color: #1c2230; border: 1px solid #2d3648; border-radius: 8px; padding: 6px 11px; font-weight: 600; color: #e2e8f0; }
            QPushButton:hover { background-color: #273044; }
            QPushButton#activeBtn { background-color: #2563eb; border-color: #3b82f6; color: #ffffff; }
            QPushButton#dangerBtn { background-color: #991b1b; border-color: #dc2626; color: #ffffff; }
            QPushButton#coolBtn { background-color: #0e7490; border-color: #06b6d4; color: #ffffff; }
            QTabWidget::pane { border: 1px solid #222938; border-radius: 12px; background: #0e1118; padding: 6px; }
            QTabBar::tab { background: #131720; color: #94a3b8; border: 1px solid #222938; padding: 7px 13px; margin-right: 4px; border-top-left-radius: 8px; border-top-right-radius: 8px; font-weight: 600; }
            QTabBar::tab:selected { background: #1e2636; color: #ffffff; border-bottom-color: #ef4444; }
            QSlider::groove:horizontal { height: 6px; background: #222938; border-radius: 3px; }
            QSlider::handle:horizontal { width: 16px; height: 16px; margin: -5px 0; border-radius: 8px; background: #f8fafc; border: 2px solid #ef4444; }
            QSlider::sub-page:horizontal { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #dc2626, stop:1 #f97316); border-radius: 3px; }
            QCheckBox { spacing: 8px; color: #cbd5e1; }
            QCheckBox::indicator { width: 16px; height: 16px; border-radius: 4px; border: 1px solid #3b465c; background: #161b26; }
            QCheckBox::indicator:checked { background: #ef4444; border-color: #ef4444; }
            QSpinBox, QComboBox, QLineEdit { background: #161b26; border: 1px solid #2d3648; border-radius: 6px; padding: 4px 8px; color: #f8fafc; }
            QListWidget, QTableWidget { background: #0d1118; border: 1px solid #222938; border-radius: 8px; color: #cbd5e1; gridline-color: #1c2230; }
            QHeaderView::section { background: #161b26; color: #94a3b8; border: none; padding: 5px; font-weight: 700; font-size: 11px; }
            QPlainTextEdit { background-color: #090b10; border: 1px solid #1e2433; border-radius: 8px; font-family: Consolas; font-size: 11px; color: #94a3b8; }
        """)

        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        self.hero = ModeHeroBanner()
        layout.addWidget(self.hero)

        self.mode_bar = AnimatedModeBar(self.manual_set_profile)
        layout.addWidget(self.mode_bar)

        # Build Session/Log tab early so self.log_box exists before other tabs sync
        self.log_box = QPlainTextEdit()
        self.log_box.setReadOnly(True)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_dashboard_tab(), "Dashboard")
        self.tabs.addTab(self._build_fans_tab(), "Fans & Curves")
        self.tabs.addTab(self._build_tuning_gpu_tab(), "CPU / GPU Tuning")
        self.tabs.addTab(self._build_automation_tab(), "Automation")
        self.tabs.addTab(self._build_session_log_tab(), "Analytics & Log")
        self.tabs.addTab(self._build_hardware_tab(), "Hardware")
        self.tabs.addTab(self._build_help_tab(), "Help & About")
        layout.addWidget(self.tabs, 1)

        footer = QHBoxLayout()
        lbl_f = QLabel("Hotkeys: Ctrl+Alt+1..4 Modes • Ctrl+Alt+H Mini HUD • Auto-Saved")
        lbl_f.setObjectName("metricSub")
        btn_hide = QPushButton("Minimize to Tray")
        btn_hide.clicked.connect(self.hide)
        btn_quit = QPushButton("Exit App")
        btn_quit.clicked.connect(self.quit_app)
        footer.addWidget(lbl_f)
        footer.addStretch()
        footer.addWidget(btn_hide)
        footer.addWidget(btn_quit)
        layout.addLayout(footer)

        self.setCentralWidget(root)

    def _make_stat_box(self, parent_layout: QHBoxLayout, label: str, value: str) -> QLabel:
        box = QFrame()
        box.setStyleSheet("QFrame { background: #0e121a; border: 1px solid #1f2737; border-radius: 8px; }")
        v = QVBoxLayout(box)
        v.setContentsMargins(10, 7, 10, 7)
        v.setSpacing(2)
        l1 = QLabel(label)
        l1.setStyleSheet("font-size: 10px; font-weight: 700; color: #64748b; border: none;")
        l2 = QLabel(value)
        l2.setStyleSheet("font-size: 13.5px; font-weight: 700; color: #f8fafc; border: none;")
        v.addWidget(l1)
        v.addWidget(l2)
        parent_layout.addWidget(box, 1)
        return l2

    # --- TAB 1: DASHBOARD ---
    def _build_dashboard_tab(self) -> QWidget:
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setSpacing(10)

        telem_row = QHBoxLayout()
        telem_row.setSpacing(10)
        self.cpu_card = TelemetryGaugeCard("CPU", self.cpu_mon.short_name, "#38bdf8")
        self.gpu_card = TelemetryGaugeCard("GPU", self.gpu_mon.name, "#ef4444")
        telem_row.addWidget(self.cpu_card)
        telem_row.addWidget(self.gpu_card)
        lay.addLayout(telem_row)

        # Battery Health + Live Wattage Sparkline Card
        batt_card = QFrame()
        batt_card.setObjectName("card")
        b_lay = QVBoxLayout(batt_card)
        b_lay.setContentsMargins(12, 10, 12, 10)
        b_lay.setSpacing(8)

        hdr = QHBoxLayout()
        lbl_b = QLabel("BATTERY HEALTH & LIVE POWER DRAW (WATTS)")
        lbl_b.setObjectName("sectionTitle")
        hdr.addWidget(lbl_b)
        hdr.addStretch()
        self.chk_batt_80_dash = QCheckBox("80% Charge Limit")
        self.chk_batt_80_dash.clicked.connect(self._on_battery_limit_clicked)
        hdr.addWidget(self.chk_batt_80_dash)
        b_lay.addLayout(hdr)

        stats_row = QHBoxLayout()
        self.lbl_batt_watts = self._make_stat_box(stats_row, "LIVE POWER", "-- W")
        self.lbl_batt_eta = self._make_stat_box(stats_row, "ESTIMATED TIME", "--")
        self.lbl_batt_wear = self._make_stat_box(stats_row, "BATTERY WEAR", "--%")
        self.lbl_batt_cap = self._make_stat_box(stats_row, "CAPACITY / VOLT", "--")
        b_lay.addLayout(stats_row)

        self.batt_spark = SparklineWidget("#f59e0b", 0.0, 90.0, height=30)
        b_lay.addWidget(self.batt_spark)
        lay.addWidget(batt_card)

        # Quick Actions Bar
        quick_row = QHBoxLayout()
        self.btn_coolboost_dash = QPushButton("CoolBoost Cooldown (Max -> 50°C)")
        self.btn_coolboost_dash.setObjectName("coolBtn")
        self.btn_coolboost_dash.clicked.connect(self.toggle_coolboost)
        self.btn_hud_dash = QPushButton("Toggle Mini HUD (Ctrl+Alt+H)")
        self.btn_hud_dash.clicked.connect(self.toggle_hud)
        self.btn_rec_dash = QPushButton("Start Session Recording")
        self.btn_rec_dash.clicked.connect(self.toggle_recording)
        quick_row.addWidget(self.btn_coolboost_dash)
        quick_row.addWidget(self.btn_hud_dash)
        quick_row.addWidget(self.btn_rec_dash)
        lay.addLayout(quick_row)
        lay.addStretch()
        return tab

    # --- TAB 2: FANS & CURVES ---
    def _build_fans_tab(self) -> QWidget:
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setSpacing(10)

        top_card = QFrame()
        top_card.setObjectName("card")
        tl = QVBoxLayout(top_card)
        tl.setContentsMargins(12, 10, 12, 10)
        tl.setSpacing(8)

        mode_row = QHBoxLayout()
        lbl = QLabel("FAN CONTROL MODE")
        lbl.setObjectName("sectionTitle")
        mode_row.addWidget(lbl)
        mode_row.addStretch()
        self.fan_mode_btns = {}
        for mode in ("Auto", "Max", "Manual", "Curve"):
            b = QPushButton(mode)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda checked=False, m=mode: self.set_fan_mode(m))
            self.fan_mode_btns[mode] = b
            mode_row.addWidget(b)
        self.btn_coolboost_fans = QPushButton("CoolBoost")
        self.btn_coolboost_fans.setObjectName("coolBtn")
        self.btn_coolboost_fans.clicked.connect(self.toggle_coolboost)
        mode_row.addWidget(self.btn_coolboost_fans)
        tl.addLayout(mode_row)

        r1 = QHBoxLayout()
        l_cf = QLabel("Manual CPU:")
        l_cf.setFixedWidth(82)
        self.slider_cpu_fan = QSlider(Qt.Orientation.Horizontal)
        self.slider_cpu_fan.setRange(25, 100)
        self.slider_cpu_fan.setValue(int(self.cfg["manual_cpu_fan"]))
        self.slider_cpu_fan.valueChanged.connect(self._on_fan_slider_changed)
        self.lbl_cpu_fan_pct = QLabel(f"{self.slider_cpu_fan.value()}%")
        self.lbl_cpu_fan_pct.setFixedWidth(38)
        r1.addWidget(l_cf)
        r1.addWidget(self.slider_cpu_fan)
        r1.addWidget(self.lbl_cpu_fan_pct)
        tl.addLayout(r1)

        r2 = QHBoxLayout()
        l_gf = QLabel("Manual GPU:")
        l_gf.setFixedWidth(82)
        self.slider_gpu_fan = QSlider(Qt.Orientation.Horizontal)
        self.slider_gpu_fan.setRange(25, 100)
        self.slider_gpu_fan.setValue(int(self.cfg["manual_gpu_fan"]))
        self.slider_gpu_fan.valueChanged.connect(self._on_fan_slider_changed)
        self.lbl_gpu_fan_pct = QLabel(f"{self.slider_gpu_fan.value()}%")
        self.lbl_gpu_fan_pct.setFixedWidth(38)
        r2.addWidget(l_gf)
        r2.addWidget(self.slider_gpu_fan)
        r2.addWidget(self.lbl_gpu_fan_pct)
        tl.addLayout(r2)
        lay.addWidget(top_card)

        curve_card = QFrame()
        curve_card.setObjectName("card")
        cl = QVBoxLayout(curve_card)
        cl.setContentsMargins(12, 10, 12, 10)
        cl.setSpacing(8)

        c_hdr = QHBoxLayout()
        l_c = QLabel("CUSTOM TEMP-TO-FAN CURVE (DRAG DOTS)")
        l_c.setObjectName("sectionTitle")
        c_hdr.addWidget(l_c)
        c_hdr.addStretch()
        self.btn_curve_cpu = QPushButton("CPU Curve")
        self.btn_curve_gpu = QPushButton("GPU Curve")
        self.btn_curve_cpu.clicked.connect(lambda: self._switch_curve_editor("CPU"))
        self.btn_curve_gpu.clicked.connect(lambda: self._switch_curve_editor("GPU"))
        btn_reset = QPushButton("Reset")
        btn_reset.clicked.connect(self._reset_active_curve)
        c_hdr.addWidget(self.btn_curve_cpu)
        c_hdr.addWidget(self.btn_curve_gpu)
        c_hdr.addWidget(btn_reset)
        cl.addLayout(c_hdr)

        self.curve_editor = FanCurveEditor(self.cfg["cpu_curve"], "#38bdf8", self._on_curve_edited)
        cl.addWidget(self.curve_editor)

        opt_row = QHBoxLayout()
        opt_row.addWidget(QLabel("Hysteresis:"))
        self.spin_hysteresis = QSpinBox()
        self.spin_hysteresis.setRange(1, 10)
        self.spin_hysteresis.setValue(int(self.cfg["curve_hysteresis"]))
        self.spin_hysteresis.setSuffix(" °C")
        self.spin_hysteresis.valueChanged.connect(self._save_ui_config)
        opt_row.addWidget(self.spin_hysteresis)
        opt_row.addSpacing(10)
        self.chk_thermal_failsafe = QCheckBox(
            f"Thermal Fail-Safe (Max fans at {THERMAL_FAILSAFE_CPU_C}°C CPU / {THERMAL_FAILSAFE_GPU_C}°C GPU)"
        )
        self.chk_thermal_failsafe.setChecked(bool(self.cfg["thermal_failsafe"]))
        self.chk_thermal_failsafe.toggled.connect(self._save_ui_config)
        opt_row.addWidget(self.chk_thermal_failsafe)
        opt_row.addStretch()
        cl.addLayout(opt_row)
        lay.addWidget(curve_card)

        self._refresh_fan_mode_buttons()
        self._switch_curve_editor("CPU")
        return tab

    # --- TAB 3: CPU / GPU TUNING & OPTIMUS WAKE-UP INSPECTOR ---
    def _build_tuning_gpu_tab(self) -> QWidget:
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setSpacing(10)

        # CPU Frequency Cap & Intel EPP Card
        cpu_card = QFrame()
        cpu_card.setObjectName("card")
        cl = QVBoxLayout(cpu_card)
        cl.setContentsMargins(12, 10, 12, 10)
        cl.setSpacing(7)

        hdr_c = QHBoxLayout()
        l_ch = QLabel(f"CPU FREQUENCY CAP & EPP TUNING  •  {self.cpu_mon.family_tag.upper()}")
        l_ch.setObjectName("sectionTitle")
        hdr_c.addWidget(l_ch)
        hdr_c.addStretch()
        btn_apply_cpu = QPushButton("Apply CPU Tuning")
        btn_apply_cpu.setObjectName("activeBtn")
        btn_apply_cpu.clicked.connect(self._apply_cpu_tuning_clicked)
        btn_reset_cpu = QPushButton("Unlimited")
        btn_reset_cpu.clicked.connect(self._reset_cpu_tuning)
        hdr_c.addWidget(btn_apply_cpu)
        hdr_c.addWidget(btn_reset_cpu)
        cl.addLayout(hdr_c)

        r_pc = QHBoxLayout()
        r_pc.addWidget(QLabel("P-Core Cap (0=Max):"))
        self.spin_pcore_cap = QSpinBox()
        self.spin_pcore_cap.setRange(0, 5800)
        self.spin_pcore_cap.setSingleStep(200)
        self.spin_pcore_cap.setValue(int(self.cfg["cpu_pcore_cap_mhz"]))
        self.spin_pcore_cap.setSuffix(" MHz")
        r_pc.addWidget(self.spin_pcore_cap)
        r_pc.addSpacing(12)
        r_pc.addWidget(QLabel("P-Core EPP (0=Fast, 100=Eco):"))
        self.spin_epp_p = QSpinBox()
        self.spin_epp_p.setRange(0, 100)
        self.spin_epp_p.setValue(int(self.cfg["cpu_epp_pcore"]))
        r_pc.addWidget(self.spin_epp_p)
        r_pc.addStretch()
        cl.addLayout(r_pc)

        r_ec = QHBoxLayout()
        r_ec.addWidget(QLabel("E-Core Cap (0=Max):"))
        self.spin_ecore_cap = QSpinBox()
        self.spin_ecore_cap.setRange(0, 4500)
        self.spin_ecore_cap.setSingleStep(200)
        self.spin_ecore_cap.setValue(int(self.cfg["cpu_ecore_cap_mhz"]))
        self.spin_ecore_cap.setSuffix(" MHz")
        self.spin_ecore_cap.setEnabled(self.cpu_mon.is_hybrid)
        r_ec.addWidget(self.spin_ecore_cap)
        r_ec.addSpacing(12)
        r_ec.addWidget(QLabel("E-Core EPP (0=Fast, 100=Eco):"))
        self.spin_epp_e = QSpinBox()
        self.spin_epp_e.setRange(0, 100)
        self.spin_epp_e.setValue(int(self.cfg["cpu_epp_ecore"]))
        self.spin_epp_e.setEnabled(self.cpu_mon.is_hybrid)
        r_ec.addWidget(self.spin_epp_e)
        r_ec.addStretch()
        cl.addLayout(r_ec)
        lay.addWidget(cpu_card)

        # NVML GPU Clock Lock Card
        gpu_card = QFrame()
        gpu_card.setObjectName("card")
        gl = QVBoxLayout(gpu_card)
        gl.setContentsMargins(12, 10, 12, 10)
        gl.setSpacing(7)

        r_gk = QHBoxLayout()
        l_gh = QLabel(f"GPU CLOCK LOCK (SOFT UNDERVOLT)  •  {self.gpu_mon.name}")
        l_gh.setObjectName("sectionTitle")
        r_gk.addWidget(l_gh)
        r_gk.addStretch()
        self.spin_gpu_cap = QSpinBox()
        self.spin_gpu_cap.setRange(0, 2800)
        self.spin_gpu_cap.setSingleStep(100)
        self.spin_gpu_cap.setValue(int(self.cfg["gpu_clock_cap_mhz"]))
        self.spin_gpu_cap.setSuffix(" MHz")
        btn_lock_gpu = QPushButton("Lock Clock")
        btn_lock_gpu.clicked.connect(self._apply_gpu_clock_lock)
        btn_unlock_gpu = QPushButton("Unlock")
        btn_unlock_gpu.clicked.connect(self._unlock_gpu_clock)
        r_gk.addWidget(QLabel("Max Clock (0=Unlock):"))
        r_gk.addWidget(self.spin_gpu_cap)
        r_gk.addWidget(btn_lock_gpu)
        r_gk.addWidget(btn_unlock_gpu)
        gl.addLayout(r_gk)
        lay.addWidget(gpu_card)

        # Optimus Wake-Up Inspector Card
        opt_card = QFrame()
        opt_card.setObjectName("card")
        ol = QVBoxLayout(opt_card)
        ol.setContentsMargins(12, 10, 12, 10)
        ol.setSpacing(6)

        o_hdr = QHBoxLayout()
        l_oh = QLabel("OPTIMUS dGPU WAKE-UP INSPECTOR (WHAT'S WAKING THE RTX GPU?)")
        l_oh.setObjectName("sectionTitle")
        btn_scan = QPushButton("Refresh Processes")
        btn_scan.clicked.connect(self._refresh_dgpu_processes)
        btn_kill = QPushButton("End Selected Process")
        btn_kill.setObjectName("dangerBtn")
        btn_kill.clicked.connect(self._kill_selected_dgpu_process)
        o_hdr.addWidget(l_oh)
        o_hdr.addStretch()
        o_hdr.addWidget(btn_scan)
        o_hdr.addWidget(btn_kill)
        ol.addLayout(o_hdr)

        self.tbl_dgpu = QTableWidget(0, 4)
        self.tbl_dgpu.setHorizontalHeaderLabels(["Process (.exe)", "PID", "Type", "VRAM (MB)"])
        self.tbl_dgpu.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tbl_dgpu.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl_dgpu.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_dgpu.setMaximumHeight(130)
        ol.addWidget(self.tbl_dgpu)
        lay.addWidget(opt_card)
        return tab

    # --- TAB 4: AUTOMATION ---
    def _build_automation_tab(self) -> QWidget:
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setSpacing(9)

        power_card = QFrame()
        power_card.setObjectName("card")
        pl = QVBoxLayout(power_card)
        pl.setContentsMargins(12, 9, 12, 9)
        pl.setSpacing(6)

        self.chk_lock = QCheckBox("Lock Performance Mode on Battery (Anti-Drift Watchdog)")
        self.chk_lock.setChecked(bool(self.cfg["dc_lock"]))
        self.chk_lock.toggled.connect(self._on_lock_toggled)
        pl.addWidget(self.chk_lock)

        self.chk_win_dc = QCheckBox("Unlock Windows DC Boost, Active Cooling & PCIe Link")
        self.chk_win_dc.setChecked(bool(self.cfg["win_dc_tuning"]))
        self.chk_win_dc.toggled.connect(self._save_ui_config)
        pl.addWidget(self.chk_win_dc)

        self.chk_poll_gpu = QCheckBox("Poll dGPU via NVML/ADL2 (uncheck to let dGPU sleep on idle battery)")
        self.chk_poll_gpu.setChecked(bool(self.cfg["poll_gpu_api"]))
        self.chk_poll_gpu.toggled.connect(self._save_ui_config)
        pl.addWidget(self.chk_poll_gpu)

        row_cut = QHBoxLayout()
        row_cut.addWidget(QLabel("Battery safety cutoff:"))
        self.spin_cutoff = QSpinBox()
        self.spin_cutoff.setRange(20, 60)
        self.spin_cutoff.setValue(int(self.cfg["safety_cutoff_pct"]))
        self.spin_cutoff.setSuffix("%")
        self.spin_cutoff.valueChanged.connect(self._save_ui_config)
        row_cut.addWidget(self.spin_cutoff)
        row_cut.addSpacing(16)
        row_cut.addWidget(QLabel("Mini HUD Corner:"))
        self.cmb_hud_corner = QComboBox()
        self.cmb_hud_corner.addItems(["Top-Right", "Top-Left", "Bottom-Right", "Bottom-Left"])
        self.cmb_hud_corner.setCurrentText(self.cfg["hud_corner"])
        self.cmb_hud_corner.currentTextChanged.connect(self._on_hud_corner_changed)
        row_cut.addWidget(self.cmb_hud_corner)
        row_cut.addStretch()
        pl.addLayout(row_cut)

        # Refresh Rate Row
        hz_row = QHBoxLayout()
        min_hz, max_hz = min(self.supported_hz), max(self.supported_hz)
        self.chk_auto_hz = QCheckBox(f"Auto Refresh ({min_hz} Hz Eco/Quiet DC ↔ {max_hz} Hz Perf/AC)")
        self.chk_auto_hz.setChecked(bool(self.cfg["auto_refresh_rate"]))
        self.chk_auto_hz.setEnabled(len(self.supported_hz) > 1)
        self.chk_auto_hz.toggled.connect(self._save_ui_config)
        hz_row.addWidget(self.chk_auto_hz)
        hz_row.addStretch()
        for hz in self.supported_hz:
            b = QPushButton(f"{hz} Hz")
            b.clicked.connect(lambda checked=False, r=hz: self._manual_set_hz(r))
            hz_row.addWidget(b)
        pl.addLayout(hz_row)

        # Per-Mode Screen Brightness Row
        br_row = QHBoxLayout()
        self.chk_auto_bright = QCheckBox("Auto Brightness:")
        self.chk_auto_bright.setChecked(bool(self.cfg["brightness_auto"]))
        self.chk_auto_bright.toggled.connect(self._save_ui_config)
        br_row.addWidget(self.chk_auto_bright)
        self.bright_spins: dict[str, QSpinBox] = {}
        for m in MODE_ORDER:
            br_row.addWidget(QLabel(f"{m[:3]}:"))
            sp = QSpinBox()
            sp.setRange(10, 100)
            sp.setValue(int(self.cfg["mode_brightness"].get(m, 70)))
            sp.setSuffix("%")
            sp.valueChanged.connect(self._save_ui_config)
            self.bright_spins[m] = sp
            br_row.addWidget(sp)
        br_row.addStretch()
        pl.addLayout(br_row)

        hk_row = QHBoxLayout()
        self.chk_hotkeys = QCheckBox("Global Hotkeys (Ctrl+Alt+1..4 & Ctrl+Alt+H)")
        self.chk_hotkeys.setChecked(bool(self.cfg["hotkeys_enabled"]))
        self.chk_hotkeys.toggled.connect(self._on_hotkeys_toggled)
        self.chk_osd = QCheckBox("OSD Toast Overlay")
        self.chk_osd.setChecked(bool(self.cfg["osd_toast_enabled"]))
        self.chk_osd.toggled.connect(self._save_ui_config)
        hk_row.addWidget(self.chk_hotkeys)
        hk_row.addStretch()
        hk_row.addWidget(self.chk_osd)
        pl.addLayout(hk_row)
        lay.addWidget(power_card)

        # Per-App Auto-Profiles + EcoQoS Guard Card
        app_card = QFrame()
        app_card.setObjectName("card")
        al = QVBoxLayout(app_card)
        al.setContentsMargins(12, 9, 12, 9)
        al.setSpacing(6)

        a_hdr = QHBoxLayout()
        self.chk_app_profiles = QCheckBox("Per-App Auto-Profiles")
        self.chk_app_profiles.setChecked(bool(self.cfg["app_profiles_enabled"]))
        self.chk_app_profiles.toggled.connect(self._save_ui_config)
        self.chk_ecoqos = QCheckBox("High Priority + Disable EcoQoS")
        self.chk_ecoqos.setChecked(bool(self.cfg["ecoqos_guard_enabled"]))
        self.chk_ecoqos.toggled.connect(self._save_ui_config)
        a_hdr.addWidget(self.chk_app_profiles)
        a_hdr.addWidget(self.chk_ecoqos)
        a_hdr.addStretch()
        self.cmb_app_mode = QComboBox()
        self.cmb_app_mode.addItems(MODE_ORDER)
        self.cmb_app_mode.setCurrentText(self.cfg["app_profile_target_mode"])
        self.cmb_app_mode.currentTextChanged.connect(self._save_ui_config)
        self.cmb_app_fan = QComboBox()
        self.cmb_app_fan.addItems(["Auto", "Max", "Curve", "Manual"])
        self.cmb_app_fan.setCurrentText(self.cfg["app_profile_target_fan"])
        self.cmb_app_fan.currentTextChanged.connect(self._save_ui_config)
        a_hdr.addWidget(self.cmb_app_mode)
        a_hdr.addWidget(self.cmb_app_fan)
        al.addLayout(a_hdr)

        add_row = QHBoxLayout()
        self.txt_exe = QLineEdit()
        self.txt_exe.setPlaceholderText("Add executable (e.g. game.exe or compiler.exe)")
        btn_add = QPushButton("Add")
        btn_add.clicked.connect(self._add_watched_app)
        btn_del = QPushButton("Remove")
        btn_del.clicked.connect(self._remove_watched_app)
        add_row.addWidget(self.txt_exe, 1)
        add_row.addWidget(btn_add)
        add_row.addWidget(btn_del)
        al.addLayout(add_row)

        self.list_apps = QListWidget()
        self.list_apps.setMaximumHeight(76)
        for exe in self.cfg["watched_apps"]:
            self.list_apps.addItem(exe)
        al.addWidget(self.list_apps)
        lay.addWidget(app_card)
        return tab

    # --- TAB 5: ANALYTICS & LOG ---
    def _build_session_log_tab(self) -> QWidget:
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setSpacing(10)

        rec_card = QFrame()
        rec_card.setObjectName("card")
        rl = QVBoxLayout(rec_card)
        rl.setContentsMargins(12, 10, 12, 10)
        rl.setSpacing(8)

        rh = QHBoxLayout()
        l_r = QLabel("SQLITE TELEMETRY SESSION RECORDER")
        l_r.setObjectName("sectionTitle")
        self.btn_rec_tab = QPushButton("Start Recording")
        self.btn_rec_tab.setObjectName("activeBtn")
        self.btn_rec_tab.clicked.connect(self.toggle_recording)
        btn_csv = QPushButton("Export Last Session CSV")
        btn_csv.clicked.connect(self._export_session_csv)
        rh.addWidget(l_r)
        rh.addStretch()
        rh.addWidget(self.btn_rec_tab)
        rh.addWidget(btn_csv)
        rl.addLayout(rh)

        s_row = QHBoxLayout()
        self.lbl_rec_dur = self._make_stat_box(s_row, "DURATION / SAMPLES", "Idle")
        self.lbl_rec_cpu = self._make_stat_box(s_row, "CPU AVG / PEAK", "--")
        self.lbl_rec_gpu = self._make_stat_box(s_row, "GPU AVG / PEAK", "--")
        self.lbl_rec_pwr = self._make_stat_box(s_row, "AVG DRAW / Wh USED", "--")
        rl.addLayout(s_row)
        lay.addWidget(rec_card)

        log_hdr = QHBoxLayout()
        l_log = QLabel("WMI & AUTOMATION EVENT LOG")
        l_log.setObjectName("sectionTitle")
        btn_clear = QPushButton("Clear Log")
        btn_clear.clicked.connect(lambda: self.log_box.clear())
        log_hdr.addWidget(l_log)
        log_hdr.addStretch()
        log_hdr.addWidget(btn_clear)
        lay.addLayout(log_hdr)

        lay.addWidget(self.log_box, 1)
        return tab

    # --- TAB 6: HARDWARE & NATIVE INTEGRATION ---
    def _build_hardware_tab(self) -> QWidget:
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setSpacing(10)

        hw_card = QFrame()
        hw_card.setObjectName("card")
        hl = QVBoxLayout(hw_card)
        hl.setContentsMargins(12, 10, 12, 10)
        hl.setSpacing(8)

        hdr = QHBoxLayout()
        l_hw = QLabel("ACER WMI HARDWARE CONTROLS (BIOS-DEPENDENT)")
        l_hw.setObjectName("sectionTitle")
        btn_inspect = QPushButton("Inspect WMI Methods")
        btn_inspect.clicked.connect(self._inspect_wmi_methods)
        hdr.addWidget(l_hw)
        hdr.addStretch()
        hdr.addWidget(btn_inspect)
        hl.addLayout(hdr)

        r1 = QHBoxLayout()
        self.chk_batt_80_hw = QCheckBox("80% Battery Charge Limit")
        self.chk_batt_80_hw.clicked.connect(self._on_battery_limit_clicked)
        self.chk_lcd_od = QCheckBox("LCD Overdrive (0x05)")
        self.chk_lcd_od.clicked.connect(lambda c: self._toggle_misc_hw("LCD Overdrive", MISC_LCD_OVERDRIVE, c))
        r1.addWidget(self.chk_batt_80_hw)
        r1.addWidget(self.chk_lcd_od)
        r1.addStretch()
        hl.addLayout(r1)

        r2 = QHBoxLayout()
        self.chk_kb_timeout = QCheckBox("KB Backlight 30s Timeout (0x02)")
        self.chk_kb_timeout.clicked.connect(lambda c: self._toggle_misc_hw("KB Backlight Timeout", MISC_KB_TIMEOUT, c))
        self.chk_usb_chg = QCheckBox("USB Power-Off Charging (0x03)")
        self.chk_usb_chg.clicked.connect(lambda c: self._toggle_misc_hw("USB Power-Off Charge", MISC_USB_CHARGE, c))
        r2.addWidget(self.chk_kb_timeout)
        r2.addWidget(self.chk_usb_chg)
        r2.addStretch()
        hl.addLayout(r2)
        lay.addWidget(hw_card)

        # Nitro Key Hijack + Service Guard Card
        nat_card = QFrame()
        nat_card.setObjectName("card")
        nl = QVBoxLayout(nat_card)
        nl.setContentsMargins(12, 10, 12, 10)
        nl.setSpacing(8)

        l_nh = QLabel("NATIVE NITRO KEY HIJACK & ACER SERVICE GUARD")
        l_nh.setObjectName("sectionTitle")
        nl.addWidget(l_nh)

        nk_row = QHBoxLayout()
        self.chk_nitro_key = QCheckBox(
            f"Hijack Dedicated Hardware Key (VK={self.cfg['nitro_key_vk']}, Scan={self.cfg['nitro_key_scan']})"
        )
        self.chk_nitro_key.setChecked(bool(self.cfg["nitro_key_hijack"]))
        self.chk_nitro_key.toggled.connect(self._on_nitro_key_toggled)
        self.btn_learn_key = QPushButton("Learn Key")
        self.btn_learn_key.clicked.connect(self._start_learn_nitro_key)
        nk_row.addWidget(self.chk_nitro_key)
        nk_row.addStretch()
        nk_row.addWidget(self.btn_learn_key)
        nl.addLayout(nk_row)

        sg_row = QHBoxLayout()
        self.chk_svc_guard = QCheckBox("Pause Conflicting Acer Sense Services While Running")
        self.chk_svc_guard.setChecked(bool(self.cfg["acer_service_guard"]))
        self.chk_svc_guard.toggled.connect(self._on_service_guard_toggled)
        self.chk_svc_restore = QCheckBox("Restore on Exit")
        self.chk_svc_restore.setChecked(bool(self.cfg["restore_acer_services_on_exit"]))
        self.chk_svc_restore.toggled.connect(self._save_ui_config)
        btn_svc_scan = QPushButton("List Acer Services")
        btn_svc_scan.clicked.connect(self._list_acer_services)
        sg_row.addWidget(self.chk_svc_guard)
        sg_row.addWidget(self.chk_svc_restore)
        sg_row.addStretch()
        sg_row.addWidget(btn_svc_scan)
        nl.addLayout(sg_row)

        lay.addWidget(nat_card)
        lay.addStretch()
        self._sync_initial_hw_toggles()
        return tab

    # --- TAB 7: HELP & ABOUT ---
    def _build_help_tab(self) -> QWidget:
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setSpacing(10)

        # About Card
        about_card = QFrame()
        about_card.setObjectName("card")
        al = QVBoxLayout(about_card)
        al.setContentsMargins(14, 12, 14, 12)
        al.setSpacing(6)

        hdr = QHBoxLayout()
        lbl_title = QLabel(f"{APP_NAME}  v{APP_VERSION}")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #f8fafc;")
        lbl_sub = QLabel(f"Developed by {APP_DEVELOPER} (@Teji007)  â€¢  {APP_LICENSE}")
        lbl_sub.setStyleSheet("font-size: 12px; color: #94a3b8;")
        hdr.addWidget(lbl_title)
        hdr.addStretch()
        hdr.addWidget(lbl_sub)
        al.addLayout(hdr)

        wmi_state = "Active (AcerGamingFunction)" if self.wmi.available else "Fallback (Windows Power)"
        lbl_sys = QLabel(
            f"Hardware: {self.cpu_mon.short_name}  â€¢  {self.gpu_mon.name} ({self.gpu_mon.vendor})  â€¢  WMI: {wmi_state}"
        )
        lbl_sys.setObjectName("metricSub")
        al.addWidget(lbl_sys)

        lbl_data = QLabel(f"Settings & Telemetry Path: {DATA_DIR}")
        lbl_data.setObjectName("metricSub")
        al.addWidget(lbl_data)

        btn_row = QHBoxLayout()
        btn_gh = QPushButton("GitHub Repository")
        btn_gh.setObjectName("activeBtn")
        btn_gh.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(APP_REPO_URL)))

        btn_dir = QPushButton("Open Data Folder")
        btn_dir.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(DATA_DIR)))

        btn_lic = QPushButton("View MIT License")
        btn_lic.clicked.connect(self._show_license_dialog)

        btn_row.addWidget(btn_gh)
        btn_row.addWidget(btn_dir)
        btn_row.addWidget(btn_lic)
        btn_row.addStretch()
        al.addLayout(btn_row)
        lay.addWidget(about_card)

        # Scrollable Feature & How-To Guide
        guide = QTextBrowser()
        guide.setOpenExternalLinks(True)
        guide.setStyleSheet(
            "QTextBrowser { background-color: #0d1118; border: 1px solid #222938; "
            "border-radius: 10px; padding: 10px; color: #cbd5e1; font-size: 12.5px; }"
        )
        guide.setHtml(f"""
        <style>
            h3 {{ color: #f8fafc; margin-top: 12px; margin-bottom: 4px; font-size: 13.5px; }}
            ul {{ margin-top: 2px; margin-bottom: 8px; padding-left: 18px; }}
            li {{ margin-bottom: 4px; line-height: 1.35; }}
            b {{ color: #f1f5f9; }}
            code {{ background-color: #1c2230; color: #fbbf24; padding: 1px 4px; border-radius: 3px; font-family: Consolas; }}
            .warn {{ color: #fca5a5; }}
        </style>

        <h3 style="margin-top:0;">1. Thermal Modes &amp; Battery (DC) Performance Unlock</h3>
        <ul>
            <li><b>Switch Modes:</b> Click <b>Eco</b>, <b>Quiet</b>, <b>Balanced</b>, or <b>Performance</b> on the top sliding bar (or press <code>Ctrl+Alt+1/2/3/4</code>). NitroPulse writes the profile directly to Acer's EC via WMI, bypassing NitroSense's battery lockout.</li>
            <li><b>Keep Performance Locked on Battery:</b> Enable <b>Lock Performance Mode on Battery</b> in the <b>Automation</b> tab. The 1.5s watchdog automatically restores <code>0x0400</code> if Windows or a background daemon tries to revert to Balanced.</li>
            <li><b>Windows DC Boost Overrides:</b> Leave <b>Unlock Windows DC Boost, Active Cooling &amp; PCIe Link</b> checked so Windows does not throttle CPU Turbo Boost or PCIe responsiveness while unplugged.</li>
        </ul>

        <h3>2. Dashboard &amp; Battery Diagnostics</h3>
        <ul>
            <li><b>Live Gauges &amp; Sparklines:</b> Monitor real-time CPU/GPU temperatures, clocks, fan RPMs, and rolling 90-second thermal trends.</li>
            <li><b>Battery Health Card:</b> Tracks live discharge/charge wattage (with a wattage sparkline), estimated runtime, voltage, and battery wear %. Toggle <b>80% Charge Limit</b> to protect battery longevity when plugged in all day (BIOS-dependent).</li>
            <li><b>Quick Actions:</b> Start <b>CoolBoost Cooldown</b>, toggle the corner <b>Mini HUD</b>, or begin a <b>Session Recording</b> directly from the bottom of the Dashboard.</li>
        </ul>

        <h3>3. Fans, Custom Curves &amp; CoolBoost (Fans &amp; Curves Tab)</h3>
        <ul>
            <li><b>Fan Modes:</b> Choose <b>Auto</b> (EC default), <b>Max</b> (100% cooling), <b>Manual</b> (drag CPU/GPU sliders independently from 20-100%), or <b>Curve</b> (automatic custom profile).</li>
            <li><b>Edit Fan Curves:</b> Select <b>CPU Curve</b> or <b>GPU Curve</b>, then drag any of the 5 dots to map temperatures (30-100 Â°C) to fan speeds (20-100%). Click <b>Reset</b> to restore defaults.</li>
            <li><b>Hysteresis &amp; Thermal Fail-Safe:</b> Set <b>Hysteresis</b> (e.g. 3 Â°C) to prevent fans from constantly pulsing up and down. Keep <b>Thermal Fail-Safe</b> checked so fans jump to <b>Max</b> automatically if CPU reaches {THERMAL_FAILSAFE_CPU_C} Â°C or GPU reaches {THERMAL_FAILSAFE_GPU_C} Â°C.</li>
            <li><b>CoolBoost Cooldown:</b> Runs both fans at 100% after heavy loads until CPU and GPU drop to {COOLBOOST_TARGET_C} Â°C or below (or after {COOLBOOST_MAX_SECS} seconds), then restores your previous fan mode.</li>
        </ul>

        <h3>4. CPU / GPU Tuning &amp; Optimus Inspector (CPU / GPU Tuning Tab)</h3>
        <ul>
            <li><b>CPU Frequency Caps &amp; EPP:</b> Set P-Core and E-Core MHz caps (<code>0 MHz</code> = unlimited) and Energy Performance Preference (<code>0</code> = max speed, <code>100</code> = max efficiency), then click <b>Apply CPU Tuning</b>. Great for stopping 50W+ spikes on battery.</li>
            <li><b>GPU Clock Lock (Soft Undervolt):</b> Enter a max clock (e.g. <code>1800-2000 MHz</code>) and click <b>Lock Clock</b> to cut RTX heat and power draw with minimal FPS loss. Click <b>Unlock</b> to restore stock boost.</li>
            <li><b>Optimus dGPU Wake-Up Inspector:</b> Click <b>Refresh Processes</b> to list every background app keeping your NVIDIA GPU awake and draining battery. Select an unwanted app and click <b>End Selected Process</b> to let the dGPU sleep.</li>
        </ul>

        <h3>5. Automation, Hotkeys &amp; Mini HUD (Automation Tab)</h3>
        <ul>
            <li><b>Battery Safety Cutoff:</b> Drops back to <b>Balanced</b> automatically at your chosen battery level (recommended <b>30%</b>) to prevent high-load voltage-sag shutdowns.</li>
            <li><b>Auto Refresh Rate &amp; Brightness:</b> Automatically drops panel refresh rate to 60 Hz on Eco/Quiet battery (and back to max Hz on Performance/AC) and adjusts screen brightness per mode.</li>
            <li><b>Per-App Auto-Profiles &amp; EcoQoS Guard:</b> Add game or heavy app names (e.g. <code>blender.exe</code>) to auto-switch mode/fans while running, elevate process priority to High, and disable Windows Efficiency Mode throttling.</li>
            <li><b>Global Hotkeys &amp; Mini HUD:</b> Press <code>Ctrl+Alt+1</code> (Eco), <code>2</code> (Quiet), <code>3</code> (Balanced), <code>4</code> (Performance), and <code>Ctrl+Alt+H</code> to toggle the click-through corner telemetry overlay.</li>
        </ul>

        <h3>6. Analytics, Hardware &amp; Native Controls</h3>
        <ul>
            <li><b>Session Recorder (Analytics &amp; Log Tab):</b> Click <b>Start Recording</b> to log samples to SQLite, view Avg/Peak temps and Wh consumed, and export to CSV. In the WMI Event Log, status <code>0x0</code> means the EC accepted the command.</li>
            <li><b>Acer Hardware Toggles (Hardware Tab):</b> Toggle 80% Charge Limit, LCD Overdrive, KB Backlight 30s Timeout, or USB Power-Off Charging. Click <b>Inspect WMI Methods</b> to log all methods exposed by your BIOS.</li>
            <li><b>Nitro Key Hijack &amp; Service Guard:</b> Click <b>Learn Key</b> and press your physical Nitro key to make it toggle NitroPulse. Enable <b>Acer Service Guard</b> to pause conflicting NitroSense daemons while NitroPulse runs.</li>
            <li><b>Portable Mode:</b> Create an empty file named <code>portable.flag</code> next to <code>NitroPulse.exe</code> to store <code>config.json</code> and <code>telemetry.db</code> in the app folder instead of AppData.</li>
        </ul>

        <p><b>Non-Affiliation Disclaimer:</b> ThermalPulse is an independent open-source project and is not affiliated with, endorsed by, or sponsored by Acer Inc., NVIDIA Corporation, AMD, or Intel. All trademarks belong to their respective owners and are referenced solely to indicate hardware compatibility.</p><p class="warn"><b>Hardware Note:</b> On battery, NVIDIA VBIOS still enforces a firmware GPU wattage cap (typically 25-35 W) to protect laptop battery cells. Keep Battery Safety Cutoff and Thermal Fail-Safe enabled.</p>
        """)
        lay.addWidget(guide, 1)
        return tab

    def _show_license_dialog(self):
        QMessageBox.information(
            self,
            f"{APP_NAME} â€” {APP_LICENSE}",
            f"{APP_NAME} v{APP_VERSION}\n"
            f"Copyright (c) 2026 {APP_DEVELOPER}\n\n"
            "Permission is hereby granted, free of charge, to any person obtaining a copy "
            "of this software and associated documentation files (the \"Software\"), to deal "
            "in the Software without restriction, including without limitation the rights "
            "to use, copy, modify, merge, publish, distribute, sublicense, and/or sell "
            "copies of the Software, subject to the MIT License terms.\n\n"
            "THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND."
        )

    def _sync_initial_hw_toggles(self):
        lim = self.wmi.get_battery_charge_limit()
        if lim is not None:
            self.chk_batt_80_dash.setChecked(lim)
            self.chk_batt_80_hw.setChecked(lim)
        for idx, chk in (
            (MISC_LCD_OVERDRIVE, self.chk_lcd_od),
            (MISC_KB_TIMEOUT, self.chk_kb_timeout),
            (MISC_USB_CHARGE, self.chk_usb_chg),
        ):
            val = self.wmi.get_misc_setting(idx)
            if val is not None:
                chk.setChecked(bool(val))

    def _build_tray(self):
        self.icon_perf = make_status_icon("#ef4444")
        self.icon_bal = make_status_icon("#818cf8")
        self.icon_eco = make_status_icon("#10b981")
        self.icon_quiet = make_status_icon("#38bdf8")
        self.icon_safe = make_status_icon("#f59e0b")

        self.tray = QSystemTrayIcon(self.icon_perf, self)
        menu = QMenu()
        act_show = QAction("Open Control Center", self)
        act_show.triggered.connect(self.show_window)
        menu.addAction(act_show)
        menu.addSeparator()

        for mode in MODE_ORDER:
            act = QAction(f"Mode: {mode}", self)
            act.triggered.connect(lambda checked=False, m=mode: self.manual_set_profile(m))
            menu.addAction(act)

        menu.addSeparator()
        for fmode in ("Auto", "Max", "Curve"):
            act = QAction(f"Fans: {fmode}", self)
            act.triggered.connect(lambda checked=False, fm=fmode: self.set_fan_mode(fm))
            menu.addAction(act)
        act_cb = QAction("CoolBoost Cooldown (Max -> 50°C)", self)
        act_cb.triggered.connect(self.toggle_coolboost)
        menu.addAction(act_cb)
        act_hud = QAction("Toggle Mini HUD", self)
        act_hud.triggered.connect(self.toggle_hud)
        menu.addAction(act_hud)

        menu.addSeparator()
        act_quit = QAction("Quit", self)
        act_quit.triggered.connect(self.quit_app)
        menu.addAction(act_quit)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray_click)
        self.tray.show()

    # -------------------------------------------------------------------------
    # HOTKEYS, NITRO KEY, HUD, COOLBOOST & RECORDING
    # -------------------------------------------------------------------------

    def _setup_hotkeys(self):
        self._teardown_hotkeys()
        if not self.chk_hotkeys.isChecked():
            return
        hwnd = int(self.winId())
        mods = 0x0002 | 0x0001 | 0x4000  # Ctrl + Alt + NoRepeat
        for hk_id, vk in ((1, 0x31), (2, 0x32), (3, 0x33), (4, 0x34), (5, 0x48)):
            if user32.RegisterHotKey(hwnd, hk_id, mods, vk):
                self._registered_hotkeys.append(hk_id)
        if self.hotkey_filter is None:
            self.hotkey_filter = GlobalHotkeyFilter(self._on_hotkey_pressed)
            QApplication.instance().installNativeEventFilter(self.hotkey_filter)

    def _teardown_hotkeys(self):
        if self._registered_hotkeys:
            hwnd = int(self.winId())
            for hk_id in self._registered_hotkeys:
                user32.UnregisterHotKey(hwnd, hk_id)
            self._registered_hotkeys.clear()

    def _on_hotkeys_toggled(self, checked: bool):
        self._save_ui_config()
        if checked:
            self._setup_hotkeys()
            self.log("Global hotkeys registered (Ctrl+Alt+1..4, Ctrl+Alt+H).")
        else:
            self._teardown_hotkeys()
            self.log("Global hotkeys unregistered.")

    def _on_hotkey_pressed(self, hk_id: int):
        if 1 <= hk_id <= len(MODE_ORDER):
            self.manual_set_profile(MODE_ORDER[hk_id - 1], show_toast=True, toast_sub="Global Hotkey Triggered")
        elif hk_id == 5:
            self.toggle_hud()

    def _on_nitro_key_toggled(self, checked: bool):
        self._save_ui_config()
        if checked:
            self.nitro_hook.start(int(self.cfg["nitro_key_vk"]), int(self.cfg["nitro_key_scan"]))
            self.log("Nitro Key hijack enabled.")
        else:
            self.nitro_hook.stop()
            self.log("Nitro Key hijack disabled.")

    def _start_learn_nitro_key(self):
        if not self.nitro_hook.hook_id:
            self.nitro_hook.start(int(self.cfg["nitro_key_vk"]), int(self.cfg["nitro_key_scan"]))
        self.nitro_hook.learning = True
        self.btn_learn_key.setText("Press Nitro Key Now...")
        self.log("Waiting for key press to bind Nitro Key...")

    def _on_nitro_key_learned(self, vk: int, scan: int):
        self.cfg["nitro_key_vk"] = vk
        self.cfg["nitro_key_scan"] = scan
        self.chk_nitro_key.setText(f"Hijack Dedicated Hardware Key (VK={vk}, Scan={scan})")
        self.chk_nitro_key.setChecked(True)
        self.btn_learn_key.setText("Learn Key")
        self._save_ui_config()
        self.log(f"Bound Hardware Key to VK={vk}, Scan={scan}.")

    def _on_nitro_key_pressed(self):
        if self.isVisible() and not self.isMinimized():
            self.hide()
        else:
            self.show_window()

    def toggle_hud(self):
        if self.hud.isVisible():
            self.hud.hide()
            self.cfg["hud_visible"] = False
            self._show_osd(self.current_mode_name, "Mini HUD Hidden")
        else:
            self.hud.set_corner(self.cmb_hud_corner.currentText())
            self.hud.show()
            self.cfg["hud_visible"] = True
            self._show_osd(self.current_mode_name, "Mini HUD Active")
        save_config(self.cfg)

    def _on_hud_corner_changed(self, corner: str):
        self.hud.set_corner(corner)
        self._save_ui_config()

    def toggle_coolboost(self):
        if self._coolboost_active:
            self._coolboost_active = False
            self.set_fan_mode(self._coolboost_prev_fan_mode)
            self.btn_coolboost_dash.setText("CoolBoost Cooldown (Max -> 50°C)")
            self.log("CoolBoost Cooldown cancelled.")
        else:
            self._coolboost_prev_fan_mode = self.fan_mode
            self._coolboost_active = True
            self._coolboost_start_ts = time.time()
            self.set_fan_mode("Max", silent=True)
            self.btn_coolboost_dash.setText("Stop CoolBoost (Active)")
            self.log(f"CoolBoost Cooldown started: Max fans until <= {COOLBOOST_TARGET_C}°C (max {COOLBOOST_MAX_SECS}s).")
            self._show_osd("Quiet", f"CoolBoost Active -> {COOLBOOST_TARGET_C}°C")

    def toggle_recording(self):
        if not self.recorder.recording:
            sid = self.recorder.start_session()
            self.btn_rec_dash.setText("Stop Session Recording")
            self.btn_rec_tab.setText("Stop Recording")
            self.btn_rec_tab.setObjectName("dangerBtn")
            self.btn_rec_tab.style().unpolish(self.btn_rec_tab)
            self.btn_rec_tab.style().polish(self.btn_rec_tab)
            self.log(f"Started SQLite telemetry session: {sid}")
        else:
            summary = self.recorder.stop_session()
            self.btn_rec_dash.setText("Start Session Recording")
            self.btn_rec_tab.setText("Start Recording")
            self.btn_rec_tab.setObjectName("activeBtn")
            self.btn_rec_tab.style().unpolish(self.btn_rec_tab)
            self.btn_rec_tab.style().polish(self.btn_rec_tab)
            self._render_session_summary(summary)
            self.log(f"Stopped telemetry session: {summary}")

    def _render_session_summary(self, s: dict):
        if not s or s.get("samples", 0) == 0:
            return
        dur = s["duration_s"]
        self.lbl_rec_dur.setText(f"{dur // 60}m {dur % 60:02d}s ({s['samples']} pts)")
        self.lbl_rec_cpu.setText(f"{s.get('avg_cpu_c', '--')}° / {s.get('peak_cpu_c', '--')}°C")
        self.lbl_rec_gpu.setText(f"{s.get('avg_gpu_c', '--')}° / {s.get('peak_gpu_c', '--')}°C")
        avg_w = f"{s['avg_dis_w']} W" if s.get("avg_dis_w") is not None else "AC"
        self.lbl_rec_pwr.setText(f"{avg_w} • {s.get('wh_used', 0.0)} Wh")

    def _export_session_csv(self):
        if not self.recorder.session_id:
            QMessageBox.information(self, "Export CSV", "Record a telemetry session first.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export Telemetry CSV", f"{self.recorder.session_id}.csv", "CSV Files (*.csv)")
        if path:
            count = self.recorder.export_csv(self.recorder.session_id, path)
            self.log(f"Exported {count} telemetry rows to {path}")

    def _show_osd(self, mode: str, subtitle: str):
        if self.chk_osd.isChecked() and mode in MODE_THEME:
            self.toast.show_toast(mode.upper(), subtitle, MODE_THEME[mode]["color"])

    # -------------------------------------------------------------------------
    # CPU / GPU TUNING, OPTIMUS INSPECTOR & SERVICE GUARD HANDLERS
    # -------------------------------------------------------------------------

    def _apply_cpu_tuning_clicked(self):
        self._save_ui_config()
        apply_cpu_freq_and_epp(
            self.spin_pcore_cap.value(),
            self.spin_ecore_cap.value(),
            self.spin_epp_p.value(),
            self.spin_epp_e.value(),
            self.cpu_mon.is_hybrid,
        )
        self.log(
            f"Applied CPU Tuning: P-Cap={self.spin_pcore_cap.value()}MHz, E-Cap={self.spin_ecore_cap.value()}MHz, "
            f"EPP P={self.spin_epp_p.value()}/E={self.spin_epp_e.value()}"
        )

    def _reset_cpu_tuning(self):
        self.spin_pcore_cap.setValue(0)
        self.spin_ecore_cap.setValue(0)
        self.spin_epp_p.setValue(10)
        self.spin_epp_e.setValue(30)
        self._apply_cpu_tuning_clicked()

    def _apply_gpu_clock_lock(self):
        self._save_ui_config()
        ok, msg = self.gpu_mon.set_clock_lock(self.spin_gpu_cap.value())
        self.log(f"GPU Clock Lock: {msg} (ok={ok})")

    def _unlock_gpu_clock(self):
        self.spin_gpu_cap.setValue(0)
        self._apply_gpu_clock_lock()

    def _refresh_dgpu_processes(self):
        procs = self.gpu_mon.get_running_processes()
        self.tbl_dgpu.setRowCount(len(procs))
        for r, item in enumerate(procs):
            self.tbl_dgpu.setItem(r, 0, QTableWidgetItem(str(item["exe"])))
            self.tbl_dgpu.setItem(r, 1, QTableWidgetItem(str(item["pid"])))
            self.tbl_dgpu.setItem(r, 2, QTableWidgetItem(str(item["type"])))
            self.tbl_dgpu.setItem(r, 3, QTableWidgetItem(f"{item['vram_mb']:.1f}"))
        self.log(f"Optimus Inspector: found {len(procs)} active dGPU process(es).")

    def _kill_selected_dgpu_process(self):
        row = self.tbl_dgpu.currentRow()
        if row < 0:
            return
        exe = self.tbl_dgpu.item(row, 0).text()
        pid = int(self.tbl_dgpu.item(row, 1).text())
        if terminate_pid(pid):
            self.log(f"Terminated dGPU process {exe} (PID {pid}).")
            QTimer.singleShot(500, self._refresh_dgpu_processes)
        else:
            self.log(f"Failed to terminate {exe} (PID {pid}) — may be protected.")

    def _on_service_guard_toggled(self, checked: bool):
        self._save_ui_config()
        if checked:
            stopped = self.svc_guard.stop_conflicting()
            self.log(f"Service Guard stopped: {stopped if stopped else 'none running'}")
        else:
            started = self.svc_guard.restore_paused()
            self.log(f"Service Guard restored: {started if started else 'none paused'}")

    def _list_acer_services(self):
        svcs = self.svc_guard.find_acer_services()
        self.log("Detected Acer services: " + (", ".join(f"{n} ({s})" for n, s in svcs) if svcs else "None found"))

    # -------------------------------------------------------------------------
    # CONFIG, HARDWARE TOGGLES & FAN HANDLERS
    # -------------------------------------------------------------------------

    def _save_ui_config(self, *_args):
        self.cfg["dc_lock"] = self.chk_lock.isChecked()
        self.cfg["win_dc_tuning"] = self.chk_win_dc.isChecked()
        self.cfg["poll_gpu_api"] = self.chk_poll_gpu.isChecked()
        self.cfg["safety_cutoff_pct"] = self.spin_cutoff.value()
        self.cfg["fan_mode"] = self.fan_mode
        self.cfg["manual_cpu_fan"] = self.slider_cpu_fan.value()
        self.cfg["manual_gpu_fan"] = self.slider_gpu_fan.value()
        self.cfg["curve_hysteresis"] = self.spin_hysteresis.value()
        self.cfg["thermal_failsafe"] = self.chk_thermal_failsafe.isChecked()
        self.cfg["auto_refresh_rate"] = self.chk_auto_hz.isChecked()
        self.cfg["hotkeys_enabled"] = self.chk_hotkeys.isChecked()
        self.cfg["osd_toast_enabled"] = self.chk_osd.isChecked()
        self.cfg["hud_corner"] = self.cmb_hud_corner.currentText()
        self.cfg["app_profiles_enabled"] = self.chk_app_profiles.isChecked()
        self.cfg["ecoqos_guard_enabled"] = self.chk_ecoqos.isChecked()
        self.cfg["app_profile_target_mode"] = self.cmb_app_mode.currentText()
        self.cfg["app_profile_target_fan"] = self.cmb_app_fan.currentText()
        self.cfg["watched_apps"] = [self.list_apps.item(i).text() for i in range(self.list_apps.count())]
        self.cfg["cpu_pcore_cap_mhz"] = self.spin_pcore_cap.value()
        self.cfg["cpu_ecore_cap_mhz"] = self.spin_ecore_cap.value()
        self.cfg["cpu_epp_pcore"] = self.spin_epp_p.value()
        self.cfg["cpu_epp_ecore"] = self.spin_epp_e.value()
        self.cfg["gpu_clock_cap_mhz"] = self.spin_gpu_cap.value()
        self.cfg["brightness_auto"] = self.chk_auto_bright.isChecked()
        for m, sp in self.bright_spins.items():
            self.cfg["mode_brightness"][m] = sp.value()
        self.cfg["nitro_key_hijack"] = self.chk_nitro_key.isChecked()
        self.cfg["acer_service_guard"] = self.chk_svc_guard.isChecked()
        self.cfg["restore_acer_services_on_exit"] = self.chk_svc_restore.isChecked()
        save_config(self.cfg)

    def _on_battery_limit_clicked(self, checked: bool):
        self.chk_batt_80_dash.setChecked(checked)
        self.chk_batt_80_hw.setChecked(checked)
        ok, msg = self.wmi.set_battery_charge_limit(checked)
        self.log(f"80% Battery Limit -> {'ON' if checked else 'OFF'} | {msg}")
        if not ok:
            self.chk_batt_80_dash.setChecked(not checked)
            self.chk_batt_80_hw.setChecked(not checked)

    def _toggle_misc_hw(self, label: str, idx: int, checked: bool):
        try:
            st = self.wmi.set_misc_setting(idx, 1 if checked else 0)
            self.log(f"{label} (0x{idx:02X}) -> {'ON' if checked else 'OFF'} (WMI status: {hex(st)})")
        except Exception as exc:
            self.log(f"{label} error: {exc}")

    def _inspect_wmi_methods(self):
        self.log("AcerGamingFunction methods: " + (", ".join(self.wmi.available_methods) if self.wmi.available_methods else "None"))
        for name, idx in (("KB Timeout", MISC_KB_TIMEOUT), ("USB Charge", MISC_USB_CHARGE), ("LCD Overdrive", MISC_LCD_OVERDRIVE)):
            self.log(f"  Misc 0x{idx:02X} ({name}) = {self.wmi.get_misc_setting(idx)}")

    def _manual_set_hz(self, hz: int):
        ok, msg = DisplayRefreshController.set_refresh_rate(hz)
        if ok:
            self.cur_hz = hz
        self.log(f"Display Refresh: {msg}")

    def _add_watched_app(self):
        exe = self.txt_exe.text().strip().lower()
        if not exe:
            return
        if not exe.endswith(".exe"):
            exe += ".exe"
        existing = [self.list_apps.item(i).text().lower() for i in range(self.list_apps.count())]
        if exe not in existing:
            self.list_apps.addItem(exe)
            self.txt_exe.clear()
            self._save_ui_config()
            self.log(f"Added watched app: {exe}")

    def _remove_watched_app(self):
        for item in self.list_apps.selectedItems():
            self.list_apps.takeItem(self.list_apps.row(item))
        self._save_ui_config()

    def _switch_curve_editor(self, target: str):
        self.active_curve_target = target
        is_cpu = target == "CPU"
        self.btn_curve_cpu.setObjectName("activeBtn" if is_cpu else "")
        self.btn_curve_gpu.setObjectName("activeBtn" if not is_cpu else "")
        for b in (self.btn_curve_cpu, self.btn_curve_gpu):
            b.style().unpolish(b)
            b.style().polish(b)
        self.curve_editor.set_curve(self.cfg["cpu_curve"] if is_cpu else self.cfg["gpu_curve"], "#38bdf8" if is_cpu else "#ef4444")

    def _on_curve_edited(self, new_pts: list[list[int]]):
        key = "cpu_curve" if self.active_curve_target == "CPU" else "gpu_curve"
        self.cfg[key] = new_pts
        self._save_ui_config()
        self.log(f"Updated {self.active_curve_target} fan curve: {new_pts}")
        if self.fan_mode != "Curve":
            self.set_fan_mode("Curve")

    def _reset_active_curve(self):
        key = "cpu_curve" if self.active_curve_target == "CPU" else "gpu_curve"
        self.cfg[key] = [list(pt) for pt in DEFAULT_CONFIG[key]]
        self._switch_curve_editor(self.active_curve_target)
        self._save_ui_config()
        self.log(f"Reset {self.active_curve_target} curve to default.")

    def _on_tray_click(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_window()

    def show_window(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def showEvent(self, event):
        super().showEvent(event)
        if not self.anim_timer.isActive():
            self.anim_timer.start(20)

    def hideEvent(self, event):
        super().hideEvent(event)
        self.anim_timer.stop()

    def _tick_animations(self):
        self.hero.advance_frame()
        self.cpu_card.gauge.tick_ease()
        self.gpu_card.gauge.tick_ease()

    def log(self, msg: str):
        if hasattr(self, "log_box"):
            self.log_box.appendPlainText(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    def _apply_saved_startup_fan_mode(self):
        if self.fan_mode in ("Auto", "Max", "Manual", "Curve"):
            self.set_fan_mode(self.fan_mode, silent=True)

    def _refresh_fan_mode_buttons(self):
        for mode, btn in self.fan_mode_btns.items():
            btn.setObjectName("activeBtn" if mode == self.fan_mode else "")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _on_fan_slider_changed(self):
        self.lbl_cpu_fan_pct.setText(f"{self.slider_cpu_fan.value()}%")
        self.lbl_gpu_fan_pct.setText(f"{self.slider_gpu_fan.value()}%")
        self._coolboost_active = False
        self.fan_mode = "Manual"
        self._refresh_fan_mode_buttons()
        self._save_ui_config()
        self.fan_apply_timer.start(150)

    def set_fan_mode(self, mode: str, silent: bool = False):
        self.fan_mode = mode
        self._refresh_fan_mode_buttons()
        self._save_ui_config()
        self._last_sent_cpu_pct = None
        self._last_sent_gpu_pct = None
        try:
            if mode == "Auto":
                st = self.wmi.set_fan_behavior("Auto")
                if not silent:
                    self.log(f"Fan mode -> Auto (WMI status: {hex(st)})")
            elif mode == "Max":
                st = self.wmi.set_fan_behavior("Max")
                if not silent:
                    self.log(f"Fan mode -> Max (WMI status: {hex(st)})")
            elif mode == "Manual":
                self._commit_manual_fan_speeds(silent=silent)
            elif mode == "Curve":
                st = self.wmi.set_fan_behavior("Custom")
                if not silent:
                    self.log(f"Fan mode -> Custom Curve active (WMI status: {hex(st)})")
        except Exception as exc:
            self.log(f"ERROR setting fan mode {mode}: {exc}")

    def _commit_manual_fan_speeds(self, silent: bool = False):
        cpu_pct, gpu_pct = self.slider_cpu_fan.value(), self.slider_gpu_fan.value()
        try:
            b_st = self.wmi.set_fan_behavior("Custom")
            c_st = self.wmi.set_fan_speed(FAN_ID_CPU, cpu_pct)
            g_st = self.wmi.set_fan_speed(FAN_ID_GPU, gpu_pct)
            if not silent:
                self.log(f"Manual fans: CPU={cpu_pct}% GPU={gpu_pct}% (beh={hex(b_st)}, cpu={hex(c_st)}, gpu={hex(g_st)})")
        except Exception as exc:
            self.log(f"ERROR setting manual fan speed: {exc}")

    def _apply_fan_curve_step(self, cpu_temp: int | None, gpu_temp: int | None):
        hyst = float(self.spin_hysteresis.value())
        changed = False
        if cpu_temp is not None:
            if self._curve_eval_cpu_t is None or cpu_temp >= self._curve_eval_cpu_t or cpu_temp <= (self._curve_eval_cpu_t - hyst):
                self._curve_eval_cpu_t = float(cpu_temp)
            target_cpu = eval_fan_curve(self.cfg["cpu_curve"], self._curve_eval_cpu_t)
            if self._last_sent_cpu_pct is None or abs(target_cpu - self._last_sent_cpu_pct) >= 2:
                self.wmi.set_fan_behavior("Custom")
                self.wmi.set_fan_speed(FAN_ID_CPU, target_cpu)
                self._last_sent_cpu_pct = target_cpu
                changed = True
        if gpu_temp is not None:
            if self._curve_eval_gpu_t is None or gpu_temp >= self._curve_eval_gpu_t or gpu_temp <= (self._curve_eval_gpu_t - hyst):
                self._curve_eval_gpu_t = float(gpu_temp)
            target_gpu = eval_fan_curve(self.cfg["gpu_curve"], self._curve_eval_gpu_t)
            if self._last_sent_gpu_pct is None or abs(target_gpu - self._last_sent_gpu_pct) >= 2:
                if not changed:
                    self.wmi.set_fan_behavior("Custom")
                self.wmi.set_fan_speed(FAN_ID_GPU, target_gpu)
                self._last_sent_gpu_pct = target_gpu

    def _reapply_fan_preference(self):
        if self.fan_mode == "Max":
            self.set_fan_mode("Max", silent=True)
        elif self.fan_mode == "Manual":
            self._commit_manual_fan_speeds(silent=True)
        elif self.fan_mode == "Curve":
            self._last_sent_cpu_pct = None
            self._last_sent_gpu_pct = None

    # -------------------------------------------------------------------------
    # MAIN WATCHDOG, AUTOMATION & TELEMETRY LOOP
    # -------------------------------------------------------------------------

    def _on_lock_toggled(self, checked: bool):
        self.safety_tripped = False
        self._save_ui_config()
        self.log(f"Battery Performance lock {'ENABLED' if checked else 'DISABLED'}.")
        self.tick_watchdog()

    def manual_set_profile(self, name: str, show_toast: bool = False, toast_sub: str = "Thermal Profile Updated"):
        try:
            status = self.wmi.set_profile(name)
            if name != "Performance":
                self.chk_lock.setChecked(False)
            self._reapply_fan_preference()
            self.log(f"Switch -> {name} (WMI status: {hex(status)})")
            if show_toast:
                self._show_osd(name, toast_sub)
            self.tick_watchdog()
        except Exception as exc:
            self.log(f"ERROR setting {name}: {exc}")

    def _check_auto_refresh_rate(self, on_ac: bool, mode_name: str):
        if not self.chk_auto_hz.isChecked() or len(self.supported_hz) < 2:
            return
        desired = min(self.supported_hz) if (not on_ac and mode_name in ("Eco", "Quiet")) else max(self.supported_hz)
        if desired != self.cur_hz:
            ok, msg = DisplayRefreshController.set_refresh_rate(desired)
            if ok:
                self.cur_hz = desired
                self.log(f"Auto Refresh: {msg}")

    def _check_auto_brightness(self, mode_name: str):
        if not self.chk_auto_bright.isChecked():
            return
        if mode_name != self._last_applied_brightness_mode and mode_name in self.bright_spins:
            pct = self.bright_spins[mode_name].value()
            if BrightnessController.set_brightness(pct):
                self._last_applied_brightness_mode = mode_name
                self.log(f"Auto Brightness ({mode_name}) -> {pct}%")

    def _check_app_auto_profiles(self, cur_mode: str):
        if not self.chk_app_profiles.isChecked():
            return
        watched = {self.list_apps.item(i).text().lower() for i in range(self.list_apps.count())}
        if not watched:
            return
        pmap = get_process_map()
        matched_pids = [(pid, exe) for pid, exe in pmap.items() if exe in watched]

        if matched_pids:
            # Apply High Priority + disable EcoQoS for newly detected watched PIDs
            if self.chk_ecoqos.isChecked():
                for pid, exe in matched_pids:
                    if pid not in self._boosted_pids:
                        if boost_process_priority_no_ecoqos(pid):
                            self._boosted_pids.add(pid)
                            self.log(f"EcoQoS Guard: Boosted {exe} (PID {pid}) to High Priority.")
            if not self._app_override_active:
                self._app_override_active = True
                self._pre_app_mode = cur_mode
                self._pre_app_fan_mode = self.fan_mode
                t_mode, t_fan = self.cmb_app_mode.currentText(), self.cmb_app_fan.currentText()
                app_name = matched_pids[0][1]
                self.wmi.set_profile(t_mode)
                self.set_fan_mode(t_fan, silent=True)
                self.log(f"Auto-Profile triggered by {app_name} -> {t_mode} + Fans:{t_fan}")
                self._show_osd(t_mode, f"Auto-Profile: {app_name}")
        elif self._app_override_active:
            self._app_override_active = False
            self._boosted_pids.clear()
            self.wmi.set_profile(self._pre_app_mode)
            self.set_fan_mode(self._pre_app_fan_mode, silent=True)
            self.log(f"Watched apps closed -> Restored {self._pre_app_mode} + Fans:{self._pre_app_fan_mode}")
            self._show_osd(self._pre_app_mode, "Auto-Profile Restored")

    def _update_telemetry(self, on_ac: bool, batt_pct: int, cur_mode: str):
        ec = self.wmi.read_ec_sensors()
        cpu_mhz, cpu_util = self.cpu_mon.read()
        gpu = self.gpu_mon.read() if self.chk_poll_gpu.isChecked() else {}
        batt = self.batt_diag.read()

        cpu_temp = ec["cpu_temp"]
        gpu_temp = gpu.get("temp_c") if gpu.get("temp_c") is not None else ec["gpu_temp"]
        cpu_rpm, gpu_rpm = ec["cpu_rpm"], ec["gpu_rpm"]

        # CPU Card
        self.cpu_card.gauge.set_temp(cpu_temp)
        self.cpu_card.spark.push(cpu_temp)
        self.cpu_card.lbl_clock.setText(f"{cpu_mhz} MHz" if cpu_mhz is not None else "-- MHz")
        self.cpu_card.lbl_line1.setText(f"Utilization: {cpu_util}%" if cpu_util is not None else "Utilization: --%")
        self.cpu_card.lbl_line2.setText(f"Fan: {cpu_rpm} RPM" if cpu_rpm is not None else "Fan: -- RPM")
        self.cpu_card.lbl_badge.setText(self.cpu_mon.family_tag)

        # GPU Card + Throttle Reason Badge
        self.gpu_card.gauge.set_temp(gpu_temp)
        self.gpu_card.spark.push(gpu_temp)
        gpu_core = gpu.get("core_mhz")
        self.gpu_card.lbl_clock.setText(
            f"{gpu_core} MHz" if gpu_core is not None else ("Sleeping" if not self.chk_poll_gpu.isChecked() else "-- MHz")
        )
        pwr_txt = f"{gpu['power_w']} W" if gpu.get("power_w") is not None else "-- W"
        mem_txt = f"{gpu['mem_mhz']} MHz" if gpu.get("mem_mhz") is not None else "--"
        self.gpu_card.lbl_line1.setText(f"Power: {pwr_txt}  •  Mem: {mem_txt}")
        self.gpu_card.lbl_line2.setText(f"Fan: {gpu_rpm} RPM" if gpu_rpm is not None else "Fan: -- RPM")
        reasons = gpu.get("throttle_reasons") or []
        self.gpu_card.lbl_badge.setText("Status: " + " / ".join(reasons[:2]) if reasons else "")

        # Battery Card + Wattage Sparkline
        watts = batt["watts"]
        if watts is not None:
            watt_str = f"{'+' if watts > 0 else ''}{watts:.1f} W"
            self.batt_spark.push(abs(watts))
        else:
            watt_str = "-- W"
        self.lbl_batt_watts.setText(f"{watt_str} ({batt['state']})")
        self.lbl_batt_eta.setText(batt["eta_str"])
        self.lbl_batt_wear.setText(f"{batt['wear_pct']}%" if batt["wear_pct"] is not None else "--%")
        cap_parts = []
        if batt["full_mwh"] and batt["designed_mwh"]:
            cap_parts.append(f"{batt['full_mwh']/1000:.1f}/{batt['designed_mwh']/1000:.1f} Wh")
        if batt["voltage_v"]:
            cap_parts.append(f"{batt['voltage_v']:.2f} V")
        self.lbl_batt_cap.setText(" • ".join(cap_parts) if cap_parts else "--")

        # Update Mini HUD Overlay
        if self.hud.isVisible():
            l1 = f"CPU {cpu_temp if cpu_temp is not None else '--'}°C {cpu_mhz or '--'}MHz  |  GPU {gpu_temp if gpu_temp is not None else '--'}°C {gpu_core or '--'}MHz {pwr_txt}"
            l2 = f"FAN {cpu_rpm or '--'}/{gpu_rpm or '--'} RPM  |  {'AC' if on_ac else 'DC'} {batt_pct}% {watt_str}  |  {cur_mode.upper()}"
            self.hud.update_metrics(l1, l2, MODE_THEME.get(cur_mode, MODE_THEME["Balanced"])["color"])

        # Update Curve Editor Live Marker
        self.curve_editor.set_live_temp(cpu_temp if self.active_curve_target == "CPU" else gpu_temp)

        # Record SQLite Telemetry Sample if active
        if self.recorder.recording:
            self.recorder.record_sample(
                cur_mode, on_ac, batt_pct, watts, cpu_temp, cpu_mhz,
                gpu_temp, gpu_core, gpu.get("power_w"), cpu_rpm, gpu_rpm,
            )
            if self._tick_counter % 2 == 0:
                self._render_session_summary(self.recorder.get_session_summary(self.recorder.session_id))

        # CoolBoost Auto-Stop Check
        if self._coolboost_active:
            elapsed = time.time() - self._coolboost_start_ts
            cooled = (cpu_temp is not None and cpu_temp <= COOLBOOST_TARGET_C) and (gpu_temp is None or gpu_temp <= COOLBOOST_TARGET_C)
            if cooled or elapsed >= COOLBOOST_MAX_SECS:
                self._coolboost_active = False
                self.set_fan_mode(self._coolboost_prev_fan_mode)
                self.btn_coolboost_dash.setText("CoolBoost Cooldown (Max -> 50°C)")
                self.log(f"CoolBoost finished ({'target reached' if cooled else 'timeout'}) -> Restored {self._coolboost_prev_fan_mode}.")
                self._show_osd(cur_mode, f"CoolBoost Done -> Fans {self._coolboost_prev_fan_mode}")
            return cpu_temp, gpu_temp, watt_str

        # Thermal Fail-Safe in Manual/Curve Mode
        if self.chk_thermal_failsafe.isChecked() and self.fan_mode in ("Manual", "Curve"):
            if (cpu_temp is not None and cpu_temp >= THERMAL_FAILSAFE_CPU_C) or (
                gpu_temp is not None and gpu_temp >= THERMAL_FAILSAFE_GPU_C
            ):
                self.log(f"THERMAL FAIL-SAFE (CPU={cpu_temp}°C, GPU={gpu_temp}°C): Switching fans to MAX.")
                self.set_fan_mode("Max")
                return cpu_temp, gpu_temp, watt_str

        if self.fan_mode == "Curve":
            self._apply_fan_curve_step(cpu_temp, gpu_temp)

        return cpu_temp, gpu_temp, watt_str

    def tick_watchdog(self):
        self._tick_counter += 1
        try:
            on_ac, pct = get_power_status()
            cur_id = self.wmi.get_profile_id()
            cur_name = ID_TO_NAME.get(cur_id, "Balanced")
            cutoff = self.spin_cutoff.value()

            if self._tick_counter % 2 == 0:
                self._check_app_auto_profiles(cur_name)
                cur_id = self.wmi.get_profile_id()
                cur_name = ID_TO_NAME.get(cur_id, "Balanced")

            if not on_ac:
                if pct <= cutoff:
                    if not self.safety_tripped:
                        self.safety_tripped = True
                        self.log(f"SAFETY CUTOFF ({pct}% <= {cutoff}%): Dropping to Balanced.")
                        self._show_osd("Balanced", f"Battery Safety Cutoff ({pct}%)")
                    if cur_id != PROFILES["Balanced"][0]:
                        self.wmi.set_profile("Balanced")
                        cur_id, cur_name = PROFILES["Balanced"][0], "Balanced"
                    if self.last_dc_tuning_state is not False:
                        apply_windows_dc_tuning(False)
                        self.last_dc_tuning_state = False
                elif self.chk_lock.isChecked() and not self._app_override_active:
                    self.safety_tripped = False
                    if cur_id != PROFILES["Performance"][0]:
                        status = self.wmi.set_profile("Performance")
                        self._reapply_fan_preference()
                        self.log(f"Watchdog restored Performance on battery (status: {hex(status)})")
                        cur_id = self.wmi.get_profile_id()
                        cur_name = ID_TO_NAME.get(cur_id, "Performance")
                    if self.chk_win_dc.isChecked() and self.last_dc_tuning_state is not True:
                        apply_windows_dc_tuning(True)
                        self.last_dc_tuning_state = True
                        self.log("Applied Windows DC Aggressive Boost & Active Cooling.")
            else:
                self.safety_tripped = False

            self._check_auto_refresh_rate(on_ac, cur_name)
            self._check_auto_brightness(cur_name)
            cpu_temp, gpu_temp, watt_str = self._update_telemetry(on_ac, pct, cur_name)

            source_short = "AC POWER" if on_ac else "BATTERY"
            fan_txt = "COOLBOOST" if self._coolboost_active else self.fan_mode.upper()
            self.hero.set_mode(cur_name, f"EC 0x{cur_id:02X}00" if self.wmi.available else "WIN POWER")
            self.hero.set_badges(f"{source_short} • {pct}%", watt_str, f"FANS: {fan_txt}")

            if cur_name != self.current_mode_name:
                self.current_mode_name = cur_name
                self.mode_bar.set_active_mode(cur_name, animate=True)

            if self.safety_tripped:
                self.tray.setIcon(self.icon_safe)
            else:
                icon_map = {"Performance": self.icon_perf, "Balanced": self.icon_bal, "Eco": self.icon_eco, "Quiet": self.icon_quiet}
                self.tray.setIcon(icon_map.get(cur_name, self.icon_bal))

            t_cpu = f"{cpu_temp}°C" if cpu_temp is not None else "--"
            t_gpu = f"{gpu_temp}°C" if gpu_temp is not None else "--"
            self.tray.setToolTip(f"ThermalPulse | {source_short} ({pct}%) | {cur_name} | {watt_str} | CPU {t_cpu} / GPU {t_gpu}")
        except Exception as exc:
            self.log(f"Watchdog error: {exc}")

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray.showMessage(
            "ThermalPulse Control Center",
            "Running silently in tray (animations paused to save battery).",
            QSystemTrayIcon.MessageIcon.Information,
            2000,
        )

    def quit_app(self):
        self._save_ui_config()
        # Hardware safety: return fans to Auto and release GPU clock lock on exit
        try:
            if self.fan_mode in ("Manual", "Curve") or self._coolboost_active:
                self.wmi.set_fan_behavior("Auto")
        except Exception:
            pass
        try:
            if self.cfg.get("gpu_clock_cap_mhz", 0) > 0:
                self.gpu_mon.set_clock_lock(0)
        except Exception:
            pass
        self._teardown_hotkeys()
        self.nitro_hook.stop()
        if self.cfg["restore_acer_services_on_exit"]:
            self.svc_guard.restore_paused()
        self.anim_timer.stop()
        self.hw_timer.stop()
        self.fan_apply_timer.stop()
        self.cpu_mon.close()
        self.gpu_mon.shutdown()
        self.recorder.close()
        self.hud.close()
        self.toast.close()
        self.tray.hide()
        QApplication.quit()


def main():
    if not is_admin():
        relaunch_as_admin()

    # Bind Windows taskbar icon/grouping to our custom AppUserModelID
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    except Exception:
        pass

    # Named Win32 mutex so Inno Setup detects running instances during upgrade/uninstall
    kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_wchar_p]
    kernel32.CreateMutexW.restype = ctypes.c_void_p
    _mutex = kernel32.CreateMutexW(None, 0, "Global\\ThermalPulse_SingleInstance_Mutex")

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setStyle("Fusion")
    app.setQuitOnLastWindowClosed(False)
    if os.path.exists(ICON_PATH):
        app.setWindowIcon(QIcon(ICON_PATH))

    # If another instance is already running, wake its window and exit
    probe = QLocalSocket()
    probe.connectToServer("ThermalPulse_IPC_Pipe")
    if probe.waitForConnected(250):
        probe.write(b"SHOW")
        probe.flush()
        probe.waitForBytesWritten(250)
        probe.disconnectFromServer()
        sys.exit(0)

    QLocalServer.removeServer("ThermalPulse_IPC_Pipe")
    ipc_server = QLocalServer()
    ipc_server.listen("ThermalPulse_IPC_Pipe")

    try:
        win = NitroDCUnlockApp()
        win.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        if os.path.exists(ICON_PATH):
            win.setWindowIcon(QIcon(ICON_PATH))

        def _on_ipc():
            conn = ipc_server.nextPendingConnection()
            if conn:
                conn.waitForReadyRead(200)
                conn.close()
            win.show_window()

        ipc_server.newConnection.connect(_on_ipc)

        if not win.cfg.get("disclaimer_accepted", False):
            reply = QMessageBox.warning(
                None,
                f"{APP_NAME} â€” Legal & Hardware Safety Notice",
                f"{APP_NAME} v{APP_VERSION} is an independent open-source utility by Tejinder Pal Singh (MIT License).\n\n"
                "NON-AFFILIATION DISCLAIMER:\n"
                "This project is not affiliated with, endorsed by, or sponsored by Acer Inc., NVIDIA Corporation, AMD, or Intel. "
                "All trademarks belong to their respective owners and are used solely to indicate hardware compatibility.\n\n"
                "HARDWARE SAFETY NOTICE:\n"
                "- High wattage draw on battery increases cell wear. Keep Battery Safety Cutoff (20%+) enabled.\n"
                "- Keep Thermal Fail-Safe enabled with custom fan curves. Fans reset to Auto automatically on exit.\n"
                "- Provided \"AS IS\" without warranty; you assume responsibility for hardware settings applied.\n\n"
                "Do you accept these terms and wish to continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if reply != QMessageBox.StandardButton.Yes:
                win.quit_app()
                sys.exit(0)
            win.cfg["disclaimer_accepted"] = True
            save_config(win.cfg)

        if "--minimized" not in sys.argv:
            win.show()
        sys.exit(app.exec())
    except Exception as e:
        QMessageBox.critical(None, f"{APP_NAME} Startup Error", str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
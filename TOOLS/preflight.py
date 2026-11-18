"""Job Chrome pre-flight (the Chrome profile in config/kit.json "chrome_profile"), the computer side. The browser side (Claude in Chrome tools) is in
BROWSER_PREFLIGHT.md, which says when to call each command.

  python preflight.py        status as JSON, changes nothing
  python preflight.py fix    Chrome closed: start the job Chrome profile. Chrome open but the extension
                             is offline: close Chrome politely and start it again, only when job Chrome is
                             the only Chrome profile open (never force-kills, never touches Brave).
                             Opening one more window does not revive a dead extension (tested), so a
                             running Chrome is always restarted, never given an extra window.
  python preflight.py unhide un-minimize Chrome behind your windows, without focus (screenshot timeouts)
  python preflight.py close  end of a scheduled run: close Chrome politely, only when job Chrome is the only profile
                             open (an open browser should mean a run is working)

Root cause this exists for (2026-10-13): the 12:37 warm-up found Chrome closed. Helium's exe is also
named chrome.exe, so "chrome is running" checks by name were wrong. Match by install path instead.
"""
import ctypes
import ctypes.wintypes
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
CHROME_EXE = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
USER_DATA = os.path.join(os.environ["LOCALAPPDATA"], "Google", "Chrome", "User Data")
sys.path.insert(0, HERE)
import kit
PROFILE = kit.cfg().get("chrome_profile", "Default")
EXT_ID = "fcoeoabgfenejglbffodgkkbkcdhcgfn"
# Chrome stops drawing minimized or covered windows, and then the extension's screenshots time out
# (first real warm-up run, 2026-10-13). These keep the pages drawing. Not automation flags.
KEEP_DRAWING = ["--disable-backgrounding-occluded-windows", "--disable-renderer-backgrounding",
                "--disable-background-timer-throttling"]
user32 = ctypes.windll.user32


def ps(cmd):
    out = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True)
    return out.stdout.strip()


def processes():
    raw = ps("Get-CimInstance Win32_Process -Filter \"name='chrome.exe' or name='brave.exe'\" | "
             "Select-Object ProcessId,Name,ExecutablePath,CommandLine | ConvertTo-Json -Compress")
    if not raw:
        return []
    data = json.loads(raw)
    return data if isinstance(data, list) else [data]


def read_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def status():
    procs = processes()
    chrome = [p for p in procs if (p.get("ExecutablePath") or "").lower() == CHROME_EXE.lower()]
    main = [p for p in chrome if "--type=" not in (p.get("CommandLine") or "")]
    ext = read_json(os.path.join(USER_DATA, PROFILE, "Secure Preferences"))
    ext = ext.get("extensions", {}).get("settings", {}).get(EXT_ID)
    open_profiles = read_json(os.path.join(USER_DATA, "Local State")).get("profile", {}).get("last_active_profiles", [])
    return {
        "chrome_running": bool(main),
        "keep_drawing": any(KEEP_DRAWING[0] in (p.get("CommandLine") or "") for p in main),
        "extension_process": any("--extension-process" in (p.get("CommandLine") or "") for p in chrome),
        "extension_installed": ext is not None,
        "extension_enabled": ext is not None and not ext.get("disable_reasons"),
        # ponytail: Local State is flushed by Chrome every few seconds, so this can lag a profile just opened.
        "open_profiles": open_profiles if main else [],
        "brave_running": any(p.get("Name") == "brave.exe" for p in procs),
    }


def wait_for(check, seconds):
    end = time.time() + seconds
    while time.time() < end:
        if check():
            return True
        time.sleep(2)
    return False


def foreground_is_chrome():
    pid = ctypes.wintypes.DWORD()
    user32.GetWindowThreadProcessId(user32.GetForegroundWindow(), ctypes.byref(pid))
    return pid.value in {p["ProcessId"] for p in processes()
                         if (p.get("ExecutablePath") or "").lower() == CHROME_EXE.lower()}


def send_chrome_back():
    """Put every Chrome window behind your windows, open but unfocused. Not minimized: Chrome will not
    draw a minimized window, so the extension's screenshots time out (tested 2026-10-13)."""
    pids = {p["ProcessId"] for p in processes() if (p.get("ExecutablePath") or "").lower() == CHROME_EXE.lower()}

    def each(hwnd, _):
        pid = ctypes.wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value in pids and user32.IsWindowVisible(hwnd) and user32.GetWindowTextLengthW(hwnd):
            user32.ShowWindow(hwnd, 4)  # SW_SHOWNOACTIVATE: un-minimize without focus
            user32.SetWindowPos(hwnd, 1, 0, 0, 0, 0, 0x13)  # HWND_BOTTOM; NOSIZE, NOMOVE, NOACTIVATE
        return True
    user32.EnumWindows(ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)(each), 0)


def launch():
    # Chrome takes keyboard focus when it starts, whatever show flag it gets (tested), and the window it
    # restores can be a Gmail inbox, where single keys are shortcuts. So if he had focus elsewhere and
    # Chrome grabs it, push Chrome behind your windows and give your window focus back.
    his_window = None if foreground_is_chrome() else user32.GetForegroundWindow()
    subprocess.Popen([CHROME_EXE, f"--profile-directory={PROFILE}", *KEEP_DRAWING])
    wait_for(lambda: status()["extension_process"], 30)
    end = time.time() + 10  # Chrome can grab focus a few seconds late (new window, restored tabs)
    while his_window and time.time() < end:
        if foreground_is_chrome():
            send_chrome_back()
            user32.SwitchToThisWindow(his_window, True)
        time.sleep(1)
    send_chrome_back()  # also un-minimizes a window left minimized, so pages draw
    s = status()
    s["action"] = "launched"
    s["chrome_had_focus_after"] = foreground_is_chrome()
    return s


def close():
    """Polite close at the end of a scheduled run (an open Chrome should mean a run is
    really working). Same guard as restart: only when job Chrome is the only profile open."""
    s = status()
    if not s["chrome_running"]:
        s["action"] = "already closed"
        return s
    others = [p for p in s["open_profiles"] if p != PROFILE]
    if others:
        s["action"] = f"left open: other Chrome profiles are open ({', '.join(others)}), you may be using them"
        return s
    for _ in range(15):
        mains = [p for p in processes() if (p.get("ExecutablePath") or "").lower() == CHROME_EXE.lower()
                 and "--type=" not in (p.get("CommandLine") or "")]
        if not mains:
            break
        for p in mains:
            subprocess.run(["taskkill", "/PID", str(p["ProcessId"])], capture_output=True)
        time.sleep(2)
    s = status()
    s["action"] = "closed" if not s["chrome_running"] else "refused: Chrome did not close politely within 30 seconds"
    return s


def restart():
    s = status()
    if not s["chrome_running"]:
        return launch()
    others = [p for p in s["open_profiles"] if p != PROFILE]
    if others:
        s["action"] = f"refused: other Chrome profiles are open ({', '.join(others)}), you may be using them"
        return s
    # Polite close: WM_CLOSE to each window, like clicking X. Never /F, so nothing is lost.
    for _ in range(15):
        mains = [p for p in processes() if (p.get("ExecutablePath") or "").lower() == CHROME_EXE.lower()
                 and "--type=" not in (p.get("CommandLine") or "")]
        if not mains:
            break
        for p in mains:
            subprocess.run(["taskkill", "/PID", str(p["ProcessId"])], capture_output=True)
        time.sleep(2)
    if status()["chrome_running"]:
        s = status()
        s["action"] = "refused: Chrome did not close politely within 30 seconds (a page may be asking to stay open)"
        return s
    return launch()


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    result = {"status": status, "fix": restart, "close": close, "unhide": lambda: (send_chrome_back(), status())[1]}[cmd]()
    print(json.dumps(result, indent=1))

# 🤖 Teleops Automation Suite

A dual-purpose automation suite designed for Symbotic Teleops operators:

1. **⚡ SOP Auto-Logging** — Lightning-fast auto-fill for "Logging SOP" forms (Multi-Display, SUSPECT & CHRF modes, Quick Clipboard). Zero AI/heavy dependencies — **installs in 5 seconds!**
2. **🎯 Teleops Auto-Claim** — Automated bot row detection and claiming using screen capture & OCR.

---

## 🧭 Choose Your Tool

| Tool | Purpose | Setup Time | Key Dependencies | Quick Launcher |
| :--- | :--- | :---: | :--- | :--- |
| **[1. SOP Auto-Logging](#-part-1-sop-auto-logging-standalone)** | Auto-fill SOP form after handling bot | **~5 seconds** | `pyautogui`, `Pillow` | `Run_SOP_Admin.bat` |
| **[2. Teleops Auto-Claim](#-part-2-teleops-auto-claim)** | Auto-scan & claim bots from table | **~1-2 minutes** | `easyocr`, `opencv`, `mss` | `Run_AutoClaim_Admin.bat` |

---

## ⚡ PART 1: SOP Auto-Logging (Standalone)

Used to auto-fill the Teleops **"Logging SOP"** form in under 0.3 seconds. Position-based, supports multiple monitors (Monitor 4 Main & Monitor 3), and features a floating HUD with dropdown type switching.

### 1. Quick Installation (Snap a finger!)

Only requires `pyautogui` and `Pillow`.

* **Option A (1-Click):** Double-click `Install_AutoLogging.bat`.
* **Option B (Terminal):**
  ```bash
  pip install -r auto_logging/requirements.txt
  ```

> 💡 **Tip:** If you double-click `Run_SOP_Admin.bat` directly, it will even auto-detect missing libraries and install them for you automatically!

### 2. How to Run

* **Method 1 (Recommended):** Double-click `Run_SOP_Admin.bat` (launches with Administrator privileges).
* **Method 2:**
  ```bash
  python sop_main.py
  ```

### 3. Screen Calibration (One-time setup per display)

SOP Auto-Logging supports both **Monitor 4 (Main)** and **Monitor 3 (Secondary)**:

#### Step 3.1: Calibrate Form Coordinates (Center of the 6 fields)
```bash
python sop_main.py calibrate --display 4      # For Main Monitor 4
python sop_main.py calibrate --display 3      # For Secondary Monitor 3
```
Click the center of: `Vision Functionality` -> `Actions Required` -> `Maintenance Issues` -> `Resolution` -> `Comment` -> `SEND`.

#### Step 3.2: Calibrate Dropdown Options
```bash
python sop_main.py calibrate_options --display 4   # For Monitor 4
python sop_main.py calibrate_options --display 3   # For Monitor 3
```

> 🌟 **Alt+Tab Pro-Tip (Prevent mouse shift):**
> 1. Click a dropdown on the SOP form so the menu expands.
> 2. Hover your mouse over the target option (**DO NOT click**).
> 3. While keeping your hand steady on the mouse, press **`Alt + Tab`** on your keyboard to focus the CMD window.
> 4. Press **`ENTER`** in the CMD window. The pixel coordinate is recorded with 100% precision!

### 4. Hotkeys & SOP Types

The floating HUD has a **Dropdown** to switch between **`SUSPECT`** and **`CHRF`**. Both types use the **exact same keys**:

| Hotkey | [SUSPECT] Case | [CHRF] Case |
| :---: | :--- | :--- |
| **`INSERT`** | Case 1: All cam / Align + Extract / Success | Case 1: All cam / Align + Place / Success |
| **`HOME`** | Case 2: No cam / No action / Unsuccessful | Case 2: All cam / Home actuator / Success |
| **`PAGE UP`** | Case 3: All cam / Not pickable / Unsuccessful | Case 3: All cam / Home + Align + Place / Success |
| **`PAGE DOWN`** | Case 4: All cam / Align + Ext / CHD (with payload) | Case 4: All cam / Home / Axes not resp / CHD (no payload) |
| **`END`** | Case 5: All cam / No case / Success | Case 5: All cam / Home / Sensor malf / CHD (no payload) |
| **`DELETE`** | Case 6: All cam / Rogue case / CHD (with payload) | Case 6: All cam / Align + Ext / Damaged / CHD (with payload) |
| **`F6`** | Toggle active monitor: **Monitor 4 (Main)** $\leftrightarrow$ **Monitor 3** | Same |
| **`Ctrl+ESC`** | Exit tool | Same |

### 5. Quick Clipboard

At the bottom of the HUD, 8 pre-configured error keywords are available. Simply **click any keyword button** to copy it instantly to your clipboard:
* `bh_damage_case_on_payload`
* `bh_rogue_case_on_payload`
* `bh_debris_on_payload`
* `bh_tape_on_actuator`
* `bh_coh_fail`
* `bh_actuator_stuck`
* `bh_lift_tilts`
* `bh_bot_damaged`

---

## 🎯 PART 2: Teleops Auto-Claim

Monitors the Teleops bot list table, detects available `CLAIM` rows using OCR, confirms your username, selects the row, and connects to the bot.

### 1. Installation

Requires OCR and vision dependencies (`easyocr`, `opencv-python`, `mss`, `rapidfuzz`).

* **Option A (1-Click):** Double-click `Install_AutoClaim.bat`.
* **Option B (Terminal):**
  ```bash
  pip install -r auto_claim/requirements.txt
  ```

> **Note:** EasyOCR will download its language recognition model (~100 MB) on first launch.

### 2. Configuration (`auto_claim/config.json`)

Open [auto_claim/config.json](file:///c:/Users/SYMBOTIC/Documents/Automation/auto_claim/config.json) and configure:

```json
{
  "username": "YOUR_TELEOPS_USERNAME",
  "allowed_teleop_types": ["SUSPECT", "CHRF"],
  "site_blocklist": []
}
```

### 3. Calibrate Table Regions

```bash
python main.py calibrate
```
A semi-transparent overlay will appear. Follow the prompts:
1. Drag-select the **Bot Table region**.
2. Drag-select the **CLAIM column**.
3. Drag-select the **TELEOP TYPE column** (containing SUSPECT / CHRF).
4. Drag-select the **SELECT button column**.
5. Click the **CONNECT button**.

### 4. How to Run

* **Method 1 (Recommended):** Double-click `Run_AutoClaim_Admin.bat`.
* **Method 2:**
  ```bash
  python main.py
  ```
* **Controls:**
  * **`F8`**: Start / Pause scanning for bots.
  * **`F9`**: Exit tool.

---

## 📁 Repository Structure

```
Automation/
├── auto_logging/               # ⚡ Tool 1: SOP Auto-Logging
│   ├── requirements.txt        # Lightweight dependencies (pyautogui, Pillow)
│   ├── sop_main.py             # Entry point
│   ├── sop_hud.py              # Floating HUD window with Dropdown & Clipboard
│   ├── sop_logging.py          # Auto-fill logic (SUSPECT & CHRF cases)
│   ├── sop_config.json         # Monitor coordinates & geometry
│   ├── sop_config.py           # Config manager
│   └── sop_calibrate.py        # Calibration tools (Form & Options)
│
├── auto_claim/                 # 🎯 Tool 2: Teleops Auto-Claim
│   ├── requirements.txt        # Vision/OCR dependencies (easyocr, opencv, mss)
│   ├── main.py                 # Entry point
│   ├── config.json             # Configuration (username, regions)
│   ├── config.py               # Config manager
│   ├── capture.py              # Fast screen capture (<10ms)
│   ├── ocr.py                  # EasyOCR text reader
│   ├── vision.py               # Row & button detector
│   ├── clicker.py              # Safe mouse controller
│   └── workflow.py             # State machine engine
│
├── Install_AutoLogging.bat     # 1-Click setup for Auto-Logging (~5s)
├── Install_AutoClaim.bat       # 1-Click setup for Auto-Claim
├── Run_SOP_Admin.bat           # 1-Click launcher for SOP Logging (Admin)
├── Run_AutoClaim_Admin.bat     # 1-Click launcher for Auto-Claim (Admin)
├── main.py                     # Root wrapper -> auto_claim.main
├── sop_main.py                 # Root wrapper -> auto_logging.sop_main
├── requirements.txt            # Complete package list
├── HUONG_DAN.txt               # Complete Vietnamese guide
└── README.md
```

---

## 🛠️ Troubleshooting

| Issue | Tool | Solution |
| :--- | :--- | :--- |
| **"No module named pyautogui"** | Auto-Logging | Run `Install_AutoLogging.bat` or `pip install -r auto_logging/requirements.txt` |
| **"Failed to register hotkey"** | Both | Make sure no other instance of the tool is running in another CMD window. Always launch with Admin (`Run_SOP_Admin.bat`). |
| **Mouse clicks wrong position** | Auto-Logging | Re-run calibration: `python sop_main.py calibrate --display <3|4>` and `calibrate_options`. |
| **Bot not claiming** | Auto-Claim | Verify `"username"` matches your exact account name in `auto_claim/config.json`. |
| **High CPU usage** | Auto-Claim | In `auto_claim/config.json`, set `"loop_interval_ms": 200`. |

# Automatic Poker Odds Calculator - Quick Start Guide

A real-time poker odds calculator that automatically detects cards to calculate hand rank probabilities.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Platform](https://img.shields.io/badge/Platform-Linux%20|%20macOS%20|%20Windows-lightgrey.svg)

---

## Prerequisites

### All Platforms
- **Python 3.10+** (check with `python3 --version`)

### Linux (X11)
You need one of these window management tools:
```bash
# Ubuntu/Debian
sudo apt install wmctrl

# Fedora
sudo dnf install wmctrl

# Arch
sudo pacman -S wmctrl
```

For reliable card detections, also install ImageMagick:
```bash
sudo apt install imagemagick
```

### macOS
No additional system tools needed (uses native Quartz APIs).

### Windows
No additional system tools needed (uses native Win32 APIs).

---

## Installation

### Step 1: Clone or Download
```bash
cd /path/to/your/projects
git clone https://github.com/aipokertools/AutomaticPokerOddsCalculator.git
cd AutomaticPokerOddsCalculator
```

### Step 2: Create Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate  # Linux/macOS
# OR
.venv\Scripts\activate     # Windows
```

### Step 3: Install Dependencies
```bash
pip install mss Pillow questionary requests rich
```

**Platform-specific extras:**

| Platform | Extra Package |
|----------|---------------|
| macOS    | `pip install pyobjc-framework-Quartz` |
| Windows  | `pip install pywin32` |

### Step 4: Verify Installation
```bash
python calculator.py --help
```

You should see:
```
usage: calculator.py [-h] [--opponents OPPONENTS]

Poker Probability Calculator

options:
  -h, --help            show this help message and exit
  --opponents OPPONENTS Number of opponents (will prompt if not provided)
```

---

## Usage

### Basic Usage
```bash
source .venv/bin/activate
python calculator.py
```

This will:
1. List all open windows
2. Let you select your poker client
3. Ask how many opponents you're playing against
4. Start the live probability display

### With Command-Line Options
```bash
# Pre-set 3 opponents (skip the prompt)
python calculator.py --opponents 3
```

### Stopping the Calculator
Press **Ctrl+C** to exit at any time.

---

## Understanding the Display

```
╭──────────────────────────── Automatic Poker Odds Calculator ♥ ♦ ♣ ♠ ────────────────────────────╮
│ Window: PokerStars  │  Opponents (↑↓): 2  │  Scan #42  │  Ctrl+C exit                            │
╰─────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─────── Your Hole Cards ───────╮╭────────────────── Community Cards ──────────────────╮
│ ┌─────┐ ┌─────┐               ││ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐                     │
│ │J    │ │2    │               ││ │9    │ │5    │ │K    │ │7    │                     │
│ │  ♦  │ │  ♣  │               ││ │  ♠  │ │  ♦  │ │  ♣  │ │  ♦  │                     │
│ │    J│ │    2│               ││ │    9│ │    5│ │    K│ │    7│                     │
│ └─────┘ └─────┘               ││ └─────┘ └─────┘ └─────┘ └─────┘                     │
╰───────────────────────────────╯╰─────────────────────────────────────────────────────╯
╭────────────────────────────────── Hand Probabilities ───────────────────────────────────╮
│ Hand               You                          Opp                                     │
│ Straight Flush    0.0%  ░░░░░░░░░░░░░░░░░░     0.0%  ░░░░░░░░░░░░░░░░░░                │
│ Four of a Kind    0.0%  ░░░░░░░░░░░░░░░░░░     0.1%  ░░░░░░░░░░░░░░░░░░                │
│ Full House        0.0%  ░░░░░░░░░░░░░░░░░░     2.5%  ░░░░░░░░░░░░░░░░░░                │
│ Flush             0.0%  ░░░░░░░░░░░░░░░░░░     3.2%  ░░░░░░░░░░░░░░░░░░                │
│ Straight          0.0%  ░░░░░░░░░░░░░░░░░░     9.9%  ▓░░░░░░░░░░░░░░░░░                │
│ Three of a Kind   0.1%  ░░░░░░░░░░░░░░░░░░     5.5%  ░░░░░░░░░░░░░░░░░░                │
│ Two Pair          0.0%  ░░░░░░░░░░░░░░░░░░    25.1%  ▓▓▓▓░░░░░░░░░░░░░░                │
│ One Pair         39.0%  ▓▓▓▓▓▓▓░░░░░░░░░░░    47.9%  ▓▓▓▓▓▓▓▓░░░░░░░░░░                │
│ High Card        60.9%  ▓▓▓▓▓▓▓▓▓▓▓░░░░░░░     5.8%  ▓░░░░░░░░░░░░░░░░░                │
╰─────────────────────────────────────────────────────────────────────────────────────────╯
╭────────────────────────────────── Win Probability ──────────────────────────────────────╮
│                                                                                          │
│ ██████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
│                                                                                          │
│   WIN:   6%   TIE:   2%   LOSE:  92%                                                    │
╰─────────────────────────────────────────────────────────────────────────────────────────╯
```

| Section | Description |
|---------|-------------|
| **Header** | Shows target window, opponent count (use ↑↓ to adjust), and scan iteration |
| **Hole Cards** | Your two private cards displayed as ASCII art |
| **Community Cards** | The flop/turn/river cards on the table |
| **Hand Probabilities** | Side-by-side comparison of hand odds for you and opponents |
| **Win Probability** | Visual bar + percentages for win/tie/lose outcomes |

### Controls
- **↑ / ↓ arrows**: Increase/decrease opponent count (1-9)
- **Ctrl+C**: Exit the calculator

---

## Troubleshooting

### "No visible windows found!"
- **Linux**: Make sure `wmctrl` is installed: `sudo apt install wmctrl`
- **All**: Ensure your poker client is open and not minimized

### "Failed to capture window"
- **Linux**: Install ImageMagick: `sudo apt install imagemagick`
- The window may have moved off-screen or been minimized
- Try selecting a different window to verify capture works

### "API request timed out"
- Check your internet connection
- The API server may be temporarily unavailable

### Cards not detected correctly
- Ensure the poker table is fully visible (not obscured)
- The window should show the cards clearly
- Supported poker clients may vary - the API works best with standard card designs

### Display looks garbled
- Make sure your terminal supports Unicode and 256 colors
- Recommended terminals: iTerm2 (macOS), Windows Terminal, GNOME Terminal, Konsole
- Try resizing your terminal to be wider

---

## API Information

The calculator uses the AIPokerTools card detection API:
- **Endpoint**: `https://aipokertools.com/api/v1/detect-cards`
- **Rate**: 1 request per second
- **License Key**: Prompted at first run and saved to `calculator_license_key.txt`

---

## File Structure

```
AutomaticPokerOddsCalculator/
├── calculator.py              # Main application
├── calculator_license_key.txt # API license key (created on first run)
├── README.md                  # This guide
├── requirements_linux.txt     # Linux dependencies
├── requirements_macos.txt     # macOS dependencies
└── .venv/                     # Python virtual environment
```

---

## License

This tool is for personal/educational use. Ensure you comply with your poker platform's terms of service regarding third-party tools.


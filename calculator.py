#!/usr/bin/env python3
"""
Automatic Poker Odds Calculator

Captures screenshots of a poker client window and sends them to an API
for card detection and probability calculation.

Usage:
    python calculator.py
"""

import argparse
import io
import platform
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Optional
import readchar
import threading

# Check for required dependencies
def check_dependencies():
    """Check and report missing dependencies."""
    missing = []

    try:
        import mss
    except ImportError:
        missing.append("mss")

    try:
        from PIL import Image
    except ImportError:
        missing.append("Pillow")

    try:
        import questionary
    except ImportError:
        missing.append("questionary")

    try:
        import requests
    except ImportError:
        missing.append("requests")

    try:
        from rich.console import Console
    except ImportError:
        missing.append("rich")

    if missing:
        print("Missing required dependencies. Install them with:")
        print(f"  pip install {' '.join(missing)}")
        sys.exit(1)

check_dependencies()

import mss
import questionary
import requests
from PIL import Image
from questionary import Style
from rich.console import Console, ConsoleOptions, RenderResult
from rich.layout import Layout
from rich.live import Live
from rich.measure import Measurement
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box


# ═══════════════════════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════════════════════

API_URL = "https://aipokertools.com/api/v1/detect-cards"
IMAGE_QUALITY_URL = "https://aipokertools.com/api/v1/image-quality"
LICENSE_KEY_FILE = "calculator_license_key.txt"
DEFAULT_IMAGE_QUALITY = 100


def get_license_key() -> str:
    """Load license key from file, or prompt user to enter it."""
    import os

    # Try to load from file
    if os.path.exists(LICENSE_KEY_FILE):
        try:
            with open(LICENSE_KEY_FILE, "r") as f:
                key = f.read().strip()
                if key:
                    return key
        except Exception:
            pass

    # Prompt user for license key
    print("\n" + "=" * 50)
    print("License key not found!")
    print("=" * 50)
    print("\nPlease enter your license key.")
    print(f"It will be saved to '{LICENSE_KEY_FILE}' for future use.\n")

    key = input("License Key: ").strip()

    if not key:
        print("No license key provided. Exiting.")
        sys.exit(1)

    # Save to file
    try:
        with open(LICENSE_KEY_FILE, "w") as f:
            f.write(key)
        print(f"\n[Saved to {LICENSE_KEY_FILE}]")
    except Exception as e:
        print(f"\nWarning: Could not save license key to file: {e}")

    return key


def get_image_quality() -> int:
    """Fetch ideal JPEG quality from API, or return default on failure."""
    try:
        response = requests.get(IMAGE_QUALITY_URL, timeout=5)
        if response.status_code == 200:
            data = response.json()
            quality = data.get("quality", DEFAULT_IMAGE_QUALITY)
            if isinstance(quality, int) and 1 <= quality <= 100:
                return quality
    except Exception:
        pass
    return DEFAULT_IMAGE_QUALITY


# Card display symbols
SUIT_SYMBOLS = {
    'h': '♥', 'hearts': '♥',
    'd': '♦', 'diamonds': '♦',
    'c': '♣', 'clubs': '♣',
    's': '♠', 'spades': '♠',
}

SUIT_COLORS = {
    'h': 'red', 'd': 'blue', 'c': 'green', 's': 'white'
}

# Poker hands in order from best to worst
POKER_HANDS = [
    "Straight Flush",
    "Four of a Kind",
    "Full House",
    "Flush",
    "Straight",
    "Three of a Kind",
    "Two Pair",
    "One Pair",
    "High Card",
]


# ═══════════════════════════════════════════════════════════════════════════════
# Window Management
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class WindowInfo:
    """Represents information about a window."""
    id: str
    title: str
    x: int
    y: int
    width: int
    height: int

    def __str__(self) -> str:
        return f"{self.title} ({self.width}x{self.height})"


class MacWindowManager:
    """Window management for macOS using native APIs."""

    def get_windows(self) -> list[WindowInfo]:
        """Get list of windows using AppleScript."""
        windows = []

        # Use CGWindowListCopyWindowInfo via Python
        try:
            import Quartz

            # Get all on-screen windows
            window_list = Quartz.CGWindowListCopyWindowInfo(
                Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements,
                Quartz.kCGNullWindowID
            )

            for win in window_list:
                # Skip windows without names or with empty names
                name = win.get(Quartz.kCGWindowName, "")
                owner = win.get(Quartz.kCGWindowOwnerName, "")

                if not name and not owner:
                    continue

                # Skip very small windows (likely UI elements)
                bounds = win.get(Quartz.kCGWindowBounds, {})
                width = int(bounds.get("Width", 0))
                height = int(bounds.get("Height", 0))

                if width < 100 or height < 100:
                    continue

                window_id = win.get(Quartz.kCGWindowNumber, 0)

                windows.append(WindowInfo(
                    id=str(window_id),
                    title=f"{owner}: {name}" if name else owner,
                    x=int(bounds.get("X", 0)),
                    y=int(bounds.get("Y", 0)),
                    width=width,
                    height=height
                ))

        except ImportError:
            print("Error: PyObjC not found. Install with: pip install pyobjc-framework-Quartz")
            sys.exit(1)

        return windows

    def focus_window(self, window: WindowInfo) -> bool:
        """Focus a window using AppleScript."""
        # Extract app name from title (format is "AppName: WindowTitle")
        app_name = window.title.split(":")[0].strip()

        script = f'''
        tell application "{app_name}"
            activate
        end tell
        '''
        try:
            subprocess.run(["osascript", "-e", script], capture_output=True, check=True)
            time.sleep(0.3)
            return True
        except subprocess.CalledProcessError:
            return False

    def capture_window(self, window: WindowInfo) -> Optional[Image.Image]:
        """Capture a specific window by its ID."""
        try:
            import Quartz
            from Quartz import CGWindowListCreateImage, CGRectNull, kCGWindowListOptionIncludingWindow, kCGWindowImageDefault

            window_id = int(window.id)

            # Capture the specific window
            image_ref = CGWindowListCreateImage(
                CGRectNull,
                kCGWindowListOptionIncludingWindow,
                window_id,
                kCGWindowImageDefault
            )

            if image_ref is None:
                return self._capture_by_bounds(window)

            # Convert CGImage to PIL Image
            width = Quartz.CGImageGetWidth(image_ref)
            height = Quartz.CGImageGetHeight(image_ref)
            bytes_per_row = Quartz.CGImageGetBytesPerRow(image_ref)

            # Get pixel data
            data_provider = Quartz.CGImageGetDataProvider(image_ref)
            data = Quartz.CGDataProviderCopyData(data_provider)

            # Create PIL image from raw data
            img = Image.frombytes("RGBA", (width, height), data, "raw", "BGRA", bytes_per_row, 1)
            return img.convert("RGB")

        except Exception:
            # Fallback to bounds-based capture
            return self._capture_by_bounds(window)

    def _capture_by_bounds(self, window: WindowInfo) -> Optional[Image.Image]:
        """Fallback capture using screen region."""
        try:
            with mss.mss() as sct:
                monitor = {
                    "left": window.x,
                    "top": window.y,
                    "width": window.width,
                    "height": window.height
                }
                screenshot = sct.grab(monitor)
                return Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
        except Exception:
            return None


class LinuxWindowManager:
    """Window management for Linux (X11) using wmctrl/xdotool."""

    def __init__(self):
        self.tool = self._detect_tool()
        if not self.tool:
            print("Error: Neither 'wmctrl' nor 'xdotool' found.")
            print("Install with: sudo apt install wmctrl")
            sys.exit(1)

    def _detect_tool(self) -> Optional[str]:
        for tool in ["wmctrl", "xdotool"]:
            try:
                subprocess.run([tool, "--version"], capture_output=True, check=True)
                return tool
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue
        return None

    def get_windows(self) -> list[WindowInfo]:
        windows = []
        if self.tool == "wmctrl":
            result = subprocess.run(["wmctrl", "-l", "-G"], capture_output=True, text=True)
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                parts = line.split(None, 8)
                if len(parts) >= 8:
                    wid, desktop, x, y, w, h, hostname, *title_parts = parts
                    title = " ".join(title_parts) if title_parts else "(unnamed)"
                    if desktop == "-1" or not title.strip():
                        continue
                    try:
                        windows.append(WindowInfo(
                            id=wid, title=title,
                            x=int(x), y=int(y), width=int(w), height=int(h)
                        ))
                    except ValueError:
                        continue
        return windows

    def focus_window(self, window: WindowInfo) -> bool:
        try:
            if self.tool == "wmctrl":
                subprocess.run(["wmctrl", "-i", "-a", window.id], check=True)
            else:
                subprocess.run(["xdotool", "windowactivate", window.id], check=True)
            return True
        except subprocess.CalledProcessError:
            return False

    def capture_window(self, window: WindowInfo) -> Optional[Image.Image]:
        """Capture window screenshot with multiple fallback methods."""
        import tempfile
        import os

        # Method 1: ImageMagick import
        try:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp_path = tmp.name
            result = subprocess.run(
                ["import", "-window", window.id, tmp_path],
                capture_output=True, timeout=10
            )
            if result.returncode == 0 and os.path.exists(tmp_path):
                img = Image.open(tmp_path)
                img.load()
                os.unlink(tmp_path)
                return img.copy()
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            pass

        # Method 2: scrot
        try:
            self.focus_window(window)
            time.sleep(0.2)
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp_path = tmp.name
            result = subprocess.run(
                ["scrot", "-u", tmp_path],
                capture_output=True, timeout=10
            )
            if result.returncode == 0 and os.path.exists(tmp_path):
                img = Image.open(tmp_path)
                img.load()
                os.unlink(tmp_path)
                return img.copy()
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            pass

        # Method 3: mss with bounds clamping
        try:
            with mss.mss() as sct:
                screen = sct.monitors[0]
                x = max(0, window.x)
                y = max(0, window.y)
                width = min(window.width, screen["width"] - x)
                height = min(window.height, screen["height"] - y)
                if width <= 0 or height <= 0:
                    return None
                monitor = {"left": x, "top": y, "width": width, "height": height}
                screenshot = sct.grab(monitor)
                return Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
        except Exception:
            return None


def get_window_manager():
    """Get the appropriate window manager for the current platform."""
    if platform.system() == "Darwin":
        return MacWindowManager()
    else:
        return LinuxWindowManager()


# ═══════════════════════════════════════════════════════════════════════════════
# API Client
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class PokerAnalysis:
    """Results from the poker analysis API."""
    success: bool
    hole_cards: list[str]
    community_cards: list[str]
    opponents: int
    win_rate: float
    lose_rate: float
    tie_rate: float
    our_hand_probabilities: dict[str, float]
    opponent_hand_probabilities: dict[str, float]
    error_message: Optional[str] = None

    @classmethod
    def from_error(cls, message: str) -> "PokerAnalysis":
        return cls(
            success=False,
            hole_cards=[],
            community_cards=[],
            opponents=0,
            win_rate=0, lose_rate=0, tie_rate=0,
            our_hand_probabilities={},
            opponent_hand_probabilities={},
            error_message=message
        )

    @classmethod
    def from_api_response(cls, data: dict) -> "PokerAnalysis":
        if not data.get("success", False):
            return cls.from_error(data.get("error", "Unknown API error"))

        result = data.get("data", {})
        return cls(
            success=True,
            hole_cards=result.get("hole_cards", []),
            community_cards=result.get("community_cards", []),
            opponents=result.get("opponents", 0),
            win_rate=result.get("win_rate", 0),
            lose_rate=result.get("lose_rate", 0),
            tie_rate=result.get("tie_rate", 0),
            our_hand_probabilities=result.get("our_hand_probabilities", {}),
            opponent_hand_probabilities=result.get("opponent_hand_probabilities", {})
        )


def analyze_screenshot(image: Image.Image, opponents: int, license_key: str, image_quality: int) -> PokerAnalysis:
    """Send screenshot to API and return analysis results."""
    try:
        # Convert image to JPEG
        img_buffer = io.BytesIO()
        image.save(img_buffer, format="JPEG", quality=image_quality)
        img_buffer.seek(0)

        # Make API request
        response = requests.post(
            API_URL,
            headers={
                "X-License-Key": license_key,
            },
            files={"image": ("screenshot.jpg", img_buffer, "image/jpeg")},
            data={"opponents": str(opponents)},
            timeout=30
        )

        if response.status_code != 200:
            # Try to get error message from response body
            try:
                error_data = response.json()
                error_msg = error_data.get("error") or error_data.get("message") or f"Status {response.status_code}"
                # Ensure error_msg is a string (API might return a dict)
                if not isinstance(error_msg, str):
                    error_msg = str(error_msg)
            except Exception:
                error_msg = f"API returned status {response.status_code}"
            return PokerAnalysis.from_error(error_msg)

        return PokerAnalysis.from_api_response(response.json())

    except requests.exceptions.Timeout:
        return PokerAnalysis.from_error("API request timed out")
    except requests.exceptions.RequestException as e:
        return PokerAnalysis.from_error(f"Network error: {e}")
    except Exception as e:
        return PokerAnalysis.from_error(f"Error: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# Terminal UI
# ═══════════════════════════════════════════════════════════════════════════════

def create_card_art(card: str) -> list[Text]:
    """Create ASCII art lines for a single card."""
    if len(card) < 2:
        return [Text(card)]

    rank = card[:-1].upper()
    # Convert "T" to "10" for display
    if rank == "T":
        rank = "10"
    suit = card[-1].lower()
    symbol = SUIT_SYMBOLS.get(suit, suit)
    color = SUIT_COLORS.get(suit, "white")

    # Pad rank to 2 chars for alignment (10 is two chars)
    rank_left = f"{rank:<2}"
    rank_right = f"{rank:>2}"

    lines = []

    # Top border
    line = Text()
    line.append("┌─────┐", style="white")
    lines.append(line)

    # Rank top-left
    line = Text()
    line.append("│", style="white")
    line.append(rank_left, style="bold white")
    line.append("   ", style="white")
    line.append("│", style="white")
    lines.append(line)

    # Suit in center
    line = Text()
    line.append("│", style="white")
    line.append(f"  {symbol}  ", style=f"bold {color}")
    line.append("│", style="white")
    lines.append(line)

    # Rank bottom-right
    line = Text()
    line.append("│", style="white")
    line.append("   ", style="white")
    line.append(rank_right, style="bold white")
    line.append("│", style="white")
    lines.append(line)

    # Bottom border
    line = Text()
    line.append("└─────┘", style="white")
    lines.append(line)

    return lines


def format_cards(cards: list[str], label: str) -> Panel:
    """Create a panel displaying cards as ASCII art."""
    if not cards:
        content = Text("No cards detected", style="dim italic")
        return Panel(content, title=f"[bold cyan]{label}[/]", border_style="cyan")

    # Get ASCII art for each card
    card_arts = [create_card_art(card) for card in cards]

    # Combine cards side by side
    num_lines = len(card_arts[0])
    combined = Text()

    for line_idx in range(num_lines):
        if line_idx > 0:
            combined.append("\n")
        for card_idx, art in enumerate(card_arts):
            if card_idx > 0:
                combined.append("  ")  # Space between cards
            combined.append_text(art[line_idx])

    return Panel(combined, title=f"[bold cyan]{label}[/]", border_style="cyan")


class WinRateBar:
    """A dynamic-width bar showing win/tie/lose rates."""

    def __init__(self, win_rate: float, tie_rate: float, lose_rate: float):
        self.win_rate = win_rate
        self.tie_rate = tie_rate
        self.lose_rate = lose_rate

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        width = options.max_width

        win_blocks = int(width * self.win_rate)
        tie_blocks = int(width * self.tie_rate)
        lose_blocks = width - win_blocks - tie_blocks

        bar = Text()
        bar.append("█" * win_blocks, style="bold green")
        bar.append("█" * tie_blocks, style="bold yellow")
        bar.append("█" * lose_blocks, style="bold red")

        yield bar

    def __rich_measure__(self, console: Console, options: ConsoleOptions) -> Measurement:
        return Measurement(1, options.max_width)


class WinRateDisplay:
    """A complete win rate display with dynamic-width bar and labels."""

    def __init__(self, win_rate: float, tie_rate: float, lose_rate: float):
        self.win_rate = win_rate
        self.tie_rate = tie_rate
        self.lose_rate = lose_rate

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        width = options.max_width
        win_pct = int(self.win_rate * 100)
        tie_pct = int(self.tie_rate * 100)
        lose_pct = int(self.lose_rate * 100)

        # Create dynamic bar
        win_blocks = int(width * self.win_rate)
        tie_blocks = int(width * self.tie_rate)
        lose_blocks = width - win_blocks - tie_blocks

        bar = Text()
        bar.append("█" * win_blocks, style="bold green")
        bar.append("█" * tie_blocks, style="bold yellow")
        bar.append("█" * lose_blocks, style="bold red")

        yield Text()
        yield bar
        yield Text()

        # Create centered labels
        labels = Text()
        labels.append(f"  WIN:  {win_pct:>3}%", style="bold green")
        labels.append("   ")
        labels.append(f"TIE:  {tie_pct:>3}%", style="bold yellow")
        labels.append("   ")
        labels.append(f"LOSE: {lose_pct:>3}%", style="bold red")

        yield labels

    def __rich_measure__(self, console: Console, options: ConsoleOptions) -> Measurement:
        return Measurement(1, options.max_width)


def create_win_rate_display(analysis: PokerAnalysis) -> Panel:
    """Create a visual win rate display."""
    if not analysis.success:
        return Panel(
            Text(analysis.error_message or "Error", style="red"),
            title="[bold red]Error[/]",
            border_style="red"
        )

    return Panel(
        WinRateDisplay(analysis.win_rate, analysis.tie_rate, analysis.lose_rate),
        title="[bold white]Win Probability[/]",
        border_style="white"
    )


def create_hand_probabilities_table(our_probs: dict[str, float], opp_probs: dict[str, float]) -> Panel:
    """Create a table showing hand probabilities for both player and opponent."""
    table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
    table.add_column("Hand", style="cyan", width=16)
    table.add_column("You", justify="right", width=6)
    table.add_column("", width=20)
    table.add_column("Opp", justify="right", width=6)
    table.add_column("", width=20)

    def get_style(prob: float) -> str:
        if prob > 0.3:
            return "green"
        elif prob > 0.1:
            return "yellow"
        return "dim"

    bar_width = 18
    for hand in POKER_HANDS:
        our_prob = our_probs.get(hand, 0.0)
        opp_prob = opp_probs.get(hand, 0.0)

        our_pct = our_prob * 100
        opp_pct = opp_prob * 100

        our_bar_len = int(our_prob * bar_width)
        opp_bar_len = int(opp_prob * bar_width)

        our_bar = "▓" * our_bar_len + "░" * (bar_width - our_bar_len)
        opp_bar = "▓" * opp_bar_len + "░" * (bar_width - opp_bar_len)

        table.add_row(
            hand,
            Text(f"{our_pct:.1f}%", style=get_style(our_prob)),
            Text(our_bar, style=get_style(our_prob)),
            Text(f"{opp_pct:.1f}%", style=get_style(opp_prob)),
            Text(opp_bar, style=get_style(opp_prob)),
        )

    return Panel(table, title="[bold magenta]Hand Probabilities[/]", border_style="magenta")


def create_status_bar(window_title: str, opponents: int, iteration: int) -> Text:
    """Create a status bar."""
    text = Text()
    text.append(f"Window: ", style="dim")
    text.append(window_title[:30], style="white")
    text.append("  │  ", style="dim")
    text.append(f"Opponents (↑↓): ", style="dim")
    text.append(str(opponents), style="bold yellow")
    text.append("  │  ", style="dim")
    text.append(f"Scan #", style="dim")
    text.append(str(iteration), style="green")
    text.append("  │  ", style="dim")
    text.append("Ctrl+C", style="bold cyan")
    text.append(" exit", style="dim")
    return text


def build_display(analysis: PokerAnalysis, window_title: str, opponents: int, iteration: int) -> Layout:
    """Build the complete display layout."""
    layout = Layout()

    # Create main sections
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="cards", size=7),
        Layout(name="main", ratio=1),
        Layout(name="footer", size=1)
    )

    # Header
    layout["header"].update(Panel(
        create_status_bar(window_title, opponents, iteration),
        style="on grey11",
        title="[bold white]Automatic Poker Odds Calculator[/] [bold red]♥[/] [bold blue]♦[/] [bold green]♣[/] [bold white]♠[/]",
    ))

    # Cards section
    cards_layout = Layout()
    cards_layout.split_row(
        Layout(format_cards(analysis.hole_cards, "Your Hole Cards")),
        Layout(format_cards(analysis.community_cards, "Community Cards"), ratio=2)
    )
    layout["cards"].update(cards_layout)

    # Main section with probabilities and win rate stacked vertically
    main_layout = Layout()
    main_layout.split_column(
        Layout(create_hand_probabilities_table(
            analysis.our_hand_probabilities,
            analysis.opponent_hand_probabilities
        ), ratio=3),
        Layout(create_win_rate_display(analysis), ratio=1),
    )
    layout["main"].update(main_layout)

    # Footer
    layout["footer"].update(Text(""))

    return layout

# Shared state
opponents = 1
running = True

def keyboard_listener():
    global opponents, running
    while running:
        key = readchar.readkey()
        if key == readchar.key.UP and opponents < 9:
            opponents += 1
        elif key == readchar.key.DOWN and opponents > 1:
            opponents -= 1


# ═══════════════════════════════════════════════════════════════════════════════
# Window Selection UI
# ═══════════════════════════════════════════════════════════════════════════════

def select_window() -> Optional[WindowInfo]:
    """Let user select a window interactively."""
    console = Console()
    console.print("\n[bold white]Automatic Poker Odds Calculator[/] [bold red]♥[/] [bold blue]♦[/] [bold green]♣[/] [bold white]♠[/]")
    console.print("=" * 40)
    console.print(f"Platform: {platform.system()}\n")

    wm = get_window_manager()

    console.print("Scanning for windows...")
    windows = wm.get_windows()

    if not windows:
        console.print("[red]No visible windows found![/]")
        return None

    console.print(f"Found {len(windows)} windows.\n")

    # Create choices
    choices = []
    for i, win in enumerate(windows):
        title = win.title[:50] + "..." if len(win.title) > 50 else win.title
        label = f"{title} ({win.width}x{win.height})"
        choices.append(questionary.Choice(title=label, value=i))

    choices.append(questionary.Choice(title="❌ Cancel", value=-1))

    style = Style([
        ("qmark", "fg:cyan bold"),
        ("question", "fg:white bold"),
        ("answer", "fg:green bold"),
        ("pointer", "fg:cyan bold"),
        ("highlighted", "fg:cyan bold"),
    ])

    selected = questionary.select(
        "Select the poker client window:",
        choices=choices,
        style=style,
        use_arrow_keys=True,
    ).ask()

    if selected is None or selected == -1:
        return None

    return windows[selected]


# ═══════════════════════════════════════════════════════════════════════════════
# Main Application
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    # 1 second scan interval
    scan_interval = 1.0

    # Get license key (from file or prompt user)
    license_key = get_license_key()

    # Get ideal image quality from API
    image_quality = get_image_quality()

    console = Console()

    # Select window
    window = select_window()
    if not window:
        console.print("\n[yellow]Cancelled.[/]")
        return

    console.print(f"\n[green]✓[/] Selected window: [cyan]{window.title}[/]")
    console.print("\n[dim]Starting in 2 seconds... Press Ctrl+C to stop.[/]\n")
    time.sleep(2)

    # Initialize window manager for capturing
    wm = get_window_manager()

    # Main loop with live display
    iteration = 0
    last_analysis = PokerAnalysis.from_error("Waiting for first scan...")

    try:
        # Start keyboard thread
        thread = threading.Thread(target=keyboard_listener, daemon=True)
        thread.start()
        with Live(console=console, refresh_per_second=10, screen=True) as live:
            while True:
                loop_start = time.time()
                iteration += 1

                # Capture screenshot
                screenshot = wm.capture_window(window)

                if screenshot is None:
                    last_analysis = PokerAnalysis.from_error("Failed to capture window")
                else:
                    # Send to API
                    last_analysis = analyze_screenshot(screenshot, opponents, license_key, image_quality)

                # Update display
                display = build_display(last_analysis, window.title, opponents, iteration)
                live.update(display)

                # Sleep only the remaining time to maintain scan interval
                elapsed = time.time() - loop_start
                sleep_time = max(0, scan_interval - elapsed)
                if sleep_time > 0:
                    time.sleep(sleep_time)

    except KeyboardInterrupt:
        pass

    console.print("\n[yellow]Stopped.[/]")


if __name__ == "__main__":
    main()

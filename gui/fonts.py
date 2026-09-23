"""Platform-aware fonts used by the Tk GUI."""

import sys


# Microsoft YaHei is normally unavailable on Linux.  An explicit CJK font
# avoids Tk selecting a poor fallback from the desktop font configuration.
UI_FONT = "Microsoft YaHei" if sys.platform == "win32" else "Noto Sans CJK SC"

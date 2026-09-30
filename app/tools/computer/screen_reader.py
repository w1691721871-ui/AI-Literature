"""Privacy-safe screen connector contract; does not capture screenshots."""


class ScreenReader:
    name = "screen_reader"
    description = "Reports connector availability only. It does not store screenshots or inspect user-private windows."

    def observe(self) -> dict[str, object]:
        return {"status": "not_connected", "screen_state": "no_screen_data", "current_window": None, "available_actions": [], "boundary": "当前版本不采集屏幕、窗口内容或用户隐私截图。"}

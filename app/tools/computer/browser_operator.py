"""Browser Computer Tool boundary: never fabricates state when no connector exists."""

class BrowserOperator:
    name = "browser_operator"
    def open_page(self, url: str) -> dict[str, object]: return self._not_connected(url)
    def inspect_page(self, url: str) -> dict[str, object]: return self._not_connected(url)
    def capture_state(self, url: str) -> dict[str, object]: return self._not_connected(url)
    def extract_content(self, url: str) -> dict[str, object]: return self._not_connected(url)
    @staticmethod
    def _not_connected(url: str) -> dict[str, object]:
        return {"status": "BROWSER_NOT_CONNECTED", "url": url, "boundary": "当前服务未接入受控浏览器，不生成截图、页面内容或浏览器操作结果。"}

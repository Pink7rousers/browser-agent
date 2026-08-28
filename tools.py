# tools.py (同步版本)
from playwright.sync_api import sync_playwright, Browser, Page
from langchain_core.tools import tool
import os

_browser: Browser = None
_page: Page = None

def get_page() -> Page:
    global _browser, _page
    if _page is None:
        playwright = sync_playwright().start()
        _browser = playwright.chromium.launch(headless=True)  # headless=False 可查看浏览器
        _page = _browser.new_page()
    return _page

def close_browser():
    global _browser, _page
    if _browser:
        _browser.close()
        _browser = None
        _page = None

@tool
def goto(url: str) -> str:
    """导航到指定 URL。参数：url（完整网址，需包含 http:// 或 https://）"""
    page = get_page()
    page.goto(url, timeout=30000, wait_until="networkidle")
    return f"已导航到 {url}，标题：{page.title()}"

@tool
def click(selector: str) -> str:
    """点击页面元素。参数：selector（CSS 选择器）"""
    page = get_page()
    try:
        page.click(selector, timeout=10000)
        return f"成功点击 {selector}"
    except Exception as e:
        return f"点击失败：{e}"

@tool
def type_text(selector: str, text: str) -> str:
    """在输入框输入文本。参数：selector，text"""
    page = get_page()
    try:
        page.wait_for_selector(selector, timeout=15000)
        page.fill(selector, text, timeout=10000)
        return f"已在 {selector} 输入：{text}"
    except Exception as e:
        return f"输入失败：{e}"

@tool
def wait_for_selector(selector: str, timeout: int = 15000) -> str:
    """等待指定元素出现在页面中。参数：selector（CSS选择器），timeout（毫秒，默认15000）"""
    page = get_page()
    try:
        page.wait_for_selector(selector, timeout=timeout)
        return f"元素 {selector} 已出现"
    except Exception as e:
        return f"等待超时：{e}"

@tool
def scroll(direction: str = "down") -> str:
    """滚动页面。参数：direction（'up' 或 'down'）"""
    page = get_page()
    if direction == "down":
        page.evaluate("window.scrollBy(0, window.innerHeight)")
    else:
        page.evaluate("window.scrollBy(0, -window.innerHeight)")
    return f"页面已向{direction}滚动"

@tool
def extract_text(selector: str = None) -> str:
    """提取页面文本。可选 selector 指定元素，否则提取整个 body 文本（截断 3000 字符）"""
    page = get_page()
    if selector:
        try:
            element = page.query_selector(selector)
            text = element.inner_text() if element else "元素不存在"
        except Exception as e:
            text = f"提取失败：{e}"
    else:
        text = page.inner_text("body")[:3000]
    return text

@tool
def get_current_url() -> str:
    """获取当前页面 URL"""
    return get_page().url

@tool
def screenshot(path: str = "screenshot.png") -> str:
    """保存截图。参数：path"""
    get_page().screenshot(path=path)
    return f"截图已保存至 {path}"

browser_tools = [goto, click, type_text, wait_for_selector, scroll, extract_text, get_current_url, screenshot]

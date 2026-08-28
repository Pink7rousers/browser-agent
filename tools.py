import os
import re
import uuid
from typing import Optional, Dict
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page
from langchain_core.tools import tool
from dotenv import load_dotenv

load_dotenv()

# 全局浏览器实例
_browser: Optional[Browser] = None
_context: Optional[BrowserContext] = None
_pages: Dict[str, Page] = {}
_current_page_id: Optional[str] = None

# 安全域名白名单（空列表表示不限制）
_allowed_domains: list = []
# 是否无头模式
_headless = os.getenv("HEADLESS", "true").lower() == "true"

def set_allowed_domains(domains: list):
    global _allowed_domains
    _allowed_domains = domains

def _is_url_allowed(url: str) -> bool:
    if not _allowed_domains:
        return True
    match = re.search(r'https?://([^/]+)', url)
    if match:
        host = match.group(1)
        return any(host == d or host.endswith('.' + d) for d in _allowed_domains)
    return False

def get_page(page_id: Optional[str] = None) -> Page:
    global _browser, _context, _pages, _current_page_id
    if _browser is None:
        playwright = sync_playwright().start()
        _browser = playwright.chromium.launch(headless=_headless)
        _context = _browser.new_context()
        _pages["default"] = _context.new_page()
        _current_page_id = "default"
    if page_id is None:
        page_id = _current_page_id
    if page_id not in _pages:
        _pages[page_id] = _context.new_page()
    _current_page_id = page_id
    return _pages[page_id]

def close_browser():
    global _browser, _context, _pages, _current_page_id
    if _browser:
        _browser.close()
        _browser = None
        _context = None
        _pages = {}
        _current_page_id = None

# ---------- 基础工具 ----------
@tool
def goto(url: str, page_id: str = None) -> str:
    """导航到指定 URL。参数：url（完整网址），page_id（可选，页签标识）"""
    if not _is_url_allowed(url):
        return f"拒绝访问：域名 {url} 不在白名单中"
    page = get_page(page_id)
    try:
        page.goto(url, timeout=30000, wait_until="networkidle")
        return f"已导航到 {url}，标题：{page.title()}"
    except Exception as e:
        return f"导航失败：{e}"

@tool
def click(selector: str, page_id: str = None) -> str:
    """点击页面元素。参数：selector（CSS选择器），page_id（可选）"""
    page = get_page(page_id)
    try:
        page.click(selector, timeout=10000)
        return f"成功点击 {selector}"
    except Exception as e:
        return f"点击失败：{e}"

@tool
def type_text(selector: str, text: str, page_id: str = None) -> str:
    """在输入框输入文本。selector 可以是单个选择器，或逗号分隔的多个备选选择器（依次尝试）"""
    page = get_page(page_id)
    selectors = [s.strip() for s in selector.split(',')]
    last_error = ""
    for sel in selectors:
        try:
            page.wait_for_selector(sel, timeout=10000)  # 每个选择器等待10秒
            page.fill(sel, text, timeout=10000)
            return f"已在 {sel} 输入：{text}"
        except Exception as e:
            last_error = f"{sel}: {e}"
            continue
    # 所有备选都失败，返回页面信息
    try:
        title = page.title()
        url = page.url
        body = page.inner_text("body")[:300]
    except:
        title, url, body = "未知", "未知", ""
    return f"输入失败。尝试的选择器：{selectors}\n错误：{last_error}\n当前页面：标题={title}, URL={url}\n页面文本片段：{body}"

@tool
def get_page_info(page_id: str = None) -> str:
    """获取当前页面的标题、URL和可见文本片段（前500字符）"""
    page = get_page(page_id)
    try:
        title = page.title()
        url = page.url
        text = page.inner_text("body")[:500]
        return f"标题：{title}\nURL：{url}\n文本片段：{text}"
    except Exception as e:
        return f"获取页面信息失败：{e}"

@tool
def scroll(direction: str = "down", page_id: str = None) -> str:
    """滚动页面。参数：direction（'up'/'down'），page_id（可选）"""
    page = get_page(page_id)
    if direction == "down":
        page.evaluate("window.scrollBy(0, window.innerHeight)")
    else:
        page.evaluate("window.scrollBy(0, -window.innerHeight)")
    return f"页面已向{direction}滚动"

@tool
def extract_text(selector: str = None, page_id: str = None) -> str:
    """提取页面文本。可选 selector，否则提取 body 文本（截断3000字符）"""
    page = get_page(page_id)
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
def get_current_url(page_id: str = None) -> str:
    """获取当前页面 URL"""
    page = get_page(page_id)
    return page.url

@tool
def screenshot(path: str = "screenshot.png", page_id: str = None) -> str:
    """保存截图。参数：path，page_id（可选）"""
    page = get_page(page_id)
    try:
        page.screenshot(path=path)
        return f"截图已保存至 {path}"
    except Exception as e:
        return f"截图失败：{e}"

# ---------- 扩展工具 ----------
@tool
def wait(selector: str, timeout: int = 15000, page_id: str = None) -> str:
    """等待元素出现。参数：selector，timeout（毫秒），page_id（可选）"""
    page = get_page(page_id)
    try:
        page.wait_for_selector(selector, timeout=timeout)
        return f"元素 {selector} 已出现"
    except Exception as e:
        return f"等待超时：{e}"

@tool
def press_key(key: str, selector: str = None, page_id: str = None) -> str:
    """按下键盘按键。参数：key（如 'Enter'），selector（可选，先聚焦该元素），page_id（可选）"""
    page = get_page(page_id)
    try:
        if selector:
            page.focus(selector)
        page.keyboard.press(key)
        return f"已按下按键 {key}"
    except Exception as e:
        return f"按键失败：{e}"

@tool
def select_option(selector: str, value: str = None, label: str = None, page_id: str = None) -> str:
    """在下拉框中选择选项。参数：selector，value，label（二选一），page_id（可选）"""
    page = get_page(page_id)
    try:
        if value:
            page.select_option(selector, value=value)
        elif label:
            page.select_option(selector, label=label)
        else:
            return "必须提供 value 或 label"
        return f"已选择 {selector} 中的选项"
    except Exception as e:
        return f"选择失败：{e}"

@tool
def get_attribute(selector: str, attribute: str, page_id: str = None) -> str:
    """获取元素属性值。参数：selector，attribute，page_id（可选）"""
    page = get_page(page_id)
    try:
        element = page.query_selector(selector)
        if element:
            value = element.get_attribute(attribute)
            return f"{selector} 的 {attribute} = {value}"
        else:
            return "元素不存在"
    except Exception as e:
        return f"获取属性失败：{e}"

@tool
def new_page(page_id: str = None) -> str:
    """创建新页签并切换到它。参数：page_id（可选，新页签标识）"""
    global _current_page_id
    if page_id is None:
        page_id = str(uuid.uuid4())[:8]
    page = get_page(page_id)
    _current_page_id = page_id
    return f"已创建/切换到页签：{page_id}"

@tool
def switch_page(page_id: str) -> str:
    """切换到指定页签。参数：page_id"""
    global _current_page_id
    if page_id in _pages:
        _current_page_id = page_id
        return f"已切换到页签 {page_id}"
    else:
        return f"页签 {page_id} 不存在"

@tool
def close_page(page_id: str = None) -> str:
    """关闭页签。参数：page_id（可选，默认当前页）"""
    global _current_page_id
    if page_id is None:
        page_id = _current_page_id
    if page_id in _pages:
        _pages[page_id].close()
        del _pages[page_id]
        if _current_page_id == page_id:
            _current_page_id = next(iter(_pages)) if _pages else None
        return f"页签 {page_id} 已关闭"
    else:
        return f"页签 {page_id} 不存在"

# 可选：人工干预工具（处理验证码等）
@tool
def human_input(prompt: str) -> str:
    """请求人工输入。参数：prompt（提示信息）"""
    print(f"\n[人工介入] {prompt}")
    return input("请输入：")

# 汇总所有工具
browser_tools = [
    goto, click, type_text, scroll, extract_text, get_current_url, screenshot,
    wait, press_key, select_option, get_attribute,
    new_page, switch_page, close_page,
    get_page_info, human_input   # 按需启用
]

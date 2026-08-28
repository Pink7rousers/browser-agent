import sys
import io
sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from agent import app, close_browser, load_state, save_state
from state import BrowserAgentState
from tools import set_allowed_domains
from dotenv import load_dotenv
import os

load_dotenv()

def main():
    # 可选：设置安全域名白名单
    allowed = os.getenv("ALLOWED_DOMAINS", "")  # 逗号分隔
    if allowed:
        set_allowed_domains([d.strip() for d in allowed.split(",")])
    
    # 可选：是否可视化
    headless = os.getenv("HEADLESS", "true").lower() == "true"
    # 注意：headless 设置在 tools.py 中硬编码，可改为全局变量

    task = input("请输入浏览器自动化任务：")
    save_path = input("是否保存状态到文件？（留空则不保存）")
    save_path = save_path.strip() or None

    # 尝试加载已有状态
    if save_path and os.path.exists(save_path):
        resume = input(f"发现状态文件 {save_path}，是否继续上次任务？(y/n)").lower() == 'y'
        if resume:
            state = load_state(save_path)
            if state:
                print("已加载上次状态，继续执行...")
                result = app.invoke(state)
                print_result(result)
                return
    
    initial_state = {
        "task": task,
        "history": [],
        "current_page_id": "default",
        "pages": {},
        "done": False,
        "final_answer": "",
        "step_count": 0,
        "max_steps": 20,
        "save_path": save_path
    }
    try:
        result = app.invoke(initial_state)
        print_result(result)
    finally:
        close_browser()

def print_result(result):
    print("\n" + "="*50)
    print("任务结果：")
    print(result.get("final_answer", "未能完成任务"))
    print("\n执行步骤：")
    for i, h in enumerate(result["history"]):
        print(f"{i+1}. {h['action']} -> {str(h['observation'])[:100]}")

if __name__ == "__main__":
    main()

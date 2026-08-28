import sys
import io
sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from agent import app, close_browser
from state import BrowserAgentState
from dotenv import load_dotenv

load_dotenv()

def main():
    task = input("请输入浏览器自动化任务：")
    initial_state = {
        "task": task,
        "history": [],
        "current_url": "",
        "page_text": "",
        "done": False,
        "final_answer": "",
        "step_count": 0,
        "max_steps": 15  # 最大步骤数，防止无限循环
    }
    print(f"\n开始执行任务：{task}\n")
    try:
        result = app.invoke(initial_state)
        print("\n" + "="*50)
        print("任务结果：")
        print(result.get("final_answer", "未能完成任务"))
        print("\n执行步骤：")
        for i, h in enumerate(result["history"]):
            print(f"{i+1}. {h['action']} -> {h['observation'][:100]}")
    finally:
        close_browser()  # 确保关闭浏览器

if __name__ == "__main__":
    main()

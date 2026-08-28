from typing import TypedDict, List, Dict, Any

class BrowserAgentState(TypedDict):
    task: str                          # 用户任务
    history: List[Dict[str, Any]]      # 历史操作记录，每条包含 action, args, observation
    current_url: str                   # 当前浏览器 URL
    page_text: str                     # 当前页面可见文本（截断）
    done: bool                         # 任务是否完成
    final_answer: str                  # 最终结果
    step_count: int                    # 已执行步数
    max_steps: int                     # 最大步数限制

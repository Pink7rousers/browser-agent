from typing import TypedDict, List, Dict, Any, Optional

class BrowserAgentState(TypedDict):
    task: str
    history: List[Dict[str, Any]]       # 操作历史
    current_page_id: str                # 当前活动页签的标识
    pages: Dict[str, str]               # 页签标识到页面 URL 的映射（简化）
    done: bool
    final_answer: str
    step_count: int
    max_steps: int
    # 持久化相关
    save_path: Optional[str]            # 可选，状态保存路径

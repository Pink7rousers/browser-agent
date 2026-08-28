import json
import os
from typing import Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END
from state import BrowserAgentState
from tools import browser_tools, close_browser, set_allowed_domains, _allowed_domains
from dotenv import load_dotenv

load_dotenv()

llm = ChatOpenAI(
    model="deepseek-chat",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com/v1",
    temperature=0,
    request_timeout=60
)

llm_with_tools = llm.bind_tools(browser_tools)

SYSTEM_PROMPT = """你是一个浏览器自动化助手，能够根据用户任务自主操作浏览器。
可用工具：goto, click, type_text, scroll, extract_text, get_current_url, screenshot, wait, press_key, select_option, get_attribute, new_page, switch_page, close_page, get_page_info, human_input。

**百度搜索示例**：
- 输入框选择器优先使用：`input[name="wd"], #kw`
- 搜索按钮选择器：`#su` 或直接按回车键（press_key 'Enter'）
- 等待搜索结果：`.result-op` 或 `.c-container`

**失败处理规则**：
- 如果 type_text 失败，调用 get_page_info 检查页面状态，并尝试使用不同选择器。
- 不要连续截图超过两次。

请遵循 ReAct 模式：先思考下一步动作，然后调用工具，观察结果，再继续。
当任务完成或无法继续时，请输出最终答案（纯文本），并停止调用工具。
注意：
1. 遇到操作失败时，先分析失败原因，可尝试截图或提取文本了解页面状态。
2. 对于搜索类任务，应等待搜索框出现后再输入。
3. 可以创建多个页签并行处理不同页面。
4. 所有输出均使用中文。
"""

def save_state(state: BrowserAgentState, path: str = "agent_state.json"):
    """将状态保存到 JSON 文件"""
    try:
        # 排除不可序列化的对象
        save_data = {
            "task": state.get("task"),
            "history": state.get("history", []),
            "done": state.get("done", False),
            "final_answer": state.get("final_answer", ""),
            "step_count": state.get("step_count", 0),
            "max_steps": state.get("max_steps", 15),
            "save_path": path
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"状态保存失败：{e}")

def load_state(path: str = "agent_state.json") -> Optional[BrowserAgentState]:
    """从 JSON 文件加载状态"""
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return BrowserAgentState(**data)

def agent_node(state: BrowserAgentState) -> dict:
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"用户任务：{state['task']}")
    ]
    if state["history"]:
        history_text = "\n".join([
            f"步骤{i+1}: 动作={h['action']}, 参数={h['args']}, 观察={h['observation']}"
            for i, h in enumerate(state["history"])
        ])
        messages.append(HumanMessage(content=f"历史操作：\n{history_text}"))
    messages.append(HumanMessage(content="请决定下一步动作，或给出最终答案。"))

    response = llm_with_tools.invoke(messages)
    if response.tool_calls:
        tool_call = response.tool_calls[0]
        new_history = state["history"] + [{
            "action": tool_call["name"],
            "args": tool_call["args"],
            "observation": None
        }]
        return {
            "history": new_history,
            "step_count": state["step_count"] + 1,
            "done": False,
            "final_answer": ""
        }
    else:
        return {
            "history": state["history"],
            "step_count": state["step_count"] + 1,
            "done": True,
            "final_answer": response.content
        }

def tool_node(state: BrowserAgentState) -> dict:
    last = state["history"][-1]
    tool_name = last["action"]
    args = last["args"]
    tool_func = next((t for t in browser_tools if t.name == tool_name), None)
    if tool_func is None:
        observation = f"未知工具：{tool_name}"
    else:
        try:
            observation = tool_func.invoke(args)
        except Exception as e:
            observation = f"工具执行出错：{e}"
    new_history = state["history"].copy()
    new_history[-1]["observation"] = observation
    # 执行后自动保存状态（可选）
    if state.get("save_path"):
        save_state({**state, "history": new_history}, state["save_path"])
    return {"history": new_history}

def should_continue(state: BrowserAgentState) -> str:
    if state.get("done", False):
        return "end"
    elif state["step_count"] >= state.get("max_steps", 15):
        return "end"
    else:
        return "continue"

def build_graph():
    workflow = StateGraph(BrowserAgentState)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tool", tool_node)
    workflow.set_entry_point("agent")
    workflow.add_edge("agent", "tool")
    workflow.add_conditional_edges(
        "tool",
        should_continue,
        {"continue": "agent", "end": END}
    )
    return workflow.compile()

app = build_graph()

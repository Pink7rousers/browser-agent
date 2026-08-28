# agent.py (同步版本)
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END
from state import BrowserAgentState
from tools import browser_tools, close_browser
import os
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
可用工具：
- goto: 导航到指定网址
- click: 点击元素
- type_text: 输入文本
- scroll: 滚动页面
- extract_text: 提取页面文本
- get_current_url: 获取当前网址
- screenshot: 截图

当操作失败时，应该先检查页面状态（如提取文本、截图、获取当前 URL），判断是否需要等待或更换选择器。

对于搜索类任务，建议步骤：先 goto 到搜索引擎首页，然后使用 wait_for_selector 等待搜索框出现，再输入文本。

请逐步思考并调用工具完成任务。当任务完成或无法继续时，请输出最终答案（纯文本），并停止调用工具。
"""

def agent_node(state: BrowserAgentState) -> dict:
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"用户任务：{state['task']}")
    ]
    # 加入历史
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
    # 找到工具
    tool_func = next((t for t in browser_tools if t.name == tool_name), None)
    if tool_func is None:
        observation = f"未知工具：{tool_name}"
    else:
        try:
            observation = tool_func.invoke(args)  # 同步调用
        except Exception as e:
            observation = f"工具执行出错：{e}"
    new_history = state["history"].copy()
    new_history[-1]["observation"] = observation
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

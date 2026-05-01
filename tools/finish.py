import os
import yaml
import tempfile
from llama_index.core.tools import FunctionTool
from llama_index.core.workflow import Context

def get_finish_tool(ctx: Context, session_id: str) -> FunctionTool:
    async def finish(continue_task: bool, summary: str) -> str:
        """
        Finishes the current agent execution.
        Args:
            continue_task (bool): If True, indicates the task is not complete and needs to continue in a new context. If False, the task is completely finished.
            summary (str): A summary of the current task and a list of steps that have been taken in chronological order.
        """
        data = {
            "continue_task": continue_task,
            "summary": summary,
            "session_id": session_id
        }
        
        temp_dir = tempfile.gettempdir()
        file_path = os.path.join(temp_dir, f"agent_session_{session_id}.yaml")
        
        with open(file_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f)
            
        if continue_task:
            await ctx.set("continue_task", True)
            return "Task context saved to YAML. Ending current execution loop to continue in a new context."
        
        return "Task completed and summary saved to YAML."
        
    return FunctionTool.from_defaults(async_fn=finish)

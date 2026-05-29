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
        if continue_task:
            await ctx.set("continue_task", True)
            await ctx.set("session_summary", summary)
            return "Task context saved. Ending current execution loop to continue in a new context."
        
        await ctx.set("session_summary", summary)
        return "Task completed and summary saved."
        
    return FunctionTool.from_defaults(async_fn=finish)

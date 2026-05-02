import asyncio

from agent import InfiniteAgentWorkflow


async def main():
    workflow = InfiniteAgentWorkflow(timeout=3600.0)
    query = input("Enter prompt: ")
    response = await workflow.run(query=query)
    print(str(response))


if __name__ == "__main__":
    asyncio.run(main())

import asyncio
from agent import InfiniteAgentWorkflow


async def main():
    print("Initializing Agent Workflow...")
    workflow = InfiniteAgentWorkflow(timeout=3600.0)

    query = "Hello! Can you confirm you are connected?"
    print(f"\nSending Query: '{query}'")

    response = await workflow.run(query=query)

    print("\nFinal Response:")
    print(str(response))


if __name__ == "__main__":
    asyncio.run(main())

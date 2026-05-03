import asyncio
from tools.web_scrape import web_scrape

async def main():
    url = "https://www.google.com"
    print(f"Testing web_scrape with URL: {url}")
    try:
        result = await web_scrape(url)
        print("\n--- Result ---")
        print(result)
        print("--------------")
    except Exception as e:
        print(f"\nCaught unexpected exception in test script: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())

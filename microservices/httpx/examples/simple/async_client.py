import asyncio
import time

import httpx


async def main():
    async with httpx.AsyncClient(base_url='http://localhost:8001', timeout=5.0) as client:
        start = time.perf_counter()
        for task_id in range(1, 6):
            await client.get(f'/tasks/{task_id}')
        print(f'по очереди: {time.perf_counter() - start:.1f} с')

        start = time.perf_counter()
        responses = await asyncio.gather(*(client.get(f'/tasks/{task_id}') for task_id in range(1, 6)))
        print(f'параллельно: {time.perf_counter() - start:.1f} с')
        print([r.json()['title'] for r in responses])


asyncio.run(main())

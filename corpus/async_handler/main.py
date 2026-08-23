"""The field target: an async request handler, the shape a web framework
gives you. One task per request, a sync parse step, an await, a sync
summarise step, and a result that looks reasonable.

Seeded bug: `summarise` totals every item except the last, so both requests
come back with a total that is too low while reporting the right count. The
count and the total disagree with each other and with nothing else -- there
is no error, no traceback and no odd value; 27 is a perfectly plausible
total for three readings.

The debugging question is where the readings were lost: did the handler
ever hold all three, or did `parse` already drop one? That is a question
about a local variable inside a coroutine, in one of two concurrently
running tasks, which is the thing this arc made answerable.
"""
import asyncio

REQUESTS = ["12,15,18", "7,9"]


def parse(req):
    return [int(p) for p in req.split(",")]


def summarise(items):
    kept = items[:-1]           # BUG: the last item never reaches the total
    return {"count": len(items), "total": sum(kept)}


async def handle(req):
    items = parse(req)
    await asyncio.sleep(0)
    return summarise(items)


async def serve():
    tasks = [asyncio.create_task(handle(r), name=f"req-{i}")
             for i, r in enumerate(REQUESTS)]
    for r in await asyncio.gather(*tasks):
        print(f"count: {r['count']}  total: {r['total']}")


if __name__ == "__main__":
    asyncio.run(serve())

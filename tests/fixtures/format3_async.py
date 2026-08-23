"""Recorded by sensorium 0.3.0 (trace_format 3) -- BEFORE per-task
fingerprints existed. Its per-thread fingerprint covers every causal event
on the thread, task events included, and its `task_fingerprints` table is
empty. Tests pin that a newer reader says exactly that and claims nothing
more. Do not edit: the .db beside this file is the recording of THIS text.
"""
import asyncio


def step(task, n):
    return f"{task}:{n}"


async def worker(name):
    step(name, 1)
    await asyncio.sleep(0)
    return step(name, 2)


async def amain():
    a = asyncio.create_task(worker("A"), name="task-A")
    b = asyncio.create_task(worker("B"), name="task-B")
    return await asyncio.gather(a, b)


def main():
    print(asyncio.run(amain()))


main()

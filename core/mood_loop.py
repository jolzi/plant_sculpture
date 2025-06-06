# core/mood_loop.py
import asyncio, time
from core.mood import Mood               # your renamed file
from core.pubsub import Bus         # tiny asyncio pub/sub helper

TICK_HZ = 50                        # 20 ms timestep

async def run(bus: Bus,
              mood: Mood | None = None,
              hz: float = TICK_HZ):
    """
    • Pull fused sensor values from the bus (non-blocking).
    • Call mood.step(dt, stimuli) every 1/​hz seconds.
    • Publish the fresh snapshot so other tasks can subscribe.
    """
    mood = mood or Mood()
    dt   = 1.0 / hz
    stim_cache = {}

    async def _collect():
        async for topic, value in bus.subscribe(["stim.*"]):
            # e.g. topic = "stim.alarm"
            key = topic.split(".", 1)[1]
            stim_cache[key] = value

    asyncio.create_task(_collect())          # fan-in sensor events

    next_tick = time.perf_counter()
    while True:
        print(f"Next tick at {next_tick:.2f} seconds")
        mood.step(dt=dt, stimuli=stim_cache)
        await bus.publish("mood.snapshot", mood.snapshot)

        next_tick += dt
        await asyncio.sleep(max(0, next_tick - time.perf_counter()))

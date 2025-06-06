import asyncio
from typing import Any
from core.pubsub      import Bus
from core.mood_loop   import run as mood_task
#from core.behaviour   import run as behaviour_task
#from sensors.vision   import stream as vision_task
#from sensors.audio    import stream as audio_task
#from actuators.limbs  import run   as limbs_task

async def main():
    print("Starting plant sculpture system... (Press Ctrl+C to stop)")
    bus = Bus()
    # Setup bus logging: wrap the publish method to log snapshot events.
    orig_publish = bus.publish
    async def new_publish(topic: str, payload: Any):
        if topic == "mood.snapshot":
            print(f"[{asyncio.get_event_loop().time():.2f}s] Mood snapshot:", payload)
        return await orig_publish(topic, payload)
    bus.publish = new_publish
    try:
        print("Initializing mood system...")
        await asyncio.gather(
            mood_task(bus),                 # ← clock-tick & chemistry
            #behaviour_task(bus),            # ← picks patterns
            #limbs_task(bus),                # ← OSC to Teensy
            #vision_task(bus),               # ← publishes stim.alarm etc.
            #audio_task(bus),
        )
    except KeyboardInterrupt:
        print("\nKeyboard interrupt received. Shutting down...")
    finally:
        print("System stopped.")

if __name__ == "__main__":
    asyncio.run(main())

import asyncio

from watchgod import PythonWatcher, awatch

from natsapi.logger import logger


class Reloader:
    def __init__(self, target):
        self.target = target
        self.restarts = 0

    async def restart(self) -> None:
        self.process.cancel()
        self.process = asyncio.create_task(self.target())
        self.restarts += 1

    async def run(self):
        self.process = asyncio.create_task(self.target())
        async for changes in awatch(".", watcher_cls=PythonWatcher):

            logger.warn(f"WatchGodReload detected file change in {[c[1] for c in changes]}. Reloading...")
            await self.restart()

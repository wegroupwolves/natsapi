# import asyncio
#
#
# from pathlib import Path
#
# import pytest
#
# from natsapi import NatsAPI
# from natsapi.reload import Reloader
#
#
# @pytest.mark.skip(reason="no way of currently testing this, need another way.")
# async def test_reload_when_file_touch_should_succeed(caplog):
#     app = NatsAPI("natsapi.development")
#     p = Path("natsapi/logger.py")
#
#     r = Reloader(app.startup)
#     asyncio.create_task(r.run())
#     p.touch()
#     await asyncio.sleep(2)
#
#     logs = [str(x) for x in caplog.records]
#     print(len(logs))
#     assert r.restarts == 1
#     for x in logs:
#         print(logs)
#     assert "WatchGodReload detected file change in ['./natsapi/logger.py']. Reloading..." in logs

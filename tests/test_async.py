import asyncio
import aiohttp

import geocoder


address = '453 Booth Street, Ottawa'


def test_async_session():
    async def async_session():
        async with aiohttp.ClientSession() as session:
            g = await geocoder.async_get(address, provider='google', session=session)
            assert g.ok

    loop = asyncio.get_event_loop()
    loop.run_until_complete(async_session())

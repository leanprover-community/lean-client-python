#!/usr/bin/env python
from pathlib import Path
import sys

import trio # type: ignore

from lean_client.trio_server import TrioLeanServer

LEAN_TEST_PATH = Path(__file__).parent.joinpath('test.lean')

async def main():
    async with trio.open_nursery() as nursery:
        server = TrioLeanServer(nursery, debug=False)
        await server.start()
        await server.full_sync(LEAN_TEST_PATH)

        with LEAN_TEST_PATH.open() as test_lean:
            for i, line in enumerate(test_lean):
                before = await server.state(LEAN_TEST_PATH, i+1, 0)
                after = await server.state(LEAN_TEST_PATH, i+1, len(line) - 1)
                if before or after:
                    sys.stdout.write(f'Line {i+1}: {line}')
                    sys.stdout.write(f'State before:\n{before}\n\n')
                    sys.stdout.write(f'State after:\n{after}\n\n')

        server.kill()
        nursery.cancel_scope.cancel()

if __name__ == '__main__':
    trio.run(main)

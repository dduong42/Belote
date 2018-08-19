import asyncio


class BeloteProtocol(asyncio.Protocol):
    def __init__(self, queue):
        super().__init__()
        self.queue = queue

    def connection_made(self, transport):
        self.transport = transport
        self.queue.put_nowait(('connection', self.transport))

    def connection_lost(self, exc):
        self.queue.put_nowait(('disconnection', self.transport, exc))

    def data_received(self, data):
        self.queue.put_nowait(('data', self.transport, data))


class Consumer:
    def __init__(self, queue):
        self.queue = queue
        self.transports = []

    async def consume(self):
        while True:
            msg = await self.queue.get()
            action = msg[0]
            args = msg[1:]

            try:
                handler = getattr(self, 'handle_' + action)
            except AttributeError:
                pass
            else:
                handler(args)

    def handle_connection(self, transport):
        self.transports.append(transport)

    def handle_disconnection(self, transport, exc):
        self.transports.remove(transport)

    def handle_data(self, transport, data):
        index = self.transports.index(transport)
        print(f'Player {index} is sending this: {data.decode()}')


loop = asyncio.get_event_loop()
queue = asyncio.Queue()
consumer = asyncio.ensure_future(Consumer(queue).consume())
loop.run_until_complete(consumer)
server = loop.run_until_complete(
    loop.create_server(lambda: BeloteProtocol(queue), '127.0.0.1', 8888))

# Serve requests until Ctrl+C is pressed
print('Serving on {}'.format(server.sockets[0].getsockname()))
try:
    loop.run_forever()
except KeyboardInterrupt:
    pass

# Close the server
server.close()
loop.run_until_complete(server.wait_closed())
loop.run_until_complete(

loop.close()

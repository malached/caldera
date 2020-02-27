import asyncio
import urllib.parse
import websockets

from app.contacts.handles.h_chat import Handle
from app.utility.base_world import BaseWorld


class WebSocket(BaseWorld):

    def __init__(self, services):
        self.name = 'websocket'
        self.description = 'Accept data through web sockets'
        self.log = self.create_logger('contact_websocket')
        self.handler = Handler(services)
        self.clients = {}

    async def start(self):
        loop = asyncio.get_event_loop()
        web_socket = self.get_config('app.contact.websocket')
        await websockets.serve(lambda x, y: self.handler.handle('server', x, y), '0.0.0.0', web_socket.split(':')[1])

    async def start_client(self, ip, port, path, beacon=None):
        if ip in ['127.0.0.1', 'localhost', (await self.get_machine_info())['ip']]:
            return
        path = path[1:] if path[0] == '/' else path
        uri = f'ws://{ip}:{port}/{path}'
        if uri not in self.clients:
            client = Client(uri, self.handler.handle)
            self.clients[uri] = client
            loop = asyncio.get_event_loop()
            loop.create_task(client.run(beacon=beacon))


class Handler:

    def __init__(self, services):
        self.services = services
        self.handles = [
            Handle(tag='chat', services=services)
        ]
        self.log = BaseWorld.create_logger('websocket_handler')
        self.users = set()

    async def handle(self, origin, socket, path):
        if origin == 'server':
            self.users.add(socket)
        try:
            self.log.debug(path)
            for handle in [h for h in self.handles if h.tag == path.split('/')[1]]:
                await handle.run(socket, path, self.users)
        except Exception as e:
            self.log.debug(e)
            self.users.remove(socket)


class Client:

    def __init__(self, uri, message_handler):
        self.uri = uri
        self.handler = message_handler
        self.socket = None
        self.log = BaseWorld.create_logger('websocket_client')

    async def run(self, beacon=None):
        async with websockets.connect(self.uri) as socket:
            self.log.debug(f'connected to client: {self.uri}, {socket}')
            self.socket = socket
            if beacon:
                await socket.send(beacon)
            await self.handler('client', socket, urllib.parse.urlparse(self.uri).path)

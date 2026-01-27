import asyncio
import websockets
from channels.generic.websocket import AsyncWebsocketConsumer
from config import TARGET_DOMAIN_PATTERN
import logging

logger = logging.getLogger(__name__)


class ProxyWebSocketConsumer(AsyncWebsocketConsumer):
    """Proxy WebSocket connections to backend services."""
    
    async def connect(self):
        """Accept the WebSocket connection and connect to backend."""
        service = self.scope['url_route']['kwargs'].get('service', '')
        path = self.scope['url_route']['kwargs'].get('path', '')
        
        # Build backend WebSocket URL
        target_domain = TARGET_DOMAIN_PATTERN.format(service=service)
        backend_url = f"wss://{target_domain}/ws/{path}"
        
        logger.info(f"[WS PROXY] Connecting to {backend_url}")
        
        try:
            # Accept the client connection
            await self.accept()
            
            # Connect to backend WebSocket
            self.backend_ws = await websockets.connect(backend_url)
            
            # Start forwarding messages both ways
            asyncio.create_task(self.forward_from_backend())
            
        except Exception as e:
            logger.error(f"[WS PROXY] Connection failed: {e}")
            await self.close()
    
    async def disconnect(self, close_code):
        """Close backend WebSocket when client disconnects."""
        if hasattr(self, 'backend_ws'):
            await self.backend_ws.close()
    
    async def receive(self, text_data=None, bytes_data=None):
        """Forward messages from client to backend."""
        try:
            if text_data:
                await self.backend_ws.send(text_data)
            elif bytes_data:
                await self.backend_ws.send(bytes_data)
        except Exception as e:
            logger.error(f"[WS PROXY] Send error: {e}")
            await self.close()
    
    async def forward_from_backend(self):
        """Forward messages from backend to client."""
        try:
            async for message in self.backend_ws:
                if isinstance(message, bytes):
                    await self.send(bytes_data=message)
                else:
                    await self.send(text_data=message)
        except Exception as e:
            logger.error(f"[WS PROXY] Receive error: {e}")
            await self.close()
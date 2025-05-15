# test_server.py
import asyncio
import websockets
import logging

logging.basicConfig(level=logging.INFO)

async def simple_handler(websocket, path):
    logging.info(f"Client connected to path: {path}")
    try:
        async for message in websocket:
            logging.info(f"Received: {message}")
            await websocket.send(f"Echo: {message}")
    except websockets.exceptions.ConnectionClosedOK:
        logging.info("Connection closed.")
    except Exception as e:
        logging.error(f"Error: {e}")

async def main():
    server = await websockets.serve(simple_handler, "localhost", 8765)
    logging.info("Simple WebSocket server started at ws://localhost:8765")
    await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())
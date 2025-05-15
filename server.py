# server.py
import asyncio
import json
import websockets
import stt_module
import db_module
import llm_module
import logging
import traceback

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

async def handle_client(websocket):
    logging.info("Client connected")
    try:
        async for message in websocket:
            logging.info(f"Received message: {message}")
            try:
                data = json.loads(message)
                event = data.get("event")

                if event == "start_listening":
                    logging.info("Starting listening...")
                    await websocket.send(json.dumps({"event": "listening"}))
                    asyncio.create_task(process_speech(websocket))

                elif event == "text_message":
                    text = data.get("text")
                    if text:
                        # Khi người dùng gõ text, coi như đó là tin nhắn của người dùng luôn
                        # UI Flutter sẽ tự hiển thị tin nhắn này.
                        # Server sẽ xử lý và gửi lại phản hồi của chatbot.
                        await process_text(websocket, text, is_user_typed=True)
                    else:
                        await websocket.send(
                            json.dumps(
                                {"event": "error", "message": "No text provided"}
                            )
                        )
                elif event == "stop_listening":
                    logging.info("Stopping listening (not fully implemented yet)...")
                    await websocket.send(
                        json.dumps({"event": "stop_listening_ack"})
                    )
                else:
                    await websocket.send(
                        json.dumps({"event": "error", "message": "Unknown event"})
                    )

            except json.JSONDecodeError as e:
                error_message = f"Invalid JSON: {e}"
                logging.error(error_message)
                await websocket.send(
                    json.dumps({"event": "error", "message": error_message})
                )
            except Exception as e:
                error_message = f"Error processing message: {e}\n{traceback.format_exc()}"
                logging.error(error_message)
                await websocket.send(
                    json.dumps({"event": "error", "message": error_message})
                )

    except websockets.exceptions.ConnectionClosedOK:
        logging.info("Connection closed normally by client.")
    except websockets.exceptions.ConnectionClosedError as e:
        logging.error(f"Connection error: {e}")
    except Exception as e:
        logging.error(f"Unexpected error in client handler: {e}\n{traceback.format_exc()}")
    finally:
        logging.info("Client disconnected")

async def process_speech(websocket):
    try:
        text_from_speech = stt_module.listen_and_recognize()
        if text_from_speech is None:
            logging.warning("STT module returned None.")
            await websocket.send(
                json.dumps({"event": "error", "message": "Speech recognition failed to return text."})
            )
            return

        logging.info(f"Speech-to-text result: {text_from_speech}")
        # Gửi kết quả STT dưới dạng chat_message với role "user_stt"
        if text_from_speech: # Chỉ gửi nếu có text
            await websocket.send(
                json.dumps({"event": "chat_message", "role": "user_stt", "message": text_from_speech})
            )
            # Sau đó xử lý text này để lấy phản hồi từ chatbot
            await process_text(websocket, text_from_speech, is_user_typed=False)
        else: # Trường hợp STT trả về chuỗi rỗng
             logging.info("STT returned empty string, not processing further for chatbot response.")


    except Exception as e:
        error_message = f"Speech-to-text processing error: {e}\n{traceback.format_exc()}"
        logging.error(error_message)
        await websocket.send(
            json.dumps({"event": "error", "message": f"Speech-to-text error: {str(e)}"})
        )

# Thêm tham số is_user_typed để phân biệt
async def process_text(websocket, text_input, is_user_typed=False):
    try:
        if not text_input:
            logging.warning("process_text received empty input.")
            return

        logging.info(f"Processing text: '{text_input}' (User typed: {is_user_typed})")
        context = None
        if db_module.should_search_db(text_input):
            context = db_module.search_knowledge_base(text_input)
            if context:
                logging.info(f"Context found in DB: {context[:200]}...")
            else:
                logging.info("No specific context found in DB for this query.")

        chatbot_response_text = llm_module.get_chatbot_response(text_input, db_context=context)
        if chatbot_response_text is None:
            logging.error("LLM module returned None response.")
            await websocket.send(
                json.dumps({"event": "error", "message": "Chatbot failed to generate a response."})
            )
            return

        logging.info(f"Chatbot response: {chatbot_response_text[:200]}...")
        # Gửi phản hồi của chatbot dưới dạng chat_message với role "chatbot"
        await websocket.send(
            json.dumps({"event": "chat_message", "role": "chatbot", "message": chatbot_response_text})
        )

    except Exception as e:
        error_message = f"Chatbot processing error: {e}\n{traceback.format_exc()}"
        logging.error(error_message)
        await websocket.send(
            json.dumps(
                {"event": "error", "message": f"Chatbot processing error: {str(e)}"}
            )
        )

async def main():
    if db_module.collection is None:
        logging.error("Cannot start server: MongoDB collection is not initialized.")
        return
    if llm_module.model is None:
        logging.error("Cannot start server: LLM model is not initialized.")
        return

    try:
        async with websockets.serve(handle_client, "0.0.0.0", 8765) as server:
            logging.info(f"WebSocket server started and listening on ws://0.0.0.0:8765")
            try:
                actual_ip = [sock.getsockname()[0] for sock in server.sockets if sock.family == asyncio.constants.AF_INET]
                if actual_ip:
                    logging.info(f"Access server from other devices in network via ws://{actual_ip[0]}:8765")
            except Exception:
                pass
            await server.wait_closed()
    except OSError as e:
        if e.errno == 98:
             logging.error(f"Server startup failed: Port 8765 is already in use. {e}")
        else:
             logging.error(f"Server startup failed with OSError: {e}\n{traceback.format_exc()}")
    except Exception as e:
        logging.error(f"Server startup failed: {e}\n{traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(main())
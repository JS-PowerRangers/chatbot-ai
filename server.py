# server.py
import asyncio
import json
import websockets
import stt_module
import db_module
import llm_module # Sẽ cần sửa đổi hàm get_chatbot_response trong module này
import logging
import traceback
from collections import deque # Sử dụng deque để quản lý cửa sổ trượt hiệu quả

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Dictionary để lưu lịch sử chat cho mỗi client (sử dụng deque cho cửa sổ trượt)
# Key: đối tượng websocket, Value: deque các tin nhắn dạng {"role": "user/model", "parts": ["message"]}
client_chat_histories = {}
MAX_HISTORY_TURNS = 5 # Số lượt hội thoại (user + model) muốn giữ lại. Ví dụ 5 lượt = 10 tin nhắn.
                      # Hoặc bạn có thể định nghĩa theo số tin nhắn: MAX_HISTORY_MESSAGES = 10

async def handle_client(websocket):
    logging.info(f"Client connected: {websocket.remote_address}")
    # Khởi tạo lịch sử chat rỗng (hoặc với tin nhắn hệ thống/mở đầu nếu muốn) cho client mới
    client_chat_histories[websocket] = deque(maxlen=MAX_HISTORY_TURNS * 2) # deque tự động loại bỏ phần tử cũ khi đầy

    try:
        async for message in websocket:
            logging.info(f"Received message from {websocket.remote_address}: {message}")
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
                        # Thêm tin nhắn người dùng vào lịch sử trước khi xử lý
                        history = client_chat_histories.get(websocket)
                        if history is not None:
                            history.append({"role": "user", "parts": [text]})
                        await process_text(websocket, text, is_user_typed=True)
                    else:
                        await websocket.send(
                            json.dumps({"event": "error", "message": "No text provided"})
                        )
                elif event == "stop_listening":
                    logging.info("Stopping listening (not fully implemented yet)...")
                    await websocket.send(json.dumps({"event": "stop_listening_ack"}))
                else:
                    await websocket.send(json.dumps({"event": "error", "message": "Unknown event"}))

            except json.JSONDecodeError as e:
                error_message = f"Invalid JSON from {websocket.remote_address}: {e}"
                logging.error(error_message)
                await websocket.send(json.dumps({"event": "error", "message": error_message}))
            except Exception as e:
                error_message = f"Error processing message from {websocket.remote_address}: {e}\n{traceback.format_exc()}"
                logging.error(error_message)
                await websocket.send(json.dumps({"event": "error", "message": error_message}))

    except websockets.exceptions.ConnectionClosedOK:
        logging.info(f"Connection from {websocket.remote_address} closed normally.")
    except websockets.exceptions.ConnectionClosedError as e:
        logging.error(f"Connection error from {websocket.remote_address}: {e}")
    except Exception as e:
        logging.error(f"Unexpected error in client handler for {websocket.remote_address}: {e}\n{traceback.format_exc()}")
    finally:
        if websocket in client_chat_histories:
            del client_chat_histories[websocket] # Dọn dẹp lịch sử khi client ngắt kết nối
            logging.info(f"Chat history cleared for disconnected client: {websocket.remote_address}")
        logging.info(f"Client disconnected: {websocket.remote_address}")

async def process_speech(websocket):
    try:
        text_from_speech = stt_module.listen_and_recognize()
        if text_from_speech is None:
            logging.warning(f"STT module returned None for {websocket.remote_address}.")
            await websocket.send(json.dumps({"event": "error", "message": "Speech recognition failed to return text."}))
            return

        logging.info(f"Speech-to-text result for {websocket.remote_address}: {text_from_speech}")

        history = client_chat_histories.get(websocket)
        if history is None: # Nên luôn tồn tại nếu client kết nối đúng cách
            logging.error(f"Chat history not found for {websocket.remote_address} in process_speech")
            history = deque(maxlen=MAX_HISTORY_TURNS * 2) # Tạo mới nếu lỡ mất
            client_chat_histories[websocket] = history

        if text_from_speech:
            # Gửi kết quả STT về UI
            await websocket.send(json.dumps({"event": "chat_message", "role": "user_stt", "message": text_from_speech}))
            # Thêm vào lịch sử
            history.append({"role": "user", "parts": [text_from_speech]})
            # Xử lý text để lấy phản hồi chatbot
            await process_text(websocket, text_from_speech, is_user_typed=False)
        else: # Trường hợp STT trả về chuỗi rỗng
             logging.info(f"STT returned empty string for {websocket.remote_address}. Notifying client.")
             # Gửi sự kiện error cho client
             await websocket.send(json.dumps({"event": "error", "message": "Không nhận dạng được giọng nói. Vui lòng thử lại."}))
    except Exception as e:
        error_message = f"Speech-to-text processing error for {websocket.remote_address}: {e}\n{traceback.format_exc()}"
        logging.error(error_message)
        await websocket.send(json.dumps({"event": "error", "message": f"Speech-to-text error: {str(e)}"}))

async def process_text(websocket, text_input, is_user_typed=False):
    try:
        if not text_input:
            logging.warning(f"process_text received empty input for {websocket.remote_address}.")
            return

        history = client_chat_histories.get(websocket)
        if history is None:
            logging.error(f"Chat history not found for {websocket.remote_address} in process_text")
            # Nếu không có history, chúng ta không thể xây dựng context cho LLM
            # Có thể gửi lỗi hoặc tạo một history rỗng tạm thời
            await websocket.send(json.dumps({"event": "error", "message": "Chat session error. Please reconnect."}))
            return

        # Log tin nhắn đang được xử lý (tin nhắn này đã được thêm vào history ở nơi gọi)
        logging.info(f"Processing text for {websocket.remote_address}: '{text_input}' (User typed: {is_user_typed})")
        logging.info(f"Current history for {websocket.remote_address} (before LLM call): {list(history)}")


        db_search_context = None
        if db_module.should_search_db(text_input):
            db_search_context = db_module.search_knowledge_base(text_input)
            if db_search_context:
                logging.info(f"Context found in DB for {websocket.remote_address}: {db_search_context[:200]}...")
            else:
                logging.info(f"No specific context found in DB for this query for {websocket.remote_address}.")

        # Gọi LLM, truyền toàn bộ lịch sử hiện tại của client (deque sẽ được chuyển thành list khi truyền)
        chatbot_response_text = llm_module.get_chatbot_response(list(history), db_context=db_search_context)

        if chatbot_response_text is None:
            logging.error(f"LLM module returned None response for {websocket.remote_address}.")
            await websocket.send(json.dumps({"event": "error", "message": "Chatbot failed to generate a response."}))
            return

        logging.info(f"Chatbot response for {websocket.remote_address}: {chatbot_response_text[:200]}...")
        # Thêm phản hồi của chatbot vào lịch sử
        history.append({"role": "model", "parts": [chatbot_response_text]})
        # Gửi phản hồi của chatbot về client
        await websocket.send(json.dumps({"event": "chat_message", "role": "chatbot", "message": chatbot_response_text}))

    except Exception as e:
        error_message = f"Chatbot processing error for {websocket.remote_address}: {e}\n{traceback.format_exc()}"
        logging.error(error_message)
        await websocket.send(json.dumps({"event": "error", "message": f"Chatbot processing error: {str(e)}"}))

async def main():
    # ... (phần main giữ nguyên)
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
        if e.errno == 98: # Address already in use
             logging.error(f"Server startup failed: Port 8765 is already in use. {e}")
        else:
             logging.error(f"Server startup failed with OSError: {e}\n{traceback.format_exc()}")
    except Exception as e:
        logging.error(f"Server startup failed: {e}\n{traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(main())
# server.py (hoặc websocket_server.py)
import asyncio
import json
import websockets
import stt_module  # Đảm bảo các module này có thể import được
import db_module
import llm_module

async def handle_client(websocket, path):
    """Xử lý kết nối WebSocket cho mỗi client."""
    try:
        async for message in websocket:
            print(f"Đã nhận tin nhắn: {message}")
            try:
                # 1. Parse JSON từ client
                data = json.loads(message)
                user_query = data.get("query")  # Lấy câu hỏi từ JSON

                if not user_query:
                    response_data = {"error": "Không tìm thấy 'query' trong tin nhắn."}
                    await websocket.send(json.dumps(response_data)) # Gửi lỗi về client
                    continue # Chờ tin nhắn tiếp theo

                # 2. Xử lý câu hỏi bằng chatbot
                context = None
                if db_module.should_search_db(user_query):
                    context = db_module.search_knowledge_base(user_query)

                chatbot_response = llm_module.get_chatbot_response(user_query, db_context=context)

                # 3. Tạo JSON response
                response_data = {
                    "response": chatbot_response,
                    "success": True # Thêm trạng thái thành công
                }

            except json.JSONDecodeError:
                response_data = {"error": "Tin nhắn không phải là JSON hợp lệ."}
            except Exception as e:
                print(f"Lỗi xử lý: {e}")
                response_data = {"error": f"Lỗi server: {str(e)}"}

            # 4. Gửi JSON response về client
            try:
                await websocket.send(json.dumps(response_data))
            except Exception as e:
                print(f"Lỗi gửi tin nhắn: {e}") # Log lỗi nếu gửi không thành công

    except websockets.exceptions.ConnectionClosedOK:
        print("Kết nối đã đóng.")
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"Kết nối bị lỗi: {e}")

async def main():
    """Khởi động server WebSocket."""
    if db_module.collection is None or llm_module.model is None:
        print("Không thể khởi động server do lỗi DB hoặc LLM.")
        return  # Không khởi động server nếu có lỗi

    server = await websockets.serve(handle_client, "localhost", 8765) # Địa chỉ và port

    print("Server WebSocket đã khởi động tại ws://localhost:8765")
    await server.wait_closed()  # Chờ server đóng

if __name__ == "__main__":
    asyncio.run(main())
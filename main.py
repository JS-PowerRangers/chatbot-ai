import stt_module
import db_module
import llm_module
# import tts_module # Tạm thời chưa dùng TTS

def should_search_db(query_text):
    """
    Quyết định xem có nên tìm kiếm trong DB hay không dựa trên từ khóa.
    Đây là logic rất cơ bản cho MVP.
    """
    if not query_text:
        return False
    query_lower = query_text.lower()
    # Các từ khóa gợi ý cần tra cứu DB
    db_keywords = ["giá", "khuyến mãi", "sản phẩm", "hàng", "raspberry pi", "dht22", "cảm biến", "arduino", "địa chỉ", "chỉ đường", "cửa hàng", "ở đâu", "mở cửa"]
    for keyword in db_keywords:
        if keyword in query_lower:
            return True
    return False

def main_loop():
    """Vòng lặp chính của chatbot."""
    print("Chào mừng bạn đến với Chatbot Hỗ trợ (MVP)!")
    print("Nói 'tạm biệt' để kết thúc.")

    while True:
        # 1. Nhận giọng nói và chuyển thành văn bản
        user_input = stt_module.listen_and_recognize()

        if user_input:
            # Kiểm tra điều kiện thoát
            if "tạm biệt" in user_input.lower():
                print("Cảm ơn bạn đã sử dụng chatbot. Tạm biệt!")
                # tts_module.speak("Cảm ơn bạn đã sử dụng chatbot. Tạm biệt!") # Nếu dùng TTS
                break

            # 2. Quyết định có tìm kiếm DB không
            context = None
            if should_search_db(user_input):
                print("Đang tìm kiếm thông tin trong cơ sở dữ liệu...")
                context = db_module.search_knowledge_base(user_input)
                if context:
                    print("Đã tìm thấy thông tin liên quan.")
                else:
                    print("Không tìm thấy thông tin cụ thể trong DB, sẽ hỏi AI chung.")

            # 3. Gọi LLM để lấy phản hồi
            response = llm_module.get_chatbot_response(user_input, db_context=context)

            # 4. Hiển thị phản hồi (In ra console cho MVP)
            print("\nChatbot trả lời:")
            print(response)
            # Optional: Dùng TTS để đọc phản hồi
            # tts_module.speak(response)

            print("\n" + "="*20 + "\n") # Ngăn cách các lượt hội thoại

        else:
            # Xử lý trường hợp STT không thành công (đã in lỗi trong stt_module)
            print("Vui lòng thử nói lại hoặc nói rõ hơn.")

if __name__ == "__main__":
    # Kiểm tra kết nối DB và LLM trước khi chạy vòng lặp chính
    if db_module.collection is None:
        print("Không thể chạy chatbot do lỗi kết nối MongoDB. Vui lòng kiểm tra cấu hình và MongoDB server.")
    elif llm_module.model is None:
        print("Không thể chạy chatbot do lỗi cấu hình Google Gemini. Vui lòng kiểm tra API Key.")
    else:
        main_loop()
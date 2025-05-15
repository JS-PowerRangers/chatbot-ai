import stt_module
import db_module
import llm_module
import tts_module # Bỏ comment và import module TTS mới

def should_search_db(query_text):
    """
    Quyết định xem có nên tìm kiếm trong DB hay không dựa trên từ khóa.
    Đây là logic rất cơ bản cho MVP.
    """
    if not query_text:
        return False
    query_lower = query_text.lower()
    # Các từ khóa gợi ý cần tra cứu DB
    db_keywords = ["giá", "khuyến mãi", "sản phẩm", "hàng", "cửa hàng", "ở đâu", "mở cửa"]
    for keyword in db_keywords:
        if keyword in query_lower:
            return True
    return False

def main_loop():
    """Vòng lặp chính của chatbot."""
    welcome_message = "Chào mừng bạn đến với Chatbot Hỗ trợ!" # MVP đã bỏ bớt
    print(welcome_message)
    tts_module.speak(welcome_message) # Nói lời chào

    instruction_message = "Nói 'tạm biệt' để kết thúc."
    print(instruction_message)
    # tts_module.speak(instruction_message) # Có thể nói hoặc không tùy bạn

    while True:
        # 1. Nhận giọng nói và chuyển thành văn bản
        user_input = stt_module.listen_and_recognize()

        if user_input:
            # Kiểm tra điều kiện thoát
            if "tạm biệt" in user_input.lower():
                farewell_message = "Cảm ơn bạn đã sử dụng chatbot. Tạm biệt!"
                print(farewell_message)
                tts_module.speak(farewell_message) # Dùng TTS
                break

            # 2. Quyết định có tìm kiếm DB không
            context = None
            if should_search_db(user_input):
                print("Đang tìm kiếm thông tin trong cơ sở dữ liệu...")
                # tts_module.speak("Đang tìm kiếm thông tin trong cơ sở dữ liệu.") # Thông báo trạng thái
                context = db_module.search_knowledge_base(user_input)
                if context:
                    print("Đã tìm thấy thông tin liên quan.")
                    # tts_module.speak("Đã tìm thấy thông tin liên quan.")
                else:
                    print("Không tìm thấy thông tin cụ thể trong DB, sẽ hỏi AI chung.")
                    # tts_module.speak("Không tìm thấy thông tin cụ thể, tôi sẽ dùng AI để trả lời.")


            # 3. Gọi LLM để lấy phản hồi
            print("Chatbot đang suy nghĩ...")
            # tts_module.speak("Để tôi suy nghĩ một chút...") # Thông báo trạng thái
            response = llm_module.get_chatbot_response(user_input, db_context=context)

            # 4. Hiển thị và phát phản hồi
            print("\nChatbot trả lời:")
            print(response)
            tts_module.speak(response) # Dùng TTS để đọc phản hồi

            print("\n" + "="*20 + "\n") # Ngăn cách các lượt hội thoại

        else:
            # Xử lý trường hợp STT không thành công (đã in lỗi trong stt_module)
            stt_fail_message = "Vui lòng thử nói lại hoặc nói rõ hơn."
            print(stt_fail_message)
            # tts_module.speak(stt_fail_message) # Thông báo cho người dùng

if __name__ == "__main__":
    # Kiểm tra kết nối DB và LLM trước khi chạy vòng lặp chính
    if db_module.collection is None:
        error_msg = "Không thể chạy chatbot do lỗi kết nối MongoDB. Vui lòng kiểm tra cấu hình và MongoDB server."
        print(error_msg)
        tts_module.speak(error_msg) # Thông báo lỗi qua TTS
    elif llm_module.model is None:
        error_msg = "Không thể chạy chatbot do lỗi cấu hình Google Gemini. Vui lòng kiểm tra API Key."
        print(error_msg)
        tts_module.speak(error_msg) # Thông báo lỗi qua TTS
    else:
        main_loop()
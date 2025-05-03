import google.generativeai as genai
import config

# Cấu hình API Key
try:
    genai.configure(api_key=config.GOOGLE_API_KEY)
    # Chọn model Gemini (gemini-pro là lựa chọn tốt cho cân bằng khả năng/chi phí/tốc độ)
    model = genai.GenerativeModel('gemini-2.0-flash')
    print("Đã cấu hình Google Generative AI SDK.")
except Exception as e:
    print(f"Lỗi cấu hình Google Generative AI SDK: {e}")
    model = None

# Định nghĩa vai trò và ngữ cảnh ban đầu cho chatbot
SYSTEM_PROMPT = """Bạn là trợ lý ảo của cửa hàng bán linh kiện điện tử và máy tính nhúng XYZ.
Nhiệm vụ của bạn là hỗ trợ khách hàng một cách thân thiện và chuyên nghiệp bằng tiếng Việt.
Bạn có thể trả lời các câu hỏi về:
- Thông tin sản phẩm (tên, mô tả, tính năng).
- Giá cả sản phẩm.
- Các chương trình khuyến mãi hiện có.
- Chỉ đường đến cửa hàng hoặc thông tin liên hệ.
- Tư vấn chọn sản phẩm phù hợp với nhu cầu.

Hãy trả lời ngắn gọn, rõ ràng và tập trung vào câu hỏi của khách hàng.
Nếu bạn được cung cấp thông tin cụ thể từ cơ sở dữ liệu của cửa hàng, hãy ưu tiên sử dụng thông tin đó để trả lời.
Nếu không có thông tin cụ thể hoặc câu hỏi nằm ngoài phạm vi, hãy trả lời một cách lịch sự rằng bạn không có thông tin đó hoặc đề nghị khách hàng hỏi rõ hơn.
"""

def get_chatbot_response(user_query, db_context=None):
    """
    Gửi yêu cầu đến Gemini và nhận phản hồi.
    Bao gồm cả ngữ cảnh từ DB nếu có.
    """
    if not model:
        return "Lỗi: Chưa khởi tạo được mô hình Gemini."

    # Xây dựng prompt hoàn chỉnh
    full_prompt = [
        {"role": "user", "parts": [SYSTEM_PROMPT]},
        {"role": "model", "parts": ["Chào bạn, tôi có thể giúp gì cho bạn?"]}, # Bắt đầu hội thoại
    ]

    prompt_content = f"Câu hỏi của khách hàng: {user_query}"

    if db_context:
        # Thêm ngữ cảnh từ DB vào prompt một cách rõ ràng
        prompt_content += f"\n\nDựa vào thông tin sau từ cơ sở dữ liệu của cửa hàng:\n---\n{db_context}\n---\nHãy trả lời câu hỏi trên."
        print("\n--- Gửi kèm ngữ cảnh từ DB đến LLM ---") # Log để debug
        # print(f"Context:\n{db_context}") # Bỏ comment nếu muốn xem chi tiết context
        print("--- Kết thúc ngữ cảnh ---")
    else:
         prompt_content += "\n\nHãy trả lời câu hỏi trên dựa vào kiến thức chung của bạn về vai trò trợ lý cửa hàng."


    full_prompt.append({"role": "user", "parts": [prompt_content]})

    try:
        print("\nĐang gửi yêu cầu đến Gemini...")
        # Sử dụng generate_content thay vì start_chat để đơn giản hóa cho MVP
        response = model.generate_content(full_prompt)

        # Kiểm tra xem response có text không
        if response.parts:
            answer = response.text
            print("Gemini đã phản hồi.")
            return answer
        else:
            # Kiểm tra thông tin chặn nếu có
            if response.prompt_feedback and response.prompt_feedback.block_reason:
                 print(f"Yêu cầu bị chặn: {response.prompt_feedback.block_reason}")
                 return f"Rất tiếc, yêu cầu của bạn không thể xử lý được do: {response.prompt_feedback.block_reason}"
            else:
                 print("Gemini không trả về nội dung.")
                 return "Xin lỗi, tôi không thể tạo phản hồi vào lúc này."

    except Exception as e:
        print(f"Lỗi khi gọi API Gemini: {e}")
        # Cung cấp thông tin lỗi chi tiết hơn nếu có thể
        error_details = str(e)
        if "API key not valid" in error_details:
            return "Lỗi: API Key của Google không hợp lệ. Vui lòng kiểm tra lại trong file config.py hoặc biến môi trường."
        elif "ConnectTimeoutError" in error_details or "Max retries exceeded" in error_details:
             return "Lỗi: Không thể kết nối đến máy chủ Google AI. Vui lòng kiểm tra kết nối mạng."
        else:
            return f"Đã xảy ra lỗi khi giao tiếp với trợ lý AI: {error_details}"


if __name__ == '__main__':
    # Test nhanh module
    test_query = "Giá của Raspberry Pi 4 là bao nhiêu?"
    # Giả lập context tìm được từ DB
    test_context = """Tên: Raspberry Pi 4 Model B 4GB. Giá: 1,800,000 VND. Mô tả: Máy tính nhúng mạnh mẽ, RAM 4GB, phù hợp cho nhiều dự án.. Khuyến mãi: Giảm 5% khi mua kèm nguồn."""
    response_with_context = get_chatbot_response(test_query, db_context=test_context)
    print("\n--- Phản hồi (có context) ---")
    print(response_with_context)

    test_query_no_context = "Chào bạn"
    response_no_context = get_chatbot_response(test_query_no_context)
    print("\n--- Phản hồi (không context) ---")
    print(response_no_context)
import google.generativeai as genai
import config
import re # Import lại để chắc chắn

# Cấu hình API Key
try:
    genai.configure(api_key=config.GOOGLE_API_KEY)
    model = genai.GenerativeModel('gemini-2.0-flash')
    print("Đã cấu hình Google Generative AI SDK.")
except Exception as e:
    print(f"Lỗi cấu hình Google Generative AI SDK: {e}")
    model = None

SYSTEM_PROMPT = """Bạn là trợ lý ảo của siêu thị ABC, giúp khách hàng mua sắm.
Bạn có thể trả lời về thông tin sản phẩm, giá, khuyến mãi, danh mục, thương hiệu.
Trả lời ngắn gọn, rõ ràng, dùng thông tin từ cơ sở dữ liệu nếu có.
Nếu không có thông tin, xin lỗi và đề nghị hỏi lại hoặc liên hệ hỗ trợ.
"""

def get_chatbot_response(user_query, db_context=None):
    """Gửi yêu cầu đến Gemini và nhận phản hồi."""
    if not model:
        return "Lỗi: Chưa khởi tạo được mô hình Gemini."

    prompt_content = f"Câu hỏi: {user_query}"

    if db_context:
        prompt_content += f"\n\nThông tin từ siêu thị:\n---\n{db_context}\n---\nHãy trả lời câu hỏi trên DỰA VÀO thông tin này." # Nhấn mạnh việc sử dụng context
        print("\n--- Gửi kèm ngữ cảnh từ DB đến LLM ---")
    else:
        prompt_content += "\n\nHãy trả lời dựa trên kiến thức của bạn về siêu thị."

    full_prompt = [
        {"role": "user", "parts": [SYSTEM_PROMPT]},
        {"role": "model", "parts": ["Chào bạn, tôi có thể giúp gì?"]},  # Bắt đầu hội thoại
        {"role": "user", "parts": [prompt_content]}
    ]

    try:
        print("\nĐang gửi yêu cầu đến Gemini...")
        response = model.generate_content(full_prompt)

        if response.parts:
            answer = response.text
            print("Gemini đã phản hồi.")

            # Kiểm tra câu trả lời có chứa thông tin nhạy cảm không (ví dụ: số điện thoại)
            if re.search(r"\d{10,}", answer): # Tìm chuỗi số có ít nhất 10 chữ số
                print("Cảnh báo: Câu trả lời có thể chứa thông tin cá nhân!")
                answer = "Xin lỗi, tôi không được phép cung cấp thông tin cá nhân."

            return answer
        else:
            if response.prompt_feedback and response.prompt_feedback.block_reason:
                print(f"Yêu cầu bị chặn: {response.prompt_feedback.block_reason}")
                return f"Rất tiếc, yêu cầu không xử lý được: {response.prompt_feedback.block_reason}"
            else:
                print("Gemini không trả về nội dung.")
                return "Xin lỗi, tôi không thể tạo phản hồi lúc này."

    except Exception as e:
        print(f"Lỗi khi gọi API Gemini: {e}")
        error_details = str(e)
        if "API key not valid" in error_details:
            return "Lỗi: API Key không hợp lệ."
        elif "ConnectTimeoutError" in error_details or "Max retries exceeded" in error_details:
            return "Lỗi: Không thể kết nối đến máy chủ."
        else:
            return f"Lỗi giao tiếp với AI: {error_details}"

if __name__ == '__main__':
    test_query = "Giá sữa tươi Vinamilk là bao nhiêu?"
    test_context = "Tên: Sữa tươi Vinamilk không đường. Giá: 30,000 VND. Danh mục: Sữa. Thương hiệu: Vinamilk."
    response_with_context = get_chatbot_response(test_query, db_context=test_context)
    print("\n--- Phản hồi (có context) ---")
    print(response_with_context)

    test_query_no_context = "Chào bạn, bạn khỏe không?"
    response_no_context = get_chatbot_response(test_query_no_context)
    print("\n--- Phản hồi (không context) ---")
    print(response_no_context)
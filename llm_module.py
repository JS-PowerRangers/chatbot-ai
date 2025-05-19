# llm_module.py
import google.generativeai as genai
import config
import re
import json
import logging
import traceback

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Cấu hình API Key
try:
    genai.configure(api_key=config.GOOGLE_API_KEY)
    # Lưu ý: gemini-2.0-flash có thể không phải là model mới nhất hoặc phù hợp nhất.
    # Kiểm tra tài liệu Gemini để chọn model phù hợp với nhu cầu và khả năng xử lý context.
    # gemini-pro hoặc các model mới hơn có thể xử lý context dài tốt hơn.
    model = genai.GenerativeModel('gemini-2.0-flash')
    print("Đã cấu hình Google Generative AI SDK với model gemini.")
except Exception as e:
    print(f"Lỗi cấu hình Google Generative AI SDK: {e}")
    model = None

SYSTEM_PROMPT = """Bạn là trợ lý ảo của siêu thị ABC, giúp khách hàng mua sắm.
Bạn có thể trả lời về thông tin sản phẩm, giá, khuyến mãi, danh mục, thương hiệu.
Trả lời ngắn gọn, rõ ràng, dùng thông tin từ cơ sở dữ liệu nếu có.
Nếu không có thông tin, xin lỗi và đề nghị hỏi lại hoặc liên hệ hỗ trợ.
Hãy duy trì tính liên tục của cuộc trò chuyện dựa trên lịch sử được cung cấp.
"""

# Thay đổi tham số đầu vào
def get_chatbot_response(chat_history, db_context=None):
    """
    Gửi yêu cầu đến Gemini và nhận phản hồi, sử dụng lịch sử chat.
    chat_history: list các dict dạng {"role": "user/model", "parts": ["message"]}
    """
    if not model:
        return "Lỗi: Chưa khởi tạo được mô hình Gemini."

    if not chat_history:
        logging.error("get_chatbot_response được gọi với chat_history rỗng.")
        return "Xin lỗi, đã có lỗi xảy ra với phiên chat."

    # Xây dựng prompt hoàn chỉnh
    # SYSTEM_PROMPT và lời chào mở đầu luôn được thêm vào đầu nếu đây là lần tương tác đầu tiên
    # Hoặc, nếu bạn muốn SYSTEM_PROMPT luôn là một phần của mọi yêu cầu:
    full_prompt_parts = [
        {"role": "user", "parts": [SYSTEM_PROMPT]},
        {"role": "model", "parts": ["Chào bạn, tôi có thể giúp gì cho bạn?"]}, # Lời chào mở đầu
    ]

    # Nối lịch sử chat hiện tại (đã bao gồm tin nhắn mới nhất của người dùng)
    full_prompt_parts.extend(chat_history)

    # Xử lý db_context nếu có
    # Cách tiếp cận: Thêm db_context vào cuối tin nhắn user cuối cùng trong history
    # (Lưu ý: history được truyền vào đã chứa tin nhắn mới nhất của user)
    if db_context and full_prompt_parts:
        # Tìm tin nhắn user cuối cùng để gắn db_context
        # Tuy nhiên, với cách chúng ta xây dựng history, tin nhắn cuối cùng trong `chat_history`
        # truyền vào `get_chatbot_response` chính là tin nhắn mới nhất của user.
        last_message_in_history = full_prompt_parts[-1]
        if last_message_in_history.get("role") == "user":
            original_user_part = last_message_in_history["parts"][0]
            last_message_in_history["parts"] = [
                f"{original_user_part}\n\nThông tin từ siêu thị (nếu liên quan):\n---\n{db_context}\n---\nHãy trả lời câu hỏi trên DỰA VÀO thông tin này và lịch sử trò chuyện."
            ]
            logging.info("\n--- Gửi kèm ngữ cảnh từ DB đến LLM (trong lịch sử) ---")
        else:
            # Trường hợp hiếm: tin nhắn cuối không phải của user, thêm db_context như một phần user mới
            # Điều này không nên xảy ra với logic hiện tại.
            logging.warning("Could not easily append db_context to the last user message in history.")
            full_prompt_parts.append(
                 {"role": "user", "parts": [f"Thông tin bổ sung từ cơ sở dữ liệu có thể liên quan: {db_context}"]}
            )


    # Ghi log prompt cuối cùng gửi đi (chỉ một phần để tránh quá dài)
    # logging.info(f"Final prompt to Gemini (first 2 parts and last part): {full_prompt_parts[:2]} ... {full_prompt_parts[-1:] if full_prompt_parts else ''}")
    # Hoặc log toàn bộ nếu cần debug kỹ:
    logging.debug(f"Full prompt to Gemini: {json.dumps(full_prompt_parts, ensure_ascii=False, indent=2)}")


    try:
        logging.info("\nĐang gửi yêu cầu đến Gemini...")
        # Sử dụng `generate_content` với toàn bộ `full_prompt_parts`
        response = model.generate_content(full_prompt_parts)

        if response.parts:
            answer = response.text
            logging.info("Gemini đã phản hồi.")

            if re.search(r"\d{10,}", answer):
                logging.warning("Cảnh báo: Câu trả lời có thể chứa thông tin cá nhân!")
                answer = "Xin lỗi, tôi không được phép cung cấp thông tin cá nhân."
            return answer
        else:
            # Xử lý trường hợp bị chặn hoặc không có phản hồi
            block_reason_msg = ""
            if response.prompt_feedback and response.prompt_feedback.block_reason:
                block_reason_msg = f" Yêu cầu bị chặn: {response.prompt_feedback.block_reason_message or response.prompt_feedback.block_reason}"
                logging.error(block_reason_msg)

            # Kiểm tra safety ratings nếu có
            safety_ratings_issues = []
            if response.candidates:
                for candidate in response.candidates:
                    if candidate.safety_ratings:
                        for rating in candidate.safety_ratings:
                            if rating.probability.value > 0: # HARASSMENT, HATE_SPEECH, SEXUALLY_EXPLICIT, DANGEROUS_CONTENT
                                safety_ratings_issues.append(f"{rating.category.name}: {rating.probability.name}")
            if safety_ratings_issues:
                 logging.error(f"Phản hồi có vấn đề về an toàn: {'; '.join(safety_ratings_issues)}")
                 return f"Xin lỗi, tôi không thể tạo phản hồi do vấn đề về an toàn nội dung.{block_reason_msg}"


            logging.error(f"Gemini không trả về nội dung.{block_reason_msg}")
            return f"Xin lỗi, tôi không thể tạo phản hồi vào lúc này.{block_reason_msg}"

    except Exception as e:
        logging.error(f"Lỗi khi gọi API Gemini: {e}\n{traceback.format_exc()}")
        error_details = str(e)
        if "API key not valid" in error_details:
            return "Lỗi: API Key không hợp lệ."
        elif "ConnectTimeoutError" in error_details or "Max retries exceeded" in error_details:
            return "Lỗi: Không thể kết nối đến máy chủ."
        # Thêm các lỗi cụ thể khác của Gemini nếu có
        elif "UserLocationValidationError" in error_details:
            return "Lỗi: Yêu cầu từ vị trí của bạn không được phép."
        else:
            return f"Lỗi giao tiếp với AI: {error_details}"

if __name__ == '__main__':
    # Test với lịch sử
    sample_history_1 = [
        {"role": "user", "parts": ["Chào bạn"]},
        {"role": "model", "parts": ["Chào bạn, tôi là trợ lý ảo ABC, tôi có thể giúp gì cho bạn?"]},
        {"role": "user", "parts": ["Tôi muốn tìm mua sữa tươi."]}
    ]
    db_context_1 = "Các loại sữa tươi đang có: Vinamilk không đường, TH True Milk có đường."
    print("\n--- Test với lịch sử và context DB ---")
    response1 = get_chatbot_response(chat_history=sample_history_1, db_context=db_context_1)
    print(response1)

    sample_history_2 = [
        {"role": "user", "parts": ["Giá của Raspberry Pi 4 là bao nhiêu?"]},
        {"role": "model", "parts": ["Hiện tại cửa hàng không có thông tin về Raspberry Pi 4. Bạn có muốn tìm sản phẩm khác không?"]},
        {"role": "user", "parts": ["Vậy còn Arduino Uno R3 thì sao?"]}
    ]
    print("\n--- Test với lịch sử, không có context DB ---")
    response2 = get_chatbot_response(chat_history=sample_history_2)
    print(response2)

    print("\n--- Test với history rỗng (không nên xảy ra trong luồng thực tế) ---")
    response3 = get_chatbot_response(chat_history=[]) # Nên trả về lỗi hoặc xử lý phù hợp
    print(response3)
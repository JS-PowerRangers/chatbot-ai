import speech_recognition as sr
import config

def listen_and_recognize():
    """Ghi âm từ microphone và nhận dạng giọng nói tiếng Việt."""
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("Chatbot đang lắng nghe...")
        # Điều chỉnh theo tiếng ồn môi trường
        r.adjust_for_ambient_noise(source, duration=0.5)
        try:
            audio = r.listen(source, timeout=5, phrase_time_limit=10) # Nghe trong tối đa 5s chờ, nói tối đa 10s
        except sr.WaitTimeoutError:
            print("Không phát hiện thấy giọng nói.")
            return None

    try:
        print("Đang xử lý giọng nói...")
        text = r.recognize_google(audio, language=config.LANGUAGE_CODE)
        print(f"Bạn đã nói: {text}")
        return text
    except sr.UnknownValueError:
        print("Xin lỗi, tôi không hiểu bạn nói gì.")
        return None
    except sr.RequestError as e:
        print(f"Lỗi kết nối tới dịch vụ Google Speech Recognition; {e}")
        return None
    except Exception as e:
        print(f"Đã xảy ra lỗi khi xử lý giọng nói: {e}")
        return None

if __name__ == '__main__':
    # Test nhanh module
    recognized_text = listen_and_recognize()
    if recognized_text:
        print(f"Kết quả nhận dạng: {recognized_text}")
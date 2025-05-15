# stt_module.py
import speech_recognition as sr
import logging

# Cấu hình logging (nếu chưa có)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def listen_and_recognize():
    """Ghi âm và chuyển giọng nói thành văn bản."""
    r = sr.Recognizer()
    with sr.Microphone() as source:
        logging.info("Nói gì đó...")
        r.adjust_for_ambient_noise(source)  # Lọc tiếng ồn xung quanh

        try:
            audio = r.listen(source, timeout=5)  # Nghe trong 5 giây
        except sr.WaitTimeoutError:
            logging.warning("Không có gì được nói trong 5 giây.")
            return "" # Hoặc thông báo lỗi

    try:
        logging.info("Đang nhận dạng...")
        text = r.recognize_google(audio, language="vi-VN")
        logging.info("Bạn đã nói: " + text)
        return text
    except sr.UnknownValueError:
        logging.error("Không nhận diện được giọng nói")
        return ""
    except sr.RequestError as e:
        logging.error("Không thể yêu cầu dịch vụ STT; {0}".format(e))
        return "" # Hoặc trả về một thông báo lỗi cụ thể hơn
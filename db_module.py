from pymongo import MongoClient
import config
import re # Import thư viện regex

# Khởi tạo kết nối một lần khi module được import
try:
    client = MongoClient(config.MONGODB_URI)
    db = client[config.DB_NAME]
    collection = db[config.COLLECTION_NAME]
    print("Kết nối MongoDB thành công.")
    # Kiểm tra kết nối
    client.admin.command('ping')
except Exception as e:
    print(f"Lỗi kết nối MongoDB: {e}")
    client = None
    db = None
    collection = None

def format_product_info(doc):
    """Định dạng thông tin tài liệu thành chuỗi dễ đọc."""
    if not doc:
        return ""
    parts = []
    if 'ten' in doc:
        parts.append(f"Tên: {doc['ten']}")
    if 'gia' in doc:
        # Định dạng tiền tệ Việt Nam
        gia_vnd = "{:,.0f} VND".format(doc['gia']) if isinstance(doc['gia'], (int, float)) else str(doc['gia'])
        parts.append(f"Giá: {gia_vnd}")
    if 'mo_ta' in doc:
        parts.append(f"Mô tả: {doc['mo_ta']}")
    if doc.get('khuyen_mai'): # Chỉ thêm nếu có khuyến mãi
        parts.append(f"Khuyến mãi: {doc['khuyen_mai']}")
    if 'dia_chi' in doc:
         parts.append(f"Địa chỉ: {doc['dia_chi']}")
    if 'gio_mo_cua' in doc:
         parts.append(f"Giờ mở cửa: {doc['gio_mo_cua']}")

    return ". ".join(parts)

def search_knowledge_base(query_text):
    """Tìm kiếm thông tin trong MongoDB dựa trên query_text."""
    if collection is None:
        print("Chưa kết nối được MongoDB.")
        return None # Trả về None thay vì chuỗi trống

    # --- Chiến lược tìm kiếm đơn giản cho MVP ---
    # 1. Tách từ khóa cơ bản từ query
    keywords = query_text.lower().split()
    # Loại bỏ các từ không quan trọng (có thể mở rộng danh sách này)
    stop_words = ["là", "bao nhiêu", "có", "giá", "của", "cho", "tôi", "biết", "về", "ở", "đâu", "địa chỉ", "đến"]
    meaningful_keywords = [word for word in keywords if word not in stop_words and len(word) > 1]

    # 2. Tạo truy vấn MongoDB linh hoạt hơn
    # Tìm kiếm trong trường 'ten', 'ma_sp', hoặc 'keywords'
    # Sử dụng $regex để tìm kiếm không phân biệt chữ hoa/thường và chứa từ khóa
    search_conditions = []
    for keyword in meaningful_keywords:
        regex_pattern = re.compile(f'.*{re.escape(keyword)}.*', re.IGNORECASE)
        search_conditions.append({"$or": [
            {"ten": regex_pattern},
            {"ma_sp": regex_pattern},
            {"keywords": regex_pattern},
            {"mo_ta": regex_pattern} # Thêm tìm kiếm trong mô tả
        ]})

    # Kết hợp các điều kiện: cần khớp *ít nhất một* điều kiện (OR)
    # Hoặc nếu muốn chặt chẽ hơn, khớp *tất cả* (AND - nhưng có thể quá chặt)
    # Chúng ta sẽ dùng $or cho các trường, nhưng có thể cần $and cho các keyword nếu muốn chính xác hơn
    # Cách đơn giản nhất cho MVP: tìm bất kỳ tài liệu nào khớp với bất kỳ keyword nào trong các trường chỉ định
    if not search_conditions:
         return None # Không có từ khóa ý nghĩa để tìm

    # Tìm các tài liệu khớp với BẤT KỲ điều kiện nào ($or)
    mongo_query = {"$or": search_conditions}

    try:
        results = collection.find(mongo_query).limit(3) # Giới hạn 3 kết quả
        found_docs = list(results) # Chuyển cursor thành list

        if not found_docs:
            print(f"Không tìm thấy thông tin trực tiếp cho: '{query_text}' trong DB.")
            return None # Trả về None nếu không tìm thấy

        # Định dạng kết quả thành một chuỗi context
        context_list = [format_product_info(doc) for doc in found_docs]
        # Lọc bỏ các chuỗi rỗng nếu format_product_info trả về rỗng
        context_list = [ctx for ctx in context_list if ctx]

        if not context_list:
             return None # Không có thông tin hữu ích để định dạng

        print(f"Đã tìm thấy {len(context_list)} thông tin liên quan trong DB.")
        return "\n---\n".join(context_list) # Ngăn cách các kết quả rõ ràng

    except Exception as e:
        print(f"Lỗi khi truy vấn MongoDB: {e}")
        return None

if __name__ == '__main__':
    # Test nhanh module
    test_query_1 = "Giá Raspberry Pi 4"
    context1 = search_knowledge_base(test_query_1)
    print(f"\n--- Kết quả tìm kiếm cho '{test_query_1}' ---")
    print(context1 if context1 else "Không tìm thấy")

    test_query_2 = "Địa chỉ cửa hàng ở đâu"
    context2 = search_knowledge_base(test_query_2)
    print(f"\n--- Kết quả tìm kiếm cho '{test_query_2}' ---")
    print(context2 if context2 else "Không tìm thấy")

    test_query_3 = "Thông tin cảm biến dht22"
    context3 = search_knowledge_base(test_query_3)
    print(f"\n--- Kết quả tìm kiếm cho '{test_query_3}' ---")
    print(context3 if context3 else "Không tìm thấy")
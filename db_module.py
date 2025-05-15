from pymongo import MongoClient
import config
import re

# Kết nối MongoDB
try:
    client = MongoClient(config.MONGODB_URI)
    db = client[config.DB_NAME]
    collection = db[config.COLLECTION_NAME]
    print("Kết nối MongoDB thành công.")
    client.admin.command('ping')  # Kiểm tra kết nối
except Exception as e:
    print(f"Lỗi kết nối MongoDB: {e}")
    client = None
    db = None
    collection = None

def format_product_info(doc):
    """Định dạng thông tin sản phẩm."""
    if not doc:
        return ""
    parts = []
    if 'ten' in doc:
        parts.append(f"Tên: {doc['ten']}")
    if 'gia' in doc:
        gia_vnd = "{:,.0f} VND".format(doc['gia']) if isinstance(doc['gia'], (int, float)) else str(doc['gia'])
        parts.append(f"Giá: {gia_vnd}")
    if 'mo_ta' in doc:
        parts.append(f"Mô tả: {doc['mo_ta']}")
    if doc.get('khuyen_mai'):
        parts.append(f"Khuyến mãi: {doc['khuyen_mai']}")
    if 'danh_muc' in doc:  # Thêm danh mục
        parts.append(f"Danh mục: {doc['danh_muc']}")
    if 'thuong_hieu' in doc: # Thêm thương hiệu
         parts.append(f"Thương hiệu: {doc['thuong_hieu']}")
    return ". ".join(parts)

def search_knowledge_base(query_text):
    """Tìm kiếm thông tin trong MongoDB."""
    if collection is None:
        print("Chưa kết nối được MongoDB.")
        return None

    keywords = query_text.lower().split()
    stop_words = ["là", "bao nhiêu", "có", "giá", "của", "cho", "tôi", "biết", "về", "ở", "đâu", "địa chỉ", "đến", "mua"]  # Thêm "mua"
    meaningful_keywords = [word for word in keywords if word not in stop_words and len(word) > 1]

    search_conditions = []
    for keyword in meaningful_keywords:
        regex_pattern = re.compile(f'.*{re.escape(keyword)}.*', re.IGNORECASE)
        search_conditions.append({"$or": [
            {"ten": regex_pattern},
            {"mo_ta": regex_pattern},
            {"keywords": regex_pattern},
            {"danh_muc": regex_pattern},  # Tìm theo danh mục
            {"thuong_hieu": regex_pattern} # Tìm theo thương hiệu
        ]})

    if not search_conditions:
        return None

    mongo_query = {"$or": search_conditions}

    try:
        results = collection.find(mongo_query).limit(5)  # Tăng limit lên 5
        found_docs = list(results)

        if not found_docs:
            print(f"Không tìm thấy thông tin cho: '{query_text}' trong DB.")
            return None

        context_list = [format_product_info(doc) for doc in found_docs]
        context_list = [ctx for ctx in context_list if ctx]

        if not context_list:
            return None

        print(f"Đã tìm thấy {len(context_list)} thông tin liên quan.")
        return "\n---\n".join(context_list)

    except Exception as e:
        print(f"Lỗi khi truy vấn MongoDB: {e}")
        return None

if __name__ == '__main__':
    test_query_1 = "Giá sữa tươi Vinamilk"
    context1 = search_knowledge_base(test_query_1)
    print(f"\n--- Kết quả tìm kiếm cho '{test_query_1}' ---")
    print(context1 if context1 else "Không tìm thấy")

    test_query_2 = "Khuyến mãi đồ gia dụng"
    context2 = search_knowledge_base(test_query_2)
    print(f"\n--- Kết quả tìm kiếm cho '{test_query_2}' ---")
    print(context2 if context2 else "Không tìm thấy")

    test_query_3 = "Tìm kiếm laptop Dell"
    context3 = search_knowledge_base(test_query_3)
    print(f"\n--- Kết quả tìm kiếm cho '{test_query_3}' ---")
    print(context3 if context3 else "Không tìm thấy")
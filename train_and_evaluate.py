import pandas as pd
# pyrefly: ignore [missing-import]
import numpy as np
# pyrefly: ignore [missing-import]
import matplotlib.pyplot as plt
import seaborn as sns
import time
# pyrefly: ignore [missing-import]
import joblib
import os
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import SVC
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report

TRAIN_FILES = ['train_1.csv', 'train_2.csv', 'train_3.csv', 'train_4.csv']
TEST_FILE = 'test.csv'

# 1. HÀM RULE-BASED
def rule_based_predict(features):
    """
    Tái tạo lại logic rule-based (gập ngón tay) từ ai_controller.py
    Features là mảng 63 phần tử (21 điểm x 3 trục).
    """
    tips = [8, 12, 16, 20]
    pips = [6, 10, 14, 18]
    folded = []
    
    for tip, pip in zip(tips, pips):
        # Lấy tọa độ (x, y, z)
        tx, ty, tz = features[tip*3], features[tip*3+1], features[tip*3+2]
        px, py, pz = features[pip*3], features[pip*3+1], features[pip*3+2]
        
        dist_tip = tx**2 + ty**2 + tz**2
        dist_pip = px**2 + py**2 + pz**2
        folded.append(dist_tip < dist_pip)
        
    fingers_folded = sum(folded)
    is_fist = fingers_folded >= 3
    is_pointing = (not folded[0]) and folded[1] and folded[2] and folded[3]
    
    if is_pointing:
        return 'POINT'
    elif is_fist:
        return 'FIST'
    else:
        return 'OPEN'

def main():
    print("1. Đang đọc dữ liệu...")
    
    # Đọc dữ liệu Train
    train_dfs = []
    for f in TRAIN_FILES:
        if os.path.exists(f):
            train_dfs.append(pd.read_csv(f))
        else:
            print(f"Cảnh báo: Không tìm thấy file {f}")
            
    if not train_dfs:
        print("Lỗi: Không có dữ liệu huấn luyện. Hãy chạy collect_data.py để tạo các file train_1.csv, train_2.csv...")
        return
        
    train_df = pd.concat(train_dfs, ignore_index=True)
    X_train = train_df.drop('label', axis=1).values
    y_train = train_df['label'].values
    
    print(f"Tổng số mẫu dữ liệu TRAIN: {len(train_df)}")
    print(train_df['label'].value_counts())
    
    # Đọc dữ liệu Test
    if os.path.exists(TEST_FILE):
        test_df = pd.read_csv(TEST_FILE)
        X_test = test_df.drop('label', axis=1).values
        y_test = test_df['label'].values
        print(f"\nTổng số mẫu dữ liệu TEST: {len(test_df)}")
        print(test_df['label'].value_counts())
    else:
        print(f"Lỗi: Không tìm thấy file {TEST_FILE}. Hãy chạy collect_data.py để tạo file test.csv")
        return
    
    # Danh sách các mô hình
    models = {
        'Rule-Based (Baseline)': None, # Không cần train
        'KNN': KNeighborsClassifier(n_neighbors=5),
        'SVM': SVC(kernel='rbf', probability=True),
        'MLP (Deep Learning)': MLPClassifier(hidden_layer_sizes=(64, 32), max_iter=500, random_state=42)
    }
    
    results = {}
    
    # 2. HUẤN LUYỆN VÀ ĐÁNH GIÁ (TRAIN & EVALUATE)
    print("\n2. Bắt đầu huấn luyện và đánh giá...")
    for name, model in models.items():
        print(f"  -> Đang xử lý mô hình: {name}")
        
        # Train (nếu không phải rule-based)
        if model is not None:
            model.fit(X_train, y_train)
            # Lưu mô hình ra file .pkl
            filename = name.split()[0].lower() + '_model.pkl'
            joblib.dump(model, filename)
            
        # Inference & Đo thời gian
        start_time = time.time()
        if model is None:
            y_pred = [rule_based_predict(row) for row in X_test]
        else:
            y_pred = model.predict(X_test)
        inference_time = (time.time() - start_time) / len(X_test) * 1000 # tính bằng millisecond
        
        acc = accuracy_score(y_test, y_pred)
        cm = confusion_matrix(y_test, y_pred, labels=['OPEN', 'FIST', 'POINT'])
        
        results[name] = {
            'Accuracy': acc * 100,
            'Inference_Time_ms': inference_time,
            'Confusion_Matrix': cm,
            'Predictions': y_pred
        }
    
    # 3. TRÌNH BÀY KẾT QUẢ & VẼ BIỂU ĐỒ
    print("\n3. Tóm tắt Kết quả Báo cáo:")
    print("="*50)
    for name, res in results.items():
        print(f"Mô hình: {name}")
        print(f" - Độ chính xác (Accuracy): {res['Accuracy']:.2f}%")
        print(f" - Tốc độ dự đoán 1 frame : {res['Inference_Time_ms']:.4f} ms")
        print("-" * 30)
        
    # Vẽ Biểu đồ So sánh Độ chính xác (Accuracy)
    plt.figure(figsize=(10, 6))
    sns.set_theme(style="whitegrid")
    names = list(results.keys())
    accs = [results[n]['Accuracy'] for n in names]
    
    ax = sns.barplot(x=names, y=accs, palette="viridis")
    plt.title('So sánh Độ chính xác giữa các Mô hình (Accuracy %)', fontsize=14)
    plt.ylim(0, 110)
    plt.ylabel('Độ chính xác (%)')
    for i, v in enumerate(accs):
        ax.text(i, v + 2, f"{v:.1f}%", ha='center', fontweight='bold')
    plt.savefig('accuracy_comparison.png')
    plt.close()
    
    # Vẽ Confusion Matrix cho từng mô hình
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    axes = axes.flatten()
    
    for idx, name in enumerate(names):
        cm = results[name]['Confusion_Matrix']
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', ax=axes[idx],
                    xticklabels=['OPEN', 'FIST', 'POINT'], 
                    yticklabels=['OPEN', 'FIST', 'POINT'])
        axes[idx].set_title(f'Confusion Matrix: {name}')
        axes[idx].set_ylabel('Thực tế')
        axes[idx].set_xlabel('Dự đoán')
        
    plt.tight_layout()
    plt.savefig('confusion_matrices.png')
    plt.close()
    
    print("\n[HOÀN TẤT] Đã lưu 3 mô hình (.pkl) và 2 file hình ảnh biểu đồ (.png).")
    
    # 4. ĐÁNH GIÁ, ƯU NHƯỢC ĐIỂM & KẾT LUẬN
    print("\n==================================================")
    print("4. ĐÁNH GIÁ VÀ KẾT LUẬN CHUYÊN SÂU")
    print("==================================================")
    
    best_model_name = max(results, key=lambda k: results[k]['Accuracy'])
    best_acc = results[best_model_name]['Accuracy']
    
    fastest_model_name = min(results, key=lambda k: results[k]['Inference_Time_ms'])
    fastest_time = results[fastest_model_name]['Inference_Time_ms']
    
    report_text = f"""
[KẾT QUẢ TỔNG QUAN]
- Mô hình đạt độ chính xác cao nhất: {best_model_name} ({best_acc:.2f}%)
- Mô hình dự đoán nhanh nhất (tối ưu realtime): {fastest_model_name} ({fastest_time:.4f} ms/frame)

[PHÂN TÍCH ƯU/NHƯỢC ĐIỂM TỪNG PHƯƠNG PHÁP]

1. Rule-Based (Lập trình logic hình học cứng):
   + Ưu điểm: Tốc độ cực nhanh, không cần thu thập dữ liệu hay huấn luyện.
   + Nhược điểm: Rất kém linh hoạt. Chỉ cần người chơi hơi nghiêng tay, để tay quá gần/xa camera là thuật toán tính khoảng cách ngón tay sẽ sai lệch ngay lập tức. Hiệu năng thực tế thường thấp nhất.

2. KNN (K-Nearest Neighbors):
   + Ưu điểm: Thuật toán đơn giản, huấn luyện (train) gần như tức thì. Khá trực quan.
   + Nhược điểm: Ở pha dự đoán (khi chơi game), mô hình phải tính toán khoảng cách với TOÀN BỘ tập dữ liệu gốc. Nếu tập data quá lớn, game sẽ bị lag/giật.

3. SVM (Support Vector Machine):
   + Ưu điểm: Rất mạnh mẽ trong không gian nhiều chiều (cụ thể ở đây là 63 chiều tọa độ tay x, y, z). Thường cho độ chính xác cực cao và đường ranh giới phân loại rất rõ nét. Tốc độ dự đoán tốt.
   + Nhược điểm: Tốn nhiều thời gian để train nếu dữ liệu lên đến hàng chục nghìn mẫu.

4. MLP (Mạng Nơ-ron Nhân tạo - Cấu trúc Deep Learning cơ bản):
   + Ưu điểm: Khả năng học các đặc trưng phức tạp (phi tuyến tính) cực tốt. Kích thước mô hình lưu trữ nhỏ gọn và tốc độ dự đoán lúc chơi game là siêu nhanh (chỉ bằng vài phép nhân ma trận).
   + Nhược điểm: Hoạt động như một "hộp đen" khó giải thích, tốn thời gian cấu hình số lớp/số nơ-ron ban đầu.

[KẾT LUẬN CHUNG DÀNH CHO DỰ ÁN]
=> Dựa trên bộ dữ liệu thực tế, mô hình [{best_model_name}] đang thể hiện hiệu năng toàn diện nhất với độ chính xác {best_acc:.2f}%.
=> Khuyến nghị: Trong môi trường Game Hub (cần đạt tốc độ 30-60 FPS), việc áp dụng Machine Learning đã khắc phục triệt để điểm yếu chí mạng của phương pháp Rule-Based truyền thống. Mô hình {best_model_name} là sự lựa chọn tối ưu nhất để tích hợp vào file 'ai_controller.py' nhằm mang lại trải nghiệm điều khiển mượt mà và chính xác nhất cho người chơi.
"""
    print(report_text)
    
    with open('evaluation_report.txt', 'w', encoding='utf-8') as f:
        f.write(report_text)
        
    print("=> Toàn bộ nội dung đánh giá đã được lưu vào file 'evaluation_report.txt'.")

if __name__ == '__main__':
    main()

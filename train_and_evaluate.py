import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import time
import joblib
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import SVC
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report

CSV_FILE = 'gesture_dataset.csv'

# ==========================================
# 1. HÀM RULE-BASED (Tái tạo logic cũ để làm Baseline)
# ==========================================
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
    df = pd.read_csv(CSV_FILE)
    X = df.drop('label', axis=1).values
    y = df['label'].values
    
    print(f"Tổng số mẫu dữ liệu: {len(df)}")
    print(df['label'].value_counts())
    
    # Chia dữ liệu 80% train, 20% test
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    # Danh sách các mô hình
    models = {
        'Rule-Based (Baseline)': None, # Không cần train
        'KNN': KNeighborsClassifier(n_neighbors=5),
        'SVM': SVC(kernel='rbf', probability=True),
        'MLP (Deep Learning)': MLPClassifier(hidden_layer_sizes=(64, 32), max_iter=500, random_state=42)
    }
    
    results = {}
    
    # ==========================================
    # 2. HUẤN LUYỆN VÀ ĐÁNH GIÁ (TRAIN & EVALUATE)
    # ==========================================
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
    
    # ==========================================
    # 3. TRÌNH BÀY KẾT QUẢ & VẼ BIỂU ĐỒ
    # ==========================================
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
    print("Bạn có thể chèn các hình ảnh 'accuracy_comparison.png' và 'confusion_matrices.png' vào Báo cáo Đồ án của mình!")

if __name__ == '__main__':
    main()

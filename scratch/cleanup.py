import os
import sys
import shutil

# Khắc phục lỗi mã hóa Unicode hiển thị tiếng Việt trên Windows console
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

def main():
    ml_dir = r"D:\GIT REPO\trafffic-density-analysis-system\traffic-density-analysis-system\ml_service"
    
    # 1. Sao chép nội dung tích hợp mới sang train.py để làm file chạy chuẩn
    reprocess_train_path = os.path.join(ml_dir, "reprocess_and_train.py")
    train_path = os.path.join(ml_dir, "train.py")
    
    if os.path.exists(reprocess_train_path):
        shutil.copy(reprocess_train_path, train_path)
        print("[+] Đã chuyển đổi tích hợp reprocess_and_train.py thành train.py chuẩn.")

    # 2. Danh sách các file lỗi thời cần loại bỏ
    files_to_remove = [
        "density_cluster.py",
        "evaluate.py",
        "light_delta_model.py",
        "phase_optimizer.py",
        "preprocess.py",
        "test_light_delta_model.py",
        "test_phase_optimizer.py",
        "traffic_predictor.py",
        "reprocess_and_train.py"
    ]

    for filename in files_to_remove:
        file_path = os.path.join(ml_dir, filename)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"  -> Đã xóa file lỗi thời: {filename}")
            except Exception as e:
                print(f"  -> Lỗi khi xóa file {filename}: {e}")

    # 3. Loại bỏ thư mục helpers/ cũ chứa các mã nguồn nháp rác
    helpers_dir = os.path.join(ml_dir, "helpers")
    if os.path.exists(helpers_dir):
        try:
            shutil.rmtree(helpers_dir)
            print("  -> Đã xóa thư mục rác: helpers/")
        except Exception as e:
            print(f"  -> Lỗi khi xóa thư mục helpers/: {e}")

    print("\n[+] ĐÃ DỌN DẸP SẠCH SẼ HOÀN TOÀN THƯ MỤC ml_service!")

if __name__ == '__main__':
    main()

import json
import os
import sys

def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')
        
    fpath = r"D:\GIT REPO\trafffic-density-analysis-system\traffic-density-analysis-system\ml_service\data_evaluation.ipynb"
    if not os.path.exists(fpath):
        print(f"Notebook not found at {fpath}")
        return
        
    with open(fpath, 'r', encoding='utf-8') as f:
        nb = json.load(f)
        
    print("="*80)
    print(" ĐỌC KẾT QUẢ THỰC THI JUPYTER NOTEBOOK")
    print("="*80)
    
    cell_idx = 0
    for cell in nb['cells']:
        if cell['cell_type'] == 'code':
            cell_idx += 1
            print(f"\n[CELL {cell_idx}] Source code snippet:")
            # In 3 dòng đầu của code cell
            code_lines = cell['source']
            for line in code_lines[:3]:
                print(f"  > {line.strip()}")
            if len(code_lines) > 3:
                print("  > ...")
                
            print(f"\n[CELL {cell_idx} OUTPUTS]:")
            for out in cell.get('outputs', []):
                if 'text' in out:
                    print("".join(out['text']))
                elif 'data' in out:
                    data = out['data']
                    keys = list(data.keys())
                    print(f"  -> [Đồ họa trực quan: {keys}]")
                    if 'image/png' in data:
                        print("     [Có chứa biểu đồ PNG của seaborn/matplotlib]")
            print("-" * 60)

if __name__ == '__main__':
    main()

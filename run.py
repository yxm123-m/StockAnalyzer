"""启动入口"""
import os
import sys
import subprocess

if __name__ == "__main__":
    # 确保在项目根目录运行
    root_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(root_dir)
    sys.path.insert(0, root_dir)

    # 启动 Streamlit
    subprocess.run([
        "streamlit", "run",
        os.path.join("ui", "app.py"),
        "--server.port", "8501",
        "--browser.serverAddress", "localhost",
    ])

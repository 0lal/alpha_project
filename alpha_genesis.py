import subprocess
import sys

def main():
    # استدعاء المايسترو الرئيسي مع أمر بناء البيئة
    subprocess.run([sys.executable, "main.py", "genesis"])

if __name__ == "__main__":
    main()
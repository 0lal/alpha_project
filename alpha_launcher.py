import subprocess
import sys

def main():
    # استدعاء المايسترو الرئيسي مع أمر التشغيل
    subprocess.run([sys.executable, "main.py", "start"])

if __name__ == "__main__":
    main()
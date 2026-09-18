# -*- coding: utf-8 -*-
"""一键打包脚本 - 自动检查并关闭运行中的程序，完成 PyInstaller 打包并同步配置"""
import os
import shutil
import subprocess
import sys

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base_dir)
    exe_name = "场外指数基金数据获取工具.exe"

    print(f"[*] 1. 检查并关闭可能在运行的 {exe_name}...")
    subprocess.run(["taskkill", "/F", "/IM", exe_name], capture_output=True)

    print("[*] 2. 执行 PyInstaller 打包...")
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "场外指数基金数据获取工具.spec"]
    ret = subprocess.run(cmd)

    if ret.returncode == 0:
        print("\n[+] 3. 打包成功！")
        dist_dir = os.path.join(base_dir, "dist")
        os.makedirs(dist_dir, exist_ok=True)
        if os.path.exists("fund_data.db"):
            shutil.copy2("fund_data.db", os.path.join(dist_dir, "fund_data.db"))
            print("[+] 已同步 fund_data.db 到 dist 目录")
        if os.path.exists("user_config.json") and not os.path.exists(os.path.join(dist_dir, "user_config.json")):
            shutil.copy2("user_config.json", os.path.join(dist_dir, "user_config.json"))
            print("[+] 已同步 user_config.json 到 dist 目录")
        print(f"\n[√] 可执行文件位于: {os.path.join(dist_dir, exe_name)}")
    else:
        print(f"\n[!] 打包失败，错误码: {ret.returncode}")
        print("[!] 常见排查方法：")
        print("    1. 请确保已关闭正在运行的「场外指数基金数据获取工具.exe」；")
        print("    2. 如果安装了杀毒软件（360、火绒、Windows Defender 等），请检查是否拦截了生成 exe 操作。")

if __name__ == "__main__":
    main()

import os
from playwright.sync_api import sync_playwright

STATE_FILE = "state.json"

def login():
    print("准备启动浏览器...")
    with sync_playwright() as p:
        # 打开 Chromium 浏览器，非无头模式（需要您看到界面扫码）
        browser = p.chromium.launch(headless=False)
        
        if os.path.exists(STATE_FILE):
            print(f"找到已有的 {STATE_FILE}，将加载现有登录状态尝试打开...")
            context = browser.new_context(storage_state=STATE_FILE)
        else:
            context = browser.new_context()
            
        page = context.new_page()
        
        print("正在打开番茄小说作家后台...")
        try:
            page.goto("https://fanqienovel.com/main/writer/?enter_from=author_zone", timeout=60000)
        except Exception as e:
            print(f"打开网页遇到问题，请检查网络: {e}")
            print("浏览器仍然保持打开，您可以手动在地址栏输入 https://fanqienovel.com/writer")
        
        print("\n" + "="*50)
        print("请在弹出的浏览器窗口中登录您的账号（可以密码、验证码或扫码登录）。")
        print("如果您已经登录完成，并且看到了作家后台首页，请回到这个黑框/终端里按【回车键】！")
        print("="*50 + "\n")
        
        input(">>> 确认登录完成后，请按回车键以保存登录状态并退出：")
        
        # 保存 Cookies 和 Local Storage 等状态
        context.storage_state(path=STATE_FILE)
        print(f"\n登录状态已成功保存到当前目录下的 {STATE_FILE} 文件中！")
        print("以后运行自动发布脚本时，会自动加载这个文件，无需再次手动登录。")
        
        browser.close()

if __name__ == "__main__":
    login()

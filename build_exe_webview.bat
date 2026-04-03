@echo off
chcp 65001 > nul
echo ===========================================
echo 番茄发文助手 Electron版 (PyWebView) 一键打包
echo ===========================================
echo.
echo 正在安装打包工具 pyinstaller ...
pip install pyinstaller
echo 正在确保项目依赖完整...
pip install -r requirements.txt
playwright install chromium
echo.
echo 开始打包成独立桌面软件...
:: 注意这里需要将 web 文件夹一同打包进去
pyinstaller -F -w -i "logo.ico" --add-data "web;web" -n FanqiePublisher_PRO main_webview.py
echo.
echo 正在为您生成桌面快捷方式...
powershell -Command "$s=(New-Object -COM WScript.Shell).CreateShortcut('%USERPROFILE%\Desktop\番茄发文大魔王.lnk');$s.TargetPath='%CD%\dist\FanqiePublisher_PRO.exe';$s.WorkingDirectory='%CD%';$s.IconLocation='%CD%\logo.ico';$s.Save()"
echo 桌面快捷方式已成功创建！
echo.
echo ===========================================
echo 打包完成！
echo 请前往 dist/ 文件夹下查看 FanqiePublisher_PRO.exe 软件
echo 注意：软件自带了网页UI界面，运行效果类似 Electron 应用。
echo 如果启动白屏，请检查客户机是否自带了 Edge WebView2 (Win10/11 默认自带)。
echo ===========================================
pause

NAView 二级结构绘图  v1.3.0   （免安装版）
==========================================================

怎么用
------
1. 把 NAView.exe 拷到目标电脑任意位置（桌面、U 盘、文件夹都行）。
2. 双击运行。不需要装 Python，不需要装任何东西。
3. 左边填「序列」和「结构」→ 点「预览」→ 右边调颜色和线宽 →
   点「保存 SVG …」导出矢量图。

它需要什么
----------
* Windows 10 / 11，64 位。别的系统（macOS、Linux）请用源码版：
  整个 naview 文件夹拷过去，装个 Python 3.8+ 就能跑。
* 第一次启动会慢 1～3 秒（单文件 exe 要先把自己解压到临时目录），
  之后正常。
* 如果 Windows 弹出「已保护你的电脑」（SmartScreen）：
  点「**更多信息**」→「**仍要运行**」。
  这是没买代码签名证书的个人程序都会有的提示——就算买了证书（OV/EV），
  第一次下载也照样提示，只是会显示发布者名字，之后慢慢攒信誉。
* 校验文件有没有被改过（可选）。本版 NAView.exe 的 SHA-256：

      96F062085FD33D0097ED16DC24C36EA73C61920809B30A283FE3763030C5FE85

  在 PowerShell 里比对：

      Get-FileHash .\NAView.exe -Algorithm SHA256

参数存在哪
----------
点界面上的「保存为默认」之后，参数会写在：

    NAView.exe 旁边的 naview-settings.json

也就是说：把 exe 和这个 json 一起拷走，配色/字号/线宽/旋转都会跟着走。
如果 exe 放在只读位置（比如光盘、Program Files），会自动改写用户目录下的
~/.naview-settings.json，状态栏会告诉你实际写到了哪里。

这个 json 是纯文本，可以用记事本直接改（存成 UTF-8 带不带 BOM 都认）。

包含什么
--------
* 图形界面（tkinter，已打包进 exe）
* NAView 算法核心（与 ViennaRNA 参考实现逐位一致）
* SVG 导出（矢量，放大不糊，可再导入 Illustrator / Inkscape / Word）

限制
----
* 只能导出 SVG，不能导出 PNG。要 PNG 的话：SVG 用浏览器打开截图，
  或装个 cairosvg 转一下。
* 想重新打包：见 naview/README.md 的「打包成 exe」一节。

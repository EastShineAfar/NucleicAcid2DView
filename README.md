# NAView —— DNA/RNA 二级结构绘图（图形界面 + 命令行）

用 Python 实现的 **NAView** 布局算法（Bruccoleri & Heinrich, *CABIOS* 4:167–173, 1988），
把 DNA/RNA 的二级结构画成平面图。带图形界面，也能命令行直接出图。

- 🖥 **图形界面**：左边预览、右边设置；输入序列和结构 → 点「预览」→ 存成 SVG
- 🎨 **配色可调**：四种碱基的圆环填充色、字母颜色都能单独改，另有圆环描边 / 骨架线 / 配对线颜色
- 🔠 **尺寸与线宽可调**：字号、圆环半径，以及骨架线 / 配对线 / 环描边三条线宽各自独立调节
- 🔃 **方向可调**：5′ 端在下方（默认）或上方；另有**任意角度旋转**，字母始终正立
- 📏 **单横线配对**，可在界面里切换成双横线
- 💾 **参数可保存**：一键「保存为默认」，下次打开照旧
- 📦 **两种用法**：Windows 直接双击打包好的 `NAView.exe`（免安装）；或拷源码（纯标准库，跨平台）
- ✅ **带自检脚本**：`tests/` 里算法 233 项、界面 61 项、参数 41 项，改完跑一遍就知道有没有画坏

---

## 一、用图形界面

启动方式：

| 环境 | 怎么做 |
|---|---|
| Windows（免安装 exe） | 双击 `NAView.exe`（见第四节） |
| Windows（源码） | 双击 `启动绘图界面.cmd`（等价于 `launcher.cmd`） |
| Linux / macOS | `./run-gui.sh` |
| 任何平台 | `python gui.py` |

界面长这样（`examples/preview_gui.png` 是实拍）：**左边是预览，右边是设置面板**。

```
┌────────────────────────────────────────┬──────────────────────┐
│                                        │ 输入                 │
│                                        │  序列 [GCGCAAAAGCGC] │
│                                        │  结构 [((((....))))] │
│                                        │  示例 [发夹 hairpin▾]│
│                                        │  + 或 & 分隔不同链   │
│             预 览 区                    ├──────────────────────┤
│                                        │ 配色                 │
│        （滚轮缩放 / 按住左键拖动）        │  碱基 圆环填充 字母  │
│                                        │   A    [■]     [■]   │
│                                        │   C    [■]     [■]   │
│                                        │   G    [■]     [■]   │
│                                        │   T/U  [■]     [■]   │
│                                        │  圆环描边[■] 骨架线[■]│
│                                        │           配对线[■]  │
│                                        ├──────────────────────┤
│                                        │ 尺寸与线宽           │
│                                        │  字号 6.0   圈径 6.2 │
│                                        │  骨架线2.0  配对线2.0│
│                                        │  环描边2.0           │
│                                        ├──────────────────────┤
│                                        │ 样式                 │
│                                        │  ◉单横线  ○双横线    │
│                                        │  ☑显示碱基字母 ☑显示配对线│
│                                        │  ☑显示骨架线  ☑起点在下方│
│                                        │  ☑自动优化间距        │
│                                        │  旋转 [====|====] 0.0 度│
│                                        │  [保存为默认][恢复出厂]│
├────────────────────────────────────────┤                      │
│ [预览 Ctrl+Enter][保存 SVG…][适应窗口]  │                      │
├────────────────────────────────────────┴──────────────────────┤
│ 预览已更新：12 个碱基 / 4 对配对 / 1 条链 / 2 个环             │
└───────────────────────────────────────────────────────────────┘
```

### 操作要点

| 想做什么 | 怎么做 |
|---|---|
| 出图 | 填好序列和结构，点 **预览**（或按 <kbd>Ctrl</kbd>+<kbd>Enter</kbd> / <kbd>F5</kbd>） |
| 改某个碱基的圆环色 / 字母色 | 「配色」里点对应那一列的色块 → 弹出取色器 |
| 改圆环描边 / 骨架线 / 配对线颜色 | 「配色」最下面三个色块 |
| **改碱基字号 / 圆环半径** | 「尺寸与线宽」里的 **字号**、**圈径**（默认 6.0 / 6.2） |
| **改线粗细** | 「尺寸与线宽」里的 **骨架线**、**配对线**、**环描边**（默认都是 2.0） |
| **5′ 端从下方 / 上方开始** | 勾选 / 取消「**起点在下方**」（默认勾选） |
| **旋转整幅图** | 拖「样式」里的 **旋转** 滑块；右边数字框可直接输入角度（步进 15°） |
| **让相邻碱基间距更均匀 / 不重叠** | 保持「**自动优化间距**」勾选（默认） |
| 单横线 ↔ 双横线 | 「样式」里的单选钮，立刻生效 |
| 只看骨架 / 不要字母 | 取消勾选「显示碱基字母」等 |
| 放大缩小 / 平移 | 预览区滚轮；或按住左键拖动 |
| 回到全览 | 点 **适应窗口** |
| **把当前参数存下来** | 点「**保存为默认**」 |
| 一键回到出厂参数 | 点「**恢复出厂**」（只改界面，不写文件；要保留再点「保存为默认」） |
| 导出 | 点 **保存 SVG …**，选路径即可 |

> 配色和尺寸的改动**即时**生效，不需要重新点预览；换了序列或结构才需要重新预览。

---

## 二、记住你的参数

点「**保存为默认**」之后，配色、字号、圈径、线宽、方向、旋转角度、各个开关都会写到：

```
源码版：  naview/naview-settings.json          ← 放在程序旁边
exe 版：  naview-exe/naview-settings.json      ← 放在 NAView.exe 旁边
```

下次打开界面自动读取，完全按上次的样子显示。

* 纯文本 JSON，可以用记事本直接改（存成 UTF-8 带不带 BOM 都认）。
* 放在程序旁边是故意的：**整个文件夹（或 exe + json）拷到别的电脑，参数也跟着走**。
* 文件夹只读时（比如装在 `Program Files`）会自动改写到 `~/.naview-settings.json`，
  状态栏会告诉你实际写到了哪里。
* 想回到出厂状态：删掉这个 json，或点「恢复出厂」后再「保存为默认」覆盖掉。

> 命令行**不读**这个文件，只认命令行参数，这样脚本行为不会因为你点过界面而改变。

---

## 三、命令行用法

```bash
# 序列 + 结构
python draw_ss.py --seq GCGCAAAAGCGC --struct "((((....))))" -o hairpin.svg

# 只给结构（碱基字母留空）
python draw_ss.py --struct "...((....))...(((..((((....)))).)))" -o seq60.svg

# 双横线 + 纯黑字母
python draw_ss.py --seq GCGCAAAAGCGC --struct "((((....))))" \
                  --pair-style double --mono -o mono.svg

# 放大字号和圆环，并让 5′ 端回到上方
python draw_ss.py --seq GCGCAAAAGCGC --struct "((((....))))" \
                  --font-size 12 --ring-radius 9 --no-flip-y -o big.svg

# 调线宽
python draw_ss.py --seq GCGCAAAAGCGC --struct "((((....))))" \
                  --backbone-width 0.6 --pair-width 2.5 --ring-width 0.4 -o lines.svg

# 旋转 90°，从文件读（可同时含 FASTA 序列和点括号行），或用 - 读标准输入
python draw_ss.py myinput.txt --rotation 90 -o out.svg
cat myinput.txt | python draw_ss.py - -o out.svg

# 只要坐标
python draw_ss.py --struct "((((....))))" --coords
```

| 开关 | 作用 |
|---|---|
| `-o FILE` | 输出 SVG（不给则输出到标准输出） |
| `--pair-style single\|double` | 配对线画一条还是两条（默认 `single`） |
| `--font-size N` | 碱基字母字号（图形像素；默认 6.0） |
| `--ring-radius N` | 碱基圆环半径（图形像素；默认 6.2） |
| `--backbone-width N` | 骨架线宽（图形像素；默认 2.0） |
| `--pair-width N` | 配对线宽（图形像素；默认 2.0） |
| `--ring-width N` | 圆环描边宽（图形像素；默认 2.0） |
| `--flip-y` / `--no-flip-y` | 5′ 端在下方（默认）/ 上方 |
| `--rotation DEG` | 整幅图旋转多少度（默认 0；字母不跟着转） |
| `--even-loops` / `--no-even-loops` | 强制 / 禁止均化各环圆心角（默认自动择优） |
| `--reference` | 关掉所有间距后处理，输出原始 NAView 布局 |
| `--mono` | 灰色圆环 + 黑色字母 |
| `--title TEXT` | 图标题 |
| `--base-distance N` | 每个 NAView 单位的像素数，默认 20 |
| `--no-bases` / `--no-pairs` / `--no-backbone` | 关掉对应元素 |
| `--open` | 生成后自动打开 |
| `--coords` | 输出坐标表（`序号 x y 配对对象`） |

---

## 四、拷到别的电脑

### 1. 免安装 exe（目标电脑什么都不用装）

拷这一个文件就行：

```
NAView.exe            （约 13 MB，Windows 64 位）
```

双击即用。参数保存在 **exe 旁边**的 `naview-settings.json`，
所以「exe + 那个 json」一起拷走，配色/字号/线宽/旋转都会跟着走。

* 单文件 exe 每次启动要先把自己解压到临时目录，**第一次启动慢 1～3 秒**。
* 只能在 64 位 Windows 上用。macOS / Linux 用下面的源码版。

**关于「已保护你的电脑」提示（SmartScreen）**：本程序没有买代码签名证书，
第一次运行 Windows 可能弹提示，点「**更多信息**」→「**仍要运行**」即可，之后不再提示。

> 买证书能不能消掉它？**基本不能。** 微软官方文档写明：有效的 OV/EV 证书第一次下载
> **仍然**会警告（只是显示发布者名字），声誉要按「文件哈希 / 证书」慢慢累积；
> **EV 证书早已不能绕过 SmartScreen**；自签名证书的提示行为跟完全不签名一模一样。
> 要做到下载即无提示，只能走 Microsoft Store。
> 参见 [SmartScreen 声誉（Microsoft Learn）](https://learn.microsoft.com/zh-cn/windows/apps/package-and-deploy/smartscreen-reputation)。

校验文件没被改过（可选）：

```powershell
Get-FileHash .\NAView.exe -Algorithm SHA256
# 本版应为 96F062085FD33D0097ED16DC24C36EA73C61920809B30A283FE3763030C5FE85
```

**自己重新打包**（需要 Python + PyInstaller）：

```powershell
pip install pyinstaller
python -m PyInstaller --noconfirm --clean --onefile --windowed `
    --name NAView --icon naview\appicon.ico --add-data "naview\appicon.ico;." `
    --distpath naview-exe --workpath exe-build --specpath exe-build naview\gui.py
```

### 2. 源码版（有 Python 就行，跨平台）

整个 `naview` 文件夹拷过去就能用，**没有第三方依赖**。要求 Python 3.8 以上并带 tkinter：

| 平台 | 说明 |
|---|---|
| **Windows** | 从 [python.org](https://www.python.org/downloads/) 装官方版即可，**默认勾选了 `tcl/tk and IDLE`**。装完双击 `启动绘图界面.cmd`。 |
| **macOS** | 官方 python.org 安装包自带 tkinter。 |
| **Ubuntu/Debian** | 额外装一次：`sudo apt install python3-tk` |

没装 Python 时，启动器会弹出提示并给出下载地址，不会静默失败。

---

## 五、在 Python 里调用（可选）

```python
import sys
sys.path.insert(0, 'naview')          # naview 文件夹所在路径

from naview import parse_dot_bracket, naview_layout
from render_svg import render_svg

layout = naview_layout(parse_dot_bracket('((((....))))'))
layout.xs, layout.ys                  # 每个碱基的坐标（NAView 单位）
layout.warnings                       # 算法告警

svg = render_svg(layout, 'GCGCAAAAGCGC',
                 font_size=6.0, ring_radius=6.2,   # 图形像素
                 backbone_width=2.0, pair_width=2.0, ring_width=2.0,
                 flip_y=True,                      # True: 5′ 端在下方
                 rotation=0.0)                     # 整幅图旋转角度
open('out.svg', 'w', encoding='utf-8').write(svg)
```

---

## 六、目录结构

```
naview/
├── gui.py              图形界面（tkinter，仅标准库）
├── naview.py           布局算法：点括号解析 + NAView
├── render_svg.py       图元构建 + SVG 导出
├── draw_ss.py          命令行入口
├── settings.py         参数持久化（naview-settings.json）
├── appicon.ico         程序图标
├── 启动绘图界面.cmd / launcher.cmd / run-gui.sh    启动器
├── tests/              自检脚本（算法 233 项 / 界面 61 项 / 参数 41 项）
└── examples/           示例 SVG、预览图、界面截图
```

---

## 七、已知限制

- **不支持假结**：NAView 要求结构是一棵树，输入 `([)]` 这类交叉配对会直接报错并说明原因。
- **只画图，不做折叠预测**：结构请用 NUPACK / ViennaRNA / mfold 等算好再粘进来。
- **只实现了 NAView 一种布局**，几何与 VARNA 的 naview 模式有出入，不是像素级一致。
- 导出只有 SVG；要 PNG 可以再拿 SVG 转（浏览器打开截图，或 `cairosvg`）。

---

## 八、出处与许可

算法出自 R.E. Bruccoleri & G. Heinrich, *Computer Applications in the Biosciences*
**4**(1):167–173, 1988。

参考实现是 `naview.c`（Copyright © 1988 Robert E. Bruccoleri，允许非商业用途的复制），
本项目据此用 Python 重写，不含 GPL 项目（如 VARNA）的代码。

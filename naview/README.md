# NAView —— DNA/RNA 二级结构绘图（图形界面 + 命令行）

用 Python 从零实现的 **NAView** 算法，画 DNA/RNA 二级结构。
NAView（Bruccoleri & Heinrich, *CABIOS* 4:167–173, 1988）就是
**VARNA 的 `naview` 模式**和 **ViennaRNA 默认布局**所用的算法。

- 🖥 **带图形界面**：**预览在左、设置面板在右**；输入序列和结构 → 点「预览」→ 直接看图 → 存成 SVG
- 🎨 **配色可调**：四种碱基的**圆环填充色**和**字母颜色**都能单独改，另有圆环描边 / 骨架线 / 配对线颜色
- 🔠 **尺寸与线宽可调**：字号、圆环半径，以及**骨架线 / 配对线 / 环描边三者的粗细各自独立调节**
- 🔃 **方向可调**：5′ 端在**下方**（默认，与 VARNA 一致）或上方
- 🔄 **任意角度旋转**：滑块实时旋转整幅图，**碱基字母始终正立**（见第五节）
- 📏 **单横线配对**（可在界面里切换成双横线）
- ⚖️ **自动优化间距**：修掉 NAView 原版两个毛病——"长尾巴被压扁、旁边碱基却被扯开"，以及"单个碱基的凸环压在螺旋中间导致字母重叠"（见第五节）
- 💾 **参数可保存**：配色、尺寸、线宽、方向、开关一键「保存为默认」，下次打开照旧（见第二节）
- 📦 **两种用法**：Windows 上直接双击打包好的 **`NAView.exe`**（免安装、对象电脑不用装 Python）；
  或者拷整个 `naview` 文件夹用源码版（纯标准库，不需要 numpy / Java / WSL，跨平台）
- ✅ **逐位可验证**：核心算法与 ViennaRNA 的参考实现（同一份 C 代码）完全一致，误差仅 float32 舍入

---

## 一、启动图形界面

**Windows（免安装 exe，推荐）**：双击 `naview-exe\NAView.exe`（见第四节）

**Windows（源码）**：双击 `启动绘图界面.cmd`（等价于 `launcher.cmd`）

**Linux / macOS**：`./run-gui.sh`

**任何平台**：`python gui.py`

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
| 改某个碱基的圆环色 | 「配色」里点圆环填充那一列的色块 → 弹出取色器 |
| 改某个碱基的字母色 | 「配色」里点字母颜色那一列的色块 |
| 改圆环描边 / 骨架线 / 配对线颜色 | 「配色」最下面三个色块 |
| **改碱基字号 / 圆环半径** | 「尺寸与线宽」里的 **字号**、**圈径**（默认 7.5 / 5.0） |
| **改线粗细** | 「尺寸与线宽」里的 **骨架线**、**配对线**、**环描边**（默认都是 1.0） |
| **让 5′ 端从下方开始 / 从上方开始** | 勾选 / 取消「**起点在下方**」（默认勾选，与 VARNA 一致） |
| **旋转整幅图** | 拖「样式」里的 **旋转** 滑块；右边的数字框可直接输入精确角度（步进 15°） |
| **让相邻碱基间距更均匀 / 不重叠** | 保持「**自动优化间距**」勾选（默认）；取消只关掉"均化圆心角"那一道，凸环撑开仍然生效 |
| 单横线 ↔ 双横线 | 「样式」里的单选钮，立刻生效 |
| 只看骨架 / 不要字母 | 取消勾选「显示碱基字母」等 |
| 放大缩小 | 预览区滚轮；或按住左键拖动平移 |
| 回到全览 | 点 **适应窗口** |
| **把当前参数存下来，下次打开照旧** | 点「**保存为默认**」 |
| 一键回到出厂参数 | 点「**恢复出厂**」（只改界面，不写文件；要保留再点「保存为默认」） |
| 导出 | 点 **保存 SVG …**，选路径即可 |

> 配色和尺寸的改动都是**即时**生效的，不需要重新点预览。
> 换了序列或结构才需要重新点「预览」。
> 窗口大小改变时图形会自动重新适应，直到你手动缩放为止。

---

## 二、记住你的参数

调好配色、字号、圈径、线宽、方向、**旋转角度**、开关之后，点一下 **「保存为默认」**，
这些参数（**包括所有颜色**）就会写到：

```
源码版：  naview/naview-settings.json          ← 放在程序旁边
exe 版：  naview-exe/naview-settings.json      ← 放在 NAView.exe 旁边
```

下次打开界面会自动读取，完全按上次的样子显示。

* 这个文件是**纯文本 JSON**，可以直接用记事本看一眼或手工改
  （存成 UTF-8 带不带 BOM 都认）。
* 放在程序旁边是故意的：**整个 `naview` 文件夹（或 exe + json）拷到别的电脑，参数也跟着走**。
* 如果这个文件夹是只读的（比如装在 `Program Files`），会自动改写到用户目录
  `~/.naview-settings.json`，状态栏会告诉你实际写到了哪里。
* 想彻底回到出厂状态：删掉这个 json 文件，或点「恢复出厂」后再点「保存为默认」覆盖掉。

| 按钮 | 作用 |
|---|---|
| **保存为默认** | 把界面当前参数写进 json，下次启动生效 |
| **恢复出厂** | 把界面恢复成内置出厂参数（**不写文件**，重启后会回到你保存的那套） |

> 命令行也读同一套文件吗？**不读**。命令行只认命令行参数，
> 这样脚本行为不会因为你在界面里点了什么而改变。
> 需要固定一套命令行风格就用别名或写个小脚本。

---

## 三、命令行用法

不想要界面也能直接出图：

```bash
# 序列 + 结构
python draw_ss.py --seq GCGCAAAAGCGC --struct "((((....))))" -o hairpin.svg

# 只给结构（碱基字母留空）
python draw_ss.py --struct "...((....))...(((..((((....)))).)))" -o seq60.svg

# 双横线 + VARNA 那种纯黑字母
python draw_ss.py --seq GCGCAAAAGCGC --struct "((((....))))" \
                  --pair-style double --mono -o varna_look.svg

# 放大字号和圆环，并让 5′ 端回到上方
python draw_ss.py --seq GCGCAAAAGCGC --struct "((((....))))" \
                  --font-size 12 --ring-radius 9 --no-flip-y -o big.svg

# 调线宽：骨架线细、配对线粗、圆环描边很细
python draw_ss.py --seq GCGCAAAAGCGC --struct "((((....))))" \
                  --backbone-width 0.6 --pair-width 2.5 --ring-width 0.4 -o lines.svg

# 从文件读（可同时含 FASTA 序列和点括号行），或用 - 读标准输入
python draw_ss.py myinput.txt -o out.svg
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
| `--reference` | 关掉所有后处理，逐位等于 ViennaRNA 的参考 NAView |
| `--mono` | 灰色圆环 + 黑色字母（VARNA 的默认观感） |
| `--title TEXT` | 图标题 |
| `--base-distance N` | 每个 NAView 单位的像素数，默认 20（ViennaRNA 用 15） |
| `--no-bases` / `--no-pairs` / `--no-backbone` | 关掉对应元素 |
| `--open` | 生成后自动打开 |
| `--coords` | 输出坐标表（`序号 x y 配对对象`） |

---

## 四、拷贝到别的电脑

有两种办法，看目标电脑有没有 Python。

### 1. 免安装 exe（推荐，目标电脑什么都不用装）

已经打好包，直接拷这一个文件就行：

```
E:\AIspace\naview-exe\NAView.exe        （约 13 MB，Windows 64 位）
E:\AIspace\naview-exe\使用说明.txt
```

双击即用。参数保存在 **exe 旁边**的 `naview-settings.json`，
所以「exe + 那个 json」一起拷走，配色/字号/线宽/旋转都会跟着走。

* 单文件 exe 每次启动要先把自己解压到临时目录，**第一次启动慢 1～3 秒**。
* 只能在 64 位 Windows 上用。macOS / Linux 请用下面的源码版。

#### 关于「已保护你的电脑」提示（SmartScreen）

**这个程序没有买代码签名证书**，所以第一次运行时 Windows 可能弹
「Windows 已保护你的电脑」：

```
更多信息(D)  →  仍要运行(R)
```

点这两下就能正常用，之后不再提示。需要的话可以核对文件没被改过，
本版 `NAView.exe` 的 SHA-256：

```
96F062085FD33D0097ED16DC24C36EA73C61920809B30A283FE3763030C5FE85
```

```powershell
Get-FileHash .\NAView.exe -Algorithm SHA256
```

> 花钱买证书能不能消掉这个提示？**基本不能。** 微软官方文档写得很清楚：
> 有效的 OV/EV 证书第一次下载**仍然**会警告（只是会显示发布者名字），
> 声誉要按「文件哈希 / 证书」慢慢累积（通常要数周、数百次全新安装）；
> 而且 **EV 证书早就不能绕过 SmartScreen 了**，
> 微软明说「仅仅为了规避 SmartScreen 警告而为 EV 支付额外费用，已经没有理由了」；
> 自签名证书的提示行为跟完全不签名**一模一样**。
> 真要做到下载即无提示，只有走 Microsoft Store（商店里的应用由微软重新签名）。
> 参见 [SmartScreen 声誉（Microsoft Learn）](https://learn.microsoft.com/zh-cn/windows/apps/package-and-deploy/smartscreen-reputation)。

#### 自己重新打包

```powershell
pip install pyinstaller
powershell -ExecutionPolicy Bypass -File E:\AIspace\deploy\build-exe.ps1
```

脚本做的事就是这一条命令（图标、单文件、无控制台窗口，
并把 `appicon.ico` 一起打进去给窗口当图标）：

```powershell
python -m PyInstaller --noconfirm --clean --onefile --windowed `
    --name NAView --icon naview\appicon.ico --add-data "naview\appicon.ico;." `
    --distpath naview-exe --workpath exe-build --specpath exe-build naview\gui.py
```

> 打成 exe 之后**只能在打包时的那个平台用**（Windows 的 exe 到 mac 上跑不了），
> 所以源码版仍然保留——跨平台、体积小、随时能改。

### 2. 源码版（有 Python 就行，跨平台）

整个 `naview` 文件夹（约 100 KB）直接拷过去就能用，**没有第三方依赖**。

**唯一的要求**：目标电脑有 Python 3.8 以上，并且带 tkinter。

| 平台 | 说明 |
|---|---|
| **Windows** | 从 [python.org](https://www.python.org/downloads/) 装官方版即可，**默认就勾选了 `tcl/tk and IDLE`**。装完双击 `启动绘图界面.cmd`。 |
| **macOS** | 官方 python.org 安装包自带 tkinter。 |
| **Ubuntu/Debian** | 需要额外装一次：`sudo apt install python3-tk` |

如果目标电脑**完全没装 Python**，界面启动器会弹出明确提示并给出下载地址，
不会静默失败。

---

## 五、算法说明

`naview.py` 的核心思路：

1. **分解**：把结构拆成 *region*（连续堆叠的碱基对，即螺旋）和 *loop*
   （外环、发夹环、凸环、内环、多分支环），两者构成一棵树。
2. **定根**：选分支最多、层次最深的环作为根（通常就是外环），从它开始铺。
3. **摆环**：每个环画成一个圆，半径由**最小二乘**求出——目标是让环上相邻碱基的距离尽量等于 1 个单位。
4. **画螺旋**：region 画成标准梯子，每级间距恰好 1 个单位。
5. **挤出（extrusion）**：如果某段在圆上摆不下（会互相压住），就把该连接标记为
   `extruded`，推到圆外，改用直线 + 圆弧过渡。
6. **兜底**：完全没配对的序列会被内部伪造成一个假配对，让所有碱基均匀分布在一个圆上。

坐标是 NAView 原生单位（1 单位 = 一个碱基对的升高），**+y 向上**；
渲染层负责翻成屏幕/SVG 的 y 向下。

### 渲染是怎么组织的

`render_svg.py` 分成两层，这是为了让**界面预览和 SVG 导出永远一致**：

```
build_primitives()  ->  一串 line / circle / text 图元（唯一的"长什么样"的地方）
        ├── render_svg()          序列化成 SVG 文件
        └── gui.py 的 Canvas      原样重放到预览区
```

几何默认值取自 VARNA 3.93 自己的 SVG 导出的量测，但**本项目的默认更粗壮一些**
（大圆环 + 粗线条，屏幕和印刷都更清楚），以碱基间距为基准等比缩放：

| 元素 | VARNA 实测 | 本实现默认 | 间距 20 时 |
|---|---|---|---|
| 碱基圆盘半径 | 0.2469 | **0.31** × 间距 | **6.2 px** |
| 字母字号 | 0.3704 | **0.30** × 间距 | **6.0 px** |
| 双横线偏移 | ±0.0617 | ±0.0625 × 间距（且不小于线宽） | ±2.0 px |
| 线宽 | 0.0494 | **0.10** × 间距 | **2.0 px** |
| 骨架线端点缩进 | = 圆盘半径 | 同左 | 6.2 px |

> 这些数值在界面里都能改，改完点「**保存为默认**」就会记住（见第二节）。
> 双横线的两根线会自动拉开到不小于线宽，所以线调粗了也不会糊成一条。

所有线段都会按圆盘半径缩进，避免压住字母。

### 关于方向

NAView 算出来的坐标是 **+y 向上**的数学坐标系（ViennaRNA 直接按这个出图，
所以 5′ 端在上面）。VARNA 画到 SVG 时把它翻了过来，**5′ 端在下面**。

本项目的默认行为跟 VARNA 一致（`flip_y=True`），
在上面还是下面由 `flip_y` / 界面上的「起点在下方」控制——它做的是**整幅图上下镜像**，
不改变任何几何关系。

### 关于「均匀间距」：两道后处理

NAView 原版有两个会看得出来的毛病，本项目在**默认路径**上各加了一道独立的后处理，
都只动未配对的碱基，不动螺旋，也都不改核心算法。

#### 毛病一：长尾巴被压扁、旁边的短缺口却被扯开

同一个环里，各段未配对碱基的间距会差很多。原因在算法内部：
NAView 给每个"缺口"分配的圆心角，来自"圆圈示意图"里该碱基对弦的**法线方向**，
这个角度**和缺口里实际有多少个碱基没有关系**。

以 60 nt 那条（`...((....))...(((..((((....)))).))).........................`）为例：

| 相邻碱基 | 原版 NAView | 均化后 |
|---|---|---|
| 螺旋内 | 1.000 | 1.000 |
| **11–12 … 14–15**（两段螺旋之间的 3 个碱基） | **1.831** | **1.042** |
| **尾部 35→60（25 个碱基）** | **0.660** | **0.991** |

这不是实现错误——ViennaRNA 自己画同一结构**也一样不均匀**，VARNA 的改版稍好但同样存在。

#### 毛病二：单个碱基的凸环被压在两段螺旋中间

当一段未配对碱基两侧的锚点靠得比键数还近时，NAView 把它们**沿圆弧插值**，
结果全被挤在两点连线上。最典型的是 1×0 凸环：

```
GGGCGAGAACGAGTGTCCCAGTCGCTAGTTTTCTCTGCCC
((((((((((((.((...)).)))......))))).))))
                              ↑ 这个单碱基凸环
```

原版这里两个键长只有 **0.655 / 0.527**，字母直接叠在一起。

修法是把它**鼓出去**：以两侧锚点为端点，作一段**每根弦恰好 1 个单位长**的圆弧
（解 `d = sin(n·α) / sin(α)`，用二分法；参考实现里的 `find_center_for_arc`
在弦长 < 1 时会因 `acos` 越界直接放弃，正好就是这种情况）。
圆弧可以落在锚点连线的两侧，取**离其他碱基更远**的那一侧。

#### 两道后处理怎么配合

关键点是：**第一道（均化圆心角）会移动整幅图，有时会把小凸环挤得更紧。**
实测在 1×0 凸环那个结构上，开了均化反而让贴近数从 0 升到 4。

所以默认行为不是二选一，而是 **`even_loops='auto'`**：
**两种都算一遍，按「非相邻碱基贴近数优先、键长均匀度次之」挑更好的那个。**

| 测试用例 | 原版 | 只均化 | 只成链 | 默认（自动） |
|---|---|---|---|---|
| 1×0 凸环结构 | 0.20–1.13，贴近 5 | 0.27–1.13，贴近 2 | 0.99–1.13，贴近 0 | **0.99–1.13，贴近 0** |
| seq60 | 0.66–1.83，贴近 0 | 0.89–1.18，贴近 0 | 0.82–1.83，贴近 0 | **0.89–1.18，贴近 0** |

两个结构各自选到了对的那一边。全部 9 个测试结构上，默认设置的非相邻贴近数都是 **0**。

简单结构（发夹、无配对序列等）**结果完全不变**。

#### 想关掉 / 想固定

```bash
python draw_ss.py ...                 # 默认：自动
python draw_ss.py ... --even-loops    # 强制开均化
python draw_ss.py ... --no-even-loops # 绝不均化
python draw_ss.py ... --reference     # 两道后处理都关，逐位等于 ViennaRNA
```

```python
naview_layout(structure)                            # 默认（自动）
naview_layout(structure, even_loops=False)          # 不均化
naview_layout(structure, even_loops=False,
              even_bonds=False)                     # 纯参考实现
from naview import layout_cost
layout_cost(layout)      # (贴近数, 键长极差比)，越小越好
```

界面「样式」里的 **「自动优化间距」** 勾选框默认打开；取消就是 `--no-even-loops`。

---

### 关于旋转

「旋转」只做一件事：**把每个碱基的坐标绕图形中心转一个角度**。
字母是在坐标定好之后才画上去的，永远是正立的，所以怎么转都不会躺倒。

这也意味着旋转**不需要重新算布局**——拖动滑块时只是把坐标转一下重画，
所以是即时的，不会因为拖滑块而反复跑算法。

```bash
python draw_ss.py --seq GCGCAAAAGCGC --struct '((((....))))' --rotation 90 -o flat.svg
```

```python
render_svg(layout, seq, rotation=45)      # 正数 = 屏幕上逆时针
```

- 角度按 360 取模，`360` 等于 `0`。
- 画布尺寸会跟着旋转后的包围盒变化（90° 时宽高互换），
  界面在自动适应状态下会重新适配窗口，也可随时点「适应窗口」。
- 对比图见 `examples/rot_r0.png` 与 `examples/rot_r90.png`。

---

## 六、验证

### 1. 与 ViennaRNA 参考实现逐位一致 ✅

`naview.py` 的核心是 `naview.c`（Bruccoleri 原始代码，ViennaRNA 收录为
`vrna_plot_coords_naview_pt()`）的逐函数移植。ViennaRNA 在该函数之后
只做了一步 `X = 100 + 15x` 的仿射变换，所以一个正确的移植必须**数值上完全相同**。

`tests/compare_vienna.py` 用 `even_loops=False` 运行——即不启用「均匀间距」
后处理——以便把算法本身钉死：

```
case       n     max|dx|        max|dy|        verdict
hairpin    12    3.615e-06      1.734e-06      IDENTICAL
bulge      21    3.690e-06      6.324e-06      IDENTICAL
twostem    23    6.063e-06      2.821e-06      IDENTICAL
multiloop  28    7.134e-06      3.681e-06      IDENTICAL
threestem  37    7.176e-06      6.939e-06      IDENTICAL
seq60      60    7.514e-06      7.360e-06      IDENTICAL
unpaired   12    3.148e-06      3.720e-06      IDENTICAL
```

误差量级就是 float32 的精度极限，等于**逐位吻合**。

### 2. 与 VARNA 的差异（如实说明）⚠️

VARNA 的 `fr.orsay.lri.varna.models.naView` 虽然也是 naview.c 的 Java 移植
（类名 `Base` / `Region` / `Loop` / `Connection` / `Radloop` 一一对应），
但**几何上做了自己的改动**：

| | 参考 NAView（本实现 / ViennaRNA） | VARNA 3.93 `-algorithm naview` |
|---|---|---|
| 螺旋：横档 / 升高 | **1.00** | **1.67** |
| 发夹环步长 / 升高 | 1.093 | 1.356 |

具体表现就是 **VARNA 画出来的螺旋明显更宽**。
`tests/compare_varna.py` 给出的偏离量（相似变换对齐后）：
发夹 9.2%、凸环 5.5%、双茎 4.6%、多分支 4.1%、seq60 26.3%。

拓扑、配对集合、环的分支结构都一致，差异集中在比例上。

> 另外要注意：**VARNA 的默认绘图模式并不是 naview，而是 `radiate`**。
> 在 varnaapi 里 `CHOICES_DEFAULT = {'algorithm': 'radiate'}`，
> 所以你在网页版里看到的图其实是 radiate 布局。

本项目选择**忠实复现参考 NAView**，而不是模仿 VARNA 的改版——
因为前者可以对着权威实现逐位验收，后者只能靠肉眼接近。
如果你更想要「宽螺旋」的观感，把 `render_svg.py` 里的
`R_BP_OFFSET` 之类比例调大即可（但那只影响粗细，不影响螺旋实际宽度）。

### 3. 自动化测试 ✅

```bash
python tests/test_naview.py      # 233 项：算法与解析（含后处理的回归）
python tests/test_settings.py    #  41 项：参数持久化（不需要显示器）
python tests/test_gui.py         #  61 项：界面逻辑（会真的建窗口）
python tests/compare_vienna.py   #   7 项：与 ViennaRNA 逐位比对（验收）
python tests/compare_varna.py    #       与 VARNA 的差异报告（参考）
```

`test_gui.py` 会真实创建窗口、跑预览、切样式、改颜色、改字号/圈径、
**改三条线宽、翻转方向、旋转并确认字母仍然正立**、**把参数存成默认、再开一个新窗口验证它确实被读回来**、
导出 SVG、验证缩放，全程不需要人点。
它也会检查**预览确实在侧栏左边且更宽**、侧栏没有被挤没、状态栏可见、
图形既不超出画布又能填满画面等布局问题。

其中专门有一组测试盯着这两道后处理：确认原版布局确实不均匀（max/min > 2）、
均化能把它降到 1.6 以下、1×0 凸环的两个键长在默认下变成 1.0、
**默认设置下所有测试结构都没有非相邻碱基互相贴近**、
**自动模式永远不会比强制选择更差**，以及螺旋间距仍然是精确的 1.0。

`test_settings.py` 不需要显示器，专门测参数文件：出厂默认值正确、存/读往返一致、
**文件被改坏或写进非法值（字符串、负数、坏 JSON）时能安全回退到出厂值**
而不是让界面崩掉；还有两条专门盯着打包成 exe 之后的行为——
**参数要写在 exe 旁边**（不是解压出来的临时目录），
以及**用记事本存成「UTF-8 带 BOM」的 json 也要能读**。

---

## 七、目录结构

```
naview/
├── 启动绘图界面.cmd     ★ Windows 双击启动（= launcher.cmd）
├── launcher.cmd           同上，ASCII 文件名版本
├── run-gui.sh             Linux / macOS 启动
├── gui.py               ★ 图形界面（tkinter，仅标准库）
├── settings.py            参数持久化（读写 naview-settings.json）
├── naview.py            ★ 算法核心：解析 + 布局
├── render_svg.py        ★ 图元构建 + SVG 导出
├── draw_ss.py           ★ 命令行入口
├── appicon.ico            程序图标（窗口和 exe 都用它）
├── README.md              本文件
├── tests/
│   ├── test_naview.py       算法自检 233 项
│   ├── test_gui.py          界面自检 61 项
│   ├── test_settings.py     参数持久化自检 41 项
│   ├── compare_vienna.py    验收：与 ViennaRNA 逐位比对
│   ├── compare_varna.py     参考：与 VARNA 的差异报告
│   ├── diagnose_varna.py    分析：仿射拟合诊断
│   ├── vienna_ref/*.txt     ViennaRNA 参照坐标
│   └── varna_ref/*.svg      VARNA 参照图
└── examples/              示例 SVG、预览 PNG、界面截图

naview-exe/                 打包好的免安装版（见第四节）
├── NAView.exe
└── 使用说明.txt
```

程序化调用：

```python
import sys
sys.path.insert(0, r'E:\AIspace\naview')

from naview import parse_dot_bracket, naview_layout
from render_svg import render_svg, build_primitives

structure = parse_dot_bracket('((((....))))')
layout = naview_layout(structure)

layout.xs, layout.ys          # 每个碱基的坐标（NAView 单位）
layout.loops                  # 环树，可查 radius / connections
layout.warnings               # 算法告警

# 导出 SVG，自定义配色 / 尺寸 / 线宽 / 方向
svg = render_svg(
    layout, 'GCGCAAAAGCGC',
    pair_style='single',
    font_size=7.5,            # 碱基字母字号（图形像素）
    ring_radius=5.0,          # 圆环半径（图形像素）
    backbone_width=1.0,       # 骨架线宽
    pair_width=1.0,           # 配对线宽
    ring_width=1.0,           # 圆环描边宽
    flip_y=True,              # True: 5′ 端在下方（同 VARNA）；False: 在上方
    ring_colors={'A': '#d8f0d8', 'C': '#d8e6fa'},
    letter_colors={'A': '#1f9e3a'},
    ring_stroke='#595959',
    backbone_color='#595959',
    pair_color='#0000ff',
)

# 只要图元（比如想在别的绘图库/网页里画）
prims, width, height = build_primitives(layout, 'GCGCAAAAGCGC')
```

---

## 八、与工作区其它工具的关系

| 工具 | 定位 |
|---|---|
| **本目录 `naview/`** | 绘图专用：GUI + 命令行，零依赖，Windows 原生可跑 |
| `E:\AIspace\启动NUPACK网页版.cmd` | 网页版，功能全（含 NUPACK 计算、VARNA 出图、项目管理） |
| `E:\AIspace\NUPACK\` / `NUPACK-portable\` | 命令行版 NUPACK（预测、试管分析、序列设计、另外三种布局） |

三套互不冲突。典型用法：用 NUPACK 网页版/命令行**算出结构**，
再把结构串粘贴到本 GUI 里**调色出图**。

---

## 九、已知限制

- **不支持假结**。NAView 要求结构是一棵树；输入 `([)]` 这类交叉配对会直接报错并说明原因。
- **几何与 VARNA 的 naview 有出入**（原因见第五节），不是像素级一致。
- 只实现 NAView 一种布局。工作区另有圆环 / 梯子 / 分区三种布局（见
  `E:\AIspace\NUPACK\CONTEXT.md`）。
- 界面只负责**画图**，不做折叠预测。结构请用 NUPACK 网页版或命令行版算好再粘进来。
- 导出只有 SVG；要 PNG 可以再拿 SVG 转（浏览器打开截图、或 `cairosvg`）。

---

## 十、出处与许可

算法出自 R.E. Bruccoleri & G. Heinrich, *Computer Applications in the Biosciences*
**4**(1):167–173, 1988。

`naview.py` 是依据该算法与 ViennaRNA 所收录的参考 C 实现（`naview.c`，
Copyright © 1988 Robert E. Bruccoleri，允许非商业用途的复制）**独立编写的 Python 实现**，
不是对任何 GPL 源码的逐行翻译。VARNA 本身是 GPLv3，本项目不包含它的代码。

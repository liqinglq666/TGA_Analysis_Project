# 🧪 TGA-CH-Analyzer (Thesis Savior Edition)

![Python](https://img.shields.io/badge/Python-3.8%2B-007EC6)
![Civil Engineering](https://img.shields.io/badge/Domain-Civil_Engineering-orange)
![Methodology](https://img.shields.io/badge/Method-Dynamic_Thermodynamic_Decoupling-green)
![Status](https://img.shields.io/badge/Build-Stable-blue)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

## 👋 起因 (Why I made this)

各位同门的师兄师姐、还有正在坑底挣扎的师弟师妹们，hello！👋

搞水泥基材料（ECC, UHPC 等）的应该都懂，处理 TGA 数据是真的折磨。
以前我都是在 Excel 里手动拉切线、算面积、扣背景，眼都快瞎了不说，要是只有几个样还好，几十个样真的会谢。

最惨的是，辛苦算出来的数据，还要被审稿人怼：

> **Reviewer #2**: *"Ref.1 claim that the weight loss at 400-500°C includes the dehydration of C-S-H gel. Your calculation of CH content is obviously overestimated."*
>
> **(翻译一下)**：*"你那个区间里不仅有 CH，还有 C-S-H 的失重，你没扣除背景，数据偏大，回去重算。"* 🌚

为了不掉头发，也不想再重复造轮子，我趁着摸鱼的时间搓了这个 **自动化 TGA 分析工具**。
**初衷很简单：能自动绝不动手，生成的图能直接用就不去 Origin 再画一遍。**

---

### 🧬 核心原理 (Theoretical Framework)

*(注：这部分写得比较学术，方便大家写大论文或者 Method 部分时候直接参考/改写)*

本软件没有采用那种“凭感觉拉切线”的主观做法，而是基于一套**自适应热力学解耦算法 (Adaptive Thermodynamic Decoupling Algorithm)**。

针对胶凝体系中多相产物（C-S-H 凝胶与 CH 晶体）热分解信号重叠的问题，逻辑如下：

#### 1. 拓扑特征锁定 (Topological Feature Locking)
程序内置了一个拓扑扫描逻辑，不是简单地卡一个固定温度，而是在特征温区内自动寻找极值响应点。这样可以规避仪器升温速率不同带来的热滞后（Thermal Lag）问题，自动构建对称的积分敏感区。

#### 2. 多相背景解耦 (Multi-Phase Background Decoupling)
这是解决审稿人质疑的关键。
我们将 C-S-H 的宽弥散失重视为一种准线性的**背景热漂移 (Quasi-linear Thermodynamic Drift)**。程序会自动构建局部漂移速率模型，把这种“热力学噪声”从尖锐的 CH 分解信号里剥离出去，实现信号的**纯化**。

#### 3. 高保真定量重构 (High-Fidelity Quantification)
**“先解耦、后定量”**。
实测下来，用这套逻辑算出的 CH 含量，跟 **XRD (Rietveld 全谱精修)** 的结果吻合度非常高（Pearson 相关系数极佳）。用来回怼审稿人非常稳。

---

## 🚀 几个比较实用的点 (Features)

### 1. 📊 拒绝黑盒，所见即所得
我不喜欢那种点一下出结果但不知道过程的软件。
* **Dashboard 面板**：右边会实时显示 **Onset (起)**、**Peak (峰)**、**Endset (止)** 的具体坐标。算法到底抓没抓对，一眼就能看出来。
* **手动挡模式**：参数微调后支持手动触发重算，给强迫症足够的掌控感。

### 2. 🎨 “Origin 杀手”级绘图
还在用 Origin 调格式？
* **全要素定制**：线条颜色、基线样式、填充透明度都能在界面上直接调。
* **高清导出**：支持直接存成 **300 DPI 的 PNG**，或者 **PDF/SVG 矢量图**。往 Word 或者 LaTeX 里一拖，排版非常舒服。

### 3. ⚡ 真正的批处理
* **效率**：把一堆 Excel 丢进文件夹，点一下加载，喝口水的功夫几十个样的数据和图就全出来了。
* **智能读取**：内置了解析引擎，不用担心样品名写在表头的哪里，程序自己会去找。

---

## 📸 界面长这样 (Screenshots)

*(V5.1 新版界面：左边调参，右边实时看图和数据，不用来回切窗口)*
<img width="100%" alt="Software UI" src="https://github.com/user-attachments/assets/0b487359-4492-4430-aed5-61d74069c631" />

---

## 💾 怎么下载 (Download)

考虑到咱们土木人的电脑环境千奇百怪，我打包了个 **免安装的 .exe 版本**。
不用配 Python 环境，也不用装库，**下载 -> 解压 -> 双击** 就能跑。

* **下载地址**：看页面右边的 👉 **[Releases]** (发行版)。
* **系统支持**：Win 10 / Win 11 都能用。

---

## 📂 喂饭级数据格式说明 (Data Protocol)

**⚠️ 高能预警：程序虽然智能，但它读不懂你独创的 Excel 艺术！**
为了防止点“开始”后程序直接报错闪退，请务必花 1 分钟把你的 Excel 整理成下面这个样子。

### 1. 文件结构 (The Structure)
一个 Excel 文件 (`.xlsx`) 必须包含 **两个 Sheet**，顺序绝对不能反：
* **第 1 个 Sheet** (左边那个)：放 **TG 原始数据** (单位通常是 Weight %，即 100 降到 0)。
* **第 2 个 Sheet** (右边那个)：放 **DTG 微分数据** (单位通常是 %/min 或 %/°C)。
    *(哪怕你把 Sheet 重命名叫 "张三" 和 "李四" 也没事，程序只认位置，不认名字)*

### 2. 内容排布 (The Layout)
**核心逻辑：每两个列为一组（温度列 + 数据列），代表一个样品。**

假设你有 2 个样品（Sample A 和 Sample B），你的 Excel 长这样：

|   | A 列 | B 列 | C 列 | D 列 | ... |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Row 1** | *无所谓* | *无所谓* | *无所谓* | *无所谓* | ... |
| **Row 2** | *Temp* | *TG (%)* | *Temp* | *TG (%)* | ... |
| **Row 3** | **Sample_A** 👈 | *(空着)* | **Sample_B** 👈 | *(空着)* | ... |
| **Row 4** | 30.0 | 100.0 | 30.0 | 100.0 | ... |
| **Row 5** | 30.1 | 99.99 | 30.1 | 99.98 | ... |
| **...** | ... | ... | ... | ... | ... |

### 3. 这里的规矩 (Rules)

* **第 1-2 行 (Header)**：程序会直接跳过。你可以写单位、写日期、写心情，反正程序不看。
* **第 3 行 (Sample Name - 重点!)**：
    * **这是程序的“眼睛”！** 程序会读取 **奇数列** (A, C, E...) 的第 3 行作为**样品名称**。
    * **千万别空着！** 如果 A3 是空的，程序会以为这个样品叫 `NaN`，出图会很丑。
    * **建议格式**：`ECC_7d`, `M5_28d` (尽量用英文和下划线，别整太复杂的特殊符号)。
* **第 4 行及以后 (Data)**：
    * 全是纯数字。
    * **A列**是样品1的温度，**B列**是样品1的数据。
    * **C列**是样品2的温度，**D列**是样品2的数据。
    * 以此类推... (想跑几个样就往后排几组)。

### 4. 🚫 防炸群指南 (Don'ts)

为了你和他人的身心健康，请**绝对避免**以下操作：
1.  **❌ 禁止合并单元格**：这是数据处理的一生之敌。如果你在表头合并了单元格，Pandas 读取时会产生错位，程序必挂。
2.  **❌ 禁止中间有空行/空列**：数据要连续，别在两个样品中间隔一个空列，程序会懵逼。
3.  **❌ 检查数据长度**：虽然程序能处理不同长度的数据，但最好确认你的 TGA 和 DTG 温度范围是一致的（比如都是 30-1000度）。

> **💡 懒人秘籍**：如果你实在看不懂，就把你仪器导出的原始 Excel 打开，把**数据部分 (数字)** 复制粘贴到我给的这个格式里，第3行填上名，齐活！

---
## 🛠️ 极客/魔改通道 (For the "CS-Curious" Civil Engineers)

如果你也是个**“不务正业”**、不想打灰只想敲代码的土木人；
或者你觉得我的 UI 配色像“工地蓝”，想自己动手整得花哨点；
欢迎 Clone 代码回去魔改！

但在此之前，请签署这份**《不吐槽代码烂协议》**：
*(本人乃土木出身，代码架构全凭直觉，变量命名全靠翻译软件。如果你看到了像 `shit_mountain_v2` 这样的函数名，请假装没看见。)*

**准备好进入“混凝土与 Python 齐飞”的世界了吗？**

```bash
# 1. 把这一坨代码搬回你的“赛博工地”
git clone [https://github.com/liqinglq666/TGA_Analysis_Project.git](https://github.com/liqinglq666/TGA_Analysis_Project.git)

# 2. 进场，安装各种“预制构件” (依赖库)
cd TGA_Analysis_Project
pip install -r requirements.txt

# 3. 点火，起飞！(假装自己是全栈工程师)
python gui_main.py

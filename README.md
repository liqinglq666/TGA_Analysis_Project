# 🧪 TGA-CH-Analyzer (Thesis Savior Edition)

![Python](https://img.shields.io/badge/Python-3.8%2B-007EC6)
![Civil Engineering](https://img.shields.io/badge/Domain-Civil_Engineering-orange)
![Methodology](https://img.shields.io/badge/Method-Dynamic_Baseline_Subtraction-green)
![Status](https://img.shields.io/badge/Mood-Save_My_Hairline-red)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

## 👋 这是一个什么神仙工具？ (Introduction)

各位同门的师兄师姐师弟师妹，你们好！👋

如果你也在折腾水泥基材料（ECC, UHPC 等），那你一定经历过这种**“科研至暗时刻”**：
面对几十个 TGA 数据文件，在 Excel 里手动拉切线、算面积、扣背景，眼花缭乱搞了一整天，结果——

> **Reviewer #2 (审稿人)**：*"Ref.1 claim that the weight loss at 400-500°C includes the dehydration of C-S-H gel. Your calculation of CH content is obviously overestimated."*
>
> **(翻译)**：*"你把 C-S-H 的失重也算进去了，数据偏大，重算。"* 🌚

为了解决这个让无数土木研究生**头秃**的问题，拒绝重复造轮子，我开发了这个 **自动化 TGA 分析神器**。

---

## 🧠 核心原理：它是怎么说服审稿人的？ (Methodology)

我们不能简单粗暴地用“质量差”来算 CH，那样太 Low 了。
本工具内置了一套 **动态基线扣除算法 (Dynamic Baseline Subtraction, DBS)**，逻辑非常性感：

1.  **自动寻峰 (Auto-Peak)**：利用二阶导数特征，自动锁定 DTG 曲线上的 CH 分解温区 ($T_{start}$ & $T_{end}$)，告别肉眼估算。
2.  **基线重构 (Baseline Modeling)**：取峰位两侧的 DTG 速率，构建一条“虚拟基线”，模拟并**扣除 C-S-H 凝胶的背景失重**。
3.  **净值计算 (Net Calculation)**：
    $$CH_{\text{content}} = (\Delta m_{\text{total}} - \Delta m_{\text{background}}) \times \frac{M_{Ca(OH)_2}}{M_{H_2O}}$$

> **✨ 实测战绩**：该算法计算出的 CH 含量与 **XRD (Rietveld 全谱精修)** 定量结果吻合度极高！(用来回复审稿人意见非常好用，亲测有效)

---

## 🚀 功能亮点 (Features)

* **⚡ 拒绝手动，批量处理**：丢进去一个文件夹的 Excel，点击“开始”，喝口水的功夫，几十个样品的 CH 含量全算好了。
* **🧹 专治手抖，智能平滑**：实验仪器老化？数据有噪点？内置 `Savitzky-Golay` 滤波器，自动把曲线熨平，顺滑得像德芙。
* **📊 出版级绘图**：生成的图表自带基线、填充区和标注，**长得跟 Origin 画出来的一样**，直接粘进论文/PPT 毫无违和感。
* **🧠 智能读取**：不管你把样品名写在 Excel 表头的左边还是右边，它都能顺藤摸瓜找出来。

---

## 📸 效果展示 (Screenshots)

*(这里是软件运行的买家秀，展示一下咱们专业的 GUI)*
<img width="1924" height="1322" alt="image" src="https://github.com/user-attachments/assets/79df317b-0f5c-448c-b145-4a58114f6c0a" />

---

## 💾 懒人下载区 (Download)

我不指望大家都会配 Python 环境（毕竟咱们是搞土木的，不是搞 CS 的）。
所以我打包好了 **.exe 文件**，**无需安装 Python**，下载下来双击就能跑。

* **Windows 绿色版**：`TGA_CH_Analyzer.exe`
* **百度网盘下载**：[点这里偷懒](https://pan.baidu.com/s/1Dj-8nSoKqELOmWSbOysHmg)
* **提取码**：`1234`

---

## 📂 数据格式预警 (Data Format)

**⚠️ 高能预警：为了不报错，请务必把你的 Excel 整理成这样！**

Excel 需要包含两个 Sheet（顺序不能反）：
1.  **Sheet1**: 放 TG 数据 (%)
2.  **Sheet2**: 放 DTG 数据 (%/min)

**列排布格式（紧凑型）：**

| Excel 行号 | 说明 | 示例 (Sample A) | 示例 (Sample B) |
| :--- | :--- | :--- | :--- |
| **Row 1** | 表头 (给人看的) | Temp / TG | Temp / TG |
| **Row 2** | 单位 | °C / % | °C / % |
| **Row 3** | **样品名 (给程序看的)** | **ECC-7d** 👈 | **ECC-28d** 👈 |
| **Row 4+** | **纯数据区域** | 30.0 / 100.0 | 30.0 / 100.0 |

> **碎碎念**：
> * **Row 3** 是抓取样品名的关键！别空着！
> * 数据区域（Row 4 以后）**千万别合并单元格**，那是 Excel 的禁术，程序会炸的。💥

---

## 🛠️ 大佬专用 (For Developers)

如果你嫌我的界面丑，或者想自己魔改算法，欢迎 Clone 代码回去自己玩：

```bash
# 1. 把代码搬回家
git clone [https://github.com/liqinglq666/TGA_Analysis_Project.git](https://github.com/liqinglq666/TGA_Analysis_Project.git)

# 2. 装一下库 (建议 Python 3.8+)
pip install -r requirements.txt

# 3. 启动引擎
python gui_main.py

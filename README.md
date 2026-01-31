# TGA-CH-Analyzer: Automated Quantification Framework for Cementitious Materials

![Python](https://img.shields.io/badge/Python-3.8%2B-007EC6)
![Domain](https://img.shields.io/badge/Domain-Civil_Engineering-orange)
![Methodology](https://img.shields.io/badge/Method-Dynamic_Baseline_Subtraction-green)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

## 📝 项目摘要 (Abstract)

**TGA-CH-Analyzer** 是一款专为水泥基复合材料（如 ECC、UHPC）研发的**热重分析 (TGA) 数据自动化处理工具**。

针对传统切线法（Tangential Method）在 400–500 °C 温区无法剥离 C-S-H 凝胶脱水干扰、导致氢氧化钙 (CH) 含量高估的系统性误差，本项目提出并实现了一种基于 **DTG 动态基线扣除 (Dynamic Baseline Subtraction, DBS)** 的量化算法。该工具集成了数据清洗、峰位自动识别、背景校正及批量批处理功能，旨在显著提升土木工程材料研究中数据分析的精度与效率。

---

## 🔬 方法论与算法原理 (Methodology)

### 1. 现有方法的局限性 (Limitations of Conventional Methods)
在水泥水化产物的热重分析中，氢氧化钙 (CH) 的分解温区 (400–500 °C) 往往与 C-S-H 凝胶的层间水脱水区间发生重叠。
* **传统方法缺陷**：直接计算质量损失 ($\Delta m$) 会将 C-S-H 的持续失重错误归算为 CH，导致实验结果被人为高估。
* **审稿人关注点**：顶级期刊（如 *Cement and Concrete Research*）审稿人常要求对这一背景误差进行修正。

### 2. 动态基线扣除算法 (The DBS Algorithm)
本工具采用以下逻辑进行修正计算：
1.  **特征峰定位 (Peak Identification)**：利用微分热重曲线 (DTG) 的二阶导数特征，精准定位 CH 的起始与终止分解温度 ($T_{start}, T_{end}$)。
2.  **背景漂移拟合 (Background Drift Modeling)**：基于区间两侧的 DTG 速率构建线性或非线性基线，模拟 C-S-H 的背景失重行为。
3.  **净含量计算 (Net Content Quantification)**：
    从总质量损失中剥离背景值，公式如下：
    $$CH_{content} = ( \Delta m_{total} - \Delta m_{background} ) \times \frac{M_{Ca(OH)_2}}{M_{H_2O}}$$

> **验证 (Validation)**：经对比测试，本算法计算结果与 XRD Rietveld 全谱拟合定量结果具有高度一致性。

---

## 🚀 主要特性 (Key Features)

* **高精度背景校正**：自动识别并扣除 C-S-H 脱水背景，输出修正后的 CH 净含量。
* **智能批处理流程**：支持读取文件夹内多组实验数据，自动匹配 TG/DTG 曲线，秒级完成数十个样品的分析。
* **自适应信号平滑**：内置 Savitzky-Golay 滤波器，有效去除实验设备产生的随机噪点，优化寻峰准确度。
* **出版级图表输出**：生成的分析图表包含基线示意与积分区域，可直接用于学术论文插图。

---

## 💾 快速部署 (Deployment)

为方便非编程背景的研究人员使用，本项目提供编译好的可执行文件。

* **Windows 可执行文件**：`TGA_CH_Analyzer.exe`
* **下载地址**：[百度网盘链接](https://pan.baidu.com/s/1Dj-8nSoKqELOmWSbOysHmg) (提取码: `1234`)

---

## 📂 数据规范 (Input Specifications)

为确保算法收敛，输入数据需遵循以下 **Excel (.xlsx)** 结构规范：

### 1. 文件结构 (Structure)
* **Sheet 1**: 存储 TG 数据 (Mass Loss, %)。
* **Sheet 2**: 存储 DTG 数据 (Derivative Mass Loss, %/min)。
    *(注：程序依据索引读取，Sheet 命名不影响运行)*

### 2. 数据排布 (Layout)
数据需按 **[温度, 数值]** 双列格式成对排列。
* **Row 7**: 样品标识符 (Sample ID)。
* **Row 8+**: 数值矩阵 (Numeric Data)。

| Column Index | A | B | C | D |
| :--- | :---: | :---: | :---: | :---: |
| **Attribute** | **Temp ($T_1$)** | **Value ($V_1$)** | **Temp ($T_2$)** | **Value ($V_2$)** |
| **Row 7 (ID)** | - | **Sample_A** | - | **Sample_B** |
| **Row 8 (Data)** | 30.0 | 100.0 | 30.0 | 100.0 |

---

## 🛠️ 开发环境配置 (Development Setup)

若需对源码进行二次开发，请按以下步骤配置环境：

1.  **克隆仓库**
    ```bash
    git clone [https://github.com/liqinglq666/TGA_Analysis_Project.git](https://github.com/liqinglq666/TGA_Analysis_Project.git)
    ```

2.  **安装依赖库**
    建议使用 Python 3.8+ 环境：
    ```bash
    pip install -r requirements.txt
    ```

3.  **启动主程序**
    ```bash
    python gui_main.py
    ```

---

## 🤝 贡献与引用 (Contribution & Citation)

本项目致力于为土木工程材料领域提供开源、透明的数据分析解决方案。
* **Bug 反馈**：请通过 Issue 提交详细描述。
* **代码贡献**：欢迎 Pull Request 优化算法逻辑。

## 📄 许可证 (License)
本项目基于 [MIT License](LICENSE) 开源发布。

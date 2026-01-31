# 🧪 TGA Analysis Project (热重分析助手)

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Status](https://img.shields.io/badge/Status-Developing-green)

## 📖 项目简介
这是我为土木工程科研开发的一款 **Python 自动化工具**。
它可以帮大家从繁杂的 TGA（热重分析）实验数据中解放出来，自动清洗数据、计算 CH 含量，并生成可以直接用的分析报表。

## ✨ 核心功能
* **📊 自动绘图**：一键生成 DTG 曲线，无需在 Excel 里反复调整。
* **🧹 数据清洗**：自动识别并剔除实验中的异常噪点。
* **⚡ 批量处理**：支持一次性导入 10+ 个 Excel 文件，效率提升 90%。
* **📑 报表导出**：分析结果直接存为格式整齐的 Excel，方便写论文使用。

## 🛠️ 如何安装
如果你想在本地运行这个工具：

1. 克隆项目：
   ```bash
   git clone [https://github.com/liqinglq666/TGA_Analysis_Project.git](https://github.com/liqinglq666/TGA_Analysis_Project.git)
2. 安装依赖 
  建议使用Python3.8或以上版本
    ```bash
    pip install -r requirements.txt
    ```
    
 ## 🚀 使用方法   
   1. 启动程序： 在终端中运行以下命令启动图形界面：
     ```bash
     python gui_main.py
     ```
   2. 导入数据：点击界面左上角的“导入数据”按钮，选择你的 TGA 原始数据文件。
   3. 开始分析： 点击 “开始计算” 按钮，程序将自动清洗数据、识别峰值并显示 DTG 曲线。
   4. 导出结果： 点击 “导出报表”，分析结果将自动汇总并保存为格式整齐的 Excel 文件。
   
## 🤝 贡献与反馈
如果你也是土木科研人员，或者在使用过程中遇到问题，欢迎：

 - 🐛 提交 Issue：反馈 Bug 或提出新功能建议。
 - 💡 提交 Pull Request：直接贡献代码改进项目。

## 📄 许可证 (License)
本项目采用 MIT License 开源许可证。

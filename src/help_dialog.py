# src/help_dialog.py

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTabWidget, QTextBrowser, QPushButton


class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("TGA-CH Analyzer - 用户指南与计算原理")
        self.resize(860, 720)

        layout = QVBoxLayout(self)
        tabs = QTabWidget()

        self.tab_guide = QTextBrowser()
        self.tab_guide.setOpenExternalLinks(True)
        self._setup_guide_content()
        tabs.addTab(self.tab_guide, "操作指南 (User Guide)")

        self.tab_formulas = QTextBrowser()
        self._setup_formulas_content()
        tabs.addTab(self.tab_formulas, "计算原理 (Formulas)")

        layout.addWidget(tabs)

        btn_close = QPushButton("关闭 (Close)")
        btn_close.clicked.connect(self.accept)
        btn_close.setStyleSheet("padding: 8px; font-weight: bold; background-color: #f4f6f9;")
        layout.addWidget(btn_close)

    def _setup_guide_content(self):
        html = """
        <h2 style='color: #0969da;'>快速上手指南</h2>

        <h3>1. 数据准备 (Data Format)</h3>
        <ul>
            <li>文件必须是 <b>.xlsx</b> 格式。</li>
            <li>包含两个 Sheet：Sheet 1 为 <b>TG 数据</b>，Sheet 2 为 <b>DTG 数据</b>。</li>
            <li>数据排布：每两个列为一组：<b>Temp, TG</b> 或 <b>Temp, DTG</b>。</li>
            <li>第 3 行，即 pandas index 2，建议填写<b>样品名称</b>；第 4 行起为数值数据。</li>
            <li>若样品名重复，程序会自动追加后缀，例如 Sample、Sample_2、Sample_3，避免数据被覆盖。</li>
            <li><span style='color: red;'>禁止使用合并单元格，禁止样本组之间留空列。</span></li>
        </ul>

        <h3>2. 核心分析参数 (Analysis Parameters)</h3>
        <ul>
            <li><b>Target Phase</b>：选择 CH、CaCO3、Friedel's Salt、Bound Water 或 Hydrate Index。</li>
            <li><b>Mass Basis</b>：选择质量基准。<b>as_input</b> 适用于 TG 已经由仪器导出为百分质量；<b>normalize_105</b> 以 105 °C 质量归一；<b>normalize_600</b> 以 600 °C 质量归一。</li>
            <li><b>Bound Water Mode</b>：<b>exclude_co2</b> 为 GUI 默认口径；<b>bhatty</b> 只建议在 CO2 信号主要来自 CH 碳化相关损失时使用。</li>
            <li><b>Heating Rate</b>：CH 背景扣除使用的升温速率，常见为 10 °C/min。</li>
            <li><b>Integration Width</b>：CH 峰两侧端点基线的积分半宽，默认 ±40 °C。</li>
            <li><b>Start / End Temp</b>：非 CH 相的温区端点，可根据 DTG 曲线手动调整。</li>
        </ul>

        <h3>3. DTG 单位提醒</h3>
        <p>
            当前 GUI 的 CH 背景扣除默认假设 DTG 是基于时间的质量损失速率，例如 <b>%/min</b> 或 <b>mg/min</b>。
            如果仪器导出的 DTG 是 <b>%/°C</b> 或 <b>mg/°C</b>，则背景项不应再除以 heating rate。
            使用前请先确认仪器导出的 DTG 单位。
        </p>

        <h3>4. 图形解释 (Plot Interpretation)</h3>
        <ul>
            <li><b>CH</b>：图中 endpoint baseline 与 corrected CH region 用于解释端点背景扣除后的 CH 净失水。</li>
            <li><b>CaCO3 / Friedel's Salt / Wn / Hydrate Index</b>：图中 Window guide 与 Selected window 只是 DTG 可视化辅助。数值来自 TG 温区质量差，不是 DTG 面积积分。</li>
            <li>图例和结果标注支持鼠标拖拽移动，方便截图和论文绘图整理。</li>
        </ul>

        <h3>5. 交互与导出</h3>
        <ul>
            <li>点击 <b>Update</b> 可根据当前参数重新计算。</li>
            <li>点击 <b>Copy</b> 可将当前样品结果复制到剪贴板，直接粘贴至 Excel。</li>
            <li>点击 <b>Export</b> 可批量导出所有样品的 CH、Wn、CaCO3、Fs、Hydrate Index、Mass Basis 与 Bound Water Mode。</li>
            <li>点击 <b>Save Image</b> 可导出当前图像，适合报告或论文初步作图。</li>
        </ul>
        """
        self.tab_guide.setHtml(html)

    def _setup_formulas_content(self):
        html = """
        <h2 style='color: #2da44e;'>核心计算原理</h2>
        <p>
            本软件采用 <b>TG mass loss interpolation</b>、<b>DTG-guided endpoint baseline correction</b>
            与 <b>stoichiometric conversion</b> 进行半定量分析。复杂重叠峰仍建议结合 XRD、FTIR、TG-MS、NMR 或热力学模拟交叉验证。
        </p>

        <hr>
        <h3 style='color: #2c3e50;'>1. 质量基准 (Mass Basis)</h3>
        <p>核心计算层支持三种质量基准：</p>
        <ul>
            <li><b>as_input</b>：TG 已经是百分质量时，直接使用 m(T1) - m(T2)。</li>
            <li><b>normalize_105</b>：以 105 °C 质量作为参考质量。</li>
            <li><b>normalize_600</b>：以 600 °C 质量作为参考质量，需结合实验目的谨慎使用。</li>
        </ul>
        <p><b>通用公式：</b></p>
        <p style='font-family: monospace;'>ΔW = [m(T1) - m(T2)] / m_ref × 100</p>

        <hr>
        <h3 style='color: #2c3e50;'>2. 氢氧化钙 / Portlandite (CH)</h3>
        <p><b>默认寻峰区间：</b> 400-520 °C。软件先在该区间寻找 DTG 最小值作为 CH 峰位，再按积分半宽确定起止点。</p>
        <p><b>反应：</b> Ca(OH)<sub>2</sub> → CaO + H<sub>2</sub>O↑</p>
        <p><b>端点区间：</b> T<sub>start</sub> = T<sub>peak</sub> - w；T<sub>end</sub> = T<sub>peak</sub> + w。</p>
        <p><b>总失重：</b> ΔW<sub>total</sub> = m(T<sub>start</sub>) - m(T<sub>end</sub>)</p>
        <p><b>背景损失：</b> ΔW<sub>bg</sub> = [(|DTG<sub>start</sub>| + |DTG<sub>end</sub>|) / (2β)] × (T<sub>end</sub> - T<sub>start</sub>)</p>
        <p><b>净失水：</b> ΔW<sub>net</sub> = max(0, ΔW<sub>total</sub> - ΔW<sub>bg</sub>)</p>
        <p><b>CH 换算：</b> CH<sub>net</sub>(%) = ΔW<sub>net</sub> × (74.09 / 18.02)</p>
        <p><span style='color:#b42318;'><b>注意：</b> 上述背景公式默认 DTG 单位是 %/min 或 mg/min。如果 DTG 已是 %/°C 或 mg/°C，需要谨慎处理 heating rate。</span></p>

        <hr>
        <h3 style='color: #2c3e50;'>3. 碳酸钙当量 (CaCO<sub>3</sub>)</h3>
        <p><b>默认温区：</b> 600-800 °C，可根据样品、气氛、升温速率和碳酸盐晶型调整。</p>
        <p><b>反应：</b> CaCO<sub>3</sub> → CaO + CO<sub>2</sub>↑</p>
        <p><b>公式：</b> CaCO<sub>3</sub>(%) = ΔW<sub>CO2</sub> × (100.09 / 44.01)</p>
        <p>如果样品含石灰石粉或外源碳酸盐，建议写作 <b>CaCO3 equivalent content</b>，不要直接等同于碳化生成量。</p>

        <hr>
        <h3 style='color: #2c3e50;'>4. 化学结合水 / 非蒸发水 (W<sub>n</sub>)</h3>
        <p><b>GUI 默认口径：</b> exclude_co2。</p>
        <p><b>exclude_co2：</b> W<sub>n</sub> = ΔW<sub>105-1000</sub> - ΔW<sub>CO2</sub></p>
        <p><b>Bhatty-style correction：</b> W<sub>n</sub> = ΔW<sub>105-1000</sub> - ΔW<sub>CO2</sub> + 0.41ΔW<sub>CO2</sub>，其中 0.41 = 18.02 / 44.01。</p>
        <p>Bhatty-style correction 主要适用于 CO2 信号被解释为 carbonation-related CO2 loss 的场景。如果体系含石灰石粉或外源碳酸盐，应谨慎解释。</p>

        <hr>
        <h3 style='color: #2c3e50;'>5. Friedel's Salt 当量</h3>
        <p><b>默认温区：</b> 300-380 °C。该区间可能与 AFm、C-A-S-H 或其他含铝水化相重叠。</p>
        <p><b>公式：</b> Fs(%) = ΔW<sub>300-380</sub> × [561.3 / (6 × 18.02)]</p>
        <p>建议写作 <b>Friedel's salt equivalent content</b>，不要表述为绝对纯相含量。</p>

        <hr>
        <h3 style='color: #2c3e50;'>6. Hydrate Index / 低温水化产物失重指数</h3>
        <p><b>默认温区：</b> 50-200 °C。</p>
        <p>该区间包含 C-S-H、AFt、AFm、吸附水、部分物理结合水等重叠信号。因此本工具输出 <b>Hydrate Index</b>，用于同批次样品横向对比，不应写作绝对 C-S-H 含量。</p>
        """
        self.tab_formulas.setHtml(html)

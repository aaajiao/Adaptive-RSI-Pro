---
description: 更新项目文档 / Update Project README
---

# README 文档更新标准流程 / README Update Standard Workflow

## 前置准备 / Prerequisites

### 确定更新范围 / Define Scope
选择要更新的项目文档：
- `RSI+/README.md` - Adaptive RSI Pro 指标文档
- `VIX/README.md` - VIX Term Structure Pro 指标文档
- `adaptive_rsi/README.md` - 其他 RSI 相关项目
- 通用 Pine Script 项目文档

**重要原则 / Guiding Principles**:
- **Bilingual / 双语**: 所有内容必须包含中英文对照 (English & Chinese).
- **Manual Git / 手动Git**: 禁止自动提交，所有变更由用户审查后手动提交.
- **Accuracy / 准确性**: 文档内容必须严格对应代码实现.

---

## 阶段一：代码分析与信息收集 / Code Analysis

### 1.1 获取最新代码状态 / Check Status
```bash
git log -1 --stat
```

查看最近的代码变更：
- [ ] 识别修改的文件
- [ ] 记录修改日期和版本号
- [ ] 确认是否有 Breaking Changes

### 1.2 提取代码元信息 / Extract Metadata
打开对应的 `.pine` 文件，提取关键信息：

#### 版本信息
- [ ] Pine Script 版本：`//@version=6`
- [ ] 指标版本号：从 `indicator()` 函数中获取
- [ ] 最后更新日期

#### 核心功能清单
系统性扫描代码，列出所有主要功能：
- [ ] **信号类型**：买入、卖出、MTF、Extreme、Divergence 等
- [ ] **Dashboard 模式**：Compact、Full、Mobile、Hidden
- [ ] **Alert 系统**：Smart Alert (Unified)
- [ ] **自适应功能**：Auto Lookback、Adaptive Thresholds、Adaptive Divergence

#### 输入参数完整列表
- [ ] 所有 `input.*` 参数
- [ ] 记录每个参数的 Title (中英)、Default Value、Min/Max、Tooltip (中英)

### 1.3 功能差异对比 / Gap Analysis
将代码功能清单与现有 README 对比：
- [ ] **新增功能**：代码有但文档未提及
- [ ] **已删除功能**：文档提及但代码已移除
- [ ] **参数变化**：默认值、范围、名称的修改

---

## 阶段二：文档结构规范化 / Document Structure

### 2.1 标准章节结构 / Standard Sections
确保 README 包含以下章节（按顺序）：

```markdown
# [指标名称] / [Indicator Name]

## 📊 简介 / Introduction (Bilingual)
## ✨ 核心功能 / Core Features (Bilingual)
## 🎯 信号系统 / Signal System (Bilingual)
## 📈 Dashboard 仪表盘 / Dashboard (Bilingual)
## ⚙️ 配置参数 / Configuration (Bilingual Tables)
## 🔔 Alert 警报系统 / Alert System (Bilingual)
## 📖 使用指南 / Usage Guide (Bilingual)
## 📝 更新日志 / Changelog (Bilingual Headers)
```

---

## 阶段三：内容更新 / Content Update

**CRITICAL: All content MUST be bilingual (Chinese & English). / 关键：所有内容必须是双语的。**

### 3.1 【高优先级】版本与元信息
更新顶部基本信息：
- [ ] **版本号**：与代码 `indicator()` 中的版本一致
- [ ] **更新日期**：当前日期
- [ ] **简介描述**：中英文双语说明

### 3.2 【高优先级】核心功能列表
使用表格或列表清晰展示所有主要功能，必须双语：
- [ ] Feature Name (Eng/Chi)
- [ ] Description (Eng/Chi)

### 3.3 【高优先级】配置参数详解 / Configuration
创建完整的参数表格，确保 Columns 包含中英文说明：
- Parameter Name (Code)
- Default
- Range/Options
- Description (Bilingual)

### 3.4 【中优先级】信号与图片 / Signals & Images
- [ ] 更新信号触发条件的双语描述
- [ ] 检查所有图片链接是否有效
- [ ] 如有新模式（如 Mobile Dashboard），添加对应截图或 Emoji 示意

### 3.5 【中优先级】警报系统 / Alerts
- [ ] 说明 Smart Alert 的机制 (One alert for all signals)
- [ ] 提供设置步骤 (双语)

---

## 阶段四：格式规范化 / Formatting Standards

### 4.1 双语格式统一
确保段落格式易读，建议中文在前英文在后，或逐段对照。

✅ **正确示例**：
```markdown
## 🎯 信号系统 / Signal System
- **超买信号** / Overbought Signal
  当 RSI 突破动态阈值时触发。
  Triggered when RSI breaches dynamic thresholds.
```

### 4.2 Markdown 最佳实践
- [ ] 代码和参数用反引号：`rsi_length`
- [ ] 使用表格展示结构化数据
- [ ] <b>加粗</b> 关键信息

---

## 阶段五：更新日志维护 / Changelog Maintenance

### 5.1 更新日志位置 / Changelog Location
更新日志应放在 README 的末尾，作为独立章节：
- [ ] 章节标题：`## Changelog | 更新日志`
- [ ] 按版本号倒序排列（最新版本在最前）

### 5.2 版本格式规范 / Version Format
每个版本条目必须包含：
```markdown
### vX.X (YYYY-MM-DD)

**🔔 [功能类别] | [Category Name]**
- **Feature Name**: English description
  中文描述
```

#### 版本号规则 / Version Rules
- **Major (vX.0)**: 重大功能更新或 Breaking Changes
- **Minor (vX.Y)**: 新功能添加、功能增强
- **Patch (vX.Y.Z)**: Bug 修复、小调整（可选）

### 5.3 常用功能类别 Emoji / Category Emojis
| Emoji | 类别 Category | 使用场景 |
|:-----:|--------------|---------|
| 🚀 | Upgrade/升级 | 语言版本、框架升级 |
| ✨ | New Feature/新功能 | 全新功能模块 |
| 🔔 | Alert System/警报系统 | 警报相关更新 |
| 📊 | Adaptive/自适应 | 自适应算法更新 |
| 📱 | Mobile/移动端 | 移动端适配 |
| 🎯 | Signal/信号 | 信号系统更新 |
| 🐛 | Bug Fix/修复 | 问题修复 |
| ⚡ | Performance/性能 | 性能优化 |
| 📈 | Core/核心 | 核心功能 |

### 5.4 双语格式要求 / Bilingual Format
每条更新必须包含中英双语：
```markdown
- **English Feature Name**: English description of the change
  中文功能名称：中文描述
```

### 5.5 更新日志示例 / Example
```markdown
## Changelog | 更新日志

### v6.1 (2025-12-16)

**🔔 Smart Alert System | 智能警报系统**
- **Unified Smart Alert**: Replaced multiple `alertcondition` calls with a single unified alert system
  统一智能警报：用单一警报系统替代多个 alertcondition 调用
- **Rising Edge Detection**: Prevents duplicate notifications
  上升沿检测：防止重复通知
```

---

## 阶段六：审查与提交 / Review & Commit

### 6.1 最终审查 / Final Review
- [ ] <b>双语检查</b>：没有遗漏翻译的段落？
- [ ] <b>一致性检查</b>：README 参数与代码完全一致？
- [ ] <b>图片检查</b>：所有图片都能正常加载？
- [ ] <b>更新日志</b>：Changelog 已更新至最新版本？

### 6.2 手动提交 / Manual Commit
确认无误后，手动运行 git 命令（不自动执行）：

```bash
git add README.md
git diff --cached README.md
git commit -m "docs: update README to vX.X (bilingual)"
git push
```
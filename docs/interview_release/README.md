# ResearchOS Interview Release

本目录是 ResearchOS 的 FDE（解决方案工程师）面试展示材料，不包含新的业务代码、客户数据、论文全文或模型密钥。

建议阅读顺序：

1. [产品介绍](./01_Product_Overview.md)
2. [FDE 方案架构](./02_FDE_Solution_Architecture.md)
3. [技术架构](./03_Technical_Architecture.md)
4. [5 分钟演示脚本](./04_Demo_Script.md)
5. [面试问答](./05_Interview_QA.md)
6. [简历项目版本](./06_Resume_Project.md)

## 真实性边界

- ResearchOS 是 AI Agent 产品原型，不是已大规模商用的 SaaS 服务。
- 客户场景、Solution Blueprint 和 Delivery Report 均为明确标注的方案演示模板。
- 系统只应基于已授权并完成索引的资料生成 Evidence；资料不足时应提示补充资料，而不是生成科研结论。
- 本地验收时诊断接口返回 7 篇资料、180 个知识片段、180 个已保存向量片段；该数字仅说明当前本地实例状态，不代表客户规模、准确率、业务收益或科研成果。

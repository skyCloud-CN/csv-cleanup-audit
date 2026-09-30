# CSV Cleanup Audit / CSV 清理与变更记录

An original, offline CSV cleanup sample with explicit transformations and auditable results. Developed with AI assistance; processing uses deterministic Python code. All included data is synthetic. Test results are limited to the documented checks and do not guarantee suitability for every file.

这是一个原创、离线的 CSV 清理样例，处理规则明确，并保留可核对的变更记录。代码和文档由 AI 辅助完成，数据转换由确定性的 Python 代码执行。所有示例均为合成数据；已执行的测试不保证适合所有文件。

## Quick start / 快速开始

Requires Python 3.10 or newer. Standard library only; no installation, accounts, API keys, network requests or paid services. Commands are run from this folder. The output directory must not exist and its parent must already exist.

需要 Python 3.10 或更高版本。仅使用标准库，无需安装依赖、注册账号、API 密钥、联网或付费服务。在本目录运行命令。输出目录必须不存在，其父目录必须已存在。

```sh
python csv_cleaner.py demo/before.csv my-result --trim --deduplicate
python -m unittest discover -s tests -v
```

To inspect without changing cell values or removing records, omit both flags:

仅检查、不改变单元格值、不删除记录时，省略两个选项：

```sh
python csv_cleaner.py demo/before.csv inspect-result
```

The input is never written. An existing output path is always refused, including symbolic links. Use a fresh directory for every run. Exit code 0 means parsing/cleanup succeeded; 2 means rejected input, I/O failure or invalid usage. Warnings do not change the exit code.

程序不会写入输入文件。任何已存在的输出路径（包括符号链接）都会被拒绝。每次运行请使用新目录。退出码 0 表示成功，2 表示输入被拒绝、文件读写失败或参数错误。警告不改变退出码。

## Explicit transformations / 明确选择的处理

- Default: preserve every parsed string and every data record, in original order. IDs such as `000123`, Chinese, emoji, quoted commas, quoted newlines, empty cells and numeric-looking strings remain text
- `--trim`: strip leading/trailing Python Unicode whitespace from **data cells only**; headers remain untouched. This can remove meaningful spaces, tabs or edge newlines, so choose it deliberately
- `--deduplicate`: keep the first row for each exact tuple of cell strings. If `--trim` is also selected, deduplication happens **after trimming**, so rows differing only in edge whitespace may be removed. There is no fuzzy matching, case folding or entity merging
- Removed-row evidence always retains the original untrimmed strings. The audit maps kept and removed rows to source record numbers and records before/after values for changed kept cells

- 默认：按原顺序保留所有解析后的字符串和数据行；前导零、中文、表情、带引号的逗号及换行、空单元格、看起来像数字的文本均保留为文本
- `--trim`：仅去除**数据单元格**两端的 Python Unicode 空白字符，不修改表头。可能移除有意义的空格、制表符或边缘换行，须明确选择
- `--deduplicate`：对单元格字符串完全相同的行保留第一条。若同时选择 `--trim`，则**先去空白再去重**，仅两端空白不同的行也可能被删除。不做模糊匹配、大小写归并或实体合并
- 删除证据保留原始、未经去空白的字符串。审计记录保留行及删除行的源记录编号，以及保留行中发生变化的单元格前后值

## Delivered files / 交付文件

| File | Meaning / 含义 |
|---|---|
| `cleaned.csv` | Header + retained rows / 表头及保留行 |
| `removed_rows.csv` | Original header + original removed rows; header only if none / 原表头及删除行原值；无删除时仅表头 |
| `audit.json` | Machine-readable counts, hashes, changes, row mapping, warnings / 行数、哈希、变更、记录映射、警告 |
| `audit.html` | Escaped, offline-readable audit; no JavaScript, external assets or remote requests / 已转义的离线审计，无脚本、外部资源或网络请求 |

For structural/encoding rejection, only audit files are created, with no cleaned or removed CSV. Missing/unreadable files, oversized files, output-path conflicts and invalid arguments fail before creating reports. Disk errors may prevent reports and trigger best-effort cleanup of new output files; the source remains untouched.

结构或编码不合格时仅生成审计文件，不生成清理或删除记录 CSV。输入缺失、不可读、文件过大、输出路径冲突或参数错误会在生成报告前终止。磁盘故障可能导致无报告，程序会尽力清理本次输出；源文件不变。

Logical CSV record numbers start at 1 including the header, not physical text lines. Multiline quoted fields can span several physical lines. SHA-256 values verify exact file bytes; CSV output is **not byte-for-byte identical** to the input even in inspection mode.

记录编号从 1 开始，包含表头，不是物理行号；带引号的字段可跨多行。SHA-256 用于校验文件字节；即使仅检查模式，CSV 输出也**不保证与源文件字节一致**。

## Supported format and limits / 支持格式与限制

- UTF-8 only, optional UTF-8 BOM; comma delimiter; first record is header; standard double-quote escaping
- Output is UTF-8 without BOM, CRLF record separators and standard CSV quoting. Original quoting style/BOM/record separators may change. Embedded newlines remain unchanged unless trimmed at a cell edge
- Inconsistent row widths, blank physical records, invalid quoting, NUL characters, invalid UTF-8 and absent headers are rejected. No cells are truncated or shifted to repair a row
- Blank/duplicate header names are warned about but not renamed. No type/date conversion, translation, inferred values, business-rule validation, phone/email validation or spreadsheet formatting
- Runtime input limit: 10 MiB and 100,000 data records. Python's default CSV field limit also applies (typically 131,072 characters per field). The proposed service scope is narrower: 5,000 rows, 20 columns and 10 MB (10,000,000 bytes)
- The tool reads the file into memory. Test coverage is synthetic and does not prove compatibility with every CSV exporter, spreadsheet app, operating system or untrusted workload

- 仅支持 UTF-8（可含 BOM）、逗号分隔、第一条记录为表头、标准双引号转义
- 输出为无 BOM 的 UTF-8，记录分隔符为 CRLF，使用标准 CSV 引号。原始引号样式、BOM 和记录分隔符可能改变。字段内部换行保留，除非它位于被选择去空白的单元格边缘
- 拒绝宽度不一致、空白物理记录、非法引号、NUL、非法 UTF-8 或无表头。不会通过截断或移位“修复”单元格
- 空白或重名表头只警告、不改名。不做类型或日期转换、翻译、补全推断、业务规则验证、电话或邮箱验证、电子表格排版
- 程序上限为 10 MiB、100,000 条数据记录；同时受 Python CSV 默认单字段长度限制（通常为 131,072 字符）。拟议服务范围更小：5,000 行、20 列、10 MB（10,000,000 字节）
- 文件会读入内存。合成测试不能证明对所有导出器、电子表格软件、操作系统或恶意输入的兼容性

## Important safety and privacy notes / 安全及隐私

Formula detection is only a heuristic warning for leading `=`, `+`, `-`, `@` after whitespace and certain control prefixes. Negative numbers can be false positives. Unknown spreadsheet-specific execution triggers may be missed. **Nothing is formula-sanitized**: headers, cleaned CSV and removed-row CSV may still contain dangerous spreadsheet formulas. Inspect using a plain-text viewer; if using a spreadsheet, use its explicit import flow with all columns as text and do not enable external content. A warning is not a guarantee of safety.

公式检测仅是启发式警告，检查空白后以 `=`、`+`、`-`、`@` 开头的内容及部分控制字符前缀。负数可能误报，不同软件的特殊触发形式可能漏报。**不会自动清除公式风险**：表头、清理 CSV 和删除证据 CSV 都可能含危险公式。建议用纯文本查看器；如需电子表格，使用明确的导入流程，将所有列设为文本，并且不要启用外部内容。警告不代表安全保证。

Audit files include actual cell values and can expose the same private information as the input. Keep every output private. The proposed sample service excludes sensitive personal datasets. Nothing in this package uploads files or contacts third parties.

审计文件含真实单元格值，可能与源数据一样敏感；所有输出均应保密。拟议服务不处理敏感个人数据。本程序不会上传文件或联系第三方。

## Demo and verification / 样例及验证

`demo/before.csv` has six synthetic data rows, Chinese, leading-zero IDs, a quoted comma, a quoted multiline cell, an empty cell, one exact duplicate and one formula-like value. `demo/after/` shows the selected trim + deduplication result: five retained rows and one removed row. `demo/rejected/` illustrates width rejection. No customer data is included.

`demo/before.csv` 含六行合成数据，包括中文、前导零、带引号的逗号、多行单元格、空值、一个完全重复行和一个疑似公式值。`demo/after/` 展示去空白与去重后的结果：保留五行、删除一行。`demo/rejected/` 展示宽度不一致的拒绝报告。未使用客户数据。

Tests cover Unicode and cell preservation; leading zeros; quoted commas, quotes and newlines; reproducible randomized conservation and idempotence for all four option combinations; original-row reconstruction; header and formula warnings; HTML escaping; malformed CSV/encoding; output overwrite refusal; input byte preservation; CLI exit codes and input limits. See [testing notes](docs/TESTING.md) for the executed checks and reproduction commands.

测试覆盖 Unicode、单元格及前导零保留、逗号/引号/换行、四种选项组合下可复现随机数据的守恒与幂等性、原始记录重建、表头和公式警告、HTML 转义、畸形 CSV/编码、禁止覆盖、源字节保留、退出码和大小限制。实际执行范围和复现命令见[测试说明](docs/TESTING.md)。

## Creation notice / 创作说明

Created with AI-assisted design, implementation and documentation. Transformations are deterministic Python code, not model-generated cell edits. Tests passed only as recorded; independent review and a non-sensitive trial file are advisable before any commercial delivery. No professional certification, paid customer validation or revenue is claimed.

设计、代码及文档由 AI 辅助完成。转换由确定性的 Python 代码执行，不由模型生成单元格内容。测试通过范围以记录为准；商业交付前建议独立审查并先试用非敏感样例。不声称专业认证、付费客户验证或已产生收入。

## Optional consultation / 可选的 CSV 清理咨询

[简数工具箱 · 爱发电 / PlainData Tools on Afdian](https://afdian.com/a/plaindata-tools)

如果需要针对文件确认清理规则，可通过以上主页咨询。拟议范围为单个非敏感 UTF-8 CSV（可含 BOM）、逗号分隔、第一条记录为表头，不超过 5,000 条数据记录、20 列和 10 MB（10,000,000 字节）。可讨论去除两端空白与完全重复行去重，不提供模糊匹配、缺失值推断或业务规则验证。

请先说明列结构、行数和希望采用的规则，并使用少量合成或确认不含敏感信息的样例。不要发送密码或敏感个人数据。是否适合处理、报价及交付安排需另行确认；咨询入口不代表已接受订单，也不构成付款或交付承诺。

For optional CSV cleanup consultation or support, use the Afdian page above. Proposed scope: one non-sensitive UTF-8, comma-delimited CSV with a header, up to 5,000 data records, 20 columns and 10 MB (10,000,000 bytes). Describe the structure and intended rules first, using a small synthetic or verified non-sensitive sample. Never send passwords or sensitive personal data. Suitability, pricing and delivery must be agreed separately; this link does not accept an order or promise a result.

## License / 许可

This repository is publicly available to view and download. No additional open-source license is granted at this time; contact the author about other uses.

本仓库公开供查看和下载。目前未授予额外开源许可；其他用途请联系作者确认。

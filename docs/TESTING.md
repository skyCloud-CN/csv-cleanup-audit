# Testing / 测试说明

Run from the repository root with Python 3.10 or newer (standard library only):

```sh
python -m unittest discover -s tests -v
python -m py_compile csv_cleaner.py tests/test_cleaner.py
```

On 2026-09-30, the 11 unittest cases passed with Python 3.12.14 on Linux, and both Python files compiled successfully. Tests include seeded randomized conservation and idempotence checks for all four flag combinations, input preservation, rejection cases, HTML escaping, and CLI behavior. These checks use synthetic data and do not guarantee correctness for every input or environment.

2026-09-30 在 Linux / Python 3.12.14 下，11 项自动化测试通过，两份 Python 文件编译检查通过。测试含四种选项组合的固定种子随机守恒和幂等性、输入保留、拒绝输入、HTML 转义与命令行行为。合成测试不保证所有输入或环境均正确。

## Reproduce the examples / 复现样例

Use fresh output directories; existing paths are refused:

```sh
python csv_cleaner.py demo/before.csv verification-result --trim --deduplicate
python csv_cleaner.py demo/bad_width.csv rejection-result
```

The first command should exit 0, retaining five of six data records, removing one duplicate, and reporting two changed cells. The second should exit 2 and produce only audit files because record 2 has three cells under a two-column header. The checked-in demo reports contain no local absolute paths.

第一条命令应返回 0，六条数据记录保留五条、删除一条重复记录，并记录两个变化的单元格。第二条命令应返回 2，因第二条记录与表头列数不符而仅生成审计文件。仓库样例报告不含本机绝对路径。

The example CSV files can contain formula-like text. Review them as plain text; formula detection warns but does not sanitize. HTML escaping and its content-security-policy are unit-tested; browser rendering was not tested.

样例可能包含疑似公式文本，请用纯文本查看；公式检测仅提示，不净化风险。HTML 转义及内容安全策略已进行单元测试，未进行浏览器渲染测试。

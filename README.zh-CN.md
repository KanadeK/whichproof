# WhichProof

> 不执行目标命令，也能证明自动化最终会选中哪个可执行文件。

[English](README.md) · [规格](docs/SPEC.md) · [修复指南](docs/repair-guide.md) ·
[竞品与重叠核对](docs/research.md)

`which`、`where` 或 `Get-Command` 只能回答当前机器此刻选中了什么。WhichProof 会枚举 PATH
中同名的所有可执行候选、记录胜出文件的字节身份，并生成可在另一台机器或 CI 上复验的快照。

它不会执行 `--version`、不会加载 shell profile、不会运行候选文件，也不会上传快照。

## 快速开始

需要 Python 3.12 或更高版本：

```bash
python -m pip install "https://github.com/KanadeK/whichproof/releases/download/v0.1.0/whichproof-0.1.0-py3-none-any.whl"
whichproof capture python git node --output toolchain.json
whichproof verify toolchain.json
```

比较两份既有快照：

```bash
whichproof diff local.json ci.json --format json
```

退出码：`0` 表示捕获成功或环境等价，`1` 表示发现漂移，`2` 表示输入/文件/运行失败。

## 它真正检查什么

- 原先存在的命令现在是否消失，或原先缺失的命令是否突然出现；
- PATH 首选文件的 SHA-256 是否改变；
- 首选文件是否只是换了路径但字节完全相同；
- 备用候选的字节身份或顺序是否变化；
- 操作系统、架构、PATH 分隔符或 PATHEXT 规则是否变化；
- 两份快照的命令清单是否一致。

运行真实的合成示例：

```bash
uv sync --locked
uv run python scripts/demo.py
```

示例会先证明环境不变，然后只修改未胜出的候选文件，并验证 `WP105` 会让比较失败。

## 明确边界

WhichProof 的权威范围是 Python 3.12+ 的 PATH/PATHEXT 文件解析模型。shell alias、函数、内建命令、
Windows App Paths、注册表启动策略以及不同 `CreateProcess`/`ShellExecute` 路径不在 v0.1.0 内，
工具不会把这些互不相同的真源混在一起制造“万能解析器”的假象。

快照含绝对 PATH 和文件路径，分享前应当审阅。快照不含文件内容，只含路径、真实路径、大小和哈希；
项目没有网络代码或遥测。

完整验收：

```bash
uv run python scripts/check.py
```

该命令覆盖静态检查、严格类型检查、分支覆盖率、构建、归档检查、隔离安装、成功/失败示例与非法输入。

# T03 Python 3.13.13 依赖验证记录

验证日期：2026-08-05  
任务：T03（仅环境与依赖验证；未连接 MySQL、未读取 Olist CSV、未运行项目脚本或 Notebook）。

## 1. 环境与依赖文件

- 正式解释器：`D:\python\python.exe`，Python 3.13.13。
- 正式虚拟环境：`.venv/`，`include-system-site-packages = false`。
- pip：26.0.1；未升级。安装过程中提示 pip 26.2.1 可用，按任务约束未处理。
- `requirements.in`：9 个一期直接依赖及最低兼容边界，不含传递依赖。
- `requirements.txt`：由已验证正式环境执行 `python -m pip freeze` 生成，共 110 条固定版本；SHA-256 为 `1E94EDC9A92EF78AA99F55F4476FA4F8261BF610E6583D99304E0913EE9DC4DB`。
- 扫描结果：`requirements.txt` 不包含本机绝对路径、`file://`、editable、本地项目路径或 Git 地址。

## 2. 实际直接依赖版本

| 直接依赖 | 已验证版本 |
| --- | --- |
| numpy | 2.5.1 |
| pandas | 3.0.5 |
| scipy | 1.18.0 |
| matplotlib | 3.11.1 |
| jupyter | 1.1.1 |
| ipykernel | 7.3.0 |
| SQLAlchemy | 2.0.51 |
| PyMySQL | 1.2.0 |
| python-dotenv | 1.2.2 |

主要传递依赖包括 JupyterLab 4.6.2、notebook 7.6.1、jupyter-server 2.20.0、IPython 9.16.1、python-dateutil 2.9.0.post0、tzdata 2026.3、Pillow 12.3.0、contourpy 1.3.3、greenlet 3.5.4、requests 2.34.2、SQLAlchemy 所需 typing-extensions 4.16.0 等；完整清单以 `requirements.txt` 为准。

## 3. 安装与兼容性结果

首次普通网络安装受到沙箱套接字权限限制（`WinError 10013`）；首次受控网络安装在 124 秒超时，未安装项目包。经用户授权后，使用同一 `.venv`、同一 `requirements.in` 重试：

```powershell
.\.venv\Scripts\python.exe -m pip install --prefer-binary --timeout 120 --retries 5 --progress-bar off --disable-pip-version-check -r requirements.in
```

重试在 333 秒内成功。核心包使用 Windows / Python 3.13 wheel（例如 `numpy-2.5.1-cp313-cp313-win_amd64.whl`、`pandas-3.0.5-cp313-cp313-win_amd64.whl`、`scipy-1.18.0-cp313-cp313-win_amd64.whl`）；未发生源码编译、依赖解析冲突或 Python 3.13 兼容性警告。

## 4. 正式环境验证

- `pip check`：通过，未发现损坏依赖。
- 全部直接依赖已成功导入并读取实际版本。
- NumPy：数组创建、求和和均值通过。
- pandas：DataFrame、`groupby`、`merge(validate='many_to_one')` 和日期转换通过。
- SciPy：`scipy.stats.spearmanr`、`chi2_contingency`、`mannwhitneyu` 均实际执行并返回有限统计量。
- matplotlib：使用 `Agg` 非交互后端在系统临时目录生成并校验 PNG；未在项目报告或仪表盘目录生成图表。
- SQLAlchemy + PyMySQL：模块导入、`mysql+pymysql` URL/Engine 构造通过；未调用连接，不读取 `.env`。
- Jupyter：`python -m jupyter --version` 正常；ipykernel 发行版版本为 7.3.0；未注册用户级或系统级 kernel。

## 5. 全新环境复现验证

使用相同的 `D:\python\python.exe` 创建临时 `.venv_t03_verify/`，并以：

```powershell
.\.venv_t03_verify\Scripts\python.exe -m pip install -r requirements.txt
```

成功安装冻结清单。临时环境 `pip check` 通过，全部直接依赖版本与正式 `.venv` 完全一致；重复通过 pandas、三项 SciPy 检验、matplotlib 临时图、Jupyter/ipykernel 与 SQLAlchemy/PyMySQL 非连接测试。该临时目录仅由 T03 创建，验证后可安全删除。

## 6. 回滚与限制

- 本任务未修改 README、PBIX、SQL、`data/raw/`、`data/processed/` 或 MySQL。
- 旧环境仍保留为 `.venv_broken_backup_20260805/`。
- 若之后必须回滚依赖文件，可在用户确认后恢复 T03 前的 `requirements.txt` SHA-256 基线，并删除仅由 T03 创建的 `requirements.in`；不得删除旧环境备份。
- 当前验证不等同于数据库连接、项目脚本、Notebook、数据处理或 Power BI 验证；这些均属于后续经确认任务。

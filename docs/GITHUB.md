# 开源到 GitHub 步骤

## 1. 本地初始化（若还没有 git）

在项目目录 `D:\C\dev\caidb\cursor-clean`：

```bash
git init
git add .
git commit -m "Initial release of cursor-clean"
```

## 2. 在 GitHub 建空仓库

1. 打开 https://github.com/new  
2. Repository name：`cursor-clean`  
3. Public  
4. **不要**勾选 README / .gitignore / license（本地已有）  
5. Create repository  

## 3. 关联并推送

把 `YOUR_USER` 换成你的 GitHub 用户名：

```bash
git branch -M main
git remote add origin https://github.com/YOUR_USER/cursor-clean.git
git push -u origin main
```

或用 GitHub CLI（已登录时）：

```bash
gh repo create cursor-clean --public --source=. --remote=origin --push
```

## 4. 建议补充

- 仓库描述：`Lightweight CLI to clean Cursor Roaming data on Windows`
- Topics：`cursor` `python` `disk-cleanup` `cli`
- 在 README 顶部加上 PyPI 徽章：

```markdown
[![PyPI](https://img.shields.io/pypi/v/cursor-clean.svg)](https://pypi.org/project/cursor-clean/)
```

- Releases：可打 tag `v0.1.2` 与 PyPI 版本对齐  

## 5. 与 PyPI 联动（可选）

在 `pyproject.toml` 的 `[project.urls]` 写上真实 GitHub 地址，下次发版时更新。

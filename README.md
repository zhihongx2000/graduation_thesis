# 安装
## 1. clone此仓库到本地
ssh方式：
```bash
git clone --single-branch --branch master git@github.com:zhihongx2000/agent_template.git
```
https方式：
```bash
git clone --single-branch --branch master https://github.com/zhihongx2000/agent_template.git
```
## 2. 安装uv
NOTE：此步骤需连接梯子。
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## 3. 同步环境
cd到项目目录下，执行以下命令：
```bash
uv python install 3.12.7
uv venv --python 3.12.7
uv sync
```
注意：
1. 若下载速度过慢，请在当前项目的`pyproject.toml`文件中，添加以下配置项：
```toml
[[tool.uv.index]]
url = "https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple"
default = true
 
[tool.uv.pip]
index-url = "https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple"
```
2. 若PyCharm提示配置的解释器路径无效，请重启PyCharm。

## 4. 验证是否安装成功
```bash

```
# 2. 如何使用模板？
## 2.1 模板说明

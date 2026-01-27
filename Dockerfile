# 使用轻量级 Python 镜像
FROM python:3.14-slim

# 设置工作目录
WORKDIR /app

# 安装 git (pip 安装依赖时可能需要)
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装依赖 (使用清华源加速，如果服务器在海外可去掉 -i 参数)
RUN pip install --no-cache-dir -r requirements.txt

# 复制所有代码
COPY . .

# 运行入口
CMD ["python", "main.py"]
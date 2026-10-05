import os
import tempfile

# api 在导入时会建表并启动认领线程；测试用临时文件 sqlite 自包含运行，
# 不依赖容器里的 PostgreSQL。必须在导入 api 之前设置。
_fd, _path = tempfile.mkstemp(prefix="tunnelconv-test-", suffix=".db")
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_path}")

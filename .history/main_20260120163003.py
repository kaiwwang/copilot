"""
AI Agent - GitHub PR 分析助手

使用方法：
    python main.py

环境变量：
    GITHUB_TOKEN    GitHub API Token（私有仓库需要）
    GEMINI_API_KEY  Gemini API Key
    LOG_LEVEL       日志级别（DEBUG/INFO/WARNING/ERROR）
"""

from app.core.config import Settings
from app.core.logger import get_logger
from app.ui.cli import CliApp


def main() -> None:
    """主入口函数"""
    # 加载配置
    settings = Settings()
    
    # 初始化日志
    logger = get_logger(settings)
    
    # 启动 CLI 应用
    app = CliApp(settings=settings, logger=logger)
    app.run()


if __name__ == "__main__":
    main()

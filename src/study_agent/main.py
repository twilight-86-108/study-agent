"""StudyAgent entry point.

アプリケーションのメインエントリーポイント。
pyproject.tomlのscriptsセクションから参照される。

Example:
    $ study-agent --help
    $ python -m study_agent.main
"""

from study_agent.cli import cli_main


def main() -> None:
    """Main entry point."""
    cli_main()


if __name__ == "__main__":
    main()

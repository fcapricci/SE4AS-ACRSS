class Logger:

    SEPARATION_LINES_LEN = 60

    @classmethod
    def log_header(cls, header : str) -> None:

        # ==== HEADER ====

        print("=" * cls.SEPARATION_LINES_LEN)
        print(header)
        print("=" * cls.SEPARATION_LINES_LEN)

    @classmethod
    def log_section(cls, title : str, *lines : str) -> None:

        # ---- {title} ----
        # line
        # ...
        # line

        print("-" * cls.SEPARATION_LINES_LEN + title + "-" * cls.SEPARATION_LINES_LEN)
        for line in lines:
            print(line)
        
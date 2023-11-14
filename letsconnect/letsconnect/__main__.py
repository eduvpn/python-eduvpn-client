from letsconnect.variant import VARIANT


def cli():
    from eduvpn_base.cli import main

    main(variant=VARIANT)


def gui():
    from eduvpn_base.ui.__main__ import main_loop

    main_loop(variant=VARIANT)


if __name__ == "__main__":
    gui()

import unittest

if __name__ == "__main__":
    suite = unittest.defaultTestLoader.discover(
        start_dir=".",
        pattern="testar_*.py",
        top_level_dir="."
    )

    resultado = unittest.TextTestRunner(
        verbosity=2
    ).run(suite)

    if not resultado.wasSuccessful():
        raise SystemExit(1)
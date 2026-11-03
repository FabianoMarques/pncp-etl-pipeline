import unittest
from pathlib import Path

if __name__ == "__main__":
    diretorio_testes = Path(__file__).parent

    suite = unittest.defaultTestLoader.discover(
        start_dir=str(diretorio_testes),
        pattern="testar_*.py"
    )

    resultado = unittest.TextTestRunner(
        verbosity=2
    ).run(suite)

    if not resultado.wasSuccessful():
        raise SystemExit(1)
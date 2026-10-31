import os
import psycopg2
from dotenv import load_dotenv

load_dotenv(override=True)

try:
    conexao = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST"),
        port=os.getenv("POSTGRES_PORT"),
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD")
    )

    print("Conexão com PostgreSQL estabelecida com sucesso!")

    cursor = conexao.cursor()
    cursor.execute("SELECT current_database(), current_user;")

    resultado = cursor.fetchone()

    print(f"Banco: {resultado[0]}")
    print(f"Usuário: {resultado[1]}")

    cursor.close()
    conexao.close()

except Exception as erro:
    print("Falha na conexão:")
    print(erro)
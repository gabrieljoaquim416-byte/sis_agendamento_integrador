
import os
import mysql.connector

from dotenv import load_dotenv
from mysql.connector import Error

load_dotenv()


def conectar():
    try:
        conexao = mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME", "sistema_agendamento")
        )

        if conexao.is_connected():
            return conexao

    except Error as erro:
        print(f"Erro ao conectar ao MySQL: {erro}")

    return None

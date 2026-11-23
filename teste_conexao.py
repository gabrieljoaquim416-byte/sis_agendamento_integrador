from conexao import conectar

banco = conectar()

if banco:
    cursor = banco.cursor()

    cursor.execute("SELECT DATABASE()")

    resultado = cursor.fetchone()

    print("Banco conectado:", resultado[0])

    cursor.close()
    banco.close()

    print("Conexão encerrada.")
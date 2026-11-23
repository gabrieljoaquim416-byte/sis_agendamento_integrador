
from flask import Flask, render_template, request, redirect, url_for, flash
from conexao import conectar
from datetime import datetime, date, time, timedelta

app = Flask(__name__)
app.secret_key = "chave_local_agendamento"



# DASHBOARD
@app.route("/")
def inicio():

    banco = conectar()

    dados = {
        "total": 0,
        "confirmados": 0,
        "pendentes": 0,
        "cancelados": 0,
        "agendamentos_hoje": 0,
        "agendamentos": []
    }

    if banco is None:
        flash("Erro ao conectar ao banco de dados.", "erro")
        return render_template("index.html", **dados)

    cursor = None

    try:
        cursor = banco.cursor(dictionary=True)

        # Total de agendamentos
        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM agendamentos
        """)
        dados["total"] = cursor.fetchone()["total"]

        # Quantidade por status
        cursor.execute("""
            SELECT status, COUNT(*) AS quantidade
            FROM agendamentos
            GROUP BY status
        """)

        for registro in cursor.fetchall():
            status = registro["status"]
            quantidade = registro["quantidade"]

            if status == "Confirmado":
                dados["confirmados"] = quantidade

            elif status == "Pendente":
                dados["pendentes"] = quantidade

            elif status == "Cancelado":
                dados["cancelados"] = quantidade

        # Agendamentos ativos do dia
        cursor.execute("""
            SELECT COUNT(*) AS quantidade
            FROM agendamentos
            WHERE data_agendamento = CURDATE()
            AND status IN ('Pendente', 'Confirmado')
        """)

        dados["agendamentos_hoje"] = (
            cursor.fetchone()["quantidade"]
        )

        # Próximos agendamentos
        cursor.execute("""
            SELECT *
            FROM agendamentos
            WHERE (
                data_agendamento > CURDATE()
                OR (
                    data_agendamento = CURDATE()
                    AND horario >= CURTIME()
                )
            )
            AND status IN ('Pendente', 'Confirmado')
            ORDER BY data_agendamento ASC, horario ASC
            LIMIT 10
        """)

        dados["agendamentos"] = cursor.fetchall()

    except Exception as erro:
        print("Erro ao carregar Dashboard:", erro)
        flash("Não foi possível carregar o Dashboard.", "erro")

    finally:
        if cursor is not None:
            cursor.close()

        banco.close()

    return render_template("index.html", **dados)



# CADASTRO DE AGENDAMENTOS
@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():

    if request.method == "POST":

        nome = request.form.get("nome_cliente", "").strip()
        telefone = request.form.get("telefone", "").strip()
        servico = request.form.get("servico", "").strip()
        data_agendamento = request.form.get("data_agendamento", "")
        horario = request.form.get("horario", "")
        observacoes = request.form.get("observacoes", "").strip()

        if not all([nome, telefone, servico, data_agendamento, horario]):
            flash("Preencha todos os campos obrigatórios.", "erro")
            return redirect(url_for("cadastro"))

        try:
            data_validada = datetime.strptime(
                data_agendamento, "%Y-%m-%d"
            ).date()

            datetime.strptime(horario, "%H:%M")

            if data_validada < date.today():
                flash("Não é permitido cadastrar datas passadas.", "erro")
                return redirect(url_for("cadastro"))

        except ValueError:
            flash("Data ou horário inválido.", "erro")
            return redirect(url_for("cadastro"))

        banco = conectar()

        if banco is None:
            flash("Erro ao conectar ao banco de dados.", "erro")
            return redirect(url_for("cadastro"))

        cursor = banco.cursor()

        try:
            cursor.execute("""
                SELECT id
                FROM agendamentos
                WHERE data_agendamento = %s
                AND horario = %s
                AND status IN ('Pendente', 'Confirmado')
            """, (data_agendamento, horario))

            conflito = cursor.fetchone()

            if conflito:
                flash("Este horário já está ocupado.", "erro")
                return redirect(url_for("cadastro"))

            cursor.execute("""
                INSERT INTO agendamentos
                (nome_cliente, telefone, servico,
                 data_agendamento, horario, observacoes)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                nome,
                telefone,
                servico,
                data_agendamento,
                horario,
                observacoes
            ))

            banco.commit()

            flash("Agendamento cadastrado com sucesso!", "sucesso")
            return redirect(url_for("inicio"))

        except Exception as erro:
            banco.rollback()
            print("Erro ao cadastrar:", erro)
            flash("Não foi possível cadastrar o agendamento.", "erro")

        finally:
            cursor.close()
            banco.close()

        return redirect(url_for("cadastro"))

    return render_template("cadastro.html")

# LISTAGEM DE AGENDAMENTOS
@app.route("/agendamentos")
def listar_agendamentos():

    banco = conectar()

    if banco is None:
        flash("Erro ao conectar ao banco de dados.", "erro")
        return render_template(
            "agendamentos.html",
            agendamentos=[]
        )

    cursor = banco.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT *
            FROM agendamentos
            ORDER BY data_agendamento ASC, horario ASC
        """)

        agendamentos = cursor.fetchall()

    except Exception as erro:
        print("Erro ao listar agendamentos:", erro)
        flash("Não foi possível carregar os agendamentos.", "erro")
        agendamentos = []

    finally:
        cursor.close()
        banco.close()

    return render_template(
        "agendamentos.html",
        agendamentos=agendamentos
    )

# EDITAR AGENDAMENTO
@app.route("/editar/<int:id>", methods=["GET", "POST"])
def editar_agendamento(id):

    banco = conectar()

    if banco is None:
        flash("Erro ao conectar ao banco de dados.", "erro")
        return redirect(url_for("listar_agendamentos"))

    cursor = banco.cursor(dictionary=True)

    try:
        cursor.execute(
            "SELECT * FROM agendamentos WHERE id = %s",
            (id,)
        )

        agendamento = cursor.fetchone()

        if agendamento is None:
            flash("Agendamento não encontrado.", "erro")
            return redirect(url_for("listar_agendamentos"))

        if request.method == "POST":

            nome = request.form.get("nome_cliente", "").strip()
            telefone = request.form.get("telefone", "").strip()
            servico = request.form.get("servico", "").strip()
            data = request.form.get("data_agendamento", "")
            horario = request.form.get("horario", "")
            observacoes = request.form.get("observacoes", "").strip()

            if not all([nome, telefone, servico, data, horario]):
                flash("Preencha todos os campos obrigatórios.", "erro")
                return redirect(url_for("editar_agendamento", id=id))

            try:
                data_validada = datetime.strptime(
                    data, "%Y-%m-%d"
                ).date()

                datetime.strptime(horario, "%H:%M")

                if data_validada < date.today():
                    flash("Não é permitido selecionar datas passadas.", "erro")
                    return redirect(url_for("editar_agendamento", id=id))

            except ValueError:
                flash("Data ou horário inválido.", "erro")
                return redirect(url_for("editar_agendamento", id=id))

            cursor.execute("""
                SELECT id FROM agendamentos
                WHERE data_agendamento = %s
                AND horario = %s
                AND id != %s
                AND status IN ('Pendente', 'Confirmado')
            """, (data, horario, id))

            if cursor.fetchone():
                flash("Este horário já está ocupado.", "erro")
                return redirect(url_for("editar_agendamento", id=id))

            cursor.execute("""
                UPDATE agendamentos
                SET nome_cliente = %s,
                    telefone = %s,
                    servico = %s,
                    data_agendamento = %s,
                    horario = %s,
                    observacoes = %s
                WHERE id = %s
            """, (
                nome, telefone, servico,
                data, horario, observacoes, id
            ))

            banco.commit()

            flash("Agendamento atualizado com sucesso!", "sucesso")
            return redirect(url_for("listar_agendamentos"))

        horario_banco = agendamento["horario"]

        if isinstance(horario_banco, timedelta):
            total_segundos = int(horario_banco.total_seconds())
            horas = total_segundos // 3600
            minutos = (total_segundos % 3600) // 60
            agendamento["horario"] = f"{horas:02d}:{minutos:02d}"

        elif isinstance(horario_banco, time):
            agendamento["horario"] = horario_banco.strftime("%H:%M")

        else:
            agendamento["horario"] = str(horario_banco)[:5]

        return render_template(
            "editar.html",
            agendamento=agendamento
        )

    except Exception as erro:
        banco.rollback()
        print("Erro ao editar agendamento:", erro)
        flash("Não foi possível editar o agendamento.", "erro")
        return redirect(url_for("listar_agendamentos"))

    finally:
        cursor.close()
        banco.close()

# ALTERAR STATUS DO AGENDAMENTO
@app.route("/status/<int:id>/<novo_status>", methods=["POST"])
def alterar_status(id, novo_status):

    status_permitidos = ["Pendente", "Confirmado", "Cancelado"]

    if novo_status not in status_permitidos:
        flash("Status inválido.", "erro")
        return redirect(url_for("listar_agendamentos"))

    banco = conectar()

    if banco is None:
        flash("Erro ao conectar ao banco de dados.", "erro")
        return redirect(url_for("listar_agendamentos"))

    cursor = banco.cursor(dictionary=True)

    try:
        cursor.execute(
            "SELECT * FROM agendamentos WHERE id = %s",
            (id,)
        )

        agendamento = cursor.fetchone()

        if agendamento is None:
            flash("Agendamento não encontrado.", "erro")
            return redirect(url_for("listar_agendamentos"))

        if novo_status in ["Pendente", "Confirmado"]:

            cursor.execute("""
                SELECT id FROM agendamentos
                WHERE data_agendamento = %s
                AND horario = %s
                AND id != %s
                AND status IN ('Pendente', 'Confirmado')
            """, (
                agendamento["data_agendamento"],
                agendamento["horario"],
                id
            ))

            if cursor.fetchone():
                flash("Existe outro agendamento neste horário.", "erro")
                return redirect(url_for("listar_agendamentos"))

        cursor.execute("""
            UPDATE agendamentos
            SET status = %s
            WHERE id = %s
        """, (novo_status, id))

        banco.commit()

        flash("Status atualizado com sucesso!", "sucesso")

    except Exception as erro:
        banco.rollback()
        print("Erro ao alterar status:", erro)
        flash("Não foi possível atualizar o status.", "erro")

    finally:
        cursor.close()
        banco.close()

    return redirect(url_for("listar_agendamentos"))

# EXCLUIR AGENDAMENTO
@app.route("/excluir/<int:id>", methods=["GET", "POST"])
def excluir_agendamento(id):

    banco = conectar()

    if banco is None:
        flash("Erro ao conectar ao banco de dados.", "erro")
        return redirect(url_for("listar_agendamentos"))

    cursor = banco.cursor(dictionary=True)

    try:
        # Consultar o agendamento pelo ID
        cursor.execute(
            "SELECT * FROM agendamentos WHERE id = %s",
            (id,)
        )

        agendamento = cursor.fetchone()

        if agendamento is None:
            flash("Agendamento não encontrado.", "erro")
            return redirect(url_for("listar_agendamentos"))

        # GET: apresentar a página de confirmação
        if request.method == "GET":
            return render_template(
                "excluir.html",
                agendamento=agendamento
            )

        # POST: excluir o agendamento
        cursor.execute(
            "DELETE FROM agendamentos WHERE id = %s",
            (id,)
        )

        banco.commit()

        flash("Agendamento excluído com sucesso!", "sucesso")
        return redirect(url_for("listar_agendamentos"))

    except Exception as erro:
        banco.rollback()
        print("Erro ao excluir agendamento:", erro)

        flash("Não foi possível excluir o agendamento.", "erro")
        return redirect(url_for("listar_agendamentos"))

    finally:
        cursor.close()
        banco.close()


if __name__ == "__main__":
    app.run(debug=True)

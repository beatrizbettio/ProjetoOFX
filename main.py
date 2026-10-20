import os
from datetime import datetime
from dotenv import load_dotenv
from ofxparse import OfxParser
import psycopg2

load_dotenv()

DB_CONFIG = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT")
}

CATEGORIAS_DISPONIVEIS = [
    "Recebimento PIX",
    "Recebimento de Clientes",
    "Serviços Prestados",
    "Aluguel & Condomínio",
    "Energia Elétrica",
    "Internet / Telecom",
    "Material e Suprimentos",
    "Folha de Pagamento",
    "Tecnologia / TI",
    "Manutenção Geral",
    "Transporte & Viagens",
    "Outras Receitas",
    "Outras Despesas"
]

def classificar_transacao(descricao: str, valor: float) -> str:
    desc = (descricao or "").upper()
    
    if valor > 0:
        if "PIX" in desc:
            return "Recebimento PIX"
        elif any(kw in desc for kw in ["RECEBIMENTO", "PAGAMENTO CLIENTE"]):
            return "Recebimento de Clientes"
        elif "PROJETO" in desc or "CONSULTORIA" in desc:
            return "Serviços Prestados"
        return "Outras Receitas"
    else:
        if "ALUGUEL" in desc:
            return "Aluguel & Condomínio"
        elif "ENERGIA" in desc or "LUZ" in desc:
            return "Energia Elétrica"
        elif "INTERNET" in desc or "TELEFONIA" in desc:
            return "Internet / Telecom"
        elif "MATERIAL" in desc:
            return "Material e Suprimentos"
        elif "FOLHA" in desc or "SALARIO" in desc:
            return "Folha de Pagamento"
        elif "EQUIPAMENTO" in desc or "CLOUD" in desc or "SOFTWARE" in desc:
            return "Tecnologia / TI"
        elif "MANUTENCAO" in desc or "VEICULO" in desc:
            return "Manutenção Geral"
        elif "ESTACIONAMENTO" in desc or "COMBUSTIVEL" in desc:
            return "Transporte & Viagens"
        return "Outras Despesas"

def processar_e_salvar_ofx(caminho_arquivo: str = "extrato.ofx"):
    if not os.path.exists(caminho_arquivo):
        print(f"\n  Erro: Arquivo '{caminho_arquivo}' nao encontrado.\n")
        return

    try:
        with open(caminho_arquivo, "rb") as arquivo:
            ofx = OfxParser.parse(arquivo)

        transacoes = ofx.account.statement.transactions
        entradas = 0.0
        saidas = 0.0
        inseridos = 0
        duplicados = 0

        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        query_insert = """
            INSERT INTO movimentacoes (fitid, data_movimentacao, valor, descricao, tipo, categoria)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (fitid) DO NOTHING;
        """

        print("\n" + "─" * 80)
        print(" PROCESSAMENTO DE EXTRATO")
        print("─" * 80)
        print(f" {'DATA':<10}   {'VALOR (R$)':>12}   {'TIPO':<8}   {'CATEGORIA':<22}   {'DESCRICAO'}")
        print("─" * 80)

        for t in transacoes:
            valor_transacao = float(t.amount)
            tipo = "ENTRADA" if valor_transacao > 0 else "SAIDA"
            categoria = classificar_transacao(t.memo, valor_transacao)

            if valor_transacao > 0:
                entradas += valor_transacao
            else:
                saidas += valor_transacao

            fitid = getattr(t, 'id', f"{t.date}_{valor_transacao}_{t.memo}")

            cursor.execute(query_insert, (
                fitid,
                t.date,
                valor_transacao,
                t.memo,
                tipo,
                categoria
            ))

            if cursor.rowcount > 0:
                inseridos += 1
            else:
                duplicados += 1

            dt_str = t.date.strftime('%d/%m/%Y')
            print(f" {dt_str:<10}   {valor_transacao:12.2f}   {tipo:<8}   {categoria:<22}   {t.memo}")

        conn.commit()
        cursor.close()
        conn.close()

        saldo_calculado = entradas + saidas

        print("─" * 80)
        print(" RESUMO DA IMPORTACAO")
        print("─" * 80)
        print(f" Registros no arquivo : {len(transacoes)}")
        print(f" Inseridos            : {inseridos}")
        print(f" Duplicados ignorados : {duplicados}")
        print("─" * 40)
        print(f" Total entradas       : R$ {entradas:10.2f}")
        print(f" Total saidas         : R$ {saidas:10.2f}")
        print(f" Saldo apurado        : R$ {saldo_calculado:10.2f}")
        print("─" * 80 + "\n")

    except Exception as e:
        print(f"\n  Erro ao processar arquivo: {e}\n")

def inserir_transacao_manual():
    print("\n" + "─" * 50)
    print(" NOVO LANCAMENTO MANUAL")
    print("─" * 50)

    data_str = input(" Data (DD/MM/AAAA) [Enter para hoje]: ").strip()
    if not data_str:
        data_movimentacao = datetime.now().date()
    else:
        try:
            data_movimentacao = datetime.strptime(data_str, "%d/%m/%Y").date()
        except ValueError:
            print("\n  Erro: Formato de data invalido.\n")
            return

    descricao = input(" Descricao: ").strip()
    if not descricao:
        print("\n  Erro: A descricao nao pode ser vazia.\n")
        return

    try:
        valor = float(input(" Valor (ex: 150.00 ou -50.00): ").replace(",", "."))
    except ValueError:
        print("\n  Erro: Valor numerico invalido.\n")
        return

    tipo = "ENTRADA" if valor > 0 else "SAIDA"

    print("\n Categoria:")
    print("─" * 35)
    for idx, cat in enumerate(CATEGORIAS_DISPONIVEIS, start=1):
        print(f"  {idx:2d}. {cat}")
    print(f"  {len(CATEGORIAS_DISPONIVEIS) + 1:2d}. Personalizada")
    print("─" * 35)

    try:
        opcao_cat = int(input(" Selecao: "))
        if 1 <= opcao_cat <= len(CATEGORIAS_DISPONIVEIS):
            categoria = CATEGORIAS_DISPONIVEIS[opcao_cat - 1]
        elif opcao_cat == len(CATEGORIAS_DISPONIVEIS) + 1:
            categoria = input(" Nome da categoria: ").strip()
            if not categoria:
                categoria = "Outras Receitas" if valor > 0 else "Outras Despesas"
        else:
            categoria = "Outras Receitas" if valor > 0 else "Outras Despesas"
    except ValueError:
        categoria = "Outras Receitas" if valor > 0 else "Outras Despesas"

    fitid_manual = f"MANUAL_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        query_insert = """
            INSERT INTO movimentacoes (fitid, data_movimentacao, valor, descricao, tipo, categoria)
            VALUES (%s, %s, %s, %s, %s, %s);
        """

        cursor.execute(query_insert, (
            fitid_manual,
            data_movimentacao,
            valor,
            descricao,
            tipo,
            categoria
        ))

        conn.commit()
        cursor.close()
        conn.close()

        print("\n  Registro salvo com sucesso.\n")

    except Exception as e:
        print(f"\n  Erro ao salvar no banco: {e}\n")

def listar_movimentacoes_banco():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, data_movimentacao, valor, tipo, categoria, descricao 
            FROM movimentacoes 
            ORDER BY data_movimentacao DESC, id DESC 
            LIMIT 20;
        """)
        registros = cursor.fetchall()

        cursor.close()
        conn.close()

        if not registros:
            print("\n  Nenhum registro encontrado no banco de dados.\n")
            return

        print("\n" + "─" * 85)
        print(" ULTIMOS REGISTROS CADASTRADOS")
        print("─" * 85)
        print(f" {'ID':<4}   {'DATA':<10}   {'VALOR (R$)':>12}   {'TIPO':<8}   {'CATEGORIA':<22}   {'DESCRICAO'}")
        print("─" * 85)

        for r in registros:
            id_reg, dt, val, tp, cat, desc = r
            dt_str = dt.strftime('%d/%m/%Y') if dt else ""
            val_float = float(val) if val is not None else 0.0
            print(f" {id_reg:<4}   {dt_str:<10}   {val_float:12.2f}   {tp:<8}   {cat:<22}   {desc}")

        print("─" * 85 + "\n")

    except Exception as e:
        print(f"\n  Erro ao consultar banco: {e}\n")

def exibir_menu():
    while True:
        print("─" * 35)
        print(" GESTAO FINANCEIRA")
        print("─" * 35)
        print(" 1. Importar arquivo OFX")
        print(" 2. Inserir lancamento manual")
        print(" 3. Consultar registros no banco")
        print(" 0. Sair")
        print("─" * 35)
        
        opcao = input(" Opcao: ").strip()

        if opcao == "1":
            nome_arq = input("\n Arquivo OFX [Enter para extrato.ofx]: ").strip()
            if not nome_arq:
                nome_arq = "extrato.ofx"
            processar_e_salvar_ofx(nome_arq)
        elif opcao == "2":
            inserir_transacao_manual()
        elif opcao == "3":
            listar_movimentacoes_banco()
        elif opcao == "0":
            print("\n Programa encerrado.\n")
            break
        else:
            print("\n  Opcao invalida.\n")

if __name__ == "__main__":
    exibir_menu()
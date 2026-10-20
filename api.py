import os
from io import BytesIO
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from ofxparse import OfxParser
import psycopg2
from dotenv import load_dotenv

from main import classificar_transacao, DB_CONFIG

load_dotenv()

app = FastAPI(title="API Gestão Financeira OFX")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/upload-ofx")
async def upload_ofx(file: UploadFile = File(...)):
    if not file.filename.endswith('.ofx'):
        raise HTTPException(status_code=400, detail="Formato inválido. Envie um arquivo .ofx")

    try:
        # Lê os bytes do arquivo enviado
        conteudo = await file.read()
        
        # Converte os bytes em um fluxo de arquivo legível pelo OfxParser
        arquivo_memoria = BytesIO(conteudo)
        ofx = OfxParser.parse(arquivo_memoria)
        
        transacoes = ofx.account.statement.transactions

        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        query_insert = """
            INSERT INTO movimentacoes (fitid, data_movimentacao, valor, descricao, tipo, categoria)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (fitid) DO NOTHING;
        """

        registros = []
        inseridos = 0
        duplicados = 0
        entradas = 0.0
        saidas = 0.0

        for t in transacoes:
            valor_transacao = float(t.amount)
            tipo = "ENTRADA" if valor_transacao > 0 else "SAIDA"
            categoria = classificar_transacao(t.memo, valor_transacao)
            fitid = getattr(t, 'id', f"{t.date}_{valor_transacao}_{t.memo}")

            if valor_transacao > 0:
                entradas += valor_transacao
            else:
                saidas += valor_transacao

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

            registros.append({
                "data": t.date.strftime("%d/%m/%Y"),
                "valor": valor_transacao,
                "tipo": tipo,
                "categoria": categoria,
                "descricao": t.memo
            })

        conn.commit()
        cursor.close()
        conn.close()

        return {
            "sucesso": True,
            "total_registros": len(transacoes),
            "inseridos": inseridos,
            "duplicados": duplicados,
            "total_entradas": entradas,
            "total_saidas": saidas,
            "saldo": entradas + saidas,
            "transacoes": registros
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar arquivo: {str(e)}")
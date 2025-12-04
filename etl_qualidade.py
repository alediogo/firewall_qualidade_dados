import pandas as pd
import boto3
import os
from io import StringIO

# --- CONFIGURAÇÕES 
AWS_ACCESS_KEY = '(chave de acesso IAM)'
AWS_SECRET_KEY = '(chave de acesso secreta)'
BUCKET_NAME = 'datalake-alexandre-projeto'

# Caminhos
INPUT_FILE_KEY = 'raw/vendas_sujas.csv' 
OUTPUT_TRUSTED = 'trusted/vendas_limpas.csv'
OUTPUT_REJECTED = 'rejected/vendas_erros.csv'

def get_s3_client():
    return boto3.client('s3',
                        aws_access_key_id=AWS_ACCESS_KEY,
                        aws_secret_access_key=AWS_SECRET_KEY)

def processar_dados():
    s3 = get_s3_client()
    print("🔄 Baixando dados do S3...")

    try:
        # 1. Baixa o objeto do S3 para a memória
        response = s3.get_object(Bucket=BUCKET_NAME, Key=INPUT_FILE_KEY)
        csv_content = response['Body'].read().decode('utf-8')
        
        # 2. Lê com Pandas a partir da memória
        df = pd.read_csv(StringIO(csv_content))
        print(f"Total de linhas recebidas: {len(df)}")

        # --- REGRAS DE QUALIDADE ---
        
        # Regra 1: ID não pode ser vazio
        regra_id = df['id'].notnull()
        
        # Regra 2: Valor deve ser numérico e maior que 0
        # Força conversão para numérico (erros viram NaN)
        df['valor'] = pd.to_numeric(df['valor'], errors='coerce')
        regra_valor = df['valor'] > 0
        
        # Regra 3: Data deve ser válida
        df['data_venda_clean'] = pd.to_datetime(df['data_venda'], errors='coerce')
        regra_data = df['data_venda_clean'].notnull()

        # --- FILTRAGEM ---
        df_trusted = df[regra_id & regra_valor & regra_data].copy()
        df_rejected = df[~(regra_id & regra_valor & regra_data)].copy()
        
        # Limpeza final no Trusted
        df_trusted = df_trusted.drop(columns=['data_venda'])
        df_trusted = df_trusted.rename(columns={'data_venda_clean': 'data_venda'})

        # --- CARGA ---
        print(f"✅ Dados Aprovados: {len(df_trusted)}")
        print(f"❌ Dados Rejeitados: {len(df_rejected)}")

        salvar_no_s3(s3, df_trusted, OUTPUT_TRUSTED)
        salvar_no_s3(s3, df_rejected, OUTPUT_REJECTED)

    except Exception as e:
        print(f"❌ Erro fatal: {e}")

def salvar_no_s3(s3_client, df, key):
    csv_buffer = StringIO()
    df.to_csv(csv_buffer, index=False)
    
    s3_client.put_object(Bucket=BUCKET_NAME, Key=key, Body=csv_buffer.getvalue())
    print(f"Arquivo salvo em: s3://{BUCKET_NAME}/{key}")

if __name__ == "__main__":
    processar_dados()
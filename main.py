from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import psycopg2
import pandas as pd
import matplotlib.pyplot as plt
import io
import os
from fastapi.responses import FileResponse

app = FastAPI()

# Diretório para armazenar o gráfico
STATIC_DIR = 'static'
os.makedirs(STATIC_DIR, exist_ok=True)

# Conectar ao banco de dados PostgreSQL
def get_db_connection():
    try:
        connection = psycopg2.connect(
            dbname="tcc_wt2c",
            user="guilherme",
            password="ArRqQLQVOtJcdPs8DZLVmGWHxZy2ZJR6",
            host="dpg-crb3dsjtq21c73cf85rg-a.oregon-postgres.render.com",
            port="5432"
        )
        print("Conectado ao banco de dados.")
        return connection
    except Exception as e:
        print(f"Erro ao conectar ao banco de dados: {e}")
        raise HTTPException(status_code=500, detail="Erro ao conectar ao banco de dados")

# Modelo de dados usando Pydantic
class SensorData(BaseModel):
    esp_id: str
    rfid: str
    peso: float
    preco: float
    nome: str

@app.post("/sensor_data/")
def insert_sensor_data(sensor_data: SensorData):
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            INSERT INTO sensor_data (esp_id, rfid, peso, preco, nome)
            VALUES (%(esp_id)s, %(rfid)s, %(peso)s, %(preco)s, %(nome)s)
        """, sensor_data.dict())
        connection.commit()
        update_sales_chart()  # Atualiza o gráfico após a inserção
        return {"message": "Dados inseridos com sucesso"}
    except Exception as e:
        connection.rollback()
        print(f"Erro ao inserir dados: {e}")
        raise HTTPException(status_code=500, detail="Erro ao inserir dados no banco de dados")
    finally:
        cursor.close()
        connection.close()

@app.get("/sensor_data/{sensor_id}")
def get_sensor_data(sensor_id: int):
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("SELECT * FROM sensor_data WHERE id = %s", (sensor_id,))
        row = cursor.fetchone()
        if row:
            return {
                "id": row[0],
                "esp_id": row[1],
                "rfid": row[2],
                "peso": row[3],
                "preco": row[4],
                "nome": row[5]
            }
        else:
            raise HTTPException(status_code=404, detail="Dados não encontrados")
    except Exception as e:
        print(f"Erro ao consultar dados: {e}")
        raise HTTPException(status_code=500, detail="Erro ao consultar dados no banco de dados")
    finally:
        cursor.close()
        connection.close()

@app.get("/sales_chart")
def get_sales_chart():
    chart_path = os.path.join(STATIC_DIR, 'sales_chart.png')
    if os.path.exists(chart_path):
        return FileResponse(chart_path)
    else:
        raise HTTPException(status_code=404, detail="Gráfico não encontrado")

def update_sales_chart():
    connection = get_db_connection()
    query = """
    SELECT nome_produto, COUNT(*) AS quantidade_vendida
    FROM pedidos
    GROUP BY nome_produto
    ORDER BY quantidade_vendida DESC
    """
    df = pd.read_sql_query(query, connection)
    connection.close()

    plt.figure(figsize=(10, 6))
    plt.bar(df['nome_produto'], df['quantidade_vendida'])
    plt.xlabel('Nome do Produto')
    plt.ylabel('Quantidade Vendida')
    plt.title('Produtos Vendidos')
    plt.xticks(rotation=45)
    plt.tight_layout()

    chart_path = os.path.join(STATIC_DIR, 'sales_chart.png')
    plt.savefig(chart_path)
    plt.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

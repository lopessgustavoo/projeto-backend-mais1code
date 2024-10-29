from fastapi import FastAPI, HTTPException, Depends
from sqlmodel import SQLModel, Field, Session, create_engine, select
from typing import Optional, List

app = FastAPI()

# Configuração do banco de dados
engine = create_engine("sqlite:///database.db")
SQLModel.metadata.create_all(engine)

# Modelos
class Item(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str
    cor: str
    tamanho: str
    quantidade_disponivel: int
    preco: float
    favorito: bool = False  # Atributo favorito como booleano em Item

class CarrinhoItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    item_id: int = Field(foreign_key="item.id")
    quantidade: int
    preco_total: float

class Carrinho(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int  # Relacionamento com o usuário


# Sessão com o banco de dados
def get_session():
    with Session(engine) as session:
        yield session


# Endpoints do Carrinho

@app.post("/carrinho/adicionar_item/")
def adicionar_item(item_id: int, quantidade: int, session: Session = Depends(get_session)):
    # Adiciona um item ao carrinho, verificando o estoque
    item = session.get(Item, item_id)
    if not item or item.quantidade_disponivel < quantidade:
        raise HTTPException(status_code=400, detail="Estoque insuficiente.")
    preco_total = item.preco * quantidade
    carrinho_item = CarrinhoItem(item_id=item_id, quantidade=quantidade, preco_total=preco_total)
    session.add(carrinho_item)
    item.quantidade_disponivel -= quantidade  # Atualiza o estoque
    session.commit()
    return {"message": f"{quantidade}x {item.nome} adicionado ao carrinho."}


@app.delete("/carrinho/remover_item/")
def remover_item(item_id: int, session: Session = Depends(get_session)):
    # Remove um item do carrinho e devolve ao estoque
    carrinho_item = session.exec(select(CarrinhoItem).where(CarrinhoItem.item_id == item_id)).first()
    if not carrinho_item:
        raise HTTPException(status_code=404, detail="Item não encontrado no carrinho.")
    item = session.get(Item, item_id)
    session.delete(carrinho_item)
    item.quantidade_disponivel += carrinho_item.quantidade  # Devolve ao estoque
    session.commit()
    return {"message": "Item removido do carrinho."}


@app.patch("/carrinho/aplicar_cupom/")
def aplicar_cupom(desconto: float, session: Session = Depends(get_session)):
    # Aplica desconto ao total do carrinho
    total = sum(item.preco_total for item in session.exec(select(CarrinhoItem)).all())
    total_com_desconto = total * ((100 - desconto) / 100)
    return {"total_com_desconto": total_com_desconto, "desconto_aplicado": desconto}


@app.patch("/carrinho/calcular_frete/")
def calcular_frete(valor_frete: float, session: Session = Depends(get_session)):
    # Calcula o frete e adiciona ao total
    total = sum(item.preco_total for item in session.exec(select(CarrinhoItem)).all())
    total_com_frete = total + valor_frete
    return {"total_com_frete": total_com_frete, "frete": valor_frete}


@app.post("/carrinho/favoritar_item/")
def salvar_favorito(item_id: int, session: Session = Depends(get_session)):
    # Define um item como favorito
    item = session.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item não encontrado.")
    item.favorito = True
    session.commit()
    return {"message": "Item favoritado."}


@app.get("/carrinho/")
def visualizar_carrinho(session: Session = Depends(get_session)):
    # Exibe os itens do carrinho e o total
    itens = session.exec(select(CarrinhoItem)).all()
    carrinho = [{"item_id": item.item_id, "quantidade": item.quantidade, "preco_total": item.preco_total} for item in itens]
    total = sum(item.preco_total for item in itens)
    return {"itens": carrinho, "total": total}

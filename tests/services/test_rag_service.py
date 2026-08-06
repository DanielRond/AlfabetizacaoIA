from curumim.services import rag_service


class FakeCollection:
    def __init__(self, query_result=None):
        self.query_result = query_result
        self.added = []

    def query(self, *args, **kwargs):
        return self.query_result

    def add(self, documents, ids):
        self.added.append((documents, ids))


def test_buscar_contexto_retorna_documentos_concatenados(monkeypatch):
    fake = FakeCollection({"documents": [["doc um", "doc dois"]]})
    monkeypatch.setattr(rag_service, "_get_collection", lambda: fake)

    resultado = rag_service.buscar_contexto("pergunta")

    assert resultado == "doc um\ndoc dois"


def test_buscar_contexto_sem_resultados_retorna_vazio(monkeypatch):
    fake = FakeCollection({"documents": [[]]})
    monkeypatch.setattr(rag_service, "_get_collection", lambda: fake)

    assert rag_service.buscar_contexto("pergunta") == ""


def test_buscar_contexto_ignora_documents_invalidos(monkeypatch):
    fake = FakeCollection({"documents": None})
    monkeypatch.setattr(rag_service, "_get_collection", lambda: fake)

    assert rag_service.buscar_contexto("pergunta") == ""


def test_buscar_contexto_retorna_vazio_em_erro(monkeypatch):
    def explodir():
        raise RuntimeError("chroma fora do ar")

    monkeypatch.setattr(rag_service, "_get_collection", explodir)

    assert rag_service.buscar_contexto("pergunta") == ""


def test_adicionar_conhecimento_chama_collection(monkeypatch):
    fake = FakeCollection()
    monkeypatch.setattr(rag_service, "_get_collection", lambda: fake)

    rag_service.adicionar_conhecimento("texto", "id-1")

    assert fake.added == [(["texto"], ["id-1"])]

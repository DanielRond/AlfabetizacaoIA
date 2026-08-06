import pytest

from curumim.services import stt_service


def test_arquivo_inexistente_retorna_vazio():
    assert stt_service.transcrever_audio("C:/nao/existe.ogg") == ""


def test_transcrever_audio_retorna_texto_limpo(monkeypatch, tmp_path):
    arquivo = tmp_path / "audio.ogg"
    arquivo.write_bytes(b"fake")

    class FakeModel:
        def transcribe(self, caminhos, batch_size):
            assert caminhos == [str(arquivo)]
            return [["texto transcrito"]]

    monkeypatch.setattr(stt_service, "_get_model", lambda: FakeModel())

    assert stt_service.transcrever_audio(str(arquivo)) == "texto transcrito"


def test_transcrever_audio_propaga_erro(monkeypatch, tmp_path):
    arquivo = tmp_path / "audio.ogg"
    arquivo.write_bytes(b"fake")

    class FakeModelQuebrado:
        def transcribe(self, caminhos, batch_size):
            raise RuntimeError("modelo falhou")

    monkeypatch.setattr(stt_service, "_get_model", lambda: FakeModelQuebrado())

    with pytest.raises(RuntimeError, match="modelo falhou"):
        stt_service.transcrever_audio(str(arquivo))

import subprocess
import time

import soundfile as sf

from curumim.services import tts_service
from curumim.services.tts_service import _limpar_texto_para_audio


def test_remove_negrito_e_emoji():
    entrada = (
        "Olá! Que excelente pergunta! 😊\n\n"
        "De acordo com o texto que estamos estudando, os **búfalos são um "
        "símbolo muito marcante da cultura e do meio de transporte** lá na "
        "ilha do Marajó! Eles são animais super importantes para a "
        "identidade da ilha..."
    )
    resultado = _limpar_texto_para_audio(entrada)
    assert "**" not in resultado
    assert "😊" not in resultado
    assert "búfalos são um símbolo muito marcante" in resultado


def test_lista_com_negrito_vira_frases_separadas():
    entrada = (
        "Eles são superimportantes para os moradores de lá:\n"
        "* **No transporte:** servem para carregar cargas e até pessoas "
        "(inclusive, a polícia local faz patrulhamento montada em búfalos!).\n"
        "* **Na economia:** deles é extraído o leite para fazer o famoso e "
        "delicioso Queijo do Marajó, além da carne e do couro.\n"
        "* **No turismo:** são uma atração incrível que turistas do mundo "
        "todo vão lá ver de perto."
    )
    resultado = _limpar_texto_para_audio(entrada)
    assert "**" not in resultado
    assert "* " not in resultado
    assert "No transporte" in resultado
    assert "Na economia" in resultado


def test_nao_remove_asterisco_de_multiplicacao():
    resultado = _limpar_texto_para_audio("2 * 3 = 6, e 4 * 5 = 20.")
    assert "2 * 3 = 6" in resultado
    assert "4 * 5 = 20" in resultado


def test_nao_remove_underscore_de_nome_de_variavel():
    resultado = _limpar_texto_para_audio("nome_da_variavel não deve sumir.")
    assert "nome_da_variavel" in resultado


def test_nao_confunde_hashtag_com_header():
    resultado = _limpar_texto_para_audio("#Marajó é lindo.")
    assert "Marajó é lindo" in resultado


def test_negrito_truncado_nao_quebra():
    resultado = _limpar_texto_para_audio("Isso é **muito importante")
    assert "**" not in resultado
    assert "muito importante" in resultado


def test_texto_vazio():
    assert _limpar_texto_para_audio("") == ""


def test_tts_disponivel_false_sem_modelos(monkeypatch):
    monkeypatch.setattr(tts_service, "KOKORO_MODEL_PATH", "nao/existe.onnx")
    monkeypatch.setattr(tts_service, "KOKORO_VOICES_PATH", "nao/existe.bin")

    assert tts_service.tts_disponivel() is False


def test_sintetizar_fala_none_sem_modelo(monkeypatch):
    monkeypatch.setattr(tts_service, "_carregar_kokoro", lambda: None)

    assert tts_service.sintetizar_fala("olá") is None


def test_sintetizar_fala_retorna_none_com_texto_vazio(monkeypatch):
    monkeypatch.setattr(tts_service, "_carregar_kokoro", lambda: object())

    assert tts_service.sintetizar_fala("**") is None


def test_sintetizar_fala_gera_ogg(monkeypatch, tmp_path):
    chamadas = {}

    class FakeKokoro:
        def create(self, texto, voice, speed, lang):
            chamadas["texto"] = texto
            return [[0.0, 0.1]], 24000

    def fake_run(cmd, capture_output, check):
        chamadas["cmd"] = cmd
        with open(cmd[-1], "wb") as f:
            f.write(b"fake-ogg")

    monkeypatch.setattr(tts_service, "TEMP_DIR", str(tmp_path))
    monkeypatch.setattr(tts_service, "_carregar_kokoro", lambda: FakeKokoro())
    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(sf, "write", lambda *a, **k: None)

    caminho = tts_service.sintetizar_fala("Olá, vamos aprender!")

    assert caminho is not None
    assert caminho.startswith(str(tmp_path))
    assert caminho.endswith(".ogg")
    assert chamadas["cmd"][0] == "ffmpeg"
    assert "aprender" in chamadas["texto"]
    assert len(list(tmp_path.glob("*.ogg"))) == 1
    assert len(list(tmp_path.glob("*.wav"))) == 0


def test_limpar_artefatos_antigos_remove_apenas_antigos(monkeypatch, tmp_path):
    antigo = tmp_path / "antigo.ogg"
    recente = tmp_path / "recente.ogg"
    antigo.write_bytes(b"x")
    recente.write_bytes(b"x")

    import os

    hora_antiga = time.time() - 2 * 3600
    os.utime(antigo, (hora_antiga, hora_antiga))

    removidos = tts_service.limpar_artefatos_antigos(str(tmp_path), max_idade_horas=1)

    assert removidos == 1
    assert not antigo.exists()
    assert recente.exists()


def test_limpar_artefatos_antigos_ignora_pasta_ausente(tmp_path):
    assert tts_service.limpar_artefatos_antigos(str(tmp_path / "nao-existe"), max_idade_horas=1) == 0


def test_sintetizar_fala_limpa_artefatos_antigos(monkeypatch, tmp_path):
    chamadas = {}

    class FakeKokoro:
        def create(self, texto, voice, speed, lang):
            chamadas["texto"] = texto
            return [[0.0, 0.1]], 24000

    def fake_run(cmd, capture_output, check):
        with open(cmd[-1], "wb") as f:
            f.write(b"fake-ogg")

    monkeypatch.setattr(tts_service, "TEMP_DIR", str(tmp_path))
    monkeypatch.setattr(tts_service, "_carregar_kokoro", lambda: FakeKokoro())
    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(sf, "write", lambda *a, **k: None)
    monkeypatch.setattr(tts_service, "limpar_artefatos_antigos", lambda *a, **k: 1)

    caminho = tts_service.sintetizar_fala("Olá")

    assert caminho is not None

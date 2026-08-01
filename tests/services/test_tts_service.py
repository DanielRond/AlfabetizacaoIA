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

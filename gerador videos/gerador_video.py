# ===========================================================
# CORREÇÃO DE COMPATIBILIDADE PILLOW (ANTIALIAS)
# ===========================================================

import PIL.Image

if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

# ===========================================================
# IMPORTAÇÕES
# ===========================================================

import os
import random
import json
import copy
from moviepy.editor import (
    VideoFileClip,
    concatenate_videoclips
)

# ===========================================================
# CONFIGURAÇÕES
# ===========================================================

DIRETORIO_SCRIPT = os.path.dirname(os.path.abspath(__file__))

# Caminhos relativos baseados na pasta do script
PASTA_ORIGEM = os.path.join(DIRETORIO_SCRIPT, "Videos sem legenda")
PASTA_DESTINO = os.path.join(DIRETORIO_SCRIPT, "Videos Gerados")
ARQUIVO_HISTORICO = os.path.join(DIRETORIO_SCRIPT, "historico_videos.json")

QTD_VIDEOS = 10
IGNORAR_INICIO = 11                  # segundos
DURACAO_TOTAL_DESEJADA = 300        # segundos

EXTENSOES = {'.mp4', '.mov', '.avi', '.mkv'}

# ===========================================================
# FUNÇÕES DE HISTÓRICO
# ===========================================================

def carregar_historico():
    if os.path.exists(ARQUIVO_HISTORICO):
        try:
            with open(ARQUIVO_HISTORICO, 'r', encoding='utf-8') as f:
                dados = json.load(f)
                # Migração: se for lista (formato antigo), converte para dicionário
                if isinstance(dados, list):
                    return {v: [IGNORAR_INICIO] for v in dados}
                return dados
        except Exception:
            return {}
    return {}


def salvar_historico(dados):
    with open(ARQUIVO_HISTORICO, 'w', encoding='utf-8') as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)

# ===========================================================
# FUNÇÃO PRINCIPAL
# ===========================================================

def processar():
    print("=== GERADOR AUTOMÁTICO DE VÍDEO ===\n")

    # -------------------------------------------------------
    # Verificações iniciais
    # -------------------------------------------------------

    if not os.path.exists(PASTA_ORIGEM):
        print(f"ERRO: Pasta de origem não existe:\n{PASTA_ORIGEM}")
        return

    if not os.path.exists(PASTA_DESTINO):
        os.makedirs(PASTA_DESTINO)

    # -------------------------------------------------------
    # Listar vídeos válidos
    # -------------------------------------------------------

    todos_videos = [
        f for f in os.listdir(PASTA_ORIGEM)
        if os.path.splitext(f)[1].lower() in EXTENSOES
    ]

    print(f"Vídeos encontrados: {len(todos_videos)}")

    if not todos_videos:
        print(f"ERRO: Nenhum vídeo encontrado.")
        return

    # -------------------------------------------------------
    # Preparação para seleção
    # -------------------------------------------------------

    historico = carregar_historico()
    
    # Embaralha os arquivos para garantir variedade
    candidatos = todos_videos.copy()
    random.shuffle(candidatos)

    clips_processados = []
    clips_abertos = [] # Para fechar corretamente depois

    tempo_por_clip = DURACAO_TOTAL_DESEJADA / QTD_VIDEOS
    
    print(f"\nCada trecho terá {tempo_por_clip:.2f} segundos.")
    print(f"Buscando trechos não utilizados anteriormente...\n")

    # Histórico temporário desta execução para evitar repetir o mesmo trecho no mesmo vídeo final
    historico_temp = copy.deepcopy(historico)

    while len(clips_processados) < QTD_VIDEOS:
        # Se acabaram os candidatos, significa que todos os trechos de todos os vídeos foram usados
        if not candidatos:
            print("\n>>> TODOS OS INTERVALOS FORAM USADOS! REINICIANDO HISTÓRICO. <<<\n")
            historico = {}
            historico_temp = {}
            candidatos = todos_videos.copy()
            random.shuffle(candidatos)

        nome_arq = candidatos.pop(0)
        caminho = os.path.join(PASTA_ORIGEM, nome_arq)

        try:
            clip = VideoFileClip(caminho)
            duracao = clip.duration

            # Calcula quantos "slots" de tempo cabem neste vídeo
            qtd_slots = int((duracao - IGNORAR_INICIO) / tempo_por_clip)
            
            if qtd_slots < 1:
                clip.close()
                continue

            # Gera lista de tempos de início possíveis: [11, 46, 81, ...]
            possiveis_inicios = [IGNORAR_INICIO + i * tempo_por_clip for i in range(qtd_slots)]
            
            # Filtra os que já foram usados
            usados = historico_temp.get(nome_arq, [])
            disponiveis = [t for t in possiveis_inicios if not any(abs(u - t) < 0.5 for u in usados)]

            if not disponiveis:
                # Todos os trechos desse vídeo já foram usados
                clip.close()
                continue

            # Escolhe um trecho disponível aleatoriamente
            inicio_escolhido = random.choice(disponiveis)
            
            trecho = clip.subclip(inicio_escolhido, inicio_escolhido + tempo_por_clip)
            trecho = trecho.resize(height=1080)
            trecho = trecho.set_position("center")

            clips_processados.append(trecho)
            clips_abertos.append(clip) # Mantém aberto até o final

            # Atualiza históricos
            if nome_arq not in historico: historico[nome_arq] = []
            if nome_arq not in historico_temp: historico_temp[nome_arq] = []
            
            historico[nome_arq].append(inicio_escolhido)
            historico_temp[nome_arq].append(inicio_escolhido)

            print(f"Adicionado: {nome_arq} (Início: {inicio_escolhido:.1f}s)")

            # Se ainda houver trechos disponíveis neste vídeo, coloca ele de volta no fim da fila
            if len(disponiveis) > 1:
                candidatos.append(nome_arq)

        except Exception as e:
            print(f"ERRO ao processar {nome_arq}: {e}")

    # -------------------------------------------------------
    # Finalização
    # -------------------------------------------------------

    if not clips_processados:
        print("\nNenhum clip pôde ser processado.")
        return

    print(f"\nUnindo {len(clips_processados)} clips...")

    video_final = concatenate_videoclips(
        clips_processados,
        method="compose"
    )

    caminho_final = os.path.join(
        PASTA_DESTINO,
        "video_final_automatico.mp4"
    )

    video_final.write_videofile(
        caminho_final,
        codec='libx264',
        audio_codec='aac',
        threads=4,
        preset='ultrafast'
    )

    # -------------------------------------------------------
    # Atualizar histórico e Limpeza
    # -------------------------------------------------------

    salvar_historico(historico)
    
    # Fecha os arquivos originais
    for clip in clips_abertos:
        clip.close()

    print("\n--- SUCESSO ---")
    print(f"Vídeo salvo em:\n{caminho_final}")
    print(f"Histórico atualizado.")

# ===========================================================
# EXECUÇÃO
# ===========================================================

if __name__ == "__main__":
    processar()

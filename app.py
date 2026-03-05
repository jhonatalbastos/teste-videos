import streamlit as st
import requests
import os
import subprocess
import time
from gtts import gTTS
from datetime import datetime

# ==========================================
# CONFIGURAÇÃO DE SEGURANÇA E LIMITES
# ==========================================
# Sua chave fornecida
FREEPIK_KEY = st.secrets.get("freepik_key", "FPSX615797bc0e15251d88165d9d5ecb3244")

# Limites do Plano Free Access do Freepik
LIMITE_DIARIO = 75
LIMITE_MINUTO = 5

# Inicializa contadores na sessão do navegador (Streamlit Session State)
if 'contagem_dia' not in st.session_state:
    st.session_state.contagem_dia = 0
if 'historico_minuto' not in st.session_state:
    st.session_state.historico_minuto = []

def registrar_uso():
    """Registra e limpa o histórico de uso para respeitar os limites."""
    agora = time.time()
    st.session_state.contagem_dia += 1
    st.session_state.historico_minuto.append(agora)
    
    # Remove registros com mais de 60 segundos
    st.session_state.historico_minuto = [t for t in st.session_state.historico_minuto if agora - t < 60]

def verificar_limites():
    """Verifica se o usuário ainda tem cota disponível."""
    agora = time.time()
    st.session_state.historico_minuto = [t for t in st.session_state.historico_minuto if agora - t < 60]
    
    if st.session_state.contagem_dia >= LIMITE_DIARIO:
        return False, "Você atingiu o limite de 75 imagens diárias do Freepik."
    
    if len(st.session_state.historico_minuto) >= LIMITE_MINUTO:
        return False, "Limite de 5 imagens por minuto atingido. Aguarde alguns segundos."
    
    return True, ""

# ==========================================
# GERAÇÃO DE IMAGEM (FREEPIK)
# ==========================================
def gerar_imagem_freepik(prompt, id_job):
    pode_gerar, msg = verificar_limites()
    if not pode_gerar:
        return f"Erro: {msg}"

    url = "https://api.freepik.com/v1/ai/text-to-image"
    payload = {
        "prompt": prompt,
        "styling": {"style": "photorealistic", "mode": "cinematic"},
        "size": "portrait" # 9:16 para Shorts/Reels
    }
    headers = {
        "Content-Type": "application/json",
        "x-freepik-api-key": FREEPIK_KEY
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            registrar_uso()
            data = response.json()
            img_url = data['data'][0]['url']
            img_res = requests.get(img_url)
            path = f"img_{id_job}.jpg"
            with open(path, "wb") as f:
                f.write(img_res.content)
            return path
        elif response.status_code == 429:
            return "Erro: Limite de cota excedido na API (429)."
        else:
            return f"Erro Freepik: {response.text}"
    except Exception as e:
        return f"Erro de Conexão: {str(e)}"

# ==========================================
# GERAÇÃO DE ÁUDIO (gTTS)
# ==========================================
def gerar_audio(texto, id_job):
    try:
        path = f"audio_{id_job}.mp3"
        tts = gTTS(text=texto, lang='pt', tld='com.br')
        tts.save(path)
        return path
    except Exception as e:
        return f"Erro Áudio: {str(e)}"

# ==========================================
# MONTAGEM DE VÍDEO (FFMPEG)
# ==========================================
def montar_video(img_path, audio_path, out_path):
    try:
        comando = [
            'ffmpeg', '-y', '-loop', '1', '-i', img_path,
            '-i', audio_path, '-c:v', 'libx264', '-tune', 'stillimage',
            '-c:a', 'aac', '-b:a', '192k', '-pix_fmt', 'yuv420p',
            '-shortest', out_path
        ]
        subprocess.run(comando, capture_output=True, check=True)
        return out_path
    except Exception as e:
        return f"Erro FFmpeg: {str(e)}"

# ==========================================
# INTERFACE STREAMLIT
# ==========================================
st.set_page_config(page_title="Evangelho Creator", page_icon="🙏")
st.title("📖 Produtor de Vídeos Bíblicos")

# Painel de Controle de Cota na Sidebar
with st.sidebar:
    st.header("📊 Uso da API (Free Access)")
    st.write(f"Imagens hoje: {st.session_state.contagem_dia} / {LIMITE_DIARIO}")
    st.progress(st.session_state.contagem_dia / LIMITE_DIARIO)
    st.write(f"No último minuto: {len(st.session_state.historico_minuto)} / {LIMITE_MINUTO}")
    if st.button("Resetar Contador Local"):
        st.session_state.contagem_dia = 0

with st.form("main_form"):
    st.info("Dica: Use prompts em inglês para melhores resultados no Freepik.")
    prompt = st.text_input("Cena da Imagem (Ex: Jesus preaching on the mountain, 8k, cinematic)")
    texto = st.text_area("Texto/Versículo para Narração")
    botao = st.form_submit_button("Gerar Vídeo Completo")

if botao:
    if not prompt or not texto:
        st.error("Preencha todos os campos.")
    else:
        with st.spinner("⏳ Gerando mídia e respeitando limites da API..."):
            res_img = gerar_imagem_freepik(prompt, "v1")
            res_aud = gerar_audio(texto, "v1")
            
            if "Erro" not in res_img and "Erro" not in res_aud:
                video_file = "video_biblico_final.mp4"
                resultado = montar_video(res_img, res_aud, video_file)
                
                if "Erro" not in resultado:
                    st.success("Glória a Deus! Vídeo gerado.")
                    st.video(video_file)
                    with open(video_file, "rb") as f:
                        st.download_button("📥 Baixar Vídeo", f, "evangelho_video.mp4")
                else:
                    st.error(resultado)
            else:
                st.error(f"{res_img} | {res_aud}")

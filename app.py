import streamlit as st
import os
import subprocess
import requests
from gtts import gTTS
import random

# ==========================================
# FUNÇÃO PARA IMAGEM GRATUITA (UNSPLASH)
# ==========================================
def buscar_imagem_gratis(query, id_job):
    """
    Busca uma imagem gratuita no Unsplash baseada no tema.
    Isso economiza sua cota de IA para o que realmente importa.
    """
    try:
        # Usamos a URL de source do Unsplash (Grátis e sem Key para uso simples)
        url = f"https://source.unsplash.com/featured/1080x1920/?bible,{query.replace(' ', ',')}"
        response = requests.get(url, timeout=15)
        
        path = f"img_{id_job}.jpg"
        if response.status_code == 200:
            with open(path, "wb") as f:
                f.write(response.content)
            return path
        return None
    except Exception as e:
        return f"Erro Imagem: {str(e)}"

# ==========================================
# FUNÇÃO PARA ÁUDIO (gTTS - ILIMITADO)
# ==========================================
def gerar_audio_ilimitado(texto, id_job):
    """
    Usa o Google TTS padrão (grátis e sem cota de API) 
    para gerar a narração em português.
    """
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
            'ffmpeg', '-y', 
            '-loop', '1', '-i', img_path,
            '-i', audio_path,
            '-c:v', 'libx264', '-tune', 'stillimage',
            '-c:a', 'aac', '-b:a', '192k',
            '-pix_fmt', 'yuv420p',
            '-shortest', out_path
        ]
        subprocess.run(comando, capture_output=True, check=True)
        return out_path
    except Exception as e:
        return f"Erro FFmpeg: {str(e)}"

# ==========================================
# INTERFACE STREAMLIT
# ==========================================
st.set_page_config(page_title="Evangelho Video Maker", page_icon="🙏")
st.title("🎥 Criador de Vídeos (Versão Estável)")
st.markdown("Esta versão não consome sua cota de IA para imagens e áudio.")

with st.form("gerador_estavel"):
    tema_imagem = st.text_input("Tema da Imagem (Ex: Cross, Jesus, Church, Desert)")
    versiculo = st.text_area("Texto para Narração")
    botao = st.form_submit_button("Gerar Vídeo Agora")

if botao:
    if not tema_imagem or not versiculo:
        st.error("Preencha os campos!")
    else:
        with st.spinner("⏳ Criando vídeo..."):
            # 1. Busca imagem em banco gratuito
            path_img = buscar_imagem_gratis(tema_imagem, "estavel")
            
            # 2. Gera áudio via gTTS (Sem erro de 429 ou 400)
            path_aud = gerar_audio_ilimitado(versiculo, "estavel")
            
            if path_img and "Erro" not in path_aud:
                video_final = "video_estavel.mp4"
                resultado = montar_video(path_img, path_aud, video_final)
                
                if "Erro" not in resultado:
                    st.success("Vídeo produzido com sucesso!")
                    st.video(video_final)
                    with open(video_final, "rb") as f:
                        st.download_button("📥 Baixar Vídeo", f, "video_biblico.mp4")
                else:
                    st.error(resultado)
            else:
                st.error("Falha ao obter recursos básicos.")

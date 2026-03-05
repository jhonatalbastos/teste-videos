import streamlit as st
import requests
import os
import subprocess
import time
from gtts import gTTS

# ==========================================
# CONFIGURAÇÃO DE CHAVE
# ==========================================
FREEPIK_KEY = st.secrets.get("freepik_key", "FPSX615797bc0e15251d88165d9d5ecb3244")

# ==========================================
# GERAÇÃO DE IMAGEM (FREEPIK)
# ==========================================
def gerar_imagem_freepik(prompt, id_job):
    url = "https://api.freepik.com/v1/ai/text-to-image"
    payload = {
        "prompt": prompt,
        "styling": {"style": "photorealistic", "mode": "cinematic"},
        "size": "portrait"
    }
    headers = {
        "Content-Type": "application/json",
        "x-freepik-api-key": FREEPIK_KEY
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        if response.status_code == 200:
            data = response.json()
            img_url = data['data'][0]['url']
            img_res = requests.get(img_url, timeout=20)
            path = f"img_{id_job}.jpg"
            with open(path, "wb") as f:
                f.write(img_res.content)
            return path
        else:
            # Retorna o erro exato da API para sabermos o que houve
            return f"Erro Freepik ({response.status_code}): {response.text}"
    except Exception as e:
        return f"Erro de Conexão Imagem: {str(e)}"

# ==========================================
# GERAÇÃO DE ÁUDIO (gTTS)
# ==========================================
def gerar_audio(texto, id_job):
    try:
        path = f"audio_{id_job}.mp3"
        # Tenta gerar o áudio em português
        tts = gTTS(text=texto, lang='pt', tld='com.br')
        tts.save(path)
        if os.path.exists(path):
            return path
        return "Erro: Arquivo de áudio não foi criado."
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
        # Captura saída para debug
        processo = subprocess.run(comando, capture_output=True, text=True)
        if processo.returncode != 0:
            return f"Erro FFmpeg: {processo.stderr}"
        return out_path
    except Exception as e:
        return f"Erro Processamento Vídeo: {str(e)}"

# ==========================================
# INTERFACE
# ==========================================
st.set_page_config(page_title="Evangelho Video Maker", layout="centered")
st.title("🙏 Criador de Vídeos (Versão Estável)")

with st.form("meu_form"):
    tema = st.text_input("Tema da Imagem (Em Inglês costuma ser melhor para a IA)", "A person praying in a modern room, cinematic lighting")
    texto = st.text_area("Texto para Narração", height=150)
    botao = st.form_submit_button("Gerar Vídeo Agora")

if botao:
    if not tema or not texto:
        st.warning("Preencha todos os campos!")
    else:
        with st.spinner("⏳ Criando mídia..."):
            # 1. Tenta Imagem
            res_img = gerar_imagem_freepik(tema, "v1")
            
            # 2. Tenta Áudio
            res_aud = gerar_audio(texto, "v1")
            
            # Verificação de Sucesso
            if os.path.exists(str(res_img)) and os.path.exists(str(res_aud)):
                video_out = "video_final.mp4"
                res_video = montar_video(res_img, res_aud, video_out)
                
                if os.path.exists(video_out) and "Erro" not in res_video:
                    st.success("Vídeo gerado!")
                    st.video(video_out)
                    with open(video_out, "rb") as f:
                        st.download_button("📥 Baixar Vídeo", f, "video_biblico.mp4")
                else:
                    st.error(f"Erro na montagem: {res_video}")
            else:
                # Mostra o erro específico que aconteceu
                st.error(f"Falha na obtenção dos recursos:\n\nIMAGEM: {res_img}\n\nÁUDIO: {res_aud}")

# Limpeza opcional: Se quiser deletar arquivos antigos ao recarregar
if st.button("Limpar arquivos temporários"):
    for f in os.listdir():
        if f.endswith(".jpg") or f.endswith(".mp3") or f.endswith(".mp4"):
            try: os.remove(f)
            except: pass
    st.rerun()

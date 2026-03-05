import streamlit as st
import google.generativeai as genai
import os
import subprocess
import time

# ==========================================
# CONFIGURAÇÃO DE SEGURANÇA (SECRETS)
# ==========================================
try:
    MINHAS_API_KEYS = st.secrets["api_keys"]
except Exception:
    st.error("Erro: Adicione 'api_keys' nos Secrets do Streamlit.")
    MINHAS_API_KEYS = []

class GerenciadorDeCota:
    def __init__(self, keys):
        self.keys = keys
        self.index = 0
    def obter_proxima_chave(self):
        if not self.keys: return None
        key = self.keys[self.index]
        self.index = (self.index + 1) % len(self.keys)
        return key

gerenciador = GerenciadorDeCota(MINHAS_API_KEYS)

# ==========================================
# GERAÇÃO DE IMAGEM (ROBUSTA)
# ==========================================
def gerar_imagem(prompt, id_job):
    # Tenta em todas as chaves disponíveis
    for _ in range(len(MINHAS_API_KEYS)):
        chave = gerenciador.obter_proxima_chave()
        genai.configure(api_key=chave)
        
        # Tentamos primeiro o modelo dedicado de imagem
        # Se falhar, o loop tentará a próxima chave automaticamente
        try:
            model = genai.GenerativeModel('gemini-2.5-flash-image')
            response = model.generate_content(prompt)
            
            path = f"img_{id_job}.png"
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'inline_data'):
                    with open(path, "wb") as f:
                        f.write(part.inline_data.data)
                    return path
        except Exception as e:
            if "429" in str(e):
                st.warning(f"Chave terminada em ...{chave[-4:]} atingiu limite de imagem. Tentando próxima...")
                continue 
            return f"Erro Imagem: {str(e)}"
            
    return "Erro: Todas as 5 chaves atingiram o limite de imagens hoje."

# ==========================================
# GERAÇÃO DE ÁUDIO (CORREÇÃO DE MODALIDADE)
# ==========================================
def gerar_audio(texto, id_job):
    for _ in range(len(MINHAS_API_KEYS)):
        chave = gerenciador.obter_proxima_chave()
        genai.configure(api_key=chave)
        
        try:
            # CORREÇÃO: Para o modelo TTS, precisamos definir a configuração de geração
            # para aceitar a modalidade AUDIO explicitamente.
            model = genai.GenerativeModel('gemini-2.5-flash-preview-tts')
            
            # Chamada de geração configurada para saída de áudio
            response = model.generate_content(
                texto,
                generation_config={"response_mime_type": "audio/mp3"}
            )
            
            path = f"audio_{id_job}.mp3"
            
            # Captura os bytes binários da resposta
            # Nos modelos nativos de 2026, o áudio vem no primeiro part
            audio_data = response.candidates[0].content.parts[0].inline_data.data
            
            with open(path, "wb") as f:
                f.write(audio_data)
            return path
            
        except Exception as e:
            if "429" in str(e):
                st.warning(f"Chave terminada em ...{chave[-4:]} atingiu limite de áudio. Tentando próxima...")
                continue
            # Se for erro de modalidade 400, tentamos um ajuste no formato da chamada
            return f"Erro Áudio: {str(e)}"
            
    return "Erro: Todas as chaves atingiram o limite de áudio."

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
        # Redireciona logs para não poluir o Streamlit
        subprocess.run(comando, capture_output=True, check=True)
        return out_path
    except Exception as e:
        return f"Erro FFmpeg: {str(e)}"

# ==========================================
# INTERFACE
# ==========================================
st.set_page_config(page_title="Evangelho AI Pro", page_icon="🙏")
st.title("🎥 Criador de Conteúdo Cristão")
st.info("Este app rotaciona 5 chaves API para maximizar seu uso gratuito.")

with st.form("meu_gerador"):
    prompt = st.text_input("Cena da Imagem (Ex: Moises abrindo o Mar Vermelho, cinematico)")
    versiculo = st.text_area("Texto para Narração")
    botao = st.form_submit_button("Gerar Vídeo Completo")

if botao:
    if not prompt or not versiculo:
        st.error("Preencha os campos!")
    else:
        with st.spinner("⏳ Gerando mídia (isso pode levar 30s)..."):
            # 1. Gera Imagem
            path_img = gerar_imagem(prompt, "job")
            
            # 2. Gera Áudio
            path_aud = gerar_audio(versiculo, "job")
            
            if "Erro" not in path_img and "Erro" not in path_aud:
                video_final = "video_evangelho.mp4"
                resultado = montar_video(path_img, path_aud, video_final)
                
                if "Erro" not in resultado:
                    st.success("Glória a Deus! Vídeo pronto.")
                    st.video(video_final)
                    with open(video_final, "rb") as f:
                        st.download_button("📥 Baixar Vídeo", f, "video_biblico.mp4")
                else:
                    st.error(resultado)
            else:
                st.error(f"Erro na Produção:\n\nIMAGEM: {path_img}\n\nÁUDIO: {path_aud}")

import streamlit as st
import google.generativeai as genai
import os
import subprocess
import concurrent.futures

# ==========================================
# CONFIGURAÇÃO DE SEGURANÇA (SECRETS)
# ==========================================
try:
    MINHAS_API_KEYS = st.secrets["api_keys"]
except Exception:
    st.error("Erro: Chaves API não encontradas nos Secrets do Streamlit.")
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
# FUNÇÕES DE GERAÇÃO (IA)
# ==========================================

def gerar_imagem(prompt, id_job):
    try:
        genai.configure(api_key=gerenciador.obter_proxima_chave())
        model = genai.GenerativeModel('gemini-2.5-flash-image')
        response = model.generate_content(prompt)
        
        path = f"img_{id_job}.png"
        for chunk in response.candidates[0].content.parts:
            if hasattr(chunk, 'inline_data'):
                with open(path, "wb") as f:
                    f.write(chunk.inline_data.data)
                return path
        return None
    except Exception as e:
        return f"Erro Imagem: {str(e)}"

def gerar_audio(texto, id_job):
    try:
        genai.configure(api_key=gerenciador.obter_proxima_chave())
        model = genai.GenerativeModel('gemini-2.5-flash-preview-tts')
        response = model.generate_content(texto)
        
        path = f"audio_{id_job}.mp3"
        with open(path, "wb") as f:
            f.write(response.data)
        return path
    except Exception as e:
        return f"Erro Áudio: {str(e)}"

# ==========================================
# FUNÇÃO DE MONTAGEM DE VÍDEO (FFMPEG DIRETO)
# ==========================================

def montar_video_ffmpeg(img_path, audio_path, out_path):
    """
    Usa o FFmpeg via linha de comando para criar o vídeo.
    É muito mais estável que o MoviePy para o Streamlit.
    """
    try:
        # Comando FFmpeg:
        # -loop 1: Repete a imagem
        # -i: Entrada (imagem e áudio)
        # -c:v libx264: Codec de vídeo padrão
        # -tune stillimage: Otimiza para imagens estáticas
        # -c:a aac: Codec de áudio
        # -shortest: Termina o vídeo quando o áudio acabar
        # -pix_fmt yuv420p: Garante compatibilidade com players
        comando = [
            'ffmpeg', '-y', 
            '-loop', '1', '-i', img_path,
            '-i', audio_path,
            '-c:v', 'libx264', '-tune', 'stillimage',
            '-c:a', 'aac', '-b:a', '192k',
            '-pix_fmt', 'yuv420p',
            '-shortest', out_path
        ]
        
        # Executa o comando e captura erros
        resultado = subprocess.run(comando, capture_output=True, text=True)
        
        if resultado.returncode != 0:
            return f"Erro FFmpeg: {resultado.stderr}"
        
        return out_path
    except Exception as e:
        return f"Erro ao processar vídeo: {str(e)}"

# ==========================================
# INTERFACE STREAMLIT
# ==========================================
st.set_page_config(page_title="Evangelho Video Maker", layout="centered")
st.title("🙏 Criador de Vídeos para o Evangelho")
st.markdown("Gere imagens e narrações bíblicas em segundos.")

prompt_img = st.text_input("Descreva a cena (Ex: Jesus no monte das oliveiras, pôr do sol)")
texto_audio = st.text_area("Texto para a narração (Versículo)")

if st.button("🎬 Gerar e Montar Vídeo"):
    if prompt_img and texto_audio:
        with st.spinner("⏳ Criando arte, voz e montando vídeo..."):
            
            # 1. Gera recursos em paralelo
            with concurrent.futures.ThreadPoolExecutor() as executor:
                f_img = executor.submit(gerar_imagem, prompt_img, "final")
                f_aud = executor.submit(gerar_audio, texto_audio, "final")
                
                res_img = f_img.result()
                res_aud = f_aud.result()

            if "Erro" not in res_img and "Erro" not in res_aud:
                # 2. Monta o vídeo final
                video_final = "resultado_evangelho.mp4"
                sucesso_video = montar_video_ffmpeg(res_img, res_aud, video_final)
                
                if "Erro" not in sucesso_video:
                    st.success("Vídeo concluído!")
                    st.video(video_final)
                    
                    with open(video_final, "rb") as f:
                        st.download_button("📥 Baixar Vídeo para o Canal", f, "video_evangelho.mp4")
                    
                    # Limpeza de arquivos temporários
                    os.remove(res_img)
                    os.remove(res_aud)
                else:
                    st.error(sucesso_video)
            else:
                st.error(f"Falha na geração: {res_img} / {res_aud}")
    else:
        st.warning("Por favor, preencha os campos de imagem e texto.")

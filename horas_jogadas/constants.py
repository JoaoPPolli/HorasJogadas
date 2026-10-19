"""Constantes globais do aplicativo."""
import os

APP_NAME = "HorasJogadas"
DATA_DIR = os.path.join(os.getenv("APPDATA") or os.path.expanduser("~"), APP_NAME)

NOME_ARQ_REGISTROS = "registros.json"
NOME_ARQ_CRONOMETROS = "cronometros.json"
NOME_ARQ_CONFIG = "config.json"
NOME_ARQ_ANDAMENTO = "em_andamento.json"
NOME_ARQ_LOG = "app.log"

FORMATO_DATA = "%Y-%m-%d %H:%M:%S"

# --- Status dos jogos ---
STATUS_PADRAO = "Jogando"
STATUS_OPCOES = {
    "Jogando": {"cor_bg": "#1a2a44", "cor_fg": "#82b1ff"},
    "Zerado": {"cor_bg": "#1b3320", "cor_fg": "#81c784"},
    "Backlog": {"cor_bg": "#332b1b", "cor_fg": "#ffd54f"},
    "Dropado": {"cor_bg": "#331b1b", "cor_fg": "#e57373"},
}
FILTROS_STATUS = ["TODOS", "JOGANDO", "ZERADO", "BACKLOG", "DROPADO"]

# --- Ordenação da home ---
ORDENACAO_PADRAO = "manual"
ORDENACOES = ("manual", "nome", "horas", "recente")   # rótulos em i18n: "ord.<chave>"

# --- Idioma da interface ---
IDIOMA_PADRAO = "pt"
IDIOMAS_DISPONIVEIS = {"pt": "Português (Brasil)", "en": "English"}   # sempre no próprio idioma

# --- Configuração padrão ---
CONFIG_PADRAO = {"modo_navegacao": "janelas", "ordenacao": ORDENACAO_PADRAO, "idioma": IDIOMA_PADRAO}

# --- Interface ---
CARD_LARGURA = 320
CARD_PADDING_X = 16
MAX_COLUNAS = 6
INTERVALO_UPDATE_MS = 200
INTERVALO_HEARTBEAT_S = 30
TAMANHO_PAGINA_HISTORICO = 200

# --- Pausa (card) ---
PAUSA_ATALHOS_MIN = (5, 10, 15, 30)       # atalhos "+N min" do diálogo de tempo
PAUSA_PADRAO_PARCIAL_MIN = 15             # sugestão do "só os últimos N min" ao contar a pausa

# --- Backups de dados e instância única ---
PASTA_BACKUPS_DADOS = "backups"           # dentro de DATA_DIR: diario/, antes_de_apagar/, manual/, antes_de_restaurar/
MAX_BACKUPS_DIARIOS = 7
MAX_BACKUPS_EXTRAS = 10                   # antes_de_apagar e manual
MAX_BACKUPS_RESTAURAR = 5
INTERVALO_BACKUP_S = 300                  # de quanto em quanto tempo verifica se virou o dia
NOME_ARQ_TRAVA = "app.lock"
NOME_ARQ_SINAL = "mostrar.sinal"
INTERVALO_SINAL_LOOPS = 5                 # checa o sinal "traga a janela para frente" a cada N ciclos (~1 s)

# --- Atualizações ---
PASTA_BACKUPS = "_versoes_anteriores"     # dentro da pasta do app
MAX_BACKUPS = 3
ARQUIVOS_DE_APOIO = ("app.py", "README.md", "build_exe.bat", "Iniciar.bat",      # atualizados junto com o código
                     "build_itch.bat", "empacotar_release.py", "LEIAME_release.txt")
MARCADOR_EMPACOTADO = "empacotado.flag"   # embutido no .exe de distribuição (itch.io): código vai dentro do exe
MARCADOR_NAO_VALIDADA = ".nova_versao_nao_validada"

# --- Cores ---
COR_BG = "#1f1f23"
COR_CARD = "#2b2b2f"
COR_BTN = "#3a3a40"
COR_ACCENT = "#5c5cff"
COR_TEXTO = "#e6e6e6"
COR_TEXTO_SUAVE = "#bfbfbf"
COR_BORDA = "#2f2f35"
COR_PERIGO = "#d9534f"
COR_PAUSA = "#ffd54f"

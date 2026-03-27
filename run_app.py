import os
import sys
import multiprocessing
import streamlit.web.cli as stcli

if __name__ == "__main__":
    # CRÍTICO PARA WINDOWS: Evita o loop infinito de processos no executável
    multiprocessing.freeze_support()
    
    if getattr(sys, 'frozen', False):
        diretorio = sys._MEIPASS
    else:
        diretorio = os.path.dirname(os.path.abspath(__file__))
        
    app_path = os.path.join(diretorio, 'app.py')
    
    # Desativa a telemetria do Streamlit
    os.environ["STREAMLIT_GATHER_USAGE_STATS"] = "false"
    
    sys.argv = [
        "streamlit", 
        "run", 
        app_path, 
        "--global.developmentMode=false",
        "--server.headless=false",
        "--server.fileWatcherType=none",
        "--browser.gatherUsageStats=false"
    ]
    
    sys.exit(stcli.main())
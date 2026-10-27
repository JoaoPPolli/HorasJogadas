"""Metade congelada do teste de atualização; o runner fornece dados fictícios."""
import json
import os
import sys
from pathlib import Path
from .release import VERSION


def run_update_self_test(result_path,archive):
    result={'version':VERSION,'ok':False}
    try:
        if not sys.platform.startswith('linux') or not getattr(sys,'frozen',False):
            raise RuntimeError('Este teste requer o executável Linux empacotado')
        from .updates import stage_linux,launch_update
        result['frozen_environment_detected']=str(sys._MEIPASS) in os.environ.get('LD_LIBRARY_PATH','')
        if not result['frozen_environment_detected']:raise RuntimeError('Teste sem ambiente real do PyInstaller')
        staged=stage_linux(archive,Path(sys.executable).parent,VERSION)
        helper=launch_update(archive,staged)
        result.update(ok=True,helper_pid=helper.pid)
    except Exception as error:
        result['error']=str(error)
    Path(result_path).write_text(json.dumps(result,indent=2),encoding='utf-8')
    return 0 if result['ok'] else 1

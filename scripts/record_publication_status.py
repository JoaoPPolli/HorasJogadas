"""Registra evidência não secreta da publicação para acompanhamento via Git."""
import json
import os
from pathlib import Path

status={
    'phase':'release', 'version':os.environ.get('RELEASE_VERSION','3.0.0'),
    'run_url':os.environ['RUN_URL'], 'commit':os.environ['SOURCE_COMMIT'],
    'build':os.environ.get('BUILD_RESULT'), 'publish':os.environ.get('PUBLISH_RESULT'),
    'pages':os.environ.get('PAGES_RESULT'),
    'release_url':os.environ.get('RELEASE_URL',''), 'site_url':os.environ.get('SITE_URL',''),
}
root=Path(os.environ.get('DIAGNOSTICS_DIR','build-diagnostics'))
status['diagnostics']={}
if root.exists():
    for file in root.rglob('*.json'):
        try: status['diagnostics'][file.stem]=json.loads(file.read_text(encoding='utf-8'))
        except (ValueError,OSError): pass
Path(os.environ.get('STATUS_FILE','status.json')).write_text(json.dumps(status,indent=2)+'\n',encoding='utf-8')

"""Gera o site estático com URLs de release explícitas, sem API nem rastreamento no navegador."""
import argparse
import html
import json
import re
import shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
import sys
sys.path.insert(0,str(ROOT))
from horas_jogadas_qt.release import VERSION


def inline(text):
    escaped=html.escape(text)
    escaped=re.sub(r'`([^`]+)`',r'<code>\1</code>',escaped)
    return re.sub(r'\*\*([^*]+)\*\*',r'<strong>\1</strong>',escaped)


def changelog(repository):
    source=(ROOT/'CHANGELOG.md').read_text(encoding='utf-8')
    catalog=json.loads((ROOT/'site'/'changelog'/'releases.json').read_text(encoding='utf-8'))
    sections=re.split(r'^## (\d+\.\d+\.\d+)\s*$',source,flags=re.M)
    navigation=[];entries=[]
    for version,body in zip(sections[1::2],sections[2::2]):
        anchor='v'+version.replace('.','-');metadata=catalog.get(version,{})
        title=metadata.get('title','Novidades e melhorias')
        latest=version==VERSION
        navigation.append('<a href="#'+anchor+'">'+version+'</a>')
        blocks=[];bullets=[];paragraph=[]
        def flush():
            if bullets:blocks.append('<ul>'+''.join('<li>'+inline(item)+'</li>' for item in bullets)+'</ul>');bullets.clear()
            if paragraph:blocks.append('<p>'+inline(' '.join(paragraph))+'</p>');paragraph.clear()
        for line in body.splitlines():
            if line.startswith('- '):
                if paragraph:flush()
                bullets.append(line[2:])
            elif not line.strip():flush()
            else:
                if bullets:flush()
                paragraph.append(line.strip())
        flush()
        url='https://github.com/'+repository
        if metadata.get('download'):
            link='<a class="release-link" href="'+url+'/releases/tag/v'+version+'">Downloads e detalhes desta versão <span aria-hidden="true">↗</span></a>'
        else:
            link='<a class="release-link" href="'+url+'/blob/main/CHANGELOG.md#'+version.replace('.','')+'">Notas no código-fonte <span aria-hidden="true">↗</span></a>'
        entries.append('<article class="release-card'+(' latest' if latest else '')+'" id="'+anchor+'" data-version="'+version+'">'
            +'<div class="release-heading"><span class="release-version">v'+version+'</span>'
            +('<span class="latest-badge">Versão atual</span>' if latest else '')+'</div><h2>'+html.escape(title)+'</h2>'
            +''.join(blocks)+link+'</article>')
    return ''.join(navigation),''.join(entries),str(len(entries))


def build(output,repository='JoaoPPolli/HorasJogadas'):
    if len(repository.split('/'))!=2 or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_./' for c in repository):
        raise ValueError('Repositório inválido')
    output=Path(output).resolve()
    if output == ROOT or output in ROOT.parents or output == ROOT/'site':
        raise ValueError('A saída não pode substituir o repositório nem o site-fonte')
    if output.exists():
        if any(output.iterdir()) and not (output/'.generated-by-horasjogadas-site').exists():
            raise ValueError('A saída contém arquivos que não pertencem a este gerador')
        shutil.rmtree(output)
    shutil.copytree(ROOT/'site',output)
    navigation,entries,count=changelog(repository)
    tokens={'__REPOSITORY__':'https://github.com/'+repository,
            '__RELEASE__':'https://github.com/'+repository+'/releases/latest','__VERSION__':VERSION,
            '__VERSION_NAV__':navigation,'__CHANGELOG_ENTRIES__':entries,'__VERSION_COUNT__':count}
    for page in output.rglob('*.html'):
        text=page.read_text(encoding='utf-8')
        for key,value in tokens.items():text=text.replace(key,value)
        page.write_text(text,encoding='utf-8')
    (output/'.nojekyll').write_text('')
    (output/'.generated-by-horasjogadas-site').write_text('')
    return output


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',default=str(ROOT/'build'/'site'))
    parser.add_argument('--repository',default='JoaoPPolli/HorasJogadas')
    args=parser.parse_args(); build(args.output,args.repository)

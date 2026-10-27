"""Gera o site estático com URLs de release explícitas, sem API nem rastreamento no navegador."""
import argparse
import shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
import sys
sys.path.insert(0,str(ROOT))
from horas_jogadas_qt.release import VERSION


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
    html=output/'index.html'
    text=html.read_text(encoding='utf-8').replace('__REPOSITORY__','https://github.com/'+repository).replace('__RELEASE__','https://github.com/'+repository+'/releases/latest').replace('__VERSION__',VERSION)
    html.write_text(text,encoding='utf-8')
    (output/'.nojekyll').write_text('')
    (output/'.generated-by-horasjogadas-site').write_text('')
    return output


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',default=str(ROOT/'build'/'site'))
    parser.add_argument('--repository',default='JoaoPPolli/HorasJogadas')
    args=parser.parse_args(); build(args.output,args.repository)
